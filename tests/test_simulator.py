"""The simulator's two guarantees: it is deterministic, and it tells the
story the demo depends on.

The narrative tests are not decoration. The Ana-vs-Beto demo only works if a
crash actually crashes, if the high-beta asset falls harder than the market,
and if the safe haven rises. If a future tuning of the scenario parameters
quietly breaks that, these tests catch it before the recording does.
"""

from __future__ import annotations

import pytest

from market_api.scenarios import ASSETS, BASE_PRICE, HORIZON_DAYS, SCENARIO_NAMES
from market_api.simulator import price_at, series_for, snapshot

TICKERS = [a.ticker for a in ASSETS]


def total_return(scenario: str, ticker: str) -> float:
    prices = series_for(scenario)[ticker]
    return prices[-1] / prices[0] - 1


# ── determinism ────────────────────────────────────────────────────────────


def test_regeneration_is_identical():
    """Clearing the cache and regenerating must produce the exact same prices."""
    series_for.cache_clear()
    first = {s: dict(series_for(s)) for s in SCENARIO_NAMES}
    series_for.cache_clear()
    second = {s: dict(series_for(s)) for s in SCENARIO_NAMES}
    assert first == second


def test_scenarios_differ_from_each_other():
    """Determinism must not come from every scenario being the same series."""
    bull = series_for("bull")["MARKET"]
    crash = series_for("crash")["MARKET"]
    assert bull != crash


def test_asset_seeds_are_independent():
    """Two assets under the same scenario must not share a price path."""
    s = series_for("crash")
    assert s["TECHX"] != s["UTILCO"]


# ── shape ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("scenario", SCENARIO_NAMES)
@pytest.mark.parametrize("ticker", TICKERS)
def test_series_shape(scenario: str, ticker: str):
    prices = series_for(scenario)[ticker]
    assert len(prices) == HORIZON_DAYS
    assert prices[0] == BASE_PRICE, "day 0 must be exactly the base price"
    assert all(p > 0 for p in prices), "a price can never be zero or negative"


def test_snapshot_matches_series():
    day = 15
    snap = snapshot("crash", day)
    assert set(snap) == set(TICKERS)
    for ticker, price in snap.items():
        assert price == series_for("crash")[ticker][day] == price_at("crash", ticker, day)


def test_out_of_range_day_raises():
    with pytest.raises(IndexError):
        price_at("crash", "MARKET", HORIZON_DAYS)
    with pytest.raises(IndexError):
        price_at("crash", "MARKET", -1)


def test_unknown_scenario_raises():
    with pytest.raises(KeyError):
        series_for("apocalypse")


# ── narrative: the demo depends on these ───────────────────────────────────


def test_crash_actually_crashes():
    assert total_return("crash", "MARKET") < -0.15


def test_bull_rises_and_recovery_rebounds():
    assert total_return("bull", "MARKET") > 0
    assert total_return("recovery", "MARKET") > 0.20


@pytest.mark.parametrize("scenario", ["bull", "crash", "recovery"])
def test_high_beta_amplifies_the_market(scenario: str):
    """TECHX (beta 1.6) must move further than MARKET in the same direction."""
    market = total_return(scenario, "MARKET")
    techx = total_return(scenario, "TECHX")
    assert abs(techx) > abs(market)
    assert (techx > 0) == (market > 0), "amplified, not inverted"


def test_low_beta_defends_in_the_crash():
    """UTILCO (beta 0.5) must lose less than the market."""
    assert total_return("crash", "UTILCO") > total_return("crash", "MARKET")


def test_safe_haven_rises_when_the_market_falls():
    """GOLDF (beta -0.2) is the reason a diversification conversation is possible."""
    assert total_return("crash", "MARKET") < 0
    assert total_return("crash", "GOLDF") > 0


def test_crash_has_a_real_drawdown():
    prices = series_for("crash")["MARKET"]
    peak = prices[0]
    max_dd = 0.0
    for p in prices:
        peak = max(peak, p)
        max_dd = min(max_dd, p / peak - 1)
    assert max_dd < -0.15
