"""Tests for matylda_lite.perception — SessionState + DistilledContext."""
from __future__ import annotations

import pytest

from matylda_lite.chronicle import build_chronicle_event
from matylda_lite.perception import (
    DistilledContext,
    SessionState,
    build_session_state,
    distill_context,
)
from tests.conftest import make_event


# ── Helpers ───────────────────────────────────────────────────────────────────

def _events(*overrides):
    """Build a list of ChronicleEvents for testing."""
    return [make_event(**kw) for kw in overrides]


# ── SessionState ──────────────────────────────────────────────────────────────

class TestSessionState:
    def test_build_from_empty_events(self):
        state = build_session_state([], project_id="p1", domain="research")
        assert isinstance(state, SessionState)
        assert state.project_id == "p1"
        assert state.active_files == ()
        assert state.recent_artifacts == ()
        assert state.current_task is None
        assert state.inferred_intent is None

    def test_active_files_from_context_ref(self):
        evs = _events({"context_ref": "desk/ACTIVE.md"}, {"context_ref": "desk/ACTIVE.md"})
        state = build_session_state(evs, project_id="p1", domain="research")
        # deduplication: same ref appears once
        assert "desk/ACTIVE.md" in state.active_files
        assert state.active_files.count("desk/ACTIVE.md") == 1

    def test_recent_artifacts_from_metadata(self):
        ev = make_event(
            event_type="memory_signal",
            context_ref="art_001",
        )
        state = build_session_state([ev], project_id="p1", domain="research")
        assert "art_001" in state.recent_artifacts

    def test_inferred_intent_from_metadata(self):
        ev = make_event(metadata={"recommended_next_step": "Run replication study"})
        state = build_session_state([ev], project_id="p1", domain="research")
        assert state.inferred_intent == "Run replication study"

    def test_source_event_ids_collected(self):
        evs = [
            make_event(timestamp="2026-01-01T00:00:00+00:00"),
            make_event(timestamp="2026-01-01T00:00:01+00:00", source="darkroom"),
        ]
        state = build_session_state(evs, project_id="p1", domain="research")
        assert len(state.source_event_ids) == 2

    def test_as_dict_has_all_keys(self):
        state = build_session_state([], project_id="p1", domain="research")
        d = state.as_dict()
        for k in ("project_id", "domain", "active_files", "recent_artifacts",
                  "current_task", "inferred_intent", "source_event_ids"):
            assert k in d


# ── DistilledContext ──────────────────────────────────────────────────────────

class TestDistilledContext:
    def _distill(self, events=None, project_id="p1", domain="research"):
        evs = events or []
        state = build_session_state(evs, project_id=project_id, domain=domain)
        return distill_context(evs, state, project_id=project_id, domain=domain)

    def test_returns_distilled_context(self):
        ctx = self._distill()
        assert isinstance(ctx, DistilledContext)

    def test_confidence_minimum_with_no_events(self):
        ctx = self._distill([])
        # Base confidence = 0.25 with zero events
        assert ctx.confidence == pytest.approx(0.25)

    def test_confidence_grows_with_events(self):
        evs = [
            make_event(timestamp=f"2026-01-01T00:00:0{i}+00:00", source="secretary")
            for i in range(5)
        ]
        ctx = self._distill(evs)
        assert ctx.confidence > 0.25

    def test_confidence_capped_at_095(self):
        # 20 events + all signal types — confidence must not exceed 0.95
        evs = (
            [make_event(timestamp=f"2026-01-01T00:00:{i:02d}+00:00", source="secretary")
             for i in range(10)]
            + [make_event(timestamp=f"2026-01-01T00:01:{i:02d}+00:00", source="darkroom")
               for i in range(10)]
        )
        ctx = self._distill(evs)
        assert ctx.confidence <= 0.95

    def test_summary_mentions_project(self):
        ctx = self._distill(project_id="zeta_proj")
        assert "zeta_proj" in ctx.summary

    def test_inferred_goal_non_empty(self):
        ctx = self._distill()
        assert ctx.inferred_goal.strip()

    def test_context_id_deterministic_for_same_events(self):
        evs = [make_event(timestamp="2026-01-01T00:00:00+00:00")]
        ctx1 = self._distill(evs)
        ctx2 = self._distill(evs)
        assert ctx1.context_id == ctx2.context_id

    def test_as_context_prefix_is_string(self):
        ctx = self._distill()
        prefix = ctx.as_context_prefix()
        assert isinstance(prefix, str)

    def test_as_context_prefix_contains_header(self):
        ctx = self._distill()
        prefix = ctx.as_context_prefix()
        assert "KONTEKST SESJI" in prefix or "Perception" in prefix or "summary" in prefix.lower()

    def test_as_dict_round_trip(self):
        ctx = self._distill()
        d = ctx.as_dict()
        for k in ("context_id", "created_at", "project_id", "domain",
                  "summary", "inferred_goal", "confidence"):
            assert k in d
        assert isinstance(d["confidence"], float)
        assert isinstance(d["source_event_ids"], list)
