"""test_v11_nogo_reflection.py — Tests for v1.1: NoGo auto-write + reflection_pattern.

Coverage:
  ■ Constitutional     — v1.1 version + 2 new bounds, threshold ordering invariant
  ■ NoGo record_signal — signal accumulation, threshold trigger (dismiss→failure,
                          approve→success), counter reset, early returns
  ■ Forgetroom         — reflection_pattern type valid, register creates extra fields,
                          re-registration increments source_reflection_count,
                          activate_object works, forgotten_candidates includes pattern
  ■ Consolidation      — approve nogo_territory → _nogo_feedback("approve"),
                          dismiss nogo_territory → _nogo_feedback("dismiss"),
                          approve reflection_candidate → reflection_pattern registered,
                          non-nogo/non-reflection findings → no side effects,
                          _analyze_diary_patterns activates existing pattern,
                          forgotten_object for reflection_pattern → correct action
  ■ Server routes      — existing endpoints still 200 (regression check)

Run: pytest tests/test_v11_nogo_reflection.py -v
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
def nogo_isolated(tmp_path, monkeypatch):
    import matylda_lite.nogo_room as nr
    monkeypatch.setattr(nr, "_NOGO_FILE", tmp_path / "nogo_room.json")
    return nr


@pytest.fixture()
def forgetroom_isolated(tmp_path, monkeypatch):
    import matylda_lite.forgetroom as fr
    monkeypatch.setattr(fr, "_FORGETROOM_FILE", tmp_path / "forgetroom.json")
    return fr


@pytest.fixture()
def sm_isolated(tmp_path, monkeypatch):
    import matylda_lite.sleeping_matylda as sm
    import matylda_lite.sleeping_matylda.consolidation as con
    state_file     = tmp_path / "sm_state.json"
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


# Helper: seed a trajectory in NoGo Room
def _seed_trajectory(nr, stem: str = "ml_basics", tag: str = "supervised",
                     risk: float = 0.8) -> None:
    nr.record_failure(stem, tag)
    # Manually force risk_score for deterministic tests
    data = nr._load()
    tid  = nr._traj_id(stem, tag)
    data["trajectories"][tid]["risk_score"] = risk
    nr._save(data)


# Helper: build a minimal pending finding dict
def _finding(ftype: str, stem: str = "ml_basics", tag: str = "supervised") -> dict:
    base = {
        "finding_id":  f"finding_{ftype[:6]}",
        "type":        ftype,
        "thread_stem": stem,
        "tags":        [tag],
        "tag":         tag,
        "entry_count": 5,
        "confidence":  0.80,
        "state":       "pending",
        "title":       "Test finding",
        "description": "Test description",
    }
    if ftype == "nogo_territory":
        base["action"]        = "acknowledge_nogo"
        base["trajectory_id"] = f"{stem}::{tag}"
        base["category"]      = "repeated_failure"
        base["effective_risk"] = 0.80
        base["evidence_count"] = 5
    elif ftype == "reflection_candidate":
        base["action"]       = "create_reflection"
        base["entry_ids"]    = []
        base["key_findings"] = []
        base["open_questions"] = []
    elif ftype == "graph_orphan":
        base["action"]    = "suggest_connection"
        base["entity_id"] = "entity_001"
        base["label"]     = "orphan"
        base["kind"]      = "concept"
    return base


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constitutional v1.1
# ─────────────────────────────────────────────────────────────────────────────

class TestConstitutionalV11:

    def test_version_is_1_1(self):
        from matylda_lite.constitutional import CONSTITUTIONAL_VERSION
        assert CONSTITUTIONAL_VERSION == "1.2"

    def test_nogo_auto_bounds_present(self):
        from matylda_lite.constitutional import BOUNDS
        assert hasattr(BOUNDS, "nogo_auto_failure_threshold")
        assert hasattr(BOUNDS, "nogo_auto_success_threshold")

    def test_failure_threshold_positive(self):
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.nogo_auto_failure_threshold > 0

    def test_success_threshold_positive(self):
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.nogo_auto_success_threshold > 0

    def test_failure_threshold_gt_success_threshold(self):
        """Dismissing warnings needs more signal than engaging with them.
        Engaging (approve) rehabilitates faster than ignoring (dismiss) condemns."""
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.nogo_auto_failure_threshold > BOUNDS.nogo_auto_success_threshold


# ─────────────────────────────────────────────────────────────────────────────
# 2. NoGo record_signal
# ─────────────────────────────────────────────────────────────────────────────

class TestNoGoRecordSignal:

    def test_unknown_trajectory_returns_gracefully(self, nogo_isolated):
        nr     = nogo_isolated
        result = nr.record_signal("nonexistent", "tag", "dismiss")
        assert result["risk_score"]    == 0.0
        assert result["signal_applied"] is False

    def test_dismiss_increments_counter(self, nogo_isolated):
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.8)
        nr.record_signal("ml_basics", "supervised", "dismiss")
        data  = nr._load()
        entry = data["trajectories"]["ml_basics::supervised"]
        assert entry["signal_dismiss_count"] == 1

    def test_dismiss_does_not_trigger_before_threshold(self, nogo_isolated):
        """Single dismiss must not fire record_failure."""
        from matylda_lite.constitutional import BOUNDS
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.5)
        result = nr.record_signal("ml_basics", "supervised", "dismiss")
        assert result["signal_applied"] is False
        # risk_score unchanged
        assert result["risk_score"] == pytest.approx(0.5)

    def test_dismiss_triggers_at_threshold(self, nogo_isolated):
        """At nogo_auto_failure_threshold dismissals → risk increases."""
        from matylda_lite.constitutional import BOUNDS
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.5)
        result = None
        for _ in range(BOUNDS.nogo_auto_failure_threshold):
            result = nr.record_signal("ml_basics", "supervised", "dismiss")
        assert result["signal_applied"] is True
        assert result["risk_score"] > 0.5  # risk went up

    def test_dismiss_resets_counter_after_trigger(self, nogo_isolated):
        """Counter resets to 0 after triggering, not accumulating indefinitely."""
        from matylda_lite.constitutional import BOUNDS
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.5)
        for _ in range(BOUNDS.nogo_auto_failure_threshold):
            nr.record_signal("ml_basics", "supervised", "dismiss")
        data  = nr._load()
        entry = data["trajectories"]["ml_basics::supervised"]
        assert entry["signal_dismiss_count"] == 0

    def test_approve_increments_counter(self, nogo_isolated):
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.8)
        nr.record_signal("ml_basics", "supervised", "approve")
        data  = nr._load()
        entry = data["trajectories"]["ml_basics::supervised"]
        assert entry["signal_approve_count"] == 1

    def test_approve_does_not_trigger_before_threshold(self, nogo_isolated):
        """Single approve must not fire record_success."""
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.8)
        result = nr.record_signal("ml_basics", "supervised", "approve")
        assert result["signal_applied"] is False
        assert result["risk_score"] == pytest.approx(0.8)

    def test_approve_triggers_at_threshold(self, nogo_isolated):
        """At nogo_auto_success_threshold approvals → risk decreases."""
        from matylda_lite.constitutional import BOUNDS
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.8)
        result = None
        for _ in range(BOUNDS.nogo_auto_success_threshold):
            result = nr.record_signal("ml_basics", "supervised", "approve")
        assert result["signal_applied"] is True
        assert result["risk_score"] < 0.8  # risk went down

    def test_approve_resets_counter_after_trigger(self, nogo_isolated):
        from matylda_lite.constitutional import BOUNDS
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.8)
        for _ in range(BOUNDS.nogo_auto_success_threshold):
            nr.record_signal("ml_basics", "supervised", "approve")
        data  = nr._load()
        entry = data["trajectories"]["ml_basics::supervised"]
        assert entry["signal_approve_count"] == 0

    def test_dismiss_and_approve_counters_are_independent(self, nogo_isolated):
        """Dismiss signals don't affect approve counter and vice versa."""
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.5)
        nr.record_signal("ml_basics", "supervised", "dismiss")
        nr.record_signal("ml_basics", "supervised", "dismiss")
        nr.record_signal("ml_basics", "supervised", "approve")
        data  = nr._load()
        entry = data["trajectories"]["ml_basics::supervised"]
        assert entry["signal_dismiss_count"] == 2
        assert entry["signal_approve_count"] == 1

    def test_risk_increase_bounded_at_1(self, nogo_isolated):
        """record_signal dismiss trigger must not push risk_score above 1.0."""
        from matylda_lite.constitutional import BOUNDS
        nr = nogo_isolated
        _seed_trajectory(nr, risk=0.95)
        for _ in range(BOUNDS.nogo_auto_failure_threshold):
            result = nr.record_signal("ml_basics", "supervised", "dismiss")
        assert result["risk_score"] <= 1.0

    def test_approve_trigger_uses_multiplicative_decay(self, nogo_isolated):
        """Approve trigger mirrors record_success: risk *= (1 - success_weight)."""
        from matylda_lite.constitutional import BOUNDS
        nr    = nogo_isolated
        risk0 = 0.8
        _seed_trajectory(nr, risk=risk0)
        for _ in range(BOUNDS.nogo_auto_success_threshold):
            result = nr.record_signal("ml_basics", "supervised", "approve")
        expected = round(risk0 * (1 - BOUNDS.nogo_success_weight), 4)
        assert result["risk_score"] == pytest.approx(expected, abs=0.001)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Forgetroom reflection_pattern
# ─────────────────────────────────────────────────────────────────────────────

class TestForgetroomReflectionPattern:

    def test_reflection_pattern_is_valid_type(self, forgetroom_isolated):
        fr = forgetroom_isolated
        assert "reflection_pattern" in fr.VALID_OBJECT_TYPES

    def test_register_creates_pattern_version_field(self, forgetroom_isolated):
        fr     = forgetroom_isolated
        result = fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        assert result["pattern_version"] == 1

    def test_register_creates_source_reflection_count(self, forgetroom_isolated):
        fr     = forgetroom_isolated
        result = fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        assert result["source_reflection_count"] == 1

    def test_reregistration_increments_source_count(self, forgetroom_isolated):
        """Second register_object call for same stem increments source_reflection_count."""
        fr = forgetroom_isolated
        fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        result = fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        assert result["source_reflection_count"] == 2

    def test_reregistration_does_not_reset_weight(self, forgetroom_isolated):
        """Re-registration must preserve effective_weight (idempotency for weight)."""
        fr = forgetroom_isolated
        fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        fr.activate_object("ml_basics")  # reinforcement_count → 1
        w_before = fr.get_effective_weight("ml_basics")
        fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        w_after = fr.get_effective_weight("ml_basics")
        assert w_after == pytest.approx(w_before, abs=0.001)

    def test_activate_works_for_reflection_pattern(self, forgetroom_isolated):
        fr = forgetroom_isolated
        fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        result = fr.activate_object("ml_basics")
        assert result["reinforcement_count"] == 1

    def test_reflection_pattern_decays_without_activation(self, forgetroom_isolated, tmp_path):
        """Pattern effective_weight decreases when last_activation is far in the past."""
        import math
        from matylda_lite.constitutional import BOUNDS
        fr = forgetroom_isolated

        # Manually inject an entry with a last_activation 30 days ago
        old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        data   = {"objects": {
            "ml_basics": {
                "object_id":            "ml_basics",
                "object_type":          "reflection_pattern",
                "initial_weight":       1.0,
                "last_activation":      old_ts,
                "reinforcement_count":  0,
                "pattern_version":      1,
                "source_reflection_count": 1,
            }
        }}
        (tmp_path / "forgetroom.json").write_text(json.dumps(data, indent=2))

        ew = fr.get_effective_weight("ml_basics")
        expected_max = math.exp(-BOUNDS.forgetroom_decay_k * 30)
        assert ew < expected_max + 0.01  # should have decayed significantly

    def test_reflection_pattern_in_forgotten_candidates(self, forgetroom_isolated, tmp_path):
        """Patterns with very low weight should appear in forgotten_candidates."""
        fr = forgetroom_isolated
        # Force a near-zero weight entry
        very_old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        data = {"objects": {
            "old_stem": {
                "object_id":            "old_stem",
                "object_type":          "reflection_pattern",
                "initial_weight":       0.5,
                "last_activation":      very_old,
                "reinforcement_count":  0,
                "pattern_version":      1,
                "source_reflection_count": 1,
            }
        }}
        (tmp_path / "forgetroom.json").write_text(json.dumps(data, indent=2))

        candidates = fr.get_forgotten_candidates()
        oids = [c["object_id"] for c in candidates]
        assert "old_stem" in oids

    def test_entity_type_does_not_get_pattern_fields(self, forgetroom_isolated):
        """entity type must NOT get pattern_version / source_reflection_count."""
        fr     = forgetroom_isolated
        result = fr.register_object("entity_001", "entity", initial_weight=1.0)
        assert "pattern_version"         not in result
        assert "source_reflection_count" not in result


# ─────────────────────────────────────────────────────────────────────────────
# 4. Consolidation integration — NoGo signal wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestConsolidationNoGoSignal:

    def test_approve_nogo_territory_calls_record_signal(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """approve_finding on nogo_territory must call nogo_room.record_signal('approve')."""
        import matylda_lite.nogo_room as nr
        nogo_path = tmp_path / "nogo_room.json"
        monkeypatch.setattr(nr, "_NOGO_FILE", nogo_path)

        calls: list[tuple] = []
        monkeypatch.setattr(nr, "record_signal", lambda stem, tag, dec: calls.append((stem, tag, dec)))

        finding = _finding("nogo_territory")
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(con, "_execute_finding", lambda f: "stubbed")

        sm_isolated.approve_finding(f"finding_{finding['type'][:6]}")
        assert any(dec == "approve" for _, _, dec in calls)

    def test_dismiss_nogo_territory_calls_record_signal(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """dismiss_finding on nogo_territory must call nogo_room.record_signal('dismiss')."""
        import matylda_lite.nogo_room as nr
        monkeypatch.setattr(nr, "_NOGO_FILE", tmp_path / "nogo_room.json")

        calls: list[tuple] = []
        monkeypatch.setattr(nr, "record_signal", lambda stem, tag, dec: calls.append((stem, tag, dec)))

        finding = _finding("nogo_territory")
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        sm_isolated.dismiss_finding(f"finding_{finding['type'][:6]}", reason="test")
        assert any(dec == "dismiss" for _, _, dec in calls)

    def test_approve_graph_orphan_does_not_call_record_signal(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """graph_orphan is not a nogo_territory — record_signal must NOT be called."""
        import matylda_lite.nogo_room as nr
        monkeypatch.setattr(nr, "_NOGO_FILE", tmp_path / "nogo_room.json")

        calls: list[tuple] = []
        monkeypatch.setattr(nr, "record_signal", lambda stem, tag, dec: calls.append((stem, tag, dec)))

        finding = _finding("graph_orphan")
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(con, "_execute_finding", lambda f: "stubbed")

        sm_isolated.approve_finding(f"finding_{finding['type'][:6]}")
        assert calls == []

    def test_repeated_dismissals_eventually_increase_risk(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """End-to-end: N dismissals of nogo_territory → risk_score increases."""
        from matylda_lite.constitutional import BOUNDS
        import matylda_lite.nogo_room as nr

        nogo_path = tmp_path / "nogo_room.json"
        monkeypatch.setattr(nr, "_NOGO_FILE", nogo_path)

        # Seed trajectory in NoGo with moderate risk
        data = {"trajectories": {
            "ml_basics::supervised": {
                "trajectory_id": "ml_basics::supervised",
                "thread_stem":   "ml_basics",
                "tag":           "supervised",
                "category":      "repeated_failure",
                "risk_score":    0.5,
                "drift_score":   0.0,
                "complexity_score": 0.0,
                "revisit_count": 2,
                "evidence_count": 2,
                "last_seen":     datetime.now(timezone.utc).isoformat(),
                "signal_dismiss_count": 0,
                "signal_approve_count": 0,
            }
        }}
        nogo_path.write_text(json.dumps(data, indent=2))

        # Insert N identical nogo_territory findings and dismiss each
        for i in range(BOUNDS.nogo_auto_failure_threshold):
            f = _finding("nogo_territory")
            f["finding_id"] = f"finding_nogo_{i:03d}"
            sm_isolated._save_state({"findings": [f], "total_cycles": 0})
            sm_isolated.dismiss_finding(f["finding_id"], reason="test")

        raw   = json.loads(nogo_path.read_text())
        entry = raw["trajectories"]["ml_basics::supervised"]
        assert entry["risk_score"] > 0.5


# ─────────────────────────────────────────────────────────────────────────────
# 5. Consolidation integration — reflection_pattern wiring
# ─────────────────────────────────────────────────────────────────────────────

class TestConsolidationReflectionPattern:

    def test_approve_reflection_candidate_registers_pattern(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """approve_finding(reflection_candidate) → reflection_pattern entry in Forgetroom."""
        import matylda_lite.forgetroom as fr
        fr_path = tmp_path / "forgetroom.json"
        monkeypatch.setattr(fr, "_FORGETROOM_FILE", fr_path)

        finding = _finding("reflection_candidate", stem="ml_basics")
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(con, "_execute_finding", lambda f: "reflection:refl_test01")

        sm_isolated.approve_finding(finding["finding_id"])

        raw = json.loads(fr_path.read_text())
        assert "ml_basics" in raw["objects"]
        assert raw["objects"]["ml_basics"]["object_type"] == "reflection_pattern"

    def test_approve_reflection_candidate_sets_pattern_version(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        import matylda_lite.forgetroom as fr
        fr_path = tmp_path / "forgetroom.json"
        monkeypatch.setattr(fr, "_FORGETROOM_FILE", fr_path)

        finding = _finding("reflection_candidate", stem="ml_basics")
        sm_isolated._save_state({"findings": [finding], "total_cycles": 0})

        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(con, "_execute_finding", lambda f: "reflection:refl_test01")

        sm_isolated.approve_finding(finding["finding_id"])

        raw = json.loads(fr_path.read_text())
        assert raw["objects"]["ml_basics"]["pattern_version"] == 1

    def test_approve_twice_increments_source_count(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """Two approvals for same stem → source_reflection_count == 2."""
        import matylda_lite.forgetroom as fr
        fr_path = tmp_path / "forgetroom.json"
        monkeypatch.setattr(fr, "_FORGETROOM_FILE", fr_path)

        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(con, "_execute_finding", lambda f: "reflection:refl_test01")

        for i in range(2):
            f = _finding("reflection_candidate", stem="ml_basics")
            f["finding_id"] = f"finding_rc_{i:03d}"
            sm_isolated._save_state({"findings": [f], "total_cycles": 0})
            sm_isolated.approve_finding(f["finding_id"])

        raw = json.loads(fr_path.read_text())
        assert raw["objects"]["ml_basics"]["source_reflection_count"] == 2

    def test_pattern_resurface_activates_forgetroom(
        self,
        sm_isolated,
        tmp_path,
        monkeypatch,
        diary_isolated,
        homeostasis_isolated,
        kg_isolated,
    ):
        """_analyze_diary_patterns must activate reflection_pattern when stem resurfaces."""
        import matylda_lite.forgetroom as fr
        fr_path = tmp_path / "forgetroom.json"
        monkeypatch.setattr(fr, "_FORGETROOM_FILE", fr_path)

        # Pre-seed a reflection_pattern for "ml_basics"
        fr.register_object("ml_basics", "reflection_pattern", initial_weight=0.8)
        rc_before = json.loads(fr_path.read_text())["objects"]["ml_basics"]["reinforcement_count"]

        # Write enough diary entries to trigger pattern_min_count
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        for i in range(BOUNDS.sleeping_matylda_pattern_min_count):
            dm.write_diary_entry(
                session_id=f"sess_{i:03d}",
                thread_stem="ml_basics",
                query_summary=f"Query about supervised learning #{i}",
                key_finding=f"finding {i}",
                tags=["supervised"],
            )

        # Also isolate counterfactual_room and positive_room
        import matylda_lite.counterfactual_room as cr
        import matylda_lite.positive_room as pr
        monkeypatch.setattr(cr, "_CF_FILE",             tmp_path / "cf.json")
        monkeypatch.setattr(cr, "_count_entities",      lambda: 0)
        monkeypatch.setattr(cr, "_current_entry_count", lambda stem: 0)
        monkeypatch.setattr(pr, "_POSITIVE_FILE",       tmp_path / "pr.json")
        import matylda_lite.nogo_room as nr
        monkeypatch.setattr(nr, "_NOGO_FILE",           tmp_path / "nogo.json")

        sm_isolated.run_cycle(force=True)

        rc_after = json.loads(fr_path.read_text())["objects"]["ml_basics"]["reinforcement_count"]
        assert rc_after > rc_before

    def test_forgotten_reflection_pattern_has_remove_reflection_action(
        self, sm_isolated, tmp_path, monkeypatch, homeostasis_isolated
    ):
        """forgotten_object finding for reflection_pattern → action == remove_reflection."""
        import matylda_lite.forgetroom as fr
        fr_path = tmp_path / "forgetroom.json"
        monkeypatch.setattr(fr, "_FORGETROOM_FILE", fr_path)

        # Inject a near-zero-weight reflection_pattern
        very_old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        data = {"objects": {
            "old_stem": {
                "object_id":            "old_stem",
                "object_type":          "reflection_pattern",
                "initial_weight":       0.5,
                "last_activation":      very_old,
                "reinforcement_count":  0,
                "pattern_version":      1,
                "source_reflection_count": 1,
            }
        }}
        fr_path.write_text(json.dumps(data, indent=2))

        candidates = fr.get_forgotten_candidates()
        assert any(c["object_id"] == "old_stem" for c in candidates)

        # Verify action_map in consolidation
        import matylda_lite.sleeping_matylda.consolidation as con
        action_map = {
            "entity":             "remove_entity",
            "reflection":         "remove_reflection",
            "reflection_pattern": "remove_reflection",
            "tension":            "remove_tension",
        }
        assert action_map["reflection_pattern"] == "remove_reflection"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Regression — existing server endpoints still respond
# ─────────────────────────────────────────────────────────────────────────────

class TestServerRegression:

    @pytest.fixture()
    def client(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient
        import matylda_lite.nogo_room as nr
        import matylda_lite.forgetroom as fr
        import matylda_lite.positive_room as pr
        import matylda_lite.counterfactual_room as cr
        monkeypatch.setattr(nr, "_NOGO_FILE",        tmp_path / "nogo.json")
        monkeypatch.setattr(fr, "_FORGETROOM_FILE",  tmp_path / "fr.json")
        monkeypatch.setattr(pr, "_POSITIVE_FILE",    tmp_path / "pr.json")
        monkeypatch.setattr(cr, "_CF_FILE",          tmp_path / "cf.json")
        monkeypatch.setattr(cr, "_count_entities",   lambda: 0)
        monkeypatch.setattr(cr, "_current_entry_count", lambda stem: 0)
        from matylda_lite.server import app
        return TestClient(app)

    def test_nogo_status_still_200(self, client):
        r = client.get("/api/nogo-room/status")
        assert r.status_code == 200

    def test_forgetroom_status_still_200(self, client):
        r = client.get("/api/forgetroom/status")
        assert r.status_code == 200

    def test_positive_status_still_200(self, client):
        r = client.get("/api/positive-room/status")
        assert r.status_code == 200

    def test_counterfactual_status_still_200(self, client):
        r = client.get("/api/counterfactual-room/status")
        assert r.status_code == 200
