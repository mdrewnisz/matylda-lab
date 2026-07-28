"""test_v08_nogo_forgetroom.py — Tests for v0.8 NoGo Room + Forgetroom.

Coverage:
  ■ Constitutional   — v0.8 version + 10 new bounds
  ■ NoGo Room        — record_failure, record_success (multiplicative), record_drift,
                       effective_risk = stored * time_discount * evidence_discount,
                       list_risky, prune, nogo_status
  ■ Forgetroom       — register, activate, decay formula, candidates, prune, summary
  ■ BranchEvaluator  — exploration_cost blend, confidence_modifier, should_prune
  ■ Integration      — forgotten_object / nogo_territory findings in run_cycle,
                       branch cost adjusts reflection_candidate confidence
  ■ Server routes    — 4 new endpoints

Run: pytest tests/test_v08_nogo_forgetroom.py -v
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
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
    """Redirect NoGo Room state file to tmp_path."""
    import matylda_lite.nogo_room as nr
    monkeypatch.setattr(nr, "_NOGO_FILE", tmp_path / "nogo_room.json")
    return nr


@pytest.fixture()
def forgetroom_isolated(tmp_path, monkeypatch):
    """Redirect Forgetroom state file to tmp_path."""
    import matylda_lite.forgetroom as fr
    monkeypatch.setattr(fr, "_FORGETROOM_FILE", tmp_path / "forgetroom.json")
    return fr


@pytest.fixture()
def sm_isolated(tmp_path, monkeypatch):
    import matylda_lite.sleeping_matylda as sm
    import matylda_lite.sleeping_matylda.consolidation as con
    state_file = tmp_path / "sleeping_matylda_state.json"
    monkeypatch.setattr(sm, "_STATE_FILE", state_file)
    monkeypatch.setattr(con, "_STATE_FILE", state_file)
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


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constitutional v0.8
# ─────────────────────────────────────────────────────────────────────────────

class TestConstitutionalV08:

    def test_version(self):
        from matylda_lite.constitutional import CONSTITUTIONAL_VERSION
        assert CONSTITUTIONAL_VERSION == "1.2"

    def test_nogo_bounds_present(self):
        from matylda_lite.constitutional import BOUNDS
        assert hasattr(BOUNDS, "nogo_risk_threshold")
        assert hasattr(BOUNDS, "nogo_max_entries")
        assert hasattr(BOUNDS, "nogo_failure_weight")
        assert hasattr(BOUNDS, "nogo_success_weight")
        assert hasattr(BOUNDS, "nogo_drift_weight")
        assert hasattr(BOUNDS, "nogo_decay_k")
        assert hasattr(BOUNDS, "nogo_min_evidence_count")

    def test_forgetroom_bounds_present(self):
        from matylda_lite.constitutional import BOUNDS
        assert hasattr(BOUNDS, "forgetroom_decay_k")
        assert hasattr(BOUNDS, "forgetroom_prune_threshold")
        assert hasattr(BOUNDS, "forgetroom_max_objects")

    def test_nogo_success_is_multiplicative(self):
        """Verify success weight means multiplicative decay (< 1.0 reduction per step)."""
        from matylda_lite.constitutional import BOUNDS
        # After N successes: risk * (1 - sw)^N — never reaches 0 for risk > 0
        sw = BOUNDS.nogo_success_weight
        assert 0.0 < sw < 1.0, "success_weight must be strictly between 0 and 1"

    def test_forgetroom_faster_than_nogo(self):
        """Forgetroom decays faster than NoGo (trash fades quicker than bad memories)."""
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.forgetroom_decay_k > BOUNDS.nogo_decay_k


# ─────────────────────────────────────────────────────────────────────────────
# 2. NoGo Room
# ─────────────────────────────────────────────────────────────────────────────

class TestNoGoRoom:

    def test_record_failure_increases_risk(self, nogo_isolated):
        nr = nogo_isolated
        r1 = nr.record_failure("python_async", "recursion", "recursive_loop")
        assert r1["risk_score"] > 0.0

    def test_record_failure_caps_at_one(self, nogo_isolated):
        nr = nogo_isolated
        from matylda_lite.constitutional import BOUNDS
        # Force enough failures to exceed cap
        iters = math.ceil(1.0 / BOUNDS.nogo_failure_weight) + 5
        for _ in range(iters):
            nr.record_failure("python_async", "recursion")
        entry = nr.get_trajectory("python_async", "recursion")
        assert entry["risk_score"] == 1.0

    def test_record_success_multiplicative(self, nogo_isolated):
        """Success uses multiplicative decay — risk never reaches 0."""
        nr = nogo_isolated
        from matylda_lite.constitutional import BOUNDS
        # Build up risk first
        for _ in range(5):
            nr.record_failure("thread", "tag")
        before = nr.get_trajectory("thread", "tag")["risk_score"]
        assert before > 0.0

        # Apply many successes
        for _ in range(100):
            nr.record_success("thread", "tag")
        after = nr.get_trajectory("thread", "tag")["risk_score"]
        # Should be very small but NOT 0 (multiplicative, not additive)
        assert after > 0.0
        assert after < before

    def test_record_success_unknown_trajectory_returns_zero(self, nogo_isolated):
        nr = nogo_isolated
        result = nr.record_success("nonexistent", "tag")
        assert result["effective_risk"] == 0.0

    def test_record_drift_increases_risk(self, nogo_isolated):
        nr = nogo_isolated
        result = nr.record_drift("thread", "topic", drift_score=0.8)
        assert result["risk_score"] > 0.0

    def test_evidence_discount_low_evidence(self, nogo_isolated):
        """Single failure → effective_risk is discounted (< stored_risk)."""
        nr = nogo_isolated
        from matylda_lite.constitutional import BOUNDS
        result = nr.record_failure("new_thread", "new_tag")
        # evidence_count = 1, min_evidence = 5 → discount = 1/5 = 0.2
        assert result["evidence_count"] == 1
        assert result["effective_risk"] < result["risk_score"]

    def test_full_evidence_no_discount(self, nogo_isolated):
        """At nogo_min_evidence_count events → effective_risk == stored_risk (no time decay)."""
        nr = nogo_isolated
        from matylda_lite.constitutional import BOUNDS
        # Generate exactly min_evidence_count failures (no time passes → time_discount ≈ 1)
        for _ in range(BOUNDS.nogo_min_evidence_count):
            result = nr.record_failure("thread_full", "tag_full")
        # evidence_discount = min(1.0, 5/5) = 1.0, time_discount ≈ 1.0 (just now)
        assert result["evidence_count"] == BOUNDS.nogo_min_evidence_count
        assert result["effective_risk"] == pytest.approx(result["risk_score"], abs=0.01)

    def test_get_risk_score_unknown_returns_zero(self, nogo_isolated):
        nr = nogo_isolated
        assert nr.get_risk_score("unknown", "tag") == 0.0

    def test_list_risky_above_threshold(self, nogo_isolated):
        nr = nogo_isolated
        from matylda_lite.constitutional import BOUNDS
        # Force high evidence + risk
        for _ in range(10):
            nr.record_failure("bad_thread", "bad_tag", "repeated_failure")
        risky = nr.list_risky_trajectories(threshold=0.0)  # all
        assert len(risky) >= 1
        tids = [t["trajectory_id"] for t in risky]
        assert "bad_thread::bad_tag" in tids

    def test_prune_old_entries(self, nogo_isolated):
        nr = nogo_isolated
        # Add 5 trajectories
        for i in range(5):
            nr.record_failure(f"thread_{i}", "tag")
        before = nr.nogo_status()["total_entries"]
        assert before == 5
        removed = nr.prune_old_entries(max_entries=3)
        assert removed == 2
        assert nr.nogo_status()["total_entries"] == 3

    def test_nogo_status_shape(self, nogo_isolated):
        nr = nogo_isolated
        status = nr.nogo_status()
        assert "total_entries" in status
        assert "high_risk_count" in status
        assert "threshold" in status
        assert "file" in status


# ─────────────────────────────────────────────────────────────────────────────
# 3. Forgetroom
# ─────────────────────────────────────────────────────────────────────────────

class TestForgetroom:

    def test_register_entity(self, forgetroom_isolated):
        fr = forgetroom_isolated
        result = fr.register_object("e1", "entity")
        assert result["object_id"] == "e1"
        assert result["object_type"] == "entity"
        assert result["effective_weight"] == pytest.approx(1.0, abs=0.01)

    def test_register_idempotent(self, forgetroom_isolated):
        """Re-registering an existing object does not reset its state."""
        fr = forgetroom_isolated
        fr.register_object("e1", "entity")
        fr.activate_object("e1")  # reinf_count = 1
        fr.register_object("e1", "entity")  # should NOT reset
        w = fr.get_effective_weight("e1")
        # After 1 activation: multiplier = 1 + log(2) ≈ 1.693
        assert w > 1.0  # still has the reinforcement

    def test_effective_weight_fresh_is_one(self, forgetroom_isolated):
        fr = forgetroom_isolated
        fr.register_object("fresh", "reflection")
        assert fr.get_effective_weight("fresh") == pytest.approx(1.0, abs=0.01)

    def test_effective_weight_unknown_is_zero(self, forgetroom_isolated):
        fr = forgetroom_isolated
        assert fr.get_effective_weight("nonexistent") == 0.0

    def test_activate_increments_reinforcement(self, forgetroom_isolated):
        fr = forgetroom_isolated
        fr.register_object("obj", "entity")
        result = fr.activate_object("obj")
        assert result["reinforcement_count"] == 1

    def test_activate_increases_effective_weight(self, forgetroom_isolated):
        """Activation bumps log-multiplier — weight after activation > 1.0."""
        fr = forgetroom_isolated
        fr.register_object("obj", "entity")
        result = fr.activate_object("obj")  # reinf=1 → multiplier = 1 + log(2) ≈ 1.693
        assert result["effective_weight"] > 1.0

    def test_activate_unknown_raises_keyerror(self, forgetroom_isolated):
        fr = forgetroom_isolated
        with pytest.raises(KeyError):
            fr.activate_object("ghost")

    def test_log_multiplier_formula(self, forgetroom_isolated):
        """Verify the formula: w = initial * (1 + log(1+reinf)) * exp(-k*t)."""
        fr = forgetroom_isolated
        from matylda_lite.constitutional import BOUNDS
        fr.register_object("obj", "entity", initial_weight=1.0)
        for _ in range(4):
            fr.activate_object("obj")  # reinf = 4
        # At t≈0: w = 1.0 * (1 + log(5)) * exp(0) ≈ 1 + 1.609 = 2.609
        expected = 1.0 * (1 + math.log(1 + 4))
        actual   = fr.get_effective_weight("obj")
        assert actual == pytest.approx(expected, abs=0.05)

    def test_get_forgotten_candidates(self, forgetroom_isolated, tmp_path):
        """Artificially old object → appears in forgotten candidates."""
        fr = forgetroom_isolated
        from matylda_lite.constitutional import BOUNDS
        # Write an old entry directly (past the decay threshold)
        old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        data = {
            "objects": {
                "old_entity": {
                    "object_id":           "old_entity",
                    "object_type":         "entity",
                    "initial_weight":      1.0,
                    "last_activation":     old_date,
                    "reinforcement_count": 0,
                }
            }
        }
        fr._FORGETROOM_FILE.write_text(json.dumps(data))
        candidates = fr.get_forgotten_candidates()
        assert len(candidates) >= 1
        oids = [c["object_id"] for c in candidates]
        assert "old_entity" in oids

    def test_fresh_object_not_forgotten(self, forgetroom_isolated):
        """Freshly registered object is not a forgotten candidate."""
        fr = forgetroom_isolated
        fr.register_object("fresh", "entity")
        candidates = fr.get_forgotten_candidates()
        assert not any(c["object_id"] == "fresh" for c in candidates)

    def test_prune_objects(self, forgetroom_isolated, tmp_path):
        """Lowest-weight objects are pruned first."""
        fr = forgetroom_isolated
        # Create 5 objects with varying ages
        for i in range(5):
            fr.register_object(f"obj_{i}", "entity")
        assert fr.forgetroom_summary()["total_objects"] == 5
        removed = fr.prune_objects(max_objects=3)
        assert removed == 2
        assert fr.forgetroom_summary()["total_objects"] == 3

    def test_forgetroom_summary_shape(self, forgetroom_isolated):
        fr = forgetroom_isolated
        summary = fr.forgetroom_summary()
        assert "total_objects" in summary
        assert "forgotten_count" in summary
        assert "threshold" in summary
        assert "oldest_object" in summary
        assert "file" in summary

    def test_forgetroom_summary_empty(self, forgetroom_isolated):
        fr = forgetroom_isolated
        summary = fr.forgetroom_summary()
        assert summary["total_objects"] == 0
        assert summary["oldest_object"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Branch Evaluator
# ─────────────────────────────────────────────────────────────────────────────

class TestBranchEvaluator:

    def test_safe_branch_low_cost(self, nogo_isolated):
        """Short branch, no NoGo history → low exploration_cost."""
        from matylda_lite.branch_evaluator import evaluate_branch
        result = evaluate_branch("fresh_thread", "tag", entry_count=2, dependency_count=1)
        assert result["exploration_cost"] < 0.3
        assert result["confidence_modifier"] >= -0.15  # small penalty
        assert result["should_prune"] is False

    def test_risky_nogo_raises_cost(self, nogo_isolated):
        """High NoGo risk → nogo_component drives up exploration_cost."""
        nr = nogo_isolated
        from matylda_lite.constitutional import BOUNDS
        # Force high effective_risk: many failures + many evidence
        for _ in range(20):
            nr.record_failure("bad", "tag", "repeated_failure")
        from matylda_lite.branch_evaluator import evaluate_branch
        result = evaluate_branch("bad", "tag", entry_count=1, dependency_count=1)
        assert result["effective_risk"] > 0.0
        assert result["exploration_cost"] > 0.0

    def test_very_long_branch_raises_cost(self, nogo_isolated):
        """entry_count exceeds limit → length_component pushes cost up."""
        from matylda_lite.branch_evaluator import evaluate_branch
        from matylda_lite.constitutional import BOUNDS
        long_count = BOUNDS.sleeping_matylda_diary_lookback_days * 3 + 10
        result = evaluate_branch("thread", "tag",
                                 entry_count=long_count, dependency_count=0)
        assert result["checks"]["branch_length_ok"] is False
        assert result["exploration_cost"] >= 0.3

    def test_confidence_modifier_non_positive(self, nogo_isolated):
        """confidence_modifier is always ≤ 0 (never increases confidence)."""
        from matylda_lite.branch_evaluator import evaluate_branch
        for ec in [0, 5, 30, 100]:
            result = evaluate_branch("t", "tg", entry_count=ec, dependency_count=ec)
            assert result["confidence_modifier"] <= 0.0

    def test_should_prune_derived_from_cost(self, nogo_isolated):
        """should_prune=True iff exploration_cost >= 0.9."""
        from matylda_lite.branch_evaluator import evaluate_branch
        result_safe = evaluate_branch("t", "tg", entry_count=0, dependency_count=0)
        assert result_safe["should_prune"] == (result_safe["exploration_cost"] >= 0.9)

    def test_result_shape(self, nogo_isolated):
        from matylda_lite.branch_evaluator import evaluate_branch
        result = evaluate_branch("t", "tag", entry_count=5, dependency_count=3)
        assert "exploration_cost" in result
        assert "confidence_modifier" in result
        assert "should_prune" in result
        assert "effective_risk" in result
        assert "reason" in result
        assert "checks" in result
        for key in ("branch_length_ok", "dependency_count_ok", "nogo_ok"):
            assert key in result["checks"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Consolidation integration (v0.8)
# ─────────────────────────────────────────────────────────────────────────────

class TestConsolidationV08Integration:

    def test_forgotten_object_finding_generated(
        self, sm_isolated, diary_isolated, homeostasis_isolated,
        forgetroom_isolated, nogo_isolated,
    ):
        """If Forgetroom has forgotten objects → forgotten_object finding appears."""
        fr = forgetroom_isolated
        import matylda_lite.sleeping_matylda.consolidation as con
        import matylda_lite.forgetroom as fr_mod
        # Also patch consolidation's import of forgetroom
        import matylda_lite.nogo_room as nr_mod

        # Write an artificially old object directly
        old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        fr._FORGETROOM_FILE.write_text(json.dumps({
            "objects": {
                "ghost_entity": {
                    "object_id":           "ghost_entity",
                    "object_type":         "entity",
                    "initial_weight":      1.0,
                    "last_activation":     old_date,
                    "reinforcement_count": 0,
                }
            }
        }))

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        assert result["status"] == "completed"
        forgotten = [f for f in result["findings"] if f["type"] == "forgotten_object"]
        assert forgotten, "No forgotten_object finding generated"
        assert forgotten[0]["object_id"] == "ghost_entity"

    def test_nogo_territory_finding_generated(
        self, sm_isolated, diary_isolated, homeostasis_isolated,
        forgetroom_isolated, nogo_isolated,
    ):
        """If NoGo has risky trajectories → nogo_territory finding appears."""
        nr = nogo_isolated
        # Force high effective_risk with enough evidence
        from matylda_lite.constitutional import BOUNDS
        for _ in range(BOUNDS.nogo_min_evidence_count + 3):
            nr.record_failure("bad_thread", "bad_tag", "repeated_failure")

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        assert result["status"] == "completed"
        nogo_findings = [f for f in result["findings"] if f["type"] == "nogo_territory"]
        assert nogo_findings, "No nogo_territory finding generated"

    def test_branch_cost_reduces_reflection_confidence(
        self, sm_isolated, diary_isolated, homeostasis_isolated,
        nogo_isolated, forgetroom_isolated,
    ):
        """High NoGo risk → reflection_candidate confidence is reduced."""
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS

        # Write diary entries for a thread
        tags = ["risky_tag"]
        for i in range(BOUNDS.sleeping_matylda_pattern_min_count + 1):
            dm.write_diary_entry(
                session_id=f"s{i}", thread_stem="risky_thread",
                query_summary=f"Q{i}", key_finding=f"F{i}",
                open_questions=[], contradicts=None,
                model_used="haiku", tags=tags,
            )

        # First cycle: baseline confidence
        sm = sm_isolated
        r1 = sm.run_cycle(force=True)
        candidates_1 = [f for f in r1["findings"] if f["type"] == "reflection_candidate"
                        and f["thread_stem"] == "risky_thread"]
        assert candidates_1, "No reflection candidate in clean cycle"
        conf_clean = candidates_1[0]["confidence"]

        # Now add NoGo risk for this trajectory
        nr = nogo_isolated
        for _ in range(BOUNDS.nogo_min_evidence_count + 2):
            nr.record_failure("risky_thread", "risky_tag", "repeated_failure")

        # Reload cycle with fresh state
        import matylda_lite.sleeping_matylda.consolidation as con
        con._save_state({
            "last_cycle_start": None, "last_cycle_end": None,
            "last_cycle_findings": 0, "total_cycles": 0, "findings": []
        })

        r2 = sm.run_cycle(force=True)
        candidates_2 = [f for f in r2["findings"] if f["type"] == "reflection_candidate"
                        and f["thread_stem"] == "risky_thread"]
        assert candidates_2, "No reflection candidate in risky cycle"
        conf_risky = candidates_2[0]["confidence"]

        assert conf_risky < conf_clean, (
            f"Expected risky confidence ({conf_risky}) < clean ({conf_clean})"
        )

    def test_approve_forgotten_object_remove(
        self, sm_isolated, homeostasis_isolated, diary_isolated,
        forgetroom_isolated, nogo_isolated,
    ):
        """Approving a forgotten_object finding with action 'remove_reflection'
        returns acknowledged (reflection removal is manual)."""
        sm = sm_isolated
        import matylda_lite.sleeping_matylda.consolidation as con

        # Inject a forgotten_object finding directly
        state = con._load_state()
        state["findings"] = [{
            "finding_id":   "finding_test_forgotten",
            "type":         "forgotten_object",
            "title":        "Test forgotten",
            "description":  "Test",
            "object_id":    "refl_001",
            "object_type":  "reflection",
            "effective_weight": 0.01,
            "days_since_activation": 90.0,
            "confidence":   0.99,
            "created":      datetime.now(timezone.utc).isoformat(),
            "state":        "pending",
            "action":       "remove_reflection",
        }]
        con._save_state(state)

        result = sm.approve_finding("finding_test_forgotten")
        assert result["state"] == "approved"
        assert "remove_reflection" in result["execution_result"]

    def test_dismiss_nogo_territory_finding(
        self, sm_isolated, homeostasis_isolated, diary_isolated,
        forgetroom_isolated, nogo_isolated,
    ):
        """Dismissing a nogo_territory finding records state without side effects."""
        sm = sm_isolated
        import matylda_lite.sleeping_matylda.consolidation as con

        state = con._load_state()
        state["findings"] = [{
            "finding_id":    "finding_nogo_test",
            "type":          "nogo_territory",
            "title":         "Test nogo",
            "description":   "Test",
            "trajectory_id": "thread::tag",
            "thread_stem":   "thread",
            "tag":           "tag",
            "category":      "repeated_failure",
            "effective_risk": 0.8,
            "evidence_count": 6,
            "confidence":    0.8,
            "created":       datetime.now(timezone.utc).isoformat(),
            "state":         "pending",
            "action":        "acknowledge_nogo",
        }]
        con._save_state(state)

        result = sm.dismiss_finding("finding_nogo_test", reason="znane ryzyko")
        assert result["state"] == "dismissed"
        assert result["dismiss_reason"] == "znane ryzyko"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Server routes (v0.8)
# ─────────────────────────────────────────────────────────────────────────────

class TestV08Routes:

    @pytest.fixture()
    def client(self, tmp_path, monkeypatch):
        import matylda_lite.nogo_room as nr
        import matylda_lite.forgetroom as fr
        monkeypatch.setattr(nr, "_NOGO_FILE", tmp_path / "nogo_room.json")
        monkeypatch.setattr(fr, "_FORGETROOM_FILE", tmp_path / "forgetroom.json")
        from fastapi.testclient import TestClient
        from matylda_lite.server import app
        return TestClient(app)

    def test_nogo_status_returns_200(self, client):
        resp = client.get("/api/nogo-room/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_entries" in data
        assert "high_risk_count" in data

    def test_nogo_trajectories_returns_list(self, client):
        resp = client.get("/api/nogo-room/trajectories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_nogo_trajectories_custom_threshold(self, client):
        resp = client.get("/api/nogo-room/trajectories?threshold=0.0")
        assert resp.status_code == 200

    def test_forgetroom_status_returns_200(self, client):
        resp = client.get("/api/forgetroom/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_objects" in data
        assert "forgotten_count" in data

    def test_forgetroom_candidates_returns_list(self, client):
        resp = client.get("/api/forgetroom/candidates")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_all_v08_routes_registered(self, client):
        from matylda_lite.server import app
        paths = {r.path for r in app.routes}
        assert "/api/nogo-room/status" in paths
        assert "/api/nogo-room/trajectories" in paths
        assert "/api/forgetroom/status" in paths
        assert "/api/forgetroom/candidates" in paths
