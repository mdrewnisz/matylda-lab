"""Matylda Lab — System hooków epistemic (v1.0).

Architektura „nerwowego systemu":
  - Hooki są lekkie i nieblokujące — nie zatrzymują przepływu pracy
  - Jeden hook = jeden wpis w chronicle.jsonl (reguła jednej linii loga)
  - Hooki ANNOTUJĄ, nie OSTRZEGAJĄ — działanie epistemic, nie zdrowotne

Zdefiniowane typy zdarzeń:
    thread.write  → stem: str, path: Path
    pre.compact   → stem: str, path: Path, size_bytes: int
    post.insight  → stem: str, insight_id: str, topic: str

Użycie (dekorator):
    from .hooks import on_event

    @on_event("thread.write")
    def moj_handler(stem: str, path: Path, **_):
        ...

Użycie (programowe):
    from .hooks import register, fire
    register("thread.write", moj_handler)
    fire("thread.write", stem="watek-x", path=Path(...))
"""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)

# ── Typy ─────────────────────────────────────────────────────────────────────

HandlerFn = Callable[..., None]

# ── Registry ─────────────────────────────────────────────────────────────────

_registry: dict[str, list[HandlerFn]] = defaultdict(list)
_registry_lock = threading.Lock()


def on_event(event_type: str) -> Callable[[HandlerFn], HandlerFn]:
    """Dekorator rejestrujący handler dla event_type."""
    def decorator(fn: HandlerFn) -> HandlerFn:
        with _registry_lock:
            _registry[event_type].append(fn)
        return fn
    return decorator


def register(event_type: str, handler: HandlerFn) -> None:
    """Rejestruj handler programowo (bez dekoratora)."""
    with _registry_lock:
        _registry[event_type].append(handler)


def unregister(event_type: str, handler: HandlerFn) -> bool:
    """Wyrejestruj handler. Zwraca True jeśli usunięto."""
    with _registry_lock:
        handlers = _registry.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            return True
    return False


def fire(event_type: str, **payload: Any) -> None:
    """Wywołaj wszystkich handlerów dla event_type.

    Błędy są łapane i logowane — hook nigdy nie blokuje przepływu.
    Każdy handler jest wywołany synchronicznie w wątku wołającym.
    """
    with _registry_lock:
        handlers = list(_registry[event_type])

    if not handlers:
        return

    for handler in handlers:
        try:
            handler(**payload)
        except Exception:  # noqa: BLE001
            log.exception(
                "hook:%s handler %s raised — kontynuuję", event_type, handler.__name__
            )


def list_handlers(event_type: str | None = None) -> dict[str, list[str]]:
    """Zwróć mapę event_type → [nazwy handlerów]. Do diagnostyki."""
    with _registry_lock:
        if event_type:
            return {event_type: [h.__name__ for h in _registry.get(event_type, [])]}
        return {et: [h.__name__ for h in hs] for et, hs in _registry.items()}
