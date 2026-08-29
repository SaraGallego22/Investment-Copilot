"""The user profile — what the agent knows about *this person* across sessions.

This is the half of the system that is deliberately NOT RAG. RAG holds
investment theory, identical for everyone; this holds one user's history.

The profile has two layers, and the gap between them is the whole product:

* **declared** — what the user said in onboarding, the same thing a broker's
  risk questionnaire collects. Cheap to gather, and often wrong.
* **observed** — what their behaviour actually showed, accumulated over
  sessions with a confidence that rises as evidence repeats.

A profile that only ever *recalled* the declared layer would be a database.
What makes it memory is ``reinforce`` / ``weaken``: the agent revises its
belief about the user as evidence arrives.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

RiskTolerance = Literal["conservative", "moderate", "aggressive"]

#: Confidence assigned the first time a pattern is observed. Deliberately low:
#: one data point is a hypothesis, not a conclusion.
INITIAL_CONFIDENCE = 0.30

#: How much each new piece of evidence moves confidence.
CONFIDENCE_STEP = 0.10

#: Never reach 1.0. The agent should stay open to being wrong about someone.
CONFIDENCE_CAP = 0.95

#: Never reach 0.0 either — keep the pattern visible so contradicting evidence
#: is recorded rather than silently discarded.
CONFIDENCE_FLOOR = 0.05

#: Confidence is rounded on every write. Repeated float addition produces
#: values like 0.7999999999999999, and this number is shown on screen during
#: the demo — a profile is a document a person reads, not a raw accumulator.
CONFIDENCE_PRECISION = 2


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ObservedPattern(BaseModel):
    """One behavioural pattern the agent has inferred about the user."""

    #: Stable slug (e.g. "loss_aversion"). The agent identifies patterns by
    #: this rather than by prose, so re-wording the description never creates
    #: an accidental duplicate.
    key: str
    pattern: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = INITIAL_CONFIDENCE

    def add_evidence(self, note: str) -> None:
        if note not in self.evidence:
            self.evidence.append(note)


class UserProfile(BaseModel):
    """Everything persisted about one user, across every session."""

    user_id: str

    # ── declared layer (onboarding) ────────────────────────────────────────
    declared_tolerance: RiskTolerance = "moderate"
    horizon_years: int = 5
    goals: list[str] = Field(default_factory=list)

    # ── observed layer (learned) ───────────────────────────────────────────
    observed_patterns: list[ObservedPattern] = Field(default_factory=list)
    #: The central insight, written by the reflection step in plain language.
    declared_observed_gap: str | None = None
    #: How the agent should treat this user next time.
    agent_strategy_note: str | None = None

    # ── history ────────────────────────────────────────────────────────────
    sessions_count: int = 0
    corrections_received: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=_now)

    # ── behaviour ──────────────────────────────────────────────────────────

    def find(self, key: str) -> ObservedPattern | None:
        return next((p for p in self.observed_patterns if p.key == key), None)

    def reinforce(self, key: str, evidence: str, pattern: str | None = None) -> ObservedPattern:
        """Record evidence supporting a pattern, raising its confidence.

        Creates the pattern if it is new. This is the step that turns a store
        into memory that learns.
        """
        existing = self.find(key)
        if existing is None:
            existing = ObservedPattern(
                key=key,
                pattern=pattern or key.replace("_", " "),
                confidence=INITIAL_CONFIDENCE,
            )
            self.observed_patterns.append(existing)
        else:
            existing.confidence = round(
                min(CONFIDENCE_CAP, existing.confidence + CONFIDENCE_STEP),
                CONFIDENCE_PRECISION,
            )
            if pattern:
                existing.pattern = pattern
        existing.add_evidence(evidence)
        self.touch()
        return existing

    def weaken(self, key: str, evidence: str) -> ObservedPattern | None:
        """Record evidence *contradicting* a pattern, lowering its confidence.

        Without this the profile could only ever become more certain, which is
        not learning — it is confirmation bias with a JSON file.
        """
        existing = self.find(key)
        if existing is None:
            return None
        existing.confidence = round(
            max(CONFIDENCE_FLOOR, existing.confidence - CONFIDENCE_STEP),
            CONFIDENCE_PRECISION,
        )
        existing.add_evidence(f"[contradicts] {evidence}")
        self.touch()
        return existing

    def record_correction(self, correction: str) -> None:
        """The user explicitly told the agent it got something wrong."""
        if correction not in self.corrections_received:
            self.corrections_received.append(correction)
        self.touch()

    def close_session(self) -> None:
        self.sessions_count += 1
        self.touch()

    def touch(self) -> None:
        self.last_updated = _now()

    def confident_patterns(self, threshold: float = 0.5) -> list[ObservedPattern]:
        """Patterns the agent should actually act on, strongest first."""
        strong = [p for p in self.observed_patterns if p.confidence >= threshold]
        return sorted(strong, key=lambda p: p.confidence, reverse=True)
