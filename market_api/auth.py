"""API key authentication.

The simulator is deployed publicly on Cloud Run, so every data endpoint sits
behind a shared secret. ``/health`` is deliberately exempt so Cloud Run's own
health checks and a quick curl can reach it without a key.

The key is read **per request**, not at import. Binding it at module load meant
whichever test module imported first fixed the key for the whole session, and
more importantly it made the service impossible to reconfigure without a
restart — the same failure mode as building a database client at import time.
"""

from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status


def configured_key() -> str:
    return os.getenv("MARKET_API_KEY", "")


def auth_required() -> bool:
    return os.getenv("REQUIRE_AUTH", "true").lower() == "true"


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency: reject anything without a valid ``X-API-Key``."""
    if not auth_required():
        return

    api_key = configured_key()
    if not api_key:
        # Fail closed. A missing secret is a misconfiguration, not permission
        # to serve the world.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MARKET_API_KEY is not configured on the server.",
        )

    # Constant-time comparison: a plain `!=` leaks key material through timing.
    if x_api_key is None or not secrets.compare_digest(x_api_key, api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid X-API-Key header.",
        )
