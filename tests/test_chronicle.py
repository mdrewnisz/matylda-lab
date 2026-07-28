"""Tests for matylda_lite.chronicle — immutable event log."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from matylda_lite.chronicle import (
    ChronicleEvent,
    build_chronicle_event,
    list_recent_events,
    list_events_as_dicts,
    log_and_build,
    log_event,
    log_secretary_event,
    log_silo_event,
    log_sm_synthesis_event,
    log_memory_event,
)
from tests.conftest import make_event


# ── build_chronicle_event (pure, no I/O) ─────────────────────────────────────

class TestBuildChronicleEvent:
    def test_returns_chronicle_event(self):
        ev = make_event()
        assert isinstance(ev, ChronicleEvent)

    def test_event_id_starts_with_chronicle(self):
        ev = make_event()
        assert ev.event_id.startswith("chronicle:")

    def test_event_id_deterministic_given_timestamp(self):
        ts = "2026-01-01T00:00:00+00:00"
        ev1 = make_event(timestamp=ts)
        ev2 = make_event(timestamp=ts)
        assert ev1.event_id == ev2.event_id

    def test_different_source_different_id(self):
        ts = "2026-01-01T00:00:00+00:00"
        ev1 = make_event(source="secretary", timestamp=ts)
        ev2 = make_event(source="darkroom", timestamp=ts)
        assert ev1.event_id != ev2.event_id

    def test_fields_preserved(self):
        ev = make_event(
            source="silo_1",
            event_type="skill_run",
            project_id="myproj",
            domain="science",
            workflow_kind="paper_review",
            context_ref="desk/FOO.md",
        )
        assert ev.source == "silo_1"
        assert ev.event_type == "skill_run"
        assert ev.project_id == "myproj"
        assert ev.domain == "science"
        assert ev.workflow_kind == "paper_review"
        assert ev.context_ref == "desk/FOO.md"

    def test_metadata_normalised_to_dict(self):
        ev = make_event(metadata={"key": "val"})
        assert ev.metadata == {"key": "val"}

    def test_none_metadata_becomes_empty_dict(self):
        ev = make_event(metadata=None)
        assert ev.metadata == {}

    def test_as_dict_round_trip(self):
        ev = make_event()
        d = ev.as_dict()
        assert d["event_id"] == ev.event_id
        assert d["source"] == ev.source
        assert d["event_type"] == ev.event_type
        assert isinstance(d["metadata"], dict)


# ── log_event + list_recent_events (I/O, uses tmp_chronicle) ─────────────────

class TestLogAndList:
    def test_log_event_writes_to_file(self, tmp_chronicle: Path):
        ev = make_event(source="secretary", event_type="task_done", timestamp="2026-01-01T10:00:00+00:00")
        log_event(ev)
        lines = tmp_chronicle.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        stored = json.loads(lines[0])
        assert stored["event_id"] == ev.event_id

    def test_duplicate_event_has_same_event_id(self, tmp_chronicle: Path):
        # log_event appends unconditionally (write-path is append-only).
        # Deduplication is id-level: two calls produce the same event_id
        # but the log may contain both raw lines.
        ts = "2026-01-01T11:00:00+00:00"
        ev = make_event(source="secretary", timestamp=ts)
        log_event(ev)
        log_event(ev)
        import json as _json
        lines = [l for l in tmp_chronicle.read_text(encoding="utf-8").strip().splitlines() if l]
        ids = [_json.loads(l)["event_id"] for l in lines]
        # Both written lines share the same deterministic id
        assert all(i == ev.event_id for i in ids)

    def test_list_recent_events_empty_log(self, tmp_chronicle: Path):
        events = list_recent_events(limit=10)
        assert events == []

    def test_list_recent_events_returns_logged(self, tmp_chronicle: Path):
        ev = make_event(source="darkroom", event_type="review_done", timestamp="2026-01-02T00:00:00+00:00")
        log_event(ev)
        events = list_recent_events(limit=10)
        assert len(events) == 1
        assert events[0].event_id == ev.event_id

    def test_list_recent_events_limit(self, tmp_chronicle: Path):
        for i in range(5):
            ev = make_event(source="secretary", event_type="task_done",
                            timestamp=f"2026-01-0{i+1}T00:00:00+00:00")
            log_event(ev)
        events = list_recent_events(limit=3)
        assert len(events) == 3

    def test_list_recent_events_filter_source(self, tmp_chronicle: Path):
        log_event(make_event(source="secretary", event_type="x", timestamp="2026-01-10T00:00:00+00:00"))
        log_event(make_event(source="darkroom",  event_type="x", timestamp="2026-01-10T00:00:01+00:00"))
        events = list_recent_events(limit=10, source="darkroom")
        assert all(e.source == "darkroom" for e in events)
        assert len(events) == 1

    def test_list_recent_events_filter_project(self, tmp_chronicle: Path):
        log_event(make_event(project_id="proj_a", timestamp="2026-01-10T01:00:00+00:00"))
        log_event(make_event(project_id="proj_b", timestamp="2026-01-10T02:00:00+00:00"))
        events = list_recent_events(limit=10, project_id="proj_a")
        assert all(e.project_id == "proj_a" for e in events)

    def test_list_events_as_dicts_returns_dicts(self, tmp_chronicle: Path):
        log_event(make_event(source="secretary", timestamp="2026-01-20T00:00:00+00:00"))
        result = list_events_as_dicts(limit=5)
        assert all(isinstance(d, dict) for d in result)
        assert "event_id" in result[0]


# ── Convenience builders ──────────────────────────────────────────────────────

class TestConvenienceBuilders:
    def test_log_secretary_event(self, tmp_chronicle: Path):
        ev = log_secretary_event(task="write a summary", model="sonnet",
                                 saved_as="artifacts/out.md", project_id="p1")
        events = list_recent_events(limit=5)
        assert any(e.event_id == ev.event_id for e in events)
        assert ev.source == "secretary"

    def test_log_silo_event(self, tmp_chronicle: Path):
        ev = log_silo_event(silo_id="silo_1", skill_id="paper_review",
                            project_id="p1", model_used="opus")
        events = list_recent_events(limit=5)
        assert any(e.event_id == ev.event_id for e in events)
        # source is prefixed: "silo:<silo_id>"
        assert ev.source == "silo:silo_1"

    def test_log_sm_synthesis_event(self, tmp_chronicle: Path):
        ev = log_sm_synthesis_event(project_id="p1", open_threads_count=3, warnings=["w1"])
        events = list_recent_events(limit=5)
        assert any(e.event_id == ev.event_id for e in events)
        assert ev.source == "sleeping_matylda"
        assert ev.event_type == "sm_synthesis"

    def test_log_memory_event(self, tmp_chronicle: Path):
        ev = log_memory_event("trace_saved", "trace_abc123", "project_fact", "p1")
        events = list_recent_events(limit=5)
        assert any(e.event_id == ev.event_id for e in events)
        assert ev.source == "memory"

    def test_log_and_build_returns_event(self, tmp_chronicle: Path):
        ev = log_and_build(source="test_src", event_type="test_evt", project_id="p1")
        assert isinstance(ev, ChronicleEvent)
        assert ev.source == "test_src"
