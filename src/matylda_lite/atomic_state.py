"""atomic_state.py — race-safe JSON state file helpers.

Several modules (sleeping_matylda, homeostasis) follow a load→mutate→save
pattern on shared JSON files. Sleeping Matylda's background cycle runs in a
separate OS thread (via loop.run_in_executor), concurrently with HTTP request
handlers that can touch the same files (e.g. approve/dismiss/triage
endpoints). Plain `Path.write_text()` is not atomic — a writer that's
preempted mid-write can leave a truncated/corrupted file, and two writers
racing on read-modify-write can silently lose one side's update.

This module fixes both failure modes for state shared within one process:
  - Writes go to a temp file then `os.replace()` — atomic at the OS level,
    so no reader ever observes a partially-written file.
  - A per-path `threading.Lock` serializes the read-modify-write critical
    section so concurrent writers don't clobber each other.

It does NOT protect against multiple separate OS processes writing the same
path (e.g. two server instances) — that would need real file locking
(fcntl/flock). Today's architecture avoids that via the health-check-before-
start pattern in app/window.py, which keeps a single server instance alive.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path)
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


def atomic_write_json(path: Path, data: Any, **dump_kwargs: Any) -> None:
    """Write `data` as JSON to `path` atomically (temp file + os.replace).

    Safe to call concurrently from multiple threads on the same path —
    writes are serialized by a per-path lock.
    """
    dump_kwargs.setdefault("ensure_ascii", False)
    dump_kwargs.setdefault("indent", 2)
    lock = _lock_for(path)
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
        tmp_path.write_text(json.dumps(data, **dump_kwargs), encoding="utf-8")
        os.replace(tmp_path, path)


def update_json(path: Path, default: Any, mutate_fn: Callable[[Any], Any]) -> Any:
    """Read-modify-write `path` under a per-path lock, atomically.

    `mutate_fn(current_data) -> new_data` receives the current contents
    (or `default` if the file is missing/corrupt) and returns the value to
    persist. The whole read+mutate+write happens under one lock acquisition,
    so it's safe against the background-worker-vs-request-handler race this
    module exists to fix.

    Returns whatever `mutate_fn` returned (so callers can return derived
    values, e.g. a bool indicating whether anything changed).
    """
    lock = _lock_for(path)
    with lock:
        try:
            current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
        except Exception:  # noqa: BLE001
            current = default
        new_data = mutate_fn(current)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
        tmp_path.write_text(
            json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        os.replace(tmp_path, path)
        return new_data
