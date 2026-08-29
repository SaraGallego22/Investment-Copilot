"""Static definition of the simulated world: the asset universe and the
three market scenarios.

Both live here because they are the same kind of thing — configuration that
describes *what* is simulated. ``simulator.py`` owns *how* it is generated.

All rates are annualised; the simulator converts them to daily steps.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Trading days per year, used to convert annualised drift/vol to a daily step.
TRADING_DAYS = 252

#: Length of every generated series. ~90 trading days ≈ one quarter.
HORIZON_DAYS = 90

#: Every asset starts here, so percentage moves are readable at a glance.
BASE_PRICE = 100.0


@dataclass(frozen=True)
class Asset:
    """One tradable instrument.

    ``beta`` is its sensitivity to the market index; ``idio_vol`` is the
    annualised volatility of the part of its movement that is *not* explained
    by the market. Together they produce a realistic correlation structure
    without building a real factor model.
    """

    ticker: str
    kind: str
    beta: float
    idio_vol: float
    role: str


#: Four assets is enough to discuss diversification, drawdown and correlation
#: without bloating the demo.
ASSETS: tuple[Asset, ...] = (
    Asset("MARKET", "index", 1.0, 0.00, "The market itself. The reference everything is measured against."),
    Asset("TECHX", "equity", 1.6, 0.25, "High beta. Amplifies every move. The exciting one."),
    Asset("UTILCO", "equity", 0.5, 0.10, "Low beta utility. Boring but steady."),
    Asset("GOLDF", "commodity", -0.2, 0.15, "Safe haven. Tends to rise when everything else falls."),
)

ASSETS_BY_TICKER: dict[str, Asset] = {a.ticker: a for a in ASSETS}


@dataclass(frozen=True)
class Scenario:
    """A market regime.

    ``seed`` is fixed so the same scenario always produces the same prices.
    Determinism is a feature: the demo must not surprise us live.
    """

    name: str
    drift: float
    vol: float
    seed: int
    description: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario("bull", 0.35, 0.14, 20260831, "Steady bull market. The opener."),
    Scenario("crash", -0.75, 0.45, 20260901, "Sharp drawdown. The climax of the demo."),
    Scenario("recovery", 0.90, 0.35, 20260902, "Rebound after the crash. The hopeful close."),
)

SCENARIOS_BY_NAME: dict[str, Scenario] = {s.name: s for s in SCENARIOS}

SCENARIO_NAMES: tuple[str, ...] = tuple(s.name for s in SCENARIOS)
