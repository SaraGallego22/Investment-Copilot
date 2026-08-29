"""Deterministic price generation.

The market index follows Geometric Brownian Motion; individual assets are
derived from it through a beta plus idiosyncratic noise::

    market:  r_m[t] = (mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z[t]
    asset i: r_i[t] = beta_i * r_m[t] + eps_i[t],  eps_i ~ N(0, idio_vol_i)
    price:   S_i[t] = BASE_PRICE * exp(cumsum(r_i)[t])

Everything is generated once, from a fixed per-scenario seed, and cached. The
same call always returns the same number — the demo has no room for surprises.

Uses only ``random`` from the standard library: no numpy, which keeps the
container image small and the results identical across platforms.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache

from .scenarios import (
    ASSETS,
    BASE_PRICE,
    HORIZON_DAYS,
    SCENARIOS_BY_NAME,
    TRADING_DAYS,
    Scenario,
)


def _market_log_returns(scenario: Scenario) -> list[float]:
    """Daily log returns of the market index under ``scenario``."""
    rng = random.Random(scenario.seed)
    dt = 1.0 / TRADING_DAYS
    drift = (scenario.drift - 0.5 * scenario.vol**2) * dt
    shock = scenario.vol * math.sqrt(dt)
    return [drift + shock * rng.gauss(0.0, 1.0) for _ in range(HORIZON_DAYS)]


def _asset_seed(scenario: Scenario, ticker: str) -> int:
    """A stable per-asset seed derived from the scenario seed.

    Deriving it (rather than drawing from a shared stream) means adding or
    reordering assets never changes the prices of the existing ones.
    """
    return scenario.seed + sum(ord(c) * (i + 1) for i, c in enumerate(ticker))


def _idio_noise(asset_seed: int, idio_vol: float, n: int) -> list[float]:
    """Zero-mean idiosyncratic daily log returns.

    The raw draws are de-meaned on purpose. Left alone, a random walk of
    idiosyncratic noise accumulates its own drift over 90 days, which was
    large enough to send a high-beta asset *down* in a bull market — the
    opposite of what beta is supposed to express. De-meaning keeps the
    day-to-day wiggle while ensuring the cumulative idiosyncratic
    contribution nets to zero, so an asset's overall direction is governed
    by its beta, as the model intends.
    """
    if not idio_vol:
        return [0.0] * n
    rng = random.Random(asset_seed)
    shock = idio_vol * math.sqrt(1.0 / TRADING_DAYS)
    draws = [rng.gauss(0.0, 1.0) for _ in range(n)]
    mean = sum(draws) / n
    return [(d - mean) * shock for d in draws]


def _generate(scenario_name: str) -> dict[str, list[float]]:
    """Generate the full price series for every asset under one scenario.

    Day 0 is exactly ``BASE_PRICE`` for every asset, so the demo can say
    "everything starts at 100" and percentage moves read directly off the chart.
    """
    scenario = SCENARIOS_BY_NAME[scenario_name]
    market_returns = _market_log_returns(scenario)
    steps = HORIZON_DAYS - 1

    series: dict[str, list[float]] = {}
    for asset in ASSETS:
        noise = _idio_noise(_asset_seed(scenario, asset.ticker), asset.idio_vol, steps)

        prices = [BASE_PRICE]
        cumulative = 0.0
        for r_market, eps in zip(market_returns[:steps], noise):
            cumulative += asset.beta * r_market + eps
            prices.append(round(BASE_PRICE * math.exp(cumulative), 2))
        series[asset.ticker] = prices

    return series


@lru_cache(maxsize=len(SCENARIOS_BY_NAME))
def series_for(scenario_name: str) -> dict[str, tuple[float, ...]]:
    """All asset series for ``scenario_name``, generated once and cached.

    Returns tuples so callers cannot mutate the cached data.
    """
    if scenario_name not in SCENARIOS_BY_NAME:
        raise KeyError(scenario_name)
    return {k: tuple(v) for k, v in _generate(scenario_name).items()}


def price_at(scenario_name: str, ticker: str, day: int) -> float:
    """Price of one asset on one day."""
    prices = series_for(scenario_name)[ticker]
    if not 0 <= day < len(prices):
        raise IndexError(day)
    return prices[day]


def snapshot(scenario_name: str, day: int) -> dict[str, float]:
    """Price of every asset on one day."""
    return {t: price_at(scenario_name, t, day) for t in series_for(scenario_name)}


def warm_cache() -> None:
    """Pre-generate every scenario. Called at service startup so the first
    request is not slower than the rest."""
    for name in SCENARIOS_BY_NAME:
        series_for(name)
