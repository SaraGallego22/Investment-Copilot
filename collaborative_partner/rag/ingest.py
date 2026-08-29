"""Chunking + indexado del corpus en `data/corpus/` hacia el vector store.

Preferir un vector store serverless (evitar clusters siempre
encendidos, ver hackathon-agentic.md sección 6). El backend concreto
(Vertex AI Search / RAG Engine, u otro) se conecta aquí.
"""

from __future__ import annotations

import os
from pathlib import Path

CORPUS_PATH = Path(os.getenv("RAG_CORPUS_PATH", "data/corpus"))


def load_documents(corpus_path: Path = CORPUS_PATH) -> list[Path]:
    if not corpus_path.exists():
        return []
    return sorted(p for p in corpus_path.rglob("*") if p.is_file())


def ingest(corpus_path: Path = CORPUS_PATH) -> int:
    """Indexa los documentos del corpus. Devuelve cuántos se procesaron.

    TODO: implementar chunking + embeddings + upsert al vector store
    elegido (Vertex AI Search / RAG Engine / otro).
    """
    documents = load_documents(corpus_path)
    for doc in documents:
        raise NotImplementedError(
            "Conectar aquí el pipeline de chunking + embeddings + upsert "
            f"para {doc}"
        )
    return len(documents)


if __name__ == "__main__":
    count = ingest()
    print(f"Documentos indexados: {count}")
