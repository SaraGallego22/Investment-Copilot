"""Shared configuration — the single source of truth for the team.

Every module reads its settings from here instead of calling ``os.getenv``
directly, so a change lands in exactly one place. Before making a design
change that touches these values, update this file first and tell the team.

All defaults were verified live against the GCP project on 2026-08-29:

* Gemini 3.5 models are served **only from the ``global`` endpoint**. They
  return 404 in us-central1, us-east5, europe-west4, us-west1 and
  asia-northeast1. ``LOCATION`` must stay ``global``.
* No Pro-class 3.5 model exists on this project (every ``gemini-3.5-pro*``
  variant 404s everywhere). The reflection step therefore uses the *same*
  Flash model with a raised thinking budget rather than a larger model.
  ``gemini-2.5-pro`` exists but violates the contest's "3.5 or newer" rule.

Re-verify with ``python cli.py check``.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_NAME = "JUSARA"

# ── Google Cloud ────────────────────────────────────────────────────────────
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
USE_VERTEX = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
# Where containers run. NOT the same as LOCATION: "global" is a valid Vertex
# model endpoint but not a valid Cloud Run region.
CLOUD_RUN_REGION = os.getenv("CLOUD_RUN_REGION", "us-central1")

# ── Models (contest mandates Gemini 3.5 or newer — do not downgrade) ────────
MODEL_DEFAULT = os.getenv("MODEL_DEFAULT", "gemini-3.5-flash")
MODEL_COMPLEX_REASONING = os.getenv("MODEL_COMPLEX_REASONING", "gemini-3.5-flash")
REFLECTION_THINKING_BUDGET = int(os.getenv("REFLECTION_THINKING_BUDGET", "8192"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

# ── Memory: the user (declared + observed layers) ───────────────────────────
MEMORY_BACKEND = os.getenv("MEMORY_BACKEND", "json")  # "json" | "firestore"
MEMORY_PATH = Path(os.getenv("MEMORY_PATH", "data/memory"))
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION_USER_PROFILES", "user_profiles")

# ── RAG: the world (external theory corpus) ─────────────────────────────────
CORPUS_PATH = Path(os.getenv("RAG_CORPUS_PATH", "data/corpus"))
INDEX_PATH = Path(os.getenv("RAG_INDEX_PATH", "data/index/corpus_index.json"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

# ── Market Simulator API: the environment ───────────────────────────────────
MARKET_API_URL = os.getenv("MARKET_API_URL", "http://localhost:8081")
MARKET_API_KEY = os.getenv("MARKET_API_KEY", "")
MARKET_SCENARIOS = ("bull", "crash", "recovery")
MARKET_ASSETS = ("MARKET", "TECHX", "UTILCO", "GOLDF")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"

# ── Behaviour flags ─────────────────────────────────────────────────────────
ENABLE_REFLECTION = os.getenv("ENABLE_REFLECTION", "true").lower() == "true"
PRIORITIZE_CLARITY = True  # ask a clarifying question rather than assume

#: Flat view of the settings above. Handy for logging and for the demo, which
#: prints the active configuration so the jury can see nothing is hidden.
STEERING_HOOKS: dict[str, object] = {
    "project_name": PROJECT_NAME,
    "gcp_project": GCP_PROJECT,
    "location": LOCATION,
    "preferred_model": MODEL_DEFAULT,
    "reasoning_model": MODEL_COMPLEX_REASONING,
    "reflection_thinking_budget": REFLECTION_THINKING_BUDGET,
    "embedding_model": EMBEDDING_MODEL,
    "memory_backend": MEMORY_BACKEND,
    "memory_path": str(MEMORY_PATH),
    "corpus_path": str(CORPUS_PATH),
    "index_path": str(INDEX_PATH),
    "max_rag_results": RAG_TOP_K,
    "market_api_url": MARKET_API_URL,
    "market_scenarios": list(MARKET_SCENARIOS),
    "market_assets": list(MARKET_ASSETS),
    "require_auth": REQUIRE_AUTH,
    "enable_reflection": ENABLE_REFLECTION,
    "prioritize_clarity": PRIORITIZE_CLARITY,
}
