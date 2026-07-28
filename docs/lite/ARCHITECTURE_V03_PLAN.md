# Matylda Lite — Plan architektury v0.3

_Data: 2026-05-10 · Status: plan_

---

## Problem z v0.2

Matylda Lite działa jako `python run.py` → `http.server.HTTPServer` na porcie 7474.

Ograniczenia:
- Blokuje terminal; kończy się przy zamknięciu okna
- Brak auto-startu przy logowaniu
- Brak integracji z systemem operacyjnym (powiadomienia, tray, sleep/wake)
- Brak IPC — inne procesy (Sleeping Matylda) nie mają jak się podpiąć
- Brak mechanizmu silo — każde nowe rozszerzenie modyfikuje monolityczny `server.py`

---

## Cel v0.3

```
Matylda Lite jako samodzielna aplikacja:
- działa w tle bez terminala
- startuje automatycznie przy logowaniu (macOS LaunchAgent)
- ma ikonę w menu bar (status, start/stop, otwórz)
- udostępnia stabilne IPC dla Sleeping Matylda
- przyjmuje silosy jako pluginy bez ingerencji w core
```

---

## Warstwa 1 — Daemon (priorytet: wysoki)

### 1.1 Zamiana http.server → uvicorn

Obecny `http.server.HTTPServer` zastępujemy `uvicorn` + `FastAPI` (lub Starlette).

Powody:
- `http.server` to single-request-at-a-time (nawet z ThreadingMixIn ma ograniczenia)
- uvicorn obsługuje WebSocket (potrzebne przy real-time Sleeping Matylda)
- FastAPI daje automatyczne generowanie schematów, łatwiejsze routery dla silo
- Graceful shutdown przez SIGTERM (LaunchAgent tego wymaga)

Migracja jest mechaniczna — każdy `_handle_*` staje się `@router.get` / `@router.post`.

### 1.2 macOS LaunchAgent

Plik `~/Library/LaunchAgents/com.matylda.lite.plist`:

```xml
<key>Label</key><string>com.matylda.lite</string>
<key>ProgramArguments</key>
<array><string>/path/to/python</string><string>run.py</string></array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>~/.matylda/logs/stdout.log</string>
<key>StandardErrorPath</key><string>~/.matylda/logs/stderr.log</string>
```

`launchctl load` / `unload` jako mechanizm start/stop.

### 1.3 Menu bar app (rumps)

`src/matylda_lite/app/menubar.py` — ikona w menu bar macOS:

```
● Matylda Lite  [ikona]
├── Status: online | model: sonnet | wątki: 7
├── Otwórz dashboard
├── ────────────────
├── Sleeping Matylda: [aktywna / uśpiona]   ← placeholder
├── ────────────────
├── Silo 1: [nazwa]    ← placeholder
├── Silo 2: [nazwa]    ← placeholder
├── Silo 3: [nazwa]    ← placeholder
├── Silo 4: [nazwa]    ← placeholder
├── ────────────────
└── Zatrzymaj / Uruchom ponownie
```

Zależność: `rumps` (MIT, macOS only, 100% Python).

---

## Warstwa 2 — IPC dla Sleeping Matylda (priorytet: średni)

### 2.1 Architektura IPC

Sleeping Matylda (główny projekt) ↔ Matylda Lite przez:

```
Unix domain socket: /tmp/matylda_lite.sock
  lub
WebSocket endpoint: ws://localhost:7474/ws/sleeping
```

Protokół: JSON over socket.

```json
// Sleeping Matylda → Lite
{"type": "wake", "context": "...", "task": "..."}
{"type": "push_insight", "content": "...", "topic": "..."}
{"type": "sync_request"}

// Lite → Sleeping Matylda
{"type": "ack", "id": "..."}
{"type": "sync_response", "threads": [...], "insights": [...]}
{"type": "alert", "message": "..."}
```

### 2.2 Placeholders w v0.3

- `src/matylda_lite/sleeping_matylda/bridge.py` — socket listener / WebSocket handler
- `src/matylda_lite/sleeping_matylda/protocol.py` — definicje typów wiadomości
- `src/matylda_lite/sleeping_matylda/sync.py` — logika synchronizacji stanu
- `GET /api/sleeping/status` — endpoint statusu połączenia
- `POST /api/sleeping/push` — endpoint do wstrzyknięcia kontekstu z Sleeping Matylda

---

## Warstwa 3 — Architektura silo (priorytet: średni)

### 3.1 Interfejs silo

Każdy silo to pakiet Python z obowiązkowym `__init__.py`:

```python
# Minimalna struktura silo
SILO_META = {
    "id": "silo_N",
    "name": "Nazwa Silo",           # wyświetlana w menu bar i dashboard
    "version": "0.1",
    "enabled": False,               # domyślnie wyłączony
    "description": "...",
    "data_dir": "data/silos/silo_N/",
    "api_prefix": "/api/silo_N",
}

def get_router():
    """Zwróć FastAPI router z endpointami silo."""
    raise NotImplementedError

def get_dashboard_widget() -> str:
    """Zwróć HTML string widgetu do dashboardu (opcjonalne)."""
    return ""

def on_startup():
    """Inicjalizacja przy starcie serwera (opcjonalne)."""
    pass

def on_shutdown():
    """Cleanup przy zamknięciu (opcjonalne)."""
    pass
```

### 3.2 Auto-discovery

Server przy starcie skanuje `src/matylda_lite/silos/*/`:
```python
for silo_dir in silos_root.iterdir():
    if (silo_dir / "__init__.py").exists():
        meta = import_silo(silo_dir).SILO_META
        if meta["enabled"]:
            app.include_router(get_router(), prefix=meta["api_prefix"])
```

### 3.3 Cztery silo (placeholdery)

| ID | Nazwa | Status |
|----|-------|--------|
| silo_1 | [do zdefiniowania] | placeholder |
| silo_2 | [do zdefiniowania] | placeholder |
| silo_3 | [do zdefiniowania] | placeholder |
| silo_4 | [do zdefiniowania] | placeholder |

Każdy silo ma katalog `src/matylda_lite/silos/silo_N/` z:
- `__init__.py` — meta + interfejs
- `router.py` — endpointy API (puste)
- `widget.py` — fragment dashboardu (pusty)
- `README.md` — opis przeznaczenia (do wypełnienia)
- `data/` — katalog danych silo

---

## Sekwencja migracji

```
v0.2 (teraz)
  └─ http.server + run.py w terminalu

v0.3a — Daemon
  └─ uvicorn zamienia http.server
  └─ LaunchAgent: auto-start przy logowaniu
  └─ run.py zostaje jako entry point

v0.3b — Menu bar
  └─ rumps: ikona w tray
  └─ Placeholdery silo widoczne w menu
  └─ Sleeping Matylda slot w menu (disabled)

v0.3c — IPC
  └─ Unix socket / WebSocket endpoint
  └─ Protokół zdefiniowany, implementacja po stronie Sleeping Matylda
  └─ /api/sleeping/* endpointy aktywne

v0.3d — Silo activation
  └─ Pierwsze silo wypełnione i aktywowane
  └─ Dashboard widget silo widoczny
```

---

## Zależności do dodania (requirements.txt)

```
# v0.3
uvicorn[standard]>=0.30
fastapi>=0.111
rumps>=0.4          # menu bar (macOS only)
websockets>=12      # IPC WebSocket
```

---

## Co NIE zmienia się

- Wszystkie pliki `darkroom/`, `library/`, `memory/`, `desk/` — bez zmian
- `secretary.py`, `memory_manager.py`, `docs_manager.py` — bez zmian
- Dashboard HTML/JS — bez zmian (serwowany przez uvicorn tak samo jak teraz)
- `.env` + `config.py` — bez zmian
- Git repo — bez zmian

Migracja dotyczy tylko warstwy transportowej i uruchamiania. Core jest stabilny.
