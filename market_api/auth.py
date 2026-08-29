"""API key authentication.

The simulator is deployed publicly on Cloud Run, so every data endpoint sits
behind a shared secret. ``/health`` is deliberately exempt so Cloud Run's own
health checks and a quick curl can reach it without a key.
"""

from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status

#: When unset the service refuses every request rather than running open. A
#: missing secret is a misconfiguration, and failing closed is the safe default.
API_KEY = os.getenv("MARKET_API_KEY", "")

REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency: reject anything without a valid ``X-API-Key``."""
    if not REQUIRE_AUTH:
        return

    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MARKET_API_KEY is not configured on the server.",
        )

    # Constant-time comparison: a plain `!=` leaks key material through timing.
    if x_api_key is None or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid X-API-Key header.",
        )
