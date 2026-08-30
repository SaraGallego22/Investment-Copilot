"""Deterministic impact projection. No model involved.

Arithmetic the agent must not improvise: what a portfolio did, what selling
today would lock in, and what a diversified alternative would have done
instead. Computing it here means the numbers in the advice are correct rather
than plausible — a language model asked to compound returns over 90 days will
produce a confident wrong answer, and in a financial context that is the worst
possible failure.

**Portfolios cross the tool boundary as two parallel lists, not a dict.** A
``dict[str, float]`` with arbitrary keys has no expressible function-calling
schema, so Gemini invented placeholder keys and sent ``{"hash_1": 50}``, which
reached the market service as a request for a ticker named ``hash_1``. Lists of
strings and floats have an exact schema and the model fills them correctly.
"""

from __future__ import annotations

import functools
from .market_tool import MarketUnavailable, _get


def _series(ticker: str, scenario: str) -> list[float]:
    body = _get(f"/series/{ticker}", scenario=scenario)
    return [p["price"] for p in body["series"]]


def _weights(tickers: list[str], weights: list[float]) -> dict[str, float]:
    """Pair and normalise the two lists the model supplies."""
    if not tickers:
        raise ValueError("tickers must not be empty.")
    if len(tickers) != len(weights):
        raise ValueError(
            f"tickers and weights must be the same length "
            f"({len(tickers)} vs {len(weights)})."
        )
    total = sum(weights)
    if total <= 0:
        raise ValueError("Weights must sum to more than zero.")
    return {t: w / total for t, w in zip(tickers, weights)}


def _path_stats(values: list[float]) -> dict:
    start, end = values[0], values[-1]
    peak = start
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1)
    return {
        "start_value": round(start, 2),
        "current_value": round(end, 2),
        "change_pct": round((end / start - 1) * 100, 1),
        "max_drawdown_pct": round(max_drawdown * 100, 1),
    }


def _portfolio_path(weights: dict[str, float], scenario: str, day: int,
                    initial: float) -> list[float]:
    series = {t: _series(t, scenario)[: day + 1] for t in weights}
    length = min(len(s) for s in series.values())
    return [
        sum(initial * w * (series[t][i] / series[t][0]) for t, w in weights.items())
        for i in range(length)
    ]


def _guard(fn):
    """Return a readable error to the model instead of killing the session.

    A tool exception aborts the whole ADK run. During a live demo a cold market
    container or a mistyped ticker would end the conversation outright; handing
    the model the problem lets it apologise, retry or ask, which is what a
    person would do.
    """

    @functools.wraps(fn)  # keeps the signature ADK introspects to build the
    def wrapper(*args, **kwargs):  # tool declaration; without it ADK declared
        try:                       # a no-argument tool and called it with none
            return fn(*args, **kwargs)
        except (MarketUnavailable, ValueError, KeyError, IndexError) as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    return wrapper


@_guard
def project_portfolio(
    tickers: list[str],
    weights: list[float],
    scenario: str,
    day: int,
) -> dict:
    """What a portfolio has actually done, up to ``day`` of ``scenario``.

    ``tickers`` and ``weights`` are parallel lists of the same length, e.g.
    tickers ["TECHX", "UTILCO"] with weights [0.5, 0.5]. Weights are normalised,
    so [50, 50] and [0.5, 0.5] mean the same thing. Valid tickers are MARKET,
    TECHX, UTILCO and GOLDF.

    Use this before telling a user what their position has done. Never estimate
    it yourself.
    """
    path = _portfolio_path(_weights(tickers, weights), scenario, day, 10000.0)
    return {
        "holdings": dict(zip(tickers, weights)),
        "scenario": scenario,
        "day": day,
        "initial_value": 10000.0,
        **_path_stats(path),
    }


@_guard
def compare_with_diversified(
    tickers: list[str],
    weights: list[float],
    scenario: str,
    day: int,
) -> dict:
    """This portfolio against an equally weighted spread of every asset.

    The concrete cost — or benefit — of concentration, in the market the user is
    actually looking at. Far more persuasive than the abstract advice to
    diversify, and it cuts both ways: in a bull run concentration wins, and you
    should say so rather than pretend otherwise.
    """
    universe = [a["ticker"] for a in _get("/assets") if a["ticker"] != "MARKET"]
    equal = {t: 1.0 / len(universe) for t in universe}

    actual = _path_stats(_portfolio_path(_weights(tickers, weights), scenario, day, 10000.0))
    diversified = _path_stats(_portfolio_path(equal, scenario, day, 10000.0))

    return {
        "scenario": scenario,
        "day": day,
        "your_portfolio": actual,
        "equally_diversified": diversified,
        "value_difference": round(actual["current_value"] - diversified["current_value"], 2),
        "drawdown_difference_pct": round(
            actual["max_drawdown_pct"] - diversified["max_drawdown_pct"], 1
        ),
    }


@_guard
def selling_now_vs_holding(
    tickers: list[str],
    weights: list[float],
    scenario: str,
    day: int,
) -> dict:
    """What selling today locks in, against holding to the end of the scenario.

    Use this when a user wants to sell during a drawdown: it is the difference
    between a paper loss and a realised one, in their own numbers.

    Honesty requirement: this compares against ONE simulated path, not a
    forecast. Present it as what this scenario did, never as what the market
    will do, and say so when you use it.
    """
    full_path = _portfolio_path(_weights(tickers, weights), scenario, 10_000, 10000.0)
    day = min(day, len(full_path) - 1)

    value_today, value_at_end, start = full_path[day], full_path[-1], full_path[0]
    return {
        "scenario": scenario,
        "day": day,
        "value_if_you_sell_today": round(value_today, 2),
        "realised_loss_pct": round((value_today / start - 1) * 100, 1),
        "value_if_you_hold_to_end": round(value_at_end, 2),
        "difference": round(value_at_end - value_today, 2),
        "caveat": (
            "Este es el recorrido de UN escenario simulado, no una predicción. "
            "Sirve para ver la diferencia entre una pérdida en papel y una realizada."
        ),
    }
