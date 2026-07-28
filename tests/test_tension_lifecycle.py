"""Tests for the tension lifecycle policy (2026-06-21).

Policy:
  - trivial queries        → never create a tension
  - ordinary (sev < 0.8)   → auto-archive after 30 days
  - critical (sev ≥ 0.8)   → stay until the operator decides
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from matylda_lite.darkroom import tension as T


# ── Trivial-query blocking (creation guard) ──────────────────────────────────

@pytest.mark.parametrize("query,expected", [
    ("1+1=?", True),
    ("Co to jest haiku? 1 zdanie.", True),
    ("odpowiedz: ile to 2*3", True),
    ("", True),
    ("   ", True),
    ("Przeanalizuj klauzule abuzywne w umowie deweloperskiej pod kątem art. 385 KC", False),
    ("Zbadaj czy hipoteza przepustowości odróżnień jest falsyfikowalna empirycznie", False),
])
def test_is_trivial_query(query, expected):
    assert T.is_trivial_query(query) is expected


# ── Aging rule (critical exempt, medium expires) ─────────────────────────────

def _tension(severity, age_days):
    created = (date.today() - timedelta(days=age_days)).isoformat()
    return {"severity": severity, "created": created, "review_count": 0}


def test_critical_never_ages_out():
    # severity >= 0.8 stays no matter how old
    assert T._should_age_out(_tension(0.8, 999)) is False
    assert T._should_age_out(_tension(0.95, 999)) is False


def test_medium_ages_out_after_30_days():
    assert T._should_age_out(_tension(0.5, 31)) is True
    assert T._should_age_out(_tension(0.5, 30)) is True


def test_medium_survives_before_30_days():
    assert T._should_age_out(_tension(0.5, 29)) is False
    assert T._should_age_out(_tension(0.3, 10)) is False


def test_aging_threshold_is_strictly_below_critical():
    # 0.79 ages out, 0.80 is critical
    assert T._should_age_out(_tension(0.79, 40)) is True
    assert T._should_age_out(_tension(0.80, 40)) is False


def test_malformed_created_date_is_safe():
    assert T._should_age_out({"severity": 0.4, "created": "not-a-date"}) is False


# ── Contextual injection (DARKROOM de-escalator) ─────────────────────────────

def test_select_for_task_excludes_unrelated_historical_tensions():
    tensions = [
        {"description": "Niedookreślona hipoteza kwantowej grawitacji", "source_task": "badanie grawitacji", "severity": 0.9},
        {"description": "Brak źródła dla umowy deweloperskiej", "source_task": "analiza umowy", "severity": 0.9},
    ]

    selected = T.select_for_task("Przetestuj hipotezę grawitacji kwantowej", tensions)

    assert selected == [tensions[0]]


def test_select_for_task_caps_context_to_three_tensions():
    tensions = [
        {"description": f"Hipoteza fotonowa wariant {i}", "source_task": "hipoteza fotonowa", "severity": i / 10}
        for i in range(1, 6)
    ]

    selected = T.select_for_task("Rozwiń hipoteza fotonowa", tensions, limit=3)

    assert len(selected) == 3
    assert [item["severity"] for item in selected] == [0.5, 0.4, 0.3]


def test_task_scoped_epistemic_mode_ignores_unrelated_registry(monkeypatch):
    from matylda_lite.darkroom import pipeline

    active = [{"description": "Kwantowa hipoteza", "source_task": "grawitacja", "severity": 0.9}]
    monkeypatch.setattr(pipeline.tens, "load_active", lambda: active)
    monkeypatch.setattr(pipeline.tens, "select_for_task", lambda task, limit: [])

    assert pipeline.check_epistemic_limit_mode(task="analiza umowy") == (False, 0)
    assert pipeline.check_epistemic_limit_mode() == (True, 0.9)
