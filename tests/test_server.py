"""HTTP integration tests for the FastAPI server (v0.4a).

Uses FastAPI TestClient (no live uvicorn). Tests verify:
  - Status codes and response shapes for read endpoints
  - 400 validation for missing required fields
  - Version bump visible in /api/health
  - New pipeline endpoints are reachable

Endpoints that call the LLM (chat, sleeping/run, etc.) are NOT called here —
they are covered by @pytest.mark.slow tests in test_server_slow.py (future).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


# ── Health + version ──────────────────────────────────────────────────────────

def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["version"] == "1.2"


# ── Chronicle ─────────────────────────────────────────────────────────────────

def test_chronicle_list_returns_events_key(client):
    r = client.get("/api/chronicle?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert "count" in data
    assert isinstance(data["events"], list)


def test_chronicle_log_requires_source_and_event_type(client):
    r = client.post("/api/chronicle/log", json={"source": "test"})
    assert r.status_code == 400


def test_chronicle_log_valid_event(client):
    r = client.post("/api/chronicle/log", json={
        "source": "test_suite",
        "event_type": "smoke_test",
        "project_id": "test",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "event" in data
    assert data["event"]["source"] == "test_suite"


# ── Research traces ───────────────────────────────────────────────────────────

def test_research_traces_list(client):
    r = client.get("/api/research/traces")
    assert r.status_code == 200
    data = r.json()
    assert "traces" in data
    assert "count" in data
    assert isinstance(data["traces"], list)


def test_research_trace_save_requires_title_and_workflow(client):
    r = client.post("/api/research/traces/save", json={"title": "Only title"})
    assert r.status_code == 400


def test_research_trace_save_valid(client):
    r = client.post("/api/research/traces/save", json={
        "title":         "Smoke test trace",
        "workflow_kind": "silo_skill",
        "project_id":    "test",
        "artifact_status": "working",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "trace_id" in data


def test_research_bootstrap(client):
    r = client.get("/api/research/bootstrap?project_id=test")
    assert r.status_code == 200
    data = r.json()
    assert "continuity_trace_count" in data
    assert "continuity_status" in data


# ── Pipeline endpoints ────────────────────────────────────────────────────────

def test_pipeline_list_reachable(client):
    r = client.get("/api/research/pipeline/list?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)


def test_pipeline_run_requires_skill_id(client):
    r = client.post("/api/research/pipeline/run", json={})
    assert r.status_code == 400


def test_pipeline_run_nonexistent_skill_returns_error_result(client):
    r = client.post("/api/research/pipeline/run", json={
        "skill_id":  "skill_xyz_does_not_exist",
        "inputs":    {},
        "project_id": "test",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["pipeline_id"].startswith("pipeline_")


def test_silo_pipeline_endpoint_reachable(client):
    r = client.post("/api/silos/silo_1/run-pipeline", json={
        "skill_id": "skill_xyz_does_not_exist",
        "inputs":   {},
    })
    assert r.status_code == 200
    data = r.json()
    assert "ok" in data
    assert "pipeline_id" in data


# ── Model performance ─────────────────────────────────────────────────────────

def test_models_performance_list(client):
    r = client.get("/api/models/performance")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert isinstance(data["summary"], dict)


def test_models_recommend(client):
    r = client.get("/api/models/recommend?task_type=general")
    assert r.status_code == 200
    data = r.json()
    assert "recommended_model" in data
    from matylda_lite.models import SUPPORTED_MODELS
    assert data["recommended_model"] in SUPPORTED_MODELS


def test_models_performance_log_requires_model(client):
    r = client.post("/api/models/performance/log", json={"task_type": "general"})
    assert r.status_code == 400


def test_models_performance_log_valid(client):
    r = client.post("/api/models/performance/log", json={
        "task_type": "research",
        "model":     "haiku",
        "success":   True,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


# ── Silos discovery ───────────────────────────────────────────────────────────

def test_silos_list(client):
    r = client.get("/api/silos")
    assert r.status_code == 200
    data = r.json()
    assert "silos" in data
    silo_ids = [s["id"] for s in data["silos"]]
    assert "silo_1" in silo_ids


def test_silo_1_info(client):
    r = client.get("/api/silos/silo_1/info")
    assert r.status_code == 200
    data = r.json()
    assert data["silo_id"] == "silo_1"


def test_silo_1_skills_list(client):
    r = client.get("/api/silos/silo_1/skills")
    assert r.status_code == 200
    data = r.json()
    assert "skills" in data
    assert isinstance(data["skills"], list)


def test_silo_1_notebooks_list(client):
    r = client.get("/api/silos/silo_1/notebooks")
    assert r.status_code == 200
    data = r.json()
    assert "notebooks" in data


def test_silo_1_llm_policy(client):
    r = client.get("/api/silos/silo_1/llm-policy")
    assert r.status_code == 200
    data = r.json()
    assert data["silo_id"] == "silo_1"
    assert "policy" in data


# ── Perception ────────────────────────────────────────────────────────────────

def test_perception_context_reachable(client):
    r = client.get("/api/perception/context?project_id=test&event_limit=5")
    assert r.status_code == 200
    data = r.json()
    assert "available" in data


def test_perception_last_reachable(client):
    r = client.get("/api/perception/last")
    assert r.status_code == 200
    data = r.json()
    assert "available" in data


# ── DARKROOM ──────────────────────────────────────────────────────────────────

def test_darkroom_status(client):
    r = client.get("/api/darkroom")
    assert r.status_code == 200


def test_darkroom_history(client):
    r = client.get("/api/darkroom/history")
    assert r.status_code == 200
    data = r.json()
    assert "history" in data


# ── Memory ───────────────────────────────────────────────────────────────────

def test_memory_list(client):
    r = client.get("/api/memory")
    assert r.status_code == 200
    data = r.json()
    assert "insights" in data


def test_memory_save_requires_content(client):
    r = client.post("/api/memory/save", json={})
    assert r.status_code == 400


def test_memory_save_valid(client):
    r = client.post("/api/memory/save", json={
        "content": "Regression test insight",
        "topic": "tests",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


# ── Search ───────────────────────────────────────────────────────────────────

def test_search_empty_returns_results_key(client):
    r = client.get("/api/search?q=")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data


def test_search_with_query(client):
    r = client.get("/api/search?q=test")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert isinstance(data["results"], list)
