"""counterfactual_room.py — v1.0 decision outcome tracking.

Counterfactual Room records approve/dismiss decisions for trajectory-linked
findings, then re-examines those decisions after counterfactual_evaluation_days
to check whether they were accurate.

Design principles:
  - Only corrects Positive Room (never NoGo) — avoids "mud is important because
    it keeps coming back" feedback loops
  - Requires counterfactual_min_signal >= 2 new entries before declaring a
    dismissed finding was wrong (confounding guard: one stray entry ≠ real signal)
  - Also requires novel_entity_delta >= 1 to distinguish real discovery from
    rumination (user refinement from design discussion)
  - Bounded corrections: magnitude capped at counterfactual_correction_magnitude
  - No circular dependency: does not import from consolidation.py

Correction logic:
  DISMISS was wrong:
    thread has >= counterfactual_min_signal new entries AND novel_entity_delta >= 1
    → record_success on Positive Room (thread was worth exploring)

  APPROVE was wrong:
    thread produced 0 new entries AND 0 new entities
    → record_failure on Positive Room (signal was a false positive)

State file: data/counterfactual_room.json
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import ROOT
from .constitutional import BOUNDS

log = logging.getLogger(__name__)

_CF_FILE = ROOT / "data" / "counterfactual_room.json"
_CF_FILE.parent.mkdir(parents=True, exist_ok=True)

_TRACKED_FINDING_TYPES = frozenset({"reflection_candidate", "synthesis_opportunity"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_cf() -> dict:
    if not _CF_FILE.exists():
        return {"records": []}
    try:
        return json.loads(_CF_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"records": []}


def _save_cf(data: dict) -> None:
    _CF_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _count_entities() -> int:
    """Lightweight entity count for delta computation."""
    try:
        from .knowledge_graph import load_graph  # noqa: PLC0415
        return len(load_graph())
    except Exception:  # noqa: BLE001
        return 0


def _current_entry_count(thread_stem: str) -> int:
    """Get current diary entry count for a thread stem (broad window).

    Uses 4× the standard lookback to capture entries generated since the
    original decision was made.
    """
    try:
        from .diary_manager import list_diary_entries  # noqa: PLC0415
        days = BOUNDS.sleeping_matylda_diary_lookback_days * 4
        entries = list_diary_entries(days=days)
        return sum(1 for e in entries if e.get("thread_stem") == thread_stem)
    except Exception:  # noqa: BLE001
        return 0


# ── Core API ──────────────────────────────────────────────────────────────────

def record_counterfactual(finding: dict, decision: str) -> dict:
    """Record an approve/dismiss decision for a trajectory-linked finding.

    Only records for finding types: reflection_candidate, synthesis_opportunity.
    Returns {} (silently) for other finding types.

    Args:
        finding: The finding dict from Sleeping Matylda.
        decision: "approve" | "dismiss".

    Returns:
        The created counterfactual record dict, or {} if the finding type is
        not tracked by the Counterfactual Room.
    """
    finding_type = finding.get("type", "")
    if finding_type not in _TRACKED_FINDING_TYPES:
        return {}

    # Extract trajectory coordinates — mirrors _positive_feedback logic
    thread_stem  = finding.get("thread_stem") or ""
    tags         = finding.get("tags") or []
    tag          = finding.get("tag") or (tags[0] if tags else "")
    dominant_tag = tag or "untagged"

    if not thread_stem:
        threads     = finding.get("threads", [])
        thread_stem = threads[0] if threads else "unassigned"

    entity_count_at_decision = _count_entities()

    record: dict = {
        "counterfactual_id":        f"cf_{uuid.uuid4().hex[:8]}",
        "finding_id":               finding.get("finding_id", ""),
        "finding_type":             finding_type,
        "decision":                 decision,
        "decided_at":               _now(),
        "thread_stem":              thread_stem,
        "tag":                      dominant_tag,
        "entry_count_at_decision":  finding.get("entry_count", 0),
        "entity_count_at_decision": entity_count_at_decision,
        "evaluated_at":             None,
        "entry_count_at_evaluation": None,
        "thread_entry_delta":       None,
        "novel_entity_delta":       None,
        "resurfaced_in_cycles":     0,
        "correction_applied":       False,
        "weight_delta":             0.0,
    }

    data = _load_cf()
    data["records"].append(record)
    _save_cf(data)
    return record


def evaluate_counterfactuals(days: int | None = None) -> list[dict]:
    """Evaluate matured counterfactual records and apply bounded corrections.

    A record is mature when:
      (now - decided_at) >= counterfactual_evaluation_days

    Corrections are applied only to Positive Room.
    NoGo Room is never touched (design constraint).

    Returns list of records evaluated in this call (may be empty).
    """
    eval_days = days if days is not None else BOUNDS.counterfactual_evaluation_days
    cutoff    = (datetime.now(timezone.utc) - timedelta(days=eval_days)).isoformat()

    data      = _load_cf()
    evaluated: list[dict] = []
    changed   = False

    for rec in data["records"]:
        if rec.get("evaluated_at") is not None:
            continue  # already evaluated — skip
        if rec.get("decided_at", "") > cutoff:
            continue  # not mature yet

        thread_stem = rec["thread_stem"]
        tag         = rec["tag"]

        # Compute deltas
        entry_count_now    = _current_entry_count(thread_stem)
        entry_count_then   = rec.get("entry_count_at_decision", 0)
        thread_entry_delta = entry_count_now - entry_count_then

        entity_count_now   = _count_entities()
        entity_count_then  = rec.get("entity_count_at_decision", 0)
        novel_entity_delta = max(0, entity_count_now - entity_count_then)

        rec["entry_count_at_evaluation"] = entry_count_now
        rec["thread_entry_delta"]        = thread_entry_delta
        rec["novel_entity_delta"]        = novel_entity_delta
        rec["evaluated_at"]              = _now()

        min_signal = BOUNDS.counterfactual_min_signal
        magnitude  = BOUNDS.counterfactual_correction_magnitude
        decision   = rec["decision"]

        weight_delta       = 0.0
        correction_applied = False

        if decision == "dismiss":
            # Dismiss wrong: thread resurfaced with new content AND novel entities
            if thread_entry_delta >= min_signal and novel_entity_delta >= 1:
                try:
                    from .positive_room import record_success  # noqa: PLC0415
                    record_success(thread_stem, tag)
                    weight_delta       = magnitude
                    correction_applied = True
                    log.info(
                        "Counterfactual correction (dismiss→wrong): %s::%s +%.2f",
                        thread_stem, tag, magnitude,
                    )
                except Exception:  # noqa: BLE001
                    pass

        elif decision == "approve":
            # Approve wrong: nothing came of the approved finding
            if thread_entry_delta == 0 and novel_entity_delta == 0:
                try:
                    from .positive_room import record_failure  # noqa: PLC0415
                    record_failure(thread_stem, tag)
                    weight_delta       = -magnitude
                    correction_applied = True
                    log.info(
                        "Counterfactual correction (approve→wrong): %s::%s -%.2f",
                        thread_stem, tag, magnitude,
                    )
                except Exception:  # noqa: BLE001
                    pass

        rec["correction_applied"] = correction_applied
        rec["weight_delta"]       = weight_delta

        evaluated.append(rec)
        changed = True

    if changed:
        _save_cf(data)

    return evaluated


def mark_resurfaced(thread_stem: str, tag: str) -> int:
    """Increment resurfaced_in_cycles for pending dismissed records on this trajectory.

    Call this when a dismissed finding re-appears in a new cycle.
    Provides a signal-counting trail without affecting correction logic.

    Returns count of records updated.
    """
    data    = _load_cf()
    updated = 0
    for rec in data["records"]:
        if (
            rec.get("decision") == "dismiss"
            and rec.get("thread_stem") == thread_stem
            and rec.get("tag") == tag
            and rec.get("evaluated_at") is None
        ):
            rec["resurfaced_in_cycles"] = rec.get("resurfaced_in_cycles", 0) + 1
            updated += 1
    if updated:
        _save_cf(data)
    return updated


def counterfactual_status() -> dict:
    """Return summary of Counterfactual Room state."""
    data    = _load_cf()
    records = data.get("records", [])

    pending     = [r for r in records if r.get("evaluated_at") is None]
    evaluated   = [r for r in records if r.get("evaluated_at") is not None]
    corrections = [r for r in evaluated if r.get("correction_applied")]

    return {
        "total_records":       len(records),
        "pending_evaluation":  len(pending),
        "evaluated":           len(evaluated),
        "corrections_applied": len(corrections),
        "bounds": {
            "evaluation_days":      BOUNDS.counterfactual_evaluation_days,
            "min_signal":           BOUNDS.counterfactual_min_signal,
            "correction_magnitude": BOUNDS.counterfactual_correction_magnitude,
        },
    }


def list_pending_evaluations() -> list[dict]:
    """Return records not yet evaluated (mature and immature both included)."""
    data = _load_cf()
    return [r for r in data.get("records", []) if r.get("evaluated_at") is None]
