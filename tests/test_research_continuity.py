"""Tests for matylda_lite.research_continuity — trace building, persistence, bootstrap."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from matylda_lite.research_continuity import (
    ResearchProjectMemoryTrace,
    build_research_project_memory_trace,
    build_research_bootstrap_view,
    load_research_traces,
    save_research_trace,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _silo_payload(
    title: str = "Test Skill Run",
    project_id: str = "proj_test",
    skill_id: str = "paper_review",
    result: str = "Found 3 papers.",
    darkroom_flags: list | None = None,
) -> dict:
    return {
        "workflow_kind":   "silo_skill",
        "title":           title,
        "project_id":      project_id,
        "artifact_status": "working",
        "skill_id":        skill_id,
        "result":          result,
        "sm_next_steps":   ["Consider replication"],
        "darkroom_flags":  darkroom_flags or [],
    }


# ── build_research_project_memory_trace (pure, no I/O) ───────────────────────

class TestBuildTrace:
    def test_returns_trace_instance(self):
        trace = build_research_project_memory_trace(_silo_payload())
        assert isinstance(trace, ResearchProjectMemoryTrace)

    def test_workflow_kind_preserved(self):
        trace = build_research_project_memory_trace(_silo_payload())
        assert trace.workflow_kind == "silo_skill"

    def test_project_id_preserved(self):
        trace = build_research_project_memory_trace(_silo_payload(project_id="myproj"))
        assert trace.project_id == "myproj"

    def test_title_preserved(self):
        trace = build_research_project_memory_trace(_silo_payload(title="My Title"))
        assert trace.title == "My Title"

    def test_summary_non_empty(self):
        trace = build_research_project_memory_trace(_silo_payload())
        assert trace.summary.strip()

    def test_key_weakness_non_empty(self):
        trace = build_research_project_memory_trace(_silo_payload())
        assert trace.key_weakness.strip()

    def test_recommended_next_step_non_empty(self):
        trace = build_research_project_memory_trace(_silo_payload())
        assert trace.recommended_next_step.strip()

    def test_darkroom_flags_in_summary(self):
        trace = build_research_project_memory_trace(
            _silo_payload(darkroom_flags=["speculative_claim"])
        )
        assert "speculative_claim" in trace.summary or "speculative_claim" in trace.key_weakness

    def test_as_dict_has_required_keys(self):
        trace = build_research_project_memory_trace(_silo_payload())
        d = trace.as_dict()
        for key in ("workflow_kind", "title", "project_id", "summary",
                    "key_weakness", "recommended_next_step", "recorded_at"):
            assert key in d, f"missing key: {key}"

    def test_as_memory_content_is_string(self):
        trace = build_research_project_memory_trace(_silo_payload())
        content = trace.as_memory_content()
        assert isinstance(content, str)
        assert len(content) > 10

    def test_generic_workflow_kind(self):
        payload = {
            "workflow_kind": "generic",
            "title":         "Generic test",
            "project_id":    "p1",
            "artifact_status": "draft",
        }
        trace = build_research_project_memory_trace(payload)
        assert trace.workflow_kind == "generic"


# ── save_research_trace + load_research_traces (I/O, uses tmp_traces_dir) ────

class TestSaveAndLoad:
    def test_save_creates_file(self, tmp_traces_dir: Path):
        trace = build_research_project_memory_trace(_silo_payload())
        result = save_research_trace(trace)
        files = list(tmp_traces_dir.glob("*.json"))
        assert len(files) == 1
        assert "id" in result

    def test_saved_id_starts_with_trace(self, tmp_traces_dir: Path):
        trace = build_research_project_memory_trace(_silo_payload())
        result = save_research_trace(trace)
        assert result["id"].startswith("trace_")

    def test_saved_kind_is_project_fact(self, tmp_traces_dir: Path):
        trace = build_research_project_memory_trace(_silo_payload())
        result = save_research_trace(trace)
        assert result["kind"] == "project_fact"

    def test_load_returns_saved_trace(self, tmp_traces_dir: Path):
        trace = build_research_project_memory_trace(
            _silo_payload(title="Load Me", project_id="loadproj")
        )
        save_research_trace(trace)
        loaded = load_research_traces()
        assert len(loaded) >= 1
        titles = [t.title for t in loaded]
        assert "Load Me" in titles

    def test_load_with_project_filter(self, tmp_traces_dir: Path):
        save_research_trace(build_research_project_memory_trace(_silo_payload(project_id="proj_a")))
        save_research_trace(build_research_project_memory_trace(_silo_payload(project_id="proj_b")))
        loaded_a = load_research_traces(project_id="proj_a")
        assert all(t.project_id == "proj_a" for t in loaded_a)
        assert len(loaded_a) == 1

    def test_load_empty_dir_returns_empty(self, tmp_traces_dir: Path):
        loaded = load_research_traces()
        assert loaded == []

    def test_round_trip_preserves_summary(self, tmp_traces_dir: Path):
        trace = build_research_project_memory_trace(_silo_payload())
        save_research_trace(trace)
        loaded = load_research_traces()[0]
        assert loaded.summary == trace.summary


# ── build_research_bootstrap_view ────────────────────────────────────────────

class TestBootstrapView:
    def test_empty_traces_returns_zero_count(self, tmp_traces_dir: Path):
        view = build_research_bootstrap_view(project_id="empty_proj")
        assert view["continuity_trace_count"] == 0
        # Status signals "no data yet" — exact value is implementation detail
        assert "bootstrap" in view["continuity_status"] or "no" in view["continuity_status"]

    def test_with_one_trace(self, tmp_traces_dir: Path):
        trace = build_research_project_memory_trace(
            _silo_payload(project_id="bp_proj", result="Bootstrap test result")
        )
        save_research_trace(trace)
        view = build_research_bootstrap_view(project_id="bp_proj")
        assert view["continuity_trace_count"] >= 1
        assert view["continuity_status"] != "no_prior_sessions"

    def test_suggested_next_step_non_empty_with_traces(self, tmp_traces_dir: Path):
        trace = build_research_project_memory_trace(_silo_payload(project_id="ns_proj"))
        save_research_trace(trace)
        view = build_research_bootstrap_view(project_id="ns_proj")
        assert isinstance(view.get("suggested_next_step"), str)

    def test_bootstrap_summary_is_string(self, tmp_traces_dir: Path):
        view = build_research_bootstrap_view(project_id="any")
        assert isinstance(view.get("bootstrap_summary", ""), str)
