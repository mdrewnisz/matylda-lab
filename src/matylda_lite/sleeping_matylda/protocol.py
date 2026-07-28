"""Protokół IPC między Sleeping Matylda (główny projekt) a Matylda Lab.

Wiadomości JSON over Unix socket lub WebSocket.

PLACEHOLDER — typy i schemat do uzgodnienia przy integracji.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal


# ── Typy wiadomości Sleeping Matylda → Lite ───────────────────────────────────

@dataclass
class WakeMessage:
    """Sleeping Matylda budzi Lite z zadaniem."""
    type: Literal["wake"] = "wake"
    task: str = ""
    context: str = ""          # dodatkowy kontekst z głównego projektu
    thread_stem: str = ""      # opcjonalne: podepnij pod konkretny wątek
    no_go: bool = False


@dataclass
class PushInsightMessage:
    """Sleeping Matylda przesyła ustalenie do pamięci Lite."""
    type: Literal["push_insight"] = "push_insight"
    content: str = ""
    topic: str = ""
    linked_thread: str = ""
    to_candidates: bool = True    # domyślnie do staging, nie do durable memory


@dataclass
class SyncRequestMessage:
    """Sleeping Matylda prosi o aktualny stan workspace."""
    type: Literal["sync_request"] = "sync_request"
    include_threads: bool = True
    include_insights: bool = True
    include_tensions: bool = False


@dataclass
class StatusQueryMessage:
    """Sleeping Matylda sprawdza status Lite."""
    type: Literal["status_query"] = "status_query"


# ── Typy wiadomości Lite → Sleeping Matylda ───────────────────────────────────

@dataclass
class AckMessage:
    """Potwierdzenie odbioru wiadomości."""
    type: Literal["ack"] = "ack"
    ref_type: str = ""            # typ wiadomości której dotyczy ack
    ok: bool = True
    detail: str = ""


@dataclass
class SyncResponseMessage:
    """Odpowiedź na SyncRequest."""
    type: Literal["sync_response"] = "sync_response"
    threads: list[dict] = field(default_factory=list)
    insights: list[dict] = field(default_factory=list)
    active_tensions: list[dict] = field(default_factory=list)
    active_project: dict | None = None


@dataclass
class AlertMessage:
    """Lite powiadamia Sleeping Matylda o zdarzeniu wymagającym uwagi."""
    type: Literal["alert"] = "alert"
    level: Literal["info", "warning", "critical"] = "info"
    message: str = ""
    source: str = ""              # np. "darkroom", "tension", "review"


@dataclass
class StatusResponseMessage:
    """Odpowiedź na StatusQuery."""
    type: Literal["status_response"] = "status_response"
    online: bool = True
    active_threads: int = 0
    pending_approvals: int = 0
    epistemic_limit_active: bool = False


# ── Registry ──────────────────────────────────────────────────────────────────

INBOUND_TYPES = {
    "wake":           WakeMessage,
    "push_insight":   PushInsightMessage,
    "sync_request":   SyncRequestMessage,
    "status_query":   StatusQueryMessage,
}

OUTBOUND_TYPES = {
    "ack":             AckMessage,
    "sync_response":   SyncResponseMessage,
    "alert":           AlertMessage,
    "status_response": StatusResponseMessage,
}


def parse_message(data: dict) -> Any:
    """Parsuj dict JSON na odpowiedni dataclass. Zwróć None jeśli typ nieznany."""
    msg_type = data.get("type", "")
    cls = INBOUND_TYPES.get(msg_type)
    if cls is None:
        return None
    try:
        return cls(**{k: v for k, v in data.items() if k != "type"})
    except TypeError:
        return cls()
