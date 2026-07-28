"""Sleeping Matylda v0 — silnik refleksyjnej syntezy dla Matylda Lab.

Zamiast Ollama używa Anthropic API (już skonfigurowanego w Lite).
Wejście:  snapshot kontekstu Lite (notatki, wątki, napięcia, artefakty).
Wyjście:  ustrukturyzowana synteza:
  - day_synthesis          — krótkie podsumowanie stanu projektu
  - open_threads           — wątki wymagające uwagi
  - tensions_or_conflicts  — napięcia epistemiczne i merytoryczne
  - next_questions         — pytania do rozstrzygnięcia
  - proposed_next_steps    — propozycje kroków (tylko propozycje, nie rozkazy)
  - reflection_notes       — obserwacje meta-poziomowe
  - warnings               — ostrzeżenia
  - uncertainty_markers    — nierozstrzygnięte niepewności

Wynik jest zapisywany w ~/.matylda/sleeping_matylda_last.json.
"""
from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from ..config import get_api_key

_LAST_RESULT_FILE = Path.home() / ".matylda" / "sleeping_matylda_last.json"

_SYSTEM_PROMPT = """\
Jesteś Sleeping Matylda v0 — bounded reflective standby surface dla projektu badawczego Matylda Lab.

Twoja rola jest WYŁĄCZNIE refleksyjna i propozycjonalna:
- Syntezujesz stan projektu na podstawie dostarczonego kontekstu.
- Wskazujesz otwarte wątki, napięcia i pytania.
- Proponujesz kolejne kroki — jako propozycje dla operatora, NIE rozkazy do autonomicznego wykonania.
- Nie implikujesz autonomicznego działania, samodzielnych zapisów ani modyfikacji własnych reguł.

Zwróć DOKŁADNIE jeden obiekt JSON zgodny ze schematem wyjściowym.
Nie dodawaj żadnego tekstu poza JSON.
Pola proposed_next_steps formułuj jako "Możliwy kolejny krok: …"
Pola next_questions formułuj jako pytanie kończące się znakiem "?"\
"""


def _build_user_prompt(snapshot: dict) -> str:
    payload: dict = {
        "role": "sleeping_matylda_v0",
        "project_name": "Matylda Lab",
        "silo_hint": snapshot.get("active_project") or "general",
        "active_tensions": snapshot.get("active_tensions", []),
        "open_threads": snapshot.get("threads", []),
        "recent_insights": snapshot.get("insights", []),
        "recent_artifacts": snapshot.get("artifacts", []),
        "darkroom_state": snapshot.get("darkroom_state", {}),
        "required_output_schema": {
            "day_synthesis": "string — 2-4 zdania, stan projektu",
            "open_threads": ["string"],
            "tensions_or_conflicts": ["string"],
            "next_questions": ["string"],
            "proposed_next_steps": ["string"],
            "reflection_notes": ["string"],
            "warnings": ["string"],
            "uncertainty_markers": ["string"],
        },
    }

    # v0.3f: Enrich with chronicle events, research bootstrap and perception context
    chronicle = snapshot.get("chronicle_events", [])
    if chronicle:
        # Include only lightweight summary of last 10 events
        payload["recent_chronicle_events"] = [
            {
                "source": ev.get("source"),
                "event_type": ev.get("event_type"),
                "workflow_kind": ev.get("workflow_kind"),
                "timestamp": (ev.get("timestamp") or "")[:19],
            }
            for ev in chronicle[:10]
        ]

    bootstrap = snapshot.get("research_bootstrap", {})
    if bootstrap.get("continuity_trace_count", 0) > 0:
        payload["research_continuity"] = {
            "trace_count":       bootstrap.get("continuity_trace_count", 0),
            "suggested_next":    bootstrap.get("suggested_next_step", ""),
            "continuity_status": bootstrap.get("continuity_status", ""),
        }

    perception = snapshot.get("perception_summary", "")
    if perception:
        payload["perception_context"] = perception

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_output(raw: dict, warnings: list[str]) -> dict:
    def _strings(key: str) -> list[str]:
        val = raw.get(key, [])
        if isinstance(val, list):
            return [str(v).strip() for v in val if str(v).strip()]
        return []

    def _proposalize(s: str) -> str:
        low = s.lower()
        if low.startswith(("możliwy kolejny krok:", "consider ", "review ")):
            return s
        return f"Możliwy kolejny krok: {s[0].lower() + s[1:] if len(s) > 1 else s.lower()}"

    def _questionize(s: str) -> str:
        s = s.strip()
        if s.lower().startswith("pytanie:"):
            return s
        if not s.endswith("?"):
            return s + "?"
        return s

    synthesis = str(raw.get("day_synthesis") or "").strip()
    return {
        "day_synthesis": synthesis or "Sleeping Matylda v0 nie wygenerowała syntezy.",
        "open_threads":          _strings("open_threads"),
        "tensions_or_conflicts": _strings("tensions_or_conflicts"),
        "next_questions":        [_questionize(q) for q in _strings("next_questions")],
        "proposed_next_steps":   [_proposalize(s) for s in _strings("proposed_next_steps")],
        "reflection_notes":      _strings("reflection_notes"),
        "warnings":              warnings + _strings("warnings"),
        "uncertainty_markers":   _strings("uncertainty_markers"),
    }


def _empty_output(warnings: list[str]) -> dict:
    return {
        "day_synthesis":         "Niewystarczające dane wejściowe dla syntezy refleksyjnej.",
        "open_threads":          [],
        "tensions_or_conflicts": [],
        "next_questions":        [],
        "proposed_next_steps":   [],
        "reflection_notes":      ["Sleeping Matylda v0 nie uruchomiła syntezy z minimalnego wejścia."],
        "warnings":              warnings,
        "uncertainty_markers":   ["insufficient_input"],
    }


def _is_minimal(snapshot: dict) -> bool:
    """Czy kontekst jest zbyt skromny, żeby warto było uruchamiać syntezę."""
    return not any([
        snapshot.get("threads"),
        snapshot.get("insights"),
        snapshot.get("active_tensions"),
        snapshot.get("artifacts"),
    ])


def run_synthesis(snapshot: dict) -> dict:
    """Uruchom Sleeping Matylda v0 z danym snapshotem kontekstu.

    Args:
        snapshot: dict z kluczami: threads, insights, active_tensions, artifacts,
                  active_project, darkroom_state

    Returns:
        dict z polami syntezy (patrz schemat wyjściowy).
    """
    warnings: list[str] = []

    if not snapshot.get("active_project") and not snapshot.get("threads"):
        warnings.append("Brak referencji projektu ani wątków.")

    if _is_minimal(snapshot):
        return _empty_output(warnings + ["Sleeping Matylda v0 otrzymała zbyt mały kontekst."])

    api_key = get_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    from ..models import call_with_model_fallback  # noqa: PLC0415
    try:
        msg = call_with_model_fallback(
            client, "haiku",   # tani model — tylko synteza refleksyjna
            max_tokens=2500,
            temperature=0.2,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(snapshot)}],
        )
    except Exception as exc:  # noqa: BLE001
        return _empty_output(warnings + [f"Sleeping Matylda v0 błąd API: {exc}"])

    raw_text = msg.content[0].text.strip() if msg.content else ""

    # Wytnij JSON z odpowiedzi (model może dodać blok markdown)
    if "```" in raw_text:
        import re
        # Usuń otwierający znacznik ``` lub ```json i zamykający ```
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        raw_text = re.sub(r"\s*```$", "", raw_text.strip())

    # Wytnij pierwszy obiekt JSON jeśli jest tekst przed/po
    if not raw_text.startswith("{"):
        import re
        m = re.search(r"\{", raw_text)
        if m:
            raw_text = raw_text[m.start():]
    if not raw_text.endswith("}"):
        import re
        m = list(re.finditer(r"\}", raw_text))
        if m:
            raw_text = raw_text[:m[-1].end()]

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        return _empty_output(warnings + ["Sleeping Matylda v0 zwróciła nieprawidłowy JSON."])

    if not isinstance(raw, dict):
        return _empty_output(warnings + ["Sleeping Matylda v0 zwróciła nie-obiekt JSON."])

    result = _normalize_output(raw, warnings)
    _save_result(result, snapshot)
    return result


def _save_result(result: dict, snapshot: dict) -> None:
    """Zapisz wynik syntezy do pliku."""
    _LAST_RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "snapshot_summary": {
            "threads_count":   len(snapshot.get("threads", [])),
            "insights_count":  len(snapshot.get("insights", [])),
            "tensions_count":  len(snapshot.get("active_tensions", [])),
            "artifacts_count": len(snapshot.get("artifacts", [])),
            "active_project":  snapshot.get("active_project"),
        },
    }
    _LAST_RESULT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last_result() -> dict | None:
    """Wczytaj ostatni wynik syntezy z pliku. Zwraca None jeśli brak."""
    if not _LAST_RESULT_FILE.exists():
        return None
    try:
        return json.loads(_LAST_RESULT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
