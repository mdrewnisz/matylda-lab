"""Synchronizacja stanu między Sleeping Matylda a Matylda Lab.

build_sync_snapshot()  — zbiera kontekst z Lite (wątki, insighty, napięcia, artefakty)
apply_pushed_insight() — zapisuje insight przesłany przez SM do kandydatów pamięci
apply_wake_task()      — uruchamia zadanie SM przez Secretary
"""
from __future__ import annotations


def build_sync_snapshot() -> dict:
    """Zbuduj snapshot stanu Lite do syntezy przez Sleeping Matylda.

    Zbiera dane z:
      - library_manager  → otwarte wątki (max 10 najnowszych)
      - memory_manager   → insighty z pamięci (max 10)
      - darkroom.tension → aktywne napięcia
      - secretary.status → artefakty i aktywny projekt
    """
    from ..library_manager import list_threads, list_projects
    from ..memory_manager import list_insights
    from ..darkroom.tension import load_active
    from ..secretary import Secretary

    # ── Wątki ────────────────────────────────────────────────────────────────
    try:
        raw_threads = list_threads(include_archived=False)
        threads = [
            {
                "id":    t.get("id", ""),
                "title": t.get("title", t.get("id", "")),
                "status": t.get("status", "active"),
            }
            for t in raw_threads[:10]
        ]
    except Exception:  # noqa: BLE001
        threads = []

    # ── Insighty pamięci ─────────────────────────────────────────────────────
    try:
        raw_insights = list_insights(include_archived=False)
        insights = [
            {
                "id":      i.get("id", ""),
                "content": (i.get("content") or "")[:300],
                "topic":   i.get("topic", ""),
            }
            for i in raw_insights[:10]
            if not i.get("archived")
        ]
    except Exception:  # noqa: BLE001
        insights = []

    # ── Napięcia DARKROOM ────────────────────────────────────────────────────
    try:
        raw_tensions = load_active()
        # Sortuj po severity malejąco, przytnij do 8 najcięższych
        raw_tensions.sort(key=lambda t: -t.get("severity", 0.5))
        active_tensions = [
            {
                "id":          t.get("id", ""),
                "type":        t.get("type", ""),
                "description": (t.get("description") or "")[:150],
                "severity":    t.get("severity", 0.5),
            }
            for t in raw_tensions[:8]
        ]
    except Exception:  # noqa: BLE001
        active_tensions = []

    # ── Status Secretary (artefakty, projekt) ────────────────────────────────
    try:
        sec = Secretary()
        sec_status = sec.status()
        artifacts = [
            {
                "id":    a.get("id", ""),
                "title": a.get("title", ""),
                "type":  a.get("type", ""),
            }
            for a in sec_status.get("artifacts", [])[:8]
        ]
        darkroom_state = {
            "pending_approvals": sec_status.get("pending_approvals", 0),
            "active_tensions":   sec_status.get("active_tensions", 0),
            "no_go":             sec_status.get("no_go", False),
            "elm_active":        sec_status.get("epistemic_limit_mode", {}).get("active", False),
        }
    except Exception:  # noqa: BLE001
        artifacts = []
        darkroom_state = {}

    # ── Aktywny projekt ──────────────────────────────────────────────────────
    try:
        projects = list_projects(include_archived=False)
        active_project = projects[0].get("name") if projects else None
    except Exception:  # noqa: BLE001
        active_project = None

    # ── Chronicle — ostatnie eventy sesji ──────────────────────────────────
    try:
        from ..chronicle import list_events_as_dicts  # noqa: PLC0415
        chronicle_events = list_events_as_dicts(limit=20)
    except Exception:  # noqa: BLE001
        chronicle_events = []

    # ── Research traces — ciągłość sesji badawczych ─────────────────────────
    try:
        from ..research_continuity import build_research_bootstrap_view  # noqa: PLC0415
        _pid = active_project or "lite"
        research_bootstrap = build_research_bootstrap_view(project_id=_pid)
    except Exception:  # noqa: BLE001
        research_bootstrap = {}

    # ── Perception — distilled context ──────────────────────────────────────
    try:
        from ..perception import get_current_session_context  # noqa: PLC0415
        perception_ctx = get_current_session_context(persist=False)
        perception_summary = perception_ctx.as_context_prefix() if perception_ctx else ""
    except Exception:  # noqa: BLE001
        perception_summary = ""

    return {
        "threads":          threads,
        "insights":         insights,
        "active_tensions":  active_tensions,
        "artifacts":        artifacts,
        "darkroom_state":   darkroom_state,
        "active_project":   active_project,
        "chronicle_events": chronicle_events,
        "research_bootstrap": research_bootstrap,
        "perception_summary": perception_summary,
    }


def apply_pushed_insight(content: str, topic: str = "", linked_thread: str = "",
                          to_candidates: bool = True) -> dict:
    """Zapisz insight przesłany przez Sleeping Matylda.

    Args:
        content:       Treść insightu.
        topic:         Temat (opcjonalny).
        linked_thread: Powiązany wątek (opcjonalny).
        to_candidates: True → do staging area kandydatów; False → bezpośrednio do pamięci.

    Returns:
        dict z polami: status, saved, id (opcjonalny).
    """
    try:
        if to_candidates:
            from ..memory_manager import save_candidate
            result = save_candidate(
                content=content,
                topic=topic,
                note="Przesłane przez Sleeping Matylda",
                linked_thread=linked_thread,
            )
            return {"status": "ok", "saved": True, "id": result.get("id"), "target": "candidates"}
        else:
            from ..memory_manager import save_insight
            result = save_insight(content=content, topic=topic, linked_thread=linked_thread)
            return {"status": "ok", "saved": True, "id": result.get("id"), "target": "insights"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "saved": False, "error": str(exc)}


def apply_wake_task(task: str, context: str = "", thread_stem: str = "",
                    no_go: bool = False) -> dict:
    """Uruchom zadanie otrzymane od Sleeping Matylda przez Secretary.

    Args:
        task:        Treść zadania.
        context:     Opcjonalny kontekst z SM.
        thread_stem: Opcjonalny plik wątku do zapisu.
        no_go:       Czy włączyć tryb NO-GO w DARKROOM.

    Returns:
        dict z polami: status, executed, response (jeśli sukces).
    """
    try:
        from ..secretary import Secretary
        sec = Secretary()
        content = f"{context}\n\n---\n\n{task}" if context else task
        messages = [{"role": "user", "content": content}]
        result = sec.chat(messages, save_as=thread_stem or None, no_go=no_go)
        return {"status": "ok", "executed": True, "response": result}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "executed": False, "error": str(exc)}
