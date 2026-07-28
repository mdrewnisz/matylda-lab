"""nogo_room.py — v0.8 NoGo Room: trajectory risk map.

Design principle:
  "Podnieś koszt eksploracji, nie stawiaj murów."

NoGo Room is NOT a blacklist. It is a risk-weighted map of exploration territory:
  - Bad trajectories get higher exploration_cost
  - High-risk trajectories → findings with reduced confidence
  - Success events reduce risk multiplicatively (never to zero — history persists)
  - Risk decays over time (prevents neurotic memory of old failures)
  - Evidence count discounts risk when few data points exist

Trajectory identity:
  trajectory_id = f"{thread_stem}::{tag}"
  e.g. "python_async::recursion"

Risk model:
  stored_risk   — persisted raw score (failure/success events)
  effective_risk — computed at query time:
    effective_risk = stored_risk
                     * evidence_discount(evidence_count)
                     * time_discount(days_since_last_seen)

State file: data/nogo_room.json
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT
from .constitutional import BOUNDS

_NOGO_FILE = ROOT / "data" / "nogo_room.json"
_NOGO_FILE.parent.mkdir(parents=True, exist_ok=True)

VALID_CATEGORIES = frozenset({
    "narrative_drift",
    "recursive_loop",
    "branch_explosion",
    "local_maximum",
    "contradiction_cluster",
    "overcomplexity",
    "repeated_failure",
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    try:
        return json.loads(_NOGO_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"trajectories": {}}


def _save(data: dict) -> None:
    _NOGO_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def _traj_id(thread_stem: str, tag: str) -> str:
    return f"{thread_stem}::{tag}"


def _effective_risk(entry: dict) -> float:
    """Compute effective_risk from stored values + temporal decay + evidence discount."""
    stored = entry.get("risk_score", 0.0)
    if stored <= 0.0:
        return 0.0

    # Temporal decay: effective = stored * exp(-k * days_since_last_seen)
    last_seen = entry.get("last_seen")
    if last_seen:
        try:
            delta = (
                datetime.now(timezone.utc) - datetime.fromisoformat(last_seen)
            ).total_seconds() / 86400  # days
            time_discount = math.exp(-BOUNDS.nogo_decay_k * delta)
        except Exception:  # noqa: BLE001
            time_discount = 1.0
    else:
        time_discount = 1.0

    # Evidence discount: few data points → discounted risk
    evidence = entry.get("evidence_count", 0)
    evidence_discount = min(1.0, evidence / BOUNDS.nogo_min_evidence_count)

    return round(stored * time_discount * evidence_discount, 4)


def _get_or_create(data: dict, thread_stem: str, tag: str, category: str) -> dict:
    tid = _traj_id(thread_stem, tag)
    if tid not in data["trajectories"]:
        data["trajectories"][tid] = {
            "trajectory_id":        tid,
            "thread_stem":          thread_stem,
            "tag":                  tag,
            "category":             category,
            "risk_score":           0.0,
            "drift_score":          0.0,
            "complexity_score":     0.0,
            "revisit_count":        0,
            "evidence_count":       0,
            "last_seen":            _now_iso(),
            # v1.1 signal accumulators
            "signal_dismiss_count": 0,
            "signal_approve_count": 0,
        }
    return data["trajectories"][tid]


# ── Public API ────────────────────────────────────────────────────────────────

def record_failure(thread_stem: str, tag: str, category: str = "repeated_failure") -> dict:
    """Record a failure event for a trajectory.

    risk_score increases additively by nogo_failure_weight (capped at 1.0).
    evidence_count incremented. Returns the updated entry with effective_risk.
    """
    if category not in VALID_CATEGORIES:
        category = "repeated_failure"

    data = _load()
    entry = _get_or_create(data, thread_stem, tag, category)

    entry["risk_score"]     = min(1.0, entry["risk_score"] + BOUNDS.nogo_failure_weight)
    entry["evidence_count"] = entry.get("evidence_count", 0) + 1
    entry["revisit_count"]  = entry.get("revisit_count", 0) + 1
    entry["category"]       = category
    entry["last_seen"]      = _now_iso()

    _prune_if_needed(data)
    _save(data)
    return {**entry, "effective_risk": _effective_risk(entry)}


def record_success(thread_stem: str, tag: str) -> dict:
    """Record a success event for a trajectory.

    risk_score decays multiplicatively: risk *= (1 - nogo_success_weight).
    Never reaches 0 — history of failures persists.
    evidence_count incremented. Returns the updated entry with effective_risk.
    """
    data = _load()
    tid  = _traj_id(thread_stem, tag)
    if tid not in data["trajectories"]:
        # Unknown trajectory — nothing to reduce
        return {"trajectory_id": tid, "risk_score": 0.0, "effective_risk": 0.0}

    entry = data["trajectories"][tid]
    entry["risk_score"]     = round(entry["risk_score"] * (1 - BOUNDS.nogo_success_weight), 4)
    entry["evidence_count"] = entry.get("evidence_count", 0) + 1
    entry["revisit_count"]  = entry.get("revisit_count", 0) + 1
    entry["last_seen"]      = _now_iso()

    _save(data)
    return {**entry, "effective_risk": _effective_risk(entry)}


def record_drift(thread_stem: str, tag: str, drift_score: float,
                 category: str = "narrative_drift") -> dict:
    """Update drift_score for a trajectory.

    risk_score += drift_score * nogo_drift_weight (capped at 1.0).
    Returns the updated entry with effective_risk.
    """
    data  = _load()
    entry = _get_or_create(data, thread_stem, tag, category)

    entry["drift_score"]    = round(drift_score, 4)
    entry["risk_score"]     = min(1.0, round(
        entry["risk_score"] + drift_score * BOUNDS.nogo_drift_weight, 4
    ))
    entry["evidence_count"] = entry.get("evidence_count", 0) + 1
    entry["last_seen"]      = _now_iso()

    _save(data)
    return {**entry, "effective_risk": _effective_risk(entry)}


def record_signal(thread_stem: str, tag: str, decision: str) -> dict:
    """Record a user approve/dismiss signal for a nogo_territory finding.

    Signals accumulate before affecting the risk score:
      decision == "dismiss":
        signal_dismiss_count += 1
        if count >= nogo_auto_failure_threshold:
          → risk increases (record_failure logic), counter resets
      decision == "approve":
        signal_approve_count += 1
        if count >= nogo_auto_success_threshold:
          → risk decreases (record_success logic), counter resets

    Rationale:
      Dismiss: user repeatedly ignores the warning → system reinforces it.
      Approve: user repeatedly engages with the risk → active engagement rewards.

    Returns entry dict with effective_risk and signal_applied flag.
    Returns early dict if trajectory is not tracked.
    """
    data = _load()
    tid  = _traj_id(thread_stem, tag)

    if tid not in data["trajectories"]:
        return {
            "trajectory_id": tid,
            "risk_score":    0.0,
            "effective_risk": 0.0,
            "signal_applied": False,
        }

    entry = data["trajectories"][tid]
    # Backfill signal counters for entries created before v1.1
    entry.setdefault("signal_dismiss_count", 0)
    entry.setdefault("signal_approve_count", 0)

    triggered = False

    if decision == "dismiss":
        entry["signal_dismiss_count"] += 1
        if entry["signal_dismiss_count"] >= BOUNDS.nogo_auto_failure_threshold:
            entry["signal_dismiss_count"] = 0  # reset after trigger
            # Inline risk increase (mirrors record_failure without extra I/O)
            entry["risk_score"]     = min(1.0, entry["risk_score"] + BOUNDS.nogo_failure_weight)
            entry["evidence_count"] = entry.get("evidence_count", 0) + 1
            entry["revisit_count"]  = entry.get("revisit_count",  0) + 1
            entry["last_seen"]      = _now_iso()
            triggered = True

    elif decision == "approve":
        entry["signal_approve_count"] += 1
        if entry["signal_approve_count"] >= BOUNDS.nogo_auto_success_threshold:
            entry["signal_approve_count"] = 0  # reset after trigger
            # Inline risk decrease (mirrors record_success without extra I/O)
            entry["risk_score"]     = round(
                entry["risk_score"] * (1 - BOUNDS.nogo_success_weight), 4
            )
            entry["evidence_count"] = entry.get("evidence_count", 0) + 1
            entry["revisit_count"]  = entry.get("revisit_count",  0) + 1
            entry["last_seen"]      = _now_iso()
            triggered = True

    _prune_if_needed(data)
    _save(data)
    return {**entry, "effective_risk": _effective_risk(entry), "signal_applied": triggered}


def get_risk_score(thread_stem: str, tag: str) -> float:
    """Return effective_risk_score for a trajectory. 0.0 if unknown."""
    data = _load()
    tid  = _traj_id(thread_stem, tag)
    entry = data["trajectories"].get(tid)
    if entry is None:
        return 0.0
    return _effective_risk(entry)


def get_trajectory(thread_stem: str, tag: str) -> dict | None:
    """Return full trajectory entry with effective_risk, or None."""
    data  = _load()
    tid   = _traj_id(thread_stem, tag)
    entry = data["trajectories"].get(tid)
    if entry is None:
        return None
    return {**entry, "effective_risk": _effective_risk(entry)}


def list_risky_trajectories(threshold: float | None = None) -> list[dict]:
    """Return all trajectories whose effective_risk >= threshold.

    Default threshold: BOUNDS.nogo_risk_threshold.
    Results sorted by effective_risk descending.
    """
    if threshold is None:
        threshold = BOUNDS.nogo_risk_threshold
    data = _load()
    result = []
    for entry in data["trajectories"].values():
        eff = _effective_risk(entry)
        if eff >= threshold:
            result.append({**entry, "effective_risk": eff})
    result.sort(key=lambda e: e["effective_risk"], reverse=True)
    return result


def prune_old_entries(max_entries: int | None = None) -> int:
    """Remove oldest entries until at most max_entries remain.

    'Oldest' = sorted by last_seen ascending. Returns count removed.
    """
    if max_entries is None:
        max_entries = BOUNDS.nogo_max_entries
    data = _load()
    trajs = data["trajectories"]
    if len(trajs) <= max_entries:
        return 0
    sorted_ids = sorted(trajs, key=lambda tid: trajs[tid].get("last_seen", ""))
    to_remove  = sorted_ids[:len(trajs) - max_entries]
    for tid in to_remove:
        del trajs[tid]
    _save(data)
    return len(to_remove)


def nogo_status() -> dict:
    """Return summary of NoGo Room state."""
    data  = _load()
    trajs = data["trajectories"]
    risky = sum(
        1 for e in trajs.values()
        if _effective_risk(e) >= BOUNDS.nogo_risk_threshold
    )
    file_str = (
        str(_NOGO_FILE.relative_to(ROOT))
        if _NOGO_FILE.is_relative_to(ROOT)
        else str(_NOGO_FILE)
    )
    return {
        "total_entries":   len(trajs),
        "high_risk_count": risky,
        "threshold":       BOUNDS.nogo_risk_threshold,
        "file":            file_str,
    }


# ── Internal ──────────────────────────────────────────────────────────────────

def _prune_if_needed(data: dict) -> None:
    """Inline prune before saving to keep cap enforcement synchronous."""
    trajs = data["trajectories"]
    if len(trajs) > BOUNDS.nogo_max_entries:
        sorted_ids = sorted(trajs, key=lambda tid: trajs[tid].get("last_seen", ""))
        for tid in sorted_ids[:len(trajs) - BOUNDS.nogo_max_entries]:
            del trajs[tid]
