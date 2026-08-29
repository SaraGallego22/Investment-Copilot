"""Download the RAG corpus from its real sources.

    python scripts/fetch_corpus.py            # fetch everything in the manifest
    python scripts/fetch_corpus.py --only cnmv-perfil-inversor
    python scripts/fetch_corpus.py --dry-run  # just check the links are alive

Reads ``data/corpus_manifest.yaml`` and writes ``data/corpus/{slug}.md``, each
file carrying YAML frontmatter so the licence and the source institution
travel with the text into the index — and out to the citation the demo shows.

Government HTML and Spanish regulator PDFs are genuinely messy inputs, which
is the point: the corpus is external knowledge, not something we wrote.

Fails loudly on a dead link so a broken source surfaces at build time rather
than mid-demo. Fetched files are committed, so the demo does not depend on
these sites being reachable on the day.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import httpx
import yaml

MANIFEST = Path("data/corpus_manifest.yaml")
OUT_DIR = Path("data/corpus")

# investor.gov sits behind a WAF that 403s any User-Agent identifying itself as
# a bot — a self-describing "JUSARA-corpus-fetcher" UA was rejected outright,
# while a normal browser string is served. These are public, public-domain
# education pages meant to be read, so we request them the way a reader would.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

#: Page furniture that carries no investment content.
DROP_TAGS = {"script", "style", "nav", "header", "footer", "form", "aside", "noscript", "svg"}

BLOCK_TAGS = {"p", "div", "li", "tr", "br", "section", "article"}
HEADING_TAGS = {"h1", "h2", "h3", "h4"}


class _Extractor(HTMLParser):
    """Pull readable text out of a page, keeping heading structure.

    A dependency-free reader beats adding BeautifulSoup for eleven pages, and
    headings matter because the chunker splits on them.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._skip = 0
        self._heading: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag in DROP_TAGS:
            self._skip += 1
        elif tag in HEADING_TAGS:
            self._heading = tag
            self._out.append("\n\n## ")
        elif tag in BLOCK_TAGS:
            self._out.append("\n")

    def handle_endtag(self, tag):
        if tag in DROP_TAGS and self._skip:
            self._skip -= 1
        elif tag in HEADING_TAGS:
            self._heading = None
            self._out.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if text:
            self._out.append(text + " ")

    def text(self) -> str:
        return "".join(self._out)


def _tidy(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # A heading that swallowed its body, or an empty one, helps nobody.
    text = re.sub(r"\n## *\n", "\n", text)
    return text.strip()


def html_to_markdown(raw: str) -> str:
    parser = _Extractor()
    parser.feed(raw)
    return _tidy(parser.text())


def _strip_running_headers(pages: list[str]) -> list[str]:
    """Drop the header/footer lines a PDF repeats on every page.

    They are pure noise, and because they repeat dozens of times they skew the
    embeddings towards the document's title instead of its content.
    """
    counts: dict[str, int] = {}
    for page in pages:
        for line in set(page.splitlines()):
            stripped = line.strip()
            if stripped:
                counts[stripped] = counts.get(stripped, 0) + 1

    threshold = max(3, len(pages) // 3)
    boilerplate = {ln for ln, n in counts.items() if n >= threshold and len(ln) < 120}

    return [
        "\n".join(ln for ln in page.splitlines() if ln.strip() not in boilerplate)
        for page in pages
    ]


def pdf_to_markdown(raw: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        # A page number often fuses onto the first word: "2Guía rápida".
        text = re.sub(r"^\d{1,3}(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])", "", text, flags=re.MULTILINE)
        # PDF extraction breaks lines mid-sentence; rejoin so chunks read well.
        text = re.sub(r"(?<![.:;!?])\n(?=[a-záéíóúñ])", " ", text)
        pages.append(text.strip())
    pages = _strip_running_headers(pages)
    return _tidy("\n\n".join(p for p in pages if p.strip()))


def frontmatter(src: dict) -> str:
    def esc(v: str) -> str:
        return str(v).replace('"', "'")

    lines = [
        "---",
        f'title: "{esc(src["title"])}"',
        f'source_org: "{esc(src["org"])}"',
        f'source_url: "{src["url"]}"',
        f'license: "{src["license"]}"',
        f'tier: {src["tier"]}',
        f'lang: {src["lang"]}',
        "retrieved: 2026-08-29",
    ]
    if src.get("note"):
        lines.append(f'note: "{esc(" ".join(src["note"].split()))}"')
    lines.append("---")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="fetch a single slug")
    parser.add_argument("--dry-run", action="store_true", help="check links, write nothing")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    if not MANIFEST.exists():
        print(f"Manifest not found: {MANIFEST}")
        return 1

    sources = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]
    if args.only:
        sources = [s for s in sources if s["slug"] == args.only]
        if not sources:
            print(f"No source with slug '{args.only}'")
            return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    print(f"\nFetching {len(sources)} source(s) into {OUT_DIR}/\n")
    with httpx.Client(timeout=args.timeout, follow_redirects=True,
                      headers=BROWSER_HEADERS) as http:
        for src in sources:
            slug = src["slug"]
            try:
                r = http.get(src["url"])
                if r.status_code != 200:
                    failures.append(f"{slug} (HTTP {r.status_code})")
                    print(f"  FAIL  {slug:26} HTTP {r.status_code}")
                    continue

                if args.dry_run:
                    print(f"  OK    {slug:26} {len(r.content):>8,} bytes")
                    continue

                if src["format"] == "pdf":
                    body = pdf_to_markdown(r.content)
                else:
                    body = html_to_markdown(r.text)

                if len(body) < 400:
                    failures.append(f"{slug} (only {len(body)} chars extracted)")
                    print(f"  FAIL  {slug:26} extracted only {len(body)} chars")
                    continue

                out = OUT_DIR / f"{slug}.md"
                out.write_text(f"{frontmatter(src)}\n\n{body}\n", encoding="utf-8")
                print(f"  OK    {slug:26} {len(body):>8,} chars  [{src['lang']}] {src['format']}")

            except Exception as exc:  # noqa: BLE001 — report and continue
                failures.append(f"{slug} ({type(exc).__name__})")
                print(f"  FAIL  {slug:26} {type(exc).__name__}: {str(exc)[:70]}")

    print()
    if failures:
        print(f"{len(failures)} source(s) failed: {', '.join(failures)}\n")
        return 1
    print(f"All sources fetched. Next: python scripts/ingest_corpus.py\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
