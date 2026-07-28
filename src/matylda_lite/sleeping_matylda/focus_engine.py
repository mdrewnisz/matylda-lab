"""focus_engine.py — v1.2 Sleeping Matylda Focus Mode.

Adds directed attention to run_cycle(): instead of scanning everything,
Matylda focuses on user-selected areas for a bounded session.

Session modes:
  timebox    — run cycles until duration_seconds elapsed
  until_idle — run until idle_threshold consecutive cycles produce 0 new findings

Focus areas:
  questions — open_questions from diary + recommended_next_step from traces
  tensions  — active DARKROOM tensions → pro/contra analysis + proposed resolution
  steps     — stale research traces (working >7d) + open active_goals → concrete steps
  no_go     — high-risk / aged trajectories: still valid? new data to reopen?

Finding provenance fields (all focus findings carry):
  focus_session_id · focus_area · source_thread · source_tension · source_question

State file: data/focus_session.json

Design note: Focus Mode is a selection layer on top of run_cycle(), not a
separate execution path. run_cycle(focus_config=...) skips the gap check and
uses _select_engines() to run only the requested engines.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import ROOT
from ..constitutional import BOUNDS

log = logging.getLogger(__name__)

_FOCUS_SESSION_FILE = ROOT / "data" / "focus_session.json"
_FOCUS_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

# Interval between focus cycles (shorter than normal gap to feel responsive)
_FOCUS_CYCLE_INTERVAL_S = 300  # 5 minutes between cycles within a session

_focus_task: asyncio.Task | None = None


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class FocusSessionConfig:
    """Immutable-ish config + mutable runtime state for a focus session."""

    session_id: str
    focus_areas: list[str]           # subset of {"questions","tensions","steps","no_go"}

    # Mode
    mode: str = "timebox"            # "timebox" | "until_idle"
    duration_seconds: int = 1800     # used when mode=="timebox"
    idle_threshold: int = 3          # used when mode=="until_idle"

    # Filters
    only_active_threads: bool = False
    silent_mode: bool = False
    auto_tag_low_risk: bool = False  # tag confidence<0.4 findings — never auto-approve

    custom_prompt: str = ""

    # Runtime state (mutated in-place, persisted to file)
    status: str = "running"          # "running"|"paused"|"completed"|"cancelled"
    start_iso: str = ""
    cycles_completed: int = 0
    findings_generated: int = 0
    consecutive_empty_cycles: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def elapsed_seconds(self) -> float:
        if not self.start_iso:
            return 0.0
        try:
            start = datetime.fromisoformat(self.start_iso)
            return (datetime.now(timezone.utc) - start).total_seconds()
        except Exception:  # noqa: BLE001
            return 0.0

    def remaining_seconds(self) -> float:
        if self.mode != "timebox":
            return -1.0
        return max(0.0, self.duration_seconds - self.elapsed_seconds())

    def is_done(self) -> bool:
        if self.status in ("completed", "cancelled"):
            return True
        if self.mode == "timebox":
            return self.elapsed_seconds() >= self.duration_seconds
        # until_idle
        return self.consecutive_empty_cycles >= self.idle_threshold


# ── Session persistence ───────────────────────────────────────────────────────

def _load_session() -> FocusSessionConfig | None:
    try:
        d = json.loads(_FOCUS_SESSION_FILE.read_text(encoding="utf-8"))
        return FocusSessionConfig(**{
            k: v for k, v in d.items()
            if k in FocusSessionConfig.__dataclass_fields__
        })
    except Exception:  # noqa: BLE001
        return None


def _save_session(cfg: FocusSessionConfig) -> None:
    _FOCUS_SESSION_FILE.write_text(
        json.dumps(cfg.as_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _clear_session() -> None:
    if _FOCUS_SESSION_FILE.exists():
        _FOCUS_SESSION_FILE.unlink()


# ── Provenance helper ─────────────────────────────────────────────────────────

def _add_provenance(
    finding: dict,
    *,
    session_id: str,
    focus_area: str,
    source_thread: str | None = None,
    source_tension: str | None = None,
    source_question: str | None = None,
) -> dict:
    finding["focus_session_id"] = session_id
    finding["focus_area"] = focus_area
    if source_thread:
        finding["source_thread"] = source_thread
    if source_tension:
        finding["source_tension"] = source_tension
    if source_question:
        finding["source_question"] = source_question
    return finding


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fid() -> str:
    return f"finding_{uuid.uuid4().hex[:8]}"


def _start_focus_worker(cfg: FocusSessionConfig) -> None:
    global _focus_task  # noqa: PLW0603
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _focus_task = loop.create_task(_focus_worker_loop(cfg))


# ── Engine: questions ─────────────────────────────────────────────────────────

def _resolve_questions(cfg: FocusSessionConfig) -> list[dict]:
    """Surface unresolved open_questions from diary + recommended_next_step from traces."""
    findings: list[dict] = []

    # 1. open_questions from diary entries
    try:
        from ..diary_manager import list_diary_entries  # noqa: PLC0415
        entries = list_diary_entries(days=BOUNDS.sleeping_matylda_diary_lookback_days)
        seen_questions: set[str] = set()
        for entry in entries:
            stem = entry.get("thread_stem") or "unassigned"
            if cfg.only_active_threads and stem == "unassigned":
                continue
            for q in entry.get("open_questions", []):
                q_key = q.strip().lower()[:80]
                if q_key in seen_questions:
                    continue
                seen_questions.add(q_key)
                f: dict[str, Any] = {
                    "finding_id":  _fid(),
                    "type":        "question_focus",
                    "title":       f"Pytanie bez odpowiedzi: {q[:80]}",
                    "description": (
                        f"Pytanie z wątku '{stem}' pozostaje bez odpowiedzi: {q}\n"
                        + (f"\nKontekst sesji: {cfg.custom_prompt}" if cfg.custom_prompt else "")
                    ),
                    "question":    q,
                    "confidence":  0.70,
                    "created":     _now(),
                    "state":       "pending",
                    "action":      "resolve_question",
                }
                _add_provenance(f, session_id=cfg.session_id, focus_area="questions",
                                source_thread=stem, source_question=q[:120])
                findings.append(f)
                if len(findings) >= 5:
                    break
            if len(findings) >= 5:
                break
    except Exception:  # noqa: BLE001
        log.exception("Focus: question scan (diary) failed")

    # 2. recommended_next_step from working research traces
    try:
        from ..research_continuity import load_research_traces  # noqa: PLC0415
        for trace in load_research_traces():
            if trace.artifact_status != "working":
                continue
            step = trace.recommended_next_step
            if not step or step.startswith("Review output manually"):
                continue
            f = {
                "finding_id":  _fid(),
                "type":        "question_focus",
                "title":       f"Krok z trace: {trace.title[:60]}",
                "description": (
                    f"Rekomendowany krok dla trace '{trace.title}': {step}\n"
                    + (f"\nKontekst sesji: {cfg.custom_prompt}" if cfg.custom_prompt else "")
                ),
                "question":    step,
                "trace_id":    None,
                "confidence":  0.65,
                "created":     _now(),
                "state":       "pending",
                "action":      "resolve_question",
            }
            _add_provenance(f, session_id=cfg.session_id, focus_area="questions",
                            source_thread=trace.project_id, source_question=step[:120])
            findings.append(f)
            if len(findings) >= 8:
                break
    except Exception:  # noqa: BLE001
        log.exception("Focus: question scan (traces) failed")

    return findings


# ── Engine: tensions ──────────────────────────────────────────────────────────

_TENSION_ANALYSIS_SYSTEM = """\
Jesteś analitykiem epistemicznym systemu DARKROOM.
Dostajesz napięcie (sprzeczność lub nierozstrzygnięty konflikt).
Twoim zadaniem jest:
1. Sformułować najsilniejszy argument PO KAŻDEJ STRONIE (1-2 zdania każdy).
2. Zaproponować jedno konkretne działanie, które mogłoby rozwiązać napięcie.

Odpowiedz TYLKO poprawnym JSON:
{
  "pro": "argument za głównym stanowiskiem",
  "contra": "argument przeciw",
  "proposed_resolution": "konkretne działanie w jednym zdaniu",
  "resolvable": true|false
}
"""


def _analyze_tensions(cfg: FocusSessionConfig) -> list[dict]:
    """For each active DARKROOM tension build a pro/contra analysis + proposed resolution."""
    try:
        from ..darkroom.tension import load_active  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    tensions = load_active()
    if not tensions:
        return []

    findings: list[dict] = []

    for tension in tensions[:4]:  # cap at 4 per cycle
        tid = tension.get("tension_id") or tension.get("id") or ""
        description = tension.get("description") or tension.get("text") or ""
        title_t = tension.get("title") or description[:60]

        analysis: dict = {
            "pro": "",
            "contra": "",
            "proposed_resolution": "Wymaga ręcznej analizy.",
            "resolvable": False,
        }

        try:
            from ..models import call_with_model_fallback  # noqa: PLC0415
            import anthropic  # noqa: PLC0415
            client = anthropic.Anthropic()
            context = (f"Kontekst sesji: {cfg.custom_prompt}\n\n" if cfg.custom_prompt else "")
            msg = call_with_model_fallback(
                client, "haiku",
                max_tokens=400,
                system=_TENSION_ANALYSIS_SYSTEM,
                messages=[{"role": "user", "content": f"{context}NAPIĘCIE:\n{description}"}],
            )
            raw = msg.content[0].text.strip()
            analysis = json.loads(raw)
        except Exception:  # noqa: BLE001
            pass

        f: dict[str, Any] = {
            "finding_id":          _fid(),
            "type":                "tension_analysis",
            "title":               f"Analiza napięcia: {title_t[:70]}",
            "description": (
                f"Napięcie: {description}\n\n"
                f"Pro: {analysis.get('pro','—')}\n"
                f"Contra: {analysis.get('contra','—')}\n\n"
                f"Proponowane rozwiązanie: {analysis.get('proposed_resolution','—')}"
            ),
            "tension_id":          tid,
            "pro":                 analysis.get("pro", ""),
            "contra":              analysis.get("contra", ""),
            "proposed_resolution": analysis.get("proposed_resolution", ""),
            "resolvable":          bool(analysis.get("resolvable", False)),
            "confidence":          0.75 if analysis.get("resolvable") else 0.50,
            "created":             _now(),
            "state":               "pending",
            "action":              "propose_resolution",
        }
        _add_provenance(f, session_id=cfg.session_id, focus_area="tensions",
                        source_tension=tid)
        findings.append(f)

    return findings


# ── Engine: steps ─────────────────────────────────────────────────────────────

def _propose_steps(cfg: FocusSessionConfig) -> list[dict]:
    """Propose concrete next steps from stale traces and open active_goals."""
    findings: list[dict] = []

    # 1. Stale research traces
    try:
        from ..research_continuity import list_stale_traces  # noqa: PLC0415
        for trace_d in list_stale_traces(days=7)[:4]:
            title_t = trace_d.get("title", "—")
            step    = trace_d.get("recommended_next_step", "")
            days_o  = trace_d.get("days_open", 0)
            f: dict[str, Any] = {
                "finding_id":  _fid(),
                "type":        "step_proposal",
                "title":       f"Zaległy krok ({days_o}d): {title_t[:55]}",
                "description": (
                    f"Trace '{title_t}' w stanie 'working' od {days_o} dni.\n"
                    f"Sugerowany krok: {step}\n"
                    + (f"\nKontekst: {cfg.custom_prompt}" if cfg.custom_prompt else "")
                ),
                "trace_id":    trace_d.get("id"),
                "days_open":   days_o,
                "step":        step,
                "confidence":  min(0.90, 0.60 + days_o * 0.02),
                "created":     _now(),
                "state":       "pending",
                "action":      "log_step",
            }
            _add_provenance(f, session_id=cfg.session_id, focus_area="steps",
                            source_thread=trace_d.get("project_id"))
            findings.append(f)
    except Exception:  # noqa: BLE001
        log.exception("Focus: step scan (traces) failed")

    # 2. Open active_goals
    try:
        from ..homeostasis import list_goals  # noqa: PLC0415
        for goal in list_goals():
            if goal.get("status") not in ("active", "open"):
                continue
            gid   = goal.get("goal_id", "")
            title_g = goal.get("title", "—")
            desc  = goal.get("description", "")
            f = {
                "finding_id":  _fid(),
                "type":        "step_proposal",
                "title":       f"Otwarty cel: {title_g[:65]}",
                "description": (
                    f"Cel '{title_g}' jest otwarty.\n"
                    f"Opis: {desc}\n"
                    f"Sugestia: zdefiniuj mierzalny krok zamknięcia lub zamknij cel.\n"
                    + (f"\nKontekst: {cfg.custom_prompt}" if cfg.custom_prompt else "")
                ),
                "goal_id":     gid,
                "step":        f"Zamknij lub zaadresuj cel: {title_g}",
                "confidence":  0.65,
                "created":     _now(),
                "state":       "pending",
                "action":      "close_goal",
            }
            _add_provenance(f, session_id=cfg.session_id, focus_area="steps")
            findings.append(f)
            if len(findings) >= 8:
                break
    except Exception:  # noqa: BLE001
        log.exception("Focus: step scan (goals) failed")

    return findings


# ── Engine: no_go validity ────────────────────────────────────────────────────

_NOGO_RECHECK_SYSTEM = """\
Jesteś recenzentem rejestru NO-GO systemu badawczego.
Dostajesz opis trajektorii odrzuconej w przeszłości oraz najnowsze wpisy dziennika
z tego wątku.

Oceń:
1. Czy powód odrzucenia (kategoria ryzyka) jest nadal aktualny?
2. Czy nowe wpisy zawierają dowody, które mogłyby uzasadnić ponowne otwarcie wątku?

Odpowiedz TYLKO poprawnym JSON:
{
  "still_valid": true|false,
  "new_evidence_found": true|false,
  "reasoning": "jedno zdanie",
  "recommendation": "keep"|"reopen"|"recheck"
}
"""


def _check_nogo_validity(cfg: FocusSessionConfig) -> list[dict]:
    """Ask: is each high-risk trajectory still valid? Any new data to reopen closed ones?"""
    try:
        from ..nogo_room import _load as _load_nogo  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    data = _load_nogo()
    trajectories = list(data.get("trajectories", {}).values())
    if not trajectories:
        return []

    try:
        from ..diary_manager import list_diary_entries  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        list_diary_entries = None  # type: ignore[assignment]

    findings: list[dict] = []

    # Sort: check high-risk first, then aged ones
    def _sort_key(t: dict) -> float:
        risk = t.get("risk_score", 0.0)
        last = t.get("last_seen", "")
        # High risk and old = highest priority
        try:
            age_days = (
                datetime.now(timezone.utc) -
                datetime.fromisoformat(last.replace("Z", "+00:00"))
            ).days
        except Exception:  # noqa: BLE001
            age_days = 0
        return risk + age_days * 0.01

    sorted_trajs = sorted(trajectories, key=_sort_key, reverse=True)

    for traj in sorted_trajs[:3]:  # cap at 3 per cycle
        stem = traj.get("thread_stem", "")
        tag  = traj.get("tag", "")
        tid  = traj.get("trajectory_id") or f"{stem}::{tag}"
        risk = traj.get("risk_score", 0.0)
        cat  = traj.get("category", "unknown")

        # Gather recent diary entries for this thread stem
        recent_entries_text = ""
        if list_diary_entries and stem:
            try:
                entries = list_diary_entries(days=14)
                stem_entries = [e for e in entries if e.get("thread_stem") == stem][-3:]
                if stem_entries:
                    recent_entries_text = "\n".join(
                        f"- [{e.get('timestamp','?')[:10]}] {e.get('key_finding','')}"
                        for e in stem_entries
                    )
            except Exception:  # noqa: BLE001
                pass

        verdict: dict = {
            "still_valid": True,
            "new_evidence_found": False,
            "reasoning": "Brak nowych danych do oceny.",
            "recommendation": "keep",
        }

        if recent_entries_text:
            try:
                from ..models import call_with_model_fallback  # noqa: PLC0415
                import anthropic  # noqa: PLC0415
                client = anthropic.Anthropic()
                context = (f"Kontekst sesji: {cfg.custom_prompt}\n\n" if cfg.custom_prompt else "")
                msg = call_with_model_fallback(
                    client, "haiku",
                    max_tokens=300,
                    system=_NOGO_RECHECK_SYSTEM,
                    messages=[{"role": "user", "content": (
                        f"{context}TRAJEKTORIA: {tid}\n"
                        f"Kategoria ryzyka: {cat}\n"
                        f"Risk score: {risk:.2f}\n\n"
                        f"NAJNOWSZE WPISY DZIENNIKA:\n{recent_entries_text}"
                    )}],
                )
                raw = msg.content[0].text.strip()
                verdict = json.loads(raw)
            except Exception:  # noqa: BLE001
                pass

        rec = verdict.get("recommendation", "keep")
        action = "reopen_trajectory" if rec == "reopen" else "acknowledge_nogo_recheck"

        f: dict[str, Any] = {
            "finding_id":        _fid(),
            "type":              "nogo_recheck",
            "title":             f"NO-GO recheck: {tid}",
            "description": (
                f"Trajektoria '{tid}' (kategoria: {cat}, risk: {risk:.2f}).\n"
                f"Ocena: {verdict.get('reasoning','—')}\n"
                f"Rekomendacja: {rec.upper()}"
            ),
            "trajectory_id":     tid,
            "thread_stem":       stem,
            "tag":               tag,
            "risk_score":        risk,
            "category":          cat,
            "still_valid":       verdict.get("still_valid", True),
            "new_evidence_found": verdict.get("new_evidence_found", False),
            "recommendation":    rec,
            "confidence":        0.80 if recent_entries_text else 0.45,
            "created":           _now(),
            "state":             "pending",
            "action":            action,
        }
        _add_provenance(f, session_id=cfg.session_id, focus_area="no_go",
                        source_thread=stem)
        findings.append(f)

    return findings


# ── Engine selector ───────────────────────────────────────────────────────────

_AREA_ENGINES = {
    "questions": _resolve_questions,
    "tensions":  _analyze_tensions,
    "steps":     _propose_steps,
    "no_go":     _check_nogo_validity,
}

VALID_FOCUS_AREAS = frozenset(_AREA_ENGINES)


def run_focused_cycle(cfg: FocusSessionConfig) -> dict:
    """Run one focus cycle: select engines by focus_areas, collect findings with provenance.

    Called by run_cycle(focus_config=cfg) — does NOT call run_cycle() itself to
    avoid double gap-check.  Returns cycle summary dict.
    """
    from .consolidation import _load_state, _save_state, _fire  # noqa: PLC0415

    all_findings: list[dict] = []

    for area in cfg.focus_areas:
        engine = _AREA_ENGINES.get(area)
        if engine is None:
            log.warning("Focus: unknown area %r — skipped", area)
            continue
        try:
            results = engine(cfg)
            all_findings.extend(results)
            log.debug("Focus engine %r: %d findings", area, len(results))
        except Exception:  # noqa: BLE001
            log.exception("Focus engine %r failed", area)

    # Tag low-risk findings (never auto-approve — just mark)
    if cfg.auto_tag_low_risk:
        for f in all_findings:
            if f.get("confidence", 1.0) < 0.4:
                f.setdefault("tags", [])
                if "low_risk" not in f["tags"]:
                    f["tags"].append("low_risk")

    # Merge into SM state
    state = _load_state()
    existing_pending = [
        f for f in state.get("findings", [])
        if f.get("state") == "pending"
    ]
    state["findings"] = existing_pending + all_findings
    state["last_cycle_end"]      = _now()
    state["last_cycle_findings"] = len(all_findings)
    _save_state(state)

    _fire("sleeping_matylda.focus_cycle_complete",
          session_id=cfg.session_id, findings=len(all_findings))

    return {
        "status":           "completed",
        "findings_new":     len(all_findings),
        "focus_session_id": cfg.session_id,
        "focus_areas":      cfg.focus_areas,
        "findings":         all_findings,
    }


# ── Session management ────────────────────────────────────────────────────────

def start_focus_session(
    focus_areas: list[str],
    *,
    mode: str = "timebox",
    duration_seconds: int = 1800,
    idle_threshold: int = 3,
    only_active_threads: bool = False,
    silent_mode: bool = False,
    auto_tag_low_risk: bool = False,
    custom_prompt: str = "",
) -> FocusSessionConfig:
    """Create and persist a new focus session, start the asyncio worker."""
    global _focus_task  # noqa: PLW0603

    # Validate focus_areas
    areas = [a for a in focus_areas if a in VALID_FOCUS_AREAS]
    if not areas:
        raise ValueError(f"No valid focus areas. Choose from: {sorted(VALID_FOCUS_AREAS)}")

    # Cancel any running session
    if _focus_task and not _focus_task.done():
        _focus_task.cancel()

    cfg = FocusSessionConfig(
        session_id=f"focus_{uuid.uuid4().hex[:8]}",
        focus_areas=areas,
        mode=mode,
        duration_seconds=duration_seconds,
        idle_threshold=idle_threshold,
        only_active_threads=only_active_threads,
        silent_mode=silent_mode,
        auto_tag_low_risk=auto_tag_low_risk,
        custom_prompt=custom_prompt,
        status="running",
        start_iso=_now(),
    )
    _save_session(cfg)
    log.info("Focus session started: %s mode=%s areas=%s", cfg.session_id, mode, areas)

    _start_focus_worker(cfg)

    return cfg


async def _focus_worker_loop(cfg: FocusSessionConfig) -> None:
    """Asyncio task: runs focused cycles until session is done."""
    log.info("Focus worker started: %s", cfg.session_id)

    while True:
        # Re-read from file so pause/stop are picked up
        current = _load_session()
        if current is None or current.session_id != cfg.session_id:
            log.info("Focus session superseded — worker exits")
            return
        if current.status == "paused":
            await asyncio.sleep(10)
            continue
        if current.is_done():
            current.status = "completed"
            _save_session(current)
            log.info("Focus session completed: %s", cfg.session_id)
            return

        # Run one cycle
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: run_focused_cycle(current))
            new_findings = result.get("findings_new", 0)
        except Exception:  # noqa: BLE001
            log.exception("Focus cycle error")
            new_findings = 0

        # Update session state
        current = _load_session()
        if current is None or current.session_id != cfg.session_id:
            return
        current.cycles_completed += 1
        current.findings_generated += new_findings
        if new_findings == 0:
            current.consecutive_empty_cycles += 1
        else:
            current.consecutive_empty_cycles = 0
        _save_session(current)

        if current.is_done():
            current.status = "completed"
            _save_session(current)
            log.info("Focus session completed: %s (idle=%d)",
                     cfg.session_id, current.consecutive_empty_cycles)
            return

        await asyncio.sleep(_FOCUS_CYCLE_INTERVAL_S)


def get_focus_status() -> dict:
    """Return current focus session status dict, or {"active": False} if none."""
    cfg = _load_session()
    if cfg is None:
        return {"active": False}
    d = cfg.as_dict()
    d["active"] = cfg.status in ("running", "paused")
    d["elapsed_seconds"] = round(cfg.elapsed_seconds())
    d["remaining_seconds"] = round(cfg.remaining_seconds()) if cfg.mode == "timebox" else -1
    return d


def pause_focus_session() -> dict:
    """Pause the running session (timer keeps ticking, no new cycles start)."""
    cfg = _load_session()
    if cfg is None:
        raise ValueError("No active focus session")
    if cfg.status != "running":
        raise ValueError(f"Session is {cfg.status!r}, not running")
    cfg.status = "paused"
    _save_session(cfg)
    return get_focus_status()


def resume_focus_session() -> dict:
    """Resume a paused session."""
    cfg = _load_session()
    if cfg is None:
        raise ValueError("No active focus session")
    if cfg.status != "paused":
        raise ValueError(f"Session is {cfg.status!r}, not paused")
    cfg.status = "running"
    _save_session(cfg)
    # Restart worker if needed
    global _focus_task  # noqa: PLW0603
    if not _focus_task or _focus_task.done():
        _start_focus_worker(cfg)
    return get_focus_status()


def stop_focus_session() -> dict:
    """Cancel the session immediately."""
    global _focus_task  # noqa: PLW0603
    if _focus_task and not _focus_task.done():
        _focus_task.cancel()
    cfg = _load_session()
    if cfg is None:
        return {"active": False, "status": "no_session"}
    cfg.status = "cancelled"
    _save_session(cfg)
    log.info("Focus session cancelled: %s (%d cycles, %d findings)",
             cfg.session_id, cfg.cycles_completed, cfg.findings_generated)
    return cfg.as_dict()
