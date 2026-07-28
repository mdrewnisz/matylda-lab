"""positive_room.py — v0.9 Positive Room: trajectory attraction map.

Design principle:
  "Pamiętaj gdzie było dobrze. Wracaj tam — ale nie za bardzo."

Positive Room is the yin to NoGo Room's yang. It tracks which trajectories
(thread::tag pairs) consistently yielded good results, and makes them more
attractive in branch_evaluator — but with diminishing novelty returns.

Key asymmetry vs NoGo Room:
  - record_success() is ADDITIVE (like NoGo's record_failure)
  - record_failure() is MULTIPLICATIVE DECAY (like NoGo's record_success)
  - This means: failures reduce attraction slowly, success builds it quickly

Novelty floor (positive_novelty_floor = 0.25):
  Prevents very familiar trajectories from dying due to over-exploitation.
  Some things should stay permanently attractive (stable heuristics, core patterns).

Branch evaluator integration:
  exploration_cost -= positive_component * novelty_factor
  where:
    novelty_factor = max(positive_novelty_floor, 1 / (1 + log(1 + reuse_count)))
    positive_component = min(1.0, effective_success / positive_success_threshold)

Effective success (same pattern as NoGo's effective_risk):
  effective_success = success_score
                      * evidence_discount(evidence_count)
                      * time_discount(days_since_last_success)
  where time_discount = exp(-nogo_decay_k * days)   ← same decay constant, symmetry

State file: data/positive_room.json
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT
from .constitutional import BOUNDS

_POSITIVE_FILE = ROOT / "data" / "positive_room.json"
_POSITIVE_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    try:
        return json.loads(_POSITIVE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"trajectories": {}}


def _save(data: dict) -> None:
    _POSITIVE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                              encoding="utf-8")


def _traj_id(thread_stem: str, tag: str) -> str:
    return f"{thread_stem}::{tag}"


def _effective_success(entry: dict) -> float:
    """Compute effective_success from stored values + temporal decay + evidence discount.

    Mirrors nogo_room._effective_risk() for architectural symmetry.
    """
    stored = entry.get("success_score", 0.0)
    if stored <= 0.0:
        return 0.0

    last_success = entry.get("last_success")
    if last_success:
        try:
            delta = (
                datetime.now(timezone.utc) - datetime.fromisoformat(last_success)
            ).total_seconds() / 86400
            time_discount = math.exp(-BOUNDS.nogo_decay_k * delta)
        except Exception:  # noqa: BLE001
            time_discount = 1.0
    else:
        time_discount = 1.0

    evidence = entry.get("evidence_count", 0)
    evidence_discount = min(1.0, evidence / max(BOUNDS.nogo_min_evidence_count, 1))

    return round(stored * time_discount * evidence_discount, 4)


def _get_or_create(data: dict, thread_stem: str, tag: str) -> dict:
    tid = _traj_id(thread_stem, tag)
    if tid not in data["trajectories"]:
        data["trajectories"][tid] = {
            "trajectory_id":  tid,
            "thread_stem":    thread_stem,
            "tag":            tag,
            "success_score":  0.0,
            "stability_score": 1.0,    # starts optimistic, degrades on failures
            "reuse_count":    0,
            "success_count":  0,
            "evidence_count": 0,
            "last_success":   _now_iso(),
        }
    return data["trajectories"][tid]


# ── Public API ────────────────────────────────────────────────────────────────

def record_success(thread_stem: str, tag: str) -> dict:
    """Record a success event for a trajectory.

    success_score increases additively by positive_success_weight (capped at 1.0).
    stability_score updated from success ratio. Returns entry with effective_success.
    """
    data  = _load()
    entry = _get_or_create(data, thread_stem, tag)

    entry["success_score"]  = min(1.0, entry["success_score"] + BOUNDS.positive_success_weight)
    entry["reuse_count"]    = entry.get("reuse_count", 0) + 1
    entry["success_count"]  = entry.get("success_count", 0) + 1
    entry["evidence_count"] = entry.get("evidence_count", 0) + 1
    entry["last_success"]   = _now_iso()

    # stability = proportion of successes in all evidence
    entry["stability_score"] = round(
        entry["success_count"] / max(1, entry["evidence_count"]), 3
    )

    _prune_if_needed(data)
    _save(data)
    return {**entry, "effective_success": _effective_success(entry)}


def record_failure(thread_stem: str, tag: str) -> dict:
    """Record a failure for a trajectory.

    success_score decays multiplicatively: score *= (1 - positive_failure_weight).
    Never reaches 0 — history of successes persists.
    Returns entry with effective_success (or zero-entry if trajectory unknown).
    """
    data = _load()
    tid  = _traj_id(thread_stem, tag)
    if tid not in data["trajectories"]:
        return {"trajectory_id": tid, "success_score": 0.0, "effective_success": 0.0}

    entry = data["trajectories"][tid]
    entry["success_score"]  = round(
        entry["success_score"] * (1 - BOUNDS.positive_failure_weight), 4
    )
    entry["evidence_count"] = entry.get("evidence_count", 0) + 1
    entry["stability_score"] = round(
        entry.get("success_count", 0) / max(1, entry["evidence_count"]), 3
    )

    _save(data)
    return {**entry, "effective_success": _effective_success(entry)}


def get_success_score(thread_stem: str, tag: str) -> float:
    """Return effective_success for a trajectory. 0.0 if unknown."""
    data  = _load()
    tid   = _traj_id(thread_stem, tag)
    entry = data["trajectories"].get(tid)
    if entry is None:
        return 0.0
    return _effective_success(entry)


def get_trajectory(thread_stem: str, tag: str) -> dict | None:
    """Return full trajectory entry with effective_success, or None."""
    data  = _load()
    tid   = _traj_id(thread_stem, tag)
    entry = data["trajectories"].get(tid)
    if entry is None:
        return None
    return {**entry, "effective_success": _effective_success(entry)}


def list_attractive_trajectories(threshold: float | None = None) -> list[dict]:
    """Return trajectories whose effective_success >= threshold.

    Default threshold: BOUNDS.positive_success_threshold.
    Results sorted by effective_success descending.
    """
    if threshold is None:
        threshold = BOUNDS.positive_success_threshold
    data   = _load()
    result = []
    for entry in data["trajectories"].values():
        eff = _effective_success(entry)
        if eff >= threshold:
            result.append({**entry, "effective_success": eff})
    result.sort(key=lambda e: e["effective_success"], reverse=True)
    return result


def positive_status() -> dict:
    """Return summary of Positive Room state."""
    data      = _load()
    trajs     = data["trajectories"]
    threshold = BOUNDS.positive_success_threshold
    attractive = sum(
        1 for e in trajs.values()
        if _effective_success(e) >= threshold
    )
    file_str = (
        str(_POSITIVE_FILE.relative_to(ROOT))
        if _POSITIVE_FILE.is_relative_to(ROOT)
        else str(_POSITIVE_FILE)
    )
    return {
        "total_entries":      len(trajs),
        "attractive_count":   attractive,
        "threshold":          threshold,
        "novelty_floor":      BOUNDS.positive_novelty_floor,
        "file":               file_str,
    }


def prune_old_entries(max_entries: int | None = None) -> int:
    """Remove lowest-success entries until at most max_entries remain.

    Pruning by lowest effective_success — weakest memories go first.
    Returns count removed.
    """
    if max_entries is None:
        max_entries = BOUNDS.positive_max_entries
    data  = _load()
    trajs = data["trajectories"]
    if len(trajs) <= max_entries:
        return 0
    sorted_ids = sorted(trajs, key=lambda tid: _effective_success(trajs[tid]))
    to_remove  = sorted_ids[:len(trajs) - max_entries]
    for tid in to_remove:
        del trajs[tid]
    _save(data)
    return len(to_remove)


# ── Internal ──────────────────────────────────────────────────────────────────

def _prune_if_needed(data: dict) -> None:
    trajs = data["trajectories"]
    if len(trajs) > BOUNDS.positive_max_entries:
        sorted_ids = sorted(trajs, key=lambda tid: _effective_success(trajs[tid]))
        for tid in sorted_ids[:len(trajs) - BOUNDS.positive_max_entries]:
            del trajs[tid]
