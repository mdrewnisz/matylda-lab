"""Chronicle — deterministyczny event log Matylda Lab.

Każde działanie systemu (Secretary, DARKROOM, silo, SM synthesis) może być
zapisane jako immutable ChronicleEvent z SHA1-hashowanym event_id.

Zastosowania:
  - Fundament observability (co system zrobił w tej sesji)
  - Wejście do Sleeping Matylda synthesis (historia kontekstu)
  - Wejście do perception.py (SessionState + DistilledContext)
  - Deduplication events (SHA1 gwarantuje unikalność tych samych zdarzeń)

Zaadaptowane z Matylda Full perception/events.py (v0.3f).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import ROOT

CHRONICLE_LOG = ROOT / "logs" / "chronicle.jsonl"
CHRONICLE_LOG.parent.mkdir(parents=True, exist_ok=True)

# Maksymalna liczba eventów trzymanych w pamięci przy list_recent_events
_DEFAULT_LIMIT = 100


# ── Core types ─────────────────────────────────────────────────────────────────

def build_chronicle_event(
    *,
    source: str,
    event_type: str,
    project_id: str = "lite",
    domain: str = "research",
    workflow_kind: str | None = None,
    context_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    timestamp: str | None = None,
) -> "ChronicleEvent":
    """Build a deterministically hashable ChronicleEvent.

    event_id is SHA1 of (timestamp, source, event_type, project_id, domain,
    workflow_kind, context_ref, metadata) — guarantees deduplication.
    """
    event_timestamp = _clean(timestamp) or datetime.now(timezone.utc).isoformat()
    norm_meta = _normalize_metadata(metadata)
    digest_seed = {
        "timestamp": event_timestamp,
        "source": source,
        "event_type": event_type,
        "project_id": project_id,
        "domain": domain,
        "workflow_kind": workflow_kind,
        "context_ref": context_ref,
        "metadata": norm_meta,
    }
    event_hash = hashlib.sha1(
        json.dumps(digest_seed, sort_keys=True, ensure_ascii=True, default=str).encode()
    ).hexdigest()[:12]
    return ChronicleEvent(
        event_id=f"chronicle:{event_hash}",
        timestamp=event_timestamp,
        source=source,
        event_type=event_type,
        project_id=project_id,
        domain=domain,
        workflow_kind=workflow_kind,
        context_ref=context_ref,
        metadata=dict(norm_meta),
    )


@dataclass(frozen=True, slots=True)
class ChronicleEvent:
    event_id: str
    timestamp: str
    source: str
    event_type: str
    project_id: str
    domain: str
    workflow_kind: str | None = None
    context_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id",    _require(self.event_id,    "event_id"))
        object.__setattr__(self, "timestamp",   _require(self.timestamp,   "timestamp"))
        object.__setattr__(self, "source",      _require(self.source,      "source"))
        object.__setattr__(self, "event_type",  _require(self.event_type,  "event_type"))
        object.__setattr__(self, "project_id",  _require(self.project_id,  "project_id"))
        object.__setattr__(self, "domain",      _require(self.domain,      "domain"))
        object.__setattr__(self, "workflow_kind", _clean(self.workflow_kind))
        object.__setattr__(self, "context_ref",   _clean(self.context_ref))
        object.__setattr__(self, "metadata",      dict(_normalize_metadata(self.metadata)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "timestamp":    self.timestamp,
            "source":       self.source,
            "event_type":   self.event_type,
            "project_id":   self.project_id,
            "domain":       self.domain,
            "workflow_kind": self.workflow_kind,
            "context_ref":  self.context_ref,
            "metadata":     dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ChronicleEvent":
        return cls(
            event_id=str(payload.get("event_id") or ""),
            timestamp=str(payload.get("timestamp") or ""),
            source=str(payload.get("source") or ""),
            event_type=str(payload.get("event_type") or ""),
            project_id=str(payload.get("project_id") or ""),
            domain=str(payload.get("domain") or ""),
            workflow_kind=_clean(payload.get("workflow_kind")),
            context_ref=_clean(payload.get("context_ref")),
            metadata=dict(payload.get("metadata") or {}),
        )


# ── Persistence ────────────────────────────────────────────────────────────────

def log_event(event: ChronicleEvent) -> None:
    """Append a ChronicleEvent to the JSONL log. Thread-safe via append mode."""
    with CHRONICLE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.as_dict(), ensure_ascii=False) + "\n")


def log_and_build(
    *,
    source: str,
    event_type: str,
    project_id: str = "lite",
    domain: str = "research",
    workflow_kind: str | None = None,
    context_ref: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ChronicleEvent:
    """Build, log, and return a ChronicleEvent in one call."""
    event = build_chronicle_event(
        source=source,
        event_type=event_type,
        project_id=project_id,
        domain=domain,
        workflow_kind=workflow_kind,
        context_ref=context_ref,
        metadata=metadata,
    )
    log_event(event)
    return event


def list_recent_events(
    limit: int = _DEFAULT_LIMIT,
    project_id: str = "",
    domain: str = "",
    event_type: str = "",
    source: str = "",
) -> list[ChronicleEvent]:
    """Return the most recent N ChronicleEvents from the log (newest first).

    Optional filters: project_id, domain, event_type, source.
    """
    if not CHRONICLE_LOG.exists():
        return []

    rows: list[ChronicleEvent] = []
    try:
        lines = CHRONICLE_LOG.read_text(encoding="utf-8").splitlines()
    except Exception:  # noqa: BLE001
        return []

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            ev = ChronicleEvent.from_dict(d)
        except Exception:  # noqa: BLE001
            continue
        if project_id and ev.project_id != project_id:
            continue
        if domain and ev.domain != domain:
            continue
        if event_type and ev.event_type != event_type:
            continue
        if source and ev.source != source:
            continue
        rows.append(ev)
        if len(rows) >= limit:
            break

    return rows


def list_events_as_dicts(limit: int = _DEFAULT_LIMIT, **filters) -> list[dict]:
    """Convenience wrapper returning plain dicts (for API responses)."""
    return [ev.as_dict() for ev in list_recent_events(limit=limit, **filters)]


# ── Convenience builders per subsystem ────────────────────────────────────────

def log_secretary_event(
    task: str,
    model: str = "",
    saved_as: str | None = None,
    project_id: str = "lite",
    success: bool = True,
) -> ChronicleEvent:
    """Log a Secretary chat event."""
    return log_and_build(
        source="secretary",
        event_type="secretary_chat",
        project_id=project_id,
        domain="research",
        context_ref=saved_as,
        metadata={
            "task_preview": task[:120],
            "model": model,
            "success": success,
        },
    )


def log_darkroom_event(
    text_preview: str,
    flags_count: int = 0,
    tension_ids: list[str] | None = None,
    project_id: str = "lite",
) -> ChronicleEvent:
    """Log a DARKROOM review event."""
    return log_and_build(
        source="darkroom",
        event_type="darkroom_review",
        project_id=project_id,
        domain="research",
        metadata={
            "text_preview": text_preview[:80],
            "flags_count": flags_count,
            "tension_ids": tension_ids or [],
        },
    )


def log_silo_event(
    silo_id: str,
    skill_id: str,
    project_id: str = "lite",
    model_used: str = "",
) -> ChronicleEvent:
    """Log a Silo skill execution event."""
    return log_and_build(
        source=f"silo:{silo_id}",
        event_type="silo_skill",
        project_id=project_id,
        domain="science",
        workflow_kind=skill_id,
        metadata={
            "silo_id": silo_id,
            "skill_id": skill_id,
            "model_used": model_used,
        },
    )


def log_sm_synthesis_event(
    project_id: str = "lite",
    open_threads_count: int = 0,
    warnings: list[str] | None = None,
) -> ChronicleEvent:
    """Log a Sleeping Matylda synthesis event."""
    return log_and_build(
        source="sleeping_matylda",
        event_type="sm_synthesis",
        project_id=project_id,
        domain="research",
        metadata={
            "open_threads_count": open_threads_count,
            "warnings": warnings or [],
        },
    )


def log_memory_event(
    action: str,
    insight_id: str = "",
    kind: str = "",
    project_id: str = "lite",
) -> ChronicleEvent:
    """Log a memory write/promote/archive event."""
    return log_and_build(
        source="memory",
        event_type=f"memory_{action}",
        project_id=project_id,
        domain="research",
        context_ref=insight_id or None,
        metadata={"action": action, "kind": kind},
    )


# ── Internal helpers ───────────────────────────────────────────────────────────

def _require(value: object, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"ChronicleEvent.{field_name} cannot be empty.")
    return normalized


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_metadata(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    return {str(k).strip(): v for k, v in payload.items() if str(k).strip()}
