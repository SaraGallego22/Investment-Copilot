"""Search the corpus index.

Cosine similarity in pure Python over a precomputed JSON index. For a corpus
this size that is a few milliseconds — a vector database would add an
always-on cluster, a dependency and a cost for no measurable gain, which the
hackathon's own guidance advises against.

Every result carries its source institution and URL. The agent must be able to
say "según la SEC" rather than "según diversification.md"; provenance is what
separates a grounded answer from a confident one.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .. import steering


@dataclass
class Result:
    """One retrieved passage, with everything needed to cite it."""

    text: str
    heading: str
    source_org: str
    source_url: str
    source_slug: str
    license: str
    lang: str
    score: float

    def citation(self) -> str:
        return f"{self.source_org} — {self.heading}" if self.heading else self.source_org


@lru_cache(maxsize=2)
def _load_index(path_str: str) -> dict:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"No corpus index at {path}. Run:\n"
            "  python scripts/fetch_corpus.py\n"
            "  python scripts/ingest_corpus.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_query(text: str) -> list[float]:
    """Embed a query.

    Uses task type RETRIEVAL_QUERY, which is asymmetric with the
    RETRIEVAL_DOCUMENT type used at ingest — that pairing is what the model is
    trained for and it measurably improves ranking.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=steering.USE_VERTEX,
        project=steering.GCP_PROJECT or None,
        location=steering.LOCATION,
    )
    response = client.models.embed_content(
        model=steering.EMBEDDING_MODEL,
        contents=[text],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return response.embeddings[0].values


#: Cap on passages returned from any one document.
#:
#: Two problems, one fix. Without it a query like "does gold protect in a
#: crash?" returns three passages from the same paper: it burns the context
#: budget and hands the agent one source dressed as three. It also lets
#: same-language documents monopolise the results — the Spanish notes and CNMV
#: outrank the English SEC material on every Spanish query, burying our most
#: authoritative and freely redistributable source. Diversifying by document
#: surfaces genuinely different sources, in both languages.
MAX_PER_SOURCE = 1


def search(
    text: str,
    top_k: int | None = None,
    index_path: Path | None = None,
    max_per_source: int = MAX_PER_SOURCE,
) -> list[Result]:
    """Return the passages most relevant to ``text``, best first.

    At most ``max_per_source`` passages come from any single document.
    """
    index = _load_index(str(index_path or steering.INDEX_PATH))
    query_vector = embed_query(text)

    scored = [
        (cosine(query_vector, chunk["embedding"]), chunk) for chunk in index["chunks"]
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    limit = top_k or steering.RAG_TOP_K
    seen: dict[str, int] = {}
    results: list[Result] = []

    for score, chunk in scored:
        slug = chunk["source_slug"]
        if seen.get(slug, 0) >= max_per_source:
            continue
        seen[slug] = seen.get(slug, 0) + 1
        results.append(
            Result(
                text=chunk["text"],
                heading=chunk["heading"],
                source_org=chunk["source_org"],
                source_url=chunk["source_url"],
                source_slug=slug,
                license=chunk["license"],
                lang=chunk["lang"],
                score=round(score, 4),
            )
        )
        if len(results) >= limit:
            break

    return results


def query(text: str, top_k: int | None = None) -> list[str]:
    """Backwards-compatible view: retrieved passages as cited strings."""
    return [f"[{r.citation()}]\n{r.text}" for r in search(text, top_k)]
