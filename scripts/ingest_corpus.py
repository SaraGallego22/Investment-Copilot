"""Chunk, embed and index the corpus.

    python scripts/ingest_corpus.py

Requires the corpus to be present. Run scripts/fetch_corpus.py first.
"""

from __future__ import annotations

import sys

from collaborative_partner import steering
from collaborative_partner.rag.ingest import build_chunks, ingest


def main() -> int:
    chunks = build_chunks()
    if not chunks:
        print("Corpus is empty. Run: python scripts/fetch_corpus.py")
        return 1

    by_source: dict[str, int] = {}
    for c in chunks:
        by_source[c.source_slug] = by_source.get(c.source_slug, 0) + 1

    print(f"\n{len(chunks)} chunks from {len(by_source)} documents:")
    for slug, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>4}  {slug}")

    print(f"\nEmbedding with {steering.EMBEDDING_MODEL} ...")
    count = ingest()
    size_mb = steering.INDEX_PATH.stat().st_size / 1_000_000
    print(f"Indexed {count} chunks -> {steering.INDEX_PATH} ({size_mb:.1f} MB)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
