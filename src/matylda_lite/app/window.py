"""Matylda Lab — natywne okno macOS (v0.6).

Uruchamia serwer FastAPI w tle i otwiera natywne okno WKWebView.
Na macOS używa WKWebView — ten sam silnik co Safari.

Użycie:
    python run.py --window
    python run.py --window --port 8080
"""
from __future__ import annotations

import json
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

PORT = 7474
SERVER_VERSION = "1.2"
# Cache file — zapisuje ścieżkę bieżącego Pythona dla .app bundle
_PYTHON_CACHE = Path(__file__).parent.parent.parent.parent.parent / ".python_path"
_READY_TIMEOUT = 12  # sekund


def _server_version(port: int = PORT) -> str | None:
    """Return the version of a responding local Matylda server, if any."""
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=1) as r:
            payload = json.loads(r.read())
            return str(payload.get("version")) if payload.get("ok") else None
    except Exception:  # noqa: BLE001
        return None


def _health_check(port: int = PORT) -> bool:
    """Sprawdź czy serwer już działa. Zwróć True jeśli OK."""
    return _server_version(port) is not None


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _select_server_port(preferred: int = PORT) -> int:
    """Reuse a current Lab server or reserve a nearby free local port.

    A stale Matylda process must not make a fresh desktop window attach to an
    incompatible API just because it happens to occupy port 7474.
    """
    for candidate in range(preferred, preferred + 10):
        if _server_version(candidate) == SERVER_VERSION:
            return candidate
    for candidate in range(preferred, preferred + 10):
        if _port_is_available(candidate):
            return candidate
    raise RuntimeError("Nie znaleziono wolnego portu dla Matylda Lab")


def _wait_for_server(port: int = PORT, timeout: float = _READY_TIMEOUT) -> bool:
    """Czekaj aż serwer wstanie. Zwróć True jeśli się doczekaliśmy."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _health_check(port):
            return True
        time.sleep(0.25)
    return False


def _start_server_thread(port: int = PORT) -> int:
    """Start the current Lab server and return the port it actually owns."""
    active_port = _select_server_port(port)
    if _server_version(active_port) == SERVER_VERSION:
        return active_port

    def _run() -> None:
        from ..server import start  # noqa: PLC0415
        start(port=active_port, open_browser=False, daemon=True)

    threading.Thread(target=_run, daemon=True, name="matylda-server").start()
    return active_port


def run_window(
    port: int = PORT,
    title: str = "Matylda Lab",
    width: int = 1280,
    height: int = 860,
    start_server: bool = True,
) -> None:
    """Uruchom natywne okno aplikacji macOS.

    Wymaga: pip install pywebview

    Args:
        port:         Port serwera FastAPI (domyślnie 7474).
        title:        Tytuł okna.
        width/height: Początkowe rozmiary okna.
        start_server: Jeśli True, uruchamia serwer w tle automatycznie.
    """
    try:
        import webview  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(
            "pywebview nie jest zainstalowany.\n"
            "Uruchom: pip install pywebview"
        ) from exc

    # Zapisz ścieżkę aktywnego Pythona — .app bundle użyje jej przy starcie
    try:
        _PYTHON_CACHE.write_text(sys.executable, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    active_port = port
    ready = _health_check(active_port) and _server_version(active_port) == SERVER_VERSION
    if start_server:
        active_port = _start_server_thread(port)
        ready = _wait_for_server(active_port, _READY_TIMEOUT)
        if not ready:
            print(f"[warn] Serwer nie odpowiedział po {_READY_TIMEOUT}s.")

    url = f"http://localhost:{active_port}/" if ready else (
        "data:text/html,<body style='font:16px -apple-system;padding:32px;background:%231c1b19;color:%23f5f4ee'>"
        "Matylda Lab nie uruchomila lokalnego serwera. Zamknij okno i sprobuj ponownie.</body>"
    )

    webview.create_window(
        title=title,
        url=url,
        width=width,
        height=height,
        min_size=(720, 520),
        resizable=True,
        text_select=False,
        confirm_close=False,
        background_color="#1c1b19",  # match Matylda Lab warm dark theme
    )

    webview.start(debug=False, private_mode=False)
