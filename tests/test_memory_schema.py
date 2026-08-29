"""Tests for the user profile and its persistence.

Replaces the scaffold's ``test_memory.py``, which tested a single-layer
dataclass that no longer exists.

The behaviour under test is the product's core claim: the profile does not
just store what the user said, it revises what the agent believes about them
as evidence accumulates.
"""

from __future__ import annotations

import json

import pytest

from collaborative_partner.memory.schema import (
    CONFIDENCE_CAP,
    CONFIDENCE_FLOOR,
    INITIAL_CONFIDENCE,
    ObservedPattern,
    UserProfile,
)
from collaborative_partner.memory.store import JsonMemoryStore, build_store


@pytest.fixture
def profile() -> UserProfile:
    return UserProfile(user_id="test", declared_tolerance="moderate", horizon_years=10)


@pytest.fixture
def store(tmp_path) -> JsonMemoryStore:
    return JsonMemoryStore(tmp_path)


# ── the two layers stay separate ───────────────────────────────────────────


def test_declared_and_observed_are_independent(profile):
    profile.reinforce("loss_aversion", "sold on a 5% dip")
    assert profile.declared_tolerance == "moderate", "observing must not rewrite the declared layer"
    assert profile.observed_patterns[0].key == "loss_aversion"


def test_invalid_tolerance_is_rejected():
    with pytest.raises(Exception):
        UserProfile(user_id="x", declared_tolerance="reckless")


# ── learning ───────────────────────────────────────────────────────────────


def test_first_observation_starts_tentative(profile):
    p = profile.reinforce("loss_aversion", "first sighting")
    assert p.confidence == INITIAL_CONFIDENCE
    assert len(profile.observed_patterns) == 1


def test_repeated_evidence_raises_confidence(profile):
    first = profile.reinforce("loss_aversion", "session 2: asked to sell").confidence
    second = profile.reinforce("loss_aversion", "session 4: wanted all cash").confidence
    assert second > first
    assert len(profile.observed_patterns) == 1, "same key must not create a duplicate"
    assert len(profile.find("loss_aversion").evidence) == 2


def test_confidence_is_capped(profile):
    for i in range(50):
        profile.reinforce("loss_aversion", f"evidence {i}")
    assert profile.find("loss_aversion").confidence <= CONFIDENCE_CAP
    assert profile.find("loss_aversion").confidence == CONFIDENCE_CAP


def test_confidence_stays_a_clean_number(profile):
    """Shown on screen in the demo: 0.7999999999999999 must never appear."""
    for i in range(6):
        profile.reinforce("loss_aversion", f"e{i}")
        c = profile.find("loss_aversion").confidence
        assert c == round(c, 2), f"float noise leaked: {c!r}"
    for i in range(3):
        profile.weaken("loss_aversion", f"c{i}")
        c = profile.find("loss_aversion").confidence
        assert c == round(c, 2), f"float noise leaked: {c!r}"


def test_duplicate_evidence_is_not_stored_twice(profile):
    profile.reinforce("loss_aversion", "same note")
    profile.reinforce("loss_aversion", "same note")
    assert len(profile.find("loss_aversion").evidence) == 1


def test_contradicting_evidence_lowers_confidence(profile):
    profile.reinforce("loss_aversion", "sold on a dip")
    profile.reinforce("loss_aversion", "sold again")
    before = profile.find("loss_aversion").confidence
    profile.weaken("loss_aversion", "held through a 12% drop")
    after = profile.find("loss_aversion").confidence
    assert after < before, "memory that can only grow more certain is not learning"


def test_confidence_has_a_floor(profile):
    profile.reinforce("loss_aversion", "once")
    for i in range(50):
        profile.weaken("loss_aversion", f"counter {i}")
    assert profile.find("loss_aversion").confidence == CONFIDENCE_FLOOR


def test_weakening_an_unknown_pattern_is_a_noop(profile):
    assert profile.weaken("never_seen", "evidence") is None


def test_confident_patterns_are_filtered_and_ranked(profile):
    profile.reinforce("weak", "one")
    for i in range(5):
        profile.reinforce("strong", f"e{i}")
    keys = [p.key for p in profile.confident_patterns(threshold=0.5)]
    assert keys == ["strong"]


def test_corrections_and_sessions_are_tracked(profile):
    profile.record_correction("don't talk to me like a beginner")
    profile.record_correction("don't talk to me like a beginner")
    profile.close_session()
    assert len(profile.corrections_received) == 1
    assert profile.sessions_count == 1


def test_touch_advances_timestamp(profile):
    before = profile.last_updated
    profile.reinforce("k", "e")
    assert profile.last_updated >= before


# ── persistence ────────────────────────────────────────────────────────────


def test_round_trip_preserves_everything(store, profile):
    profile.reinforce("loss_aversion", "session 2", "Sells on any red")
    profile.declared_observed_gap = "declares moderate, acts conservative"
    profile.agent_strategy_note = "confront with horizon first"
    store.save(profile)

    loaded = store.get("test")
    assert loaded == profile


def test_unknown_user_returns_none_and_get_or_create_builds_one(store):
    assert store.get("nobody") is None
    fresh = store.get_or_create("nobody")
    assert fresh.user_id == "nobody" and fresh.sessions_count == 0


def test_saved_file_is_readable_json(store, profile):
    """The demo shows `git diff` on this file, so it must stay human-readable."""
    profile.reinforce("loss_aversion", "session 2")
    store.save(profile)
    text = (store.path / "test.json").read_text(encoding="utf-8")
    assert "\n  " in text, "must be indented"
    assert text.endswith("\n"), "trailing newline keeps diffs clean"
    assert json.loads(text)["observed_patterns"][0]["key"] == "loss_aversion"


def test_accents_are_not_escaped(store, profile):
    """Spanish profiles must stay legible on screen, not \\u00e1 soup."""
    profile.goals = ["jubilación"]
    store.save(profile)
    assert "jubilación" in (store.path / "test.json").read_text(encoding="utf-8")


def test_save_is_atomic_and_leaves_no_temp_files(store, profile):
    store.save(profile)
    store.save(profile)
    assert list(store.path.glob("*.tmp")) == []
    assert store.list_users() == ["test"]


def test_confidence_survives_the_round_trip(store, profile):
    for i in range(3):
        profile.reinforce("loss_aversion", f"e{i}")
    expected = profile.find("loss_aversion").confidence
    store.save(profile)
    assert store.get("test").find("loss_aversion").confidence == expected


# ── factory ────────────────────────────────────────────────────────────────


def test_build_store_selects_json():
    assert isinstance(build_store("json"), JsonMemoryStore)


def test_build_store_rejects_unknown_backend():
    with pytest.raises(ValueError):
        build_store("postgres")


# ── the seeded personas ────────────────────────────────────────────────────


def test_seeded_personas_embody_the_gap():
    """Ana and Beto must actually contradict themselves, or the demo has no point."""
    from scripts.seed_memory import ANA, BETO

    assert ANA.declared_tolerance == "moderate"
    assert BETO.declared_tolerance == "aggressive"
    for persona in (ANA, BETO):
        assert persona.declared_observed_gap, "the gap must be written down"
        assert persona.agent_strategy_note, "the agent needs a plan for this user"
        assert persona.observed_patterns, "seeded users need prior history"
        assert persona.confident_patterns(0.5), "at least one pattern strong enough to act on"
        for pattern in persona.observed_patterns:
            assert pattern.evidence, f"{pattern.key} has no supporting evidence"
