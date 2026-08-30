"""Deterministic impact projection. No model involved.

Arithmetic the agent must not improvise: what a portfolio did, what selling
today would lock in, and what a diversified alternative would have done
instead. Computing it here means the numbers in the advice are correct rather
than plausible — a language model asked to compound returns over 90 days will
produce a confident wrong answer, and in a financial context that is the worst
possible failure.
"""

from __future__ import annotations

from .market_tool import _get


def _series(ticker: str, scenario: str) -> list[float]:
    body = _get(f"/series/{ticker}", scenario=scenario)
    return [p["price"] for p in body["series"]]


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
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Portfolio weights must sum to more than zero.")
    normalised = {t: w / total for t, w in weights.items()}

    series = {t: _series(t, scenario)[: day + 1] for t in normalised}
    length = min(len(s) for s in series.values())

    path = []
    for i in range(length):
        value = sum(
            initial * weight * (series[t][i] / series[t][0])
            for t, weight in normalised.items()
        )
        path.append(value)
    return path


def project_portfolio(
    holdings: dict[str, float],
    scenario: str,
    day: int,
    initial_value: float = 10000.0,
) -> dict:
    """What this portfolio has actually done, up to ``day`` of ``scenario``.

    ``holdings`` maps ticker to weight (they are normalised, so {"TECHX": 100}
    and {"TECHX": 1} mean the same thing). Use this before telling a user what
    their position has done — never estimate it.
    """
    path = _portfolio_path(holdings, scenario, day, initial_value)
    return {
        "holdings": holdings,
        "scenario": scenario,
        "day": day,
        **_path_stats(path),
    }


def compare_with_diversified(
    holdings: dict[str, float],
    scenario: str,
    day: int,
    initial_value: float = 10000.0,
) -> dict:
    """This portfolio against an equally weighted spread of every asset.

    The concrete cost — or benefit — of concentration, in the market the user
    is actually looking at. Far more persuasive than the abstract advice to
    diversify, and it cuts both ways: in a bull run concentration wins, and the
    agent should say so rather than pretend otherwise.
    """
    from .market_tool import _get as fetch

    tickers = [a["ticker"] for a in fetch("/assets") if a["ticker"] != "MARKET"]
    equal_weights = {t: 1.0 for t in tickers}

    actual = _path_stats(_portfolio_path(holdings, scenario, day, initial_value))
    diversified = _path_stats(_portfolio_path(equal_weights, scenario, day, initial_value))

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


def selling_now_vs_holding(
    holdings: dict[str, float],
    scenario: str,
    day: int,
    initial_value: float = 10000.0,
) -> dict:
    """What selling today locks in, against what holding to the end of the
    scenario would have produced.

    Use this when a user wants to sell during a drawdown. It is the difference
    between a paper loss and a realised one, in their own numbers.

    Honesty requirement: this compares against ONE simulated path, not a
    forecast. Present it as what this scenario did, never as what the market
    will do. Say so when you use it.
    """
    full_path = _portfolio_path(holdings, scenario, 10_000, initial_value)
    day = min(day, len(full_path) - 1)

    value_today = full_path[day]
    value_at_end = full_path[-1]
    start = full_path[0]

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
