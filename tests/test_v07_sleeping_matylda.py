"""test_v07_sleeping_matylda.py — Tests for v0.7 Sleeping Matylda.

Coverage:
  ■ Constitutional   — v0.7 version + 5 new bounds
  ■ Core cycle       — run_cycle returns correct shape, skips on gap, skips on over_budget
  ■ Diary analysis   — reflection_candidate + synthesis_opportunity + stale_question findings
  ■ Graph analysis   — orphan + duplicate_candidate findings
  ■ Finding lifecycle — approve (each action), dismiss, double-approve raises
  ■ Prune            — old terminal findings removed
  ■ Server routes    — 5 Sleeping Matylda endpoints registered

Run: pytest tests/test_v07_sleeping_matylda.py -v
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
def sm_isolated(tmp_path, monkeypatch):
    """Redirect Sleeping Matylda state file to tmp_path.

    Must patch BOTH the re-export in __init__.py AND the module-level
    variable in consolidation.py — the latter is what _load_state()/_save_state()
    actually use at runtime.
    """
    import matylda_lite.sleeping_matylda as sm
    import matylda_lite.sleeping_matylda.consolidation as con
    state_file = tmp_path / "sleeping_matylda_state.json"
    monkeypatch.setattr(sm, "_STATE_FILE", state_file)
    monkeypatch.setattr(con, "_STATE_FILE", state_file)
    return sm


@pytest.fixture()
def diary_isolated(tmp_path, monkeypatch):
    """Redirect diary_manager to tmp_path."""
    import matylda_lite.diary_manager as dm
    monkeypatch.setattr(dm, "DIARY_DIR",       tmp_path / "diary")
    monkeypatch.setattr(dm, "REFLECTIONS_DIR", tmp_path / "reflections")
    monkeypatch.setattr(dm, "RULES_FILE",      tmp_path / "rules.md")
    monkeypatch.setattr(dm, "NEGATIVE_DIR",    tmp_path / "negative")
    (tmp_path / "diary").mkdir()
    (tmp_path / "reflections").mkdir()
    (tmp_path / "negative").mkdir()


@pytest.fixture()
def kg_isolated(tmp_path, monkeypatch):
    """Redirect knowledge_graph to tmp_path."""
    import matylda_lite.knowledge_graph as kg
    monkeypatch.setattr(kg, "GRAPH_FILE", tmp_path / "knowledge_graph.json")


@pytest.fixture()
def queue_isolated(tmp_path, monkeypatch):
    """Redirect task_queue to tmp_path."""
    import matylda_lite.task_queue as tq
    monkeypatch.setattr(tq, "QUEUE_FILE", tmp_path / "task_queue.jsonl")


@pytest.fixture()
def homeostasis_isolated(tmp_path, monkeypatch):
    """Redirect homeostasis state files to tmp_path."""
    import matylda_lite.homeostasis as hm
    hdir = tmp_path / "homeostasis"
    hdir.mkdir()
    monkeypatch.setattr(hm, "HOMEOSTASIS_DIR", hdir)
    monkeypatch.setattr(hm, "_GOALS_FILE",     hdir / "active_goals.json")
    monkeypatch.setattr(hm, "_BUDGET_FILE",    hdir / "attention_budget.json")
    monkeypatch.setattr(hm, "_FATIGUE_FILE",   hdir / "fatigue.json")
    monkeypatch.setattr(hm, "_STALE_FILE",     hdir / "stale_items.json")


def _write_diary_entries(dm, count: int, thread_stem: str, tags: list[str], days_ago: int = 0):
    """Helper: write N diary entries for a thread."""
    for i in range(count):
        ts = (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=i)).isoformat()
        dm.write_diary_entry(
            session_id=f"sess_{i}",
            thread_stem=thread_stem,
            query_summary=f"Q{i} about {thread_stem}",
            key_finding=f"Finding {i} in {thread_stem}",
            open_questions=[f"Question {i}?"] if days_ago > 3 else [],
            contradicts=None,
            model_used="haiku",
            tags=tags,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constitutional v0.7
# ─────────────────────────────────────────────────────────────────────────────

class TestConstitutionalV07:

    def test_version(self):
        from matylda_lite.constitutional import CONSTITUTIONAL_VERSION
        assert CONSTITUTIONAL_VERSION == "1.2"

    def test_sleeping_matylda_bounds_present(self):
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.sleeping_matylda_min_gap_hours == 6.0
        assert BOUNDS.sleeping_matylda_diary_lookback_days == 7
        assert BOUNDS.sleeping_matylda_pattern_min_count == 3
        assert BOUNDS.sleeping_matylda_max_findings_per_cycle == 5
        assert BOUNDS.sleeping_matylda_graph_similarity_threshold == 0.7

    def test_pattern_min_count_gte_reflection_min_occurrences(self):
        """pattern_min_count must be >= reflection_min_occurrences so promoted
        reflections automatically pass the injection guard."""
        from matylda_lite.constitutional import BOUNDS
        assert BOUNDS.sleeping_matylda_pattern_min_count >= BOUNDS.reflection_min_occurrences, (
            "sleeping_matylda_pattern_min_count < reflection_min_occurrences: "
            "promoted reflections would fail injection guard"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cycle — gap, skip, status
# ─────────────────────────────────────────────────────────────────────────────

class TestCycleGap:

    def test_first_cycle_runs(self, sm_isolated, diary_isolated, homeostasis_isolated):
        sm = sm_isolated
        result = sm.run_cycle(force=False)
        assert result["status"] == "completed"
        assert "cycle" in result
        assert result["cycle"] == 1

    def test_second_cycle_skipped_within_gap(self, sm_isolated, diary_isolated, homeostasis_isolated):
        sm = sm_isolated
        sm.run_cycle(force=False)
        # Immediately try again
        result = sm.run_cycle(force=False)
        assert result["status"] == "skipped"
        assert "Last cycle" in result["reason"]

    def test_force_overrides_gap(self, sm_isolated, diary_isolated, homeostasis_isolated):
        sm = sm_isolated
        sm.run_cycle(force=False)
        result = sm.run_cycle(force=True)
        assert result["status"] == "completed"
        assert result["cycle"] == 2

    def test_skip_when_attention_over_budget(self, sm_isolated, homeostasis_isolated, monkeypatch):
        sm = sm_isolated
        # Monkeypatch attention_status to report over_budget
        import matylda_lite.sleeping_matylda as _sm
        monkeypatch.setattr(
            "matylda_lite.homeostasis.attention_status",
            lambda: {"over_budget": True, "topics_used": 11, "max": 10},
        )
        result = sm.run_cycle(force=True)
        assert result["status"] == "skipped"
        assert "attention" in result["reason"]

    def test_reduced_scope_when_fatigued(self, sm_isolated, diary_isolated, homeostasis_isolated, monkeypatch):
        sm = sm_isolated
        # Monkeypatch fatigue to high
        monkeypatch.setattr(
            "matylda_lite.homeostasis.fatigue_status",
            lambda: {"fatigue": 0.80, "high": True},
        )
        result = sm.run_cycle(force=True)
        assert result["status"] == "completed"
        assert result["reduced_scope"] is True
        from matylda_lite.constitutional import BOUNDS
        assert result["days_analysed"] == BOUNDS.sleeping_matylda_diary_lookback_days // 2

    def test_get_status_shape(self, sm_isolated, diary_isolated, homeostasis_isolated):
        sm = sm_isolated
        sm.run_cycle(force=True)
        status = sm.get_status()
        assert "last_cycle_start" in status
        assert "last_cycle_end" in status
        assert "total_cycles" in status
        assert "pending_findings" in status
        assert "pending_by_type" in status
        assert "bounds" in status
        assert status["total_cycles"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Diary analysis — finding detection
# ─────────────────────────────────────────────────────────────────────────────

class TestDiaryAnalysis:

    def test_reflection_candidate_found(self, sm_isolated, diary_isolated, homeostasis_isolated):
        """Thread with >= pattern_min_count entries → reflection_candidate finding."""
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        _write_diary_entries(dm, BOUNDS.sleeping_matylda_pattern_min_count,
                             "deep_thread", ["topic_a"])

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        assert result["status"] == "completed"

        candidates = [f for f in result["findings"] if f["type"] == "reflection_candidate"]
        assert candidates, "No reflection_candidate finding generated"
        assert candidates[0]["thread_stem"] == "deep_thread"
        assert candidates[0]["entry_count"] >= BOUNDS.sleeping_matylda_pattern_min_count

    def test_no_reflection_candidate_below_threshold(self, sm_isolated, diary_isolated, homeostasis_isolated):
        """Thread with < pattern_min_count entries → no reflection_candidate."""
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        _write_diary_entries(dm, BOUNDS.sleeping_matylda_pattern_min_count - 1,
                             "shallow_thread", ["topic_b"])

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        candidates = [f for f in result["findings"] if f["type"] == "reflection_candidate"]
        assert not candidates

    def test_synthesis_opportunity_cross_thread(self, sm_isolated, diary_isolated, homeostasis_isolated):
        """Tag appearing in ≥2 threads → synthesis_opportunity finding."""
        import matylda_lite.diary_manager as dm
        _write_diary_entries(dm, 1, "thread_alpha", ["shared_tag"])
        _write_diary_entries(dm, 1, "thread_beta",  ["shared_tag"])

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        synths = [f for f in result["findings"] if f["type"] == "synthesis_opportunity"]
        assert synths, "No synthesis_opportunity finding generated"
        assert synths[0]["tag"] == "shared_tag"
        assert "thread_alpha" in synths[0]["threads"]
        assert "thread_beta"  in synths[0]["threads"]

    def test_findings_capped_at_max(self, sm_isolated, diary_isolated, homeostasis_isolated):
        """Total findings per cycle capped at sleeping_matylda_max_findings_per_cycle."""
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        # Create many qualifying threads
        for i in range(10):
            _write_diary_entries(dm, BOUNDS.sleeping_matylda_pattern_min_count,
                                 f"thread_{i:02d}", [f"tag_{i}"])

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        assert len(result["findings"]) <= BOUNDS.sleeping_matylda_max_findings_per_cycle

    def test_finding_confidence_increases_with_entries(self, sm_isolated, diary_isolated, homeostasis_isolated):
        """More entries → higher confidence on reflection_candidate."""
        import matylda_lite.diary_manager as dm
        _write_diary_entries(dm, 3, "thread_small", ["t"])
        _write_diary_entries(dm, 8, "thread_large", ["t"])

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        by_thread = {f["thread_stem"]: f["confidence"]
                     for f in result["findings"] if f["type"] == "reflection_candidate"}
        if "thread_small" in by_thread and "thread_large" in by_thread:
            assert by_thread["thread_large"] > by_thread["thread_small"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Graph analysis — finding detection
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphAnalysis:

    def test_orphan_detected(self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated):
        """Entity with no relations → graph_orphan finding."""
        import matylda_lite.knowledge_graph as kg
        kg.add_entity(entity_id="lonely", label="Lonely Entity", kind="concept")

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        orphans = [f for f in result["findings"] if f["type"] == "graph_orphan"]
        assert orphans
        assert orphans[0]["entity_id"] == "lonely"

    def test_no_orphan_when_entity_has_relations(self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated):
        """Entity with relations → not flagged as orphan."""
        import matylda_lite.knowledge_graph as kg
        kg.add_entity(entity_id="source", label="Source", kind="concept")
        kg.add_entity(entity_id="target", label="Target", kind="concept")
        kg.add_relation(from_id="source", rel_type="supports", to_id="target", confidence=0.8)

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        orphans = [f for f in result["findings"] if f["type"] == "graph_orphan"]
        assert not any(o["entity_id"] in ("source", "target") for o in orphans)

    def test_duplicate_candidate_detected(self, sm_isolated, diary_isolated, kg_isolated, homeostasis_isolated):
        """Two entities with high label overlap → graph_duplicate_candidate."""
        import matylda_lite.knowledge_graph as kg
        from matylda_lite.constitutional import BOUNDS
        kg.add_entity(entity_id="e1", label="Machine Learning Model", kind="concept")
        kg.add_entity(entity_id="e2", label="Machine Learning Model v2", kind="concept")

        sm = sm_isolated
        result = sm.run_cycle(force=True)
        dupes = [f for f in result["findings"] if f["type"] == "graph_duplicate_candidate"]
        assert dupes
        assert dupes[0]["similarity"] >= BOUNDS.sleeping_matylda_graph_similarity_threshold

    def test_graph_skipped_in_reduced_scope(self, sm_isolated, diary_isolated, kg_isolated,
                                             homeostasis_isolated, monkeypatch):
        """Reduced scope (high fatigue) → graph analysis skipped."""
        import matylda_lite.knowledge_graph as kg
        kg.add_entity(entity_id="orphan_r", label="Orphan", kind="concept")

        monkeypatch.setattr(
            "matylda_lite.homeostasis.fatigue_status",
            lambda: {"fatigue": 0.80, "high": True},
        )
        sm = sm_isolated
        result = sm.run_cycle(force=True)
        assert result["reduced_scope"] is True
        graph_findings = [f for f in result["findings"]
                          if f["type"] in ("graph_orphan", "graph_duplicate_candidate")]
        assert not graph_findings


# ─────────────────────────────────────────────────────────────────────────────
# 5. Finding lifecycle — approve, dismiss
# ─────────────────────────────────────────────────────────────────────────────

class TestFindingLifecycle:

    def test_approve_reflection_candidate(
        self, sm_isolated, diary_isolated, homeostasis_isolated, monkeypatch
    ):
        """Approving reflection_candidate calls save_reflection and returns reflection id."""
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        _write_diary_entries(dm, BOUNDS.sleeping_matylda_pattern_min_count, "my_thread", ["ai"])

        sm = sm_isolated
        cycle = sm.run_cycle(force=True)
        candidates = [f for f in cycle["findings"] if f["type"] == "reflection_candidate"]
        assert candidates, "No candidates to approve"

        approved = sm.approve_finding(candidates[0]["finding_id"])
        assert approved["state"] == "approved"
        assert approved["execution_result"].startswith("reflection:")
        assert approved["approved_by"] == "user"

        # Verify reflection was saved
        reflections = dm.list_reflections(days=1)
        assert any(r.get("source") == "sleeping_matylda" for r in reflections)

    def test_approve_synthesis_opportunity(
        self, sm_isolated, diary_isolated, queue_isolated, homeostasis_isolated
    ):
        """Approving synthesis_opportunity enqueues a task (may need approval)."""
        import matylda_lite.diary_manager as dm
        import matylda_lite.task_queue as tq
        _write_diary_entries(dm, 1, "thread_x", ["shared"])
        _write_diary_entries(dm, 1, "thread_y", ["shared"])

        sm = sm_isolated
        cycle = sm.run_cycle(force=True)
        synths = [f for f in cycle["findings"] if f["type"] == "synthesis_opportunity"]
        assert synths

        approved = sm.approve_finding(synths[0]["finding_id"])
        result = approved["execution_result"]
        assert result.startswith("task:")

        # Task was enqueued
        tasks = tq.load_tasks()
        assert any(t.get("created_by") == "sleeping_matylda" for t in tasks.values())

    def test_dismiss_finding(self, sm_isolated, diary_isolated, homeostasis_isolated):
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        _write_diary_entries(dm, BOUNDS.sleeping_matylda_pattern_min_count, "thread_d", [])

        sm = sm_isolated
        cycle = sm.run_cycle(force=True)
        assert cycle["findings"]

        fid = cycle["findings"][0]["finding_id"]
        dismissed = sm.dismiss_finding(fid, reason="not relevant")
        assert dismissed["state"] == "dismissed"
        assert dismissed["dismiss_reason"] == "not relevant"
        assert "dismissed_at" in dismissed

    def test_double_approve_raises(self, sm_isolated, diary_isolated, homeostasis_isolated):
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        _write_diary_entries(dm, BOUNDS.sleeping_matylda_pattern_min_count, "thread_e", [])

        sm = sm_isolated
        cycle = sm.run_cycle(force=True)
        candidates = [f for f in cycle["findings"] if f["type"] == "reflection_candidate"]
        assert candidates
        fid = candidates[0]["finding_id"]

        sm.approve_finding(fid)
        with pytest.raises(ValueError, match="not pending"):
            sm.approve_finding(fid)

    def test_unknown_finding_raises_keyerror(self, sm_isolated):
        sm = sm_isolated
        with pytest.raises(KeyError):
            sm.approve_finding("finding_nonexistent")
        with pytest.raises(KeyError):
            sm.dismiss_finding("finding_nonexistent")

    def test_pending_findings_persist_across_cycles(self, sm_isolated, diary_isolated, homeostasis_isolated):
        """Pending findings survive into the next cycle without duplication."""
        import matylda_lite.diary_manager as dm
        from matylda_lite.constitutional import BOUNDS
        _write_diary_entries(dm, BOUNDS.sleeping_matylda_pattern_min_count, "persist_thread", [])

        sm = sm_isolated
        sm.run_cycle(force=True)
        pending_after_first = len(sm.get_findings(state_filter="pending"))
        assert pending_after_first > 0

        sm.run_cycle(force=True)
        # Pending findings from first cycle should still be there
        pending_after_second = len(sm.get_findings(state_filter="pending"))
        assert pending_after_second >= pending_after_first  # never loses pending


# ─────────────────────────────────────────────────────────────────────────────
# 6. Prune
# ─────────────────────────────────────────────────────────────────────────────

class TestPrune:

    def test_prune_removes_old_terminal_findings(self, sm_isolated):
        sm = sm_isolated
        old_time = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        state = sm._load_state()
        state["findings"] = [
            {"finding_id": "f_old_approved", "type": "reflection_candidate",
             "state": "approved", "approved_at": old_time, "created": old_time},
            {"finding_id": "f_old_dismissed", "type": "graph_orphan",
             "state": "dismissed", "dismissed_at": old_time, "created": old_time},
            {"finding_id": "f_pending", "type": "graph_orphan",
             "state": "pending", "created": old_time},  # active — must NOT be pruned
        ]
        sm._save_state(state)

        pruned = sm.prune_old_findings(days=30)
        assert pruned == 2
        remaining = sm.get_findings()
        assert len(remaining) == 1
        assert remaining[0]["finding_id"] == "f_pending"

    def test_prune_keeps_recent_terminal(self, sm_isolated):
        sm = sm_isolated
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        state = sm._load_state()
        state["findings"] = [
            {"finding_id": "f_recent", "type": "reflection_candidate",
             "state": "approved", "approved_at": recent, "created": recent},
        ]
        sm._save_state(state)

        pruned = sm.prune_old_findings(days=30)
        assert pruned == 0


# ─────────────────────────────────────────────────────────────────────────────
# 7. Server routes
# ─────────────────────────────────────────────────────────────────────────────

class TestSleepingMatyldaRoutes:

    def test_all_routes_registered(self, client):
        routes = {r.path for r in client.app.routes}
        expected = {
            "/api/sleeping-matylda/status",
            "/api/sleeping-matylda/run",
            "/api/sleeping-matylda/findings",
            "/api/sleeping-matylda/findings/{finding_id}/approve",
            "/api/sleeping-matylda/findings/{finding_id}/dismiss",
        }
        missing = expected - routes
        assert not missing, f"Missing routes: {missing}"

    def test_status_endpoint_returns_200(self, client):
        r = client.get("/api/sleeping-matylda/status")
        assert r.status_code == 200
        data = r.json()
        assert "total_cycles" in data
        assert "pending_findings" in data
        assert "bounds" in data

    def test_findings_endpoint_returns_list(self, client):
        r = client.get("/api/sleeping-matylda/findings")
        assert r.status_code == 200
        assert "findings" in r.json()

    def test_run_endpoint_returns_status(self, client):
        r = client.post("/api/sleeping-matylda/run?force=true")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") in ("completed", "skipped")

    def test_approve_nonexistent_returns_404(self, client):
        r = client.post("/api/sleeping-matylda/findings/finding_nonexistent/approve")
        assert r.status_code == 404

    def test_dismiss_nonexistent_returns_404(self, client):
        r = client.post("/api/sleeping-matylda/findings/finding_nonexistent/dismiss")
        assert r.status_code == 404
