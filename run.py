#!/usr/bin/env python3
"""Matylda Lab — entry point.

Użycie:
    python run.py               # dev: serwer + otwiera przeglądarkę
    python run.py --menubar     # serwer + ikona w menu bar macOS
    python run.py --daemon      # background: bez przeglądarki i menu bar
    python run.py --port 8080   # inny port
    python run.py --host 0.0.0.0  # dostęp z sieci lokalnej
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


def main():
    parser = argparse.ArgumentParser(description="Matylda Lab")
    parser.add_argument("--menubar", action="store_true",
                        help="Uruchom z ikoną w menu bar macOS (wymaga: pip install rumps)")
    parser.add_argument("--daemon",  action="store_true",
                        help="Tryb tła: bez przeglądarki i menu bar")
    parser.add_argument("--window", action="store_true",
                        help="Uruchom jako natywna aplikacja macOS (wymaga: pip install pywebview)")
    parser.add_argument("--port",    type=int, default=7474,
                        help="Port (domyślnie: 7474)")
    parser.add_argument("--host",    type=str, default="localhost",
                        help="Host (domyślnie: localhost)")
    parser.add_argument("--automation", action="store_true",
                        help="Włącz opcjonalne workery tła (kolejka, watcher, Sleeping Matylda)")
    args = parser.parse_args()

    if args.window:
        from matylda_lite.app.window import run_window
        run_window(port=args.port, start_server=True)
    elif args.menubar:
        from matylda_lite.app.menubar import run_menubar
        run_menubar(start_server=True)
    else:
        from matylda_lite.server import start
        start(port=args.port, host=args.host,
              open_browser=not args.daemon, daemon=args.daemon,
              enable_automation=args.automation)


if __name__ == "__main__":
    main()
