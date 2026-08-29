"""Tool de RAG expuesta al agente: conocimiento externo del corpus."""

from ..rag.retriever import query as _query


def retrieve_context(question: str) -> list[str]:
    """Recupera fragmentos del corpus relevantes para responder `question`.

    Usar SOLO para conocimiento del corpus/documento, no para nada
    relacionado con el usuario (eso es memoria, ver `memory_tool.py`).
    """
    return _query(question)
