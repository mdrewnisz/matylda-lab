"""test_v10_counterfactual.py — Tests for v1.0 Counterfactual Room.

Coverage:
  ■ Constitutional   — v1.0 version + 3 new bounds, min_signal >= 2 invariant
  ■ Counterfactual record  — record_counterfactual fields, type filtering
  ■ Counterfactual evaluate — maturity gate, dismiss-wrong, approve-wrong,
                              confounding guard (min_signal + novel_entity),
                              weight_delta sign, already-evaluated skip
  ■ Status / list    — counterfactual_status shape, list_pending_evaluations
  ■ mark_resurfaced  — counter incremented for dismissed pending records
  ■ Consolidation    — approve/dismiss wire CF record, non-trajectory skipped,
                       run_cycle triggers evaluate_counterfactuals
  ■ Server routes    — 2 new endpoints

Run: pytest tests/test_v10_counterfactual.py -v
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def cf_isolated(tmp_path, monkeypatch):
    """Counterfactual Room with isolated tmp_path state file."""
    import matylda_lite.counterfactual_room as cr
    monkeypatch.setattr(cr, "_CF_FILE", tmp_path / "counterfactual_room.json")
    # Prevent real I/O to diary/graph in unit tests
    monkeypatch.setattr(cr, "_count_entities",       lambda: 0)
    monkeypatch.setattr(cr, "_current_entry_count",  lambda stem: 0)
    return cr


@pytest.fixture()
def positive_isolated(tmp_path, monkeypatch):
    import matylda_lite.positive_room as pr
    monkeypatch.setattr(pr, "_POSITIVE_FILE", tmp_path / "positive_room.json")
    return pr


@pytest.fixture()
def sm_isolated(tmp_path, monkeypatch):
    import matylda_lite.sleeping_matylda as sm
    import matylda_lite.sleeping_matylda.consolidation as con
    state_file     = tmp_path / "sleeping_matylda_state.json"
    snapshots_file = tmp_path / "identity_snapshots.json"
    monkeypatch.setattr(sm,  "_STATE_FILE",     state_file)
    monkeypatch.setattr(sm,  "_SNAPSHOTS_FILE", snapshots_file)
    monkeypatch.setattr(con, "_STATE_FILE",     state_file)
    monkeypatch.setattr(con, "_SNAPSHOTS_FILE", snapshots_file)
    return sm


@pytest.fixture()
def diary_isolated(tmp_path, monkeypatch):
    import matylda_lite.diary_manager as dm
    monkeypatch.setattr(dm, "DIARY_DIR",       tmp_path / "diary")
    monkeypatch.setattr(dm, "REFLECTIONS_DIR", tmp_path / "reflections")
    monkeypatch.setattr(dm, "RULES_FILE",      tmp_path / "rules.md")
    monkeypatch.setattr(dm, "NEGATIVE_DIR",    tmp_path / "negative")
    (tmp_path / "diary").mkdir()
    (tmp_path / "reflections").mkdir()
    (tmp_path / "negative").mkdir()


@pytest.fixture()
def homeostasis_isolated(tmp_path, monkeypatch):
    import matylda_lite.homeostasis as hm
    hdir = tmp_path / "homeostasis"
    hdir.mkdir()
    monkeypatch.setattr(hm, "HOMEOSTASIS_DIR", hdir)
    monkeypatch.setattr(hm, "_GOALS_FILE",     hdir / "active_goals.json")
    monkeypatch.setattr(hm, "_BUDGET_FILE",    hdir / "attention_budget.json")
    monkeypatch.setattr(hm, "_FATIGUE_FILE",   hdir / "fatigue.json")
    monkeypatch.setattr(hm, "_STALE_FILE",     hdir / "stale_items.json")


@pytest.fixture()
def kg_isolated(tmp_path, monkeypatch):
    import matylda_lite.knowledge_graph as kg
    monkeypatch.setattr(kg, "GRAPH_FILE", tmp_path / "knowledge_graph.json")


# Helper: build a minimal finding dict
def _finding(ftype: str, stem: str = "ml_basics", tag: str = "supervised",
              entry_count: int = 5) -> dict:
    return {
        "finding_id":  "finding_abc12345",
        "type":        ftype,
        "thread_stem": stem,
        "tags":        [tag],
        "tag":         tag,
        "entry_count": entry_count,
        "confidence":  0.80,
        "state":       "pending",
        "action":      "create_reflection",
    }


# Helper: make an old timestamp (enough days in the past to be mature)
def _old_ts(days: int = 20) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constitutional v1.0
# ─────────────────────────────────────────────────────────────────────────────

class TestConstitutionalV10:

    def test_version_is_1_0(self):
        from matylda_lite.constitutional import CONSTITUTIONAL_VERSION
        assert CONSTITUTIONAL_VERSION == "1.2"

    def test_counterfactual_bounds_present(self):
        from matylda_lite.constitutional import BOUNDS
        assert hasattr(BOUNDS, "counterfactual_evaluation_days")
        assert hasattr(BOUNDS, "counterfactual_min_signal")
        assert hasattr(BOUNDS, "counterfactual_correction_magnitude")

    def test_evaluation_days_positive(self):
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.counterfactual_evaluation_days > 0

    def test_min_signal_gte_2(self):
        """Design constraint from confounding discussion: single entry ≠ real signal."""
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.counterfactual_min_signal >= 2

    def test_correction_magnitude_range(self):
        """Magnitude must be weak — correction should not dominate Positive Room."""
        from matylda_lite.constitutional import BOUNDS
        assert 0.0 < BOUNDS.counterfactual_correction_magnitude < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Counterfactual recording
# ─────────────────────────────────────────────────────────────────────────────

class TestCounterfactualRecord:

    def test_record_approve_reflection_candidate(self, cf_isolated):
        cr     = cf_isolated
        result = cr.record_counterfactual(_finding("reflection_candidate"), "approve")
        assert result["decision"] == "approve"
        assert result["finding_type"] == "reflection_candidate"

    def test_record_dismiss_synthesis_opportunity(self, cf_isolated):
        cr = cf_isolated
        f  = {
            "finding_id":  "finding_syn001",
            "type":        "synthesis_opportunity",
            "tag":         "recursion",
            "threads":     ["stem_a", "stem_b"],
            "confidence":  0.70,
            "state":       "pending",
            "action":      "enqueue_synthesis",
        }
        result = cr.record_counterfactual(f, "dismiss")
        assert result["decision"] == "dismiss"
        assert result["finding_type"] == "synthesis_opportunity"
        assert result["thread_stem"] == "stem_a"  # first thread used

    def test_record_skips_non_trajectory_type(self, cf_isolated):
        """graph_orphan is not a trajectory finding — must return {}."""
        cr     = cf_isolated
        result = cr.record_counterfactual(_finding("graph_orphan"), "approve")
        assert result == {}

    def test_record_has_all_required_fields(self, cf_isolated):
        cr     = cf_isolated
        result = cr.record_counterfactual(_finding("reflection_candidate"), "dismiss")
        required = {
            "counterfactual_id", "finding_id", "finding_type", "decision",
            "decided_at", "thread_stem", "tag",
            "entry_count_at_decision", "entity_count_at_decision",
            "evaluated_at", "entry_count_at_evaluation",
            "thread_entry_delta", "novel_entity_delta",
            "resurfaced_in_cycles", "correction_applied", "weight_delta",
        }
        assert required.issubset(result.keys())

    def test_record_evaluated_at_is_none(self, cf_isolated):
        """A freshly created record is pending — not yet evaluated."""
        cr     = cf_isolated
        result = cr.record_counterfactual(_finding("reflection_candidate"), "approve")
        assert result["evaluated_at"] is None
        assert result["correction_applied"] is False
        assert result["weight_delta"] == 0.0

    def test_record_uses_finding_id(self, cf_isolated):
        cr = cf_isolated
        f  = _finding("reflection_candidate")
        f["finding_id"] = "finding_xyz99"
        result = cr.record_counterfactual(f, "approve")
        assert result["finding_id"] == "finding_xyz99"

    def test_record_persisted_to_file(self, cf_isolated, tmp_path):
        cr = cf_isolated
        cr.record_counterfactual(_finding("reflection_candidate"), "approve")
        raw = json.loads((tmp_path / "counterfactual_room.json").read_text())
        assert len(raw["records"]) == 1

    def test_record_entry_count_copied(self, cf_isolated):
        cr = cf_isolated
        result = cr.record_counterfactual(_finding("reflection_candidate", entry_count=7), "approve")
        assert result["entry_count_at_decision"] == 7


# ─────────────────────────────────────────────────────────────────────────────
# 3. Counterfactual evaluation
# ─────────────────────────────────────────────────────────────────────────────

class TestCounterfactualEvaluate:

    def _inject_record(self, cf_isolated, tmp_path, *, decision: str,
                       decided_at: str | None = None,
                       entry_count_at_decision: int = 3,
                       entity_count_at_decision: int = 0) -> str:
        """Write a raw record to the CF state file and return its counterfactual_id."""
        rec = {
            "counterfactual_id":        "cf_test0001",
            "finding_id":               "finding_test",
            "finding_type":             "reflection_candidate",
            "decision":                 decision,
            "decided_at":               decided_at or _old_ts(20),
            "thread_stem":              "test_stem",
            "tag":                      "test_tag",
            "entry_count_at_decision":  entry_count_at_decision,
            "entity_count_at_decision": entity_count_at_decision,
            "evaluated_at":             None,
            "entry_count_at_evaluation": None,
            "thread_entry_delta":       None,
            "novel_entity_delta":       None,
            "resurfaced_in_cycles":     0,
            "correction_applied":       False,
            "weight_delta":             0.0,
        }
        cf_path = tmp_path / "counterfactual_room.json"
        cf_path.write_text(json.dumps({"records": [rec]}, indent=2))
        return rec["counterfactual_id"]

    def test_immature_record_not_evaluated(self, cf_isolated, tmp_path):
        """Record decided 1 day ago must not be evaluated (needs 14 days)."""
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="dismiss",
                            decided_at=_old_ts(1))
        result = cr.evaluate_counterfactuals(days=14)
        assert result == []

    def test_mature_record_is_evaluated(self, cf_isolated, tmp_path):
        """Record decided 20 days ago (> 14) must get evaluated_at set."""
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="dismiss",
                            decided_at=_old_ts(20))
        result = cr.evaluate_counterfactuals(days=14)
        assert len(result) == 1
        assert result[0]["evaluated_at"] is not None

    def test_already_evaluated_skipped(self, cf_isolated, tmp_path):
        """Second call does not re-evaluate records that already have evaluated_at."""
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="dismiss",
                            decided_at=_old_ts(20))
        first  = cr.evaluate_counterfactuals(days=14)
        second = cr.evaluate_counterfactuals(days=14)
        assert len(first)  == 1
        assert len(second) == 0

    def test_dismiss_wrong_correction_applied(self, cf_isolated, tmp_path, monkeypatch):
        """Dismiss wrong: entry_delta >= min_signal AND novel_entity >= 1 → correction."""
        from matylda_lite.constitutional import BOUNDS
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="dismiss",
                            decided_at=_old_ts(20),
                            entry_count_at_decision=3,
                            entity_count_at_decision=0)
        # Thread now has 3 + min_signal entries, and 2 new entities
        monkeypatch.setattr(cr, "_current_entry_count",
                            lambda stem: 3 + BOUNDS.counterfactual_min_signal)
        monkeypatch.setattr(cr, "_count_entities", lambda: 2)

        result = cr.evaluate_counterfactuals(days=14)
        assert len(result) == 1
        rec = result[0]
        assert rec["correction_applied"] is True
        assert rec["weight_delta"] == pytest.approx(BOUNDS.counterfactual_correction_magnitude)

    def test_dismiss_not_wrong_no_new_entries(self, cf_isolated, tmp_path, monkeypatch):
        """Dismiss NOT wrong: entry_delta < min_signal → no correction."""
        from matylda_lite.constitutional import BOUNDS
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="dismiss",
                            decided_at=_old_ts(20),
                            entry_count_at_decision=3)
        # Only 1 new entry (< min_signal=2)
        monkeypatch.setattr(cr, "_current_entry_count", lambda stem: 4)
        monkeypatch.setattr(cr, "_count_entities", lambda: 5)  # new entities present

        result = cr.evaluate_counterfactuals(days=14)
        assert result[0]["correction_applied"] is False
        assert result[0]["weight_delta"] == 0.0

    def test_dismiss_not_wrong_no_novel_entity(self, cf_isolated, tmp_path, monkeypatch):
        """Confounding guard: entry_delta >= min_signal but novel_entity == 0 → no correction.

        Thread resurfaces ≠ dismissal was wrong if no new entities appeared.
        Could be rumination, not discovery.
        """
        from matylda_lite.constitutional import BOUNDS
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="dismiss",
                            decided_at=_old_ts(20),
                            entry_count_at_decision=3,
                            entity_count_at_decision=5)
        # Enough new entries, but no new entities
        monkeypatch.setattr(cr, "_current_entry_count",
                            lambda stem: 3 + BOUNDS.counterfactual_min_signal)
        monkeypatch.setattr(cr, "_count_entities", lambda: 5)  # no change

        result = cr.evaluate_counterfactuals(days=14)
        assert result[0]["correction_applied"] is False

    def test_approve_wrong_correction_applied(self, cf_isolated, tmp_path, monkeypatch):
        """Approve wrong: thread dead (entry_delta=0 AND novel_entity=0) → correction."""
        from matylda_lite.constitutional import BOUNDS
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="approve",
                            decided_at=_old_ts(20),
                            entry_count_at_decision=5,
                            entity_count_at_decision=10)
        # Nothing new after approval
        monkeypatch.setattr(cr, "_current_entry_count", lambda stem: 5)
        monkeypatch.setattr(cr, "_count_entities", lambda: 10)

        result = cr.evaluate_counterfactuals(days=14)
        assert result[0]["correction_applied"] is True
        assert result[0]["weight_delta"] == pytest.approx(-BOUNDS.counterfactual_correction_magnitude)

    def test_approve_not_wrong_has_entries(self, cf_isolated, tmp_path, monkeypatch):
        """Approve NOT wrong: new entries appeared → no correction."""
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="approve",
                            decided_at=_old_ts(20),
                            entry_count_at_decision=5)
        monkeypatch.setattr(cr, "_current_entry_count", lambda stem: 8)
        monkeypatch.setattr(cr, "_count_entities", lambda: 0)

        result = cr.evaluate_counterfactuals(days=14)
        assert result[0]["correction_applied"] is False

    def test_weight_delta_positive_for_dismiss_correction(self, cf_isolated, tmp_path, monkeypatch):
        """Dismiss wrong → weight_delta > 0 (Positive Room boosted)."""
        from matylda_lite.constitutional import BOUNDS
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="dismiss",
                            decided_at=_old_ts(20))
        monkeypatch.setattr(cr, "_current_entry_count",
                            lambda stem: 3 + BOUNDS.counterfactual_min_signal)
        monkeypatch.setattr(cr, "_count_entities", lambda: 2)

        result = cr.evaluate_counterfactuals(days=14)
        assert result[0]["weight_delta"] > 0.0

    def test_weight_delta_negative_for_approve_correction(self, cf_isolated, tmp_path, monkeypatch):
        """Approve wrong → weight_delta < 0 (Positive Room decayed)."""
        cr = cf_isolated
        self._inject_record(cf_isolated, tmp_path, decision="approve",
                            decided_at=_old_ts(20),
                            entry_count_at_decision=5,
                            entity_count_at_decision=10)
        monkeypatch.setattr(cr, "_current_entry_count", lambda stem: 5)
        monkeypatch.setattr(cr, "_count_entities", lambda: 10)

        result = cr.evaluate_counterfactuals(days=14)
        assert result[0]["weight_delta"] < 0.0

    def test_evaluate_returns_only_newly_evaluated(self, cf_isolated, tmp_path, monkeypatch):
        """evaluate_counterfactuals returns only the records it evaluated this call."""
        cr = cf_isolated
        # Write two records: one mature, one immature
        records = [
            {
                "counterfactual_id": "cf_old", "finding_id": "f1",
                "finding_type": "reflection_candidate", "decision": "dismiss",
                "decided_at": _old_ts(20), "thread_stem": "stem_a", "tag": "t1",
                "entry_count_at_decision": 0, "entity_count_at_decision": 0,
                "evaluated_at": None, "entry_count_at_evaluation": None,
                "thread_entry_delta": None, "novel_entity_delta": None,
                "resurfaced_in_cycles": 0, "correction_applied": False, "weight_delta": 0.0,
            },
            {
                "counterfactual_id": "cf_new", "finding_id": "f2",
                "finding_type": "reflection_candidate", "decision": "dismiss",
                "decided_at": _old_ts(1), "thread_stem": "stem_b", "tag": "t2",
                "entry_count_at_decision": 0, "entity_count_at_decision": 0,
                "evaluated_at": None, "entry_count_at_evaluation": None,
                "thread_entry_delta": None, "novel_entity_delta": None,
                "resurfaced_in_cycles": 0, "correction_applied": False, "weight_delta": 0.0,
            },
        ]
        cf_path = tmp_path / "counterfactual_room.json"
        cf_path.write_text(json.dumps({"records": records}, indent=2))

        result = cr.evaluate_counterfactuals(days=14)
        assert len(result) == 1
        assert result[0]["counterfactual_id"] == "cf_old"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Status and list
# ─────────────────────────────────────────────────────────────────────────────

class TestCounterfactualStatus:

    def test_status_empty_state(self, cf_isolated):
        cr     = cf_isolated
        status = cr.counterfactual_status()
        assert status["total_records"]      == 0
        assert status["pending_evaluation"] == 0
        assert status["evaluated"]          == 0
        assert status["corrections_applied"] == 0

    def test_status_bounds_present(self, cf_isolated):
        cr     = cf_isolated
        status = cr.counterfactual_status()
        assert "evaluation_days"      in status["bounds"]
        assert "min_signal"           in status["bounds"]
        assert "correction_magnitude" in status["bounds"]

    def test_status_counts_correctly(self, cf_isolated, tmp_path, monkeypatch):
        cr = cf_isolated
        # One pending, one already-evaluated-with-correction
        records = [
            {
                "counterfactual_id": "cf_a", "finding_id": "f1",
                "finding_type": "reflection_candidate", "decision": "dismiss",
                "decided_at": _old_ts(20), "thread_stem": "s", "tag": "t",
                "entry_count_at_decision": 0, "entity_count_at_decision": 0,
                "evaluated_at": None, "entry_count_at_evaluation": None,
                "thread_entry_delta": None, "novel_entity_delta": None,
                "resurfaced_in_cycles": 0, "correction_applied": False, "weight_delta": 0.0,
            },
            {
                "counterfactual_id": "cf_b", "finding_id": "f2",
                "finding_type": "reflection_candidate", "decision": "approve",
                "decided_at": _old_ts(30), "thread_stem": "s2", "tag": "t2",
                "entry_count_at_decision": 0, "entity_count_at_decision": 0,
                "evaluated_at": _old_ts(16),
                "entry_count_at_evaluation": 0,
                "thread_entry_delta": 0, "novel_entity_delta": 0,
                "resurfaced_in_cycles": 0, "correction_applied": True, "weight_delta": -0.08,
            },
        ]
        (tmp_path / "counterfactual_room.json").write_text(
            json.dumps({"records": records}, indent=2)
        )
        status = cr.counterfactual_status()
        assert status["total_records"]       == 2
        assert status["pending_evaluation"]  == 1
        assert status["evaluated"]           == 1
        assert status["corrections_applied"] == 1

    def test_list_pending_evaluations_returns_pending_only(self, cf_isolated, tmp_path):
        cr = cf_isolated
        records = [
            {
                "counterfactual_id": "cf_pending", "finding_id": "f1",
                "finding_type": "reflection_candidate", "decision": "dismiss",
                "decided_at": _old_ts(5), "thread_stem": "s", "tag": "t",
                "entry_count_at_decision": 0, "entity_count_at_decision": 0,
                "evaluated_at": None, "entry_count_at_evaluation": None,
                "thread_entry_delta": None, "novel_entity_delta": None,
                "resurfaced_in_cycles": 0, "correction_applied": False, "weight_delta": 0.0,
            },
            {
                "counterfactual_id": "cf_done", "finding_id": "f2",
                "finding_type": "reflection_candidate", "decision": "approve",
                "decided_at": _old_ts(30), "thread_stem": "s2", "tag": "t2",
                "entry_count_at_decision": 0, "entity_count_at_decision": 0,
                "evaluated_at": _old_ts(16),
                "entry_count_at_evaluation": 3,
                "thread_entry_delta": 3, "novel_entity_delta": 0,
                "resurfaced_in_cycles": 0, "correction_applied": False, "weight_delta": 0.0,
            },
        ]
        (tmp_path / "counterfactual_room.json").write_text(
            json.dumps({"records": records}, indent=2)
        )
        pending = cr.list_pending_evaluations()
        assert len(pending) == 1
        assert pending[0]["counterfactual_id"] == "cf_pending"


# ─────────────────────────────────────────────────────────────────────────────
# 5. mark_resurfaced
# ─────────────────────────────────────────────────────────────────────────────

class TestMarkResurfaced:

    def _write_records(self, tmp_path, records: list[dict]) -> None:
        (tmp_path / "counterfactual_room.json").write_text(
            json.dumps({"records": records}, indent=2)
        )

    def _base_record(self, cf_id: str, decision: str, stem: str, tag: str,
                     evaluated: bool = False) -> dict:
        return {
            "counterfactual_id": cf_id,
            "finding_id": "f_x",
            "finding_type": "reflection_candidate",
            "decision": decision,
            "decided_at": _old_ts(5),
            "thread_stem": stem,
            "tag": tag,
            "entry_count_at_decision": 0,
            "entity_count_at_decision": 0,
            "evaluated_at": _old_ts(1) if evaluated else None,
            "entry_count_at_evaluation": None,
            "thread_entry_delta": None,
            "novel_entity_delta": None,
            "resurfaced_in_cycles": 0,
            "correction_applied": False,
            "weight_delta": 0.0,
        }

    def test_mark_resurfaced_increments_counter(self, cf_isolated, tmp_path):
        cr = cf_isolated
        self._write_records(tmp_path, [
            self._base_record("cf_1", "dismiss", "stem_a", "tag_a"),
        ])
        n = cr.mark_resurfaced("stem_a", "tag_a")
        assert n == 1
        raw = json.loads((tmp_path / "counterfactual_room.json").read_text())
        assert raw["records"][0]["resurfaced_in_cycles"] == 1

    def test_mark_resurfaced_skips_approved_records(self, cf_isolated, tmp_path):
        """Approved records don't track resurfacing (only dismissed ones do)."""
        cr = cf_isolated
        self._write_records(tmp_path, [
            self._base_record("cf_1", "approve", "stem_a", "tag_a"),
        ])
        n = cr.mark_resurfaced("stem_a", "tag_a")
        assert n == 0

    def test_mark_resurfaced_skips_evaluated_records(self, cf_isolated, tmp_path):
        """Already-evaluated records are not updated by mark_resurfaced."""
        cr = cf_isolated
        self._write_records(tmp_path, [
            self._base_record("cf_1", "dismiss", "stem_a", "tag_a", evaluated=True),
        ])
        n = cr.mark_resurfaced("stem_a", "tag_a")
        assert n == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Consolidation integration
# ─────────────────────────────────────────────────────────────────────────────

class TestConsolidationIntegration:

    def _pending_finding(self, ftype: str, stem: str = "ml_basics",
                         tag: str = "supervised") -> dict:
        """Insert a pending finding into sleeping_matylda state and return it."""
        return {
            "finding_id":  "finding_int001",
            "type":        ftype,
            "thread_stem": stem,
            "tags":        [tag],
            "tag":         tag,
            "entry_count": 5,
            "confidence":  0.80,
            "state":       "pending",
            "action":      "create_reflection",
            "title":       "Test finding",
            "description": "Test description",
        }

    def test_approve_records_counterfactual(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """approve_finding must create a counterfactual record with decision='approve'."""
        import matylda_lite.counterfactual_room as cr
        cf_path = tmp_path / "counterfactual_room.json"
        monkeypatch.setattr(cr, "_CF_FILE",              cf_path)
        monkeypatch.setattr(cr, "_count_entities",       lambda: 0)
        monkeypatch.setattr(cr, "_current_entry_count",  lambda stem: 0)

        # Insert finding directly into state
        finding = self._pending_finding("reflection_candidate")
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        # Stub execution to avoid real diary write
        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(con, "_execute_finding", lambda f: "stubbed")

        sm_isolated.approve_finding("finding_int001")

        raw = json.loads(cf_path.read_text())
        assert len(raw["records"]) == 1
        assert raw["records"][0]["decision"] == "approve"

    def test_dismiss_records_counterfactual(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """dismiss_finding must create a counterfactual record with decision='dismiss'."""
        import matylda_lite.counterfactual_room as cr
        cf_path = tmp_path / "counterfactual_room.json"
        monkeypatch.setattr(cr, "_CF_FILE",              cf_path)
        monkeypatch.setattr(cr, "_count_entities",       lambda: 0)
        monkeypatch.setattr(cr, "_current_entry_count",  lambda stem: 0)

        finding = self._pending_finding("synthesis_opportunity")
        finding["threads"] = ["stem_a", "stem_b"]
        del finding["thread_stem"]
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        sm_isolated.dismiss_finding("finding_int001", reason="not relevant")

        raw = json.loads(cf_path.read_text())
        assert len(raw["records"]) == 1
        assert raw["records"][0]["decision"] == "dismiss"

    def test_approve_non_trajectory_finding_not_recorded(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """approve_finding on a graph_orphan must NOT create a CF record."""
        import matylda_lite.counterfactual_room as cr
        cf_path = tmp_path / "counterfactual_room.json"
        monkeypatch.setattr(cr, "_CF_FILE",              cf_path)
        monkeypatch.setattr(cr, "_count_entities",       lambda: 0)
        monkeypatch.setattr(cr, "_current_entry_count",  lambda stem: 0)

        finding = {
            "finding_id":  "finding_int002",
            "type":        "graph_orphan",
            "entity_id":   "entity_001",
            "label":       "orphan entity",
            "kind":        "concept",
            "confidence":  0.60,
            "state":       "pending",
            "action":      "suggest_connection",
            "title":       "Orphan",
            "description": "No relations",
        }
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(con, "_execute_finding", lambda f: "stubbed")

        sm_isolated.approve_finding("finding_int002")

        # CF file should not exist (or have zero records)
        if cf_path.exists():
            raw = json.loads(cf_path.read_text())
            assert len(raw.get("records", [])) == 0

    def test_run_cycle_triggers_evaluate_counterfactuals(
        self,
        sm_isolated,
        tmp_path,
        monkeypatch,
        diary_isolated,
        homeostasis_isolated,
        kg_isolated,
    ):
        """run_cycle must call evaluate_counterfactuals during each cycle."""
        import matylda_lite.counterfactual_room as cr_module

        calls: list[str] = []
        original_evaluate = cr_module.evaluate_counterfactuals

        def _mock_evaluate(days=None):
            calls.append("evaluate_counterfactuals")
            return []

        monkeypatch.setattr(cr_module, "evaluate_counterfactuals", _mock_evaluate)
        monkeypatch.setattr(cr_module, "_CF_FILE",             tmp_path / "cf.json")
        monkeypatch.setattr(cr_module, "_count_entities",      lambda: 0)
        monkeypatch.setattr(cr_module, "_current_entry_count", lambda stem: 0)

        sm_isolated.run_cycle(force=True)

        assert "evaluate_counterfactuals" in calls


# ─────────────────────────────────────────────────────────────────────────────
# 7. Server endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestServerEndpoints:

    @pytest.fixture()
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient
        import matylda_lite.counterfactual_room as cr
        monkeypatch.setattr(cr, "_CF_FILE",             tmp_path / "cf.json")
        monkeypatch.setattr(cr, "_count_entities",      lambda: 0)
        monkeypatch.setattr(cr, "_current_entry_count", lambda stem: 0)
        from matylda_lite.server import app
        return TestClient(app)

    def test_counterfactual_status_endpoint_ok(self, client):
        r = client.get("/api/counterfactual-room/status")
        assert r.status_code == 200
        data = r.json()
        assert "total_records"      in data
        assert "pending_evaluation" in data
        assert "evaluated"          in data
        assert "corrections_applied" in data

    def test_counterfactual_status_has_bounds(self, client):
        r    = client.get("/api/counterfactual-room/status")
        data = r.json()
        assert "bounds" in data
        assert "evaluation_days"      in data["bounds"]
        assert "min_signal"           in data["bounds"]
        assert "correction_magnitude" in data["bounds"]

    def test_counterfactual_pending_endpoint_ok(self, client):
        r    = client.get("/api/counterfactual-room/pending")
        assert r.status_code == 200
        data = r.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_counterfactual_pending_empty_on_fresh_state(self, client):
        r = client.get("/api/counterfactual-room/pending")
        assert r.json()["records"] == []
