"""Perception — SessionState + DistilledContext dla Matylda Lab.

Buduje "co jest aktywne w tej sesji" z historii ChronicleEventów.
Wynik (DistilledContext) może być przekazany do Secretary przed zapytaniem
lub do Sleeping Matylda synthesis jako dodatkowy kontekst.

Zaadaptowane z Matylda Full perception/session_state.py + distillation.py.
Uproszczenia: brak zależności od capture.py (Full workbench API).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import ROOT
from .chronicle import ChronicleEvent, list_recent_events

DISTILLED_LOG = ROOT / "logs" / "perception" / "distilled.jsonl"
DISTILLED_LOG.parent.mkdir(parents=True, exist_ok=True)


# ── SessionState ───────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SessionState:
    """What is active in the current working session.

    Derived from a window of ChronicleEvents.
    """
    project_id: str
    domain: str
    active_files: tuple[str, ...]       = ()   # context_refs from events
    recent_artifacts: tuple[str, ...]   = ()   # artifact refs from event metadata
    current_task: str | None            = None  # last known task_id
    inferred_intent: str | None         = None  # last recommended_next_step
    source_event_ids: tuple[str, ...]   = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id",      _clean(self.project_id) or "unknown")
        object.__setattr__(self, "domain",           _clean(self.domain) or "unknown")
        object.__setattr__(self, "active_files",     _dedup_tuple(self.active_files))
        object.__setattr__(self, "recent_artifacts", _dedup_tuple(self.recent_artifacts))
        object.__setattr__(self, "current_task",     _clean(self.current_task))
        object.__setattr__(self, "inferred_intent",  _clean(self.inferred_intent))
        object.__setattr__(self, "source_event_ids", _dedup_tuple(self.source_event_ids))

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id":      self.project_id,
            "domain":          self.domain,
            "active_files":    list(self.active_files),
            "recent_artifacts": list(self.recent_artifacts),
            "current_task":    self.current_task,
            "inferred_intent": self.inferred_intent,
            "source_event_ids": list(self.source_event_ids),
        }


# ── DistilledContext ───────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class DistilledContext:
    """A condensed snapshot of what the system has been doing lately.

    Passed to Secretary as context prefix, or to Sleeping Matylda synthesis.
    """
    context_id: str
    created_at: str
    project_id: str
    domain: str
    summary: str
    relevant_artifacts: tuple[str, ...]
    active_files: tuple[str, ...]
    inferred_goal: str
    confidence: float
    source_event_ids: tuple[str, ...]
    review_required: bool = True
    canonical: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", max(0.0, min(1.0, float(self.confidence))))
        object.__setattr__(self, "relevant_artifacts", _dedup_tuple(self.relevant_artifacts))
        object.__setattr__(self, "active_files",       _dedup_tuple(self.active_files))
        object.__setattr__(self, "source_event_ids",   _dedup_tuple(self.source_event_ids))

    def as_dict(self) -> dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "created_at":        self.created_at,
            "project_id":        self.project_id,
            "domain":            self.domain,
            "summary":           self.summary,
            "relevant_artifacts": list(self.relevant_artifacts),
            "active_files":      list(self.active_files),
            "inferred_goal":     self.inferred_goal,
            "confidence":        self.confidence,
            "source_event_ids":  list(self.source_event_ids),
            "review_required":   self.review_required,
            "canonical":         self.canonical,
        }

    def as_context_prefix(self) -> str:
        """Format as a context string suitable for injecting into prompts."""
        lines = [
            "=== KONTEKST SESJI ===",
            f"Projekt: {self.project_id} | Domena: {self.domain}",
            f"Zaufanie: {self.confidence:.0%}",
            f"Cel sesji: {self.inferred_goal}",
            self.summary,
        ]
        if self.active_files:
            lines.append("Aktywne pliki: " + ", ".join(list(self.active_files)[:5]))
        if self.relevant_artifacts:
            lines.append("Ostatnie artefakty: " + ", ".join(list(self.relevant_artifacts)[:5]))
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DistilledContext":
        return cls(
            context_id=str(d.get("context_id") or ""),
            created_at=str(d.get("created_at") or ""),
            project_id=str(d.get("project_id") or ""),
            domain=str(d.get("domain") or ""),
            summary=str(d.get("summary") or ""),
            relevant_artifacts=tuple(d.get("relevant_artifacts") or ()),
            active_files=tuple(d.get("active_files") or ()),
            inferred_goal=str(d.get("inferred_goal") or ""),
            confidence=float(d.get("confidence") or 0.0),
            source_event_ids=tuple(d.get("source_event_ids") or ()),
            review_required=bool(d.get("review_required", True)),
            canonical=bool(d.get("canonical", False)),
        )


# ── Build functions ────────────────────────────────────────────────────────────

def build_session_state(
    events: Iterable[ChronicleEvent],
    *,
    project_id: str,
    domain: str,
) -> SessionState:
    """Derive SessionState from a sequence of ChronicleEvents."""
    rows = list(events)

    active_files = _dedup_tuple(
        [ev.context_ref for ev in rows if ev.context_ref]
        + [
            path
            for ev in rows
            for path in ev.metadata.get("source_paths", [])
            if _clean(path)
        ]
    )
    recent_artifacts = _dedup_tuple(
        [
            aid
            for ev in rows
            for aid in ev.metadata.get("source_artifact_ids", [])
            if _clean(aid)
        ]
        + [
            ev.context_ref
            for ev in rows
            if ev.event_type == "memory_signal" and ev.context_ref
        ]
    )
    current_task = _last_nonempty(
        [ev.metadata.get("task_id") for ev in rows]
        + [tid for ev in rows for tid in ev.metadata.get("task_ids", [])]
    )
    inferred_intent = _last_nonempty(
        [ev.metadata.get("recommended_next_step") for ev in rows]
        + [ev.metadata.get("intelligence_reason") for ev in rows]
    )

    return SessionState(
        project_id=project_id,
        domain=domain,
        active_files=active_files,
        recent_artifacts=recent_artifacts,
        current_task=current_task,
        inferred_intent=inferred_intent,
        source_event_ids=tuple(ev.event_id for ev in rows),
    )


def distill_context(
    events: Iterable[ChronicleEvent],
    session_state: SessionState,
    *,
    project_id: str,
    domain: str,
) -> DistilledContext:
    """Distil a DistilledContext from ChronicleEvents + SessionState."""
    rows = list(events)

    dominant_workflows = _dedup_tuple(
        [ev.workflow_kind for ev in rows if ev.workflow_kind]
    )
    memory_signals      = [ev for ev in rows if ev.event_type == "memory_signal"]
    session_signals     = [ev for ev in rows if ev.event_type == "session_signal"]
    darkroom_signals    = [ev for ev in rows if ev.source == "darkroom"]
    sm_signals          = [ev for ev in rows if ev.source == "sleeping_matylda"]
    secretary_signals   = [ev for ev in rows if ev.source == "secretary"]

    inferred_goal = (
        session_state.inferred_intent
        or _first_nonempty([ev.metadata.get("recommended_next_step") for ev in memory_signals + rows])
        or "Inspect recent workflow activity before broadening context."
    )

    summary_parts = [
        f"Perception summary for {project_id} ({domain}): {len(rows)} recent event(s).",
    ]
    if dominant_workflows:
        summary_parts.append("Workflows: " + ", ".join(dominant_workflows[:3]) + ".")
    if secretary_signals:
        summary_parts.append(f"{len(secretary_signals)} Secretary interaction(s) logged.")
    if darkroom_signals:
        summary_parts.append(f"{len(darkroom_signals)} DARKROOM review(s) in recent history.")
    if sm_signals:
        summary_parts.append("Sleeping Matylda synthesis was recently active.")
    if session_state.active_files:
        summary_parts.append(f"{len(session_state.active_files)} active context reference(s).")
    if memory_signals:
        summary_parts.append("Memory write pressure visible in signal trace.")

    # Confidence grows with more evidence
    confidence = min(
        0.95,
        0.25
        + min(len(rows), 10) * 0.05
        + (0.10 if bool(session_state.active_files) else 0.0)
        + (0.08 if bool(session_state.recent_artifacts) else 0.0)
        + (0.06 if bool(session_signals) else 0.0)
        + (0.06 if bool(memory_signals) else 0.0)
        + (0.05 if bool(darkroom_signals) else 0.0)
        + (0.05 if bool(sm_signals) else 0.0)
    )

    context_id = _make_context_id(project_id, session_state.source_event_ids)

    return DistilledContext(
        context_id=context_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        project_id=project_id,
        domain=domain,
        summary=" ".join(summary_parts),
        relevant_artifacts=session_state.recent_artifacts,
        active_files=session_state.active_files,
        inferred_goal=inferred_goal,
        confidence=confidence,
        source_event_ids=session_state.source_event_ids,
    )


def get_current_session_context(
    project_id: str = "lite",
    domain: str = "research",
    event_limit: int = 30,
    persist: bool = True,
) -> DistilledContext | None:
    """One-shot facade: read recent events → build SessionState → distill.

    Args:
        project_id:  Filter events by project (empty = all).
        domain:      Filter events by domain (empty = all).
        event_limit: How many recent events to consider.
        persist:     Whether to append the result to distilled.jsonl.

    Returns:
        DistilledContext or None if no events available.
    """
    events = list_recent_events(
        limit=event_limit,
        project_id=project_id if project_id != "lite" else "",
        domain=domain if domain != "research" else "",
    )
    # Reverse to chronological order for processing
    events = list(reversed(events))

    if not events:
        return None

    state = build_session_state(events, project_id=project_id, domain=domain)
    ctx   = distill_context(events, state, project_id=project_id, domain=domain)

    if persist:
        _save_distilled_context(ctx)

    return ctx


def load_last_distilled_context() -> DistilledContext | None:
    """Return the most recently saved DistilledContext, or None."""
    if not DISTILLED_LOG.exists():
        return None
    try:
        lines = DISTILLED_LOG.read_text(encoding="utf-8").splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                return DistilledContext.from_dict(d)
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    return None


def _save_distilled_context(ctx: DistilledContext) -> None:
    with DISTILLED_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ctx.as_dict(), ensure_ascii=False) + "\n")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedup_tuple(values: Iterable[object | None]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for v in values:
        text = _clean(v)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _first_nonempty(values: Iterable[object | None]) -> str | None:
    for v in values:
        text = _clean(v)
        if text:
            return text
    return None


def _last_nonempty(values: Iterable[object | None]) -> str | None:
    last: str | None = None
    for v in values:
        text = _clean(v)
        if text:
            last = text
    return last


def _make_context_id(project_id: str, source_event_ids: tuple[str, ...]) -> str:
    digest = json.dumps([project_id, *source_event_ids], ensure_ascii=True).encode()
    return "distilled:" + hashlib.sha1(digest).hexdigest()[:12]
