"""Market tools exposed to the agent: the environment.

An HTTP client for the separate market simulator service. The agent never
imports the simulator — it calls it over the network with an API key, the same
way it would call a real market data vendor.

These functions return **summaries, not raw series**. Handing a model 90 price
points for each of 4 assets is 360 numbers it has to reason over arithmetically,
which is expensive and exactly the kind of computation a model is bad at. The
drawdown and the percentage move are computed here, deterministically, and the
model gets the conclusions.
"""

from __future__ import annotations

from functools import lru_cache

import httpx

from .. import steering


class MarketUnavailable(RuntimeError):
    """The simulator could not be reached or refused the request."""


@lru_cache(maxsize=1)
def _client() -> httpx.Client:
    return httpx.Client(
        base_url=steering.MARKET_API_URL.rstrip("/"),
        headers={"X-API-Key": steering.MARKET_API_KEY},
        timeout=30.0,
        follow_redirects=True,
    )


def _get(path: str, **params) -> dict:
    try:
        response = _client().get(path, params=params)
    except httpx.HTTPError as exc:
        raise MarketUnavailable(
            f"Cannot reach the market service at {steering.MARKET_API_URL}: {exc}"
        ) from exc

    if response.status_code == 403:
        raise MarketUnavailable("Market service rejected the API key (403).")
    if response.status_code >= 400:
        raise MarketUnavailable(
            f"Market service returned {response.status_code}: {response.text[:200]}"
        )
    return response.json()


def _summarise(prices: list[float]) -> dict:
    """Turn a price path into the handful of numbers that matter."""
    start, end = prices[0], prices[-1]
    peak = start
    max_drawdown = 0.0
    for price in prices:
        peak = max(peak, price)
        max_drawdown = min(max_drawdown, price / peak - 1)
    return {
        "start_price": round(start, 2),
        "current_price": round(end, 2),
        "change_pct": round((end / start - 1) * 100, 1),
        "max_drawdown_pct": round(max_drawdown * 100, 1),
    }


def get_market_snapshot(scenario: str, day: int) -> dict:
    """Current price of every asset on a given day of a scenario.

    Call this before giving any advice about the present moment. Scenarios are
    'bull', 'crash' or 'recovery'; day runs 0-89.
    """
    return _get("/snapshot", scenario=scenario, day=day)


def get_asset_summary(ticker: str, scenario: str, up_to_day: int | None = None) -> dict:
    """How one asset has behaved: change, drawdown, and its role.

    Returns computed statistics rather than the raw series, so the model reads
    conclusions instead of doing arithmetic on 90 numbers.
    """
    body = _get(f"/series/{ticker}", scenario=scenario)
    prices = [p["price"] for p in body["series"]]
    if up_to_day is not None:
        prices = prices[: up_to_day + 1]
    return {"ticker": ticker, "scenario": scenario, "days": len(prices), **_summarise(prices)}


def get_all_assets_summary(scenario: str, up_to_day: int | None = None) -> dict:
    """Compare every asset under one scenario in a single call.

    This is the diversification conversation in one object: which asset
    amplified the move, which cushioned it, which went the other way.
    """
    assets = {a["ticker"]: a for a in _get("/assets")}
    summaries = {
        ticker: {**get_asset_summary(ticker, scenario, up_to_day), "beta": meta["beta"],
                 "role": meta["role"]}
        for ticker, meta in assets.items()
    }
    return {"scenario": scenario, "assets": summaries}


def list_scenarios() -> list[dict]:
    """The market regimes available to reason about."""
    return _get("/scenarios")
