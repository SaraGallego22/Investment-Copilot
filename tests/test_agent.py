"""Tests for the tools and the agent wiring.

The market tools are exercised against the real simulator running in-process
via ``TestClient``, not against mocks. Mocking HTTP here would only prove that
the mock matches itself; running the actual service catches a drifting contract
between the two halves of the system, which is the failure that would surface
during the demo.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from market_api.main import app  # noqa: E402

TEST_KEY = "agent-test-key"


@pytest.fixture(scope="module", autouse=True)
def market():
    """Point the market tool's HTTP client at the in-process simulator."""
    from collaborative_partner.tools import market_tool

    os.environ["MARKET_API_KEY"] = TEST_KEY
    os.environ["REQUIRE_AUTH"] = "true"

    with TestClient(app) as client:
        client.headers.update({"X-API-Key": TEST_KEY})
        market_tool._client.cache_clear()
        original = market_tool._client
        market_tool._client = lambda: client
        yield client
        market_tool._client = original
        market_tool._client.cache_clear()


# ── market tool ────────────────────────────────────────────────────────────


def test_snapshot_returns_every_asset():
    from collaborative_partner.tools.market_tool import get_market_snapshot

    snap = get_market_snapshot("crash", 15)
    assert set(snap["prices"]) == {"MARKET", "TECHX", "UTILCO", "GOLDF"}


def test_asset_summary_computes_not_dumps():
    """The model must receive conclusions, not 90 raw numbers to add up."""
    from collaborative_partner.tools.market_tool import get_asset_summary

    summary = get_asset_summary("TECHX", "crash")
    assert set(summary) >= {"change_pct", "max_drawdown_pct", "current_price"}
    assert "series" not in summary
    assert summary["change_pct"] < -30


def test_asset_summary_respects_up_to_day():
    from collaborative_partner.tools.market_tool import get_asset_summary

    early = get_asset_summary("MARKET", "crash", up_to_day=10)
    late = get_asset_summary("MARKET", "crash", up_to_day=80)
    assert early["days"] == 11 and late["days"] == 81
    assert late["change_pct"] < early["change_pct"], "the crash deepens over time"


def test_all_assets_summary_carries_beta_for_the_diversification_talk():
    from collaborative_partner.tools.market_tool import get_all_assets_summary

    assets = get_all_assets_summary("crash")["assets"]
    assert assets["TECHX"]["beta"] == 1.6
    assert assets["TECHX"]["change_pct"] < assets["UTILCO"]["change_pct"]
    assert assets["GOLDF"]["change_pct"] > 0


def test_bad_api_key_surfaces_as_a_readable_error(market):
    """Reported to the model as data, not raised: an exception aborts the run."""
    from collaborative_partner.tools import market_tool

    good = market_tool._client
    try:
        with TestClient(app) as bad:
            bad.headers.update({"X-API-Key": "wrong"})
            market_tool._client = lambda: bad
            result = market_tool.get_market_snapshot("crash", 0)
            assert "403" in result["error"]
    finally:
        # Without this the bad client leaks into every later test in the module.
        market_tool._client = good


# ── projector: the arithmetic the model must not improvise ─────────────────


def test_project_portfolio_normalises_weights():
    from collaborative_partner.tools.projector import project_portfolio

    a = project_portfolio(["TECHX"], [100], "crash", 50)
    b = project_portfolio(["TECHX"], [1], "crash", 50)
    assert a["current_value"] == b["current_value"]


def test_concentration_hurts_more_than_diversification_in_a_crash():
    from collaborative_partner.tools.projector import compare_with_diversified

    result = compare_with_diversified(["TECHX"], [1.0], "crash", 89)
    assert result["your_portfolio"]["change_pct"] < result["equally_diversified"]["change_pct"]
    assert result["value_difference"] < 0
    assert result["drawdown_difference_pct"] < 0, "concentrated drawdown must be deeper"


def test_concentration_wins_in_a_bull_run():
    """The comparison must cut both ways, or it is propaganda rather than advice."""
    from collaborative_partner.tools.projector import compare_with_diversified

    result = compare_with_diversified(["TECHX"], [1.0], "bull", 89)
    assert result["value_difference"] > 0


def test_selling_now_vs_holding_reports_both_and_a_caveat():
    from collaborative_partner.tools.projector import selling_now_vs_holding

    result = selling_now_vs_holding(["TECHX", "UTILCO"], [0.5, 0.5], "recovery", 20)
    assert result["value_if_you_hold_to_end"] > result["value_if_you_sell_today"]
    assert result["realised_loss_pct"] < 0
    assert "no una predicción" in result["caveat"], "must not read as a forecast"


def test_bad_portfolio_returns_an_error_the_model_can_read():
    """A tool exception aborts the whole ADK run, so these must not raise."""
    from collaborative_partner.tools.projector import project_portfolio

    assert "error" in project_portfolio(["TECHX"], [0.0], "crash", 10)
    assert "error" in project_portfolio([], [], "crash", 10)
    assert "error" in project_portfolio(["TECHX", "UTILCO"], [1.0], "crash", 10)
    assert "error" in project_portfolio(["NOSUCH"], [1.0], "crash", 10)


def test_tool_signatures_avoid_dicts():
    """A dict[str, float] has no expressible function-calling schema: Gemini
    invented keys and sent {"hash_1": 50}, which the market service rejected as
    an unknown ticker and which killed the demo run."""
    import inspect

    from collaborative_partner.tools import projector

    for name in ("project_portfolio", "compare_with_diversified", "selling_now_vs_holding"):
        sig = inspect.signature(getattr(projector, name))
        for param in sig.parameters.values():
            assert "dict" not in str(param.annotation).lower(), f"{name}.{param.name}"


# ── agent wiring ───────────────────────────────────────────────────────────


def test_root_agent_has_all_three_systems():
    from collaborative_partner import root_agent

    names = {t.__name__ for t in root_agent.tools}
    assert "get_user_profile" in names, "memory"
    assert "retrieve_theory" in names, "rag"
    assert "get_market_snapshot" in names, "market"
    assert "selling_now_vs_holding" in names, "deterministic arithmetic"


def test_reflection_agent_cannot_give_advice():
    """It writes memory only. No market or theory tools to wander into."""
    from collaborative_partner import reflection_agent

    names = {t.__name__ for t in reflection_agent.tools}
    assert "update_profile_synthesis" in names
    assert not names & {"retrieve_theory", "get_market_snapshot", "project_portfolio"}


def test_reflection_can_both_reinforce_and_contradict():
    from collaborative_partner import reflection_agent

    names = {t.__name__ for t in reflection_agent.tools}
    assert {"record_observation", "record_contradiction"} <= names


def test_models_are_rules_compliant():
    """The contest mandates Gemini 3.5 or newer. 2.x would fail Stage One."""
    from collaborative_partner import reflection_agent, root_agent

    for agent in (root_agent, reflection_agent):
        assert "gemini-3" in agent.model, f"{agent.name} uses {agent.model}"


def test_reflection_uses_a_raised_thinking_budget():
    from collaborative_partner import reflection_agent

    budget = reflection_agent.generate_content_config.thinking_config.thinking_budget
    assert budget >= 4096


def test_advice_temperature_is_low():
    """Invented statistics are the failure mode that matters here."""
    from collaborative_partner import root_agent

    assert root_agent.generate_content_config.temperature <= 0.4


# ── prompt guardrails ──────────────────────────────────────────────────────


def test_prompt_forbids_executing_trades():
    from collaborative_partner.prompts import ROOT_AGENT_INSTRUCTIONS as p

    assert "Nunca ejecutas operaciones" in p
    assert "SIMULADOS" in p


def test_prompt_states_the_central_rule():
    from collaborative_partner.prompts import ROOT_AGENT_INSTRUCTIONS as p

    flat = " ".join(p.split())  # the prompt wraps mid-sentence
    assert "manda la conducta observada" in flat
    assert "confianza >= 0.5" in flat, "acting on a weak pattern must stay forbidden"


def test_prompt_carries_both_confrontation_examples():
    from collaborative_partner.prompts import ROOT_AGENT_INSTRUCTIONS as p

    assert "Ana" in p and "Beto" in p
    assert "Vanguard" in p, "Beto's advice must stay grounded in the real finding"
