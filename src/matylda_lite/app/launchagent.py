"""Instalacja/deinstalacja macOS LaunchAgent dla Matylda Lab.

PLACEHOLDER — implementacja w v0.3a.

LaunchAgent startuje Matyldę przy logowaniu użytkownika
i restartuje ją jeśli crashuje (KeepAlive=true).

Użycie (docelowe):
    python -m matylda_lite.app.launchagent install
    python -m matylda_lite.app.launchagent uninstall
    python -m matylda_lite.app.launchagent status
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LABEL          = "com.matylda.lite"
PLIST_DIR      = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH     = PLIST_DIR / f"{LABEL}.plist"
LOG_DIR        = Path.home() / ".matylda" / "logs"
HOST           = "localhost"
PORT           = 7474

PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{run_py}</string>
        <string>{mode}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ThrottleInterval</key>
    <integer>30</integer>

    <key>StandardOutPath</key>
    <string>{log_dir}/stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{log_dir}/stderr.log</string>

    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
</dict>
</plist>
"""


def _find_run_py() -> Path:
    """Znajdź run.py względem tego modułu."""
    # src/matylda_lite/app/launchagent.py → ../../.. = root
    return Path(__file__).parent.parent.parent.parent / "run.py"


def install(menubar: bool = True) -> None:
    """Zainstaluj LaunchAgent.

    Args:
        menubar: True → uruchom z ikoną w menu bar (domyślnie);
                 False → uruchom w trybie daemon (bez UI)
    """
    run_py = _find_run_py()
    if not run_py.exists():
        print(f"Nie znaleziono run.py: {run_py}")
        return

    # Sprawdź czy rumps dostępny jeśli tryb menubar
    if menubar:
        try:
            import rumps  # noqa: F401
        except ImportError:
            print("rumps nie zainstalowany — przełączam na --daemon")
            print("Aby zainstalować: pip install rumps")
            menubar = False

    PLIST_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    mode = "--menubar" if menubar else "--daemon"
    plist = PLIST_TEMPLATE.format(
        label=LABEL,
        python=sys.executable,
        run_py=str(run_py),
        mode=mode,
        log_dir=str(LOG_DIR),
        working_dir=str(run_py.parent),
    )

    PLIST_PATH.write_text(plist, encoding="utf-8")
    print(f"Zapisano: {PLIST_PATH}")

    result = subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"LaunchAgent załadowany: {LABEL}")
        print(f"Matylda Lab startuje automatycznie przy logowaniu → http://{HOST}:{PORT}/")
    else:
        print(f"Błąd ładowania LaunchAgent: {result.stderr.strip()}")
        print(f"Ręcznie: launchctl load {PLIST_PATH}")


def uninstall() -> None:
    """Odinstaluj LaunchAgent."""
    if not PLIST_PATH.exists():
        print("LaunchAgent nie zainstalowany")
        return

    subprocess.run(["launchctl", "unload", str(PLIST_PATH)],
                   capture_output=True)
    PLIST_PATH.unlink()
    print(f"LaunchAgent usunięty: {LABEL}")


def status() -> None:
    """Sprawdź status LaunchAgent."""
    installed = PLIST_PATH.exists()
    print(f"Plik plist: {'istnieje' if installed else 'brak'} ({PLIST_PATH})")
    if installed:
        result = subprocess.run(
            ["launchctl", "list", LABEL],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"LaunchAgent aktywny:\n{result.stdout}")
        else:
            print("LaunchAgent nie jest załadowany (użyj: launchctl load ...)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "install":
        install()
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "status":
        status()
    else:
        print(f"Nieznana komenda: {cmd}. Użyj: install | uninstall | status")
