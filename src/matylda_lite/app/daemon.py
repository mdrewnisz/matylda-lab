"""Daemon management — start/stop/status Matylda Lab jako procesu tła.

PLACEHOLDER — implementacja w v0.3a.

Docelowo:
  - Zastąpienie http.server przez uvicorn (ASGI)
  - Obsługa SIGTERM dla graceful shutdown
  - PID file w ~/.matylda/matylda_lite.pid
  - Health check endpoint: GET /api/health

Użycie (docelowe):
    python -m matylda_lite.app.daemon start
    python -m matylda_lite.app.daemon stop
    python -m matylda_lite.app.daemon status
    python -m matylda_lite.app.daemon restart
"""
from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

from ..config import ROOT

# ── Konfiguracja ──────────────────────────────────────────────────────────────

PID_FILE  = Path.home() / ".matylda" / "matylda_lite.pid"
LOG_DIR   = Path.home() / ".matylda" / "logs"
PORT      = 7474
HOST      = "localhost"


# ── Status ────────────────────────────────────────────────────────────────────

def get_pid() -> int | None:
    """Odczytaj PID z pliku. Zwróć None jeśli nie istnieje lub proces martwy."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # sprawdź czy proces żyje
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        return None


def is_running() -> bool:
    return get_pid() is not None


def status() -> dict:
    pid = get_pid()
    return {
        "running": pid is not None,
        "pid":     pid,
        "port":    PORT,
        "url":     f"http://{HOST}:{PORT}",
    }


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start() -> None:
    """Uruchom serwer w tle.

    PLACEHOLDER — docelowo uruchamia uvicorn zamiast http.server.
    """
    if is_running():
        print(f"Matylda Lab już działa (PID {get_pid()})")
        return

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    import subprocess  # noqa: PLC0415

    # Znajdź run.py (src/matylda_lite/app/daemon.py → ../../.. = root)
    run_py = Path(__file__).parent.parent.parent.parent / "run.py"
    if not run_py.exists():
        print(f"Nie znaleziono run.py: {run_py}")
        return

    proc = subprocess.Popen(
        [sys.executable, str(run_py), "--daemon",
         "--host", HOST, "--port", str(PORT)],
        stdout=open(LOG_DIR / "stdout.log", "a"),
        stderr=open(LOG_DIR / "stderr.log", "a"),
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"Matylda Lab uruchomiona (PID {proc.pid}) → http://{HOST}:{PORT}/")


def stop() -> None:
    """Zatrzymaj serwer."""
    pid = get_pid()
    if pid is None:
        print("Matylda Lab nie działa")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        print(f"Matylda Lab zatrzymana (PID {pid})")
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        print("Proces już nie istniał")


def restart() -> None:
    stop()
    import time; time.sleep(1)  # noqa: E702
    start()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "restart":
        restart()
    elif cmd == "status":
        s = status()
        print(f"Running: {s['running']} | PID: {s['pid']} | URL: {s['url']}")
    else:
        print(f"Nieznana komenda: {cmd}. Użyj: start | stop | restart | status")
