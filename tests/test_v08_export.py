"""Tests for v0.8 — Polished MD export, research bundle, share HTML."""
from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def export_workspace(tmp_path, monkeypatch):
    """Create a mini workspace for export tests."""
    from matylda_lite import config
    monkeypatch.setattr(config, "ROOT", tmp_path)

    # Patch export_manager paths
    import matylda_lite.export_manager as em
    monkeypatch.setattr(em, "ROOT", tmp_path)

    # Threads
    threads = tmp_path / "library" / "threads"
    threads.mkdir(parents=True, exist_ok=True)
    (threads / "quantum_gravity.md").write_text(
        "# Quantum Gravity Research\n\n"
        "## Metadata\n- Domain: physics\n- Status: active\n- Last Updated: 2025-01-15\n\n"
        "## Introduction\n\nLoop quantum gravity proposes discretized spacetime.\n\n"
        "## Methods\n\nString theory offers a different approach to quantum gravity.\n\n"
        "### Sub-method A\n\nSome details here.\n\n"
        "## Conclusions\n\nMore research is needed.\n",
        encoding="utf-8",
    )
    (threads / "machine_learning.md").write_text(
        "# Machine Learning Notes\n\n## Metadata\n- Domain: CS\n\n"
        "Transformer architectures revolutionized NLP.\n"
        "Attention mechanisms are the key innovation.",
        encoding="utf-8",
    )

    # Timeline
    timeline_dir = threads / "timeline"
    timeline_dir.mkdir(exist_ok=True)
    (timeline_dir / "quantum_gravity.json").write_text(json.dumps({
        "events": [
            {"type": "conversation", "description": "Initial research session", "date": "2025-01-10"},
            {"type": "artifact_created", "description": "Created review paper", "date": "2025-01-15"},
        ]
    }), encoding="utf-8")

    # Memory insights
    insights = tmp_path / "memory" / "insights"
    insights.mkdir(parents=True, exist_ok=True)
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
    # Research trace
    (insights / "trace_1.json").write_text(json.dumps({
        "trace_kind": "research_project_memory_trace",
        "project_id": "proj_qg",
        "title": "Quantum gravity session 1",
        "summary": "Explored loop quantum gravity",
    }), encoding="utf-8")

    # Candidates
    candidates = tmp_path / "memory" / "candidates"
    candidates.mkdir(parents=True, exist_ok=True)
    (candidates / "cand_1.json").write_text(json.dumps({
        "content": "Loop quantum gravity predicts discrete area spectrum",
        "topic": "quantum gravity",
        "kind": "project_fact",
    }), encoding="utf-8")

    # Artifacts
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "review_paper.md").write_text(
        "# Critical Review\n\nThis paper reviews quantum_gravity predictions.",
        encoding="utf-8",
    )
    (artifacts / "unrelated_art.md").write_text(
        "# Unrelated\n\nThis has nothing to do with quantum gravity.",
        encoding="utf-8",
    )

    # Docs
    docs_attached = tmp_path / "library" / "docs" / "attached"
    docs_attached.mkdir(parents=True, exist_ok=True)
    (docs_attached / "notes.txt").write_text(
        "Notes about quantum_gravity experiments.",
        encoding="utf-8",
    )
    docs_gen = tmp_path / "library" / "docs" / "generated"
    docs_gen.mkdir(parents=True, exist_ok=True)
    (docs_gen / "summary.md").write_text(
        "Summary of quantum_gravity approaches.",
        encoding="utf-8",
    )

    # Archive
    archive = threads / "archive"
    archive.mkdir(exist_ok=True)

    return tmp_path


# ── Polished Markdown ────────────────────────────────────────────────────────

class TestPolishedMd:
    def test_polished_md_has_frontmatter(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        md = em.export_polished_md("quantum_gravity")
        assert md.startswith("---\n")
        assert "title: Quantum Gravity Research" in md
        assert "generator: Matylda Lab v1.2" in md
        assert "---" in md[4:]  # closing frontmatter

    def test_polished_md_has_toc(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        md = em.export_polished_md("quantum_gravity")
        assert "## Spis treści" in md
        assert "[Introduction]" in md
        assert "[Methods]" in md
        assert "[Conclusions]" in md

    def test_polished_md_has_body(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        md = em.export_polished_md("quantum_gravity")
        assert "Loop quantum gravity" in md
        assert "String theory" in md

    def test_polished_md_has_footer(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        md = em.export_polished_md("quantum_gravity")
        assert "Wyeksportowano z Matylda Lab" in md

    def test_polished_md_metadata_extracted(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        md = em.export_polished_md("quantum_gravity")
        assert "domain: physics" in md
        assert "status: active" in md

    def test_polished_md_not_found(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        with pytest.raises(FileNotFoundError):
            em.export_polished_md("nonexistent_thread")


# ── Research Bundle ──────────────────────────────────────────────────────────

class TestResearchBundle:
    def test_bundle_is_valid_zip(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        assert len(data) > 0
        zf = zipfile.ZipFile(io.BytesIO(data))
        assert len(zf.namelist()) > 0

    def test_bundle_contains_thread(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        assert any("quantum_gravity.md" in n for n in names)

    def test_bundle_contains_manifest(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        manifest_name = [n for n in names if "manifest.json" in n]
        assert len(manifest_name) == 1

        manifest = json.loads(zf.read(manifest_name[0]))
        assert manifest["stem"] == "quantum_gravity"
        assert manifest["generator"] == "Matylda Lab v1.2"
        assert "contents" in manifest

    def test_bundle_contains_timeline(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        assert any("timeline.json" in n for n in names)

    def test_bundle_contains_insights(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        insight_files = [n for n in names if "/insights/" in n]
        assert len(insight_files) >= 1

    def test_bundle_contains_artifacts(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        art_files = [n for n in names if "/artifacts/" in n]
        # review_paper.md mentions quantum_gravity
        assert any("review_paper" in n for n in art_files)

    def test_bundle_contains_docs(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        doc_files = [n for n in names if "/docs/" in n]
        assert len(doc_files) >= 1

    def test_bundle_contains_candidates(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        cand_files = [n for n in names if "/candidates/" in n]
        assert len(cand_files) >= 1

    def test_bundle_thread_is_polished(self, export_workspace, monkeypatch):
        """The thread MD in the bundle should be the polished version."""
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        data = em.export_research_bundle("quantum_gravity")
        zf = zipfile.ZipFile(io.BytesIO(data))
        thread_file = [n for n in zf.namelist() if n.endswith("quantum_gravity.md")][0]
        content = zf.read(thread_file).decode("utf-8")
        # Should have frontmatter (polished version)
        assert content.startswith("---\n")
        assert "Spis treści" in content

    def test_bundle_not_found(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        with pytest.raises(FileNotFoundError):
            em.export_research_bundle("nonexistent_thread")


# ── Share HTML ───────────────────────────────────────────────────────────────

class TestShareHtml:
    def test_share_html_is_valid(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_share_html_has_title(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        assert "<title>Quantum Gravity Research</title>" in html

    def test_share_html_has_embedded_css(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        assert "<style>" in html
        assert "font-family" in html
        # Light/dark theme support
        assert "prefers-color-scheme" in html

    def test_share_html_has_content(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        assert "Loop quantum gravity" in html
        assert "String theory" in html

    def test_share_html_has_meta_badges(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        assert "physics" in html
        assert "meta-badge" in html

    def test_share_html_has_footer(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        assert "Matylda Lab v1.2" in html

    def test_share_html_not_found(self, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        with pytest.raises(FileNotFoundError):
            em.export_share_html("nonexistent_thread")

    def test_share_html_self_contained(self, export_workspace, monkeypatch):
        """No external CSS/JS — only localhost back-link allowed."""
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        # Strip the localhost return-bar link before checking for external links
        import re
        html_no_local = re.sub(r'href="http://localhost[^"]*"', '', html)
        assert 'href="http' not in html_no_local
        assert 'src="http' not in html

    def test_share_html_has_return_link(self, export_workspace, monkeypatch):
        """Share HTML has a return link to Matylda Lab."""
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)

        html = em.export_share_html("quantum_gravity")
        assert "return-bar" in html
        assert "localhost:7474" in html
        assert "Matylda Lab" in html


# ── Markdown to HTML converter ───────────────────────────────────────────────

class TestMarkdownToHtml:
    def test_headings(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("# Heading 1\n\n## Heading 2\n\n### Heading 3")
        assert "<h1" in html
        assert "<h2" in html
        assert "<h3" in html

    def test_paragraphs(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("This is a paragraph.\n\nThis is another.")
        assert "<p>" in html
        assert "This is a paragraph." in html

    def test_bold_and_italic(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("This is **bold** and *italic*.")
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_unordered_list(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("- Item A\n- Item B\n- Item C")
        assert "<ul>" in html
        assert "<li>" in html
        assert "Item A" in html

    def test_ordered_list(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("1. First\n2. Second")
        assert "<ol>" in html
        assert "<li>" in html

    def test_code_block(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("```python\nprint('hello')\n```")
        assert "<pre>" in html
        assert "<code" in html

    def test_inline_code(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("Use `code` here")
        assert "<code>code</code>" in html

    def test_blockquote(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("> A wise quote")
        assert "<blockquote>" in html
        assert "A wise quote" in html

    def test_horizontal_rule(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("Above\n\n---\n\nBelow")
        assert "<hr>" in html

    def test_link(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("Visit [Google](https://google.com)")
        assert '<a href="https://google.com">Google</a>' in html

    def test_html_escaping(self):
        from matylda_lite.export_manager import _markdown_to_html
        html = _markdown_to_html("Use <script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


# ── HTTP endpoint tests ──────────────────────────────────────────────────────

class TestExportAPI:
    def test_polished_md_endpoint(self, client):
        """Endpoint returns 400 when stem is missing."""
        r = client.get("/api/export/polished-md?stem=")
        assert r.status_code == 400

    def test_polished_md_not_found(self, client):
        r = client.get("/api/export/polished-md?stem=nonexistent_xyz")
        assert r.status_code == 404

    def test_research_bundle_endpoint(self, client):
        r = client.get("/api/export/research-bundle?stem=")
        assert r.status_code == 400

    def test_research_bundle_not_found(self, client):
        r = client.get("/api/export/research-bundle?stem=nonexistent_xyz")
        assert r.status_code == 404

    def test_share_html_endpoint(self, client):
        r = client.get("/api/export/share-html?stem=")
        assert r.status_code == 400

    def test_share_html_not_found(self, client):
        r = client.get("/api/export/share-html?stem=nonexistent_xyz")
        assert r.status_code == 404

    def test_share_html_preview_endpoint(self, client):
        r = client.get("/api/export/share-html/preview?stem=")
        assert r.status_code == 400

    def test_share_html_preview_not_found(self, client):
        r = client.get("/api/export/share-html/preview?stem=nonexistent_xyz")
        assert r.status_code == 404

    def test_polished_md_real_thread(self, client, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)
        r = client.get("/api/export/polished-md?stem=quantum_gravity")
        assert r.status_code == 200
        assert "text/markdown" in r.headers.get("content-type", "")
        assert b"---\n" in r.content

    def test_research_bundle_real_thread(self, client, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)
        r = client.get("/api/export/research-bundle?stem=quantum_gravity")
        assert r.status_code == 200
        assert "application/zip" in r.headers.get("content-type", "")
        # Verify it's a valid ZIP
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        assert len(zf.namelist()) > 0

    def test_share_html_real_thread(self, client, export_workspace, monkeypatch):
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)
        r = client.get("/api/export/share-html?stem=quantum_gravity")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert b"<!DOCTYPE html>" in r.content

    def test_share_html_preview_no_download(self, client, export_workspace, monkeypatch):
        """Preview endpoint should NOT have Content-Disposition header."""
        import matylda_lite.export_manager as em
        monkeypatch.setattr(em, "ROOT", export_workspace)
        r = client.get("/api/export/share-html/preview?stem=quantum_gravity")
        assert r.status_code == 200
        assert "Content-Disposition" not in r.headers or "attachment" not in r.headers.get("Content-Disposition", "")


# ── Dashboard HTML tests ────────────────────────────────────────────────────

class TestDashboardV08:
    @pytest.fixture(autouse=True)
    def _html(self):
        from matylda_lite.dashboard import build
        self.html = build(server_mode=True)

    def test_export_menu_present(self):
        assert "toggleExportMenu" in self.html
        assert "export-menu" in self.html

    def test_export_menu_items(self):
        assert "exportPolishedMd" in self.html
        assert "exportResearchBundle" in self.html
        assert "exportShareHtml" in self.html
        assert "previewShareHtml" in self.html

    def test_polished_md_label(self):
        assert "Polished Markdown" in self.html

    def test_research_bundle_label(self):
        assert "Research Bundle" in self.html

    def test_share_html_label(self):
        assert "Share HTML" in self.html

    def test_version_10(self):
        from matylda_lite.server import app
        assert app.version == "1.2"
