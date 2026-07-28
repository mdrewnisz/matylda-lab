"""Menu bar app dla macOS — Matylda Lab w tray.

Uruchomienie:
    python run.py --menubar        # serwer + menu bar (zalecane)
    python -m matylda_lite.app.menubar  # samo menu bar (zakłada że serwer już działa)

Wymagania: pip install rumps
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PORT = 7474
BASE = f"http://localhost:{PORT}"

# ── Ikony statusu ─────────────────────────────────────────────────────────────

ICON_ONLINE  = "M●"
ICON_OFFLINE = "M○"
ICON_BUSY    = "M…"


# ── API helper ────────────────────────────────────────────────────────────────

def _get(path: str, timeout: float = 2.0) -> dict | None:
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:  # noqa: BLE001
        return None


# ── App ───────────────────────────────────────────────────────────────────────

def run_menubar(start_server: bool = True) -> None:
    """Uruchom menu bar app. Blokuje wątek wywołujący (NSApp event loop)."""
    import rumps  # noqa: PLC0415

    if start_server:
        _start_server_thread()

    app = _MatyldaApp()
    app.run()


def _start_server_thread() -> None:
    """Uruchom uvicorn w wątku tła jeśli jeszcze nie działa."""
    if _get("/api/health") is not None:
        return  # już działa (np. LaunchAgent)

    def _run():
        from ..server import start  # noqa: PLC0415
        start(port=PORT, open_browser=False, daemon=True)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    # poczekaj aż serwer wstanie (max 8s)
    for _ in range(16):
        time.sleep(0.5)
        if _get("/api/health") is not None:
            break


# ── rumps App ─────────────────────────────────────────────────────────────────

class _MatyldaApp:
    """Wrapper — tworzy rumps.App i buduje menu."""

    def __init__(self):
        import rumps  # noqa: PLC0415
        self._rumps = rumps
        self._app   = rumps.App(ICON_ONLINE, quit_button=None)
        self._build_menu()
        self._timer = rumps.Timer(self._tick, 15)
        self._timer.start()

    def run(self):
        self._app.run()

    # ── Budowanie menu ─────────────────────────────────────────────────────────

    def _build_menu(self):
        rumps = self._rumps

        # ── Informacje ──
        self._item_status   = rumps.MenuItem("● online")
        self._item_threads  = rumps.MenuItem("Wątki: —")
        self._item_pending  = rumps.MenuItem("DARKROOM: —")
        self._item_model    = rumps.MenuItem("Model: —")

        # ── Główne akcje ──
        self._item_open     = rumps.MenuItem("Otwórz dashboard", callback=self._open_dashboard)
        self._item_restart  = rumps.MenuItem("Uruchom ponownie", callback=self._restart)

        # ── Sleeping Matylda ──
        self._item_sm_status = rumps.MenuItem("Sleeping Matylda: rozłączona")
        self._item_sm_status.set_callback(None)

        # ── Silo ──
        self._silo_items = self._build_silo_items()

        # ── Quit ──
        self._item_quit = rumps.MenuItem("Zatrzymaj Matyldę", callback=self._quit)

        self._app.menu = [
            self._item_status,
            self._item_threads,
            self._item_pending,
            self._item_model,
            None,
            self._item_open,
            None,
            "── Sleeping Matylda ──",
            self._item_sm_status,
            None,
            "── Silo ──",
            *self._silo_items,
            None,
            self._item_restart,
            self._item_quit,
        ]

        # Pierwsze wypełnienie danych
        self._update()

    def _build_silo_items(self) -> list:
        """Zbuduj pozycje menu dla 4 silo."""
        rumps = self._rumps
        items = []
        silos_data = _get("/api/silos")
        silos = silos_data.get("silos", []) if silos_data else []

        for i in range(1, 5):
            meta = next((s for s in silos if s.get("id") == f"silo_{i}"), {})
            name    = meta.get("name", f"Silo {i}")
            enabled = meta.get("enabled", False)
            label   = f"{'●' if enabled else '○'} {name}"
            item    = rumps.MenuItem(label)
            item.set_callback(None)   # wyłączone — placeholder
            items.append(item)

        return items

    # ── Callbacki ─────────────────────────────────────────────────────────────

    def _open_dashboard(self, _=None):
        webbrowser.open(f"{BASE}/")

    def _restart(self, _=None):
        self._app.title = ICON_BUSY
        self._item_status.title = "○ restartowanie…"

        def _do_restart():
            from .daemon import stop, start  # noqa: PLC0415
            stop()
            time.sleep(1)
            start()
            time.sleep(3)
            self._update()

        threading.Thread(target=_do_restart, daemon=True).start()

    def _quit(self, _=None):
        import rumps  # noqa: PLC0415
        # Nie zatrzymujemy serwera — LaunchAgent go utrzymuje
        # Zamykamy tylko menu bar app
        rumps.quit_application()

    # ── Timer tick ────────────────────────────────────────────────────────────

    def _tick(self, _=None):
        self._update()

    def _update(self):
        """Odśwież wszystkie pozycje menu danymi z API."""
        # Health
        health = _get("/api/health")
        online = health is not None

        self._app.title = ICON_ONLINE if online else ICON_OFFLINE
        self._item_status.title = "● online" if online else "○ offline"

        if not online:
            self._item_threads.title = "Wątki: —"
            self._item_pending.title = "DARKROOM: —"
            self._item_model.title   = "Model: —"
            return

        # Status
        status = _get("/api/status")
        if status:
            n_threads  = status.get("active_threads", 0)
            n_artifacts = len(status.get("artifacts", []))
            self._item_threads.title = f"Wątki: {n_threads}  ·  Artefakty: {n_artifacts}"

        # DARKROOM
        darkroom = _get("/api/darkroom")
        if darkroom:
            pending  = len(darkroom.get("pending_approvals", []))
            tensions = len(darkroom.get("active_tensions", []))
            epi      = darkroom.get("epistemic_limit_mode", {}).get("active", False)
            epi_mark = " ⚠ ELM" if epi else ""
            self._item_pending.title = (
                f"DARKROOM: {pending} approval{'s' if pending != 1 else ''}  "
                f"·  {tensions} napięć{epi_mark}"
            )

        # Sleeping Matylda
        sm = _get("/api/sleeping/status")
        if sm:
            connected = sm.get("connected", False)
            self._item_sm_status.title = (
                "Sleeping Matylda: ● połączona" if connected
                else "Sleeping Matylda: ○ rozłączona"
            )

        # Silo (odśwież nazwy jeśli się zmieniły)
        silos_data = _get("/api/silos")
        silos = silos_data.get("silos", []) if silos_data else []
        for i, item in enumerate(self._silo_items):
            meta    = next((s for s in silos if s.get("id") == f"silo_{i+1}"), {})
            name    = meta.get("name", f"Silo {i+1}")
            enabled = meta.get("enabled", False)
            item.title = f"{'●' if enabled else '○'} {name}"


# ── Standalone entry ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_menubar(start_server=True)
