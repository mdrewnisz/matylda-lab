"""Tests for matylda_lite.research_pipeline — PipelineResult struct and error paths.

All tests here are unit-level (no real LLM calls, no live server).
The pipeline's graceful-degradation error paths are tested by providing
a nonexistent skill_id so Stage 1 fails cleanly.
"""
from __future__ import annotations

import pytest

from matylda_lite.research_pipeline import PipelineResult, run_research_pipeline


# ── PipelineResult dataclass ──────────────────────────────────────────────────

class TestPipelineResultStruct:
    def _make(self, **kw) -> PipelineResult:
        defaults = dict(
            pipeline_id="pipeline_abc12345",
            silo_id="silo_1",
            skill_id="paper_review",
            skill_name="Paper Review",
            project_id="proj_test",
            started_at="2026-01-01T00:00:00+00:00",
            completed_at="2026-01-01T00:00:02+00:00",
            duration_ms=2000,
        )
        defaults.update(kw)
        return PipelineResult(**defaults)

    def test_ok_defaults_to_true(self):
        r = self._make()
        assert r.ok is True

    def test_error_defaults_to_empty(self):
        r = self._make()
        assert r.error == ""

    def test_as_dict_contains_core_keys(self):
        r = self._make()
        d = r.as_dict()
        for key in ("pipeline_id", "silo_id", "skill_id", "skill_name",
                    "project_id", "started_at", "completed_at", "duration_ms",
                    "ok", "error"):
            assert key in d, f"missing key: {key}"

    def test_as_dict_contains_stage_keys(self):
        r = self._make()
        d = r.as_dict()
        for key in ("skill_result", "darkroom_flags", "llm_used",
                    "trace_id", "trace_summary", "trace_key_weakness",
                    "trace_recommended_next_step",
                    "sm_day_synthesis", "sm_proposed_next_steps",
                    "sm_next_questions", "sm_warnings",
                    "chronicle_event_ids"):
            assert key in d, f"missing stage key: {key}"

    def test_summary_text_contains_pipeline_id(self):
        r = self._make()
        txt = r.summary_text()
        assert "pipeline_abc12345" in txt

    def test_summary_text_ok_shows_checkmark(self):
        r = self._make(ok=True)
        assert "✓ OK" in r.summary_text()

    def test_summary_text_error_shows_message(self):
        r = self._make(ok=False, error="Skill failed: not found")
        txt = r.summary_text()
        assert "✗" in txt

    def test_summary_text_includes_darkroom_count(self):
        r = self._make(darkroom_flags=["flag_a", "flag_b"])
        txt = r.summary_text()
        assert "2 flag" in txt

    def test_summary_text_no_flags_shows_brak(self):
        r = self._make(darkroom_flags=[])
        txt = r.summary_text()
        assert "brak" in txt.lower()

    def test_chronicle_event_ids_default_empty(self):
        r = self._make()
        assert r.chronicle_event_ids == []

    def test_sm_fields_default_empty(self):
        r = self._make()
        assert r.sm_proposed_next_steps == []
        assert r.sm_next_questions == []
        assert r.sm_warnings == []

    def test_as_dict_lists_are_lists(self):
        r = self._make(
            darkroom_flags=["f1"],
            sm_proposed_next_steps=["step1"],
            chronicle_event_ids=["chronicle:abc123"],
        )
        d = r.as_dict()
        assert isinstance(d["darkroom_flags"], list)
        assert isinstance(d["sm_proposed_next_steps"], list)
        assert isinstance(d["chronicle_event_ids"], list)


# ── run_research_pipeline — error paths ──────────────────────────────────────

class TestPipelineErrorPaths:
    """Test graceful failure without LLM calls.

    The pipeline returns ok=False when the skill doesn't exist
    (Stage 1 failure), but still fills pipeline_id / timing fields.
    Chronicle and trace stages are skipped but don't raise.
    """

    def test_nonexistent_skill_returns_result(self, tmp_chronicle, tmp_traces_dir):
        result = run_research_pipeline(
            "skill_does_not_exist_xyz",
            {},
            silo_id="silo_1",
            project_id="test",
        )
        assert isinstance(result, PipelineResult)

    def test_nonexistent_skill_ok_is_false(self, tmp_chronicle, tmp_traces_dir):
        result = run_research_pipeline(
            "skill_does_not_exist_xyz",
            {},
            silo_id="silo_1",
            project_id="test",
        )
        assert result.ok is False

    def test_nonexistent_skill_error_message_present(self, tmp_chronicle, tmp_traces_dir):
        result = run_research_pipeline(
            "skill_does_not_exist_xyz",
            {},
            silo_id="silo_1",
            project_id="test",
        )
        assert result.error.strip()

    def test_pipeline_id_always_set(self, tmp_chronicle, tmp_traces_dir):
        result = run_research_pipeline(
            "skill_does_not_exist_xyz",
            {},
            silo_id="silo_1",
            project_id="test",
        )
        assert result.pipeline_id.startswith("pipeline_")

    def test_timing_fields_filled(self, tmp_chronicle, tmp_traces_dir):
        result = run_research_pipeline(
            "skill_does_not_exist_xyz",
            {},
            silo_id="silo_1",
            project_id="test",
        )
        assert result.started_at
        assert result.completed_at
        assert result.duration_ms >= 0

    def test_unsupported_silo_returns_error(self, tmp_chronicle, tmp_traces_dir):
        result = run_research_pipeline(
            "some_skill",
            {},
            silo_id="silo_99",
            project_id="test",
        )
        assert result.ok is False
        assert "silo_99" in result.error or "nie jest obsługiwany" in result.error

    def test_as_dict_serializable_on_error(self, tmp_chronicle, tmp_traces_dir):
        import json
        result = run_research_pipeline(
            "skill_does_not_exist_xyz",
            {},
            silo_id="silo_1",
            project_id="test",
        )
        d = result.as_dict()
        # Must be JSON-serializable
        serialized = json.dumps(d)
        assert serialized
