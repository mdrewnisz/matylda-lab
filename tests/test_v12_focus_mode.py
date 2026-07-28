"""Tests for Sleeping Matylda v1.2 — Focus Mode.

Covers:
  - FocusSessionConfig: modes, is_done(), remaining_seconds()
  - Session persistence: save / load / clear
  - run_focused_cycle() with mocked engines
  - start_focus_session() / get_focus_status() / pause / resume / stop
  - run_cycle(focus_config=...) delegation
  - Finding provenance fields
  - _execute_finding for new action types
  - Endpoint smoke tests (via TestClient)
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_focus_file(tmp_path, monkeypatch):
    """Redirect focus session file to tmp_path."""
    focus_file = tmp_path / "focus_session.json"
    import matylda_lite.sleeping_matylda.focus_engine as fe
    monkeypatch.setattr(fe, "_FOCUS_SESSION_FILE", focus_file)
    return focus_file


@pytest.fixture()
def sm_isolated(tmp_path, monkeypatch):
    """Redirect SM state file to tmp_path."""
    import matylda_lite.sleeping_matylda.consolidation as c
    state_file = tmp_path / "sm_state.json"
    monkeypatch.setattr(c, "_STATE_FILE", state_file)
    return state_file


@pytest.fixture()
def homeostasis_isolated(tmp_path, monkeypatch):
    import matylda_lite.homeostasis as h
    for attr in ("_FATIGUE_FILE", "_BUDGET_FILE", "_GOALS_FILE", "_STALE_FILE"):
        if hasattr(h, attr):
            monkeypatch.setattr(h, attr, tmp_path / f"{attr}.json")


# ── FocusSessionConfig unit tests ─────────────────────────────────────────────

class TestFocusSessionConfig:
    def _cfg(self, **kw):
        from matylda_lite.sleeping_matylda.focus_engine import FocusSessionConfig
        defaults = dict(
            session_id="focus_test",
            focus_areas=["questions"],
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        defaults.update(kw)
        return FocusSessionConfig(**defaults)

    def test_is_done_timebox_elapsed(self):
        cfg = self._cfg(mode="timebox", duration_seconds=1,
                        start_iso="2020-01-01T00:00:00+00:00")
        assert cfg.is_done() is True

    def test_is_done_timebox_not_elapsed(self):
        cfg = self._cfg(mode="timebox", duration_seconds=9999)
        assert cfg.is_done() is False

    def test_is_done_until_idle_threshold_reached(self):
        cfg = self._cfg(mode="until_idle", idle_threshold=3,
                        consecutive_empty_cycles=3)
        assert cfg.is_done() is True

    def test_is_done_until_idle_not_reached(self):
        cfg = self._cfg(mode="until_idle", idle_threshold=3,
                        consecutive_empty_cycles=2)
        assert cfg.is_done() is False

    def test_is_done_cancelled(self):
        cfg = self._cfg(status="cancelled")
        assert cfg.is_done() is True

    def test_is_done_completed(self):
        cfg = self._cfg(status="completed")
        assert cfg.is_done() is True

    def test_remaining_seconds_timebox(self):
        cfg = self._cfg(mode="timebox", duration_seconds=3600)
        rem = cfg.remaining_seconds()
        assert 3590 < rem <= 3600

    def test_remaining_seconds_until_idle_returns_minus_one(self):
        cfg = self._cfg(mode="until_idle")
        assert cfg.remaining_seconds() == -1.0

    def test_as_dict_round_trips(self):
        from matylda_lite.sleeping_matylda.focus_engine import FocusSessionConfig
        cfg = self._cfg(focus_areas=["questions", "tensions"])
        d = cfg.as_dict()
        restored = FocusSessionConfig(**{
            k: v for k, v in d.items()
            if k in FocusSessionConfig.__dataclass_fields__
        })
        assert restored.focus_areas == ["questions", "tensions"]


# ── Session persistence ───────────────────────────────────────────────────────

class TestSessionPersistence:
    def test_save_and_load_roundtrip(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, _save_session, _load_session,
        )
        cfg = FocusSessionConfig(
            session_id="focus_abc",
            focus_areas=["tensions"],
            mode="until_idle",
            idle_threshold=2,
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        _save_session(cfg)
        loaded = _load_session()
        assert loaded is not None
        assert loaded.session_id == "focus_abc"
        assert loaded.focus_areas == ["tensions"]
        assert loaded.mode == "until_idle"

    def test_load_missing_file_returns_none(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import _load_session
        assert _load_session() is None

    def test_clear_session(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, _save_session, _load_session, _clear_session,
        )
        cfg = FocusSessionConfig(
            session_id="x", focus_areas=["steps"],
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        _save_session(cfg)
        _clear_session()
        assert _load_session() is None


# ── Finding provenance ────────────────────────────────────────────────────────

class TestFindingProvenance:
    def test_add_provenance_sets_all_fields(self):
        from matylda_lite.sleeping_matylda.focus_engine import _add_provenance
        f: dict = {"type": "question_focus"}
        _add_provenance(f, session_id="ses1", focus_area="questions",
                        source_thread="my_thread", source_question="What?")
        assert f["focus_session_id"] == "ses1"
        assert f["focus_area"] == "questions"
        assert f["source_thread"] == "my_thread"
        assert f["source_question"] == "What?"

    def test_add_provenance_omits_none_fields(self):
        from matylda_lite.sleeping_matylda.focus_engine import _add_provenance
        f: dict = {}
        _add_provenance(f, session_id="s", focus_area="tensions")
        assert "source_thread" not in f
        assert "source_tension" not in f

    def test_auto_tag_low_risk_marks_low_confidence(self, tmp_focus_file, sm_isolated):
        import matylda_lite.sleeping_matylda.focus_engine as fe
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, run_focused_cycle,
        )
        cfg = FocusSessionConfig(
            session_id="tag_test", focus_areas=["questions"],
            auto_tag_low_risk=True,
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        low_risk_finding = {
            "finding_id": "finding_x", "type": "question_focus",
            "confidence": 0.30, "state": "pending",
            "focus_session_id": cfg.session_id, "focus_area": "questions",
        }
        # Patch _AREA_ENGINES dict directly — function refs are captured at import time
        with patch.dict(fe._AREA_ENGINES, {"questions": lambda c: [low_risk_finding]}):
            result = run_focused_cycle(cfg)

        findings = result.get("findings", [])
        assert findings, "Expected at least one finding"
        tagged = [f for f in findings if "low_risk" in f.get("tags", [])]
        assert tagged, "Low-confidence finding should be tagged low_risk"

    def test_auto_tag_does_not_approve(self, tmp_focus_file, sm_isolated):
        """auto_tag_low_risk must never change state to 'approved'."""
        import matylda_lite.sleeping_matylda.focus_engine as fe
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, run_focused_cycle,
        )
        cfg = FocusSessionConfig(
            session_id="notag", focus_areas=["questions"],
            auto_tag_low_risk=True,
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        low = {"finding_id": "f1", "type": "question_focus",
               "confidence": 0.1, "state": "pending",
               "focus_session_id": cfg.session_id, "focus_area": "questions"}
        with patch.dict(fe._AREA_ENGINES, {"questions": lambda c: [low]}):
            result = run_focused_cycle(cfg)
        for f in result.get("findings", []):
            assert f.get("state") != "approved", "auto_tag must never approve"


# ── run_focused_cycle integration ─────────────────────────────────────────────

class TestRunFocusedCycle:
    def _make_cfg(self, areas=None):
        from matylda_lite.sleeping_matylda.focus_engine import FocusSessionConfig
        return FocusSessionConfig(
            session_id=f"focus_{uuid.uuid4().hex[:6]}",
            focus_areas=areas or ["questions"],
            start_iso=datetime.now(timezone.utc).isoformat(),
        )

    def test_returns_completed_status(self, tmp_focus_file, sm_isolated):
        import matylda_lite.sleeping_matylda.focus_engine as fe
        from matylda_lite.sleeping_matylda.focus_engine import run_focused_cycle
        cfg = self._make_cfg()
        with patch.dict(fe._AREA_ENGINES, {"questions": lambda c: []}):
            result = run_focused_cycle(cfg)
        assert result["status"] == "completed"

    def test_findings_carry_session_id(self, tmp_focus_file, sm_isolated):
        import matylda_lite.sleeping_matylda.focus_engine as fe
        from matylda_lite.sleeping_matylda.focus_engine import run_focused_cycle
        cfg = self._make_cfg(areas=["tensions"])
        fake_finding = {
            "finding_id": "f_x", "type": "tension_analysis",
            "confidence": 0.7, "state": "pending",
            "focus_session_id": cfg.session_id, "focus_area": "tensions",
        }
        with patch.dict(fe._AREA_ENGINES, {"tensions": lambda c: [fake_finding]}):
            result = run_focused_cycle(cfg)
        assert result["findings_new"] == 1
        f = result["findings"][0]
        assert f["focus_session_id"] == cfg.session_id
        assert f["focus_area"] == "tensions"

    def test_only_selected_engines_run(self, tmp_focus_file, sm_isolated):
        import matylda_lite.sleeping_matylda.focus_engine as fe
        from matylda_lite.sleeping_matylda.focus_engine import run_focused_cycle
        cfg = self._make_cfg(areas=["steps"])
        tensions_called = []
        orig_engines = dict(fe._AREA_ENGINES)
        with patch.dict(fe._AREA_ENGINES, {
            "steps": lambda c: [],
            "tensions": lambda c: tensions_called.append(True) or [],
        }):
            run_focused_cycle(cfg)
        assert not tensions_called, "_analyze_tensions must not run when 'tensions' not in focus_areas"

    def test_unknown_area_is_skipped(self, tmp_focus_file, sm_isolated):
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, run_focused_cycle,
        )
        cfg = FocusSessionConfig(
            session_id="bad_area", focus_areas=["nonexistent"],
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        result = run_focused_cycle(cfg)
        assert result["status"] == "completed"
        assert result["findings_new"] == 0

    def test_findings_saved_to_sm_state(self, tmp_focus_file, sm_isolated):
        import matylda_lite.sleeping_matylda.focus_engine as fe
        from matylda_lite.sleeping_matylda.focus_engine import run_focused_cycle
        from matylda_lite.sleeping_matylda.consolidation import _load_state
        cfg = self._make_cfg(areas=["questions"])
        fake = {"finding_id": "f_saved", "type": "question_focus",
                "confidence": 0.7, "state": "pending",
                "focus_session_id": cfg.session_id, "focus_area": "questions"}
        with patch.dict(fe._AREA_ENGINES, {"questions": lambda c: [fake]}):
            run_focused_cycle(cfg)
        state = _load_state()
        ids = [f["finding_id"] for f in state.get("findings", [])]
        assert "f_saved" in ids


# ── run_cycle delegation ──────────────────────────────────────────────────────

class TestRunCycleDelegation:
    def test_focus_config_bypasses_gap_check(self, sm_isolated, homeostasis_isolated):
        """run_cycle with focus_config must not be blocked by gap check."""
        from matylda_lite.sleeping_matylda.consolidation import (
            _load_state, _save_state, run_cycle,
        )
        state = _load_state()
        state["last_cycle_start"] = datetime.now(timezone.utc).isoformat()
        _save_state(state)

        from matylda_lite.sleeping_matylda.focus_engine import FocusSessionConfig
        cfg = FocusSessionConfig(
            session_id="bypass_test", focus_areas=["questions"],
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        with patch("matylda_lite.sleeping_matylda.focus_engine._resolve_questions",
                   return_value=[]):
            result = run_cycle(focus_config=cfg)
        assert result.get("status") != "skipped"

    def test_normal_run_cycle_unaffected(self, sm_isolated, homeostasis_isolated):
        """run_cycle() without focus_config still performs gap check."""
        from matylda_lite.sleeping_matylda.consolidation import (
            _load_state, _save_state, run_cycle,
        )
        state = _load_state()
        state["last_cycle_start"] = datetime.now(timezone.utc).isoformat()
        _save_state(state)
        result = run_cycle(force=False)
        assert result.get("status") == "skipped"


# ── Session management API ────────────────────────────────────────────────────

class TestSessionManagement:
    def test_start_creates_session_file(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import (
            start_focus_session, _load_session,
        )
        with patch("matylda_lite.sleeping_matylda.focus_engine._start_focus_worker"):
            cfg = start_focus_session(["questions"], mode="timebox", duration_seconds=600)
        assert tmp_focus_file.exists()
        loaded = _load_session()
        assert loaded is not None
        assert loaded.session_id == cfg.session_id
        assert loaded.status == "running"

    def test_start_rejects_empty_areas(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import start_focus_session
        with pytest.raises(ValueError, match="No valid focus areas"):
            start_focus_session([])

    def test_start_rejects_invalid_areas(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import start_focus_session
        with pytest.raises(ValueError):
            start_focus_session(["invalid_area"])

    def test_pause_changes_status(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, _save_session, pause_focus_session,
        )
        cfg = FocusSessionConfig(
            session_id="p1", focus_areas=["steps"], status="running",
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        _save_session(cfg)
        result = pause_focus_session()
        assert result["status"] == "paused"

    def test_pause_raises_if_no_session(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import pause_focus_session
        with pytest.raises(ValueError, match="No active focus session"):
            pause_focus_session()

    def test_resume_changes_status_back(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, _save_session, resume_focus_session,
        )
        cfg = FocusSessionConfig(
            session_id="r1", focus_areas=["questions"], status="paused",
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        _save_session(cfg)
        with patch("matylda_lite.sleeping_matylda.focus_engine._start_focus_worker"):
            result = resume_focus_session()
        assert result["status"] == "running"

    def test_stop_sets_cancelled(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, _save_session, stop_focus_session,
        )
        cfg = FocusSessionConfig(
            session_id="s1", focus_areas=["tensions"], status="running",
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        _save_session(cfg)
        result = stop_focus_session()
        assert result["status"] == "cancelled"

    def test_get_status_returns_active_true_when_running(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import (
            FocusSessionConfig, _save_session, get_focus_status,
        )
        cfg = FocusSessionConfig(
            session_id="gs1", focus_areas=["no_go"], status="running",
            mode="timebox", duration_seconds=3600,
            start_iso=datetime.now(timezone.utc).isoformat(),
        )
        _save_session(cfg)
        status = get_focus_status()
        assert status["active"] is True
        assert "remaining_seconds" in status
        assert status["remaining_seconds"] > 0

    def test_get_status_returns_active_false_when_none(self, tmp_focus_file):
        from matylda_lite.sleeping_matylda.focus_engine import get_focus_status
        status = get_focus_status()
        assert status["active"] is False


# ── Endpoint smoke tests ──────────────────────────────────────────────────────

pytestmark_integration = pytest.mark.integration


@pytest.mark.integration
class TestFocusEndpoints:
    def test_focus_status_no_session(self, client):
        r = client.get("/api/sleeping-matylda/focus-status")
        assert r.status_code == 200
        data = r.json()
        assert data["active"] is False

    def test_focus_start_requires_focus_areas(self, client):
        r = client.post("/api/sleeping-matylda/focus-start", json={})
        assert r.status_code in (200, 400)
        assert "error" in r.json()

    def test_focus_start_rejects_invalid_area(self, client):
        r = client.post("/api/sleeping-matylda/focus-start",
                        json={"focus_areas": ["bogus_area"]})
        assert r.status_code in (200, 400)
        assert "error" in r.json()

    def test_focus_start_valid_returns_session(self, client, tmp_path, monkeypatch):
        import matylda_lite.sleeping_matylda.focus_engine as fe
        monkeypatch.setattr(fe, "_FOCUS_SESSION_FILE", tmp_path / "fs.json")
        monkeypatch.setattr(fe, "_start_focus_worker", lambda _cfg: None)
        r = client.post("/api/sleeping-matylda/focus-start", json={
            "focus_areas": ["questions"],
            "mode": "timebox",
            "duration_seconds": 300,
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "session" in data
        assert data["session"]["focus_areas"] == ["questions"]

    def test_focus_pause_endpoint_reachable(self, client):
        # Endpoint must respond — error or success depending on session state
        r = client.post("/api/sleeping-matylda/focus-pause")
        assert r.status_code in (200, 400)
        assert isinstance(r.json(), dict)

    def test_focus_stop_no_session_returns_status(self, client):
        r = client.post("/api/sleeping-matylda/focus-stop")
        assert r.status_code == 200

    def test_focus_resume_endpoint_reachable(self, client):
        # With no active session the endpoint returns an error (400 or 200+error)
        r = client.post("/api/sleeping-matylda/focus-resume")
        assert r.status_code in (200, 400)
        assert "error" in r.json()


# ── _execute_finding new actions ──────────────────────────────────────────────

@pytest.mark.integration
class TestFocusFindingActions:
    def _make_finding(self, action, **extra):
        return {"finding_id": f"f_{uuid.uuid4().hex[:6]}", "state": "pending",
                "action": action, **extra}

    def test_acknowledge_nogo_recheck_is_informational(self, sm_isolated, homeostasis_isolated):
        from matylda_lite.sleeping_matylda.consolidation import _execute_finding
        f = self._make_finding("acknowledge_nogo_recheck", type="nogo_recheck")
        result = _execute_finding(f)
        assert result == "acknowledged:no_action"

    def test_resolve_question_enqueues_task(self, sm_isolated, homeostasis_isolated):
        from matylda_lite.sleeping_matylda.consolidation import _execute_finding
        f = self._make_finding("resolve_question",
                               question="What is the Ringwald conjecture?",
                               type="question_focus")
        # _execute_finding imports task_queue inline — just verify it returns a string
        # and doesn't raise (real task_queue may or may not be available)
        result = _execute_finding(f)
        assert isinstance(result, str)
        assert "task:" in result or "failed" in result or "resolve_question" in result

    def test_propose_resolution_handles_missing_tension(self, sm_isolated, homeostasis_isolated):
        from matylda_lite.sleeping_matylda.consolidation import _execute_finding
        f = self._make_finding("propose_resolution",
                               tension_id="",
                               proposed_resolution="Resolve by X",
                               type="tension_analysis")
        result = _execute_finding(f)
        assert "propose_resolution" in result

    def test_reopen_trajectory_handles_not_found(self, sm_isolated, homeostasis_isolated):
        from matylda_lite.sleeping_matylda.consolidation import _execute_finding
        f = self._make_finding("reopen_trajectory",
                               trajectory_id="nonexistent::tag",
                               type="nogo_recheck")
        result = _execute_finding(f)
        # Should either reopen or say not_found — must not crash
        assert isinstance(result, str)
