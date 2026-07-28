"""Shared fixtures for Matylda Lite regression tests.

Isolation strategy
------------------
All tests that touch the filesystem patch module-level Path constants
(CHRONICLE_LOG, TRACES_DIR, PERFORMANCE_LOG) to point at tmp_path.
This keeps tests hermetic and avoids polluting the real workspace.

API calls
---------
Tests that could trigger a real LLM call either:
  - monkeypatch `get_api_key` to return a sentinel "sk-test" — so that code
    paths that don't actually call the LLM still work, OR
  - are marked @pytest.mark.slow and skipped by default.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ── Path isolation helpers ────────────────────────────────────────────────────

@pytest.fixture()
def tmp_chronicle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect CHRONICLE_LOG to a fresh tmp file and yield its path."""
    log = tmp_path / "chronicle.jsonl"
    log.touch()
    import matylda_lite.chronicle as ch
    monkeypatch.setattr(ch, "CHRONICLE_LOG", log)
    return log


@pytest.fixture()
def tmp_traces_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect TRACES_DIR to a fresh tmp directory and yield its path."""
    d = tmp_path / "traces"
    d.mkdir()
    import matylda_lite.research_continuity as rc
    monkeypatch.setattr(rc, "TRACES_DIR", d)
    return d


@pytest.fixture()
def tmp_perf_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect PERFORMANCE_LOG to a fresh tmp file and yield its path."""
    log = tmp_path / "model_performance.jsonl"
    log.touch()
    import matylda_lite.models as mdl
    monkeypatch.setattr(mdl, "PERFORMANCE_LOG", log)
    return log


# ── API key mock ──────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_api_key(monkeypatch: pytest.MonkeyPatch):
    """Provide a dummy API key so code that reads it won't raise."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")


# ── FastAPI TestClient ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    """Return a FastAPI TestClient for the Matylda Lite server.

    Uses scope="session" so the app is only constructed once per test run.
    Starts with ANTHROPIC_API_KEY set to a dummy value.
    """
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")
    from matylda_lite.server import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Notebook dir isolation ────────────────────────────────────────────────────

@pytest.fixture()
def tmp_nb_dir_s1(tmp_path, monkeypatch):
    """Redirect silo_1 notebook dir and index to tmp."""
    import matylda_lite.silos.silo_1 as s1
    d = tmp_path / "silo1_notebooks"; d.mkdir()
    idx = tmp_path / "silo1_notebooks_index.json"
    monkeypatch.setattr(s1, "_NB_DIR", d)
    monkeypatch.setattr(s1, "_NB_INDEX", idx)
    return d

@pytest.fixture()
def tmp_nb_dir_s2(tmp_path, monkeypatch):
    """Redirect silo_2 notebook dir and index to tmp."""
    import matylda_lite.silos.silo_2 as s2
    d = tmp_path / "silo2_notebooks"; d.mkdir()
    idx = tmp_path / "silo2_notebooks_index.json"
    monkeypatch.setattr(s2, "_NB_DIR", d)
    monkeypatch.setattr(s2, "_NB_INDEX", idx)
    return d


# ── Chronicle event factory ───────────────────────────────────────────────────

def make_event(
    source: str = "secretary",
    event_type: str = "task_done",
    project_id: str = "proj_test",
    domain: str = "research",
    workflow_kind: str | None = "paper_review",
    context_ref: str | None = "desk/TEST.md",
    metadata: dict | None = None,
    timestamp: str | None = None,
):
    """Helper: build a ChronicleEvent without writing to disk."""
    from matylda_lite.chronicle import build_chronicle_event
    return build_chronicle_event(
        source=source,
        event_type=event_type,
        project_id=project_id,
        domain=domain,
        workflow_kind=workflow_kind,
        context_ref=context_ref,
        metadata=metadata,
        timestamp=timestamp,
    )
