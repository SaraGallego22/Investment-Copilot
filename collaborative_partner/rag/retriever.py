"""Consulta al vector store del corpus indexado por `ingest.py`."""

from __future__ import annotations


def query(text: str, top_k: int = 5) -> list[str]:
    """Devuelve los `top_k` fragmentos del corpus más relevantes para `text`.

    TODO: conectar al vector store real (Vertex AI Search / RAG Engine).
    """
    raise NotImplementedError("Conectar retriever al vector store del corpus")
