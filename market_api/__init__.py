"""JUSARA Market Simulator — a standalone, deterministic market data service.

Deployed separately from the agent (Cloud Run service ``jusara-market-api``)
so the agent is an HTTP client rather than a monolith, and so we can stress
the agent against any market condition on demand.

This package must never import from ``collaborative_partner``.
"""
