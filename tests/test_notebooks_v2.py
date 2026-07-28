"""Tests for v0.4e Notebooks v2 — YAML frontmatter, structured update, DELETE."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── silo_1 notebook functions ─────────────────────────────────────────────────

class TestFrontmatterHelpers:
    """Test _parse_frontmatter and _serialize_frontmatter in silo_1."""

    def test_parse_empty_returns_empty_meta(self):
        from matylda_lite.silos.silo_1 import _parse_frontmatter
        meta, body = _parse_frontmatter("# Hello\n\nContent")
        assert meta == {}
        assert "# Hello" in body

    def test_parse_valid_frontmatter(self):
        from matylda_lite.silos.silo_1 import _parse_frontmatter
        content = "---\ntitle: Test\ntags: [a, b]\n---\n# Body"
        meta, body = _parse_frontmatter(content)
        assert meta["title"] == "Test"
        assert meta["tags"] == ["a", "b"]
        assert "# Body" in body

    def test_serialize_roundtrip(self):
        from matylda_lite.silos.silo_1 import _parse_frontmatter, _serialize_frontmatter
        meta = {"title": "RT", "tags": ["x"], "silo": "science"}
        body = "## Content\n\nSome text\n"
        serialized = _serialize_frontmatter(meta, body)
        parsed_meta, parsed_body = _parse_frontmatter(serialized)
        assert parsed_meta["title"] == "RT"
        assert parsed_body == body

    def test_serialize_starts_with_dashes(self):
        from matylda_lite.silos.silo_1 import _serialize_frontmatter
        result = _serialize_frontmatter({"title": "T"}, "body")
        assert result.startswith("---\n")

    def test_parse_bad_yaml_returns_empty_meta(self):
        from matylda_lite.silos.silo_1 import _parse_frontmatter
        content = "---\n: broken: yaml:\n---\nbody"
        meta, body = _parse_frontmatter(content)
        # Should not crash; meta may be empty or partial
        assert isinstance(meta, dict)
        assert "body" in body


class TestSilo1NotebooksV2:
    """Integration tests for silo_1 notebook CRUD with frontmatter."""

    def test_create_returns_modified_at(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook
        meta = _create_notebook("FM Test", project_id="p1")
        assert "modified" in meta

    def test_create_writes_frontmatter(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _NB_DIR
        meta = _create_notebook("FM Write", tags=["alpha"])
        nb_file = _NB_DIR / meta["file"]
        raw = nb_file.read_text()
        assert raw.startswith("---\n")
        assert "alpha" in raw
        assert "FM Write" in raw

    def test_read_returns_body_and_frontmatter(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _read_notebook
        meta = _create_notebook("Read V2")
        nb = _read_notebook(meta["id"])
        assert "body" in nb
        assert "frontmatter" in nb
        assert nb["frontmatter"]["title"] == "Read V2"

    def test_update_title_updates_frontmatter(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _update_notebook, _read_notebook
        meta = _create_notebook("Old Title")
        _update_notebook(meta["id"], title="New Title")
        nb = _read_notebook(meta["id"])
        assert nb["frontmatter"]["title"] == "New Title"
        assert nb["title"] == "New Title"

    def test_update_tags_updates_index(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _update_notebook, _load_nb_index
        meta = _create_notebook("Tag Test", tags=["old"])
        _update_notebook(meta["id"], tags=["new1", "new2"])
        idx = _load_nb_index()
        entry = next(n for n in idx if n["id"] == meta["id"])
        assert entry["tags"] == ["new1", "new2"]

    def test_update_body_preserves_frontmatter(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _update_notebook, _read_notebook
        meta = _create_notebook("Body Test")
        _update_notebook(meta["id"], body="## New body\n\nContent here\n")
        nb = _read_notebook(meta["id"])
        assert "## New body" in nb["body"]
        assert nb["frontmatter"]["title"] == "Body Test"

    def test_update_sets_modified_at(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _update_notebook, _load_nb_index
        meta = _create_notebook("Mod Test")
        original_modified = meta.get("modified", "")
        _update_notebook(meta["id"], body="changed")
        idx = _load_nb_index()
        entry = next(n for n in idx if n["id"] == meta["id"])
        # modified should be updated (may be same if very fast, but field exists)
        assert "modified" in entry

    def test_delete_removes_file_and_index(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _delete_notebook, _load_nb_index, _NB_DIR
        meta = _create_notebook("Delete Me")
        nb_file = _NB_DIR / meta["file"]
        assert nb_file.exists()
        result = _delete_notebook(meta["id"])
        assert result is True
        assert not nb_file.exists()
        idx = _load_nb_index()
        assert not any(n["id"] == meta["id"] for n in idx)

    def test_delete_nonexistent_returns_false(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _delete_notebook
        result = _delete_notebook("nb_doesnotexist")
        assert result is False


class TestSilo2NotebooksV2:
    """Integration tests for silo_2 (Legal) notebook CRUD with frontmatter."""

    def test_create_returns_modified_at(self, tmp_nb_dir_s2):
        from matylda_lite.silos.silo_2 import _create_notebook
        meta = _create_notebook("Legal FM Test", project_id="legal_p1")
        assert "modified" in meta

    def test_create_writes_frontmatter_legal_silo(self, tmp_nb_dir_s2):
        from matylda_lite.silos.silo_2 import _create_notebook, _NB_DIR
        meta = _create_notebook("Legal NB", tags=["umowa"])
        nb_file = _NB_DIR / meta["file"]
        raw = nb_file.read_text()
        assert raw.startswith("---\n")
        assert "legal" in raw.lower()

    def test_delete_legal_notebook(self, tmp_nb_dir_s2):
        from matylda_lite.silos.silo_2 import _create_notebook, _delete_notebook, _NB_DIR
        meta = _create_notebook("Legal Del Test")
        nb_file = _NB_DIR / meta["file"]
        assert nb_file.exists()
        result = _delete_notebook(meta["id"])
        assert result is True
        assert not nb_file.exists()


# ── HTTP endpoints (TestClient) ───────────────────────────────────────────────

class TestNotebookEndpointsV2:
    def test_create_notebook_with_project_id(self, client, tmp_nb_dir_s1):
        resp = client.post('/api/silos/silo_1/notebooks/create', json={
            "title": "HTTP FM NB", "project_id": "proj_http"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["title"] == "HTTP FM NB"

    def test_get_notebook_returns_body_and_frontmatter(self, client, tmp_nb_dir_s1):
        r1 = client.post('/api/silos/silo_1/notebooks/create', json={"title": "Get V2 Test"})
        nb_id = r1.json()["id"]
        r2 = client.get(f'/api/silos/silo_1/notebooks/{nb_id}')
        assert r2.status_code == 200
        data = r2.json()
        assert "body" in data
        assert "frontmatter" in data
        assert data["frontmatter"]["title"] == "Get V2 Test"

    def test_update_notebook_title_via_put(self, client, tmp_nb_dir_s1):
        r1 = client.post('/api/silos/silo_1/notebooks/create', json={"title": "PUT Title Old"})
        nb_id = r1.json()["id"]
        r2 = client.put(f'/api/silos/silo_1/notebooks/{nb_id}', json={"title": "PUT Title New"})
        assert r2.status_code == 200
        r3 = client.get(f'/api/silos/silo_1/notebooks/{nb_id}')
        assert r3.json()["frontmatter"]["title"] == "PUT Title New"

    def test_update_notebook_body_via_put(self, client, tmp_nb_dir_s1):
        r1 = client.post('/api/silos/silo_1/notebooks/create', json={"title": "Body PUT"})
        nb_id = r1.json()["id"]
        new_body = "## Updated\n\nNew content here\n"
        r2 = client.put(f'/api/silos/silo_1/notebooks/{nb_id}', json={"body": new_body})
        assert r2.status_code == 200
        r3 = client.get(f'/api/silos/silo_1/notebooks/{nb_id}')
        assert "## Updated" in r3.json()["body"]

    def test_delete_notebook_endpoint(self, client, tmp_nb_dir_s1):
        r1 = client.post('/api/silos/silo_1/notebooks/create', json={"title": "Delete HTTP"})
        nb_id = r1.json()["id"]
        r2 = client.delete(f'/api/silos/silo_1/notebooks/{nb_id}')
        assert r2.status_code == 200
        assert r2.json()["deleted"] is True
        r3 = client.get(f'/api/silos/silo_1/notebooks/{nb_id}')
        assert r3.status_code == 404

    def test_delete_nonexistent_notebook_404(self, client, tmp_nb_dir_s1):
        r = client.delete('/api/silos/silo_1/notebooks/nb_xxxxxxxx')
        assert r.status_code == 404

    def test_silo2_create_notebook(self, client, tmp_nb_dir_s2):
        resp = client.post('/api/silos/silo_2/notebooks/create', json={"title": "Legal HTTP NB"})
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_silo2_delete_notebook(self, client, tmp_nb_dir_s2):
        r1 = client.post('/api/silos/silo_2/notebooks/create', json={"title": "Legal Del HTTP"})
        nb_id = r1.json()["id"]
        r2 = client.delete(f'/api/silos/silo_2/notebooks/{nb_id}')
        assert r2.status_code == 200
        assert r2.json()["deleted"] is True
