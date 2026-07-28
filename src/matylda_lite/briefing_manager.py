"""Morning Briefing Manager — v0.9 → v0.4 diary-aware.

Checks whether a morning briefing should be shown (based on session gap),
loads the last Sleeping Matylda synthesis, and detects cross-thread connections.

v0.4 additions:
  - diary_entries: recent diary entries surfaced in the briefing
  - negative_summary: excerpt from memory/negative/ failure logs
  - rules_active: whether procedural rules are injected this session
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config as _config
from .constitutional import BOUNDS

_MIN_GAP_HOURS: float = BOUNDS.briefing_min_gap_hours


# ── Session tracking ──────────────────────────────────────────────────────────

def _session_file() -> Path:
    """Dynamic lookup so monkeypatching config.ROOT works in tests."""
    return _config.ROOT / "data" / "briefing_session.json"


def mark_session_start() -> None:
    """Record the current time as the start of a new session."""
    path = _session_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"last_session": datetime.now(timezone.utc).isoformat()},
                   ensure_ascii=False)
    )


def _last_session_time() -> datetime | None:
    path = _session_file()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        ts = data.get("last_session")
        if ts:
            return datetime.fromisoformat(ts)
    except Exception:  # noqa: BLE001
        pass
    return None


def should_show_briefing(min_gap_hours: float = _MIN_GAP_HOURS) -> bool:
    """Return True if ≥ min_gap_hours have passed since last session."""
    last = _last_session_time()
    if last is None:
        return False  # first-ever session — no history to brief about
    now = datetime.now(timezone.utc)
    gap = (now - last).total_seconds() / 3600
    return gap >= min_gap_hours


def gap_hours() -> float:
    """Return hours since last session (0.0 if unknown)."""
    last = _last_session_time()
    if last is None:
        return 0.0
    return (datetime.now(timezone.utc) - last).total_seconds() / 3600


# ── Sleeping Matylda ─────────────────────────────────────────────────────────

def _load_last_synthesis() -> dict | None:
    try:
        from .sleeping_matylda.synthesis import load_last_result  # noqa: PLC0415
        return load_last_result()
    except Exception:  # noqa: BLE001
        return None


# ── Cross-thread connections ──────────────────────────────────────────────────

_STOPWORDS: frozenset[str] = frozenset({
    # English
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "will", "would", "could", "should", "that", "this",
    "these", "those", "it", "its", "not", "also", "very", "more", "than",
    # Polish
    "że", "się", "nie", "jak", "ale", "czy", "przez", "jako", "więc", "już",
    "jest", "być", "ten", "tej", "tego", "ich", "jego", "jej", "przy", "tylko",
    "może", "tego", "który", "która", "które", "który", "oraz", "dla", "bez",
    "tym", "być", "można", "każdy", "każda", "jego", "nasz", "nasze",
})


def _extract_keywords(text: str) -> set[str]:
    words = re.findall(r"\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{4,}\b", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def detect_cross_thread_connections(max_threads: int = BOUNDS.max_threads_for_link_detection) -> list[dict]:
    """Find potential connections between threads by shared keyword overlap.

    Returns a list of connection dicts, sorted by score desc, limited to top 5.
    Each dict has: thread_a, thread_b, shared_keywords, score.
    """
    try:
        from .library_manager import list_threads, read_thread  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    threads = list_threads(include_archived=False)[:max_threads]
    if len(threads) < 2:
        return []

    # Collect (stem, title, keyword_set) for each thread
    thread_kws: list[tuple[str, str, set[str]]] = []
    for t in threads:
        try:
            content = read_thread(t["stem"])
        except Exception:  # noqa: BLE001
            content = t.get("title", "")
        kws = _extract_keywords(content)
        thread_kws.append((t["stem"], t.get("title", t["stem"]), kws))

    connections: list[dict] = []
    seen: set[frozenset] = set()

    for i, (stem_a, title_a, kws_a) in enumerate(thread_kws):
        for stem_b, title_b, kws_b in thread_kws[i + 1:]:
            if len(kws_a) < 5 or len(kws_b) < 5:
                continue
            shared = kws_a & kws_b
            if len(shared) < 3:
                continue
            score = len(shared) / min(len(kws_a), len(kws_b))
            if score < 0.06:
                continue
            key = frozenset([stem_a, stem_b])
            if key in seen:
                continue
            seen.add(key)
            connections.append({
                "thread_a": {"stem": stem_a, "title": title_a},
                "thread_b": {"stem": stem_b, "title": title_b},
                "shared_keywords": sorted(shared)[:8],
                "score": round(score, 3),
            })

    connections.sort(key=lambda c: c["score"], reverse=True)
    return connections[:BOUNDS.briefing_max_connections]


# ── Diary context ─────────────────────────────────────────────────────────────

def _load_diary_context() -> dict[str, Any]:
    """Load recent diary entries and negative memory summary for briefing."""
    try:
        from .diary_manager import (  # noqa: PLC0415
            get_recent_diary_for_briefing,
            load_negative_summary,
            load_rules_for_injection,
        )
        return {
            "diary_entries":    get_recent_diary_for_briefing(n=5),
            "negative_summary": load_negative_summary(),
            "rules_active":     bool(load_rules_for_injection(max_tokens=500)),
        }
    except Exception:  # noqa: BLE001
        return {
            "diary_entries":    [],
            "negative_summary": {},
            "rules_active":     False,
        }


# ── Main briefing builder ─────────────────────────────────────────────────────

def get_morning_briefing(force: bool = False) -> dict[str, Any]:
    """Build the morning briefing payload.

    Returns:
        show             – bool: whether to display the briefing
        gap_hours        – float: hours since last session
        synthesis        – dict | None: last Sleeping Matylda result
        connections      – list[dict]: cross-thread connections
        diary_entries    – list[dict]: recent diary entries (v0.4)
        negative_summary – dict[str, str]: failure pattern excerpts (v0.4)
        rules_active     – bool: are procedural rules injected? (v0.4)
        timestamp        – str: ISO timestamp of this call
    """
    _gap = gap_hours()
    show = force or should_show_briefing()

    synthesis: dict | None = None
    connections: list[dict] = []
    diary_ctx: dict[str, Any] = {
        "diary_entries": [],
        "negative_summary": {},
        "rules_active": False,
    }

    if show:
        synthesis = _load_last_synthesis()
        connections = detect_cross_thread_connections()
        diary_ctx = _load_diary_context()

    return {
        "show":             show,
        "gap_hours":        round(_gap, 1),
        "synthesis":        synthesis,
        "connections":      connections,
        "diary_entries":    diary_ctx["diary_entries"],
        "negative_summary": diary_ctx["negative_summary"],
        "rules_active":     diary_ctx["rules_active"],
        "timestamp":        datetime.now(timezone.utc).isoformat(),
    }
