"""stale_scanner.py — v0.5 proactive stale-thread suggestions.

Runs periodically (every BOUNDS.stale_scan_interval_hours) via ThreadWatcher.
Scans active threads, identifies those past BOUNDS.stale_thread_age_days
with no writes, generates up to BOUNDS.max_proactive_suggestions actionable
suggestions — but only when attention budget is not exhausted.

Suggestion format:
  {
    "suggestion_id": "sug_<8hex>",
    "stem":          str,
    "title":         str,
    "age_days":      float,
    "last_modified": ISO str,
    "actions":       ["freeze", "explore:<query>", "snooze_7d"],
    "created":       ISO str,
    "snoozed_until": ISO str | null,
    "dismissed":     bool,
  }

Storage: homeostasis/suggestions.json
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import ROOT
from .constitutional import BOUNDS

SUGGESTIONS_FILE = ROOT / "homeostasis" / "suggestions.json"
SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

_THREADS_DIR = ROOT / "library" / "threads"


# ── I/O ───────────────────────────────────────────────────────────────────────

def _load() -> dict:
    if not SUGGESTIONS_FILE.exists():
        return {"suggestions": [], "last_scan": None}
    try:
        return json.loads(SUGGESTIONS_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"suggestions": [], "last_scan": None}


def _save(data: dict) -> None:
    SUGGESTIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ── Scan ──────────────────────────────────────────────────────────────────────

def _thread_title(path: Path) -> str:
    """Extract first heading or fall back to stem."""
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:10]:
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    except Exception:  # noqa: BLE001
        pass
    return path.stem.replace("_", " ").title()


def _is_frozen(stem: str) -> bool:
    """Check if thread is frozen (status file or status in thread metadata)."""
    try:
        from .library_manager import list_threads  # noqa: PLC0415
        threads = list_threads(include_archived=False)
        for t in threads:
            if t.get("stem") == stem:
                return t.get("status") == "frozen"
    except Exception:  # noqa: BLE001
        pass
    return False


def _attention_budget_ok() -> bool:
    """Return True if attention budget allows a new suggestion cycle."""
    try:
        from .homeostasis import attention_status  # noqa: PLC0415
        st = attention_status()
        return not st.get("over_budget", False)
    except Exception:  # noqa: BLE001
        return True  # fail-open


def _build_explore_query(stem: str) -> str:
    """Suggest a follow-up question based on thread stem keywords."""
    words = [w for w in stem.replace("_", " ").split() if len(w) > 3][:3]
    if words:
        return f"Co nowego w temacie: {' '.join(words)}?"
    return "Czy są nowe informacje na ten temat?"


def scan_stale_threads() -> list[dict]:
    """Scan active threads and return a list of staleness suggestions.

    Respects:
    - BOUNDS.stale_thread_age_days: minimum age to qualify
    - BOUNDS.max_proactive_suggestions: cap on results
    - Attention budget: returns [] if over_budget
    - Snoozed items: skips until snooze expires
    - Frozen threads: skipped
    """
    if not _attention_budget_ok():
        return []

    if not _THREADS_DIR.exists():
        return []

    now = datetime.now(timezone.utc)
    threshold_seconds = BOUNDS.stale_thread_age_days * 86400

    # Load existing suggestions to check snooze / dismiss state
    existing = _load()
    snoozed_stems: set[str] = set()
    dismissed_stems: set[str] = set()
    for s in existing.get("suggestions", []):
        if s.get("dismissed"):
            dismissed_stems.add(s["stem"])
            continue
        snooze_until = s.get("snoozed_until")
        if snooze_until:
            try:
                until = datetime.fromisoformat(snooze_until)
                if until > now:
                    snoozed_stems.add(s["stem"])
            except Exception:  # noqa: BLE001
                pass

    candidates: list[tuple[float, Path]] = []
    for p in _THREADS_DIR.glob("*.md"):
        if not p.is_file() or "archive" in p.parts:
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        age = now.timestamp() - mtime
        if age >= threshold_seconds:
            candidates.append((age, p))

    # Sort: oldest first
    candidates.sort(key=lambda x: x[0], reverse=True)

    suggestions: list[dict] = []
    for age_secs, p in candidates:
        if len(suggestions) >= BOUNDS.max_proactive_suggestions:
            break
        stem = p.stem
        if stem in snoozed_stems or stem in dismissed_stems:
            continue
        if _is_frozen(stem):
            continue

        age_days = round(age_secs / 86400, 1)
        last_modified = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()

        suggestions.append({
            "suggestion_id": f"sug_{uuid.uuid4().hex[:8]}",
            "stem":          stem,
            "title":         _thread_title(p),
            "age_days":      age_days,
            "last_modified": last_modified,
            "actions": [
                "freeze",
                f"explore:{_build_explore_query(stem)}",
                f"snooze_{BOUNDS.snooze_default_days}d",
            ],
            "created":       now.isoformat(),
            "snoozed_until": None,
            "dismissed":     False,
        })

    return suggestions


def run_scan_and_save() -> list[dict]:
    """Run the full scan, persist results, return active suggestions."""
    suggestions = scan_stale_threads()
    data = _load()

    # Preserve non-dismissed, non-expired snoozed items
    now = datetime.now(timezone.utc)
    kept: list[dict] = []
    for s in data.get("suggestions", []):
        if s.get("dismissed"):
            continue
        snooze_until = s.get("snoozed_until")
        if snooze_until:
            try:
                until = datetime.fromisoformat(snooze_until)
                if until > now:
                    kept.append(s)
                    continue
            except Exception:  # noqa: BLE001
                pass

    # Merge: new suggestions for stems not already tracked
    existing_stems = {s["stem"] for s in kept}
    for sug in suggestions:
        if sug["stem"] not in existing_stems:
            kept.append(sug)

    # Cap
    kept = kept[:BOUNDS.max_proactive_suggestions]

    data["suggestions"] = kept
    data["last_scan"] = now.isoformat()
    _save(data)
    return kept


# ── Actions ───────────────────────────────────────────────────────────────────

def dismiss_suggestion(suggestion_id: str) -> bool:
    """Mark a suggestion as dismissed. Returns True if found."""
    data = _load()
    for s in data.get("suggestions", []):
        if s.get("suggestion_id") == suggestion_id:
            s["dismissed"] = True
            _save(data)
            return True
    return False


def snooze_suggestion(suggestion_id: str, days: int | None = None) -> bool:
    """Snooze a suggestion for `days` days. Returns True if found."""
    days = days or BOUNDS.snooze_default_days
    data = _load()
    now = datetime.now(timezone.utc)
    for s in data.get("suggestions", []):
        if s.get("suggestion_id") == suggestion_id:
            s["snoozed_until"] = (now + timedelta(days=days)).isoformat()
            _save(data)
            return True
    return False


def apply_freeze(suggestion_id: str) -> dict:
    """Freeze the thread referenced by suggestion_id. Returns result."""
    data = _load()
    stem = None
    for s in data.get("suggestions", []):
        if s.get("suggestion_id") == suggestion_id:
            stem = s["stem"]
            s["dismissed"] = True
            break
    if not stem:
        return {"ok": False, "error": "Suggestion not found"}

    try:
        from .library_manager import set_thread_status  # noqa: PLC0415
        set_thread_status(stem, "frozen")
        _save(data)
        return {"ok": True, "stem": stem, "action": "frozen"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def get_active_suggestions() -> list[dict]:
    """Return non-dismissed, non-snoozed suggestions."""
    data = _load()
    now = datetime.now(timezone.utc)
    result = []
    for s in data.get("suggestions", []):
        if s.get("dismissed"):
            continue
        snooze_until = s.get("snoozed_until")
        if snooze_until:
            try:
                if datetime.fromisoformat(snooze_until) > now:
                    continue
            except Exception:  # noqa: BLE001
                pass
        result.append(s)
    return result


def scanner_status() -> dict[str, Any]:
    """Summary for dashboard / briefing."""
    data = _load()
    return {
        "active_suggestions": len(get_active_suggestions()),
        "max_suggestions":    BOUNDS.max_proactive_suggestions,
        "last_scan":          data.get("last_scan"),
        "stale_threshold_days": BOUNDS.stale_thread_age_days,
    }
