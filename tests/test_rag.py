"""Tests for corpus ingestion and retrieval.

Most run offline against a synthetic index: they exercise chunking, frontmatter
parsing, cosine similarity and source diversification without spending
embedding quota or needing network.

The tests that hit the real index are marked ``live`` and skip automatically
when the index or credentials are absent, so a fresh clone still gets a green
suite before running the corpus pipeline.
"""

from __future__ import annotations

import json

import pytest

from collaborative_partner import steering
from collaborative_partner.rag.ingest import (
    MIN_CHUNK_CHARS,
    build_chunks,
    is_boilerplate,
    parse_frontmatter,
    split_sections,
)
from collaborative_partner.rag.retriever import cosine, search

# ── frontmatter and chunking (offline) ─────────────────────────────────────


def test_frontmatter_is_parsed_and_stripped():
    raw = '---\ntitle: "T"\nsource_org: "SEC"\nlang: en\n---\n\n## H\n\nbody text'
    meta, body = parse_frontmatter(raw)
    assert meta["source_org"] == "SEC"
    assert meta["lang"] == "en"
    assert body.startswith("## H")


def test_document_without_frontmatter_is_handled():
    meta, body = parse_frontmatter("just text")
    assert meta == {} and body == "just text"


def test_sections_split_on_headings():
    sections = split_sections("## One\n\nalpha\n\n## Two\n\nbeta")
    headings = [h for h, _ in sections]
    assert "One" in headings and "Two" in headings


def test_long_sections_are_broken_up():
    body = "## Big\n\n" + "\n\n".join(["word " * 120] * 8)
    sections = split_sections(body)
    assert len(sections) > 1, "a wall of text must not become one chunk"
    assert all(len(text) <= 2400 for _, text in sections)


def test_boilerplate_is_detected():
    assert is_boilerplate("Skip to main content and other nav")
    assert is_boilerplate("The .gov means it is official")
    assert not is_boilerplate("Diversification reduces portfolio risk.")


# ── the real corpus (offline: reads files, does not embed) ─────────────────


@pytest.mark.skipif(not steering.CORPUS_PATH.exists(), reason="corpus not fetched")
class TestCorpusFiles:
    def test_corpus_produces_chunks(self):
        assert len(build_chunks()) > 50

    def test_every_chunk_carries_its_provenance(self):
        """A passage with no source cannot be cited, which defeats the point."""
        for chunk in build_chunks():
            assert chunk.source_org and chunk.source_org != "unknown", chunk.chunk_id
            assert chunk.source_url.startswith("http"), chunk.chunk_id
            assert chunk.license != "unknown", chunk.chunk_id

    def test_no_chunk_is_boilerplate_or_tiny(self):
        for chunk in build_chunks():
            assert len(chunk.text) >= MIN_CHUNK_CHARS
            assert not is_boilerplate(chunk.text)

    def test_both_institutions_and_both_languages_are_present(self):
        chunks = build_chunks()
        orgs = " ".join(c.source_org for c in chunks)
        assert "Securities and Exchange Commission" in orgs
        assert "Comisión Nacional del Mercado de Valores" in orgs
        assert {c.lang for c in chunks} >= {"en", "es"}

    def test_tier_b_notes_are_summaries_not_copied_prose(self):
        """Cite-only notes must be our words, flagged as such."""
        tier_b = [c for c in build_chunks() if c.tier == "B"]
        assert tier_b, "the cite-only notes should be indexed"
        for chunk in tier_b:
            assert chunk.license == "cite-only-summary"

    def test_both_sides_of_the_behaviour_gap_debate_are_indexed(self):
        """The agent must be able to argue, not recite."""
        slugs = {c.source_slug for c in build_chunks()}
        assert "behaviour-gap-morningstar" in slugs
        assert "behaviour-gap-rebuttal" in slugs


# ── similarity and diversification (offline, synthetic index) ──────────────


def test_cosine_basics():
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([0, 0], [1, 0]) == 0.0, "a zero vector must not blow up"


@pytest.fixture
def fake_index(tmp_path, monkeypatch):
    """An index where one document would otherwise monopolise the results."""
    chunks = []
    for i in range(5):
        chunks.append({
            "chunk_id": f"hog#{i}", "text": f"hog {i}", "heading": f"H{i}",
            "source_slug": "hog", "source_org": "Hog Corp", "source_url": "http://x",
            "license": "l", "lang": "en", "tier": "A", "embedding": [1.0, 0.01 * i],
        })
    for i in range(3):
        chunks.append({
            "chunk_id": f"other{i}#0", "text": f"other {i}", "heading": "H",
            "source_slug": f"other{i}", "source_org": f"Org {i}", "source_url": "http://y",
            "license": "l", "lang": "es", "tier": "B", "embedding": [0.9, 0.1],
        })
    path = tmp_path / "index.json"
    path.write_text(json.dumps({"model": "m", "dimensions": 2, "chunks": chunks}))
    monkeypatch.setattr(
        "collaborative_partner.rag.retriever.embed_query", lambda _t: [1.0, 0.0]
    )
    return path


def test_results_are_diversified_across_sources(fake_index):
    results = search("q", top_k=3, index_path=fake_index)
    slugs = [r.source_slug for r in results]
    assert len(set(slugs)) == 3, f"one document monopolised the results: {slugs}"


def test_max_per_source_can_be_relaxed(fake_index):
    results = search("q", top_k=3, index_path=fake_index, max_per_source=3)
    assert [r.source_slug for r in results] == ["hog", "hog", "hog"]


def test_results_are_ordered_by_score(fake_index):
    scores = [r.score for r in search("q", top_k=3, index_path=fake_index)]
    assert scores == sorted(scores, reverse=True)


def test_missing_index_gives_an_actionable_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="fetch_corpus"):
        search("q", index_path=tmp_path / "nope.json")


# ── live retrieval (needs the built index and credentials) ─────────────────


@pytest.mark.skipif(not steering.INDEX_PATH.exists(), reason="index not built")
class TestLiveRetrieval:
    def test_spanish_panic_query_finds_the_right_theory(self):
        """Ana's moment: the agent must reach the behavioural literature."""
        results = search("El mercado cayó 40% y quiero vender todo ahora mismo", top_k=3)
        slugs = {r.source_slug for r in results}
        assert slugs & {"disposition-effect-odean", "panic-selling-framing",
                        "dont-panic-plan-it", "loss-aversion-prospect-theory"}

    def test_spanish_concentration_query_finds_the_dca_evidence(self):
        """Beto's moment: dosing must be grounded in the Vanguard finding."""
        results = search("Quiero meter todo mi dinero en la acción que más sube", top_k=3)
        assert "dca-vs-lump-sum" in {r.source_slug for r in results}

    def test_declared_profile_query_reaches_the_regulator(self):
        """The declared layer should be grounded in CNMV, who defines it."""
        results = search("¿qué es un perfil de riesgo moderado?", top_k=3)
        assert any("Comisión Nacional" in r.source_org for r in results)

    def test_cross_lingual_retrieval_works(self):
        """A Spanish query must be able to reach the English SEC corpus.

        This was an unverified assumption in the design: the corpus mixes
        English and Spanish while the agent speaks Spanish.
        """
        results = search("¿el oro protege cuando la bolsa cae?", top_k=3)
        assert any(r.lang == "en" for r in results), (
            "no English source surfaced for a Spanish query — cross-lingual "
            "retrieval regressed; fall back to indexing a Spanish summary "
            "alongside each English chunk"
        )

    def test_every_result_can_be_cited(self):
        for r in search("diversificación de cartera", top_k=3):
            assert r.citation() and r.source_url.startswith("http")
