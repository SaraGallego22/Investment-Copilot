"""Memory tools exposed to the agent: what is known about THIS user.

Deliberately separate from ``rag_tool.py``. RAG answers "what is true about
investing"; these answer "what is true about this person".

**The user id is never a parameter the model supplies.** It is read from the
ADK session via ``ToolContext``. An earlier version accepted it as an argument
and the model promptly invented one — it called ``get_user_profile("user_1")``
for a session belonging to "ana", loaded an empty profile, greeted a user with
four sessions of history as a stranger, and then wrote her observations to a
phantom record. Cross-session memory is the entire product, so the identity it
keys on cannot be something a language model guesses.

Each tool is a thin wrapper over a plain function that does take ``user_id``,
so the CLI, the demo and the tests can drive the same logic directly.
"""

from __future__ import annotations

from functools import lru_cache

from google.adk.tools import ToolContext

from ..memory.schema import UserProfile
from ..memory.store import BaseMemoryStore, build_store


@lru_cache(maxsize=1)
def _get_store() -> BaseMemoryStore:
    """Build the store on first use, not at import time.

    Building it at module level ran a Firestore client during
    ``import collaborative_partner``, so the package — and every test touching
    it — failed on machines without GCP credentials.
    """
    return build_store()


def _uid(tool_context: ToolContext) -> str:
    user_id = getattr(tool_context, "user_id", None)
    if not user_id:
        raise RuntimeError(
            "No user_id on the tool context. The session must be created with "
            "the user's id; memory cannot key on a guess."
        )
    return user_id


# ── plain functions (used by the CLI, the demo and the tests) ──────────────


def load_profile(user_id: str) -> dict:
    profile = _get_store().get_or_create(user_id)
    data = profile.model_dump(mode="json")
    data["is_new_user"] = profile.sessions_count == 0
    return data


def observe(user_id: str, pattern_key: str, evidence: str, description: str = "") -> dict:
    store = _get_store()
    profile = store.get_or_create(user_id)
    updated = profile.reinforce(pattern_key, evidence, description or None)
    store.save(profile)
    return {
        "pattern_key": updated.key,
        "confidence": updated.confidence,
        "evidence_count": len(updated.evidence),
    }


def contradict(user_id: str, pattern_key: str, evidence: str) -> dict:
    store = _get_store()
    profile = store.get_or_create(user_id)
    updated = profile.weaken(pattern_key, evidence)
    if updated is None:
        return {"pattern_key": pattern_key, "status": "unknown_pattern"}
    store.save(profile)
    return {"pattern_key": updated.key, "confidence": updated.confidence, "status": "weakened"}


def correct(user_id: str, correction: str) -> dict:
    store = _get_store()
    profile = store.get_or_create(user_id)
    profile.record_correction(correction)
    store.save(profile)
    return {"corrections_count": len(profile.corrections_received)}


def synthesise(user_id: str, gap: str = "", strategy: str = "",
               close_session: bool = True) -> dict:
    store = _get_store()
    profile = store.get_or_create(user_id)
    if gap:
        profile.declared_observed_gap = gap
    if strategy:
        profile.agent_strategy_note = strategy
    if close_session:
        profile.close_session()
    store.save(profile)
    return {
        "user_id": user_id,
        "sessions_count": profile.sessions_count,
        "declared_observed_gap": profile.declared_observed_gap,
        "agent_strategy_note": profile.agent_strategy_note,
    }


def declare(user_id: str, tolerance: str, horizon_years: int, goals: list[str]) -> dict:
    store = _get_store()
    profile = store.get_or_create(user_id)
    profile.declared_tolerance = tolerance  # type: ignore[assignment]
    profile.horizon_years = horizon_years
    profile.goals = goals
    profile.touch()
    UserProfile.model_validate(profile.model_dump())  # fail fast on a bad value
    store.save(profile)
    return profile.model_dump(mode="json")


# ── ADK tools (the model sees these; note: no user_id parameter) ───────────


def get_user_profile(tool_context: ToolContext) -> dict:
    """Load everything known about the current user from previous sessions.

    Call this at the START of every session, before giving any advice. The
    declared profile is what the user claims; ``observed_patterns`` is what
    their behaviour has actually shown. When the two disagree, trust the
    observed one.
    """
    return load_profile(_uid(tool_context))


def record_observation(
    pattern_key: str,
    evidence: str,
    pattern_description: str,
    tool_context: ToolContext,
) -> dict:
    """Record behaviour that SUPPORTS a pattern, raising its confidence.

    Use a stable snake_case ``pattern_key`` ("loss_aversion",
    "fomo_concentration"). Reuse the key of an existing pattern when the
    behaviour repeats, so evidence accumulates instead of fragmenting into
    near-duplicates. ``evidence`` is one concrete sentence about what the user
    did, including the market context: "sesión 5 (crash -40%): pidió vender
    todo el mismo día de la caída".
    """
    return observe(_uid(tool_context), pattern_key, evidence, pattern_description)


def record_contradiction(pattern_key: str, evidence: str, tool_context: ToolContext) -> dict:
    """Record behaviour that CONTRADICTS a pattern, lowering its confidence.

    Use this when the user acts against a pattern you had inferred — holding
    through a drop you expected them to panic on. Without it the profile could
    only ever grow more certain, which is not learning.
    """
    return contradict(_uid(tool_context), pattern_key, evidence)


def record_correction(correction: str, tool_context: ToolContext) -> dict:
    """Save an explicit correction the user made to the agent.

    Call this whenever the user says you misread them. Corrections persist and
    must shape later sessions.
    """
    return correct(_uid(tool_context), correction)


def update_profile_synthesis(
    declared_observed_gap: str,
    agent_strategy_note: str,
    tool_context: ToolContext,
) -> dict:
    """Write the reflection: the gap between what the user declares and what
    they do, and how to treat them next time.

    Call this ONCE at the end of a session, after any observations. This is the
    step that makes the next session different from this one.
    """
    return synthesise(_uid(tool_context), declared_observed_gap, agent_strategy_note)


def set_declared_profile(
    declared_tolerance: str,
    horizon_years: int,
    goals: list[str],
    tool_context: ToolContext,
) -> dict:
    """Store the user's onboarding answers — the DECLARED layer only.

    ``declared_tolerance`` must be "conservative", "moderate" or "aggressive".
    Never write behavioural inferences here; those belong in
    ``record_observation``. Keeping the layers apart is what lets you show the
    user the gap between them.
    """
    return declare(_uid(tool_context), declared_tolerance, horizon_years, goals)
