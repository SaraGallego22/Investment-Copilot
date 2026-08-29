"""JUSARA Market Simulator — FastAPI application.

Six endpoints over a deterministic, pre-generated market. The agent consumes
this over HTTP with an API key; it is not importable from the agent package.

Run locally:  uvicorn market_api.main:app --port 8081 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status

from . import simulator
from .auth import require_api_key
from .scenarios import (
    ASSETS,
    ASSETS_BY_TICKER,
    HORIZON_DAYS,
    SCENARIO_NAMES,
    SCENARIOS,
    SCENARIOS_BY_NAME,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Generate every scenario up front so the first request is no slower than
    # the rest — it also surfaces a broken simulator at boot, not mid-demo.
    simulator.warm_cache()
    yield


app = FastAPI(
    title="JUSARA Market Simulator",
    description="Deterministic simulated market data. Not real securities.",
    version="1.0.0",
    lifespan=lifespan,
)


def _validate_scenario(scenario: str) -> str:
    if scenario not in SCENARIOS_BY_NAME:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown scenario '{scenario}'. Valid: {list(SCENARIO_NAMES)}",
        )
    return scenario


def _validate_ticker(ticker: str) -> str:
    if ticker not in ASSETS_BY_TICKER:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown ticker '{ticker}'. Valid: {list(ASSETS_BY_TICKER)}",
        )
    return ticker


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe. Intentionally unauthenticated."""
    return {"status": "ok", "scenarios": list(SCENARIO_NAMES), "days": HORIZON_DAYS}


@app.get("/scenarios", tags=["meta"], dependencies=[Depends(require_api_key)])
async def list_scenarios() -> list[dict]:
    """The available market regimes."""
    return [
        {
            "name": s.name,
            "drift": s.drift,
            "vol": s.vol,
            "description": s.description,
        }
        for s in SCENARIOS
    ]


@app.get("/assets", tags=["meta"], dependencies=[Depends(require_api_key)])
async def list_assets() -> list[dict]:
    """The asset universe, with each instrument's beta to the market."""
    return [
        {"ticker": a.ticker, "type": a.kind, "beta": a.beta, "role": a.role}
        for a in ASSETS
    ]


@app.get("/series/{ticker}", tags=["data"], dependencies=[Depends(require_api_key)])
async def get_series(ticker: str, scenario: str = Query(...)) -> dict:
    """Full price history of one asset under one scenario."""
    ticker = _validate_ticker(ticker)
    scenario = _validate_scenario(scenario)
    prices = simulator.series_for(scenario)[ticker]
    return {
        "ticker": ticker,
        "scenario": scenario,
        "series": [{"day": d, "price": p} for d, p in enumerate(prices)],
    }


@app.get("/price/{ticker}", tags=["data"], dependencies=[Depends(require_api_key)])
async def get_price(ticker: str, scenario: str = Query(...), day: int = Query(...)) -> dict:
    """Price of one asset on one day."""
    ticker = _validate_ticker(ticker)
    scenario = _validate_scenario(scenario)
    try:
        price = simulator.price_at(scenario, ticker, day)
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"day must be between 0 and {HORIZON_DAYS - 1}.",
        )
    return {"ticker": ticker, "scenario": scenario, "day": day, "price": price}


@app.get("/snapshot", tags=["data"], dependencies=[Depends(require_api_key)])
async def get_snapshot(scenario: str = Query(...), day: int = Query(...)) -> dict:
    """Price of every asset on one day — what the agent reads each turn."""
    scenario = _validate_scenario(scenario)
    try:
        prices = simulator.snapshot(scenario, day)
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"day must be between 0 and {HORIZON_DAYS - 1}.",
        )
    return {"scenario": scenario, "day": day, "prices": prices}
