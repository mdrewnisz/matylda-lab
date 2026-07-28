"""task_queue.py — v0.6 async Task Queue with Approval Gate.

Design principle:
  "Zamierzam zrobić X" — not "już zrobiłam X".

Every task with estimated_tokens > BOUNDS.task_approval_token_threshold,
or with approval_required=True, pauses at AWAITING_APPROVAL before executing.
A human must explicitly approve (or reject) before the worker proceeds.

Task lifecycle:
  queued → running → done | failed
  queued → awaiting_approval → [approved → running → done | failed]
                               [rejected → rejected]

Storage:
  data/task_queue.jsonl  — append-only log of all task events
  Loaded into memory on demand; state derived from last event per task_id.

Task schema:
  {
    task_id:           str,
    intent:            str,           # human-readable: "what Matylda intends to do"
    payload:           str,           # the actual prompt / instruction to execute
    estimated_tokens:  int,
    approval_required: bool,          # explicit override
    created_by:        str,           # "user" | "system" | "sleeping_matylda"
    created:           ISO str,
    state:             TaskState str,
    priority:          int,           # 1 (highest) — 5 (lowest)
    result:            str | null,
    error:             str | null,
    started:           ISO str | null,
    completed:         ISO str | null,
    approved_by:       str | null,
    approval_note:     str | null,
    tags:              list[str],
  }

Worker:
  asyncio background task, started once on server startup.
  Picks highest-priority queued (or approved) task, runs via Secretary.
  Max BOUNDS.max_running_tasks simultaneously.
  Interrupt supported: set state to "interrupted" → worker skips.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .config import ROOT
from .constitutional import BOUNDS

log = logging.getLogger(__name__)

QUEUE_FILE = ROOT / "data" / "task_queue.jsonl"
QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── Task state ────────────────────────────────────────────────────────────────

class TaskState(str, Enum):
    QUEUED            = "queued"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED          = "approved"
    RUNNING           = "running"
    DONE              = "done"
    FAILED            = "failed"
    REJECTED          = "rejected"
    INTERRUPTED       = "interrupted"

TERMINAL_STATES: frozenset[str] = frozenset({
    TaskState.DONE, TaskState.FAILED, TaskState.REJECTED, TaskState.INTERRUPTED,
})
ACTIVE_STATES: frozenset[str] = frozenset({
    TaskState.QUEUED, TaskState.AWAITING_APPROVAL, TaskState.APPROVED, TaskState.RUNNING,
})


# ── Persistence ───────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_event(task: dict) -> None:
    """Append a task snapshot to the JSONL log (one JSON per line)."""
    with QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(task, ensure_ascii=False) + "\n")


def _load_all_events() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    events: list[dict] = []
    try:
        for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))
    except Exception:  # noqa: BLE001
        pass
    return events


def _derive_tasks(events: list[dict]) -> dict[str, dict]:
    """Derive current task state from event log: last snapshot per task_id wins."""
    tasks: dict[str, dict] = {}
    for event in events:
        tid = event.get("task_id")
        if tid:
            tasks[tid] = event
    return tasks


def load_tasks() -> dict[str, dict]:
    return _derive_tasks(_load_all_events())


def load_active_tasks() -> list[dict]:
    """Return tasks in non-terminal states, sorted by priority asc then created asc."""
    tasks = load_tasks()
    active = [t for t in tasks.values() if t.get("state") in ACTIVE_STATES]
    active.sort(key=lambda t: (t.get("priority", 3), t.get("created", "")))
    return active


def load_task(task_id: str) -> dict | None:
    return load_tasks().get(task_id)


def _count_running() -> int:
    return sum(1 for t in load_tasks().values() if t.get("state") == TaskState.RUNNING)


def _count_active() -> int:
    return sum(1 for t in load_tasks().values() if t.get("state") in ACTIVE_STATES)


# ── Mutations ─────────────────────────────────────────────────────────────────

def enqueue(
    *,
    intent:            str,
    payload:           str,
    estimated_tokens:  int = 500,
    approval_required: bool = False,
    created_by:        str = "user",
    priority:          int = 3,
    tags:              list[str] | None = None,
) -> dict:
    """Add a task to the queue.

    If the task requires approval (explicit flag OR estimated_tokens above threshold),
    initial state is AWAITING_APPROVAL instead of QUEUED.

    Raises ValueError when queue is at capacity (BOUNDS.max_queued_tasks).
    """
    if _count_active() >= BOUNDS.max_queued_tasks:
        raise ValueError(
            f"Task queue at capacity ({BOUNDS.max_queued_tasks} active tasks). "
            "Complete or interrupt existing tasks first."
        )
    if not 1 <= priority <= 5:
        raise ValueError("priority must be 1–5")

    needs_approval = approval_required or (estimated_tokens > BOUNDS.task_approval_token_threshold)
    initial_state  = TaskState.AWAITING_APPROVAL if needs_approval else TaskState.QUEUED

    task: dict[str, Any] = {
        "task_id":           f"task_{uuid.uuid4().hex[:8]}",
        "intent":            intent.strip(),
        "payload":           payload.strip(),
        "estimated_tokens":  estimated_tokens,
        "approval_required": needs_approval,
        "created_by":        created_by,
        "created":           _now(),
        "state":             initial_state,
        "priority":          priority,
        "result":            None,
        "error":             None,
        "started":           None,
        "completed":         None,
        "approved_by":       None,
        "approval_note":     None,
        "tags":              tags or [],
    }
    _append_event(task)
    log.info("task enqueued: %s state=%s intent=%s", task["task_id"], initial_state, intent[:60])
    return task


def approve_task(task_id: str, approved_by: str = "user", note: str = "") -> dict:
    """Approve a task in AWAITING_APPROVAL state → moves to QUEUED."""
    task = load_task(task_id)
    if not task:
        raise KeyError(f"Task not found: {task_id}")
    if task["state"] != TaskState.AWAITING_APPROVAL:
        raise ValueError(f"Task {task_id} is in state {task['state']!r}, not awaiting_approval")
    updated = {
        **task,
        "state":        TaskState.APPROVED,
        "approved_by":  approved_by,
        "approval_note": note,
    }
    _append_event(updated)
    log.info("task approved: %s by=%s", task_id, approved_by)

    # Fire hook
    _fire_task_event("task.approved", updated)
    return updated


def reject_task(task_id: str, rejected_by: str = "user", note: str = "") -> dict:
    """Reject a task in AWAITING_APPROVAL state → terminal REJECTED."""
    task = load_task(task_id)
    if not task:
        raise KeyError(f"Task not found: {task_id}")
    if task["state"] != TaskState.AWAITING_APPROVAL:
        raise ValueError(f"Task {task_id} is in state {task['state']!r}, not awaiting_approval")
    updated = {
        **task,
        "state":        TaskState.REJECTED,
        "approved_by":  rejected_by,
        "approval_note": note,
        "completed":    _now(),
    }
    _append_event(updated)
    log.info("task rejected: %s by=%s", task_id, rejected_by)
    return updated


def interrupt_task(task_id: str) -> dict:
    """Interrupt a running or queued task."""
    task = load_task(task_id)
    if not task:
        raise KeyError(f"Task not found: {task_id}")
    if task["state"] in TERMINAL_STATES:
        raise ValueError(f"Task {task_id} is already in terminal state {task['state']!r}")
    updated = {**task, "state": TaskState.INTERRUPTED, "completed": _now()}
    _append_event(updated)
    log.info("task interrupted: %s", task_id)
    return updated


def _set_state(task: dict, state: str, **extra) -> dict:
    updated = {**task, "state": state, **extra}
    _append_event(updated)
    return updated


def _fire_task_event(event_type: str, task: dict) -> None:
    try:
        from .hooks import fire  # noqa: PLC0415
        fire(event_type, task_id=task["task_id"], task=task)
    except Exception:  # noqa: BLE001
        pass


# ── Worker ────────────────────────────────────────────────────────────────────

_worker_task: asyncio.Task | None = None
_worker_running: bool = False


async def _execute_task(task: dict) -> None:
    """Run a single task via Secretary. Updates state in QUEUE_FILE."""
    task_id = task["task_id"]
    task = _set_state(task, TaskState.RUNNING, started=_now())
    log.info("task starting: %s | %s", task_id, task["intent"][:60])

    try:
        loop = asyncio.get_event_loop()

        def _run_sync():
            from .secretary import Secretary  # noqa: PLC0415
            from .config import get_api_key   # noqa: PLC0415
            import anthropic                  # noqa: PLC0415
            client = anthropic.Anthropic(api_key=get_api_key())
            sec = Secretary(client=client)
            result = sec.chat([{"role": "user", "content": task["payload"]}])
            return result.get("result", "")

        raw_result = await loop.run_in_executor(None, _run_sync)

        # Truncate if needed
        result_text = str(raw_result)
        if len(result_text) > BOUNDS.task_result_max_chars:
            result_text = result_text[:BOUNDS.task_result_max_chars] + "\n… (truncated)"

        task = _set_state(task, TaskState.DONE, result=result_text, completed=_now())
        log.info("task done: %s", task_id)
        _fire_task_event("task.completed", task)

    except asyncio.CancelledError:
        _set_state(task, TaskState.INTERRUPTED, completed=_now())
        raise
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)[:1000]
        _set_state(task, TaskState.FAILED, error=error_msg, completed=_now())
        log.error("task failed: %s — %s", task_id, error_msg)
        _fire_task_event("task.failed", task)


async def _worker_loop() -> None:
    """Background worker: polls queue, executes eligible tasks respecting concurrency limit."""
    global _worker_running  # noqa: PLW0603
    _worker_running = True
    log.info("TaskQueue worker started")
    try:
        while True:
            await asyncio.sleep(2)  # poll every 2 seconds
            try:
                if _count_running() >= BOUNDS.max_running_tasks:
                    continue

                # Pick next eligible task (QUEUED or APPROVED), highest priority first
                candidates = [
                    t for t in load_active_tasks()
                    if t["state"] in (TaskState.QUEUED, TaskState.APPROVED)
                ]
                if not candidates:
                    continue

                next_task = candidates[0]
                # Re-check it's still in eligible state (race condition guard)
                fresh = load_task(next_task["task_id"])
                if not fresh or fresh["state"] not in (TaskState.QUEUED, TaskState.APPROVED):
                    continue

                asyncio.ensure_future(_execute_task(fresh))

            except Exception:  # noqa: BLE001
                log.exception("worker_loop iteration error")
    finally:
        _worker_running = False
        log.info("TaskQueue worker stopped")


def start_worker() -> None:
    """Start the background worker. Called once at server startup. Safe to call multiple times."""
    global _worker_task  # noqa: PLW0603
    if _worker_task and not _worker_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
        _worker_task = loop.create_task(_worker_loop())
        log.info("TaskQueue worker task created")
    except RuntimeError:
        # No running event loop, for example during import-time test setup.
        pass


def stop_worker() -> None:
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()


def worker_status() -> dict:
    return {
        "running":       _worker_running,
        "active_tasks":  _count_active(),
        "running_tasks": _count_running(),
        "max_running":   BOUNDS.max_running_tasks,
        "max_queued":    BOUNDS.max_queued_tasks,
    }


# ── Prune ─────────────────────────────────────────────────────────────────────

def prune_old_tasks() -> int:
    """Remove terminal tasks older than BOUNDS.task_retention_days from the log.

    Rewrites the JSONL file keeping only relevant events.
    Returns number of tasks pruned.
    """
    from datetime import timedelta  # noqa: PLC0415
    cutoff = (datetime.now(timezone.utc) - timedelta(days=BOUNDS.task_retention_days)).isoformat()
    events = _load_all_events()
    tasks = _derive_tasks(events)

    keep_ids: set[str] = set()
    pruned = 0
    for tid, task in tasks.items():
        if task.get("state") in TERMINAL_STATES and (task.get("completed") or "") < cutoff:
            pruned += 1
        else:
            keep_ids.add(tid)

    if pruned == 0:
        return 0

    # Rewrite keeping only events for tasks we want to keep
    kept_events = [e for e in events if e.get("task_id") in keep_ids]
    QUEUE_FILE.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in kept_events) + ("\n" if kept_events else ""),
        encoding="utf-8",
    )
    log.info("task_queue pruned %d old tasks", pruned)
    return pruned


# ── Stats ─────────────────────────────────────────────────────────────────────

def queue_stats() -> dict[str, Any]:
    tasks = load_tasks()
    by_state: dict[str, int] = {}
    for t in tasks.values():
        s = t.get("state", "unknown")
        by_state[s] = by_state.get(s, 0) + 1

    pending_approval = [
        {"task_id": t["task_id"], "intent": t["intent"], "estimated_tokens": t["estimated_tokens"]}
        for t in tasks.values()
        if t.get("state") == TaskState.AWAITING_APPROVAL
    ]

    return {
        "total_tasks":      len(tasks),
        "by_state":         by_state,
        "active":           _count_active(),
        "pending_approval": pending_approval,
        "worker":           worker_status(),
        "queue_file":       str(QUEUE_FILE.relative_to(ROOT)) if QUEUE_FILE.is_relative_to(ROOT) else str(QUEUE_FILE),
    }
