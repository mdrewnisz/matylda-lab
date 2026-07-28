"""Tests for v0.5 Multi-project: project CRUD, activation, notebook filtering, summary."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_projects_dir(tmp_path, monkeypatch):
    """Redirect projects dirs to tmp."""
    import matylda_lite.library_manager as lm
    proj_dir = tmp_path / "projects"
    proj_dir.mkdir()
    arch_dir = tmp_path / "projects" / "archive"
    arch_dir.mkdir()
    monkeypatch.setattr(lm, "_PROJECTS_DIR", proj_dir)
    monkeypatch.setattr(lm, "_PROJECTS_ARCHIVE_DIR", arch_dir)
    return proj_dir


@pytest.fixture()
def tmp_active_project(tmp_path, monkeypatch):
    """Redirect active_project.json to tmp."""
    import matylda_lite.project_context as pc
    active_file = tmp_path / "active_project.json"
    monkeypatch.setattr(pc, "_ACTIVE_FILE", active_file)
    monkeypatch.setattr(pc, "_PROJECTS_DIR", tmp_path / "projects_ctx")
    (tmp_path / "projects_ctx").mkdir()
    return active_file


# ── library_manager project functions ─────────────────────────────────────────

class TestProjectCRUD:
    def test_create_project_returns_id(self, tmp_projects_dir):
        from matylda_lite.library_manager import create_project
        proj = create_project("Test Alpha")
        assert proj["id"].startswith("proj_")
        assert proj["name"] == "Test Alpha"

    def test_create_project_sets_status_active(self, tmp_projects_dir):
        from matylda_lite.library_manager import create_project
        proj = create_project("Status Test")
        assert proj["status"] == "active"

    def test_list_projects_returns_created(self, tmp_projects_dir):
        from matylda_lite.library_manager import create_project, list_projects
        create_project("List Me")
        projects = list_projects()
        names = [p["name"] for p in projects]
        assert "List Me" in names

    def test_create_multiple_projects(self, tmp_projects_dir):
        from matylda_lite.library_manager import create_project, list_projects
        create_project("Alpha")
        create_project("Beta")
        create_project("Gamma")
        assert len(list_projects()) == 3

    def test_archive_project(self, tmp_projects_dir):
        from matylda_lite.library_manager import create_project, archive_project, list_projects
        proj = create_project("Archive Me")
        ok = archive_project(proj["id"])
        assert ok is True
        active = list_projects(include_archived=False)
        assert not any(p["id"] == proj["id"] for p in active)

    def test_archive_then_restore(self, tmp_projects_dir):
        from matylda_lite.library_manager import create_project, archive_project, restore_project, list_projects
        proj = create_project("Restore Me")
        archive_project(proj["id"])
        restore_project(proj["id"])
        active = list_projects()
        assert any(p["id"] == proj["id"] for p in active)

    def test_archive_nonexistent_returns_false(self, tmp_projects_dir):
        from matylda_lite.library_manager import archive_project
        assert archive_project("proj_doesnotexist") is False


# ── project_context ───────────────────────────────────────────────────────────

class TestProjectContext:
    def test_get_active_returns_none_when_no_file(self, tmp_active_project):
        from matylda_lite.project_context import get_active_project
        assert get_active_project() is None

    def test_clear_active_no_error_when_no_file(self, tmp_active_project):
        from matylda_lite.project_context import clear_active_project
        clear_active_project()  # should not raise

    def test_set_and_get_active_project(self, tmp_active_project, tmp_projects_dir, monkeypatch):
        import matylda_lite.project_context as pc
        monkeypatch.setattr(pc, "_PROJECTS_DIR", tmp_projects_dir)
        from matylda_lite.library_manager import create_project
        proj = create_project("Active Test")
        # Write project file to tmp_projects_dir (already there)
        from matylda_lite.project_context import set_active_project, get_active_project
        set_active_project(proj["id"])
        active = get_active_project()
        assert active is not None
        assert active["project_id"] == proj["id"]

    def test_clear_active_removes_file(self, tmp_active_project, tmp_projects_dir, monkeypatch):
        import matylda_lite.project_context as pc
        monkeypatch.setattr(pc, "_PROJECTS_DIR", tmp_projects_dir)
        from matylda_lite.library_manager import create_project
        proj = create_project("Clear Test")
        from matylda_lite.project_context import set_active_project, clear_active_project, get_active_project
        set_active_project(proj["id"])
        assert get_active_project() is not None
        clear_active_project()
        assert get_active_project() is None


# ── Notebook filtering by project_id ─────────────────────────────────────────

class TestNotebookProjectFilter:
    def test_silo1_notebooks_filtered_by_project(self, tmp_nb_dir_s1):
        from matylda_lite.silos.silo_1 import _create_notebook, _load_nb_index
        _create_notebook("NB Proj A", project_id="proj_a")
        _create_notebook("NB Proj B", project_id="proj_b")
        all_nbs = _load_nb_index()
        proj_a = [n for n in all_nbs if n.get("project_id") == "proj_a"]
        proj_b = [n for n in all_nbs if n.get("project_id") == "proj_b"]
        assert len(proj_a) == 1
        assert len(proj_b) == 1

    def test_silo2_notebooks_filtered_by_project(self, tmp_nb_dir_s2):
        from matylda_lite.silos.silo_2 import _create_notebook, _load_nb_index
        _create_notebook("Legal NB A", project_id="legal_a")
        _create_notebook("Legal NB B", project_id="legal_b")
        all_nbs = _load_nb_index()
        a = [n for n in all_nbs if n.get("project_id") == "legal_a"]
        assert len(a) == 1

    def test_http_notebook_filter_silo1(self, client, tmp_nb_dir_s1):
        client.post('/api/silos/silo_1/notebooks/create', json={"title": "Filter A", "project_id": "filter_proj_a"})
        client.post('/api/silos/silo_1/notebooks/create', json={"title": "Filter B", "project_id": "filter_proj_b"})
        r = client.get('/api/silos/silo_1/notebooks?project_id=filter_proj_a')
        assert r.status_code == 200
        nbs = r.json()["notebooks"]
        assert len(nbs) == 1
        assert nbs[0]["title"] == "Filter A"

    def test_http_notebook_no_filter_returns_all(self, client, tmp_nb_dir_s1):
        client.post('/api/silos/silo_1/notebooks/create', json={"title": "All A"})
        client.post('/api/silos/silo_1/notebooks/create', json={"title": "All B"})
        r = client.get('/api/silos/silo_1/notebooks')
        assert r.status_code == 200
        nbs = r.json()["notebooks"]
        assert len(nbs) >= 2


# ── Project summary endpoint ──────────────────────────────────────────────────

class TestProjectSummaryEndpoint:
    def test_summary_returns_project_id(self, client, tmp_traces_dir):
        r = client.get('/api/library/projects/some_proj/summary')
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == "some_proj"

    def test_summary_zero_counts_for_unknown_project(self, client, tmp_traces_dir):
        r = client.get('/api/library/projects/unknown_xxx/summary')
        assert r.status_code == 200
        data = r.json()
        assert data["trace_count"] == 0
        assert data["notebook_count"] == 0
        assert data["last_activity"] is None

    def test_summary_counts_traces(self, client, tmp_traces_dir):
        from matylda_lite.research_continuity import build_research_project_memory_trace, save_research_trace
        trace = build_research_project_memory_trace({
            "workflow_kind": "silo_skill",
            "title": "Summary trace",
            "project_id": "summary_proj",
            "artifact_status": "working",
            "skill_id": "test_skill",
            "result": "done",
            "sm_next_steps": [],
            "darkroom_flags": [],
        })
        save_research_trace(trace)
        r = client.get('/api/library/projects/summary_proj/summary')
        data = r.json()
        assert data["trace_count"] >= 1


# ── HTTP project endpoints ────────────────────────────────────────────────────

class TestProjectHTTPEndpoints:
    def test_list_projects_returns_list(self, client):
        r = client.get('/api/library/projects')
        assert r.status_code == 200
        assert "projects" in r.json()

    def test_create_project_via_http(self, client, tmp_projects_dir):
        r = client.post('/api/library/projects', json={"name": "HTTP Project", "description": "Test"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["project"]["name"] == "HTTP Project"

    def test_create_project_no_name_returns_error(self, client):
        r = client.post('/api/library/projects', json={"name": ""})
        assert r.status_code in (200, 400, 422)
        if r.status_code == 200:
            data = r.json()
            assert data.get("ok") is False or data.get("error")

    def test_activate_then_get_active(self, client, tmp_projects_dir, tmp_active_project, monkeypatch):
        import matylda_lite.project_context as pc
        monkeypatch.setattr(pc, "_PROJECTS_DIR", tmp_projects_dir)
        monkeypatch.setattr(pc, "_ACTIVE_FILE", tmp_active_project)
        # Create project first
        r1 = client.post('/api/library/projects', json={"name": "Activate Me"})
        proj_id = r1.json()["project"]["id"]
        # Activate
        r2 = client.post('/api/library/projects/activate', json={"project_id": proj_id})
        assert r2.status_code == 200
        # Get active
        r3 = client.get('/api/library/projects/active')
        active = r3.json().get("project")
        assert active is not None
        assert active.get("project_id") == proj_id or active.get("id") == proj_id

    def test_deactivate_project(self, client, tmp_active_project, monkeypatch):
        import matylda_lite.project_context as pc
        monkeypatch.setattr(pc, "_ACTIVE_FILE", tmp_active_project)
        r = client.post('/api/library/projects/deactivate')
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_version_is_08(self, client):
        r = client.get('/api/health')
        assert r.status_code == 200
        assert r.json()["version"] == "1.2"
