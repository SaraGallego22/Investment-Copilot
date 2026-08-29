"""Chunk the corpus, embed it, and write the index.

Run via ``python scripts/ingest_corpus.py``. The output,
``data/index/corpus_index.json``, is committed: embedding at startup would
cost money on every cold start and make the demo depend on the API being up.

Provenance (``source_org``, ``source_url``, ``license``) is carried from each
document's frontmatter into every chunk, so a retrieved passage can be cited
as "U.S. SEC" rather than as a filename. That citation is what makes the
advice credible on screen.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .. import steering

#: Chunks below this are usually stray headings, above it they blur topics.
MIN_CHUNK_CHARS = 250
MAX_CHUNK_CHARS = 1800

#: Embedding calls are batched; Vertex rejects oversized batches.
BATCH_SIZE = 16


@dataclass
class Chunk:
    chunk_id: str
    text: str
    heading: str
    source_slug: str
    source_org: str
    source_url: str
    license: str
    lang: str
    tier: str
    embedding: list[float] = field(default_factory=list)


def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Split a corpus file into its YAML frontmatter and its body."""
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    meta: dict[str, str] = {}
    for line in raw[3:end].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"')
    return meta, raw[end + 4 :].lstrip()


def split_sections(body: str) -> list[tuple[str, str]]:
    """Split on `##` headings, returning (heading, text) pairs.

    Long sections are broken on paragraph boundaries so no single chunk buries
    a specific claim inside a wall of text.
    """
    parts = re.split(r"\n##\s*", "\n" + body)
    sections: list[tuple[str, str]] = []

    for part in parts:
        if not part.strip():
            continue
        lines = part.strip().split("\n", 1)
        heading = lines[0].strip() if len(lines) > 1 else ""
        text = (lines[1] if len(lines) > 1 else lines[0]).strip()

        if len(text) <= MAX_CHUNK_CHARS:
            sections.append((heading, text))
            continue

        buffer = ""
        for paragraph in text.split("\n\n"):
            if len(buffer) + len(paragraph) > MAX_CHUNK_CHARS and buffer:
                sections.append((heading, buffer.strip()))
                buffer = paragraph
            else:
                buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if buffer.strip():
            sections.append((heading, buffer.strip()))

    return sections


#: Site furniture that survives HTML extraction. These pages open with a US
#: government security banner and a nav menu; indexed, they match any query
#: about "official information" and crowd out the actual guidance.
BOILERPLATE_MARKERS = (
    "skip to main content",
    "the .gov means",
    "before sharing sensitive information",
    "official websites use .gov",
    "securely to the .gov website",
    "https:// means you",
    "sign up for investor updates",
    "check out your investment professional",
)


def is_boilerplate(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in BOILERPLATE_MARKERS)


def load_documents(corpus_path: Path | None = None) -> list[Path]:
    """Every markdown file in the corpus, including the Tier B notes."""
    root = Path(corpus_path or steering.CORPUS_PATH)
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def build_chunks(corpus_path: Path | None = None) -> list[Chunk]:
    """Read the corpus and cut it into chunks, without embedding them."""
    chunks: list[Chunk] = []
    for doc in load_documents(corpus_path):
        meta, body = parse_frontmatter(doc.read_text(encoding="utf-8"))
        slug = doc.stem
        for i, (heading, text) in enumerate(split_sections(body)):
            if len(text) < MIN_CHUNK_CHARS or is_boilerplate(text):
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{slug}#{i}",
                    text=text,
                    heading=heading,
                    source_slug=slug,
                    source_org=meta.get("source_org", "unknown"),
                    source_url=meta.get("source_url", ""),
                    license=meta.get("license", "unknown"),
                    lang=meta.get("lang", "en"),
                    tier=meta.get("tier", "A"),
                )
            )
    return chunks


def embed_texts(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed a list of texts with the configured Gemini embedding model."""
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=steering.USE_VERTEX,
        project=steering.GCP_PROJECT or None,
        location=steering.LOCATION,
    )
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        response = client.models.embed_content(
            model=steering.EMBEDDING_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(task_type=task),
        )
        vectors.extend(e.values for e in response.embeddings)
    return vectors


def ingest(corpus_path: Path | None = None, index_path: Path | None = None) -> int:
    """Chunk, embed and write the index. Returns the number of chunks."""
    chunks = build_chunks(corpus_path)
    if not chunks:
        raise RuntimeError(
            "Corpus is empty. Run `python scripts/fetch_corpus.py` first."
        )

    for chunk, vector in zip(chunks, embed_texts([c.text for c in chunks])):
        chunk.embedding = vector

    out = Path(index_path or steering.INDEX_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "model": steering.EMBEDDING_MODEL,
                "dimensions": len(chunks[0].embedding),
                "chunks": [asdict(c) for c in chunks],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return len(chunks)
