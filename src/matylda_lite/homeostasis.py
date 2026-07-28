"""homeostasis.py — v0.4.5 internal state regulation.

Tracks four runtime signals:
  active_goals    — what Matylda is currently working toward (max: BOUNDS.max_open_goals)
  attention_budget — topics consumed this session (max: BOUNDS.attention_budget_per_session)
  fatigue         — cumulative load (0.0 rested → 1.0 exhausted)
  stale_items     — attention items that aged past BOUNDS.stale_item_age_hours

All limits come from constitutional.BOUNDS — this module never defines its own.

Design:
  - Each function is side-effect-safe: reads then writes atomically.
  - All state lives in homeostasis/*.json at ROOT.
  - Homeostasis does NOT call secretary, sleeping_matylda, or darkroom —
    it is a leaf node in the dependency graph.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT
from .constitutional import BOUNDS

HOMEOSTASIS_DIR = ROOT / "homeostasis"
HOMEOSTASIS_DIR.mkdir(parents=True, exist_ok=True)

_GOALS_FILE     = HOMEOSTASIS_DIR / "active_goals.json"
_BUDGET_FILE    = HOMEOSTASIS_DIR / "attention_budget.json"
_FATIGUE_FILE   = HOMEOSTASIS_DIR / "fatigue.json"
_STALE_FILE     = HOMEOSTASIS_DIR / "stale_items.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def _save(path: Path, data: dict) -> None:
    from .atomic_state import atomic_write_json  # noqa: PLC0415
    atomic_write_json(path, data)


# ── Active Goals ──────────────────────────────────────────────────────────────

_CLOSED_GOALS_KEEP = 3  # how many recent closed goals to retain


def _prune_closed_goals(data: dict) -> bool:
    """Remove old closed goals beyond the retention window. Returns True if pruned."""
    goals: list[dict] = data.get("goals", [])
    closed = [g for g in goals if g.get("status") == "closed"]
    if len(closed) <= _CLOSED_GOALS_KEEP:
        return False
    # Keep the _CLOSED_GOALS_KEEP most recently closed
    closed_sorted = sorted(closed, key=lambda g: g.get("closed") or "", reverse=True)
    keep_ids = {g["goal_id"] for g in closed_sorted[:_CLOSED_GOALS_KEEP]}
    data["goals"] = [g for g in goals if g.get("status") != "closed" or g["goal_id"] in keep_ids]
    return True


def list_goals() -> list[dict]:
    """Return current goals (active + recent closed). Prunes stale closed goals."""
    data = _load(_GOALS_FILE, {"goals": []})
    if _prune_closed_goals(data):
        _save(_GOALS_FILE, data)
    return data.get("goals", [])


def add_goal(title: str, description: str = "", tags: list[str] | None = None) -> dict:
    """Add a new active goal. Raises ValueError if at capacity.

    Goal dict: {goal_id, title, description, tags, created, status: "active"}
    """
    data = _load(_GOALS_FILE, {"goals": []})
    goals: list[dict] = data.get("goals", [])
    active = [g for g in goals if g.get("status") == "active"]

    if len(active) >= BOUNDS.max_open_goals:
        raise ValueError(
            f"Limit aktywnych celów osiągnięty ({BOUNDS.max_open_goals}). "
            "Zamknij jeden cel przed dodaniem nowego."
        )

    goal: dict[str, Any] = {
        "goal_id":     f"goal_{uuid.uuid4().hex[:8]}",
        "title":       title.strip(),
        "description": description.strip(),
        "tags":        tags or [],
        "created":     _now_iso(),
        "status":      "active",
        "closed":      None,
    }
    goals.append(goal)
    data["goals"] = goals
    _save(_GOALS_FILE, data)
    return goal


def close_goal(goal_id: str, resolution: str = "") -> bool:
    """Mark a goal as closed. Returns True if found and closed."""
    data = _load(_GOALS_FILE, {"goals": []})
    goals: list[dict] = data.get("goals", [])
    found = False
    for g in goals:
        if g.get("goal_id") == goal_id:
            g["status"] = "closed"
            g["closed"] = _now_iso()
            g["resolution"] = resolution.strip()
            found = True
            break
    if found:
        data["goals"] = goals
        _prune_closed_goals(data)
        _save(_GOALS_FILE, data)
    return found


def goals_status() -> dict:
    """Summary dict for briefing / dashboard."""
    goals = list_goals()
    active = [g for g in goals if g.get("status") == "active"]
    return {
        "active_count": len(active),
        "max_goals":    BOUNDS.max_open_goals,
        "at_capacity":  len(active) >= BOUNDS.max_open_goals,
        "goals":        active,
    }


# ── Attention Budget ──────────────────────────────────────────────────────────

def session_start(session_id: str) -> None:
    """Reset attention budget for a new session."""
    data = {
        "_schema":      "attention_budget/v0.4.5",
        "_max_topics":  BOUNDS.attention_budget_per_session,
        "session_id":   session_id,
        "session_start": _now_iso(),
        "topics_used":  0,
        "topics":       [],
    }
    _save(_BUDGET_FILE, data)


def consume_attention(topic: str) -> dict:
    """Register one attention unit for `topic`. Returns budget state.

    Does NOT raise on overflow — caller decides how to handle warning.
    """
    data = _load(_BUDGET_FILE, {
        "session_id": None, "topics_used": 0, "topics": []
    })
    topics: list[str] = data.get("topics", [])
    if topic not in topics:
        topics.append(topic)
    data["topics"] = topics
    data["topics_used"] = len(topics)
    _save(_BUDGET_FILE, data)

    over = data["topics_used"] > BOUNDS.attention_budget_per_session
    return {
        "topics_used": data["topics_used"],
        "max":         BOUNDS.attention_budget_per_session,
        "over_budget": over,
        "warning":     "Uwaga: przekroczono budżet uwagi tej sesji." if over else None,
    }


def attention_status() -> dict:
    data = _load(_BUDGET_FILE, {"topics_used": 0, "topics": []})
    used = data.get("topics_used", 0)
    return {
        "topics_used": used,
        "max":         BOUNDS.attention_budget_per_session,
        "over_budget": used > BOUNDS.attention_budget_per_session,
        "session_id":  data.get("session_id"),
        "topics":      data.get("topics", []),
    }


# ── Fatigue ───────────────────────────────────────────────────────────────────

def tick_fatigue() -> dict:
    """Called at session start. Increments fatigue or recovers if enough time passed.

    Returns current fatigue state dict.
    """
    data = _load(_FATIGUE_FILE, {"fatigue": 0.0, "last_session": None, "session_count_since_rest": 0})
    last_str = data.get("last_session")
    now = datetime.now(timezone.utc)

    if last_str:
        last = datetime.fromisoformat(last_str)
        gap_hours = (now - last).total_seconds() / 3600
        if gap_hours >= BOUNDS.fatigue_recovery_hours:
            # Rested: reset to 0, then apply this session's increment
            data["fatigue"] = BOUNDS.fatigue_increment_per_session
            data["session_count_since_rest"] = 1
        else:
            data["fatigue"] = min(1.0, data.get("fatigue", 0.0) + BOUNDS.fatigue_increment_per_session)
            data["session_count_since_rest"] = data.get("session_count_since_rest", 0) + 1
    else:
        data["fatigue"] = BOUNDS.fatigue_increment_per_session  # first ever session

    data["last_session"] = now.isoformat()
    _save(_FATIGUE_FILE, data)

    return fatigue_status(data)


def fatigue_status(data: dict | None = None) -> dict:
    if data is None:
        data = _load(_FATIGUE_FILE, {"fatigue": 0.0, "last_session": None, "session_count_since_rest": 0})
    fatigue = data.get("fatigue", 0.0)
    return {
        "fatigue":              round(fatigue, 3),
        "high":                 fatigue >= BOUNDS.fatigue_high_threshold,
        "fatigue_high_threshold": BOUNDS.fatigue_high_threshold,
        "session_count_since_rest": data.get("session_count_since_rest", 0),
        "last_session":         data.get("last_session"),
        "recommendation":       (
            "Zmniejsz głębokość syntezy Sleeping Matylda — wysoki poziom zmęczenia."
            if fatigue >= BOUNDS.fatigue_high_threshold else None
        ),
    }


# ── Stale Items ───────────────────────────────────────────────────────────────

def register_attention_item(label: str, thread_stem: str | None = None) -> str:
    """Register a new attention item for staleness tracking.

    Returns item_id. Items not resolved within BOUNDS.stale_item_age_hours
    are surfaced in the next briefing.
    """
    data = _load(_STALE_FILE, {"stale_items": []})
    items: list[dict] = data.get("stale_items", [])

    item_id = f"attn_{uuid.uuid4().hex[:8]}"
    items.append({
        "item_id":     item_id,
        "label":       label.strip(),
        "thread_stem": thread_stem,
        "registered":  _now_iso(),
        "resolved":    False,
    })
    data["stale_items"] = items
    _save(_STALE_FILE, data)
    return item_id


def resolve_attention_item(item_id: str) -> bool:
    """Mark an attention item as resolved. Returns True if found."""
    data = _load(_STALE_FILE, {"stale_items": []})
    items: list[dict] = data.get("stale_items", [])
    for item in items:
        if item.get("item_id") == item_id:
            item["resolved"] = True
            item["resolved_at"] = _now_iso()
            data["stale_items"] = items
            _save(_STALE_FILE, data)
            return True
    return False


def get_stale_items() -> list[dict]:
    """Return unresolved items older than BOUNDS.stale_item_age_hours."""
    data = _load(_STALE_FILE, {"stale_items": []})
    now = datetime.now(timezone.utc)
    stale: list[dict] = []
    for item in data.get("stale_items", []):
        if item.get("resolved"):
            continue
        try:
            registered = datetime.fromisoformat(item["registered"])
            age_hours = (now - registered).total_seconds() / 3600
            if age_hours >= BOUNDS.stale_item_age_hours:
                stale.append({**item, "age_hours": round(age_hours, 1)})
        except Exception:  # noqa: BLE001
            pass
    return stale


# ── Full status snapshot ──────────────────────────────────────────────────────

def homeostasis_status() -> dict[str, Any]:
    """Return a full homeostasis snapshot for dashboard / briefing."""
    return {
        "goals":      goals_status(),
        "attention":  attention_status(),
        "fatigue":    fatigue_status(),
        "stale_items": get_stale_items(),
        "constitutional_version": BOUNDS.__class__.__module__ + ".BOUNDS v" +
                                  __import__("matylda_lite.constitutional",
                                             fromlist=["CONSTITUTIONAL_VERSION"]
                                             ).CONSTITUTIONAL_VERSION,
    }
