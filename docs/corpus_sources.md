# RAG Corpus — Sources, Licensing, and Ingestion Plan

> **Why this document exists.** The RAG corpus must be *external knowledge*, not text we wrote
> ourselves. A hand-authored `diversification.md` is the prompt in disguise — it proves nothing about
> retrieval, and a technical jury will read it that way. Every chunk in `data/corpus/` therefore
> traces to a named, verifiable institution, and every source below was checked live on
> **2026-08-29** (HTTP status shown).
>
> This also answers a judging criterion head-on: *"Did the team ingest unusual, messy, or highly
> complex unstructured data streams?"* — we ingest live government HTML and Spanish regulator PDFs,
> not markdown we typed.

---

## 1. Licensing model (two tiers)

The contest rules (§6, *Intellectual Property* / *Third-Party Integrations*) require that we hold the
rights to everything we redistribute in a public repository. So the corpus is split:

| Tier | What we store | Legal basis |
|---|---|---|
| **A — verbatim** | The source's actual text, converted to Markdown, committed to `data/corpus/`. | Public domain (17 U.S.C. §105) or an explicit open licence. |
| **B — cite-only** | *Our own* short structured note stating the finding, plus full citation and URL. **No source prose is copied.** | Facts and findings are not copyrightable; attribution-only summary. |

Every corpus file carries YAML frontmatter, so the licence travels with the chunk and the demo can
display a real institution name instead of a filename:

```yaml
---
title: "Beginners' Guide to Asset Allocation, Diversification, and Rebalancing"
source_org: "U.S. Securities and Exchange Commission — Office of Investor Education and Advocacy"
source_url: "https://www.investor.gov/additional-resources/general-resources/publications-research/info-sheets/beginners-guide-asset"
license: "public-domain-us-gov"
tier: A
lang: en
retrieved: 2026-08-29
---
```

---

## 2. Tier A — public domain / open licence (ingested verbatim)

### 2.1 U.S. SEC — Investor.gov · `public-domain-us-gov`

Works of U.S. federal employees created in the course of their official duties carry **no copyright**
(17 U.S.C. §105) and may be reproduced freely. This is the backbone of the corpus.

| # | Document | Status | Feeds which agent behaviour |
|---|---|---|---|
| 1 | [Beginners' Guide to Asset Allocation, Diversification, and Rebalancing](https://www.investor.gov/additional-resources/general-resources/publications-research/info-sheets/beginners-guide-asset) | 200 | Core theory: allocation, diversification, rebalancing |
| 2 | [Don't Panic, Plan It! (Director's Take)](https://www.investor.gov/additional-resources/spotlight/formerdirectorlorischock-directors-take/dont-panic-plan-it) | 200 | **Confronting Ana.** Official "don't sell into a downturn" guidance |
| 3 | [Investor Alert: Thinking About Investing in the Latest Hot Stock?](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/investor-alert-thinking-about-investing-latest-hot-stock-understand-significant-risks-short-term) | 200 | **Confronting Beto.** FOMO, concentration, short-term trading risk |
| 4 | [Asset Allocation and Diversification](https://www.investor.gov/introduction-investing/getting-started/asset-allocation) | 200 | Allocation by horizon and tolerance |
| 5 | [What is Risk?](https://www.investor.gov/introduction-investing/investing-basics/what-risk) | 200 | Risk/return; risk capacity vs. tolerance |
| 6 | [Dollar Cost Averaging (glossary)](https://www.investor.gov/introduction-investing/investing-basics/glossary/dollar-cost-averaging) | 200 | Definition of DCA |
| 7 | [Diversification (glossary)](https://www.investor.gov/introduction-investing/investing-basics/glossary/diversification) | 200 | Definition of diversification |
| 8 | [Información en Español](https://www.investor.gov/informacion-en-espanol) | 200 | Spanish-language regulator vocabulary |

> `sec.gov` itself returns **403** to scripted clients (bot protection). `investor.gov` mirrors the
> same Office of Investor Education content and responds 200 — **fetch from investor.gov.**

### 2.2 Spain — CNMV (Comisión Nacional del Mercado de Valores) · `psi-reuse-attribution`

Spanish public sector information is reusable under **Ley 37/2007** and **RD 1495/2011**, on three
conditions: do not distort the meaning, cite the source, and state the last-update date. Our
frontmatter satisfies all three.

These matter disproportionately because **the agent speaks Spanish** — it can cite a Spanish-language
regulator directly instead of translating on the fly.

| # | Document | Status | Feeds which agent behaviour |
|---|---|---|---|
| 9 | [Guía rápida: Conozca su perfil como inversor](https://www.cnmv.es/DocPortal/Publicaciones/Fichas/GR12_Perfil_Inversor.pdf) | 200 · PDF | **The keystone.** The official *declared* risk-profile questionnaire — literally the "declared" half of our thesis |
| 10 | [Los fondos de inversión y la inversión colectiva](https://www.cnmv.es/DocPortal/Publicaciones/Guias/Los_fondos_de_inversion.pdf) | 200 · PDF | Risk profile ↔ product fit; capacity to absorb losses |
| 11 | [El mercado de valores y los productos de inversión (manual)](https://www.cnmv.es/DocPortal/Publicaciones/Guias/ManualUniversitarios.pdf) | 200 · PDF | Volatility, correlation, market mechanics in Spanish |

**Why #9 is the keystone:** CNMV's guide *is* the instrument that produces a declared profile
("moderado"). The agent can quote the regulator's own definition of *moderado* and then show that
Ana's observed behaviour does not match it. The confrontation stops being the agent's opinion and
becomes a documented mismatch against an official standard.

---

## 3. Tier B — cite-only (structured notes, no copied prose)

These give the project its intellectual weight. We store a short note per finding — our words, their
citation.

| # | Source | Finding we encode | Feeds |
|---|---|---|---|
| 12 | Morningstar, *Mind the Gap 2025* — [link](https://www.morningstar.com/business/insights/research/mind-the-gap) | Fund investors earned **7.0%** vs the **8.2%** their own funds returned, 2015–2024. A **1.2 pp/yr** shortfall (~15% of gains) attributable to the *timing* of buys and sells. The gap widens with volatility (1.8% for the most volatile funds vs 0.8% for the most stable) and collapses to **0.1%** for allocation funds. | **The thesis itself.** Quantifies the behaviour gap |
| 13 | Fulkerson, Jordan, Riley & Yan, *"Bad Timing Does Not Cost Investors 15% of Their Funds' Returns"*, **Financial Analysts Journal** (2026) — [DOI](https://www.tandfonline.com/doi/full/10.1080/0015198X.2026.2657253) · [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4904652) | A direct methodological rebuttal of #12: the measured gap overstates the true cost of bad timing. | **Intellectual honesty.** The agent presents a debate, not a slogan |
| 14 | Odean, *"Are Investors Reluctant to Realize Their Losses?"*, Journal of Finance 53(5), 1998 | The **disposition effect**: investors sell winners and hold losers, driven by loss aversion. 10,000 brokerage accounts, 1987–1993. | **Ana.** Names her pattern with the seminal finding |
| 15 | Baur & Lucey, *"Is Gold a Hedge or a Safe Haven?"*, Financial Review 45(2), 2010 | Gold is a hedge on average **and** a safe haven in extreme equity declines — but the safe-haven property is **short-lived**. | Explains what `GOLDF` does in the crash, with the caveat |
| 16 | Vanguard, *Cost averaging: invest now or temporarily hold your cash?* (2023) — [PDF](https://corporate.vanguard.com/content/dam/corp/research/pdf/cost_averaging_invest_now_or_temporarily_hold_your_cash.pdf) | Lump-sum beats DCA **~2/3 of the time** (11.7% vs 10.4% annualised, US). But DCA shows lower volatility (15.2% vs 17.8%) and a smaller max drawdown (50.2% vs 55.3%). | **Beto.** Lets the agent say something true and non-obvious |
| 17 | Kahneman & Tversky, *Prospect Theory*, Econometrica 47(2), 1979 | Losses hurt roughly twice as much as equivalent gains please. | Theoretical root of loss aversion |
| 18 | *Behavioral Biases in Panic Selling: Framing during the COVID-19 Market Crisis*, **Risks** 12(10):162, MDPI 2024 — CC BY 4.0 | Framing shapes panic-selling behaviour under stress. | Justifies *how* the agent phrases the warning |

> Note on #18: MDPI journals are CC BY 4.0, so this could qualify as Tier A. The publisher returns
> 403 to scripted clients, so we treat it as cite-only rather than build a scraper for one paper.

---

## 4. What this buys us

The corpus stops being a pile of definitions and becomes **an argument with two sides**:

- #12 and #16 say behaviour costs investors real money, and that dosing reduces drawdown.
- #13 and #16 say the headline number is overstated, and that dosing costs expected return.

So when the agent tells Ana not to sell, it is not reciting a platitude — it cites the SEC's own
guidance (#2), names her bias with Odean (#14), and quantifies the cost with Morningstar (#12)
*while acknowledging the rebuttal* (#13). That is the difference between a chatbot and an advisor.

And the declared-vs-observed gap stops being our invention: **CNMV (#9) defines the declared profile;
Morningstar (#12) measures the cost of the observed one.** Our agent sits in between. That is the pitch.

---

## 5. Ingestion pipeline

`scripts/fetch_corpus.py` (new) — makes the corpus **reproducible** rather than committed-by-hand:

1. Read `data/corpus_manifest.yaml` (the tables above, as data: url, org, licence, tier, lang).
2. Tier A: fetch each URL with a browser User-Agent.
   - **HTML** (investor.gov) → strip nav/footer, convert main content to Markdown.
   - **PDF** (CNMV) → extract text with `pypdf`, normalise whitespace, drop running headers/footers.
3. Write `data/corpus/{slug}.md` with the YAML frontmatter block from §1.
4. Tier B: notes are authored once by hand in `data/corpus/notes/` — they are *our* summaries, so
   there is nothing to fetch — but they carry the same frontmatter.
5. Fail loudly on a non-200, so a dead link is caught at build time rather than during the demo.

Then `scripts/ingest_corpus.py` chunks by `##` heading, embeds with `gemini-embedding-001`, and
writes `data/index/corpus_index.json`. **Both `data/corpus/` and `data/index/` must be committed** —
the current `.gitignore` excludes them, which would strip the entire knowledge base from the judges'
clone.

New dependency: `pypdf` (for the CNMV PDFs). One extra package, and it is what earns the
"messy unstructured data" credit.

### Retrieval risk to verify, not assume

Chunks are mixed English (SEC) and Spanish (CNMV) while the agent answers in Spanish.
`gemini-embedding-001` is multilingual, so cross-language retrieval should work — but this needs a
**test**, not an assumption: a Spanish query about panic selling must retrieve the English SEC
"Don't Panic" chunk. If cross-language recall disappoints, the fallback is to embed a one-line
Spanish summary alongside each English chunk and index both.
