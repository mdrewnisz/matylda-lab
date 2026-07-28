# First Workflow Postmortem — Matylda Lite v0.1

_Data: 2026-05-10 · Autorstwo: operacyjne (nie techniczne)_

---

## Kontekst

Dokument nie jest przeglądem kodu. Jest przeglądem **tego, jak system zachował się w pracy** — gdzie pomógł, gdzie zaczął puchnąć, które mechanizmy były uczciwe, a które dekoracyjne.

Zakres: od pierwszego uruchomienia systemu do zamknięcia cyklu scalar pump + implementacja roadmapy v1.

---

## Co zadziałało

### 1. DARKROOM jako hamulec narracyjny

Najważniejszy wynik operacyjny: system potrafił **zawęzić własny claim zamiast go pompować**.

Konkretnie: scalar pump zaczął jako potencjalny no-go theorem, przeszedł hostile review, i wylądował jako *wewnętrzny artefakt diagnostyczny* — nie jako paper. To jest rzadkie. Większość środowisk AI-wspomaganego pisania generuje coraz bardziej elokwentne wersje tego samego overclaima.

Mechanizmy, które na to pozwoliły:
- hostile reviewer jako osobna rola (nie jedna z pięciu głosów, ale osobny tryb NO-GO)
- `SCALAR_PUMP_NO_GO_HOSTILE_REVIEW.md` — dokument, który wprost wypisał failure modes zanim stały się nawykiem
- parking criteria w wątku: *"Park if it cannot be stated without overclaiming"*

### 2. Tensions zamiast moderation

TENSIONS jako format okazały się lepsze niż ogólny scoring. Nie mówią "odpowiedź była zła" — mówią "to konkretne napięcie jest nierozwiązane". To pozwala wrócić do niego po czasie.

24 aktywne napięcia po kilku sesjach to nie problem — to normalny stan pracy badawczej. Problemem byłoby zero.

### 3. Wątki jako jednostka pamięci (nie rozmowa)

Decyzja żeby pamięć była na poziomie wątku, nie sesji czatu, okazała się słuszna. Czat jest efemeryczny — wątek ma ciągłość. Szczególnie przydatne przy scalar pump: każda sesja mogła zacząć od `=== WĄTEK: ftar_scalar_pump_no_go ===` i miała pełny kontekst bez streszczania.

### 4. Persona jako regulator stylu, nie estetyczny gadget

PERSONA_MATYLDA_LITE.md zadziałała konkretnie: `Szóstka` (odmowa spekulowania) pojawiła się realnie przy kilku promptach gdzie odpowiedź mogła dryfować. Nie jako deklaracja — jako rzeczywista interwencja w output.

---

## Gdzie system zaczął puchnąć

### 1. Liczba artefaktów vs ich użyteczność

6 artefaktów po pierwszym cyklu. Uczciwa ocena:

| Artefakt | Użyteczny? |
|----------|-----------|
| `SCALAR_PUMP_NO_GO_HOSTILE_REVIEW.md` | **tak** — realnie zawęził scope |
| `SCALAR_PUMP_NO_GO_NOTE.md` | **tak** — dobry draft, wymaga dalszej pracy |
| `LITERATURA_test_2026-05-10.md` | **nie** — test systemu, nie zawartość |
| `DARKROOM_EPISTEMOLOGY_ANALYSIS.md` | **częściowo** — meta-analiza przydatna jednorazowo |
| `test.md` | **nie** — artefakt testowy |
| `dashboard.html` | **nie** — techniczny relikt |

Wniosek: 2 z 6 artefaktów ma realną wartość badawczą. To lepszy wynik niż przy klasycznym LLM-chacie, ale system nie rozróżniał automatycznie *working artifacts* od *test artifacts*.

### 2. Zbyt wczesna implementacja roadmapy

Przeszliśmy przez 5 faz roadmapy podczas gdy wciąż trwała pierwsza sesja badawcza. To odwróciło priorytety: system rozwijał swoje możliwości zamiast używać ich do pracy.

Sygnał ostrzegawczy: kiedy implementacja systemu staje się głównym zadaniem, a badania schodzą na drugi plan — to narracyjny drift na poziomie meta.

### 3. Pending approvals — strukturalny backlog

3 oczekujące zatwierdzenia zmiany disposition (max_severity 0.72–0.92). Żadna z nich nie została zatwierdzona. To oznacza że DARKROOM generuje rekomendacje, ale nie ma ustalonego rytmu ich przeglądu.

Ryzyko: jeśli backlog approvals rośnie bez przeglądu, system traci kalibrację. Disposition stoi w miejscu mimo sygnałów.

### 4. Epistemic reports bez użytkownika

System ma mechanizm `generate_epistemic_report()` — tygodniowe raporty z agregacją failure patterns. Mechanizm istnieje, ale nie było rytmu kiedy go uruchamiać. Feature bez kontekstu użycia.

---

## Które prompty były zbyt ekspansywne

### Ekspansywne (zbyt szeroki zakres):
- *"Przygotuj mapę literatury dla tematu: test"* — temat "test" nie powinien wchodzić do realnego pipeline'u. Wynikiem był artefakt bez wartości.
- *"Co to jest DARKROOM w systemie Matylda Lite? Odpowiedz w 2 zdaniach."* → odpowiedź była znacznie dłuższa, z sekcją ograniczeń epistemicznych. Epistemic Limit Mode był aktywny — to prawidłowa reakcja systemu, ale pokazuje że krótkie pytania o system meta wyzwalają meta-komentarz.

### Dobrze skalibrowane:
- *"Hipoteza: DARKROOM jest wystarczający do kontroli epistemicznej LLM."* + `no_go=true` — konkretna hipoteza, konkretna destrukcja. Wynik: 5848 znaków failure modes, model=sonnet. Użyteczny.

---

## Co realnie pomogło utrzymać scope

1. **Explicit parking criteria** w wątkach — zamiast "do zrobienia", konkretny warunek parkowania
2. **NO-GO jako osobny tryb** — nie komentarz do odpowiedzi, ale osobna sesja z innym system promptem
3. **Widok wątku w czacie** — kontekst ładowany do wiadomości, nie do osobnego okna. Małe, ale utrzymuje flow.
4. **Decision memo format** w wątku scalar pump — `## Next Action` i `## Parking Criteria` jako wymagane sekcje

---

## Gdzie pojawił się narracyjny drift

### Drift 1: System buduje siebie
Moment kiedy Matylda Lite zaczęła pisać roadmapę własnego rozwoju i ją implementować w tej samej sesji — to drift. Badania fizyczne (scalar pump) stały się kontekstem dla feature development.

Nie jest to błąd systemu — to błąd planowania sesji. System zachował się poprawnie (generował to o co był proszony). Problem był w pytaniu.

### Drift 2: Meta-meta poziom
Kilka odpowiedzi o DARKROOM zawierało sekcje "Ograniczenia epistemiczne" dotyczące *samego DARKROOM-u*. System analizował swoje mechanizmy analityczne. To nie jest zawsze złe — ale kiedy pojawia się bez zadania, jest sygnałem puchnięcia.

### Drift 3: Tension accumulation bez resolution
24 aktywne napięcia. Żadne nie zostało formalnie zamknięte przez `resolve_tension`. Napięcia działają jako sygnały — ale jeśli nie ma rytmu ich przeglądu, stają się szumem.

---

## Które artefakty były naprawdę użyteczne / "tylko ładne"

**Naprawdę użyteczne:**
- `SCALAR_PUMP_NO_GO_HOSTILE_REVIEW.md` — użyteczny bo zawęził. Byłby do niczego gdyby tylko potwierdził.
- `ftar_scalar_pump_no_go.md` (wątek) — ma parking criteria, explicit next action, decision memo. Format działa.
- `matylda_arch_review.md` — self-review Matyldy z konkretnymi propozycjami (structural vs epistemic split) — zaimplementowanymi.

**Tylko ładne (lub techniczne):**
- `DARKROOM_EPISTEMOLOGY_ANALYSIS.md` — analiza systemu przez system. Interesująca jednorazowo, potem szum.
- `roadmap_v1.md` — użyteczna jako artefakt planowania, ale jej istnienie jako *wątku bibliotecznego* podnosi pytanie: czy to research czy to system documentation?

---

## Wnioski operacyjne — co zmienić w v0.2

### Priorytet 1: Rytm przeglądów
Brak: tygodniowy przegląd pending approvals + resolve aktywnych napięć.
Potrzeba: nie feature — **konwencja**. Raz w tygodniu: approval session + tension review.

### Priorytet 2: Rozróżnienie artifact types
Working artifacts vs test artifacts powinny lądować w różnych miejscach.
Propozycja: `artifacts/working/` vs `artifacts/scratch/` — lub przynajmniej tag w metadanych.

### Priorytet 3: Memory candidates (staging area)
Między notatką a durable memory jest luka. Insight zapisany od razu jako `memory/insights/` to za dużo commitment. Potrzeba: `memory/candidates/` — staging area gdzie insight czeka na potwierdzenie.

### Priorytet 4: Wyraźny koniec sesji badawczej
Brak rytuału zamknięcia sesji. Po każdej sesji: jedno zdanie do wątku (`## Ostatnia sesja: [data] — [co ustalono]`). To by eliminowało drift między sesjami.

---

## Ogólny werdykt

Matylda Lite v0.1 jest **bounded cognitive workspace** — i to jest dobre określenie.

Nie superinteligencja. Nie research consciousness engine.
Coś skromniejszego i użyteczniejszego: środowisko które pomaga **nie zgubić sensownych wątków i nie utonąć we własnych narracjach**.

Najtrudniejszy problem nie brzmi "jak zrobić superinteligencję" — tylko "jak nie zgubić tego co ważne". V0.1 pokazało że umie trochę pomagać w tym drugim.

---

_Dokument do archiwizacji po zatwierdzeniu._
