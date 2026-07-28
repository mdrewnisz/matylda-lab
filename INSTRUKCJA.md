# Matylda Lab — Instrukcja obsługi v1.0

> Lokalny asystent epistemic. Działa w przeglądarce, dane zostają na Twoim dysku.

---

## Uruchomienie

```bash
cd "matylda lite"
python run.py                          # port 7474
# lub
matylda-lite                           # jeśli zainstalowane przez pip
```

Otwórz **http://localhost:7474** w przeglądarce.

Usługi wykonawcze w tle są domyślnie wyłączone. Włącz je świadomie przez
`python run.py --automation`.

---

## Układ interfejsu

```
┌──┬─────────────────┬──────────────────────────────┬─────────────┐
│  │  WĄTKI          │   Obszar czatu               │  DARKROOM   │
│💬│  Filtruj…       │                              │  (prawy     │
│  │  ─────────────  │   Wpisz zadanie…             │   panel)    │
│📚│  Aktywne (4)    │                              │             │
│  │  ▸ Wątek A      │                              │             │
│⚗ │  ▸ Wątek B      │                              │             │
│  │  ─────────────  │  [📎] [________________] [▶] │             │
│  │  PROJEKTY       │  [⊗]  [─────────────]  [✕] │             │
│  │                 │  [🌐 URL…] [💾 nazwa…]       │             │
│🔍│                 │  ▶ Narzędzia                 │             │
└──┴─────────────────┴──────────────────────────────┴─────────────┘
```

### Ribbon (lewy pasek)
| Ikona | Skrót | Funkcja |
|---|---|---|
| 💬 | ⌘1 | Praca — czat + wątki |
| 📚 | ⌘2 | Biblioteka — pełna lista wątków i dokumentów |
| ⚗ | ⌘3 | Analityka — DARKROOM, silosy, sesje |
| 🔍 | ⌘K | Szukaj (BM25 po wątkach, dokumentach, artefaktach) |

---

## Wątki

### Tworzenie wątku
- Kliknij **+** przy nagłówku WĄTKI → wpisz nazwę
- Przeciągnij plik `.md` / `.pdf` / `.txt` na sidebar → "Utwórz nowy wątek z tego pliku"

### Statusy wątku
| Status | Kolor | Znaczenie |
|---|---|---|
| **aktywny** | 🟢 zielony | Wątek wymaga uwagi AI |
| **zamrożony** | 🔵 niebieski | Zachowany, ale bez priorytetu AI |
| **biblioteka** | ⚫ szary | Durable, zamknięty |
| **canonical** | ⚫ szary | Wiedza referencyjna |

> ⚠️ Utrzymuj max **5 aktywnych** wątków — system wyświetla ostrzeżenie przy przekroczeniu.

### Freeze / Thaw
- Kliknij **❄** przy wątku → zamroź
- Kliknij **▶** przy zamrożonym wątku → odmroź
- Lub przez HTTP: `POST /api/library/threads/{stem}/set-status` z `{"status": "frozen"}`

### Filtrowanie
Pole **Filtruj wątki…** filtruje live po tytule i domenie.

### Eksport wątku
Kliknij **⬇** przy wątku:
| Format | Co zawiera |
|---|---|
| 📝 Polished Markdown | Czysty MD gotowy do publikacji |
| 📦 Research Bundle (ZIP) | MD + wszystkie dokumenty + artefakty |
| 🌐 Share HTML | Samodzielna strona HTML z przyciskiem powrotu |
| ⬇ Prosty ZIP | Surowy plik wątku |

### Dołączanie sekcji (Append)
Przy otwartym wątku → przycisk **📎 Do wątku** pod odpowiedzią AI dodaje sekcję do pliku `.md`.

---

## Czat

### Wysyłanie
- **⌘+Enter** lub kliknij **▶**
- Wpisz zadanie i wyślij — kontekst aktywnego wątku jest automatycznie dołączany

### Tryb NO-GO ⊗
Wciśnij **⊗** → pola wejściowego zmienia kolor. Wpisz hipotezę, którą chcesz zniszczyć. AI przechodzi w tryb falsyfikacji.

### Nowa rozmowa ✕
Kliknij **✕** → czyści historię czatu (wątki zostają).

### Pobieranie URL 🌐
Wpisz adres w pole **pobierz URL…** → ↓ pobiera surowy tekst, 📖 uruchamia reader mode (wyciąga artykuł bez reklam).

### Zapis pliku 💾
Wpisz nazwę w **zapisz jako…** i wyślij wiadomość — odpowiedź AI zostanie zapisana jako plik.

---

## Komendy slash

| Komenda | Efekt |
|---|---|
| `/briefing` | Wyświetl podsumowanie poranne (gap między sesjami, powiązania między wątkami) |
| `/briefing clear` | Zamknij kartę briefingu |

---

## Narzędzia badawcze

Kliknij **▶ Narzędzia** nad obszarem czatu, aby rozwinąć toolbar:

| Narzędzie | Opis |
|---|---|
| 📖 Mapa literatury | Generuje mapę źródeł i powiązań cytowań |
| ⊗ Stress-test | Falsyfikacja hipotezy — AI szuka słabych punktów |
| ⇌ Synteza | Łączy zaznaczone wątki w jeden dokument syntezy |
| ⎙ PDF | Drukuje/zapisuje widok jako PDF |
| ⚖ Porównaj modele | Uruchamia to samo zadanie na kilku modelach |

---

## Morning Briefing

Automatycznie pojawia się jeśli przerwa między sesjami wynosi **≥8 godzin**.

Zawiera:
- Liczbę godzin przerwy
- Powiązania tematyczne między wątkami (wspólne słowa kluczowe)
- Syntezę stanu projektu

Wymuś ręcznie: `/briefing` lub `GET /api/briefing?force=true`

---

## DARKROOM (System Health)

Prawy panel → sekcja **SYSTEM HEALTH**.

| Wskaźnik | Znaczenie |
|---|---|
| Active threads | Wątki ze statusem `active` |
| Frozen threads | Wątki ze statusem `frozen` |
| Complexity score | `active×2 + candidates×0.5 + insights×0.1` |
| Limit OK | Zielony jeśli aktywnych ≤ 5 |

---

## Skróty klawiszowe

| Skrót | Akcja |
|---|---|
| ⌘+Enter | Wyślij wiadomość |
| ⌘K | Otwórz wyszukiwarkę |
| ⌘N | Nowy wątek |
| ⌘1 | Widok: Praca |
| ⌘2 | Widok: Biblioteka |
| ⌘3 | Widok: Analityka |
| ⌘⇧S | Synteza zaznaczonych wątków |
| Escape | Zamknij otwarte okno dialogowe |

---

## Struktura plików

```
matylda lite/
├── library/
│   └── threads/          ← pliki wątków (.md)
│       └── archive/      ← zarchiwizowane wątki
├── data/
│   └── briefing_session.json
├── inbox/
│   └── raw_notes.md      ← surowe notatki do przetworzenia
├── artifacts/            ← wygenerowane pliki AI
├── logs/
│   └── chronicle.jsonl   ← historia sesji
└── src/matylda_lite/
    ├── server.py          ← API (FastAPI, port 7474)
    ├── dashboard.py       ← interfejs HTML
    ├── library_manager.py ← zarządzanie wątkami
    ├── briefing_manager.py← poranny briefing
    └── export_manager.py  ← eksport wątków
```

---

## API (dla zaawansowanych)

```
GET  /api/library/threads              → lista wątków
GET  /api/library/threads/{stem}       → treść wątku
POST /api/library/threads/create       → nowy wątek
POST /api/library/threads/{stem}/append         → dodaj sekcję
POST /api/library/threads/{stem}/set-status     → zmień status
POST /api/library/threads/archive      → archiwizuj
POST /api/library/threads/restore      → przywróć z archiwum

GET  /api/briefing                     → stan briefingu
GET  /api/briefing?force=true          → wymuś briefing
POST /api/briefing/mark-session        → zapisz timestamp sesji

GET  /api/health                       → wersja serwera
GET  /api/health/system                → metryki systemu

GET  /api/export/polished-md?stem=X    → eksport MD
GET  /api/export/share-html?stem=X     → eksport HTML
GET  /api/export/research-bundle?stem=X→ eksport ZIP
```

---

## Wskazówki

- **Jakość wątków > ilość.** Każdy aktywny wątek konsumuje okno kontekstu. 3–4 aktywne to optimum.
- **Freeze zamiast archiwum.** Zamrożony wątek zostaje dostępny w wyszukiwaniu, ale nie konsumuje uwagi AI.
- **Briefing poranny.** Przy dłuższych przerwach pozwól Matyldzie zebrać wątki — podsumowanie zajmuje <30 sekund.
- **Draft persist.** Niedokończona wiadomość zapisuje się w localStorage — wróć do niej po zamknięciu karty.
- **Toolbar badań domyślnie zwinięty.** Kliknij ▶ Narzędzia tylko gdy potrzebujesz — oszczędza przestrzeń.
- **Filtr wątków.** Wpisz fragment nazwy lub domeny — lista aktualizuje się na bieżąco.

---

*Matylda Lab v1.0 · lokalny · offline-first · 442 testy ✓*
