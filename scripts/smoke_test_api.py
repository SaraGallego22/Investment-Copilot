"""Smoke-test the market simulator, locally or on Cloud Run.

Verifies every endpoint, that auth is actually enforced, and that repeated
calls return identical prices — the determinism the demo depends on.

    python scripts/smoke_test_api.py --url http://localhost:8081
    python scripts/smoke_test_api.py --url https://jusara-market-api-xxx.run.app

The key is read from --key or from MARKET_API_KEY.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

EXPECTED_ASSETS = {"MARKET", "TECHX", "UTILCO", "GOLDF"}
EXPECTED_SCENARIOS = ["bull", "crash", "recovery"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("MARKET_API_URL", "http://localhost:8081"))
    parser.add_argument("--key", default=os.getenv("MARKET_API_KEY", ""))
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    base = args.url.rstrip("/")
    headers = {"X-API-Key": args.key}
    failures: list[str] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}{f' — {detail}' if detail else ''}")
        if not ok:
            failures.append(label)

    print(f"\nSmoke-testing {base}\n")

    with httpx.Client(timeout=args.timeout, follow_redirects=True) as http:
        # /health — no key required
        try:
            r = http.get(f"{base}/health")
            check("health responds 200", r.status_code == 200, f"status {r.status_code}")
            check("health needs no API key", r.status_code == 200)
        except httpx.HTTPError as exc:
            check("service is reachable", False, str(exc)[:120])
            print("\nCannot reach the service. Is it running?\n")
            return 1

        # auth is enforced
        r = http.get(f"{base}/assets")
        check("data endpoint rejects missing key", r.status_code == 403, f"got {r.status_code}")

        if not args.key:
            print("\nNo API key supplied (--key or MARKET_API_KEY). Skipping data checks.\n")
            return 1 if failures else 0

        # /scenarios
        r = http.get(f"{base}/scenarios", headers=headers)
        names = [s["name"] for s in r.json()] if r.status_code == 200 else []
        check("scenarios returns bull/crash/recovery", names == EXPECTED_SCENARIOS, str(names))

        # /assets
        r = http.get(f"{base}/assets", headers=headers)
        tickers = {a["ticker"] for a in r.json()} if r.status_code == 200 else set()
        check("assets returns the 4 instruments", tickers == EXPECTED_ASSETS, str(sorted(tickers)))

        # /series
        r = http.get(f"{base}/series/TECHX", params={"scenario": "crash"}, headers=headers)
        series = r.json().get("series", []) if r.status_code == 200 else []
        check("series returns 90 days", len(series) == 90, f"{len(series)} points")
        check("series starts at 100", bool(series) and series[0]["price"] == 100.0)

        # /price and /snapshot agree
        r1 = http.get(f"{base}/price/TECHX", params={"scenario": "crash", "day": 15}, headers=headers)
        r2 = http.get(f"{base}/snapshot", params={"scenario": "crash", "day": 15}, headers=headers)
        price = r1.json().get("price") if r1.status_code == 200 else None
        snap = r2.json().get("prices", {}) if r2.status_code == 200 else {}
        check("price and snapshot agree", price is not None and price == snap.get("TECHX"))

        # determinism as seen from outside
        again = http.get(f"{base}/price/TECHX", params={"scenario": "crash", "day": 15}, headers=headers)
        check("repeated call is identical", again.json().get("price") == price, "determinism")

        # the crash must actually crash
        r = http.get(f"{base}/series/MARKET", params={"scenario": "crash"}, headers=headers)
        pts = r.json().get("series", []) if r.status_code == 200 else []
        drop = (pts[-1]["price"] / pts[0]["price"] - 1) if pts else 0.0
        check("crash scenario really drops", drop < -0.15, f"{drop:+.1%}")

        # errors
        r = http.get(f"{base}/series/NOPE", params={"scenario": "bull"}, headers=headers)
        check("unknown ticker is 404", r.status_code == 404, f"got {r.status_code}")
        r = http.get(f"{base}/price/MARKET", params={"scenario": "bull", "day": 999}, headers=headers)
        check("out-of-range day is 400", r.status_code == 400, f"got {r.status_code}")

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {', '.join(failures)}\n")
        return 1
    print("All checks passed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
