# JUSARA — architecture

> Condensed technical description. Written to be pasted, largely as-is, into the
> Devpost "text description" field.

## What it is

An investment copilot that advises but never trades, and whose real subject is
not the market but the user. It learns the gap between the risk profile a person
*declares* and the one their behaviour *reveals*, and reflects that gap back
before they act against their own interests.

**Track:** The Collaborative Partner.

## The problem

Risk questionnaires are self-reports collected once, in calm conditions, by
people guessing how they will feel about losing money. Morningstar's *Mind the
Gap 2025* measures what that costs: over 2015–2024, funds returned 8.2% annually
while their own investors earned 7.0%. That 1.2 percentage points a year — about
15% of all gains — was destroyed purely by the timing of buys and sells, and the
gap widens with volatility.

Nobody measures that gap for the individual. JUSARA does.

## Three systems, kept separate

The common failure in this track is a chatbot with retrieval, relabelled as
memory. JUSARA keeps three systems that are separate in the code, separate in
storage, and visibly separate in the UI.

| System | Holds | Storage | Made visible by |
|---|---|---|---|
| **Memory** | The user: declared layer, observed patterns with confidence, corrections, session count | Firestore (deployed) / JSON (local) | Right-hand panel; the changed pattern is highlighted |
| **RAG** | The world: investment theory | `data/index/corpus_index.json` | Every answer cites its source institution |
| **Market** | The environment: simulated prices | Separate Cloud Run service | Scenario and day controls; live prices |

### Memory — the differentiator

`UserProfile` carries two layers. The declared layer is onboarding data. The
observed layer is a list of `ObservedPattern`, each with a stable key, its
supporting evidence, and a confidence between 0.05 and 0.95.

The methods that matter are `reinforce` and `weaken`. Repeated evidence raises a
pattern's confidence; contradicting behaviour lowers it. Without the second one
the profile could only ever grow more certain, which is confirmation bias with a
JSON file rather than learning.

A **reflection step** runs at session close as a separate ADK agent with *only*
memory-writing tools — no market or theory access, so it cannot drift into
giving advice. Its single job is to decide what today revealed and rewrite the
`declared_observed_gap` and the `agent_strategy_note` that will open the next
session.

The user id is never a model-supplied parameter. It comes from the ADK session
via `ToolContext`. An earlier version passed it as an argument and the model
invented one, greeting a user with four sessions of history as a stranger.
Cross-session memory is the product; the identity it keys on cannot be a guess.

### RAG — fetched, not written

A hand-authored theory file is the prompt in disguise. The corpus is downloaded
from named institutions by `scripts/fetch_corpus.py`:

- **U.S. SEC / Investor.gov** — 7 pages, public domain under 17 U.S.C. §105.
- **CNMV (Spain)** — 3 PDFs, reusable under Ley 37/2007 with attribution.
  Including *Conozca su perfil como inversor*, the official questionnaire that
  **produces** a declared risk profile — the exact instrument this product
  interrogates.
- **7 cite-only notes** — our own summaries of Morningstar, Odean 1998,
  Kahneman & Tversky 1979, Baur & Lucey 2010, Vanguard 2023, and the 2026
  *Financial Analysts Journal* rebuttal of the behaviour-gap finding. No source
  prose is reproduced.

Because both sides of the behaviour-gap debate are indexed, the agent argues
rather than recites.

Provenance travels from each document's frontmatter into every chunk, so a
retrieved passage is cited as "U.S. SEC", never as a filename. Retrieval is
cosine similarity over a committed JSON index of 233 chunks embedded with
`gemini-embedding-001` — serverless, no vector cluster, no cold-start embedding
cost. Results are capped at one passage per source document, which both stops a
single paper monopolising the context and surfaces the English SEC material that
Spanish queries would otherwise bury.

### Market — a separate service

An independent FastAPI service on Cloud Run. The agent is an HTTP client with an
API key, exactly as it would be against a real data vendor.

Prices come from Geometric Brownian Motion for the index, with individual assets
derived through a beta plus idiosyncratic noise — a realistic correlation
structure without a financial engine. Four assets (`MARKET`, `TECHX` β1.6,
`UTILCO` β0.5, `GOLDF` β−0.2) across three scenarios (`bull`, `crash`,
`recovery`), 90 days each, generated from a fixed seed. The same call always
returns the same number.

The idiosyncratic noise is de-meaned deliberately: as a raw random walk it
accumulated enough drift over 90 days to send the high-beta asset *down* in a
bull market, which is the opposite of what beta means.

## Model choices

Everything runs on **`gemini-3.5-flash`** via Vertex AI. Two findings shaped
this, both verified live:

1. Gemini 3.5 is served **only from the `global` endpoint**. It returns 404 in
   us-central1, us-east5, europe-west4, us-west1 and asia-northeast1.
2. **No Pro-class Gemini 3.5 model exists** on Vertex. Rather than drop to 2.5
   Pro — which would violate the contest's "3.5 or newer" requirement — the
   reflection step raises the *thinking budget* on the same Flash model. The task
   needs more deliberation, not more knowledge, and it is cheaper.

The advice agent runs at temperature 0.3. Invented statistics are the failure
mode that matters in a financial context, so all portfolio arithmetic is done
deterministically in `tools/projector.py` and handed to the model as
conclusions. A model asked to compound returns over 90 days produces a confident
wrong answer.

## Google Cloud footprint

| Service | Role |
|---|---|
| **Cloud Run** ×2 | `jusara-agent` (agent + UI), `jusara-market-api` (simulator). Both `--min-instances=0` |
| **Firestore** | Persistent user profiles in the deployed environment |
| **Vertex AI** | `gemini-3.5-flash` and `gemini-embedding-001` |
| **Cloud Build / Artifact Registry** | Container builds |

Cost controls, per the hackathon's guidance: Flash everywhere, scale-to-zero
with an instance ceiling, a precomputed embeddings index instead of an always-on
vector database, and API-key protection on the simulator.

## Compliance

The guardrails are structural, in the system prompt and in the tool surface, not
decorative disclaimers:

- The agent has no tool that executes a trade. It cannot.
- It never says "buy X" or "sell X" — only "your pattern suggests you consider".
- Market data is stated as simulated.
- Framing is educational; it is not regulated financial advice.
- `selling_now_vs_holding` carries a built-in caveat so its output reads as one
  simulated path, never as a forecast.

## Testing

105 tests. The ones worth naming are the behavioural assertions rather than the
unit checks:

- The simulator's **narrative** is asserted, not just its determinism: a crash
  must crash, the high-beta asset must fall harder, the safe haven must rise. A
  retuning that breaks the demo story fails the suite instead of the recording.
- `compare_with_diversified` is tested **in both directions** — concentration
  must win in the bull run, or the comparison is propaganda rather than advice.
- Cross-lingual retrieval is verified, not assumed: a Spanish query must reach
  the English SEC corpus, and the test names the fallback if it regresses.
- The seeded personas are asserted to genuinely contradict themselves, since the
  demo is pointless otherwise.

## Repo layout

```
collaborative_partner/   agent, prompts, steering, memory/, rag/, tools/
market_api/              separate FastAPI simulator service
web/                     FastAPI app + three-panel UI
data/                    corpus (fetched), index (embedded), memory (seeded)
scripts/                 fetch_corpus · ingest_corpus · seed_memory · smoke_test
cli.py                   check · fetch-corpus · ingest · seed · run · demo
```
