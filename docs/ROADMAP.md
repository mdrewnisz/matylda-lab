# Historical: Matylda Lite Roadmap v1.1

> Historyczny zapis stanu Lite z maja 2026. Bieżący kierunek opisuje
> `MATYLDA_LAB_CHARTER.md`; ten dokument nie jest aktywną roadmapą.
> v1.0: 2026-05-19 | v1.1: 2026-05-19 (rewizja po recenzji architektonicznej)

---

## Stan obecny (v0.3f, maj 2026)

**Zbudowane:**
- Thread-based research flow (statusy: aktywny / zamrożony / biblioteka / canonical)
- UCB1 model router — haiku/sonnet/opus z uczeniem na podstawie historii wywołań
- Streaming chat z auto-injekcją kontekstu aktywnego wątku
- DARKROOM — review + confidence topology po każdej odpowiedzi
- Web fetch + reader mode, tryb NO-GO (falsyfikacja), synteza multi-wątek
- Silosy domenowe, BM25 full-text search, morning briefing
- Conversation persistence — localStorage + seamless przełączanie wątków
- Background stream detach — przełączenie wątku nie przerywa odpowiedzi API

**Luka wobec stanu sztuki (2026):**

| Obszar | Stan obecny | Cel |
|---|---|---|
| Pamięć | Płaskie JSONL, brak struktury | Four-tier (episodic → semantic → procedural → negative) |
| Inicjatywa | Reaktywna (odpowiada) | Proaktywna (monitoruje, sugeruje, zapomina) |
| Retrieval | BM25 | BM25 + embeddingi + typowany graf |
| Uwaga | Nieograniczona, flat | Budżet uwagi, homeostaza, selekcja |
| Współbieżność | Jeden agent na żądanie | Async queue → Approval Gate → opcjonalnie subagenci |

---

## Trendy definiujące kierunek

| Trend | Źródło | Implikacja dla Matyldy |
|---|---|---|
| **Four-tier memory** (episodic → semantic → procedural → negative) | Mem0, MAGMA, MemArchitect 2025–2026 | Rozbudowa `memory/` o warstwę błędów |
| **Proaktywni agenci z budżetem uwagi** | Stanford HAI AI Index 2026 | Homeostaza zanim Thread Watcher |
| **Hybrid retrieval** (BM25 + wektory + typowany graf) | Mem0, Zylos Research 2026 | Graf z relacjami i confidence, nie flat linki |
| **Bounded multi-agent** — agenty z wąskimi interfejsami | Anthropic Research System, arXiv 2601.12542 | Subagenci po task queue, nie przed |
| **Controlled forgetting** — systemy poznawcze, nie archiwa | cognitive science, PASK 2604.08000 | Konsolidacja diary → refleksje → reguły |
| **Agentualność z nadzorem** | PASK arXiv 2604.08000 | Approval Gate jako pierwsza warstwa autonomii |

---

## Filozofia architektury

Typowa agentowa roadmap wygląda:
```
więcej modeli → więcej agentów → więcej autonomii
```

Ta wygląda inaczej:
```
więcej pamięci → więcej krytyki → więcej selekcji → kontrolowane zapominanie
```

Dwie zasady, które z tego wynikają:

**1. Co nie działa = osobny typ wiedzy**
Refuted theories są często bardziej informatywne niż confirmed ones.
`negative/` memory nie jest "złym końcem spektrum" — to oddzielna warstwa.

**2. Pamięć bez zapominania to archiwum**
System poznawczy ma salience, recency, relevance.
Archiwum ma tylko search.
Matylda powinna być systemem, nie archiwum.

---

## Faza 1 — Pamięć i kontekst (v0.4) ✅ POTWIERDZONA

> Cel: Matylda pamięta między sesjami i rozumie własną bazę wiedzy — w tym błędy.

### 1.1 Four-tier memory

```
memory/
├── diary/          ← episodic: raw session observations
│   └── YYYY-MM-DD.jsonl
├── reflections/    ← semantic: patterns extracted from diary
│   └── YYYY-WW.md
├── rules/          ← procedural: co działa (edytowalne przez użytkownika)
│   └── rules.md
└── negative/       ← negative: co nie działa — osobny typ wiedzy
    ├── failed_assumptions.md
    ├── no_go_patterns.md
    └── hallucination_patterns.md
```

**Negative memory — dlaczego osobna warstwa:**
- Wymaga innej walidacji niż pozytywna wiedza
- Musi zawierać: *co* się nie sprawdziło + *pod jakimi warunkami* + *czy warunki nadal obowiązują*
- Jest specyficzna dla użytkownika i kontekstu (model ogólny tego nie zastąpi)
- Przy badaniach bywa cenniejsza niż lista tego, co działa

### 1.2 Diary (warstwa episodyczna)

Structured `diary_entry` po każdej sesji:
```jsonl
{
  "date": "...",
  "thread_stem": "...",
  "query_summary": "...",
  "key_finding": "...",
  "open_questions": [...],
  "contradicts": [...],
  "model_used": "..."
}
```
- Pole `contradicts` — jawne oznaczenie gdy wynik obala wcześniejsze założenie
- Morning briefing czyta diary → real refleksja, nie odliczanie godzin

### 1.3 Reflections — z progiem pewności

Tygodniowy job: haiku analizuje diary entries → szuka wzorców

**Safeguard anty-narracyjny:**
- Wzorzec tworzony tylko gdy `occurrences >= 3` w oknie czasowym
- Każda refleksja wymaga kontrprzykładu: "przypadki, gdy wzorzec NIE zadziałał"
- Jeśli model nie może wymienić kontrprzykładu → refleksja flagowana jako `low_confidence`
- `low_confidence` refleksje nie są injektowane do systemu promptu

Wyniki: `memory/reflections/YYYY-WW.md`

### 1.4 Controlled forgetting — konsolidacja

```
Diary entries (raw episodic, szczegółowe)
    → po 30 dniach: konsolidacja do refleksji
    → diary przechodzi w "low-weight archive" (nie ładowane aktywnie)
    → refleksje → po 90 dniach: ekstrakcja reguł do rules.md
    → refleksje archiwizowane
    → rules.md: edytowalny przez użytkownika, auto-injektowany (<500 tokenów)
```

**Zasada:** Matylda nie kasuje — archiwizuje z obniżonym salience. Dostęp na żądanie, nie automatyczny.

### 1.5 Document Index (RAG)

- Chunking wątków i plików → SQLite FTS5 + opcjonalnie `sqlite-vec` embeddingi
- `GET /api/search?q=X&mode=hybrid` (BM25 + semantic)
- Auto-inject najwyżej scorowanych fragmentów przed wysłaniem do API

**KPI:** Briefing zawiera real recall z diary; `occurrences < 3` blokuje refleksje; precision@5 > 0.7

---

## Faza 1.5 — Homeostaza (v0.4.5) ✅ POTWIERDZONA

> Cel: budżet uwagi zanim Matylda zacznie rosnąć. Architektura poznawcza potrzebuje limitów.

```
/homeostasis/
├── active_goals.json      ← co jest aktualnie śledzone
├── attention_budget.json  ← ile "uwagi" zostało
├── stale_items.json       ← co traci priorytet
└── fatigue.json           ← co jest nadmiernie aktywne
```

### Reguły homeostazy

| Reguła | Wartość domyślna | Konfigurowalna |
|---|---|---|
| Max aktywnych wątków | 5 | tak |
| Max równoległych zadań | 3 | tak |
| Stale threshold | 7 dni bez aktywności | tak |
| Fatigue threshold | >10 zapytań/tydzień na wątek → priorytet -20% | tak |

### Mechanizm priorytetyzacji

```python
priority_score = (
    recency_score * 0.4        # kiedy ostatnio dotykany
  + activity_score * 0.3       # ile aktywności
  + open_questions_count * 0.2 # ile otwartych pytań
  - fatigue_penalty * 0.1      # nie za bardzo aktywny
)
```

Stale items: propozycja freeze (nie automatyczne zamrożenie — approval gate).

**Dlaczego to jest przed Thread Watcherem:**
Thread Watcher bez homeostazy może sam produkować noise — "zajmij się X" gdy X jest stale z dobrego powodu.

**KPI:** Zero "zombie active threads" (aktywny wątek bez aktywności > 14 dni bez świadomej decyzji)

---

## Faza 2 — Agentualność pasywna (v0.5) ⬜ DO DYSKUSJI

> Cel: Matylda monitoruje i sugeruje — homeostaza jako filtr, nie wszystko staje się alert.

### 2.1 Thread Watcher (z homeostazą jako filtrem)

- Background: co 24h skan aktywnych wątków
- Warunek alertu: stale_items.json zawiera wątek + priorytet poniżej threshold
- UI: żółty chip w ribbonie — max 3 sugestie jednocześnie (attention budget)
- Sugestia zawiera: "Wątek X, 9 dni bez aktywności. Propozycja: [freeze] [zbadaj Y] [ignoruj 7 dni]"

### 2.2 Proaktywne powiązania

- Po `done` evencie: haiku sprawdza semantic overlap z innymi wątkami
- Próg: `similarity > 0.75` + oba wątki aktywne
- Nie produkuje alertu jeśli attention_budget wyczerpany

### 2.3 Knowledge Graph — typowane relacje z confidence

Nie flat linki — typed relationships:

```
FTAR
    └── contradicts(0.91) ── scalar_pump
    └── extends(0.72) ────── field_theory
    └── cites(1.0) ──────── source_paper

Matylda
    └── extends(0.82) ────── memory_system_v0
    └── failed_approach(0.95) ── flat_embedding_store
```

Format `data/entities.jsonl`:
```jsonl
{
  "entity": "FTAR",
  "thread_stem": "ftar_main",
  "relations": [
    {"type": "contradicts", "target": "scalar_pump", "confidence": 0.91, "date": "..."},
    {"type": "extends", "target": "field_theory", "confidence": 0.72, "date": "..."}
  ]
}
```

Typy relacji: `contradicts | extends | cites | refutes | supports | depends_on | failed_approach`

- Confidence propaguje się przez graf (jeśli A contradicts B z 0.9 i B supports C z 0.8 → A weakens C z 0.72)
- Graf jest aktualizowany gdy przychodzi nowe `done` — nie budowany jednorazowo

### 2.4 Background Synthesis

- `POST /api/tasks/synthesize` — do task queue, nie blokuje UI
- Wynik: notyfikacja + plik w `artifacts/`

**KPI:** Graf ma typed relations; Thread Watcher produkuje max 3 alerty/dzień

---

## Faza 3 — Autonomia (v0.6) ⬜ DO DYSKUSJI

> Cel: async tasks i approval gate ZANIM pojawią się subagenci.
> Reordering względem v1.0: Task Queue → Approval Gate → opcjonalnie subagenci.

### 3.1 Task Queue (najpierw)

- `data/task_queue.jsonl` — persystentna kolejka
- Worker: asyncio background, pobiera i wykonuje
- UI: log w DARKROOM, interrupt/resume
- Każde zadanie ma: `intent`, `estimated_tokens`, `approval_required: bool`

### 3.2 Approval Gate (przed subagentami)

Przed każdą autonomiczną akcją:
```
┌─────────────────────────────────────────────┐
│ Matylda zamierza:                           │
│ Zapisać wynik syntezy jako:                 │
│ artifacts/SYNTHESIS_FTAR_2026-05-19.md      │
│                                             │
│ [Zatwierdź] [Zmień nazwę] [Anuluj]         │
└─────────────────────────────────────────────┘
```
Zasada: "Zamierzam zrobić X" — nie "już zrobiłam X".

### 3.3 Subagenci (po Task Queue i Approval Gate)

Dopiero gdy infrastruktura async działa i approval gate jest przetestowany:

| Agent | Model | Rola | Interfejs |
|---|---|---|---|
| **Orchestrator** | sonnet | Dekomponuje, przydziela | Wąskie, bounded — list of tasks |
| **Researcher** | sonnet + web | Zbiera materiały | Zwraca: sources + findings |
| **Reviewer** | opus | Falsyfikacja, stress-test | Zwraca: issues + confidence |
| **Synthesizer** | sonnet | Łączy wyniki | Zwraca: draft + open_questions |

**Safeguard anty-dryfowy:**
- Każdy subagent ma max_tokens na turę
- Orchestrator nie może delegować więcej niż 3 subzadania jednocześnie (attention_budget)
- Jeśli subagent zwraca wynik sprzeczny z negative/memory → automatyczny flag do review

**KPI:** Task Queue działa bez subagentów; subagenci dodani tylko gdy queue przetestowany

---

## Faza 4 — Semantyczny backend (v0.7) ⬜ DO DYSKUSJI

> Cel: retrieval klasy produkcyjnej, pamięć wielowarstwowa z propagacją pewności.

### 4.1 Lokalny embedding store

- `sentence-transformers` `all-MiniLM-L6-v2` (~80 MB, CPU)
- SQLite + `sqlite-vec` — bez zewnętrznych zależności
- Inkrementalny update; rebuild na żądanie

### 4.2 Hybrid retrieval

```
score = 0.6 × BM25 + 0.4 × cosine_similarity
```
Negatywna pamięć ma ujemny wkład:
```
score -= 0.3 × negative_memory_overlap
```
Wyniki z `negative/` sygnalizowane inaczej w UI — nie blokują, ale ostrzegają.

### 4.3 Memory consolidation pipeline

```
Diary (raw, 30-dniowe okno)
    → haiku → Reflections (occurrences ≥ 3, z kontrprzykładem)
        → sonnet → Rules (memory/rules.md)
            → diary archiwizowane (low-weight, dostęp na żądanie)

Reflections starsze niż 90 dni → archiwizowane
Rules: edytowalne przez użytkownika, auto-injektowane
```

### 4.4 Temporal graph

- `GET /api/graph/timeline?stem=X` → historia ewolucji wątku z diff confidence
- Briefing: "FTAR zmienił relationship z scalar_pump z supports na contradicts w ciągu 2 tygodni"

**KPI:** Hybrid retrieval precision@5 > 0.85; negative memory widoczny w wynikach search

---

## Faza 5 — Otwarty ekosystem (v0.8+) ⬜ DO DYSKUSJI

> Cel: Matylda jako węzeł — otwarta na inne narzędzia, nie izolowana.

### 5.1 Lokalne modele (Ollama)

- `config.yaml`: `provider: anthropic | ollama`
- Mapowanie: haiku → `llama3.2:3b`, sonnet → `llama3.1:8b`, opus → `llama3.3:70b`
- UCB1 uczy się osobno per provider
- Offline-capable baseline

### 5.2 MCP Server

- Matylda eksponuje wątki jako MCP resources
- `GET /mcp/threads`, `GET /mcp/threads/{stem}`, `POST /mcp/threads/{stem}/append`
- Negative memory eksponowana jako read-only (inne agenty mogą ostrzegać, nie zapisywać)

### 5.3 Plugin system

- `plugins/` directory, hot-reload, `register_routes(app)` + `register_tools(toolbar)`
- Przykłady: `plugin_zotero`, `plugin_arxiv_watcher`, `plugin_calendar`

---

## Sleeping Matylda — rozszerzony cykl

Obecny cykl:
```
observe → compare → doubt → connect
```

Po tej roadmapie:
```
observe → compare → doubt → connect → forget
```

**Forget** nie oznacza kasowania:
- Specific diary entries konsolidują się w refleksje (zapominanie szczegółów, zapamiętywanie wzorców)
- Refleksje archiwizowane po ekstrakcji reguł
- Negative memory nigdy nie jest kasowane — archiwizowane z datą i warunkami
- Po 1 roku: Matylda ma reguły i wzorce, nie terabajty dzienników

---

## Zasady projektowe (niezmienne)

| Zasada | Znaczenie |
|---|---|
| **Local-first** | Dane na dysku użytkownika, nigdy w chmurze bez zgody |
| **Agentualność z nadzorem** | Matylda proponuje, użytkownik zatwierdza |
| **Epistemic integrity** | DARKROOM + NO-GO + negative memory jako rdzeń |
| **Homeostaza przed skalowaniem** | Budżet uwagi musi być przed dodawaniem agentów |
| **Bounded interfaces** | Każdy agent/moduł ma wąski, zdefiniowany interfejs |
| **Forget by design** | Konsolidacja pamięci — system poznawczy, nie archiwum |
| **Minimalizm UI** | Nowe elementy UI muszą uzasadnić swoją obecność |

---

## Harmonogram (zaktualizowany)

```
v0.4    Q3 2026   Four-tier memory, diary, reflections z progiem, RAG  ✅ POTWIERDZONA
v0.4.5  Q3 2026   Homeostaza — budżet uwagi, reguły selekcji          ✅ POTWIERDZONA
v0.5    Q4 2026   Thread Watcher (z homeostazą), typowany graf         do dyskusji
v0.6    Q1 2027   Task Queue → Approval Gate → opcjonalnie subagenci   do dyskusji
v0.7    Q2 2027   Hybrid retrieval, temporal graph, consolidation      do dyskusji
v0.8    Q3 2027+  Ollama, MCP server, plugin system                    do dyskusji
```

---

## Źródła i inspiracje

- [Agentic Knowledge Management: The Next Evolution of PKM](https://www.dsebastien.net/agentic-knowledge-management-the-next-evolution-of-pkm/)
- [State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [How Anthropic built its multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [PASK: Toward Intent-Aware Proactive Agents with Long-Term Memory](https://arxiv.org/pdf/2604.08000)
- [5 Key Trends Shaping Agentic Development in 2026](https://thenewstack.io/5-key-trends-shaping-agentic-development-in-2026/)
- [AI Agent Memory Architectures: From Context Windows to Persistent Knowledge](https://zylos.ai/research/2026-04-05-ai-agent-memory-architectures-persistent-knowledge)
- [Rethinking Interactive Multi-Agent Workflows for Scientific Discovery](https://arxiv.org/pdf/2601.12542)

---

*Matylda Lite Roadmap v1.1 · rewizja po recenzji architektonicznej · 2026-05-19*
*local-first · epistemic-first · forget by design*
