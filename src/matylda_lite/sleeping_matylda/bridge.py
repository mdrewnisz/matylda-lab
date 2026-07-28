"""IPC bridge — Sleeping Matylda ↔ Matylda Lab.

v0.3c: Synthesis działa (Anthropic API). Socket IPC z głównym projektem Matylda — placeholder.

Dwie warstwy:
  1. Synthesis (AKTYWNE) — lokalny reflective synthesis przez Anthropic API.
     Wywołaj: run_synthesis_now() lub POST /api/sleeping/run
  2. Socket IPC (PLACEHOLDER) — komunikacja z zewnętrznym procesem Sleeping Matylda.
     Aktywacja: ENABLED = True po uzgodnieniu protokołu z głównym projektem.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from ..config import ROOT
from .protocol import parse_message, AckMessage, StatusResponseMessage

logger = logging.getLogger("matylda.sleeping_bridge")

# ── Konfiguracja ──────────────────────────────────────────────────────────────

ENABLED = False                                  # TODO: True po implementacji
SOCKET_PATH = Path("/tmp/matylda_lite.sock")
WS_PATH     = "/ws/sleeping"                     # endpoint po migracji na FastAPI
BRIDGE_LOG  = ROOT / "data" / "sleeping" / "bridge.log"


# ── Status ────────────────────────────────────────────────────────────────────

_connected_clients: list = []   # TODO: lista aktywnych połączeń WebSocket/socket


def is_connected() -> bool:
    """Czy Sleeping Matylda jest aktualnie połączona."""
    return ENABLED and len(_connected_clients) > 0


def connection_count() -> int:
    return len(_connected_clients)


def get_status() -> dict:
    from .synthesis import load_last_result
    last = load_last_result()
    return {
        "enabled":         ENABLED,
        "connected":       is_connected(),
        "clients":         connection_count(),
        "socket":          str(SOCKET_PATH),
        "ws_path":         WS_PATH,
        "synthesis_ready": last is not None,
        "last_synthesis":  last.get("timestamp") if last else None,
    }


def run_synthesis_now() -> dict:
    """Uruchom lokalny Sleeping Matylda synthesis synchronicznie.

    Nie wymaga połączenia z zewnętrznym procesem SM.
    Używa Anthropic API + kontekstu z Matylda Lab.

    Returns:
        dict z wynikiem syntezy lub {"error": ...} przy niepowodzeniu.
    """
    try:
        from .sync import build_sync_snapshot
        from .synthesis import run_synthesis
        snapshot = build_sync_snapshot()
        result = run_synthesis(snapshot)
        _log_event("synthesis_run", {
            "threads":   snapshot.get("threads", []).__len__(),
            "tensions":  snapshot.get("active_tensions", []).__len__(),
            "insights":  snapshot.get("insights", []).__len__(),
        })
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error("Sleeping Matylda synthesis błąd: %s", exc)
        return {"error": str(exc)}


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start() -> None:
    """Uruchom bridge przy starcie serwera."""
    if not ENABLED:
        logger.debug("Sleeping Matylda bridge: wyłączony (ENABLED=False)")
        return
    # TODO: Uruchom asyncio server na SOCKET_PATH lub zarejestruj WS endpoint
    BRIDGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Sleeping Matylda bridge: start [PLACEHOLDER]")
    _log_event("bridge_start", {})


def stop() -> None:
    """Zatrzymaj bridge przy shutdown."""
    if not ENABLED:
        return
    # TODO: Zamknij wszystkie połączenia, usuń socket file
    logger.info("Sleeping Matylda bridge: stop [PLACEHOLDER]")
    _log_event("bridge_stop", {})
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink(missing_ok=True)


# ── Obsługa wiadomości ────────────────────────────────────────────────────────

async def handle_message(raw: str | bytes) -> str:
    """Odbierz wiadomość od Sleeping Matylda i zwróć odpowiedź JSON.

    PLACEHOLDER — logika obsługi do zaimplementowania.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        return json.dumps({"type": "error", "detail": f"invalid JSON: {e}"})

    msg = parse_message(data)
    _log_event("received", {"type": data.get("type"), "parsed": msg is not None})

    if msg is None:
        return json.dumps({"type": "error", "detail": "unknown message type"})

    # TODO: Zaimplementuj obsługę każdego typu wiadomości
    # Przykład:
    # if isinstance(msg, WakeMessage):
    #     result = await _handle_wake(msg)
    #     return json.dumps(asdict(AckMessage(ref_type="wake", ok=True, detail=result)))
    #
    # if isinstance(msg, SyncRequestMessage):
    #     response = await _handle_sync(msg)
    #     return json.dumps(asdict(response))

    # Tymczasowa odpowiedź: ack z info że placeholder
    ack = AckMessage(ref_type=data.get("type", ""), ok=False,
                     detail="bridge placeholder — nie zaimplementowany")
    return json.dumps({"type": ack.type, "ref_type": ack.ref_type,
                       "ok": ack.ok, "detail": ack.detail})


# ── Emit do Sleeping Matylda ──────────────────────────────────────────────────

async def emit(message: dict) -> bool:
    """Wyślij wiadomość do wszystkich połączonych klientów Sleeping Matylda.

    PLACEHOLDER — wymaga aktywnych połączeń.
    """
    if not is_connected():
        return False
    # TODO: Wyślij do wszystkich _connected_clients
    _log_event("emit", message)
    return True


# ── Wewnętrzne ────────────────────────────────────────────────────────────────

def _log_event(event: str, data: dict) -> None:
    """Zapisz zdarzenie bridge do logu."""
    try:
        BRIDGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = json.dumps({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            **data
        }, ensure_ascii=False)
        with BRIDGE_LOG.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:  # noqa: BLE001
        pass
