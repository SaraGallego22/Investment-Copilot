"""RAG tool exposed to the agent: external knowledge.

Deliberately separate from ``memory_tool.py``. This answers "what is true
about investing"; memory answers "what is true about this person". Keeping the
two apart is the whole architecture.

Every passage comes back with the institution that published it, because the
agent must be able to say "según la SEC" rather than stating a claim on its own
authority.
"""

from __future__ import annotations

from ..rag.retriever import search


def retrieve_theory(question: str, top_k: int = 3) -> list[dict]:
    """Look up investment theory relevant to ``question``.

    Use this for anything about how investing works — diversification,
    drawdowns, risk profiles, behavioural biases. Do NOT use it for anything
    about the user; that is what the memory tools are for.

    Always cite ``source_org`` in your answer. Never present a retrieved claim
    as your own opinion, and never invent a source that did not come back here.
    """
    return [
        {
            "text": r.text,
            "source_org": r.source_org,
            "source_url": r.source_url,
            "section": r.heading,
            "language": r.lang,
            "relevance": r.score,
        }
        for r in search(question, top_k=top_k)
    ]


#: Kept so older call sites and the ADK tool list keep working.
retrieve_context = retrieve_theory
