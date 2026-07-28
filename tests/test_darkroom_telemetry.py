"""Regression tests for DARKROOM telemetry schemas and counters."""
from __future__ import annotations

import json
from datetime import date

from matylda_lite.darkroom import meta_evaluator
from matylda_lite.darkroom import pipeline


def _review(timestamp: str, verdict: str | None, *, legacy: bool = True) -> dict:
    summary = {
        "verdict": verdict,
        "total_issues": 1,
        "reviews": [
            {
                "reviewer": "skeptic",
                "issues": ["issue"],
                "notes": "",
            }
        ],
    }
    record = {"timestamp": timestamp, "summary": summary}
    if not legacy:
        record["verdict"] = verdict
    return record


def test_nested_verdict_is_not_silently_replaced_with_pass():
    assert pipeline.review_verdict(_review("20260727T100000", "flag")) == "flag"
    assert pipeline.review_verdict({"timestamp": "20260727T100001"}) is None


def test_review_summary_counts_unknown_separately():
    records = [
        _review("20260727T100000", "pass"),
        _review("20260727T100001", "flag"),
        _review("20260727T100002", "fail"),
        {"timestamp": "20260727T100003"},
    ]

    metrics = pipeline.summarize_review_records(records)

    assert metrics["total_reviews"] == 3
    assert metrics["total_passes"] == 1
    assert metrics["total_flags"] == 1
    assert metrics["total_failures"] == 1
    assert metrics["unknown_reviews"] == 1
    assert metrics["telemetry_status"] == "degraded"


def test_reviewer_execution_error_degrades_telemetry():
    record = _review("20260727T100000", "pass")
    record["summary"]["reviews"][0]["notes"] = "[REVIEWER ERROR: invalid JSON]"

    metrics = pipeline.summarize_review_records([record])

    assert metrics["reviewer_errors"] == 1
    assert metrics["telemetry_status"] == "degraded"


def test_metrics_are_rebuilt_from_review_logs(tmp_path, monkeypatch):
    logs = tmp_path / "review_logs"
    logs.mkdir()
    metrics_file = tmp_path / "failure_metrics.json"
    metrics_file.write_text(
        json.dumps({"total_reviews": 99, "repeated_patterns": [{"issue": "x"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline, "_REVIEW_LOGS_DIR", logs)
    monkeypatch.setattr(pipeline, "_METRICS_FILE", metrics_file)

    for index, verdict in enumerate(("pass", "flag", "fail")):
        path = logs / f"review_{index}.json"
        path.write_text(
            json.dumps(_review(f"20260727T10000{index}", verdict)),
            encoding="utf-8",
        )

    pipeline._update_metrics({"verdict": "pass"})
    rebuilt = json.loads(metrics_file.read_text(encoding="utf-8"))

    assert rebuilt["total_reviews"] == 3
    assert rebuilt["total_passes"] == 1
    assert rebuilt["total_flags"] == 1
    assert rebuilt["total_failures"] == 1
    assert rebuilt["repeated_patterns"] == [{"issue": "x"}]


def test_meta_payload_reads_heuristic_failures_and_disposition():
    failures = [
        {
            "heuristic_failures": [
                {"reviewer": "skeptic", "issue": "Unsupported claim"},
                {"reviewer": "skeptic", "issue": "Unsupported claim"},
            ]
        }
    ]
    today = date.today().strftime("%Y%m%d")
    reviews = [
        _review(f"{today}T100000", "flag"),
        _review(f"{today}T100001", "pass"),
    ]
    stored = {
        "total_reviews": 2,
        "total_passes": 1,
        "total_flags": 1,
        "total_failures": 0,
        "repeated_patterns": [],
    }
    profile = {
        "skepticism_level": 0.76,
        "uncertainty_tolerance": 0.8,
        "falsification_preference": 0.9,
        "narrative_risk_sensitivity": 0.8,
        "review_strictness": 1.0,
        "last_updated": "2026-06-29",
    }

    data = meta_evaluator._build_analysis_data(
        failures, stored, reviews, reviews, 0, profile
    )

    assert data["pass"] == 1
    assert data["flag"] == 1
    assert data["fail"] == 0
    assert data["unknown_verdicts"] == 0
    assert data["top_issue_patterns"][0] == ("unsupported claim", 2)
    assert data["issues_by_reviewer"] == {"skeptic": 2}
    assert data["disposition"]["review_strictness"] == 1.0
    assert data["telemetry_quality"] == "ok"
