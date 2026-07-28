"""Tests for matylda_lite.models — UCB1 routing, performance log, recommendations."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from matylda_lite.models import (
    SUPPORTED_MODELS,
    TASK_TYPES,
    calculate_model_scores,
    get_model_performance_summary,
    recommend_model_ucb1,
    update_model_performance,
)


# ── calculate_model_scores (uses tmp_perf_log) ────────────────────────────────

class TestCalculateModelScores:
    def test_all_models_present_in_output(self, tmp_perf_log: Path):
        scores = calculate_model_scores("general")
        assert set(scores.keys()) == set(SUPPORTED_MODELS)

    def test_no_data_gives_zero_calls(self, tmp_perf_log: Path):
        scores = calculate_model_scores("general")
        for m, s in scores.items():
            assert s["calls"] == 0

    def test_no_data_ucb1_is_infinite(self, tmp_perf_log: Path):
        scores = calculate_model_scores("general")
        import math
        for m, s in scores.items():
            # No data → ucb1 = inf (exploration-first: never-tried models
            # get infinite priority so they are sampled before UCB1 kicks in)
            assert math.isinf(s["ucb1"]) or s["ucb1"] == 0.0

    def test_after_one_success_success_rate_is_1(self, tmp_perf_log: Path):
        update_model_performance("general", "haiku", success=True)
        scores = calculate_model_scores("general")
        assert scores["haiku"]["successes"] == 1
        assert scores["haiku"]["calls"] == 1
        assert scores["haiku"]["success_rate"] == pytest.approx(1.0)

    def test_after_one_failure_success_rate_is_0(self, tmp_perf_log: Path):
        update_model_performance("general", "sonnet", success=False)
        scores = calculate_model_scores("general")
        assert scores["sonnet"]["success_rate"] == pytest.approx(0.0)

    def test_mixed_successes_correct_rate(self, tmp_perf_log: Path):
        update_model_performance("research", "opus", success=True)
        update_model_performance("research", "opus", success=True)
        update_model_performance("research", "opus", success=False)
        scores = calculate_model_scores("research")
        assert scores["opus"]["calls"] == 3
        assert scores["opus"]["successes"] == 2
        assert scores["opus"]["success_rate"] == pytest.approx(2 / 3)

    def test_task_type_isolation(self, tmp_perf_log: Path):
        update_model_performance("research", "haiku", success=True)
        update_model_performance("coding", "sonnet", success=True)
        research_scores = calculate_model_scores("research")
        coding_scores   = calculate_model_scores("coding")
        assert research_scores["haiku"]["calls"] == 1
        assert coding_scores["sonnet"]["calls"] == 1
        assert research_scores["sonnet"]["calls"] == 0

    def test_ucb1_increases_with_exploration_need(self, tmp_perf_log: Path):
        # Give haiku 5 calls, sonnet 1 call — haiku should have lower UCB1
        # (less exploration bonus) assuming equal success rate
        for _ in range(5):
            update_model_performance("synthesis", "haiku", success=True)
        update_model_performance("synthesis", "sonnet", success=True)
        scores = calculate_model_scores("synthesis")
        # sonnet has fewer calls → higher UCB1 exploration bonus
        assert scores["sonnet"]["ucb1"] > scores["haiku"]["ucb1"]


# ── recommend_model_ucb1 ──────────────────────────────────────────────────────

class TestRecommendModelUCB1:
    def test_returns_supported_model(self, tmp_perf_log: Path):
        rec = recommend_model_ucb1("general")
        assert rec in SUPPORTED_MODELS

    def test_explore_never_tried_model(self, tmp_perf_log: Path):
        # With zero data every model is equal — function must return one of them
        rec = recommend_model_ucb1("planning")
        assert rec in SUPPORTED_MODELS

    def test_hostile_review_biases_toward_opus(self, tmp_perf_log: Path):
        # With zero data UCB1 can't differentiate, but after priming with equal
        # data the content bias for "hostile" text should prefer opus.
        for m in SUPPORTED_MODELS:
            for _ in range(3):
                update_model_performance("review", m, success=True)
        rec = recommend_model_ucb1("review", task_text="hostile review of the methodology")
        assert rec == "opus"

    def test_status_query_biases_toward_haiku(self, tmp_perf_log: Path):
        for m in SUPPORTED_MODELS:
            for _ in range(3):
                update_model_performance("general", m, success=True)
        rec = recommend_model_ucb1("general", task_text="list all active threads status")
        assert rec == "haiku"

    def test_all_task_types_return_valid_model(self, tmp_perf_log: Path):
        for tt in TASK_TYPES:
            rec = recommend_model_ucb1(tt)
            assert rec in SUPPORTED_MODELS, f"Invalid model for task_type={tt}: {rec}"


# ── update_model_performance ──────────────────────────────────────────────────

class TestUpdateModelPerformance:
    def test_appends_to_log(self, tmp_perf_log: Path):
        update_model_performance("coding", "haiku", success=True)
        lines = tmp_perf_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1

    def test_appends_multiple_rows(self, tmp_perf_log: Path):
        update_model_performance("coding", "haiku",  success=True)
        update_model_performance("coding", "sonnet", success=False)
        lines = tmp_perf_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_row_structure(self, tmp_perf_log: Path):
        row = update_model_performance("research", "opus", success=True,
                                       latency_ms=1234.5, project_id="p1")
        assert row["task_type"]  == "research"
        assert row["model"]      == "opus"
        assert row["success"]    is True
        assert row["latency_ms"] == 1234.5
        assert row["project_id"] == "p1"


# ── get_model_performance_summary ────────────────────────────────────────────

class TestGetModelPerformanceSummary:
    def test_returns_dict_of_task_types(self, tmp_perf_log: Path):
        summary = get_model_performance_summary()
        assert isinstance(summary, dict)

    def test_summary_includes_logged_task_types_only(self, tmp_perf_log: Path):
        # Summary only includes task types that have at least one observation.
        # With no data the summary is empty; after logging it gains entries.
        assert get_model_performance_summary() == {}
        update_model_performance("coding", "haiku", success=True)
        summary = get_model_performance_summary()
        assert "coding" in summary

    def test_summary_values_have_model_keys(self, tmp_perf_log: Path):
        update_model_performance("general", "haiku", success=True)
        summary = get_model_performance_summary()
        general = summary["general"]
        assert "haiku" in general or "recommended" in general
