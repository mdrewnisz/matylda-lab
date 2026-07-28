"""forgetroom.py — v1.1 Forgetroom: exponential decay of cognitive objects.

Design principle:
  "Nieaktywne obiekty zanikają. Często używane stabilizują się.
   Zanikanie jest lazy — obliczane z timestampa, nie persisted."

Weight formula:
  effective_weight(t) = initial_weight * (1 + log(1 + reinforcement_count))
                        * exp(-forgetroom_decay_k * days_since_last_activation)

This means:
  - A fresh object (reinf=0) decays normally from initial_weight
  - Each activation resets the clock AND increments reinforcement_count
  - More reinforcement → slower effective decay (log-bounded)
  - Spam activations give diminishing returns (log growth)

Object types tracked:
  "entity"             — knowledge graph entity (entity_id)
  "reflection"         — diary reflection (reflection_id)
  "reflection_pattern" — exploration pattern for a thread_stem (v1.1)
                         Tracks how alive a conceptual pattern is, not a specific
                         document. object_id == thread_stem. Extra fields:
                           pattern_version        — incremented on structural shift
                           source_reflection_count — how many reflections contributed
  "tension"            — darkroom tension (tension_id)

Finding integration:
  Objects below forgetroom_prune_threshold surface as 'forgotten_object'
  findings in Sleeping Matylda — user must approve before any removal.

State file: data/forgetroom.json
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT
from .constitutional import BOUNDS

_FORGETROOM_FILE = ROOT / "data" / "forgetroom.json"
_FORGETROOM_FILE.parent.mkdir(parents=True, exist_ok=True)

VALID_OBJECT_TYPES = frozenset({"entity", "reflection", "reflection_pattern", "tension"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    try:
        return json.loads(_FORGETROOM_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"objects": {}}


def _save(data: dict) -> None:
    _FORGETROOM_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                encoding="utf-8")


def _compute_weight(entry: dict) -> float:
    """Compute effective_weight lazily from the stored entry.

    effective_weight = initial_weight
                       * (1 + log(1 + reinforcement_count))
                       * exp(-k * delta_days)
    """
    initial   = entry.get("initial_weight", 1.0)
    reinf     = entry.get("reinforcement_count", 0)
    last_act  = entry.get("last_activation")

    # Reinforcement multiplier (log-bounded, starts at 1.0 for reinf=0)
    reinf_multiplier = 1.0 + math.log(1 + reinf)

    # Temporal decay
    if last_act:
        try:
            delta_days = (
                datetime.now(timezone.utc) - datetime.fromisoformat(last_act)
            ).total_seconds() / 86400
            time_factor = math.exp(-BOUNDS.forgetroom_decay_k * delta_days)
        except Exception:  # noqa: BLE001
            time_factor = 1.0
    else:
        time_factor = 1.0

    return round(initial * reinf_multiplier * time_factor, 4)


# ── Public API ────────────────────────────────────────────────────────────────

def register_object(
    object_id: str,
    object_type: str,
    initial_weight: float = 1.0,
) -> dict:
    """Register a cognitive object for decay tracking.

    General rule (entity / reflection / tension):
      Idempotent — re-registration preserves weight and reinforcement_count.

    Special rule (reflection_pattern):
      First registration adds pattern_version=1 and source_reflection_count=1.
      Re-registration increments source_reflection_count (accumulates evidence).
      pattern_version bump on structural shift is a stub for now (always skipped).

    Args:
        object_id:      Unique ID. For reflection_pattern: use thread_stem.
        object_type:    One of: "entity", "reflection", "reflection_pattern", "tension"
        initial_weight: Starting weight (default 1.0). Persisted — affects decay scale.

    Returns:
        Entry dict including computed effective_weight.
    """
    if object_type not in VALID_OBJECT_TYPES:
        object_type = "entity"  # safe fallback

    data = _load()

    if object_id not in data["objects"]:
        entry: dict = {
            "object_id":           object_id,
            "object_type":         object_type,
            "initial_weight":      round(initial_weight, 4),
            "last_activation":     _now_iso(),
            "reinforcement_count": 0,
        }
        # reflection_pattern gets extra trajectory-pattern fields
        if object_type == "reflection_pattern":
            entry["pattern_version"]         = 1
            entry["source_reflection_count"] = 1
        data["objects"][object_id] = entry
        _prune_if_needed(data)
        _save(data)

    elif object_type == "reflection_pattern":
        # Re-registration: accumulate source evidence
        # structural_similarity check is a stub — pattern_version bump deferred
        entry = data["objects"][object_id]
        entry["source_reflection_count"] = entry.get("source_reflection_count", 1) + 1
        _save(data)

    # else: other types are fully idempotent — no action on re-registration

    entry = data["objects"][object_id]
    return {**entry, "effective_weight": _compute_weight(entry)}


def activate_object(object_id: str) -> dict:
    """Reinforce an object: reset clock + increment reinforcement_count.

    Resets last_activation to now (clock restart), increments reinforcement_count
    (increases the log-multiplier for future decay).

    Raises:
        KeyError: If object_id not registered.
    """
    data = _load()
    if object_id not in data["objects"]:
        raise KeyError(f"Object not tracked: {object_id!r}. Call register_object() first.")

    entry = data["objects"][object_id]
    entry["last_activation"]     = _now_iso()
    entry["reinforcement_count"] = entry.get("reinforcement_count", 0) + 1

    _save(data)
    return {**entry, "effective_weight": _compute_weight(entry)}


def get_effective_weight(object_id: str) -> float:
    """Return effective_weight for object. 0.0 if not tracked."""
    data  = _load()
    entry = data["objects"].get(object_id)
    if entry is None:
        return 0.0
    return _compute_weight(entry)


def get_forgotten_candidates(threshold: float | None = None) -> list[dict]:
    """Return objects whose effective_weight < threshold.

    Results sorted by effective_weight ascending (most forgotten first).
    Each entry includes: object_id, object_type, effective_weight, days_since_activation.
    """
    if threshold is None:
        threshold = BOUNDS.forgetroom_prune_threshold

    data = _load()
    result = []
    now   = datetime.now(timezone.utc)

    for entry in data["objects"].values():
        ew = _compute_weight(entry)
        if ew < threshold:
            try:
                delta_days = (
                    now - datetime.fromisoformat(entry.get("last_activation", _now_iso()))
                ).total_seconds() / 86400
            except Exception:  # noqa: BLE001
                delta_days = 0.0
            result.append({
                **entry,
                "effective_weight":     ew,
                "days_since_activation": round(delta_days, 1),
            })

    result.sort(key=lambda e: e["effective_weight"])
    return result


def forgetroom_summary() -> dict:
    """Return summary of Forgetroom state."""
    data      = _load()
    objects   = data["objects"]
    threshold = BOUNDS.forgetroom_prune_threshold
    forgotten = sum(1 for e in objects.values() if _compute_weight(e) < threshold)
    now       = datetime.now(timezone.utc)

    oldest: dict | None = None
    max_days = -1.0
    for entry in objects.values():
        try:
            d = (now - datetime.fromisoformat(entry.get("last_activation", _now_iso()))
                 ).total_seconds() / 86400
        except Exception:  # noqa: BLE001
            d = 0.0
        if d > max_days:
            max_days = d
            oldest   = {"object_id": entry["object_id"], "days_since_activation": round(d, 1)}

    file_str = (
        str(_FORGETROOM_FILE.relative_to(ROOT))
        if _FORGETROOM_FILE.is_relative_to(ROOT)
        else str(_FORGETROOM_FILE)
    )
    return {
        "total_objects":  len(objects),
        "forgotten_count": forgotten,
        "threshold":       threshold,
        "oldest_object":   oldest,
        "file":            file_str,
    }


def prune_objects(max_objects: int | None = None) -> int:
    """Remove lowest-weight objects until at most max_objects remain.

    Returns count removed.
    """
    if max_objects is None:
        max_objects = BOUNDS.forgetroom_max_objects

    data    = _load()
    objects = data["objects"]
    if len(objects) <= max_objects:
        return 0

    sorted_ids = sorted(objects, key=lambda oid: _compute_weight(objects[oid]))
    to_remove  = sorted_ids[:len(objects) - max_objects]
    for oid in to_remove:
        del objects[oid]
    _save(data)
    return len(to_remove)


# ── Internal ──────────────────────────────────────────────────────────────────

def _prune_if_needed(data: dict) -> None:
    """Inline prune before saving to keep cap enforcement synchronous."""
    objects = data["objects"]
    if len(objects) > BOUNDS.forgetroom_max_objects:
        sorted_ids = sorted(objects, key=lambda oid: _compute_weight(objects[oid]))
        for oid in sorted_ids[:len(objects) - BOUNDS.forgetroom_max_objects]:
            del objects[oid]
