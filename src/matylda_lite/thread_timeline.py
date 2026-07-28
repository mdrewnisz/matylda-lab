"""Thread timeline — log of work events per thread."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path

from .config import ROOT

TIMELINE_DIR = ROOT / "library" / "threads" / "timeline"
TIMELINE_DIR.mkdir(parents=True, exist_ok=True)

_VALID_EVENT_TYPES = frozenset(
    {"conversation", "artifact_created", "insight_saved", "reviewed"}
)
_MAX_EVENTS = 100


def log_event(
    stem: str,
    event_type: str,
    description: str,
    artifact_path: str = "",
) -> None:
    """Append an event to the thread's timeline file."""
    if not stem:
        return
    path = TIMELINE_DIR / f"{stem}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {"events": []}
    else:
        data = {"events": []}

    events: list[dict] = data.get("events", [])
    events.append(
        {
            "type": event_type,
            "description": description,
            "artifact_path": artifact_path,
            "date": str(date.today()),
        }
    )
    # Trim oldest if over limit
    if len(events) > _MAX_EVENTS:
        events = events[-_MAX_EVENTS:]

    data["events"] = events
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_timeline(stem: str) -> list[dict]:
    """Return events for a thread, newest first. Empty list if file missing."""
    if not stem:
        return []
    path = TIMELINE_DIR / f"{stem}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        events = data.get("events", [])
        return list(reversed(events))
    except Exception:  # noqa: BLE001
        return []
