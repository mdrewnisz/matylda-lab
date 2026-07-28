"""Matylda Lab — local FastAPI server.

Zastąpienie http.server przez uvicorn + FastAPI.
Wszystkie endpointy zachowane 1:1.

Uruchomienie:
    python run.py              # dev (z auto-restart)
    python run.py --daemon     # background (bez okna przeglądarki)
"""
from __future__ import annotations

import asyncio
import json
import threading
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from .constitutional import BOUNDS as _BOUNDS

PORT = 7474

# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(application: FastAPI):
    """Keep execution workers opt-in for an otherwise local research workspace."""
    if application.state.enable_automation:
        _start_background_services()
    else:
        print("[lab] Usługi wykonawcze wyłączone (uruchom z --automation, aby je włączyć)")
    yield


app = FastAPI(
    title="Matylda Lab",
    version="1.2",
    docs_url=None,
    redoc_url=None,
    lifespan=_lifespan,
)
app.state.enable_automation = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ── Secretary singleton ───────────────────────────────────────────────────────

_secretary = None
_secretary_lock = threading.Lock()


def _get_secretary():
    global _secretary  # noqa: PLW0603
    if _secretary is None:
        with _secretary_lock:
            if _secretary is None:
                from .secretary import Secretary  # noqa: PLC0415
                _secretary = Secretary()
    return _secretary


# ── Async bridge for blocking Secretary calls ─────────────────────────────────

async def _stream_in_thread(
    messages: list[dict],
    save_as: str | None = None,
    no_go: bool = False,
) -> AsyncGenerator[str, None]:
    """Run synchronous stream_chat() in a thread pool; bridge events to async via queue.

    Without this, stream_chat() blocks the uvicorn event loop and every
    concurrent request (including /api/health) times out during streaming.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    secretary = _get_secretary()

    def _producer() -> None:
        try:
            for event in secretary.stream_chat(messages, save_as=save_as, no_go=no_go):
                loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "error", "error": str(exc)}
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

    loop.run_in_executor(None, _producer)

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    from .dashboard import build  # noqa: PLC0415
    return HTMLResponse(content=build(server_mode=True))


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    return _get_secretary().status()


# ── Chat (SSE streaming) ──────────────────────────────────────────────────────

@app.post("/api/chat")
async def api_chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    save_as  = (body.get("save_as") or "").strip() or None
    no_go    = bool(body.get("no_go", False))

    if not messages or not any(m.get("role") == "user" for m in messages):
        return Response(
            content=json.dumps({"error": "messages muszą zawierać wiadomość użytkownika."}),
            status_code=400, media_type="application/json",
        )

    return StreamingResponse(
        _stream_in_thread(messages, save_as=save_as, no_go=no_go),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/task")
async def api_task(request: Request):
    """Backward compat: wrap single task as streaming chat."""
    body = await request.json()
    task = body.get("task", "")
    save_as = body.get("save_as", "")
    return await api_chat(Request(request.scope, request.receive))  # delegate


# ── Fetch URL ─────────────────────────────────────────────────────────────────

@app.post("/api/fetch")
async def api_fetch(request: Request):
    body = await request.json()
    url = (body.get("url") or "").strip()
    if not url:
        return _err("url wymagany")
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: _get_secretary().fetch(url))
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── DARKROOM ──────────────────────────────────────────────────────────────────

@app.get("/api/darkroom")
async def api_darkroom():
    from .darkroom.pipeline import darkroom_status  # noqa: PLC0415
    return darkroom_status()


@app.get("/api/darkroom/history")
async def api_darkroom_history():
    from .darkroom.context import load_recent_history  # noqa: PLC0415
    return {"history": load_recent_history(n=20)}


@app.get("/api/darkroom/reviews")
async def api_darkroom_reviews():
    from .darkroom.pipeline import _REVIEW_LOGS_DIR  # noqa: PLC0415
    logs = sorted(_REVIEW_LOGS_DIR.glob("*.json"))
    reviews = []
    for p in logs[-20:]:
        try:
            reviews.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return {"reviews": reviews}


@app.get("/api/darkroom/failure-trend")
async def api_failure_trend():
    from .darkroom.context import load_failure_trend  # noqa: PLC0415
    return {"trend": load_failure_trend(days=30)}


@app.get("/api/darkroom/disposition-history")
async def api_disposition_history():
    from .darkroom.disposition import load_disposition_history  # noqa: PLC0415
    return {"history": load_disposition_history()}


@app.get("/api/darkroom/epistemic-report")
async def api_epistemic_report():
    from .darkroom.meta_evaluator import load_latest_report  # noqa: PLC0415
    return {"report": load_latest_report()}


@app.post("/api/darkroom/approve")
async def api_approve(request: Request):
    body = await request.json()
    aid = (body.get("approval_id") or "").strip()
    if not aid:
        return _err("approval_id wymagany")
    try:
        from .darkroom.pipeline import approve  # noqa: PLC0415
        return {"ok": True, "updated_profile": approve(aid)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/darkroom/reject")
async def api_reject(request: Request):
    body = await request.json()
    aid = (body.get("approval_id") or "").strip()
    if not aid:
        return _err("approval_id wymagany")
    try:
        from .darkroom.pipeline import reject  # noqa: PLC0415
        reject(aid)
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/darkroom/tension/archive")
async def api_tension_archive(request: Request):
    body = await request.json()
    tid  = (body.get("tension_id") or "").strip()
    note = (body.get("note") or "").strip()
    if not tid:
        return _err("tension_id wymagany")
    try:
        from .darkroom.tension import archive  # noqa: PLC0415
        return {"ok": archive(tid, resolution_note=note)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/darkroom/tension/triage")
async def api_tension_triage():
    """Conservative dedup + test-pollution cleanup of active tensions.

    Does NOT resolve genuine distinct tensions (they are first-class artifacts).
    """
    try:
        from .darkroom.tension import triage_tensions  # noqa: PLC0415
        return {"ok": True, **triage_tensions()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/darkroom/tension/create")
async def api_tension_create(request: Request):
    body = await request.json()
    desc = (body.get("description") or "").strip()
    if not desc:
        return _err("description wymagany")
    try:
        from .darkroom.tension import create  # noqa: PLC0415
        t = create(
            description=desc,
            tension_type=body.get("type", "unresolved_critique"),
            severity=float(body.get("severity", 0.5)),
            source_task=body.get("source_task", ""),
        )
        return {"ok": True, "tension": t}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/darkroom/validate")
async def api_darkroom_validate(request: Request):
    """Validate a research claim using opus as independent epistemic reviewer."""
    body = await request.json()
    claim = (body.get("claim") or "").strip()
    if not claim:
        return _err("claim required")
    sources = body.get("sources") or []
    if not isinstance(sources, list):
        sources = [str(sources)]
    try:
        from .darkroom.pipeline import validate_finding  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: validate_finding(claim, sources, _get_secretary().client)
        )
        return {"ok": True, "validation": result}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/darkroom/generate-report")
async def api_generate_report():
    try:
        from .darkroom.meta_evaluator import generate_epistemic_report  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None, lambda: generate_epistemic_report(_get_secretary().client)
        )
        return {"ok": True, "report": report}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Library — Threads ─────────────────────────────────────────────────────────

# ── Lab — explicit hypothesis lifecycle ───────────────────────────────────────

@app.get("/api/hypotheses")
async def api_hypotheses():
    from .hypothesis_manager import overview  # noqa: PLC0415
    return overview()


@app.post("/api/hypotheses")
async def api_hypothesis_create(request: Request):
    body = await request.json()
    try:
        from .hypothesis_manager import create_hypothesis  # noqa: PLC0415
        record = create_hypothesis(str(body.get("title", "")), body.get("fields"))
        return {"ok": True, "hypothesis": record}
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/hypotheses/{record_id}/transition")
async def api_hypothesis_transition(record_id: str, request: Request):
    body = await request.json()
    try:
        from .hypothesis_manager import transition_hypothesis  # noqa: PLC0415
        record = transition_hypothesis(record_id, str(body.get("state", "")), body.get("fields"))
        return {"ok": True, "hypothesis": record}
    except KeyError as exc:
        return _err(str(exc), 404)
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/hypotheses/{record_id}/revive")
async def api_hypothesis_revive(record_id: str):
    try:
        from .hypothesis_manager import revive_hypothesis  # noqa: PLC0415
        return {"ok": True, "hypothesis": revive_hypothesis(record_id)}
    except KeyError as exc:
        return _err(str(exc), 404)
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)

@app.get("/api/library/threads")
async def api_list_threads():
    from .library_manager import list_threads, list_projects  # noqa: PLC0415
    return {"threads": list_threads(), "projects": list_projects()}


@app.get("/api/library/threads/content")
async def api_thread_content(stem: str = Query("")):
    if not stem:
        return _err("stem wymagany")
    try:
        from .library_manager import read_thread  # noqa: PLC0415
        return {"content": read_thread(stem)}
    except FileNotFoundError:
        return _err("thread not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/library/threads/timeline")
async def api_thread_timeline(stem: str = Query("")):
    from .thread_timeline import get_timeline  # noqa: PLC0415
    return {"timeline": get_timeline(stem)}


@app.post("/api/library/threads/archive")
async def api_thread_archive(request: Request):
    body = await request.json()
    fn = (body.get("filename") or "").strip()
    if not fn:
        return _err("filename wymagany")
    try:
        from .library_manager import archive_thread  # noqa: PLC0415
        return {"ok": archive_thread(fn)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/threads/restore")
async def api_thread_restore(request: Request):
    body = await request.json()
    fn = (body.get("filename") or "").strip()
    if not fn:
        return _err("filename wymagany")
    try:
        from .library_manager import restore_thread  # noqa: PLC0415
        return {"ok": restore_thread(fn)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Library — Projects ────────────────────────────────────────────────────────

@app.get("/api/library/projects")
async def api_list_projects():
    from .library_manager import list_projects  # noqa: PLC0415
    return {"projects": list_projects()}


@app.post("/api/library/projects")
async def api_project_create(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        return _err("name wymagany")
    try:
        from .library_manager import create_project  # noqa: PLC0415
        p = create_project(name, body.get("description", ""), body.get("threads", []))
        return {"ok": True, "project": p}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/projects/archive")
async def api_project_archive(request: Request):
    body = await request.json()
    pid = (body.get("project_id") or "").strip()
    if not pid:
        return _err("project_id wymagany")
    try:
        from .library_manager import archive_project  # noqa: PLC0415
        return {"ok": archive_project(pid)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/projects/restore")
async def api_project_restore(request: Request):
    body = await request.json()
    pid = (body.get("project_id") or "").strip()
    if not pid:
        return _err("project_id wymagany")
    try:
        from .library_manager import restore_project  # noqa: PLC0415
        return {"ok": restore_project(pid)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/projects/add-thread")
async def api_project_add_thread(request: Request):
    body = await request.json()
    try:
        from .library_manager import add_thread_to_project  # noqa: PLC0415
        ok = add_thread_to_project(body.get("project_id", ""), body.get("thread_stem", ""))
        return {"ok": ok}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/projects/remove-thread")
async def api_project_remove_thread(request: Request):
    body = await request.json()
    try:
        from .library_manager import remove_thread_from_project  # noqa: PLC0415
        ok = remove_thread_from_project(body.get("project_id", ""), body.get("thread_stem", ""))
        return {"ok": ok}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/library/projects/active")
async def api_get_active_project():
    from .project_context import get_active_project  # noqa: PLC0415
    return {"project": get_active_project()}


@app.post("/api/library/projects/activate")
async def api_activate_project(request: Request):
    body = await request.json()
    pid = (body.get("project_id") or "").strip()
    if not pid:
        return _err("project_id wymagany")
    try:
        from .project_context import set_active_project  # noqa: PLC0415
        from .library_manager import list_projects  # noqa: PLC0415
        projects = list_projects()
        proj = next((p for p in projects if p.get("id") == pid), None)
        if not proj:
            return _err("project not found", 404)
        set_active_project(pid)
        return {"ok": True, "project": proj}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/projects/deactivate")
async def api_deactivate_project():
    from .project_context import clear_active_project  # noqa: PLC0415
    clear_active_project()
    return {"ok": True}


@app.get("/api/library/projects/{project_id}/summary")
async def api_project_summary(project_id: str):
    """Per-project stats: trace count, notebook count, last activity."""
    try:
        from .research_continuity import load_research_traces  # noqa: PLC0415
        from .silos.silo_1 import _load_nb_index as _s1_nbs  # noqa: PLC0415
        from .silos.silo_2 import _load_nb_index as _s2_nbs  # noqa: PLC0415
        traces = load_research_traces(project_id=project_id)
        s1 = [n for n in _s1_nbs() if n.get("project_id") == project_id]
        s2 = [n for n in _s2_nbs() if n.get("project_id") == project_id]
        last = traces[0] if traces else None
        return {
            "project_id":        project_id,
            "trace_count":       len(traces),
            "notebook_count":    len(s1) + len(s2),
            "last_activity":     last.recorded_at if last else None,
            "last_trace_title":  last.title if last else None,
        }
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Library — Docs ────────────────────────────────────────────────────────────

@app.get("/api/library/docs")
async def api_list_docs():
    from . import docs_manager  # noqa: PLC0415
    return {"docs": docs_manager.list_docs()}


@app.get("/api/library/docs/content")
async def api_doc_content(path_rel: str = Query("")):
    if not path_rel:
        return _err("path_rel wymagany")
    try:
        from . import docs_manager  # noqa: PLC0415
        return {"content": docs_manager.read_doc_content(path_rel)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/docs/upload")
async def api_doc_upload(request: Request):
    import base64  # noqa: PLC0415
    body = await request.json()
    filename    = (body.get("filename") or "").strip()
    content_b64 = (body.get("content_b64") or "").strip()
    if not filename or not content_b64:
        return _err("filename i content_b64 wymagane")
    try:
        raw_bytes = base64.b64decode(content_b64)
        from . import docs_manager  # noqa: PLC0415
        doc = docs_manager.save_uploaded(filename, raw_bytes)
        return {"ok": True, "doc": doc}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/docs/save")
async def api_doc_save(request: Request):
    body = await request.json()
    name    = (body.get("name") or "").strip()
    content = body.get("content", "")
    source  = (body.get("source") or "generated").strip()
    if not name:
        return _err("name wymagany")
    try:
        from . import docs_manager  # noqa: PLC0415
        doc = docs_manager.save_doc(name, content, source)
        return {"ok": True, "doc": doc}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/docs/archive")
async def api_doc_archive(request: Request):
    body = await request.json()
    path_rel = (body.get("path_rel") or "").strip()
    if not path_rel:
        return _err("path_rel wymagany")
    try:
        from . import docs_manager  # noqa: PLC0415
        return {"ok": docs_manager.archive_doc(path_rel)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Library — PDF/file → auto-thread (v0.6.2) ────────────────────────────────

@app.post("/api/library/docs/upload-to-thread")
async def api_doc_upload_to_thread(request: Request):
    """Upload a file, extract text, create a new library thread from it."""
    import base64  # noqa: PLC0415
    body = await request.json()
    filename    = (body.get("filename") or "").strip()
    content_b64 = (body.get("content_b64") or "").strip()
    if not filename or not content_b64:
        return _err("filename i content_b64 wymagane")
    try:
        raw_bytes = base64.b64decode(content_b64)
        from . import docs_manager  # noqa: PLC0415
        from .config import ROOT  # noqa: PLC0415

        # 1. Save to attached dir
        doc = docs_manager.save_uploaded(filename, raw_bytes)
        extracted = doc.get("extracted_text", "")
        if not extracted or extracted.startswith("["):
            return _err(f"Nie udało się wyekstrahować tekstu z {filename}")

        # 2. Build thread name from filename (drop extension)
        from pathlib import Path as _P  # noqa: PLC0415
        stem = _P(filename).stem.replace("_", " ").replace("-", " ").title()
        title = body.get("title") or stem

        # 3. Create thread .md file
        from datetime import date as _date  # noqa: PLC0415
        threads_dir = ROOT / "library" / "threads"
        threads_dir.mkdir(parents=True, exist_ok=True)

        safe_stem = stem.lower().replace(" ", "_")[:60]
        thread_file = threads_dir / f"{safe_stem}.md"
        counter = 1
        while thread_file.exists():
            thread_file = threads_dir / f"{safe_stem}_{counter}.md"
            counter += 1

        domain = body.get("domain", "imported / document")
        thread_content = f"""# {title}

## Metadata
- Domain: {domain}
- Value: reference
- Status: library
- Last updated: {_date.today().isoformat()}
- Source: {filename}
- Type: imported document

---

## Treść dokumentu

{extracted[:25000]}
"""
        thread_file.write_text(thread_content, encoding="utf-8")

        return {
            "ok": True,
            "thread_stem": thread_file.stem,
            "thread_title": title,
            "doc": doc,
            "chars_extracted": len(extracted),
        }
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Library — Thread create (v0.6.3) ─────────────────────────────────────────

@app.post("/api/library/threads/create")
async def api_thread_create(request: Request):
    """Create a new empty thread from the UI (Cmd+N shortcut)."""
    body = await request.json()
    title = (body.get("title") or "").strip()
    if not title:
        return _err("title wymagany")
    from .config import ROOT  # noqa: PLC0415
    from datetime import date as _date  # noqa: PLC0415

    threads_dir = ROOT / "library" / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)

    # Build stem from title
    import re as _re  # noqa: PLC0415
    stem = body.get("stem") or _re.sub(r"[^a-z0-9ąćęłńóśźż]+", "_", title.lower()).strip("_")[:60]
    thread_file = threads_dir / f"{stem}.md"
    counter = 1
    while thread_file.exists():
        thread_file = threads_dir / f"{stem}_{counter}.md"
        counter += 1

    content = body.get("content") or f"""# {title}

## Metadata
- Domain: —
- Value: —
- Status: active
- Last updated: {_date.today().isoformat()}

---

## Notatki

"""
    thread_file.write_text(content, encoding="utf-8")
    return {"ok": True, "stem": thread_file.stem, "title": title}


# ── v1.0 — Thread append + status ─────────────────────────────────────────────

@app.post("/api/library/threads/{stem}/append")
async def api_thread_append(stem: str, request: Request):
    """Append a new section to an existing thread file.

    Body: { "section_title": str, "content": str }
    Returns: { "ok": True, "section_added": str, "updated_at": str }
    """
    body = await request.json()
    content = (body.get("content") or "").strip()
    section_title = (body.get("section_title") or "Wynik AI").strip()
    if not content:
        return _err("content jest wymagany")
    try:
        from .library_manager import append_to_thread  # noqa: PLC0415
        result = append_to_thread(stem, section_title, content)
        return result
    except FileNotFoundError:
        return _err(f"Wątek '{stem}' nie istnieje", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/library/threads/{stem}/set-status")
async def api_thread_set_status(stem: str, request: Request):
    """Change the Status field in a thread's Metadata section.

    Body: { "status": "active" | "frozen" | "library" | "canonical" }
    Returns: { "ok": True, "stem": str, "status": str }
    """
    body = await request.json()
    status = (body.get("status") or "").strip()
    if not status:
        return _err("status jest wymagany")
    try:
        from .library_manager import set_thread_status  # noqa: PLC0415
        ok = set_thread_status(stem, status)
        if not ok:
            return _err(f"Wątek '{stem}' nie istnieje", 404)
        return {"ok": True, "stem": stem, "status": status}
    except ValueError as e:
        return _err(str(e))
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Library — Thread links ────────────────────────────────────────────────────

def _thread_links_file():
    from .config import ROOT  # noqa: PLC0415
    f = ROOT / "library" / "thread_links.json"
    if not f.exists():
        f.write_text("{}", encoding="utf-8")
    return f

def _load_thread_links() -> dict:
    try:
        return json.loads(_thread_links_file().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}

def _save_thread_links(data: dict) -> None:
    _thread_links_file().write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

@app.get("/api/library/thread-links")
async def api_thread_links_get(stem: str = Query("")):
    data = _load_thread_links()
    if stem:
        return {"links": data.get(stem, [])}
    return {"links": data}

@app.post("/api/library/thread-links")
async def api_thread_links_add(request: Request):
    body = await request.json()
    stem  = (body.get("stem") or "").strip()
    url   = (body.get("url") or "").strip()
    title = (body.get("title") or url).strip()
    if not stem or not url:
        return _err("stem i url wymagane")
    from datetime import datetime, timezone  # noqa: PLC0415
    data = _load_thread_links()
    data.setdefault(stem, [])
    if not any(l["url"] == url for l in data[stem]):
        data[stem].append({"url": url, "title": title,
                           "added": datetime.now(timezone.utc).isoformat()[:10]})
    _save_thread_links(data)
    return {"ok": True, "links": data[stem]}

@app.delete("/api/library/thread-links")
async def api_thread_links_delete(request: Request):
    body = await request.json()
    stem = (body.get("stem") or "").strip()
    url  = (body.get("url") or "").strip()
    if not stem or not url:
        return _err("stem i url wymagane")
    data = _load_thread_links()
    if stem in data:
        data[stem] = [l for l in data[stem] if l["url"] != url]
    _save_thread_links(data)
    return {"ok": True}


# ── Memory ────────────────────────────────────────────────────────────────────

@app.get("/api/memory")
async def api_list_insights(kind: str = Query("")):
    from .memory_manager import list_insights  # noqa: PLC0415
    return {"insights": list_insights(kind_filter=kind)}


@app.get("/api/memory/kinds")
async def api_memory_kinds():
    from .memory_manager import MemoryKind, MEMORY_KIND_LABELS, MEMORY_KIND_COLORS  # noqa: PLC0415
    return {
        "kinds": [
            {"value": k.value, "label": MEMORY_KIND_LABELS.get(k.value, k.value), "color": MEMORY_KIND_COLORS.get(k.value, "")}
            for k in MemoryKind
        ]
    }


@app.post("/api/memory/save")
async def api_save_insight(request: Request):
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content:
        return _err("content wymagany")
    try:
        from .memory_manager import save_insight  # noqa: PLC0415
        insight = save_insight(
            content,
            body.get("topic", ""),
            body.get("linked_thread", ""),
            body.get("linked_project", ""),
            kind=body.get("kind", ""),
        )
        return {"ok": True, "insight": insight}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/memory/archive")
async def api_archive_insight(request: Request):
    body = await request.json()
    iid = (body.get("insight_id") or "").strip()
    if not iid:
        return _err("insight_id wymagany")
    try:
        from .memory_manager import archive_insight  # noqa: PLC0415
        return {"ok": archive_insight(iid)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/candidates")
async def api_list_candidates(kind: str = Query("")):
    from .memory_manager import list_candidates  # noqa: PLC0415
    return {"candidates": list_candidates(kind_filter=kind)}


@app.post("/api/memory/candidates/save")
async def api_save_candidate(request: Request):
    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content:
        return _err("content wymagany")
    try:
        from .memory_manager import save_candidate  # noqa: PLC0415
        c = save_candidate(
            content,
            body.get("topic", ""),
            body.get("note", ""),
            body.get("linked_thread", ""),
            kind=body.get("kind", ""),
            confidence=float(body.get("confidence", 0.5)),
            usefulness=float(body.get("usefulness", 0.5)),
            risk=float(body.get("risk", 0.2)),
            stability=float(body.get("stability", 0.5)),
        )
        return {"ok": True, "candidate": c}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/candidates/{candidate_id}/score")
async def api_score_candidate(candidate_id: str):
    """Return auto-score and promotion recommendation for a candidate."""
    try:
        from .memory_manager import score_candidate  # noqa: PLC0415
        result = score_candidate(candidate_id)
        if result is None:
            return _err("candidate not found", 404)
        return result
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/memory/candidates/promote")
async def api_promote_candidate(request: Request):
    body = await request.json()
    cid = (body.get("candidate_id") or "").strip()
    if not cid:
        return _err("candidate_id wymagany")
    try:
        from .memory_manager import promote_candidate  # noqa: PLC0415
        insight = promote_candidate(cid)
        if insight:
            return {
                "ok": True,
                "insight": insight,
                "auto_score": insight.get("auto_score"),
                "recommendation_at_promotion": insight.get("recommendation_at_promotion"),
            }
        return _err("candidate not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/memory/candidates/discard")
async def api_discard_candidate(request: Request):
    body = await request.json()
    cid = (body.get("candidate_id") or "").strip()
    if not cid:
        return _err("candidate_id wymagany")
    try:
        from .memory_manager import discard_candidate  # noqa: PLC0415
        return {"ok": discard_candidate(cid)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Diary / v0.4 memory ──────────────────────────────────────────────────────

@app.post("/api/memory/diary")
async def api_diary_write(request: Request):
    """Append a diary entry. Called at session end or after significant exchange.

    Body (JSON):
      session_id:      str  (required)
      thread_stem:     str | null
      query_summary:   str  (required)
      key_finding:     str | null
      open_questions:  list[str]
      contradicts:     list[str]   — insight/rule ids this entry questions
      model_used:      str | null
      tags:            list[str]
    """
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON body", 400)

    session_id    = (body.get("session_id") or "").strip()
    query_summary = (body.get("query_summary") or "").strip()
    if not session_id:
        return _err("session_id wymagany")
    if not query_summary:
        return _err("query_summary wymagany")

    try:
        from .diary_manager import write_diary_entry  # noqa: PLC0415
        entry_id = write_diary_entry(
            session_id     = session_id,
            thread_stem    = body.get("thread_stem"),
            query_summary  = query_summary,
            key_finding    = body.get("key_finding"),
            open_questions = body.get("open_questions") or [],
            contradicts    = body.get("contradicts") or [],
            model_used     = body.get("model_used"),
            tags           = body.get("tags") or [],
        )
        return {"ok": True, "entry_id": entry_id}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/diary")
async def api_diary_list(days: int = Query(30, ge=1, le=365)):
    """Return diary entries from the last `days` days, newest first."""
    try:
        from .diary_manager import list_diary_entries  # noqa: PLC0415
        return {"entries": list_diary_entries(days=days)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/diary/stats")
async def api_diary_stats():
    """Return diary statistics for the dashboard."""
    try:
        from .diary_manager import diary_stats  # noqa: PLC0415
        return diary_stats()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/reflect")
async def api_reflections_list(days: int = Query(90, ge=1, le=365)):
    """Return reflections from the last `days` days, newest first."""
    try:
        from .diary_manager import list_reflections  # noqa: PLC0415
        return {"reflections": list_reflections(days=days)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/reflect/injectable")
async def api_reflections_injectable():
    """Return only reflections that pass injection criteria (confidence ≥ 0.6, occurrences ≥ 3)."""
    try:
        from .diary_manager import get_injectable_reflections  # noqa: PLC0415
        return {"reflections": get_injectable_reflections()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/memory/reflect")
async def api_reflection_save(request: Request):
    """Persist a reflection. Body should match the ReflectionPattern schema in diary_manager."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON body", 400)
    try:
        from .diary_manager import save_reflection  # noqa: PLC0415
        reflection_id = save_reflection(body)
        return {"ok": True, "reflection_id": reflection_id}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/rules")
async def api_rules():
    """Return the active procedural rules content (injectable into system prompt)."""
    try:
        from .diary_manager import load_rules_for_injection  # noqa: PLC0415
        content = load_rules_for_injection()
        return {"rules": content, "has_rules": bool(content)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/memory/negative")
async def api_negative_summary():
    """Return excerpts from negative memory files (failed assumptions, no-go, hallucinations)."""
    try:
        from .diary_manager import load_negative_summary  # noqa: PLC0415
        return {"negative": load_negative_summary()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Homeostasis / v0.4.5 ─────────────────────────────────────────────────────

@app.get("/api/homeostasis")
async def api_homeostasis_status():
    """Full homeostasis snapshot: goals, attention, fatigue, stale items."""
    try:
        from .homeostasis import homeostasis_status  # noqa: PLC0415
        return homeostasis_status()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/homeostasis/goals")
async def api_goals_list():
    """List active goals."""
    try:
        from .homeostasis import goals_status  # noqa: PLC0415
        return goals_status()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/goals")
async def api_goal_add(request: Request):
    """Add a new active goal. Fails if at BOUNDS.max_open_goals capacity.

    Body: {title: str, description?: str, tags?: list[str]}
    """
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    title = (body.get("title") or "").strip()
    if not title:
        return _err("title wymagany")
    try:
        from .homeostasis import add_goal  # noqa: PLC0415
        goal = add_goal(
            title=title,
            description=body.get("description", ""),
            tags=body.get("tags") or [],
        )
        return {"ok": True, "goal": goal}
    except ValueError as e:
        return _err(str(e), 409)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/goals/close")
async def api_goal_close(request: Request):
    """Close a goal. Body: {goal_id: str, resolution?: str}"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    goal_id = (body.get("goal_id") or "").strip()
    if not goal_id:
        return _err("goal_id wymagany")
    try:
        from .homeostasis import close_goal  # noqa: PLC0415
        ok = close_goal(goal_id, resolution=body.get("resolution", ""))
        return {"ok": ok}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/homeostasis/attention")
async def api_attention_status():
    """Return current session attention budget state."""
    try:
        from .homeostasis import attention_status  # noqa: PLC0415
        return attention_status()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/attention/consume")
async def api_attention_consume(request: Request):
    """Register one attention unit for a topic. Body: {topic: str}"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    topic = (body.get("topic") or "").strip()
    if not topic:
        return _err("topic wymagany")
    try:
        from .homeostasis import consume_attention  # noqa: PLC0415
        return consume_attention(topic)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/homeostasis/fatigue")
async def api_fatigue_status():
    """Return current fatigue level and recommendation."""
    try:
        from .homeostasis import fatigue_status  # noqa: PLC0415
        return fatigue_status()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/homeostasis/stale")
async def api_stale_items():
    """Return attention items that have exceeded the stale age threshold."""
    try:
        from .homeostasis import get_stale_items  # noqa: PLC0415
        return {"stale_items": get_stale_items()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/stale/resolve")
async def api_stale_resolve(request: Request):
    """Resolve an attention item. Body: {item_id: str}"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    item_id = (body.get("item_id") or "").strip()
    if not item_id:
        return _err("item_id wymagany")
    try:
        from .homeostasis import resolve_attention_item  # noqa: PLC0415
        return {"ok": resolve_attention_item(item_id)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/constitutional")
async def api_constitutional():
    """Return the current AutonomyBounds values (read-only snapshot)."""
    from dataclasses import asdict  # noqa: PLC0415
    from .constitutional import BOUNDS, CONSTITUTIONAL_VERSION  # noqa: PLC0415
    return {
        "version": CONSTITUTIONAL_VERSION,
        "bounds":  asdict(BOUNDS),
    }


# ── Stale thread suggestions / v0.5 ──────────────────────────────────────────

@app.get("/api/homeostasis/suggestions")
async def api_suggestions_list():
    """Return active stale-thread suggestions (not dismissed, not snoozed)."""
    try:
        from .stale_scanner import get_active_suggestions, scanner_status  # noqa: PLC0415
        return {
            "suggestions": get_active_suggestions(),
            "status":      scanner_status(),
        }
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/suggestions/scan")
async def api_suggestions_scan():
    """Manually trigger a stale-thread scan (ignores interval guard)."""
    try:
        from .stale_scanner import run_scan_and_save  # noqa: PLC0415
        suggestions = run_scan_and_save()
        return {"ok": True, "suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/suggestions/dismiss")
async def api_suggestion_dismiss(request: Request):
    """Dismiss a suggestion. Body: {suggestion_id: str}"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    sid = (body.get("suggestion_id") or "").strip()
    if not sid:
        return _err("suggestion_id wymagany")
    try:
        from .stale_scanner import dismiss_suggestion  # noqa: PLC0415
        return {"ok": dismiss_suggestion(sid)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/suggestions/snooze")
async def api_suggestion_snooze(request: Request):
    """Snooze a suggestion. Body: {suggestion_id: str, days?: int}"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    sid = (body.get("suggestion_id") or "").strip()
    if not sid:
        return _err("suggestion_id wymagany")
    try:
        from .stale_scanner import snooze_suggestion  # noqa: PLC0415
        ok = snooze_suggestion(sid, days=body.get("days"))
        return {"ok": ok}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/homeostasis/suggestions/freeze")
async def api_suggestion_freeze(request: Request):
    """Freeze the thread referenced by a suggestion. Body: {suggestion_id: str}"""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    sid = (body.get("suggestion_id") or "").strip()
    if not sid:
        return _err("suggestion_id wymagany")
    try:
        from .stale_scanner import apply_freeze  # noqa: PLC0415
        return apply_freeze(sid)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Task Queue / v0.6 ────────────────────────────────────────────────────────

@app.get("/api/tasks")
async def api_tasks_list(state: str | None = Query(None)):
    """List tasks, optionally filtered by state.

    States: queued | awaiting_approval | approved | running | done | failed | rejected | interrupted
    """
    try:
        from .task_queue import load_tasks  # noqa: PLC0415
        tasks = load_tasks()
        result = list(tasks.values())
        if state:
            result = [t for t in result if t.get("state") == state]
        result.sort(key=lambda t: t.get("created", ""), reverse=True)
        return {"tasks": result, "total": len(result)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/tasks/stats")
async def api_tasks_stats():
    """Queue statistics: counts by state, worker status, pending approvals."""
    try:
        from .task_queue import queue_stats  # noqa: PLC0415
        return queue_stats()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/tasks/{task_id}")
async def api_task_get(task_id: str):
    """Get a single task by ID."""
    try:
        from .task_queue import load_task  # noqa: PLC0415
        task = load_task(task_id)
        if not task:
            return _err(f"Task not found: {task_id}", 404)
        return task
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/tasks")
async def api_tasks_enqueue(request: Request):
    """Enqueue a new task.

    Body:
      intent:            str  (required) — what Matylda intends to do
      payload:           str  (required) — the actual instruction/prompt
      estimated_tokens:  int  (default 500)
      approval_required: bool (default false — auto-set if tokens > threshold)
      created_by:        str  (default "user")
      priority:          int  1-5 (default 3)
      tags:              list[str]

    Returns task with state: "queued" or "awaiting_approval".
    """
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)

    intent  = (body.get("intent") or "").strip()
    payload = (body.get("payload") or "").strip()
    if not intent:
        return _err("intent wymagany")
    if not payload:
        return _err("payload wymagany")

    try:
        from .task_queue import enqueue  # noqa: PLC0415
        task = enqueue(
            intent           = intent,
            payload          = payload,
            estimated_tokens = int(body.get("estimated_tokens", 500)),
            approval_required = bool(body.get("approval_required", False)),
            created_by       = body.get("created_by", "user"),
            priority         = int(body.get("priority", 3)),
            tags             = body.get("tags") or [],
        )
        return {"ok": True, "task": task}
    except ValueError as e:
        return _err(str(e), 400)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/tasks/{task_id}/approve")
async def api_task_approve(task_id: str, request: Request):
    """Approve a task in awaiting_approval state.

    Body (optional): {approved_by?: str, note?: str}
    """
    try:
        body: dict = {}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            pass
        from .task_queue import approve_task  # noqa: PLC0415
        task = approve_task(
            task_id,
            approved_by = body.get("approved_by", "user"),
            note        = body.get("note", ""),
        )
        return {"ok": True, "task": task}
    except (KeyError, ValueError) as e:
        return _err(str(e), 400)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/tasks/{task_id}/reject")
async def api_task_reject(task_id: str, request: Request):
    """Reject a task in awaiting_approval state.

    Body (optional): {rejected_by?: str, note?: str}
    """
    try:
        body: dict = {}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            pass
        from .task_queue import reject_task  # noqa: PLC0415
        task = reject_task(
            task_id,
            rejected_by = body.get("rejected_by", "user"),
            note        = body.get("note", ""),
        )
        return {"ok": True, "task": task}
    except (KeyError, ValueError) as e:
        return _err(str(e), 400)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/tasks/{task_id}/interrupt")
async def api_task_interrupt(task_id: str):
    """Interrupt a running or queued task."""
    try:
        from .task_queue import interrupt_task  # noqa: PLC0415
        task = interrupt_task(task_id)
        return {"ok": True, "task": task}
    except (KeyError, ValueError) as e:
        return _err(str(e), 400)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/tasks/prune")
async def api_tasks_prune():
    """Prune terminal tasks older than BOUNDS.task_retention_days (30d)."""
    try:
        from .task_queue import prune_old_tasks  # noqa: PLC0415
        pruned = prune_old_tasks()
        return {"ok": True, "pruned": pruned}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Knowledge Graph / v0.5 ───────────────────────────────────────────────────

@app.get("/api/graph/stats")
async def api_graph_stats():
    """Knowledge graph statistics: entity count, relation counts by type, most connected."""
    try:
        from .knowledge_graph import graph_stats  # noqa: PLC0415
        return graph_stats()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/graph/entities")
async def api_graph_entities(kind: str | None = Query(None)):
    """List all entities, optionally filtered by kind (thread|insight|concept|external)."""
    try:
        from .knowledge_graph import load_graph, _entity_to_dict  # noqa: PLC0415
        graph = load_graph()
        entities = [_entity_to_dict(e) for e in graph.values()
                    if kind is None or e.kind == kind]
        entities.sort(key=lambda e: e.get("updated", ""), reverse=True)
        return {"entities": entities, "total": len(entities)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/graph/entities")
async def api_graph_add_entity(request: Request):
    """Add or update an entity.

    Body: {label: str, kind?: str, entity_id?: str, thread_stem?: str,
           insight_id?: str, description?: str, tags?: list[str]}
    """
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    label = (body.get("label") or "").strip()
    if not label:
        return _err("label wymagany")
    try:
        from .knowledge_graph import add_entity, _entity_to_dict  # noqa: PLC0415
        e = add_entity(
            entity_id   = body.get("entity_id"),
            label       = label,
            kind        = body.get("kind", "concept"),
            thread_stem = body.get("thread_stem"),
            insight_id  = body.get("insight_id"),
            description = body.get("description", ""),
            tags        = body.get("tags") or [],
        )
        return {"ok": True, "entity": _entity_to_dict(e)}
    except ValueError as e:
        return _err(str(e), 400)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/graph/entities/{entity_id}")
async def api_graph_get_entity(entity_id: str):
    """Get a single entity with its neighbours (outgoing + incoming relations)."""
    try:
        from .knowledge_graph import get_neighbours  # noqa: PLC0415
        nb = get_neighbours(entity_id)
        if not nb:
            return _err(f"Entity not found: {entity_id}", 404)
        return nb
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/graph/relations")
async def api_graph_add_relation(request: Request):
    """Add a typed relation between two entities.

    Body: {from_id: str, rel_type: str, to_id: str, confidence: float,
           source?: str, note?: str}
    """
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("Invalid JSON", 400)
    from_id    = (body.get("from_id") or "").strip()
    to_id      = (body.get("to_id") or "").strip()
    rel_type   = (body.get("rel_type") or "").strip()
    confidence = float(body.get("confidence", 0.5))
    if not (from_id and to_id and rel_type):
        return _err("from_id, to_id, rel_type wymagane")
    try:
        from .knowledge_graph import add_relation, _relation_to_dict  # noqa: PLC0415
        rel = add_relation(
            from_id    = from_id,
            rel_type   = rel_type,
            to_id      = to_id,
            confidence = confidence,
            source     = body.get("source", "user"),
            note       = body.get("note", ""),
        )
        return {"ok": True, "relation": _relation_to_dict(rel)}
    except (ValueError, KeyError) as e:
        return _err(str(e), 400)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.delete("/api/graph/relations/{from_id}/{relation_id}")
async def api_graph_remove_relation(from_id: str, relation_id: str):
    """Remove a relation by relation_id from a given entity."""
    try:
        from .knowledge_graph import remove_relation  # noqa: PLC0415
        ok = remove_relation(from_id, relation_id)
        return {"ok": ok}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/graph/propagate/{entity_id}")
async def api_graph_propagate(
    entity_id: str,
    depth: int = Query(2, ge=1, le=4),
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
):
    """Compute confidence propagation from entity_id up to `depth` hops.

    Returns inferred (non-stored) relations derived through the propagation rules.
    """
    try:
        from .knowledge_graph import propagate  # noqa: PLC0415
        from dataclasses import asdict  # noqa: PLC0415
        inferred = propagate(entity_id, max_depth=depth, min_confidence=min_confidence)
        return {
            "entity_id": entity_id,
            "depth":     depth,
            "inferred":  [asdict(r) for r in inferred],
            "count":     len(inferred),
        }
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/graph/suggest/{stem}")
async def api_graph_suggest(stem: str, min_similarity: float = Query(0.75)):
    """Suggest knowledge graph relations for a thread based on semantic link scores."""
    try:
        from .knowledge_graph import suggest_relations_from_links  # noqa: PLC0415
        suggestions = suggest_relations_from_links(stem, min_similarity=min_similarity)
        return {"stem": stem, "suggestions": suggestions}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Docs / knowledge artifacts ────────────────────────────────────────────────

@app.get("/api/docs/parse")
async def api_parse_doc(path_rel: str = Query(..., description="Path relative to ROOT")):
    """Parse a markdown document with YAML frontmatter. Returns structured metadata."""
    try:
        from .docs_manager import ROOT as DOCS_ROOT, load_knowledge_artifact  # noqa: PLC0415
        full_path = DOCS_ROOT / path_rel
        doc = load_knowledge_artifact(full_path)
        return {
            "path": doc.path,
            "title": doc.artifact_title,
            "artifact_kind": doc.artifact_kind,
            "workflow_kind": doc.workflow_kind,
            "status": doc.status,
            "review_required": doc.review_required,
            "sources_used": list(doc.sources_used),
            "metadata": doc.metadata,
            "bullet_fields": doc.bullet_fields,
            "sections": list(doc.sections.keys()),
        }
    except ValueError as e:
        return _err(str(e), 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Chronicle ─────────────────────────────────────────────────────────────────

@app.get("/api/chronicle")
async def api_chronicle(
    limit: int = Query(50),
    project_id: str = Query(""),
    domain: str = Query(""),
    event_type: str = Query(""),
    source: str = Query(""),
):
    """List recent ChronicleEvents."""
    try:
        from .chronicle import list_events_as_dicts  # noqa: PLC0415
        events = list_events_as_dicts(
            limit=limit, project_id=project_id, domain=domain,
            event_type=event_type, source=source,
        )
        return {"events": events, "count": len(events)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/chronicle/log")
async def api_chronicle_log(request: Request):
    """Manually log a ChronicleEvent (for external tools / testing)."""
    body = await request.json()
    source = (body.get("source") or "").strip()
    event_type = (body.get("event_type") or "").strip()
    if not source or not event_type:
        return _err("source and event_type required")
    try:
        from .chronicle import log_and_build  # noqa: PLC0415
        ev = log_and_build(
            source=source,
            event_type=event_type,
            project_id=body.get("project_id", "lite"),
            domain=body.get("domain", "research"),
            workflow_kind=body.get("workflow_kind"),
            context_ref=body.get("context_ref"),
            metadata=body.get("metadata"),
        )
        return {"ok": True, "event": ev.as_dict()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Perception ─────────────────────────────────────────────────────────────────

@app.get("/api/perception/context")
async def api_perception_context(
    project_id: str = Query("lite"),
    domain: str = Query("research"),
    event_limit: int = Query(30),
):
    """Distil a DistilledContext from recent ChronicleEvents."""
    try:
        from .perception import get_current_session_context  # noqa: PLC0415
        ctx = get_current_session_context(
            project_id=project_id, domain=domain,
            event_limit=event_limit, persist=True,
        )
        if ctx is None:
            return {"available": False, "context": None, "reason": "no events in chronicle log"}
        return {"available": True, "context": ctx.as_dict(), "prefix": ctx.as_context_prefix()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/perception/last")
async def api_perception_last():
    """Return the last saved DistilledContext."""
    try:
        from .perception import load_last_distilled_context  # noqa: PLC0415
        ctx = load_last_distilled_context()
        if ctx is None:
            return {"available": False, "context": None}
        return {"available": True, "context": ctx.as_dict()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Research continuity ────────────────────────────────────────────────────────

@app.get("/api/research/traces")
async def api_research_traces(project_id: str = Query("")):
    """List all ResearchProjectMemoryTraces."""
    try:
        from .research_continuity import load_research_traces  # noqa: PLC0415
        traces = load_research_traces(project_id=project_id)
        return {"traces": [t.as_dict() for t in traces], "count": len(traces)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/research/traces/save")
async def api_research_trace_save(request: Request):
    """Save a ResearchProjectMemoryTrace from a skill/research result dict."""
    body = await request.json()
    if not body.get("title") or not body.get("workflow_kind"):
        return _err("title and workflow_kind required")
    try:
        from .research_continuity import build_research_project_memory_trace, save_research_trace  # noqa: PLC0415
        trace = build_research_project_memory_trace(body)
        saved = save_research_trace(trace)
        return {"ok": True, "trace_id": saved["id"], "trace": trace.as_dict()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/research/traces/stale")
async def api_research_traces_stale(days: int = Query(7)):
    """List working-status traces open for ≥ days days (default 7)."""
    try:
        from .research_continuity import list_stale_traces  # noqa: PLC0415
        stale = list_stale_traces(days=days)
        return {"stale": stale, "count": len(stale), "threshold_days": days}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/research/traces/promote")
async def api_research_trace_promote(request: Request):
    """Promote a trace to a new artifact_status.

    Publishing ('published' / 'canonical') requires at least one approved
    DARKROOM disposition entry (canonical output gate).
    """
    body = await request.json()
    trace_id   = (body.get("trace_id") or "").strip()
    new_status = (body.get("new_status") or "").strip()
    if not trace_id or not new_status:
        return _err("trace_id and new_status required")
    try:
        from .darkroom.pipeline import _APPROVALS_FILE  # noqa: PLC0415
        from .research_continuity import promote_trace  # noqa: PLC0415
        result = promote_trace(trace_id, new_status, _APPROVALS_FILE)
        return result
    except ValueError as e:
        return _err(str(e))
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/research/bootstrap")
async def api_research_bootstrap(project_id: str = Query("lite")):
    """Build a research bootstrap view for a project."""
    try:
        from .research_continuity import build_research_bootstrap_view  # noqa: PLC0415
        view = build_research_bootstrap_view(project_id=project_id)
        return view
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Research Pipeline (v0.4a) ─────────────────────────────────────────────────

@app.post("/api/research/pipeline/run")
async def api_pipeline_run(request: Request):
    """Uruchom pełny ResearchPipeline: Silo skill → DARKROOM → Trace → SM synthesis.

    Body (JSON):
      skill_id   str   — id skilla w silosie
      inputs     dict  — dane wejściowe dla skilla
      silo_id    str   — "silo_1" (domyślnie)
      project_id str   — id projektu (domyślnie "lite")
      title      str   — tytuł trace'a (opcjonalny)
    """
    import asyncio  # noqa: PLC0415
    body = await request.json()
    skill_id = (body.get("skill_id") or "").strip()
    if not skill_id:
        return _err("skill_id wymagany")
    try:
        from .research_pipeline import run_research_pipeline  # noqa: PLC0415
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_research_pipeline(
                skill_id,
                body.get("inputs", {}),
                silo_id=body.get("silo_id", "silo_1"),
                project_id=body.get("project_id", "lite"),
                title=body.get("title", ""),
            ),
        )
        return result.as_dict()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/research/pipeline/list")
async def api_pipeline_list(limit: int = Query(20), project_id: str = Query("")):
    """List recent pipeline runs (cross-referenced traces + chronicle)."""
    try:
        from .research_pipeline import list_pipeline_results  # noqa: PLC0415
        results = list_pipeline_results(limit=limit, project_id=project_id)
        return {"results": results, "count": len(results)}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Model performance (UCB1) ──────────────────────────────────────────────────

@app.get("/api/models/performance")
async def api_models_performance():
    """Return UCB1 model performance summary across all task types."""
    try:
        from .models import get_model_performance_summary  # noqa: PLC0415
        return {"summary": get_model_performance_summary()}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/models/performance/log")
async def api_models_performance_log(request: Request):
    """Manually log a model performance observation."""
    body = await request.json()
    task_type = (body.get("task_type") or "general").strip()
    model = (body.get("model") or "").strip()
    success = bool(body.get("success", True))
    if not model:
        return _err("model required")
    try:
        from .models import update_model_performance  # noqa: PLC0415
        row = update_model_performance(
            task_type=task_type, model=model, success=success,
            latency_ms=body.get("latency_ms"), project_id=body.get("project_id", ""),
        )
        return {"ok": True, "row": row}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/models/recommend")
async def api_models_recommend(task_type: str = Query("general"), task_text: str = Query("")):
    """Get UCB1 model recommendation for a task type."""
    try:
        from .models import recommend_model_ucb1  # noqa: PLC0415
        recommendation = recommend_model_ucb1(task_type, task_text)
        return {"task_type": task_type, "recommended_model": recommendation}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Search ────────────────────────────────────────────────────────────────────

@app.get("/api/search")
async def api_search(q: str = Query(""), source: str = Query("")):
    """v0.7: BM25-ranked cross-source search via FTS5."""
    if not q:
        return {"results": []}
    try:
        from .search_manager import search  # noqa: PLC0415
        source_filter = source if source else None
        return {"results": search(q, source_filter=source_filter), "query": q}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/search/stats")
async def api_search_stats():
    """v0.7: Return search index statistics."""
    try:
        from .search_index import index_stats  # noqa: PLC0415
        return index_stats()
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/search/rebuild")
async def api_search_rebuild():
    """v0.7: Force rebuild of the search index."""
    try:
        from .search_index import rebuild_index  # noqa: PLC0415
        count = rebuild_index()
        return {"ok": True, "documents_indexed": count}
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.post("/api/fetch/reader")
async def api_fetch_reader(request: Request):
    """v0.7: Reader mode — extract main content from URL."""
    body = await request.json()
    url = (body.get("url") or "").strip()
    if not url:
        return _err("url wymagany")
    try:
        from .browser import fetch_reader  # noqa: PLC0415
        return fetch_reader(url)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── Research tools ────────────────────────────────────────────────────────────

@app.post("/api/research/literature-map")
async def api_literature_map(request: Request):
    return await _research_stream(request, "literature_map")


@app.post("/api/research/stress-test")
async def api_stress_test(request: Request):
    return await _research_stream(request, "stress_test")


@app.post("/api/research/synthesize")
async def api_synthesize(request: Request):
    return await _research_stream(request, "synthesis")


@app.post("/api/research/compare-models")
async def api_compare_models(request: Request):
    body = await request.json()
    task = (body.get("task") or "").strip()
    if not task:
        return _err("task wymagany")
    try:
        from .darkroom.pipeline import compare_models  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: compare_models(task, _get_secretary().client)
        )
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


async def _research_stream(request: Request, tool: str) -> StreamingResponse:
    body = await request.json()
    from .research_tools import (  # noqa: PLC0415
        build_literature_map_prompt, build_stress_test_prompt,
        build_synthesis_prompt, suggested_filename_for_tool,
    )

    subject = (body.get("topic") or body.get("hypothesis") or
               body.get("subject") or "").strip()
    thread_stems = body.get("threads", [])

    if tool == "literature_map":
        task = build_literature_map_prompt(subject)
        save_as = suggested_filename_for_tool("literature_map", subject)
    elif tool == "stress_test":
        task = build_stress_test_prompt(subject)
        save_as = suggested_filename_for_tool("stress_test", subject)
    elif tool == "synthesis":
        # Load actual thread content — stems alone are useless for synthesis
        from .library_manager import read_thread  # noqa: PLC0415
        threads_with_content: list[dict] = []
        for stem in thread_stems:
            if isinstance(stem, dict):
                threads_with_content.append(stem)  # already has title+content
            else:
                try:
                    content = read_thread(str(stem))
                    threads_with_content.append({"title": str(stem), "content": content})
                except Exception:  # noqa: BLE001
                    threads_with_content.append({"title": str(stem), "content": f"[nie udało się załadować wątku: {stem}]"})
        task = build_synthesis_prompt(threads_with_content)
        save_as = suggested_filename_for_tool("synthesis", "_".join(str(s) for s in thread_stems[:3]))
    else:
        return _err("unknown tool")

    messages = [{"role": "user", "content": task}]

    return StreamingResponse(
        _stream_in_thread(messages, save_as=save_as),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Export ────────────────────────────────────────────────────────────────────

@app.get("/api/export/thread")
async def api_export_thread(stem: str = Query("")):
    if not stem:
        return _err("stem wymagany")
    try:
        from .export_manager import export_thread_zip  # noqa: PLC0415
        data = export_thread_zip(stem)
        return Response(content=data, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{stem}.zip"'})
    except FileNotFoundError:
        return _err("not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/export/project")
async def api_export_project(project_id: str = Query("")):
    if not project_id:
        return _err("project_id wymagany")
    try:
        from .export_manager import export_project_zip  # noqa: PLC0415
        data = export_project_zip(project_id)
        return Response(content=data, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{project_id}.zip"'})
    except FileNotFoundError:
        return _err("not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/export/artifact")
async def api_export_artifact(name: str = Query("")):
    if not name:
        return _err("name wymagany")
    try:
        from .export_manager import export_artifact  # noqa: PLC0415
        data, filename = export_artifact(name)
        ct = "application/zip" if filename.endswith(".zip") else "text/markdown; charset=utf-8"
        return Response(content=data, media_type=ct,
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except FileNotFoundError:
        return _err("not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── v0.8 — Polished MD, Research Bundle, Share HTML ──────────────────────────

@app.get("/api/export/polished-md")
async def api_export_polished_md(stem: str = Query("")):
    """Export thread as polished Markdown with YAML frontmatter and ToC."""
    if not stem:
        return _err("stem wymagany")
    try:
        from .export_manager import export_polished_md  # noqa: PLC0415
        md = export_polished_md(stem)
        return Response(
            content=md.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{stem}_polished.md"'},
        )
    except FileNotFoundError:
        return _err("not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/export/research-bundle")
async def api_export_research_bundle(stem: str = Query("")):
    """Export thread as a research bundle ZIP with all related files."""
    if not stem:
        return _err("stem wymagany")
    try:
        from .export_manager import export_research_bundle  # noqa: PLC0415
        data = export_research_bundle(stem)
        return Response(
            content=data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{stem}_bundle.zip"'},
        )
    except FileNotFoundError:
        return _err("not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/export/share-html")
async def api_export_share_html(stem: str = Query("")):
    """Export thread as self-contained share HTML page."""
    if not stem:
        return _err("stem wymagany")
    try:
        from .export_manager import export_share_html  # noqa: PLC0415
        html = export_share_html(stem)
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{stem}_share.html"'},
        )
    except FileNotFoundError:
        return _err("not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


@app.get("/api/export/share-html/preview")
async def api_export_share_html_preview(stem: str = Query("")):
    """Preview share HTML inline (no Content-Disposition, renders in browser)."""
    if not stem:
        return _err("stem wymagany")
    try:
        from .export_manager import export_share_html  # noqa: PLC0415
        html = export_share_html(stem)
        return Response(content=html.encode("utf-8"), media_type="text/html; charset=utf-8")
    except FileNotFoundError:
        return _err("not found", 404)
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── v0.9 — Morning Briefing ───────────────────────────────────────────────────

@app.get("/api/briefing")
async def api_briefing(force: bool = Query(False)):
    """Return morning briefing payload (shows when gap > 8 h since last session)."""
    try:
        from .briefing_manager import get_morning_briefing  # noqa: PLC0415
        return get_morning_briefing(force=force)
    except Exception as e:  # noqa: BLE001
        return {"show": False, "gap_hours": 0.0, "synthesis": None,
                "connections": [], "error": str(e)}


@app.post("/api/briefing/mark-session")
async def api_briefing_mark_session(request: Request):
    """Record current time as session start. Call on page load.

    Optional body: {"session_id": str}
    v0.4.5: also ticks fatigue and resets attention budget.
    """
    try:
        body: dict = {}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            pass

        from .briefing_manager import mark_session_start  # noqa: PLC0415
        mark_session_start()

        # v0.4.5 homeostasis
        from .homeostasis import tick_fatigue, session_start  # noqa: PLC0415
        session_id = body.get("session_id") or f"session_{__import__('uuid').uuid4().hex[:8]}"
        fatigue = tick_fatigue()
        session_start(session_id)

        return {"ok": True, "session_id": session_id, "fatigue": fatigue}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@app.get("/api/health/system")
async def api_health_system():
    """System complexity metrics for the DARKROOM System Health panel.

    Returns active/frozen thread counts, insight/candidate/artifact counts,
    and a composite complexity score. All counts come from live filesystem state.
    """
    try:
        from .library_manager import list_threads   # noqa: PLC0415
        from .memory_manager import list_insights   # noqa: PLC0415
        from .config import ROOT as _root           # noqa: PLC0415

        threads      = list_threads(include_archived=False)
        active       = [t for t in threads if t.get("status") == "active"]
        frozen       = [t for t in threads if t.get("status") == "frozen"]
        library_thr  = [t for t in threads if t.get("status") not in ("active", "frozen")]

        insights     = list_insights(include_archived=False)

        candidates_dir = _root / "memory" / "candidates"
        candidate_count = len(list(candidates_dir.glob("*.json"))) if candidates_dir.exists() else 0

        artifacts_dir = _root / "library" / "artifacts"
        artifact_count = len(list(artifacts_dir.glob("*.md"))) if artifacts_dir.exists() else 0

        # Composite score: active threads dominate (cost 2 each); insights/candidates are lighter
        score = round(
            len(active) * 2.0 +
            candidate_count * 0.5 +
            len(insights) * 0.1,
            1,
        )

        return {
            "active_threads":    len(active),
            "frozen_threads":    len(frozen),
            "library_threads":   len(library_thr),
            "total_threads":     len(threads),
            "insight_count":     len(insights),
            "candidate_count":   candidate_count,
            "artifact_count":    artifact_count,
            "complexity_score":  score,
            "limit_ok":          len(active) <= _BOUNDS.max_active_threads,
            "active_thread_limit": _BOUNDS.max_active_threads,
            "thread_watcher": __import__(
                "matylda_lite.thread_watcher", fromlist=["watcher_status"]
            ).watcher_status(),
        }
    except Exception as e:  # noqa: BLE001
        return _err(str(e), 500)


# ── v0.3 — Sleeping Matylda & Silos ──────────────────────────────────────────

@app.get("/api/sleeping/status")
async def api_sleeping_status():
    from .sleeping_matylda.bridge import get_status  # noqa: PLC0415
    return get_status()


@app.post("/api/sleeping/run")
async def api_sleeping_run():
    """Uruchom Sleeping Matylda synthesis.

    Zbiera kontekst z Matylda Lab (wątki, insighty, napięcia, artefakty)
    i generuje refleksyjną syntezę przez Anthropic API.
    Wynik zapisywany w ~/.matylda/sleeping_matylda_last.json.
    """
    import asyncio  # noqa: PLC0415
    from .sleeping_matylda.bridge import run_synthesis_now  # noqa: PLC0415
    # run_synthesis_now jest synchroniczne — uruchamiamy w thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_synthesis_now)
    return result


@app.get("/api/sleeping/last")
async def api_sleeping_last():
    """Zwróć ostatni wynik Sleeping Matylda synthesis."""
    from .sleeping_matylda.synthesis import load_last_result  # noqa: PLC0415
    last = load_last_result()
    if last is None:
        return {"available": False, "result": None, "timestamp": None}
    return {
        "available":  True,
        "timestamp":  last.get("timestamp"),
        "result":     last.get("result"),
        "snapshot_summary": last.get("snapshot_summary"),
    }


@app.get("/api/silos")
async def api_silos_list():
    from .silos import all_silo_meta  # noqa: PLC0415
    return {"silos": all_silo_meta()}


# ── Silo routers (auto-discovery przy starcie) ────────────────────────────────

def _register_silo_routers() -> None:
    """Załaduj i zarejestruj routery wszystkich aktywnych silosów."""
    try:
        from .silos import load_enabled_silos  # noqa: PLC0415
        for meta, router in load_enabled_silos():
            app.include_router(router)
            print(f"[silos] ✓ {meta['id']} ({meta['name']}) — {len(router.routes)} endpointów")
    except Exception as exc:  # noqa: BLE001
        print(f"[silos] błąd rejestracji routerów: {exc}")


_register_silo_routers()


# ── Thread Watcher (hooks: OnThreadWrite) ────────────────────────────────────

def _start_background_services() -> None:
    """Uruchom usługi tła: watcher wątków + system hooków + task worker."""
    try:
        from .thread_watcher import start_watcher  # noqa: PLC0415
        start_watcher()
        print("[hooks] ✓ ThreadWatcher uruchomiony (OnThreadWrite aktywny)")
    except Exception as exc:  # noqa: BLE001
        print(f"[hooks] ThreadWatcher nie uruchomiony: {exc}")

    try:
        from .task_queue import start_worker  # noqa: PLC0415
        start_worker()
        print("[tasks] ✓ TaskQueue worker uruchomiony")
    except Exception as exc:  # noqa: BLE001
        print(f"[tasks] TaskQueue worker nie uruchomiony: {exc}")

    try:
        from .sleeping_matylda import start_background_worker as _sm_start  # noqa: PLC0415
        _sm_start()
        print("[sleeping-matylda] ✓ Sleeping Matylda worker uruchomiony")
    except Exception as exc:  # noqa: BLE001
        print(f"[sleeping-matylda] Sleeping Matylda nie uruchomiona: {exc}")

    # Tension lifecycle: age out medium/low tensions >30 days at startup
    # (critical tensions stay ad infinitum). Covers the desktop restart cadence.
    try:
        from .darkroom.tension import triage_tensions  # noqa: PLC0415
        r = triage_tensions()
        if r["test_archived"] or r["aged_archived"] or r["deduped"]:
            print(f"[tensions] ✓ auto-triage: {r['aged_archived']} przeterminowanych, "
                  f"{r['test_archived']} testowych, {r['deduped']} duplikatów → "
                  f"{r['active_remaining']} aktywnych")
    except Exception as exc:  # noqa: BLE001
        print(f"[tensions] auto-triage pominięty: {exc}")


# ── Hooks API ────────────────────────────────────────────────────────────────

@app.get("/api/hooks")
async def api_hooks():
    """Lista zarejestrowanych hooków (do diagnostyki)."""
    from .hooks import list_handlers  # noqa: PLC0415
    return {"hooks": list_handlers()}


@app.get("/api/threads/{stem}/links")
async def api_thread_links(stem: str):
    """Powiązania semantyczne wątku z innymi wątkami (z thread_links.json)."""
    from .thread_watcher import get_thread_links  # noqa: PLC0415
    return {"stem": stem, "links": get_thread_links(stem)}


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def api_health():
    """Health check dla LaunchAgent i monitoringu."""
    return {"ok": True, "version": "1.2"}


# ── Helper ────────────────────────────────────────────────────────────────────

def _err(msg: str, code: int = 400) -> Response:
    return Response(
        content=json.dumps({"error": msg}, ensure_ascii=False),
        status_code=code,
        media_type="application/json",
    )


# ── Sleeping Matylda API (v0.7) ───────────────────────────────────────────────

@app.get("/api/sleeping-matylda/status")
async def sm_status():
    """Stan Sleeping Matylda: ostatni cykl, pending findings, bounds."""
    try:
        from .sleeping_matylda import get_status  # noqa: PLC0415
        return get_status()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/sleeping-matylda/run")
async def sm_run(force: bool = Query(default=False)):
    """Uruchom cykl konsolidacji ręcznie. force=true pomija sprawdzanie min_gap."""
    try:
        from .sleeping_matylda import run_cycle  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: run_cycle(force=force))
        return result
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/sleeping-matylda/findings")
async def sm_findings(state: str = Query(default="pending")):
    """Lista findings filtrowanych po state: pending | approved | dismissed | all.

    Auto-triages unscored pending findings on every fetch so the caller
    always receives Eisenhower-scored data without needing a separate call.
    """
    try:
        from .sleeping_matylda import get_findings  # noqa: PLC0415
        from .sleeping_matylda.consolidation import triage_findings  # noqa: PLC0415
        if state in ("pending", "all"):
            raw_pending = get_findings(state_filter="pending")
            if any("eisenhower_quadrant" not in f for f in raw_pending):
                triage_findings(auto_archive_q4=True)
        state_filter = None if state == "all" else state
        return {"findings": get_findings(state_filter=state_filter)}
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/sleeping-matylda/triage")
async def sm_triage():
    """Eisenhower triage: score all unscored pending findings, auto-archive Q4."""
    try:
        from .sleeping_matylda.consolidation import triage_findings  # noqa: PLC0415
        result = triage_findings(auto_archive_q4=True)
        return {"ok": True, **result}
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/sleeping-matylda/findings/{finding_id}/approve")
async def sm_approve_finding(finding_id: str, request: Request):
    """Zatwierdź finding i wykonaj jego akcję."""
    try:
        from .sleeping_matylda import approve_finding  # noqa: PLC0415
        body = {}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            pass
        approved_by = body.get("approved_by", "user")
        result = approve_finding(finding_id, approved_by=approved_by)
        return {"ok": True, "finding": result}
    except KeyError as exc:
        return _err(str(exc), 404)
    except ValueError as exc:
        return _err(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/sleeping-matylda/findings/{finding_id}/dismiss")
async def sm_dismiss_finding(finding_id: str, request: Request):
    """Odrzuć finding (bez efektów ubocznych)."""
    try:
        from .sleeping_matylda import dismiss_finding  # noqa: PLC0415
        body = {}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            pass
        reason = body.get("reason", "")
        result = dismiss_finding(finding_id, reason=reason)
        return {"ok": True, "finding": result}
    except KeyError as exc:
        return _err(str(exc), 404)
    except ValueError as exc:
        return _err(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


# ── Positive Room endpoints (v0.9) ───────────────────────────────────────────

@app.get("/api/positive-room/status")
async def positive_room_status():
    """Positive Room summary: total entries, attractive count, threshold."""
    try:
        from .positive_room import positive_status  # noqa: PLC0415
        return positive_status()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/positive-room/trajectories")
async def positive_room_trajectories(threshold: float = Query(default=None)):
    """List trajectories above success threshold (default: positive_success_threshold)."""
    try:
        from .positive_room import list_attractive_trajectories  # noqa: PLC0415
        kw = {} if threshold is None else {"threshold": threshold}
        return list_attractive_trajectories(**kw)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


# ── Identity Snapshot endpoints (v0.9) ────────────────────────────────────────

@app.post("/api/sleeping-matylda/snapshot")
async def sm_snapshot(request: Request):
    """Take a lightweight identity snapshot (label optional in JSON body)."""
    try:
        from .sleeping_matylda import snapshot_identity  # noqa: PLC0415
        body = {}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            pass
        label = body.get("label", "")
        snap  = snapshot_identity(label=label)
        return {"ok": True, "snapshot": snap}
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/sleeping-matylda/snapshots")
async def sm_snapshots():
    """List all identity snapshots, newest first."""
    try:
        from .sleeping_matylda import list_snapshots  # noqa: PLC0415
        return {"snapshots": list_snapshots()}
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/sleeping-matylda/snapshots/compare")
async def sm_compare_snapshots(a: str = Query(...), b: str = Query(...)):
    """Compare two snapshots by ID. Returns structural deltas."""
    try:
        from .sleeping_matylda import compare_snapshots  # noqa: PLC0415
        return compare_snapshots(a, b)
    except KeyError as exc:
        return _err(str(exc), 404)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/sleeping-matylda/meta-drift")
async def sm_meta_drift():
    """Current meta_drift summary: score, alert status, avg_confidence_modifier."""
    try:
        from .sleeping_matylda import get_meta_drift  # noqa: PLC0415
        return get_meta_drift()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


# ── Sleeping Matylda Focus Mode endpoints (v1.2) ─────────────────────────────

@app.post("/api/sleeping-matylda/focus-start")
async def sm_focus_start(request: Request):
    """Start a Focus Mode session.

    Body (JSON):
      focus_areas        list[str]   — subset of ["questions","tensions","steps","no_go"]
      mode               str         — "timebox" (default) | "until_idle"
      duration_seconds   int         — seconds for timebox mode (default 1800)
      idle_threshold     int         — consecutive empty cycles for until_idle (default 3)
      only_active_threads bool       — restrict to threads with recent activity
      silent_mode        bool        — suppress chronicle logging during session
      auto_tag_low_risk  bool        — tag low-confidence findings (never auto-approve)
      custom_prompt      str         — optional focus instruction injected into engines
    """
    body = await request.json()
    areas = body.get("focus_areas") or []
    if not isinstance(areas, list) or not areas:
        return _err("focus_areas must be a non-empty list")
    try:
        from .sleeping_matylda.focus_engine import start_focus_session, VALID_FOCUS_AREAS  # noqa: PLC0415
        invalid = [a for a in areas if a not in VALID_FOCUS_AREAS]
        if invalid:
            return _err(f"Unknown focus areas: {invalid}. Valid: {sorted(VALID_FOCUS_AREAS)}")
        cfg = start_focus_session(
            focus_areas=areas,
            mode=body.get("mode", "timebox"),
            duration_seconds=int(body.get("duration_seconds", 1800)),
            idle_threshold=int(body.get("idle_threshold", 3)),
            only_active_threads=bool(body.get("only_active_threads", False)),
            silent_mode=bool(body.get("silent_mode", False)),
            auto_tag_low_risk=bool(body.get("auto_tag_low_risk", False)),
            custom_prompt=str(body.get("custom_prompt", "")),
        )
        return {"ok": True, "session": cfg.as_dict()}
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/sleeping-matylda/focus-status")
async def sm_focus_status():
    """Return current focus session status, remaining time, findings count."""
    try:
        from .sleeping_matylda.focus_engine import get_focus_status  # noqa: PLC0415
        return get_focus_status()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/sleeping-matylda/focus-pause")
async def sm_focus_pause():
    """Pause the running focus session (timer keeps ticking, no new cycles)."""
    try:
        from .sleeping_matylda.focus_engine import pause_focus_session  # noqa: PLC0415
        return pause_focus_session()
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/sleeping-matylda/focus-resume")
async def sm_focus_resume():
    """Resume a paused focus session."""
    try:
        from .sleeping_matylda.focus_engine import resume_focus_session  # noqa: PLC0415
        return resume_focus_session()
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.post("/api/sleeping-matylda/focus-stop")
async def sm_focus_stop():
    """Cancel the active focus session immediately."""
    try:
        from .sleeping_matylda.focus_engine import stop_focus_session  # noqa: PLC0415
        return stop_focus_session()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


# ── Counterfactual Room endpoints (v1.0) ─────────────────────────────────────

@app.get("/api/counterfactual-room/status")
async def counterfactual_room_status():
    """Counterfactual Room summary: total records, pending, evaluated, corrections."""
    try:
        from .counterfactual_room import counterfactual_status  # noqa: PLC0415
        return counterfactual_status()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/counterfactual-room/pending")
async def counterfactual_room_pending():
    """List counterfactual records awaiting evaluation (mature and immature)."""
    try:
        from .counterfactual_room import list_pending_evaluations  # noqa: PLC0415
        return {"records": list_pending_evaluations()}
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


# ── NoGo Room endpoints (v0.8) ────────────────────────────────────────────────

@app.get("/api/nogo-room/status")
async def nogo_room_status():
    """NoGo Room summary: total entries, high-risk count, threshold."""
    try:
        from .nogo_room import nogo_status  # noqa: PLC0415
        return nogo_status()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/nogo-room/trajectories")
async def nogo_room_trajectories(threshold: float = Query(default=None)):
    """List trajectories above threshold (default: constitutional nogo_risk_threshold)."""
    try:
        from .nogo_room import list_risky_trajectories  # noqa: PLC0415
        kw = {} if threshold is None else {"threshold": threshold}
        return list_risky_trajectories(**kw)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


# ── Forgetroom endpoints (v0.8) ───────────────────────────────────────────────

@app.get("/api/forgetroom/status")
async def forgetroom_status():
    """Forgetroom summary: total objects, forgotten count, threshold, oldest object."""
    try:
        from .forgetroom import forgetroom_summary  # noqa: PLC0415
        return forgetroom_summary()
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@app.get("/api/forgetroom/candidates")
async def forgetroom_candidates(threshold: float = Query(default=None)):
    """List forgotten objects below threshold (default: forgetroom_prune_threshold)."""
    try:
        from .forgetroom import get_forgotten_candidates  # noqa: PLC0415
        kw = {} if threshold is None else {"threshold": threshold}
        return get_forgotten_candidates(**kw)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


# ── Uvicorn entry ─────────────────────────────────────────────────────────────

def start(port: int = PORT, host: str = "localhost", open_browser: bool = True,
          daemon: bool = False, enable_automation: bool = False) -> None:
    """Uruchom serwer uvicorn. Blokuje wątek wywołujący."""
    import uvicorn  # noqa: PLC0415
    import webbrowser  # noqa: PLC0415

    app.state.enable_automation = enable_automation
    print(f"Matylda Lab + DARKROOM → http://{host}:{port}/")

    if open_browser and not daemon:
        import threading as _t  # noqa: PLC0415
        _t.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}/")).start()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
