"""Research continuity — strukturalne ślady sesji badawczych.

Po każdej sesji z umiejętnością silosu lub po hostile review można zapisać
ResearchProjectMemoryTrace — ustrukturyzowany zapis "co zrobiliśmy i co dalej".
Sleeping Matylda synthesis może odczytać te traces i budować bootstrap view
przy starcie nowej sesji.

Zaadaptowane z Matylda Full research/continuity.py (v0.3f).
Uproszczenia: usunięto zależność od matylda.core.artifacts.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import ROOT

# Traces zapisywane jako JSON w memory/insights/ z kind=project_fact
TRACES_DIR = ROOT / "memory" / "insights"
TRACES_DIR.mkdir(parents=True, exist_ok=True)

_TRACE_KIND = "research_project_memory_trace"


# ── Core dataclass ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ResearchProjectMemoryTrace:
    """Immutable record of what a research session produced and what to do next."""
    project_id: str
    workflow_kind: str
    title: str
    artifact_status: str
    recorded_at: str
    analyzed_object: str
    summary: str
    key_weakness: str
    recommended_next_step: str
    limitations: tuple[str, ...]
    question: str | None = None
    reference_artifact_path: str | None = None
    scope_summary: str | None = None
    session_start_hint: str | None = None
    trace_kind: str = _TRACE_KIND
    memory_scope: str = "project_working"
    review_required: bool = True
    canonical: bool = False
    completion_criteria: str = ""
    validation_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "trace_kind":             self.trace_kind,
            "project_id":             self.project_id,
            "workflow_kind":          self.workflow_kind,
            "title":                  self.title,
            "artifact_status":        self.artifact_status,
            "recorded_at":            self.recorded_at,
            "analyzed_object":        self.analyzed_object,
            "summary":                self.summary,
            "key_weakness":           self.key_weakness,
            "recommended_next_step":  self.recommended_next_step,
            "limitations":            list(self.limitations),
            "question":               self.question,
            "reference_artifact_path": self.reference_artifact_path,
            "scope_summary":          self.scope_summary,
            "session_start_hint":     self.session_start_hint,
            "memory_scope":           self.memory_scope,
            "review_required":        self.review_required,
            "canonical":              self.canonical,
            "completion_criteria":    self.completion_criteria,
            "validation_id":          self.validation_id,
        }

    def as_memory_content(self) -> str:
        """Serialise as flat key:value string for memory storage."""
        lines = [
            f"[{_TRACE_KIND}]",
            f"project: {self.project_id}",
            f"workflow: {self.workflow_kind}",
            f"title: {self.title}",
            f"recorded_at: {self.recorded_at}",
            f"artifact_status: {self.artifact_status}",
            f"memory_scope: {self.memory_scope}",
            f"review_required: {str(self.review_required).lower()}",
            f"canonical: {str(self.canonical).lower()}",
            f"analyzed_object: {self.analyzed_object}",
            f"summary: {self.summary}",
            f"key_weakness: {self.key_weakness}",
            f"recommended_next_step: {self.recommended_next_step}",
        ]
        if self.limitations:
            lines.append(f"limitations: {'; '.join(self.limitations)}")
        if self.question:
            lines.append(f"question: {self.question}")
        if self.reference_artifact_path:
            lines.append(f"reference_artifact_path: {self.reference_artifact_path}")
        if self.scope_summary:
            lines.append(f"scope_summary: {self.scope_summary}")
        if self.session_start_hint:
            lines.append(f"session_start_hint: {self.session_start_hint}")
        return "\n".join(lines)


# ── Builders ───────────────────────────────────────────────────────────────────

def build_research_project_memory_trace(
    result: Mapping[str, Any] | dict,
    *,
    recorded_at: str | None = None,
) -> ResearchProjectMemoryTrace:
    """Build a ResearchProjectMemoryTrace from a skill/research result dict.

    Supported workflow_kind values:
      paper_red_team, claim_support_map, silo_skill, generic
    """
    payload = dict(result) if isinstance(result, Mapping) else {}
    workflow_kind = _req(payload.get("workflow_kind"), "workflow_kind")
    project_id    = _opt(payload.get("project_id")) or "lite"
    title         = _req(payload.get("title"), "title")
    artifact_status = _opt(payload.get("artifact_status")) or "working"

    trace_payload = _trace_payload_for_workflow(workflow_kind, payload)

    return ResearchProjectMemoryTrace(
        project_id=project_id,
        workflow_kind=workflow_kind,
        title=title,
        artifact_status=artifact_status,
        recorded_at=recorded_at or _utc_now(),
        analyzed_object=trace_payload["analyzed_object"],
        summary=trace_payload["summary"],
        key_weakness=trace_payload["key_weakness"],
        recommended_next_step=trace_payload["recommended_next_step"],
        limitations=tuple(trace_payload.get("limitations", [])),
        question=_opt(trace_payload.get("question")),
        reference_artifact_path=_opt(trace_payload.get("reference_artifact_path")),
        scope_summary=_opt(trace_payload.get("scope_summary")),
        session_start_hint=_opt(trace_payload.get("session_start_hint")),
    )


def save_research_trace(trace: ResearchProjectMemoryTrace) -> dict:
    """Persist a ResearchProjectMemoryTrace to memory/insights/ as a JSON insight.

    Returns the saved insight dict with id, kind=project_fact, trace embedded.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    insight_id = "trace_" + uuid.uuid4().hex[:8]
    data = {
        "id": insight_id,
        "content": trace.as_memory_content(),
        "topic": f"[{trace.workflow_kind}] {trace.title}",
        "kind": "project_fact",
        "trace": trace.as_dict(),
        "linked_project": trace.project_id,
        "linked_thread": "",
        "created": today,
        "status": "active",
        "review_required": trace.review_required,
    }
    path = TRACES_DIR / f"{today}_{insight_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def load_research_traces(project_id: str = "") -> list[ResearchProjectMemoryTrace]:
    """Load all ResearchProjectMemoryTraces from memory/insights/.

    Optional project_id filter. Sorted by recorded_at desc.
    """
    traces: list[ResearchProjectMemoryTrace] = []
    for p in sorted(TRACES_DIR.glob("*.json"), reverse=True):
        if not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        # Must have embedded trace dict
        trace_dict = d.get("trace")
        if not isinstance(trace_dict, dict):
            # Try parsing from content string (legacy)
            content = d.get("content", "")
            if _TRACE_KIND not in content:
                continue
            trace = _parse_trace_from_content(d)
        else:
            trace = _trace_from_dict(trace_dict)
        if trace is None:
            continue
        if project_id and trace.project_id != project_id:
            continue
        traces.append(trace)
    return traces


# ── Bootstrap view ─────────────────────────────────────────────────────────────

def build_research_bootstrap_view(
    *,
    project_id: str,
    active_project: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a "what did we do and what's next" view from all saved traces.

    Used by Sleeping Matylda synthesis to bootstrap a new research session.
    """
    traces = load_research_traces(project_id=project_id)

    # Build trace entries sorted by recorded_at desc
    entries: list[dict] = []
    for trace in traces:
        entries.append({
            "workflow_kind":         trace.workflow_kind,
            "title":                 trace.title,
            "recorded_at":           trace.recorded_at,
            "summary":               trace.summary,
            "key_weakness":          trace.key_weakness,
            "recommended_next_step": trace.recommended_next_step,
            "review_required":       trace.review_required,
            "analyzed_object":       trace.analyzed_object,
            "limitations":           list(trace.limitations),
        })

    # Find latest by workflow type
    def _latest(wk: str) -> dict | None:
        return next((e for e in entries if e["workflow_kind"] == wk), None)

    latest_review    = _latest("paper_red_team")
    latest_claims    = _latest("claim_support_map")
    latest_skill     = _latest("silo_skill")

    # Collect deduplicated recommended_next_steps
    all_next_steps: list[str] = []
    seen: set[str] = set()
    for e in entries[:5]:
        step = e.get("recommended_next_step", "")
        if step and step not in seen:
            all_next_steps.append(step)
            seen.add(step)

    suggested_next_step = (
        all_next_steps[0]
        if all_next_steps
        else "Review latest research traces before starting a new session."
    )

    continuity_status = "bootstrap_ready" if entries else "bootstrap_needs_manual_seed"

    if entries:
        latest = entries[0]
        bootstrap_summary = (
            f"Research bootstrap for {project_id}: {len(entries)} trace(s) available. "
            f"Latest workflow: {latest['workflow_kind']} on '{latest['title']}'. "
            f"Suggested next step: {suggested_next_step}"
        )
    else:
        bootstrap_summary = (
            f"No research continuity traces yet for {project_id}. "
            "Start from current project state and keep first output review-oriented."
        )

    project_payload = {
        "id":     project_id,
        "name":   _opt(_mapping_get(active_project, "name")),
        "status": _opt(_mapping_get(active_project, "status")),
    }

    return {
        "workflow_kind":           "research_bootstrap_view",
        "project_id":              project_id,
        "active_project":          project_payload,
        "continuity_status":       continuity_status,
        "continuity_trace_count":  len(entries),
        "review_required_count":   sum(1 for e in entries if e.get("review_required")),
        "last_review_outcome":     latest_review,
        "last_claims_outcome":     latest_claims,
        "last_skill_outcome":      latest_skill,
        "suggested_next_step":     suggested_next_step,
        "recommended_next_steps":  all_next_steps,
        "bootstrap_summary":       bootstrap_summary,
    }


# ── Workflow payload extractors ────────────────────────────────────────────────

def _trace_payload_for_workflow(workflow_kind: str, payload: dict) -> dict:
    if workflow_kind == "paper_red_team":
        findings   = payload.get("findings") or []
        first_f    = findings[0] if isinstance(findings, list) and findings else {}
        priority   = _str_list(payload.get("priority_actions"))
        limitations = _str_list(payload.get("limitations_of_review"))
        key_weakness = (
            _opt(_mapping_get(first_f, "title"))
            or (limitations[0] if limitations else "No major weakness surfaced.")
        )
        next_step = priority[0] if priority else "Review red-team findings before treating draft as stronger."
        return {
            "analyzed_object": f"paper review of '{payload.get('title', 'unknown')}'",
            "summary":         _req(payload.get("summary"), "summary"),
            "key_weakness":    key_weakness,
            "recommended_next_step": next_step,
            "limitations":     limitations[:2],
        }

    if workflow_kind == "claim_support_map":
        claim_entries = payload.get("claim_entries") or []
        first_c  = claim_entries[0] if isinstance(claim_entries, list) and claim_entries else {}
        gaps     = _str_list(payload.get("support_gaps"))
        priority = _str_list(payload.get("priority_actions"))
        key_weakness = (
            gaps[0]
            if gaps
            else _opt(_mapping_get(first_c, "claim_text"))
            or "No explicit support gap surfaced."
        )
        next_step = (
            priority[0]
            if priority
            else _opt(_mapping_get(first_c, "follow_up"))
            or "Review weakest-supported claims."
        )
        return {
            "analyzed_object": f"claim-support review of '{payload.get('title', 'unknown')}'",
            "summary":         _req(payload.get("support_summary"), "support_summary"),
            "key_weakness":    key_weakness,
            "recommended_next_step": next_step,
            "limitations":     _str_list(payload.get("limitations_of_map"))[:2],
        }

    if workflow_kind == "silo_skill":
        # Generic silo skill result
        result_text = str(payload.get("result") or "")[:300]
        sm_next = _str_list(payload.get("sm_next_steps") or [])
        darkroom_flags = _str_list(payload.get("darkroom_flags") or [])
        return {
            "analyzed_object": f"silo skill '{payload.get('skill_id', 'unknown')}'",
            "summary":         result_text or "Silo skill executed.",
            "key_weakness":    darkroom_flags[0] if darkroom_flags else "No DARKROOM flags raised.",
            "recommended_next_step": sm_next[0] if sm_next else "Review skill output and plan next research step.",
            "limitations":     ["Skill output is working-only and review-required."],
        }

    # Generic fallback
    summary_field = payload.get("summary") or payload.get("result") or payload.get("content") or "No summary provided."
    return {
        "analyzed_object": f"research session '{payload.get('title', workflow_kind)}'",
        "summary":         str(summary_field)[:500],
        "key_weakness":    str(payload.get("key_weakness") or "Not explicitly surfaced."),
        "recommended_next_step": str(
            payload.get("recommended_next_step") or payload.get("next_step") or
            "Review output manually before planning follow-up."
        ),
        "limitations": _str_list(payload.get("limitations") or []),
    }


# ── Parsing helpers ────────────────────────────────────────────────────────────

def _trace_from_dict(d: dict) -> ResearchProjectMemoryTrace | None:
    try:
        return ResearchProjectMemoryTrace(
            project_id=d.get("project_id") or "lite",
            workflow_kind=d.get("workflow_kind") or "generic",
            title=d.get("title") or "Untitled",
            artifact_status=d.get("artifact_status") or "working",
            recorded_at=d.get("recorded_at") or _utc_now(),
            analyzed_object=d.get("analyzed_object") or "",
            summary=d.get("summary") or "",
            key_weakness=d.get("key_weakness") or "",
            recommended_next_step=d.get("recommended_next_step") or "",
            limitations=tuple(d.get("limitations") or []),
            question=_opt(d.get("question")),
            reference_artifact_path=_opt(d.get("reference_artifact_path")),
            scope_summary=_opt(d.get("scope_summary")),
            session_start_hint=_opt(d.get("session_start_hint")),
            memory_scope=d.get("memory_scope") or "project_working",
            review_required=bool(d.get("review_required", True)),
            canonical=bool(d.get("canonical", False)),
            completion_criteria=d.get("completion_criteria") or "",
            validation_id=_opt(d.get("validation_id")),
        )
    except Exception:  # noqa: BLE001
        return None


def _parse_trace_from_content(insight_dict: dict) -> ResearchProjectMemoryTrace | None:
    content = insight_dict.get("content", "")
    parsed: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if line == f"[{_TRACE_KIND}]":
            parsed["trace_kind"] = _TRACE_KIND
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() and value.strip():
            parsed[key.strip()] = value.strip()

    if parsed.get("trace_kind") != _TRACE_KIND:
        return None

    return _trace_from_dict({
        "project_id":             parsed.get("project", "lite"),
        "workflow_kind":          parsed.get("workflow", "generic"),
        "title":                  parsed.get("title", "Untitled"),
        "artifact_status":        parsed.get("artifact_status", "working"),
        "recorded_at":            parsed.get("recorded_at", _utc_now()),
        "analyzed_object":        parsed.get("analyzed_object", ""),
        "summary":                parsed.get("summary", ""),
        "key_weakness":           parsed.get("key_weakness", ""),
        "recommended_next_step":  parsed.get("recommended_next_step", ""),
        "limitations":            [s.strip() for s in parsed.get("limitations", "").split(";") if s.strip()],
        "memory_scope":           parsed.get("memory_scope", "project_working"),
        "review_required":        parsed.get("review_required", "true").lower() == "true",
        "canonical":              parsed.get("canonical", "false").lower() == "true",
    })


# ── Utility ────────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _req(value: object, field_name: str) -> str:
    cleaned = _opt(value)
    if cleaned is None:
        raise ValueError(f"{field_name} is required for research continuity traces.")
    return cleaned


def _opt(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _str_list(candidate: object) -> list[str]:
    if not isinstance(candidate, list):
        return []
    return [str(item).strip() for item in candidate if str(item).strip()]


def _mapping_get(m: Mapping | None, key: str) -> object:
    if not isinstance(m, Mapping):
        return None
    return m.get(key)


# ── Research readiness helpers ─────────────────────────────────────────────────

_STALE_DAYS = 7


def list_stale_traces(days: int = _STALE_DAYS) -> list[dict]:
    """Return traces with artifact_status='working' open for ≥ days days."""
    now = datetime.now(timezone.utc)
    result = []
    for trace in load_research_traces():
        if trace.artifact_status != "working":
            continue
        try:
            recorded = datetime.fromisoformat(
                trace.recorded_at.replace("Z", "+00:00")
            )
            age = (now - recorded).days
        except Exception:  # noqa: BLE001
            continue
        if age >= days:
            result.append({**trace.as_dict(), "days_open": age})
    result.sort(key=lambda x: x["days_open"], reverse=True)
    return result


def promote_trace(trace_id: str, new_status: str, darkroom_approvals_path: Path) -> dict:
    """Promote a trace to new_status.

    Publishing ('published' or 'canonical') requires at least one approved
    DARKROOM disposition entry as a canonical output gate.
    Returns {"ok": True} or raises ValueError with the reason.
    """
    _PUBLISH_STATUSES = {"published", "canonical"}
    if new_status in _PUBLISH_STATUSES:
        try:
            data = json.loads(darkroom_approvals_path.read_text(encoding="utf-8"))
            approved = [a for a in data.get("approvals", []) if a.get("status") == "approved"]
        except Exception:  # noqa: BLE001
            approved = []
        if not approved:
            raise ValueError(
                "Canonical gate: no approved DARKROOM disposition found. "
                "At least one DARKROOM approval is required before publishing."
            )

    # Find and update the trace file
    for p in TRACES_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        trace_dict = d.get("trace", {})
        insight_id = d.get("id", "")
        if insight_id == trace_id or trace_dict.get("id") == trace_id:
            trace_dict["artifact_status"] = new_status
            if new_status in _PUBLISH_STATUSES:
                trace_dict["canonical"] = True
            d["trace"] = trace_dict
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "trace_id": insight_id, "new_status": new_status}

    raise ValueError(f"Trace '{trace_id}' not found")
