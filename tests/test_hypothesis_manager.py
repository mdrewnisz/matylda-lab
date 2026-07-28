"""Regression tests for the explicit Matylda Lab hypothesis lifecycle."""
from __future__ import annotations

import pytest

from matylda_lite import hypothesis_manager as hm


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    path = tmp_path / "hypotheses.json"
    monkeypatch.setattr(hm, "REGISTRY_FILE", path)
    return path


def test_lifecycle_requires_context_before_waiting_or_burial(registry):
    record = hm.create_hypothesis("Nieoczywista korelacja")
    record = hm.transition_hypothesis(record["id"], "incubator")
    record = hm.transition_hypothesis(record["id"], "exploration")
    record = hm.transition_hypothesis(record["id"], "working_model")

    with pytest.raises(ValueError, match="current_evidence"):
        hm.transition_hypothesis(record["id"], "waiting_room")

    waiting = hm.transition_hypothesis(record["id"], "waiting_room", {
        "current_evidence": "Dwie obserwacje, bez kontroli.",
        "missing_test": "Porównanie z grupą kontrolną.",
        "reentry_condition": "Pojawią się dane porównawcze.",
        "review_date": "2026-08-01",
    })
    with pytest.raises(ValueError, match="cemetery_reason"):
        hm.transition_hypothesis(waiting["id"], "cemetery")


def test_revival_creates_a_linked_new_working_model(registry):
    record = hm.create_hypothesis("Hipoteza do sprawdzenia")
    record = hm.transition_hypothesis(record["id"], "cemetery", {
        "cemetery_reason": "Sprzeczna z wynikiem testu.",
        "cemetery_record": "test-17",
    })
    revived = hm.revive_hypothesis(record["id"])

    assert revived["state"] == "working_model"
    assert revived["parent_id"] == record["id"]
    assert revived["id"] != record["id"]


def test_waiting_focus_is_capped_at_seven(registry):
    for number in range(8):
        record = hm.create_hypothesis(f"Hipoteza {number}")
        record = hm.transition_hypothesis(record["id"], "incubator")
        record = hm.transition_hypothesis(record["id"], "exploration")
        record = hm.transition_hypothesis(record["id"], "working_model")
        hm.transition_hypothesis(record["id"], "waiting_room", {
            "current_evidence": "Wstępna obserwacja.",
            "missing_test": "Prosty test.",
            "reentry_condition": "Nowe dane.",
            "review_date": "2026-08-01",
        })

    result = hm.overview()
    assert len(result["focus_waiting"]) == 7
    assert result["waiting_overflow"] == 1


def test_hypothesis_api_connects_the_lab_dashboard_to_the_registry(client, registry):
    created = client.post("/api/hypotheses", json={
        "title": "Hipoteza przez API",
        "fields": {"exploration_cost": "5 min"},
    })
    assert created.status_code == 200
    record = created.json()["hypothesis"]
    assert record["state"] == "seed"

    overview = client.get("/api/hypotheses")
    assert overview.status_code == 200
    assert overview.json()["by_state"]["seed"][0]["id"] == record["id"]
