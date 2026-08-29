# Investment Copilot — Design Document

> **Track:** The Collaborative Partner — All Things Agentic Hackathon (Google Cloud)
> **Deadline:** August 31, 2026
> **Package:** `collaborative_partner/` (ADK, Gemini Flash by default)
> **Working name:** *Investment Copilot* (changeable)
>
> **How to use this doc:** This is the shared source of truth for the whole team. Each build phase (Section 11) maps to a repo area one person can own. To start work, take your phase, read the relevant sections here, and turn them into a Claude Code prompt (see Section 14 for the prompt template).

---

## 1. Product thesis

A conversational investment copilot that **does not trade for the user** — it advises, and above all **learns how the user actually decides under market stress**.

The differentiator is not recommending stocks. It is detecting and using the **gap between the profile the user declares and the profile their behavior reveals**. A user who calls themselves "moderate" but panics on every dip is not moderate — and the agent learns this, records it, and in future sessions confronts them with their own pattern before they self-sabotage.

**One-line pitch:** *the agent learns your investing psychology by observing you, and reflects it back so you don't betray yourself.*

---

## 2. Why this fits the challenge

The track requires three things, and all three appear as **separate, visible systems**:

| Track requirement | How we meet it |
|---|---|
| **Persistent memory across sessions** | User profile with two layers: *declared* (onboarding) and *observed* (learned). Updated in a reflection step at the end of every session. |
| **RAG over an external corpus** | Stable investment knowledge base (diversification, drawdown, dollar-cost averaging, asset allocation). The advisor's "textbook." Identical for all users. |
| **Adaptive personalization** | The agent changes its advice across sessions based on learned behavior, not declared profile. |

**The right kind of autonomy:** the agent is autonomous in *process* (fetches market data, cross-references theory, projects, synthesizes, decides what to warn about) but **not** in *execution* (it never trades; the user makes the final call). Human-in-the-loop on money decisions is not weak autonomy — it is responsible design, and it matches the axis the challenge rewards.

---

## 3. Three-system architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT (ADK + Gemini Flash)                │
│                  collaborative_partner/agent.py             │
│                                                             │
│   loop: onboarding → query market → cross-ref theory        │
│         → project → advise → reflect → persist memory        │
└───────────┬─────────────────┬──────────────────┬───────────┘
            │                 │                  │
      ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼───────┐
      │  MEMORY    │    │     RAG     │    │  MARKET API   │
      │  (user)    │    │  (theory)   │    │ (environment) │
      │            │    │             │    │               │
      │ declared   │    │ corpus md   │    │ FastAPI on    │
      │ + observed │    │ + retriever │    │ Cloud Run     │
      │ + history  │    │             │    │ (simulated,   │
      │            │    │             │    │  deterministic)│
      │ JSON/      │    │ vector      │    │               │
      │ Firestore  │    │ store       │    │ 3 scenarios   │
      └────────────┘    └─────────────┘    └───────────────┘
```

**Key point for the demo:** all three are visible and auditable. Judges can watch the memory file change, see which theory chunk was retrieved, and see the simulator respond to different scenarios. Nothing is a black box.

---

## 4. Market Simulator API (separate service)

An independent microservice that simulates market data. Deployed on **Cloud Run**; the agent consumes it over HTTP with an API key. It lives in its own folder with its own Dockerfile.

### 4.1 Why a separate API and not a local function

- Demonstrates real systems architecture: the agent is an HTTP client, not a monolith.
- Impresses a Google Cloud jury (deployed service, with auth, scale-to-zero).
- Decoupled: the simulator can evolve without touching the agent.
- Narrative value: *"we can stress-test the agent against any market condition"* — the simulator is a feature, not a patch.

### 4.2 Price generation model

**Pre-generated with a fixed seed** at service startup. Deterministic: the same call always returns the same result. Zero surprises live.

Method: **Geometric Brownian Motion** for the market index; individual assets are derived from the market via a beta + idiosyncratic noise (this produces a realistic correlation structure without building a financial engine).

```
# Market index (GBM)
S[t+1] = S[t] * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z[t])
        with Z[t] ~ N(0,1), fixed seed per scenario

# Individual asset i
r_asset[i][t] = beta[i] * r_market[t] + epsilon[i][t]
        with epsilon ~ N(0, sigma_idio[i])
```

### 4.3 Asset universe

| Ticker | Type | Beta | Narrative role |
|---|---|---|---|
| `MARKET` | Index | 1.0 | The "market" that rises/falls. The reference. |
| `TECHX` | Volatile tech | 1.6 | High beta. Amplifies everything. The "exciting" one. |
| `UTILCO` | Defensive utility | 0.5 | Low beta. Stable. The "boring but safe" one. |
| `GOLDF` | Safe haven | -0.2 | Negative correlation. Rises when everything falls. |

Four assets are enough to discuss diversification, drawdown, and correlation without bloating the demo.

### 4.4 Scenarios

| Scenario | drift (mu) | vol (sigma) | Description |
|---|---|---|---|
| `bull` | +high | low | Steady bull market. The opener. |
| `crash` | −strong | high | Sharp drop. The demo climax. |
| `recovery` | +strong | medium-high | Rebound after the crash. Hopeful close. |

Each scenario generates ~90-day (3-month) series for the 4 assets.

### 4.5 Endpoints

```
GET  /health
     → {"status": "ok"}

GET  /scenarios
     → ["bull", "crash", "recovery"]

GET  /assets
     → [{"ticker": "MARKET", "type": "index", ...}, ...]

GET  /series/{ticker}?scenario=crash
     → {"ticker": "TECHX", "scenario": "crash",
        "series": [{"day": 0, "price": 100.0}, {"day": 1, ...}]}

GET  /price/{ticker}?scenario=crash&day=15
     → {"ticker": "TECHX", "day": 15, "price": 78.42}

GET  /snapshot?scenario=crash&day=15
     → {"scenario": "crash", "day": 15,
        "prices": {"MARKET": 82.1, "TECHX": 78.4, "UTILCO": 94.3, "GOLDF": 108.7}}
```

**Auth:** `X-API-Key` header. Rejects requests without a valid key (403). The key lives in the agent's env var.

### 4.6 Deploy

- `market_api/Dockerfile` — slim Python image + uvicorn.
- Cloud Run with `--min-instances=0` (scale-to-zero, zero idle cost) and a `--max-instances` ceiling.
- `market_api/deploy.sh` — build + push + deploy.
- Local dev: `uvicorn market_api.main:app --reload`.

---

## 5. The two personas (seeded memory)

The demo compares two users with profiles that are **opposite in what they declare but revealing in what they do**. They are seeded into memory before recording (seed data). This is honest: systems with history are demonstrated with prior history + one incremental live update.

### Ana — "the false moderate"

```
declared:
  risk_tolerance: "moderate"
  horizon: "10 years"
  goals: ["buy a house", "retirement"]

observed (learned in prior sessions):
  pattern: "acute aversion to short-term losses"
  evidence:
    - "session 2 (bull→dip): asked to sell on a 5% drop"
    - "session 4 (volatility): anxiety, wanted to move everything to cash"
  gap: "declares moderate but acts conservative under stress"
  agent_note: "confront with her horizon before she panic-sells"
```

### Beto — "the false aggressive"

```
declared:
  risk_tolerance: "aggressive"
  horizon: "5 years"
  goals: ["maximize returns"]

observed (learned in prior sessions):
  pattern: "chases upside thrill, low real tolerance for drawdown"
  evidence:
    - "session 1 (bull): wanted to concentrate everything in TECHX"
    - "session 3 (mild dip): anxious messages demanding explanations"
  gap: "declares aggressive but red numbers destabilize him more than he admits"
  agent_note: "curb the FOMO, dose it out, don't allow over-concentration"
```

### The winning moment

When the **same `crash` scenario** hits both, the agent **does not apply the declared-profile rule**. It applies what it learned:

- **To Ana:** *"I know you want to sell right now — it's what you did in sessions 2 and 4. Before you touch anything: your horizon is 10 years. This drop is noise at that scale. Let's talk about why you got in."*
- **To Beto:** *"You're going to want to average down and pile more into TECHX. Your declared profile would allow it, but I've noticed dips make you more anxious than you admit. Let's do this in pieces, not all at once."*

Same market. Opposite advice. Anchored in the learned pattern, not the form. **That is the Collaborative Partner.**

---

## 6. Memory schema

`collaborative_partner/memory/schema.py`

```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class ObservedPattern(BaseModel):
    pattern: str                   # behavior description
    evidence: list[str]            # sessions that support it
    confidence: float              # 0-1, rises with each reinforcement

class UserProfile(BaseModel):
    user_id: str
    # declared layer (onboarding)
    declared_tolerance: Literal["conservative", "moderate", "aggressive"]
    horizon_years: int
    goals: list[str]
    # observed layer (learned)
    observed_patterns: list[ObservedPattern]
    declared_observed_gap: str | None    # the central insight
    agent_strategy_note: str | None      # how to treat this user
    # history
    sessions_count: int
    corrections_received: list[str]      # when the user corrects the agent
    last_updated: datetime
```

**Reflection step (session close):** the agent evaluates the session, detects behavior that reinforces or contradicts a pattern, and updates `observed_patterns` (raises `confidence`) or creates a new one. It rewrites `declared_observed_gap` and `agent_strategy_note`. This is what makes memory *learn* rather than just *recall*.

**Store:** local JSON (`data/memory/{user_id}.json`) for the MVP; Firestore for prod. `store.py` abstracts which one.

---

## 7. RAG — theory corpus

`data/corpus/` — stable investment knowledge, identical for all users. Minimum 8-12 chunks:

- `diversification.md` — why not to concentrate, correlation between assets.
- `drawdown_and_volatility.md` — what a normal drop looks like, when it's noise.
- `time_horizon.md` — how horizon changes tolerable risk.
- `dollar_cost_averaging.md` — averaging over time, averaging down.
- `investor_biases.md` — loss aversion, FOMO, panic. **(key: the agent cites this when confronting Ana/Beto)**
- `asset_allocation.md` — profiles and typical mixes.
- `safe_haven_assets.md` — what something like GOLDF does in a crash.

**Retriever:** simple search (embeddings + similarity) for the MVP; Vertex AI Search for prod. The demo must show *which chunk was retrieved* to justify the advice (RAG made visible).

---

## 8. Agent and orchestration

`collaborative_partner/agent.py`

Per-turn loop:

1. **Load memory** for the user (`memory_tool`).
2. **Query market** via the Market API (`market_tool` → HTTP to Cloud Run).
3. **Retrieve theory** relevant to the context (`rag_tool`).
4. **Analyze:** cross user position + market state + observed pattern.
5. **Project** impact (uses the API's series).
6. **Advise:** recommendation anchored in the learned pattern, citing theory.
7. **Reflect and persist:** update the observed profile (`memory_tool` write).

**Models:** Gemini Flash for the loop. Gemini Pro **only** for the complex final reflection step (synthesizing the learning), and justified.

`collaborative_partner/prompts.py`:
- System prompt: copilot role (advises, does not trade), tone, use of the two profile layers.
- Guardrails: educational framing, structural disclaimer ("not regulated financial advice"), never "buy X" but "here's what your pattern suggests you consider."
- Few-shot of the confrontation moment (declared vs observed).

---

## 9. Repo structure

```
Hackaton-Agentic/
├── collaborative_partner/          # ADK agent (already exists)
│   ├── __init__.py                 # exposes root_agent
│   ├── agent.py                    # ← loop orchestration
│   ├── prompts.py                  # ← system + guardrails + few-shot
│   ├── steering.py                 # ← team hooks
│   ├── memory/
│   │   ├── schema.py               # ← UserProfile (declared + observed)
│   │   └── store.py                # local JSON / Firestore
│   ├── rag/
│   │   ├── ingest.py               # chunking + indexing
│   │   └── retriever.py            # search
│   └── tools/
│       ├── market_tool.py          # ← HTTP client for the Market API
│       ├── rag_tool.py             # theory retrieval
│       ├── memory_tool.py          # read/write profile
│       └── projector.py            # ← impact projection
│
├── market_api/                     # ← SEPARATE SERVICE
│   ├── main.py                     # FastAPI app
│   ├── simulator.py                # GBM + pre-seed generation
│   ├── scenarios.py                # bull/crash/recovery params
│   ├── auth.py                     # API key
│   ├── Dockerfile
│   ├── deploy.sh                   # deploy to Cloud Run
│   └── requirements.txt
│
├── data/
│   ├── corpus/                     # ← investment theory (RAG)
│   │   ├── diversification.md
│   │   ├── investor_biases.md
│   │   └── ...
│   └── memory/                     # ← seeded profiles
│       ├── ana.json
│       └── beto.json
│
├── scripts/
│   ├── ingest_corpus.py            # indexes data/corpus/
│   ├── seed_memory.py              # ← seeds ana.json and beto.json
│   └── smoke_test_api.py           # ← verifies the Market API
│
├── deploy/
│   ├── Dockerfile                  # agent image (Cloud Run)
│   └── deploy_cloud_run.sh
│
├── docs/
│   ├── demo_script.md              # ← video script
│   └── architecture.md             # this design, condensed
│
├── tests/
│   ├── test_simulator.py           # ← GBM determinism
│   ├── test_market_api.py          # ← endpoints
│   ├── test_memory_schema.py       # ← profile + reflection
│   └── test_agent.py
│
├── cli.py                          # ← interface: run / demo / seed / ingest
├── .env.example                    # API keys, Market API URL
├── pyproject.toml
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

## 10. Demo script (video, 3-5 min)

| # | Time | Scene |
|---|---|---|
| 1 | 0:30 | **Setup.** "An investment copilot that doesn't trade for you — it advises and learns how you decide. And we can stress-test it against any market." Show the scenario dial of the Market API (bull/crash/recovery). |
| 2 | 0:45 | **The two profiles.** Open `ana.json` and `beto.json`. Contrast *declared* vs *observed*. The jury sees the gap in writing. |
| 3 | 1:30 | **The crash, side by side.** Fire the same `crash` scenario for both. Two panels. Same market, opposite advice, each citing the learned pattern + a theory chunk (RAG visible). **Climax.** |
| 4 | 0:45 | **Live learning.** Ana asks to sell again. The agent records it; show `ana.json` updating (pattern confidence rises). "Next time it'll know even better how to talk to her." |
| 5 | 0:30 | **Close.** Recap the three systems: Memory (learned each user), RAG (grounded the advice), Market API (the controllable environment). Educational disclaimer. |

**Golden rules for the video:**
- Market API deterministic with seed → zero surprises.
- Seeded memory + one incremental live update (step 4). Honest and sufficient.
- Always educational framing. Never "buy this."

---

## 11. Build phases (ownership map)

**Suggested order** (enables parallel work by folder — one owner per phase):

### Phase 0 — Base
- [ ] `steering.py` with team hooks (source of truth).
- [ ] `.env.example` (GEMINI_API_KEY, MARKET_API_URL, MARKET_API_KEY).
- [ ] Update `pyproject.toml` / `requirements.txt`.

### Phase 1 — Market API (unblocks everything else)
- [ ] `market_api/scenarios.py` — params for the 3 scenarios.
- [ ] `market_api/simulator.py` — pre-generated GBM, deterministic.
- [ ] `market_api/main.py` — endpoints + auth.
- [ ] `tests/test_simulator.py` — verify determinism.
- [ ] `market_api/Dockerfile` + `deploy.sh` → deploy to Cloud Run.
- [ ] `scripts/smoke_test_api.py`.

### Phase 2 — Memory
- [ ] `memory/schema.py` — `UserProfile` with two layers.
- [ ] `memory/store.py` — local JSON.
- [ ] `scripts/seed_memory.py` → generate `ana.json` and `beto.json`.
- [ ] `tests/test_memory_schema.py`.

### Phase 3 — RAG
- [ ] Write the corpus (`data/corpus/*.md`), minimum 8 chunks.
- [ ] `rag/ingest.py` + `rag/retriever.py`.
- [ ] `scripts/ingest_corpus.py`.

### Phase 4 — Tools + Agent
- [ ] `tools/market_tool.py` (HTTP client).
- [ ] `tools/memory_tool.py`, `tools/rag_tool.py`, `tools/projector.py`.
- [ ] `agent.py` — loop orchestration.
- [ ] `prompts.py` — system + guardrails + few-shot of the key moment.

### Phase 5 — CLI + Demo
- [ ] `cli.py` — `run` / `demo` / `seed` / `ingest`.
- [ ] `demo` command that runs the Ana-vs-Beto case end-to-end.
- [ ] `docs/demo_script.md`.

### Phase 6 — Polish
- [ ] Integration tests.
- [ ] README with setup + how to interact.
- [ ] Deploy the agent to Cloud Run.

**Dependency note:** Phase 1 (Market API) unblocks the most, so start it first and in parallel. But it also carries the most GCP setup (deploy, auth, IAM). **Confirm someone on the team has Cloud Run access on day 1**, before coding — not during.

---

## 12. Cost & compliance conventions

**Cost (from the hackathon rules):**
- Gemini Flash by default; Pro only for final reflection, justified.
- Cloud Run with `min-instances=0` (both agent and Market API).
- Serverless RAG, no always-on clusters.
- Prune long memories; store only the essential.
- Endpoints protected with an API key.

**Compliance (critical in a financial domain):**
- **Structural** disclaimer, not decorative: the agent frames everything as educational.
- Never "buy/sell X." Always "your pattern suggests you consider…".
- The user makes every execution decision. The agent never trades.
- Market data is explicitly simulated; stated in the demo.

---

## 13. Steering hooks (for the team)

`collaborative_partner/steering.py`

```python
STEERING_HOOKS = {
    "project_name": "InvestmentCopilot",
    "preferred_model": "gemini-2.0-flash",
    "reasoning_model": "gemini-2.0-pro",   # final reflection only
    "prioritize_clarity": True,            # ask for clarification, don't assume
    "enable_reflection": True,             # update observed profile on close
    "memory_backend": "json",              # "json" (MVP) | "firestore" (prod)
    "memory_path": "data/memory/",
    "rag_backend": "simple",               # "simple" (MVP) | "vertex" (prod)
    "corpus_path": "data/corpus/",
    "max_rag_results": 3,
    "market_api_url": None,                # read from env; None = localhost
    "market_scenarios": ["bull", "crash", "recovery"],
    "market_assets": ["MARKET", "TECHX", "UTILCO", "GOLDF"],
    "require_auth": True,
}
```

---

## 14. How to turn a phase into a Claude Code prompt

Every team member works in a separate Claude Code session. To keep the codebase coherent, derive your prompt from **this doc**, not from memory. Use this template:

```
CONTEXT (paste every time):
- Project: Investment Copilot — Collaborative Partner track, All Things Agentic Hackathon (Google Cloud). Deadline Aug 31 2026.
- Stack: Python 3.11+, google-adk, Gemini Flash default. Market data via a separate FastAPI service on Cloud Run.
- Differentiator: the agent learns the gap between the user's DECLARED risk profile and their OBSERVED behavior, and adapts advice across sessions.
- Three separate systems: MEMORY (user, two layers) / RAG (investment theory) / MARKET API (simulated environment).
- Read DESIGN_investment_partner.md and CLAUDE.md before writing code. Respect steering.py as the source of truth.

MY PHASE: [e.g. "Phase 1 — Market API"]

DELIVERABLES (from the design doc, Section [X]):
- [copy the checklist items for your phase]

CONSTRAINTS:
- Modular: my area must not break others' (memory/rag/tools/market_api are independent).
- Every tool/module gets tests.
- No hardcoded API keys.
- Deterministic where the doc says deterministic (Market API seed).
- Files ideally < ~80 lines, docstrings, idiomatic Python.

ACCEPTANCE:
- [copy the relevant acceptance criteria]
```

**Team rules:**
1. Before any significant design change, update `steering.py` first, then tell the team.
2. One branch per phase: `feat/market-api`, `feat/memory-schema`, `feat/rag`, etc.
3. Code review checklist: respects steering hooks? new tool has tests? changed `schema.py` → migration in `store.py`?

---

## Locked decisions

| Topic | Decision |
|---|---|
| Learning axis | Declared vs observed gap |
| Market API | Separate service on GCP (Cloud Run) |
| Price generation | Pre-generated, fixed seed, deterministic |
| Assets | MARKET (index) + TECHX + UTILCO + GOLDF |
| Scenarios | bull, crash, recovery |
| Personas | Ana (false moderate) + Beto (false aggressive), seeded |
| Demo | Video 3-5 min, side-by-side comparison during the crash |

---

## Open questions (resolve before coding)

1. **Product name** — "Investment Copilot" is a placeholder. Final one?
2. **Cloud Run vs Cloud Function** for the Market API — Cloud Run recommended (more control, Dockerfile, scaling). Agreed?
3. **RAG vector store** — for the MVP, does simple in-memory search suffice, or start with Vertex AI Search?
4. **Agent language** — does it respond in Spanish (LATAM market) or bilingual?