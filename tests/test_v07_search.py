"""Tests for v0.7 — Semantic search (FTS5), cross-source search, URL reader mode."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def search_workspace(tmp_path, monkeypatch):
    """Create a mini workspace with various file types for indexing."""
    from matylda_lite import config
    monkeypatch.setattr(config, "ROOT", tmp_path)

    # Threads
    threads = tmp_path / "library" / "threads"
    threads.mkdir(parents=True)
    (threads / "quantum_gravity.md").write_text(
        "# Quantum Gravity Research\n\n## Metadata\n- Domain: physics\n\n"
        "Loop quantum gravity proposes discretized spacetime.\n"
        "String theory offers a different approach to quantum gravity.",
        encoding="utf-8",
    )
    (threads / "machine_learning.md").write_text(
        "# Machine Learning Notes\n\n## Metadata\n- Domain: CS\n\n"
        "Transformer architectures revolutionized NLP.\n"
        "Attention mechanisms are the key innovation.",
        encoding="utf-8",
    )

    # Memory insights
    insights = tmp_path / "memory" / "insights"
    insights.mkdir(parents=True)
    (insights / "insight_1.json").write_text(json.dumps({
        "content": "Quantum gravity requires reconciling general relativity with quantum mechanics",
        "topic": "physics",
        "kind": "project_fact",
    }), encoding="utf-8")
    (insights / "insight_2.json").write_text(json.dumps({
        "content": "The transformer model uses self-attention for sequence processing",
        "topic": "machine learning",
        "kind": "procedural_lesson",
    }), encoding="utf-8")

    # Candidates
    candidates = tmp_path / "memory" / "candidates"
    candidates.mkdir(parents=True)
    (candidates / "cand_1.json").write_text(json.dumps({
        "content": "Loop quantum gravity predicts discrete area spectrum",
        "topic": "LQG",
        "kind": "project_fact",
    }), encoding="utf-8")

    # Docs
    docs_dir = tmp_path / "library" / "docs" / "attached"
    docs_dir.mkdir(parents=True)
    (docs_dir / "notes.txt").write_text(
        "Additional notes on quantum gravity experiments and measurements.",
        encoding="utf-8",
    )

    # Generated docs
    gen_dir = tmp_path / "library" / "docs" / "generated"
    gen_dir.mkdir(parents=True)
    (gen_dir / "summary.md").write_text(
        "# Summary of Quantum Research\n\nA comprehensive overview of quantum gravity approaches.",
        encoding="utf-8",
    )

    # Artifacts
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "review_paper.md").write_text(
        "# Critical Review\n\nThis paper reviews quantum gravity predictions.",
        encoding="utf-8",
    )

    # Archived thread (should NOT be indexed)
    archive = threads / "archive"
    archive.mkdir()
    (archive / "old_thread.md").write_text(
        "# Old archived thread about quantum gravity",
        encoding="utf-8",
    )

    return tmp_path


# ── search_index module tests ────────────────────────────────────────────────

class TestSearchIndex:
    def test_build_index(self, search_workspace, monkeypatch):
        # Patch ROOT in search_index too
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)

        count = si.rebuild_index()
        assert count >= 6  # threads + insights + candidate + docs + artifact

    def test_fts_search_basic(self, search_workspace, monkeypatch):
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        results = si.fts_search("quantum gravity")
        assert len(results) > 0
        # Top result should be about quantum gravity
        assert any("quantum" in r["title"].lower() or "quantum" in r["snippet"].lower()
                    for r in results)

    def test_fts_search_bm25_ranking(self, search_workspace, monkeypatch):
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        results = si.fts_search("quantum gravity")
        # Results should have scores
        for r in results:
            assert "score" in r
            assert r["score"] >= 0

        # Scores should be sorted descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        # At least one result should have a positive score
        assert any(r["score"] > 0 for r in results)

    def test_fts_search_source_filter(self, search_workspace, monkeypatch):
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        # Filter by thread only
        results = si.fts_search("quantum", source_filter="thread")
        assert all(r["type"] == "thread" for r in results)
        assert len(results) >= 1

        # Filter by insight only
        results = si.fts_search("quantum", source_filter="insight")
        assert all(r["type"] == "insight" for r in results)

    def test_fts_search_cross_source(self, search_workspace, monkeypatch):
        """Results should come from multiple source types."""
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        results = si.fts_search("quantum")
        types = {r["type"] for r in results}
        # Should find results in at least 3 different source types
        assert len(types) >= 3, f"Expected cross-source results, got types: {types}"

    def test_fts_search_no_archived(self, search_workspace, monkeypatch):
        """Archived files should not appear in search results."""
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        results = si.fts_search("old archived")
        # The archived thread should NOT be in results
        assert not any("archive" in r["path_rel"] for r in results)

    def test_fts_search_empty_query(self, search_workspace, monkeypatch):
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        results = si.fts_search("")
        assert results == []

    def test_fts_search_no_results(self, search_workspace, monkeypatch):
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        results = si.fts_search("xyznonexistent")
        assert results == []

    def test_index_stats(self, search_workspace, monkeypatch):
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        stats = si.index_stats()
        assert stats["total_documents"] >= 6
        assert "by_type" in stats
        assert stats["by_type"].get("thread", 0) >= 2
        assert stats["by_type"].get("insight", 0) >= 2

    def test_prefix_search(self, search_workspace, monkeypatch):
        """Prefix search: 'quant' should match 'quantum'."""
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        results = si.fts_search("quant")
        assert len(results) > 0

    def test_special_chars_safe(self, search_workspace, monkeypatch):
        """Special characters in query should not crash."""
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        # These should not raise
        si.fts_search("test (with) parens")
        si.fts_search('"quoted"')
        si.fts_search("a*b*c")
        si.fts_search("OR AND NOT")


# ── search_manager integration tests ────────────────────────────────────────

class TestSearchManager:
    def test_search_via_manager(self, search_workspace, monkeypatch):
        import matylda_lite.search_index as si
        monkeypatch.setattr(si, "ROOT", search_workspace)
        si.rebuild_index()

        from matylda_lite.search_manager import search
        results = search("transformer attention")
        assert len(results) > 0
        assert any("transformer" in r.get("snippet", "").lower() or
                    "transformer" in r.get("title", "").lower()
                    for r in results)


# ── HTTP endpoint tests ──────────────────────────────────────────────────────

class TestSearchAPI:
    def test_search_endpoint(self, client):
        r = client.get("/api/search?q=test")
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "query" in data

    def test_search_empty_query(self, client):
        r = client.get("/api/search?q=")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_search_stats(self, client):
        r = client.get("/api/search/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_documents" in data
        assert "by_type" in data

    def test_search_rebuild(self, client):
        r = client.post("/api/search/rebuild")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["documents_indexed"] >= 0

    def test_search_with_source_filter(self, client):
        r = client.get("/api/search?q=test&source=thread")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["results"], list)

    def test_reader_mode_requires_url(self, client):
        r = client.post("/api/fetch/reader", json={"url": ""})
        assert r.status_code == 400
        assert "error" in r.json()


# ── browser.py reader mode tests ────────────────────────────────────────────

class TestReaderMode:
    def test_extract_metadata_from_html(self):
        from matylda_lite.browser import _extract_metadata
        html = '''<html><head>
            <title>Test Article Title</title>
            <meta name="description" content="A test description">
            <meta name="author" content="John Doe">
        </head><body></body></html>'''
        meta = _extract_metadata(html)
        assert meta["title"] == "Test Article Title"
        assert meta["description"] == "A test description"
        assert meta["author"] == "John Doe"

    def test_extract_metadata_h1_overrides_title(self):
        from matylda_lite.browser import _extract_metadata
        html = '<html><head><title>Page Title</title></head><body><h1>Article Heading</h1></body></html>'
        meta = _extract_metadata(html)
        assert meta["title"] == "Article Heading"

    def test_extract_article_html_from_article_tag(self):
        from matylda_lite.browser import _extract_article_html
        html = '<html><body><nav>menu</nav><article><p>Main content here about the topic.</p></article><footer>footer</footer></body></html>'
        content = _extract_article_html(html)
        assert "Main content" in content

    def test_extract_article_html_fallback_paragraphs(self):
        from matylda_lite.browser import _extract_article_html
        html = '<html><body><p>Short nav</p><p>This is a longer paragraph about an important topic that contains enough text to be considered content.</p></body></html>'
        content = _extract_article_html(html)
        assert "important topic" in content

    def test_fetch_reader_invalid_url(self):
        from matylda_lite.browser import fetch_reader
        result = fetch_reader("http://nonexistent.invalid.domain.test/")
        assert result["ok"] is False
        assert result["error"]


# ── Dashboard HTML tests ────────────────────────────────────────────────────

class TestDashboardV07:
    @pytest.fixture(autouse=True)
    def _html(self):
        from matylda_lite.dashboard import build
        self.html = build(server_mode=True)

    def test_reader_mode_button(self):
        assert "fetchReaderMode" in self.html
        assert "📖" in self.html

    def test_search_filter_buttons(self):
        assert "search-filter-btn" in self.html
        assert "setSearchFilter" in self.html
        assert "Wszystko" in self.html

    def test_bm25_search_placeholder(self):
        assert "BM25" in self.html

    def test_source_icons_in_search(self):
        assert "sourceIcons" in self.html
        assert "sourceLabels" in self.html
