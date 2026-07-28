"""Local, explicit hypothesis lifecycle for Matylda Lab.

The registry is deliberately small: it preserves research possibilities without
turning them into decisions or letting a background worker promote them.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .atomic_state import update_json
from .config import ROOT

REGISTRY_FILE = ROOT / "data" / "hypotheses.json"
FOCUS_WAITING_LIMIT = 7
EXPLORATION_COSTS = ("5 min", "30 min", "half day", "2 days", "experiment", "new capability")

STATES = frozenset({
    "seed", "incubator", "exploration", "working_model", "waiting_room", "cemetery",
})
_ALLOWED_TRANSITIONS = {
    "seed": {"incubator", "cemetery"},
    "incubator": {"exploration", "cemetery"},
    "exploration": {"working_model", "cemetery"},
    "working_model": {"waiting_room", "cemetery"},
    "waiting_room": {"working_model", "cemetery"},
    "cemetery": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _records(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        return []
    return [item for item in data["records"] if isinstance(item, dict)]


def _require(fields: dict[str, Any], names: tuple[str, ...]) -> None:
    missing = [name for name in names if not str(fields.get(name, "")).strip()]
    if missing:
        raise ValueError("Brak wymaganych pól: " + ", ".join(missing))


def _normalise_fields(fields: dict[str, Any] | None, *, default_cost: str | None = None) -> dict[str, Any]:
    if fields is not None and not isinstance(fields, dict):
        raise ValueError("Pola hipotezy muszą być obiektem")
    clean = {key: value for key, value in (fields or {}).items() if isinstance(key, str)}
    if "exploration_cost" in clean:
        cost = str(clean["exploration_cost"]).strip()
        if cost not in EXPLORATION_COSTS:
            raise ValueError("Nieprawidłowy koszt eksploracji")
        clean["exploration_cost"] = cost
    elif default_cost:
        clean["exploration_cost"] = default_cost
    return clean


def create_hypothesis(title: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise ValueError("Tytuł hipotezy jest wymagany")
    fields = _normalise_fields(fields, default_cost="30 min")
    created: dict[str, Any] = {}

    def mutate(data: Any) -> dict[str, Any]:
        nonlocal created
        records = _records(data)
        now = _now()
        created = {
            "id": f"hyp_{uuid4().hex[:10]}",
            "title": title,
            "state": "seed",
            "created_at": now,
            "updated_at": now,
            "parent_id": None,
            **fields,
        }
        records.append(created)
        return {"records": records}

    update_json(REGISTRY_FILE, {"records": []}, mutate)
    return created


def transition_hypothesis(record_id: str, state: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    if state not in STATES:
        raise ValueError("Nieznany stan hipotezy")
    fields = _normalise_fields(fields)
    updated: dict[str, Any] = {}

    def mutate(data: Any) -> dict[str, Any]:
        nonlocal updated
        records = _records(data)
        record = next((item for item in records if item.get("id") == record_id), None)
        if record is None:
            raise KeyError("Nie znaleziono hipotezy")
        previous = str(record.get("state", ""))
        if state not in _ALLOWED_TRANSITIONS.get(previous, set()):
            raise ValueError(f"Nie można przejść z {previous} do {state}")
        candidate = {**record, **fields, "state": state, "updated_at": _now()}
        if state == "waiting_room":
            _require(candidate, ("current_evidence", "missing_test", "reentry_condition", "review_date"))
        if state == "cemetery":
            _require(candidate, ("cemetery_reason", "cemetery_record"))
        record.clear()
        record.update(candidate)
        updated = dict(record)
        return {"records": records}

    update_json(REGISTRY_FILE, {"records": []}, mutate)
    return updated


def revive_hypothesis(record_id: str) -> dict[str, Any]:
    revived: dict[str, Any] = {}

    def mutate(data: Any) -> dict[str, Any]:
        nonlocal revived
        records = _records(data)
        parent = next((item for item in records if item.get("id") == record_id), None)
        if parent is None:
            raise KeyError("Nie znaleziono hipotezy")
        if parent.get("state") != "cemetery":
            raise ValueError("Wskrzeszać można tylko rekord z Kostnicy")
        now = _now()
        revived = {
            key: value for key, value in parent.items()
            if key not in {"id", "state", "created_at", "updated_at", "cemetery_reason", "cemetery_record"}
        }
        revived.update({
            "id": f"hyp_{uuid4().hex[:10]}",
            "title": f"{parent.get('title', 'Hipoteza')} (revival)",
            "state": "working_model",
            "parent_id": record_id,
            "created_at": now,
            "updated_at": now,
        })
        records.append(revived)
        return {"records": records}

    update_json(REGISTRY_FILE, {"records": []}, mutate)
    return revived


def overview() -> dict[str, Any]:
    try:
        raw = json.loads(REGISTRY_FILE.read_text(encoding="utf-8")) if REGISTRY_FILE.exists() else {}
    except (OSError, json.JSONDecodeError):
        raw = {}
    records = sorted(_records(raw), key=lambda item: item.get("updated_at", ""), reverse=True)
    by_state = {state: [item for item in records if item.get("state") == state] for state in STATES}
    waiting = by_state["waiting_room"]
    return {
        "by_state": by_state,
        "focus_waiting": waiting[:FOCUS_WAITING_LIMIT],
        "focus_waiting_limit": FOCUS_WAITING_LIMIT,
        "waiting_overflow": max(0, len(waiting) - FOCUS_WAITING_LIMIT),
        "exploration_costs": EXPLORATION_COSTS,
    }
