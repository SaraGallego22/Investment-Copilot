"""Memory tools exposed to the agent: what is known about THIS user.

Deliberately separate from ``rag_tool.py``. RAG answers "what is true about
investing"; these answer "what is true about this person". Keeping them apart
is the difference between a chatbot with retrieval and a partner that learns.

Every function returns a plain ``dict`` because that is what the model
consumes as tool output.
"""

from __future__ import annotations

from functools import lru_cache

from ..memory.schema import UserProfile
from ..memory.store import BaseMemoryStore, build_store


@lru_cache(maxsize=1)
def _get_store() -> BaseMemoryStore:
    """Build the store on first use, not at import time.

    Building it at module level ran a Firestore client during
    ``import collaborative_partner``, so the whole package — and every test
    that touched it — failed on machines without GCP credentials.
    """
    return build_store()


def get_user_profile(user_id: str) -> dict:
    """Load everything known about this user from previous sessions.

    Call this at the START of every session, before giving any advice. The
    declared profile is what the user claims; ``observed_patterns`` is what
    their behaviour has actually shown. When the two disagree, trust the
    observed one.
    """
    profile = _get_store().get_or_create(user_id)
    data = profile.model_dump(mode="json")
    data["is_new_user"] = profile.sessions_count == 0
    return data


def record_observation(
    user_id: str,
    pattern_key: str,
    evidence: str,
    pattern_description: str = "",
) -> dict:
    """Record behaviour that SUPPORTS a pattern, raising its confidence.

    Use a stable, snake_case ``pattern_key`` (e.g. "loss_aversion",
    "concentration_bias") so repeated observations reinforce one pattern
    instead of creating near-duplicates. ``evidence`` should be one concrete
    sentence about what the user did, including the session context.
    """
    store = _get_store()
    profile = store.get_or_create(user_id)
    updated = profile.reinforce(pattern_key, evidence, pattern_description or None)
    store.save(profile)
    return {
        "pattern_key": updated.key,
        "confidence": round(updated.confidence, 2),
        "evidence_count": len(updated.evidence),
    }


def record_contradiction(user_id: str, pattern_key: str, evidence: str) -> dict:
    """Record behaviour that CONTRADICTS a pattern, lowering its confidence.

    Use this when the user acts against a pattern you had inferred — held
    through a drop you expected them to panic on, for example. Without it the
    profile could only ever grow more certain, which is not learning.
    """
    store = _get_store()
    profile = store.get_or_create(user_id)
    updated = profile.weaken(pattern_key, evidence)
    if updated is None:
        return {"pattern_key": pattern_key, "status": "unknown_pattern"}
    store.save(profile)
    return {
        "pattern_key": updated.key,
        "confidence": round(updated.confidence, 2),
        "status": "weakened",
    }


def record_correction(user_id: str, correction: str) -> dict:
    """Save an explicit correction the user made to the agent.

    Call this whenever the user says the agent misread them. These persist and
    must shape later sessions.
    """
    store = _get_store()
    profile = store.get_or_create(user_id)
    profile.record_correction(correction)
    store.save(profile)
    return {"corrections_count": len(profile.corrections_received)}


def update_profile_synthesis(
    user_id: str,
    declared_observed_gap: str = "",
    agent_strategy_note: str = "",
    close_session: bool = True,
) -> dict:
    """Write the reflection: the gap between declared and observed, and how to
    treat this user next time.

    Call this ONCE at the end of a session, after any observations. This is the
    step that makes the next session different from this one.
    """
    store = _get_store()
    profile = store.get_or_create(user_id)
    if declared_observed_gap:
        profile.declared_observed_gap = declared_observed_gap
    if agent_strategy_note:
        profile.agent_strategy_note = agent_strategy_note
    if close_session:
        profile.close_session()
    store.save(profile)
    return {
        "user_id": user_id,
        "sessions_count": profile.sessions_count,
        "declared_observed_gap": profile.declared_observed_gap,
        "agent_strategy_note": profile.agent_strategy_note,
    }


def set_declared_profile(
    user_id: str,
    declared_tolerance: str,
    horizon_years: int,
    goals: list[str],
) -> dict:
    """Store the onboarding answers — the DECLARED layer only.

    Never write behavioural inferences here; those belong in
    ``record_observation``. Keeping the layers separate is what lets the agent
    show the user the gap between them.
    """
    store = _get_store()
    profile = store.get_or_create(user_id)
    profile.declared_tolerance = declared_tolerance  # type: ignore[assignment]
    profile.horizon_years = horizon_years
    profile.goals = goals
    profile.touch()
    UserProfile.model_validate(profile.model_dump())  # fail fast on a bad value
    store.save(profile)
    return profile.model_dump(mode="json")
