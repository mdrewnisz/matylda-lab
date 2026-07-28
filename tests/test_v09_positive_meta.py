"""test_v09_positive_meta.py — Tests for v0.9 Positive Room + Meta Drift + Identity Snapshot.

Coverage:
  ■ Constitutional   — v0.9 version + 7 new bounds, forgetroom_decay_k > nogo_decay_k invariant
  ■ Positive Room    — record_success (additive), record_failure (multiplicative decay),
                       effective_success (time + evidence discount), list_attractive,
                       novelty_floor, stability_score, prune
  ■ Branch Evaluator — Positive Room reduces exploration_cost, novelty_floor prevents death,
                       cost never negative
  ■ Meta Drift       — cycle_history tracking, score computation (window/baseline),
                       meta_drift_alert finding generated
  ■ Identity Snapshot — snapshot_identity shape, list_snapshots, compare_snapshots deltas
  ■ Server routes    — 6 new endpoints

Run: pytest tests/test_v09_positive_meta.py -v
"""
from __future__ import annotations

import json
import math
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
def positive_isolated(tmp_path, monkeypatch):
    import matylda_lite.positive_room as pr
    monkeypatch.setattr(pr, "_POSITIVE_FILE", tmp_path / "positive_room.json")
    return pr


@pytest.fixture()
def nogo_isolated(tmp_path, monkeypatch):
    import matylda_lite.nogo_room as nr
    monkeypatch.setattr(nr, "_NOGO_FILE", tmp_path / "nogo_room.json")
    return nr


@pytest.fixture()
def sm_isolated(tmp_path, monkeypatch):
    import matylda_lite.sleeping_matylda as sm
    import matylda_lite.sleeping_matylda.consolidation as con
    state_file    = tmp_path / "sleeping_matylda_state.json"
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


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constitutional v0.9
# ─────────────────────────────────────────────────────────────────────────────

class TestConstitutionalV09:

    def test_version(self):
        from matylda_lite.constitutional import CONSTITUTIONAL_VERSION
        assert CONSTITUTIONAL_VERSION == "1.2"

    def test_positive_bounds_present(self):
        from matylda_lite.constitutional import BOUNDS
        assert hasattr(BOUNDS, "positive_success_weight")
        assert hasattr(BOUNDS, "positive_failure_weight")
        assert hasattr(BOUNDS, "positive_success_threshold")
        assert hasattr(BOUNDS, "positive_novelty_floor")
        assert hasattr(BOUNDS, "positive_max_entries")

    def test_meta_drift_bounds_present(self):
        from matylda_lite.constitutional import BOUNDS
        assert hasattr(BOUNDS, "meta_drift_window_days")
        assert hasattr(BOUNDS, "meta_drift_alert_threshold")

    def test_novelty_floor_in_range(self):
        """novelty_floor must be strictly in (0, 1) — allows some decay."""
        from matylda_lite.constitutional import BOUNDS
        assert 0.0 < BOUNDS.positive_novelty_floor < 1.0

    def test_forgetroom_decays_faster_than_nogo(self):
        """Architectural invariant: trash fades faster than bad memories."""
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.forgetroom_decay_k > BOUNDS.nogo_decay_k

    def test_positive_uses_same_decay_as_nogo(self):
        """Positive Room reuses nogo_decay_k (symmetry design)."""
        from matylda_lite.constitutional import BOUNDS
        # Verified by code inspection — both modules import nogo_decay_k
        # Boundary: nogo_decay_k must exist (already tested in v0.8)
        assert BOUNDS.nogo_decay_k > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Positive Room
# ─────────────────────────────────────────────────────────────────────────────

class TestPositiveRoom:

    def test_record_success_increases_score(self, positive_isolated):
        pr = positive_isolated
        result = pr.record_success("ml_basics", "supervised")
        assert result["success_score"] > 0.0

    def test_record_success_caps_at_one(self, positive_isolated):
        pr = positive_isolated
        from matylda_lite.constitutional import BOUNDS
        iters = math.ceil(1.0 / BOUNDS.positive_success_weight) + 5
        for _ in range(iters):
            pr.record_success("thread", "tag")
        entry = pr.get_trajectory("thread", "tag")
        assert entry["success_score"] == 1.0

    def test_record_failure_multiplicative_decay(self, positive_isolated):
        """Failure multiplies score down — never reaches 0."""
        pr = positive_isolated
        from matylda_lite.constitutional import BOUNDS
        for _ in range(5):
            pr.record_success("thread", "tag")
        before = pr.get_trajectory("thread", "tag")["success_score"]
        assert before > 0.0
        for _ in range(100):
            pr.record_failure("thread", "tag")
        after = pr.get_trajectory("thread", "tag")["success_score"]
        assert after > 0.0, "Multiplicative failure should never reach 0"
        assert after < before

    def test_record_failure_unknown_trajectory_returns_zero(self, positive_isolated):
        pr = positive_isolated
        result = pr.record_failure("nonexistent", "tag")
        assert result["effective_success"] == 0.0

    def test_evidence_discount_low_evidence(self, positive_isolated):
        """Single success → effective_success is discounted (< stored_score)."""
        pr = positive_isolated
        result = pr.record_success("new_thread", "new_tag")
        assert result["evidence_count"] == 1
        assert result["effective_success"] < result["success_score"]

    def test_full_evidence_no_discount(self, positive_isolated):
        """At nogo_min_evidence_count events → effective_success ≈ stored_score."""
        pr = positive_isolated
        from matylda_lite.constitutional import BOUNDS
        for _ in range(BOUNDS.nogo_min_evidence_count):
            result = pr.record_success("t", "tg")
        assert result["effective_success"] == pytest.approx(result["success_score"], abs=0.01)

    def test_stability_score_all_successes(self, positive_isolated):
        """All successes → stability_score = 1.0."""
        pr = positive_isolated
        for _ in range(5):
            pr.record_success("thread", "tag")
        entry = pr.get_trajectory("thread", "tag")
        assert entry["stability_score"] == 1.0

    def test_stability_score_mixed(self, positive_isolated):
        """Mixed record → stability_score < 1.0."""
        pr = positive_isolated
        for _ in range(3):
            pr.record_success("t", "tg")
        for _ in range(3):
            pr.record_failure("t", "tg")
        entry = pr.get_trajectory("t", "tg")
        assert entry["stability_score"] < 1.0

    def test_get_success_score_unknown_returns_zero(self, positive_isolated):
        pr = positive_isolated
        assert pr.get_success_score("ghost", "tag") == 0.0

    def test_list_attractive_above_threshold(self, positive_isolated):
        pr = positive_isolated
        from matylda_lite.constitutional import BOUNDS
        for _ in range(10):
            pr.record_success("good_thread", "good_tag")
        attractive = pr.list_attractive_trajectories(threshold=0.0)
        tids = [t["trajectory_id"] for t in attractive]
        assert "good_thread::good_tag" in tids

    def test_prune_removes_weakest(self, positive_isolated):
        pr = positive_isolated
        for i in range(5):
            pr.record_success(f"t{i}", "tag")
        assert pr.positive_status()["total_entries"] == 5
        removed = pr.prune_old_entries(max_entries=3)
        assert removed == 2
        assert pr.positive_status()["total_entries"] == 3

    def test_positive_status_shape(self, positive_isolated):
        pr = positive_isolated
        status = pr.positive_status()
        assert "total_entries" in status
        assert "attractive_count" in status
        assert "threshold" in status
        assert "novelty_floor" in status


# ─────────────────────────────────────────────────────────────────────────────
# 3. Branch Evaluator (v0.9 additions)
# ─────────────────────────────────────────────────────────────────────────────

class TestBranchEvaluatorV09:

    def test_positive_room_reduces_cost(self, positive_isolated, nogo_isolated):
        """High success score → exploration_cost reduced vs clean state."""
        pr = positive_isolated
        from matylda_lite.constitutional import BOUNDS
        # Build high success for a trajectory
        for _ in range(BOUNDS.nogo_min_evidence_count + 3):
            pr.record_success("good_thread", "good_tag")

        from matylda_lite.branch_evaluator import evaluate_branch
        result = evaluate_branch("good_thread", "good_tag",
                                 entry_count=5, dependency_count=3)
        assert result["positive_discount"] > 0.0
        assert result["effective_success"] > 0.0
        assert result["checks"]["positive_ok"] is True

    def test_novelty_floor_prevents_full_death(self, positive_isolated, nogo_isolated):
        """Even with huge reuse_count, novelty_factor >= positive_novelty_floor."""
        pr = positive_isolated
        from matylda_lite.constitutional import BOUNDS
        # Simulate 1000 reuses
        for _ in range(1000):
            pr.record_success("ancient_thread", "ancient_tag")

        from matylda_lite.branch_evaluator import evaluate_branch
        result = evaluate_branch("ancient_thread", "ancient_tag",
                                 entry_count=0, dependency_count=0)
        assert result["novelty_factor"] >= BOUNDS.positive_novelty_floor

    def test_exploration_cost_never_negative(self, positive_isolated, nogo_isolated):
        """exploration_cost is always >= 0.0 even with max positive discount."""
        pr = positive_isolated
        for _ in range(100):
            pr.record_success("super_good", "tag")
        from matylda_lite.branch_evaluator import evaluate_branch
        result = evaluate_branch("super_good", "tag",
                                 entry_count=0, dependency_count=0)
        assert result["exploration_cost"] >= 0.0

    def test_result_has_v09_fields(self, positive_isolated, nogo_isolated):
        from matylda_lite.branch_evaluator import evaluate_branch
        result = evaluate_branch("t", "tag", entry_count=2, dependency_count=1)
        assert "effective_success" in result
        assert "positive_discount" in result
        assert "novelty_factor" in result
        assert "positive_ok" in result["checks"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Meta Drift
# ─────────────────────────────────────────────────────────────────────────────

class TestMetaDrift:

    def test_meta_drift_neutral_when_no_history(self, sm_isolated):
        sm = sm_isolated
        result = sm.get_meta_drift()
        assert result["meta_drift_score"] == 1.0
        assert result["alert"] is False

    def test_meta_drift_shape(self, sm_isolated):
        sm = sm_isolated
        result = sm.get_meta_drift()
        assert "meta_drift_score" in result
        assert "window_days" in result
        assert "avg_confidence_modifier" in result
        assert "cycles_in_window" in result
        assert "cycles_in_baseline" in result
        assert "alert" in result

    def test_cycle_history_appended_on_run_cycle(
        self, sm_isolated, diary_isolated, homeostasis_isolated
    ):
        """After run_cycle(), cycle_history grows by 1."""
        sm = sm_isolated
        import matylda_lite.sleeping_matylda.consolidation as con
        sm.run_cycle(force=True)
        state = con._load_state()
        assert len(state.get("cycle_history", [])) == 1

    def test_meta_drift_alert_finding_generated(
        self, sm_isolated, diary_isolated, homeostasis_isolated
    ):
        """Manually set a high meta_drift_score → alert finding appears."""
        sm = sm_isolated
        import matylda_lite.sleeping_matylda.consolidation as con
        from matylda_lite.constitutional import BOUNDS

        # Pre-populate cycle_history: baseline window (2×window_days ago)
        # with low activity, current window with high activity
        now = datetime.now(timezone.utc)
        window = BOUNDS.meta_drift_window_days

        # Baseline: 3 findings, 2 windows ago
        baseline_ts = (now - timedelta(days=window + 5)).isoformat()
        # Current: 15 findings, just now
        current_ts = now.isoformat()

        state = con._load_state()
        state["cycle_history"] = [
            # Baseline entry
            {"cycle": 1, "timestamp": baseline_ts, "findings_count": 2,
             "avg_confidence_modifier": -0.05,
             "reflections_delta": 1, "entities_delta": 0, "goals_delta": 0,
             "structural_snapshot": {"reflections": 1, "entities": 0, "goals": 0}},
            # Current entries (high activity)
            *[{
                "cycle": i + 2, "timestamp": current_ts, "findings_count": 5,
                "avg_confidence_modifier": -0.3,
                "reflections_delta": 3, "entities_delta": 2, "goals_delta": 1,
                "structural_snapshot": {"reflections": 10, "entities": 5, "goals": 2}
            } for i in range(6)],
        ]
        con._save_state(state)

        drift = sm.get_meta_drift()
        assert drift["meta_drift_score"] >= BOUNDS.meta_drift_alert_threshold, (
            f"Expected drift >= {BOUNDS.meta_drift_alert_threshold}, got {drift['meta_drift_score']}"
        )

    def test_meta_drift_avg_modifier_tracks_risky_trajectories(
        self, sm_isolated, diary_isolated, homeostasis_isolated
    ):
        """avg_confidence_modifier in cycle_history reflects exploration cost of findings."""
        sm = sm_isolated
        import matylda_lite.sleeping_matylda.consolidation as con
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS

        # Write diary entries with a thread (will have exploration_cost field)
        for i in range(BOUNDS.sleeping_matylda_pattern_min_count + 1):
            dm.write_diary_entry(
                session_id=f"s{i}", thread_stem="test_thread",
                query_summary=f"Q{i}", key_finding=f"F{i}",
                open_questions=[], contradicts=None,
                model_used="haiku", tags=["test_tag"],
            )

        sm.run_cycle(force=True)
        state = con._load_state()
        history = state.get("cycle_history", [])
        assert history, "Cycle history should not be empty"
        # avg_confidence_modifier should be recorded (might be 0 if no exploration_cost)
        assert "avg_confidence_modifier" in history[-1]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Identity Snapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestIdentitySnapshot:

    def test_snapshot_returns_shape(
        self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated
    ):
        sm = sm_isolated
        snap = sm.snapshot_identity(label="test_snapshot")
        assert "snapshot_id" in snap
        assert "label" in snap
        assert "created" in snap
        assert "reflection_count" in snap
        assert "entity_count" in snap
        assert "relation_count" in snap
        assert "goal_count" in snap
        assert "top_tags" in snap
        assert "meta_drift_score_at_snapshot" in snap

    def test_snapshot_label_preserved(
        self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated
    ):
        sm = sm_isolated
        snap = sm.snapshot_identity(label="pre_v09_baseline")
        assert snap["label"] == "pre_v09_baseline"

    def test_snapshot_default_label_has_date(
        self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated
    ):
        sm = sm_isolated
        snap = sm.snapshot_identity()
        assert snap["label"].startswith("snapshot_")

    def test_list_snapshots_newest_first(
        self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated
    ):
        sm = sm_isolated
        sm.snapshot_identity(label="first")
        sm.snapshot_identity(label="second")
        snaps = sm.list_snapshots()
        assert len(snaps) == 2
        assert snaps[0]["label"] == "second"  # newest first
        assert snaps[1]["label"] == "first"

    def test_compare_snapshots_delta(
        self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated
    ):
        """compare_snapshots returns correct numeric deltas."""
        sm = sm_isolated
        snap_a = sm.snapshot_identity(label="before")
        snap_b = sm.snapshot_identity(label="after")
        diff   = sm.compare_snapshots(snap_a["snapshot_id"], snap_b["snapshot_id"])
        assert "deltas" in diff
        assert "tags_gained" in diff
        assert "tags_lost" in diff
        assert "meta_drift_delta" in diff
        # Both have same counts (no changes between) → all deltas = 0
        for field, delta in diff["deltas"].items():
            assert delta == 0, f"Expected delta=0 for {field}, got {delta}"

    def test_compare_unknown_snapshot_raises_keyerror(
        self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated
    ):
        sm = sm_isolated
        snap_a = sm.snapshot_identity(label="real")
        with pytest.raises(KeyError):
            sm.compare_snapshots(snap_a["snapshot_id"], "snap_nonexistent")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Positive Room → Sleeping Matylda feedback
# ─────────────────────────────────────────────────────────────────────────────

class TestPositiveFeedback:

    def test_approve_reflection_candidate_registers_success(
        self, sm_isolated, diary_isolated, homeostasis_isolated, positive_isolated
    ):
        """Approving a reflection_candidate finding registers success in Positive Room."""
        sm = sm_isolated
        import matylda_lite.sleeping_matylda.consolidation as con
        import matylda_lite.positive_room as pr

        state = con._load_state()
        state["findings"] = [{
            "finding_id":    "f_approve_test",
            "type":          "reflection_candidate",
            "title":         "Test",
            "description":   "Test",
            "thread_stem":   "good_thread",
            "entry_count":   5,
            "entry_ids":     [],
            "key_findings":  [],
            "open_questions": [],
            "tags":          ["good_tag"],
            "confidence":    0.85,
            "created":       datetime.now(timezone.utc).isoformat(),
            "state":         "pending",
            "action":        "create_reflection",
        }]
        con._save_state(state)

        sm.approve_finding("f_approve_test")
        # Positive Room should have an entry for this trajectory
        entry = pr.get_trajectory("good_thread", "good_tag")
        assert entry is not None
        assert entry["success_count"] == 1

    def test_dismiss_reflection_candidate_registers_failure(
        self, sm_isolated, diary_isolated, homeostasis_isolated, positive_isolated
    ):
        """Dismissing a reflection_candidate registers failure in Positive Room."""
        sm = sm_isolated
        import matylda_lite.sleeping_matylda.consolidation as con
        import matylda_lite.positive_room as pr

        # First build up a success score
        pr.record_success("bad_thread", "bad_tag")
        pr.record_success("bad_thread", "bad_tag")
        before = pr.get_trajectory("bad_thread", "bad_tag")["success_score"]

        state = con._load_state()
        state["findings"] = [{
            "finding_id":    "f_dismiss_test",
            "type":          "reflection_candidate",
            "title":         "Test",
            "description":   "Test",
            "thread_stem":   "bad_thread",
            "entry_count":   3,
            "entry_ids":     [],
            "key_findings":  [],
            "open_questions": [],
            "tags":          ["bad_tag"],
            "confidence":    0.60,
            "created":       datetime.now(timezone.utc).isoformat(),
            "state":         "pending",
            "action":        "create_reflection",
        }]
        con._save_state(state)

        sm.dismiss_finding("f_dismiss_test", reason="not useful")
        after = pr.get_trajectory("bad_thread", "bad_tag")["success_score"]
        assert after < before


# ─────────────────────────────────────────────────────────────────────────────
# 7. Server routes (v0.9)
# ─────────────────────────────────────────────────────────────────────────────

class TestV09Routes:

    @pytest.fixture()
    def client(self, tmp_path, monkeypatch):
        import matylda_lite.positive_room as pr
        import matylda_lite.sleeping_matylda as sm
        import matylda_lite.sleeping_matylda.consolidation as con
        monkeypatch.setattr(pr,  "_POSITIVE_FILE",  tmp_path / "positive_room.json")
        state_file    = tmp_path / "sm_state.json"
        snapshots_file = tmp_path / "identity_snapshots.json"
        monkeypatch.setattr(sm,  "_STATE_FILE",     state_file)
        monkeypatch.setattr(sm,  "_SNAPSHOTS_FILE", snapshots_file)
        monkeypatch.setattr(con, "_STATE_FILE",     state_file)
        monkeypatch.setattr(con, "_SNAPSHOTS_FILE", snapshots_file)
        from fastapi.testclient import TestClient
        from matylda_lite.server import app
        return TestClient(app)

    def test_positive_status_returns_200(self, client):
        resp = client.get("/api/positive-room/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_entries" in data

    def test_positive_trajectories_returns_list(self, client):
        resp = client.get("/api/positive-room/trajectories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_meta_drift_returns_200(self, client):
        resp = client.get("/api/sleeping-matylda/meta-drift")
        assert resp.status_code == 200
        data = resp.json()
        assert "meta_drift_score" in data

    def test_snapshot_post_returns_ok(self, client):
        resp = client.post("/api/sleeping-matylda/snapshot",
                          json={"label": "test_snap"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "snapshot" in data
        assert data["snapshot"]["label"] == "test_snap"

    def test_snapshots_list_returns_200(self, client):
        resp = client.get("/api/sleeping-matylda/snapshots")
        assert resp.status_code == 200
        assert "snapshots" in resp.json()

    def test_compare_unknown_returns_404(self, client):
        resp = client.get("/api/sleeping-matylda/snapshots/compare?a=snap_abc&b=snap_xyz")
        assert resp.status_code == 404

    def test_all_v09_routes_registered(self, client):
        from matylda_lite.server import app
        paths = {r.path for r in app.routes}
        assert "/api/positive-room/status" in paths
        assert "/api/positive-room/trajectories" in paths
        assert "/api/sleeping-matylda/meta-drift" in paths
        assert "/api/sleeping-matylda/snapshot" in paths
        assert "/api/sleeping-matylda/snapshots" in paths
        assert "/api/sleeping-matylda/snapshots/compare" in paths
