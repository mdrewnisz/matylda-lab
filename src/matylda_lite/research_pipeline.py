"""ResearchPipeline — spinanie Silo → DARKROOM → ResearchTrace → SM synthesis.

Zamiast 5 osobnych kroków ręcznych, jedno wywołanie:
  run_research_pipeline(skill_id, inputs, project_id) → PipelineResult

Przepływ:
  1. Uruchom skill w silosie (LLM + DARKROOM wewnętrznie)
  2. Zaloguj ChronicleEvent dla silosu
  3. Zbuduj ResearchProjectMemoryTrace z wyniku
  4. Zapisz trace do memory/insights/
  5. Uruchom SM synthesis na snapshoe wzbogaconym o wynik skilla
     (silo_2/closed: SM synthesis pomijana — brak Sleeping Matylda w closed silo)
  6. Zaloguj ChronicleEvent dla SM synthesis
  7. Zwróć PipelineResult ze wszystkimi etapami

v0.4b — wspiera silo_1 (Science/open) i silo_2 (Privacy Lab/closed).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


# ── PipelineResult ─────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Unified result of a full research pipeline run."""
    pipeline_id: str
    silo_id: str
    skill_id: str
    skill_name: str
    project_id: str
    started_at: str
    completed_at: str
    duration_ms: int

    # Stage 1 — Silo skill
    skill_result: dict = field(default_factory=dict)
    darkroom_flags: list[str] = field(default_factory=list)
    llm_used: str = ""

    # Stage 2 — Research trace
    trace_id: str = ""
    trace_summary: str = ""
    trace_key_weakness: str = ""
    trace_recommended_next_step: str = ""

    # Stage 3 — SM synthesis
    sm_day_synthesis: str = ""
    sm_proposed_next_steps: list[str] = field(default_factory=list)
    sm_next_questions: list[str] = field(default_factory=list)
    sm_warnings: list[str] = field(default_factory=list)

    # Chronicle event IDs for traceability
    chronicle_event_ids: list[str] = field(default_factory=list)

    # Status
    ok: bool = True
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id":   self.pipeline_id,
            "silo_id":       self.silo_id,
            "skill_id":      self.skill_id,
            "skill_name":    self.skill_name,
            "project_id":    self.project_id,
            "started_at":    self.started_at,
            "completed_at":  self.completed_at,
            "duration_ms":   self.duration_ms,
            "ok":            self.ok,
            "error":         self.error,
            # Skill
            "skill_result":    self.skill_result,
            "darkroom_flags":  self.darkroom_flags,
            "llm_used":        self.llm_used,
            # Trace
            "trace_id":                    self.trace_id,
            "trace_summary":               self.trace_summary,
            "trace_key_weakness":          self.trace_key_weakness,
            "trace_recommended_next_step": self.trace_recommended_next_step,
            # SM
            "sm_day_synthesis":        self.sm_day_synthesis,
            "sm_proposed_next_steps":  self.sm_proposed_next_steps,
            "sm_next_questions":       self.sm_next_questions,
            "sm_warnings":             self.sm_warnings,
            # Chronicle
            "chronicle_event_ids": self.chronicle_event_ids,
        }

    def summary_text(self) -> str:
        """Human-readable one-page summary of the pipeline run."""
        lines = [
            f"=== ResearchPipeline [{self.pipeline_id}] ===",
            f"Skill:    {self.skill_name} ({self.skill_id})",
            f"Projekt:  {self.project_id}",
            f"Czas:     {self.duration_ms}ms",
            f"Status:   {'✓ OK' if self.ok else '✗ ' + self.error}",
            "",
            "── Wynik skilla ──",
        ]
        if self.darkroom_flags:
            lines.append(f"DARKROOM: {len(self.darkroom_flags)} flag(i) — " + "; ".join(self.darkroom_flags[:3]))
        else:
            lines.append("DARKROOM: brak flag")

        if self.trace_id:
            lines += [
                "",
                "── Research Trace ──",
                f"Podsumowanie:  {self.trace_summary[:120]}",
                f"Słabość:       {self.trace_key_weakness[:100]}",
                f"Kolejny krok:  {self.trace_recommended_next_step[:100]}",
            ]

        if self.sm_day_synthesis:
            lines += [
                "",
                "── Sleeping Matylda ──",
                self.sm_day_synthesis,
            ]
            if self.sm_proposed_next_steps:
                lines.append("Propozycje:")
                for step in self.sm_proposed_next_steps[:3]:
                    lines.append(f"  • {step}")

        return "\n".join(lines)


# ── Silo dispatch ──────────────────────────────────────────────────────────────

_SUPPORTED_SILOS = {"silo_1", "silo_2"}

# Silos that run SM synthesis as part of the pipeline (open silos only).
# Closed silos skip Stage 5 — no Sleeping Matylda to avoid leaking patterns.
_SM_ENABLED_SILOS = {"silo_1"}


def _run_silo_skill(silo_id: str, skill_id: str, inputs: dict) -> dict:
    """Dispatch skill execution to the correct silo module."""
    if silo_id == "silo_1":
        from .silos.silo_1 import _run_skill  # noqa: PLC0415
        return _run_skill(skill_id, inputs)
    if silo_id == "silo_2":
        from .silos.silo_2 import _run_skill  # noqa: PLC0415
        return _run_skill(skill_id, inputs)
    raise ValueError(f"Silo '{silo_id}' nie jest obsługiwany przez pipeline (v0.4b: silo_1, silo_2).")


def _get_skill_name(silo_id: str, skill_id: str) -> str:
    try:
        if silo_id == "silo_1":
            from .silos.silo_1 import _load_skill  # noqa: PLC0415
            skill = _load_skill(skill_id)
            return (skill or {}).get("name", skill_id)
        if silo_id == "silo_2":
            from .silos.silo_2 import _load_skill  # noqa: PLC0415
            skill = _load_skill(skill_id)
            return (skill or {}).get("name", skill_id)
    except Exception:  # noqa: BLE001
        pass
    return skill_id


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_research_pipeline(
    skill_id: str,
    inputs: dict,
    *,
    silo_id: str = "silo_1",
    project_id: str = "lite",
    title: str = "",
) -> PipelineResult:
    """Run a full research pipeline and return a PipelineResult.

    Stages:
      1. Silo skill execution (LLM + DARKROOM)
      2. ChronicleEvent for silo
      3. ResearchProjectMemoryTrace auto-save
      4. ChronicleEvent for trace
      5. SM synthesis on enriched snapshot
      6. ChronicleEvent for SM synthesis

    Args:
        skill_id:   Skill to run (must exist in silo).
        inputs:     Input dict for the skill.
        silo_id:    Which silo to use (default "silo_1").
        project_id: Project context.
        title:      Human-readable title for the trace.
                    Defaults to "<skill_name> — <date>".

    Returns:
        PipelineResult with all stages populated.
    """
    pipeline_id = "pipeline_" + uuid.uuid4().hex[:8]
    started_at  = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()

    skill_name = _get_skill_name(silo_id, skill_id)
    effective_title = title or f"{skill_name} — {started_at[:10]}"
    chronicle_ids: list[str] = []

    # ── Stage 1: Run silo skill ───────────────────────────────────────────────
    try:
        skill_result = _run_silo_skill(silo_id, skill_id, inputs)
    except Exception as exc:  # noqa: BLE001
        completed_at = datetime.now(timezone.utc).isoformat()
        return PipelineResult(
            pipeline_id=pipeline_id, silo_id=silo_id, skill_id=skill_id,
            skill_name=skill_name, project_id=project_id,
            started_at=started_at, completed_at=completed_at,
            duration_ms=int((time.monotonic() - t0) * 1000),
            ok=False, error=f"Skill failed: {exc}",
        )

    if skill_result.get("error"):
        completed_at = datetime.now(timezone.utc).isoformat()
        return PipelineResult(
            pipeline_id=pipeline_id, silo_id=silo_id, skill_id=skill_id,
            skill_name=skill_name, project_id=project_id,
            started_at=started_at, completed_at=completed_at,
            duration_ms=int((time.monotonic() - t0) * 1000),
            skill_result=skill_result,
            ok=False, error=skill_result["error"],
        )

    darkroom_flags = skill_result.get("darkroom_flags", [])
    llm_used = skill_result.get("llm_used", "")

    # ── Stage 2: ChronicleEvent for silo skill ────────────────────────────────
    try:
        from .chronicle import log_silo_event  # noqa: PLC0415
        ev = log_silo_event(
            silo_id=silo_id, skill_id=skill_id,
            project_id=project_id, model_used=llm_used,
        )
        chronicle_ids.append(ev.event_id)
    except Exception:  # noqa: BLE001
        pass

    # ── Stage 3: ResearchProjectMemoryTrace ───────────────────────────────────
    trace_id = ""
    trace_summary = ""
    trace_key_weakness = ""
    trace_next_step = ""
    try:
        from .research_continuity import (  # noqa: PLC0415
            build_research_project_memory_trace, save_research_trace,
        )
        # Build trace payload compatible with continuity module
        trace_payload = {
            "workflow_kind":   "silo_skill",
            "title":           effective_title,
            "project_id":      project_id,
            "artifact_status": "working",
            "skill_id":        skill_id,
            "result":          json.dumps(skill_result.get("result", {}), ensure_ascii=False)[:500],
            "sm_next_steps":   skill_result.get("sm_next_steps", []),
            "darkroom_flags":  darkroom_flags,
        }
        trace = build_research_project_memory_trace(trace_payload)
        saved = save_research_trace(trace)
        trace_id       = saved["id"]
        trace_summary  = trace.summary
        trace_key_weakness = trace.key_weakness
        trace_next_step    = trace.recommended_next_step
    except Exception:  # noqa: BLE001
        pass

    # ── Stage 4: ChronicleEvent for trace ─────────────────────────────────────
    if trace_id:
        try:
            from .chronicle import log_memory_event  # noqa: PLC0415
            ev2 = log_memory_event("trace_saved", trace_id, "project_fact", project_id)
            chronicle_ids.append(ev2.event_id)
        except Exception:  # noqa: BLE001
            pass

    # ── Stage 5: SM synthesis on enriched snapshot ────────────────────────────
    # Skipped for closed silos (silo_2+) — Sleeping Matylda disabled.
    sm_day_synthesis   = ""
    sm_next_steps: list[str] = []
    sm_next_questions: list[str] = []
    sm_warnings: list[str] = []
    if silo_id not in _SM_ENABLED_SILOS:
        sm_warnings = [f"Sleeping Matylda wyłączona w silosie '{silo_id}' (closed)."]
    try:
        if silo_id not in _SM_ENABLED_SILOS:
            raise StopIteration  # jump to except, skip SM
        from .sleeping_matylda.sync import build_sync_snapshot  # noqa: PLC0415
        from .sleeping_matylda.synthesis import run_synthesis  # noqa: PLC0415
        snapshot = build_sync_snapshot()
        # Enrich snapshot with this pipeline's context
        snapshot["active_project"] = project_id
        snapshot["pipeline_context"] = {
            "skill_id":      skill_id,
            "skill_name":    skill_name,
            "title":         effective_title,
            "darkroom_flags": darkroom_flags,
            "trace_id":      trace_id,
            "trace_summary": trace_summary,
            "trace_next_step": trace_next_step,
        }
        # Inject skill result as a fresh insight for synthesis context
        snapshot.setdefault("insights", []).insert(0, {
            "content": trace_summary or str(skill_result.get("result", ""))[:300],
            "topic": f"[pipeline] {skill_name}",
        })
        sm_out = run_synthesis(snapshot)
        sm_day_synthesis   = sm_out.get("day_synthesis", "")
        sm_next_steps      = sm_out.get("proposed_next_steps", [])
        sm_next_questions  = sm_out.get("next_questions", [])
        sm_warnings        = sm_out.get("warnings", [])
    except StopIteration:
        pass  # closed silo — SM intentionally skipped
    except Exception:  # noqa: BLE001
        pass

    # ── Stage 6: ChronicleEvent for SM synthesis ──────────────────────────────
    try:
        from .chronicle import log_sm_synthesis_event  # noqa: PLC0415
        ev3 = log_sm_synthesis_event(
            project_id=project_id,
            open_threads_count=len(sm_next_steps),
            warnings=sm_warnings[:3],
        )
        chronicle_ids.append(ev3.event_id)
    except Exception:  # noqa: BLE001
        pass

    completed_at = datetime.now(timezone.utc).isoformat()
    duration_ms  = int((time.monotonic() - t0) * 1000)

    return PipelineResult(
        pipeline_id=pipeline_id,
        silo_id=silo_id,
        skill_id=skill_id,
        skill_name=skill_name,
        project_id=project_id,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        skill_result=skill_result,
        darkroom_flags=darkroom_flags,
        llm_used=llm_used,
        trace_id=trace_id,
        trace_summary=trace_summary,
        trace_key_weakness=trace_key_weakness,
        trace_recommended_next_step=trace_next_step,
        sm_day_synthesis=sm_day_synthesis,
        sm_proposed_next_steps=sm_next_steps,
        sm_next_questions=sm_next_questions,
        sm_warnings=sm_warnings,
        chronicle_event_ids=chronicle_ids,
        ok=True,
    )


def list_pipeline_results(limit: int = 20, project_id: str = "") -> list[dict]:
    """Return recent pipeline runs from the chronicle log.

    Filters to sm_synthesis events which bookend pipeline runs,
    then cross-references with research traces.
    """
    from .chronicle import list_recent_events  # noqa: PLC0415
    from .research_continuity import load_research_traces  # noqa: PLC0415

    events = list_recent_events(
        limit=limit * 3,
        event_type="sm_synthesis",
        project_id=project_id,
    )
    traces = load_research_traces(project_id=project_id)

    # Match trace to events by proximity in time (simple: last N traces)
    results = []
    for trace in traces[:limit]:
        entry = {
            "trace_id":           None,
            "workflow_kind":      trace.workflow_kind,
            "title":              trace.title,
            "recorded_at":        trace.recorded_at,
            "summary":            trace.summary,
            "key_weakness":       trace.key_weakness,
            "recommended_next_step": trace.recommended_next_step,
            "project_id":         trace.project_id,
        }
        results.append(entry)

    return results
