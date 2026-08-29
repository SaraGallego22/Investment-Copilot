"""Endpoint and auth tests for the market simulator.

``MARKET_API_KEY`` is set before importing the app because ``auth.py`` reads
it at import time.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

TEST_KEY = "test-key-not-a-secret"
os.environ["MARKET_API_KEY"] = TEST_KEY
os.environ["REQUIRE_AUTH"] = "true"

from market_api.main import app  # noqa: E402
from market_api.scenarios import HORIZON_DAYS  # noqa: E402

HEADERS = {"X-API-Key": TEST_KEY}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # `with` runs the lifespan, warming the cache
        yield c


# ── auth ───────────────────────────────────────────────────────────────────


def test_health_needs_no_key(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.parametrize(
    "path",
    ["/scenarios", "/assets", "/series/MARKET?scenario=bull",
     "/price/MARKET?scenario=bull&day=0", "/snapshot?scenario=bull&day=0"],
)
def test_data_endpoints_reject_missing_key(client, path):
    assert client.get(path).status_code == 403


def test_wrong_key_is_rejected(client):
    r = client.get("/assets", headers={"X-API-Key": "wrong"})
    assert r.status_code == 403


# ── endpoints ──────────────────────────────────────────────────────────────


def test_scenarios(client):
    names = [s["name"] for s in client.get("/scenarios", headers=HEADERS).json()]
    assert names == ["bull", "crash", "recovery"]


def test_assets(client):
    assets = client.get("/assets", headers=HEADERS).json()
    assert {a["ticker"] for a in assets} == {"MARKET", "TECHX", "UTILCO", "GOLDF"}
    beta = {a["ticker"]: a["beta"] for a in assets}
    assert beta["TECHX"] > beta["MARKET"] > beta["UTILCO"] > 0 > beta["GOLDF"]


def test_series(client):
    body = client.get("/series/TECHX?scenario=crash", headers=HEADERS).json()
    assert body["ticker"] == "TECHX" and body["scenario"] == "crash"
    assert len(body["series"]) == HORIZON_DAYS
    assert body["series"][0] == {"day": 0, "price": 100.0}


def test_price_and_snapshot_agree(client):
    price = client.get("/price/TECHX?scenario=crash&day=15", headers=HEADERS).json()
    snap = client.get("/snapshot?scenario=crash&day=15", headers=HEADERS).json()
    assert price["price"] == snap["prices"]["TECHX"]
    assert set(snap["prices"]) == {"MARKET", "TECHX", "UTILCO", "GOLDF"}


def test_repeated_calls_return_the_same_price(client):
    """Determinism as seen from outside — what the demo actually relies on."""
    url = "/price/TECHX?scenario=crash&day=42"
    first = client.get(url, headers=HEADERS).json()["price"]
    second = client.get(url, headers=HEADERS).json()["price"]
    assert first == second


# ── errors ─────────────────────────────────────────────────────────────────


def test_unknown_scenario_is_404(client):
    assert client.get("/series/MARKET?scenario=nope", headers=HEADERS).status_code == 404


def test_unknown_ticker_is_404(client):
    assert client.get("/series/NOPE?scenario=bull", headers=HEADERS).status_code == 404


@pytest.mark.parametrize("day", [-1, HORIZON_DAYS, 9999])
def test_out_of_range_day_is_400(client, day):
    r = client.get(f"/price/MARKET?scenario=bull&day={day}", headers=HEADERS)
    assert r.status_code == 400
