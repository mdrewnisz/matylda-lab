"""Tests for the constructive Matylda Lab DARKROOM calibration."""
from __future__ import annotations

from matylda_lite.darkroom import disposition
from matylda_lite.darkroom import pipeline
from matylda_lite.darkroom.reviewers import Review, aggregate
from matylda_lite.secretary import Secretary


def _flag(severity: float) -> Review:
    return Review(
        reviewer="skeptic",
        verdict="flag",
        issues=["possible overclaim"],
        severity=severity,
        confidence_adjustment=-0.1,
        notes="",
        critique_type="epistemic",
    )


def test_review_strictness_changes_effective_verdict():
    assert aggregate([_flag(0.45)], strictness=1.0)["verdict"] == "flag"

    calibrated = aggregate([_flag(0.45)], strictness=0.55)

    assert calibrated["review_threshold"] == 0.48
    assert calibrated["verdict"] == "pass"
    assert calibrated["reviews"][0]["verdict"] == "flag"


def test_normal_system_prompt_is_constructive(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "build_darkroom_context",
        lambda task: "[DARKROOM] constructive",
    )
    monkeypatch.setattr(
        pipeline,
        "check_epistemic_limit_mode",
        lambda task: (False, 0.0),
    )

    system = Secretary(client=object())._build_system("Rozwiń pomysł", "")

    assert "Domyślnie rozwijaj użyteczną możliwość" in system
    assert "bądź naprawdę krytyczny" not in system


def test_no_go_keeps_explicit_hostile_review():
    system = Secretary(client=object())._build_system(
        "Obal hipotezę",
        "",
        no_go=True,
    )

    assert "NO-GO mode" in system
    assert "precise and ruthless" in system


def test_ordinary_review_cannot_exceed_creative_ceiling(monkeypatch):
    profile = dict(disposition.CREATIVE_BASELINE)
    profile["update_count"] = 0
    saved = {}
    monkeypatch.setattr(disposition, "load_profile", lambda: dict(profile))
    monkeypatch.setattr(disposition, "save_profile", lambda value: saved.update(value))

    disposition.apply_approval({
        "review_strictness": {"from": 0.55, "to": 1.0},
        "falsification_preference": {"from": 0.60, "to": 0.95},
    })

    assert saved["review_strictness"] == 0.70
    assert saved["falsification_preference"] == 0.70


def test_single_review_does_not_propose_global_hardening():
    summary = {
        "max_severity": 0.9,
        "verdict": "flag",
        "reviews": [],
    }

    assert pipeline._create_pending_approval(
        summary,
        "one task",
        repeated_patterns=[],
    ) is None
