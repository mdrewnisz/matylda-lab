# Matylda: rdzeń

Wersja 0.4, 23 listopada 2026 r. (v0.4: świat T1; v0.3: wyniki S-0/S-0b po recenzji; v0.2: poprawiona rola LMM jako intuicji Matyldy; rdzeń dopisany do Masterplanu jako rozdz. 0, S-0 jako P1). Dokument wizji i minimalnego programu, nie plan wdrożenia.
Uzupełnia Masterplan z 22.11 (nie zastępuje go): Masterplan mówi, **jak** Matylda pracuje i co kontroluje; ten dokument mówi, **po co** to wszystko istnieje.

Oznaczenia: **[WYNIK]** sprawdzone w kodzie lub danych, **[WNIOSK.]** wynika z założeń, **[HIPOTEZA]** do sprawdzenia, **[SPEKULACJA]** kierunek bez uzasadnienia.

---

## 1. Jedno zdanie

**Matylda to autonomiczny badacz, który w dzień zbiera i sprawdza, w nocy przebudowuje to, co wie, a rano budzi się z nowym przeczuciem, które znowu da się sprawdzić.**

Wszystko inne (protokół, klient, benchmarki, modele) jest narzędziem tej pętli albo nie należy do rdzenia.

## 2. Skąd ta wizja i co z niej zostało

Pierwotny zamysł nie zginął, tylko rozpłynął się po warstwach:

- **[WYNIK]** W `matylda-lab/src/matylda_lite/sleeping_matylda/` istnieje „Sleeping Matylda” (ok. 2 900 linii): cykl `observe → compare → doubt → connect`, roadmapa dopisuje `→ forget` i zasadę „Forget by design: system poznawczy, nie archiwum” (`docs/ROADMAP.md`). Szczegóły dziennika mają konsolidować się w wzorce i reguły.
- **[WYNIK]** Ta „noc” pracuje dziś na *workspace*, nie na *wiedzy*: jej wyniki to „findings” porządkowe (osierocone encje, duplikaty, stare pytania, alarmy dryfu) plus synteza LLM dnia. Nie rekombinuje twierdzeń i nie produkuje nowych hipotez do sprawdzenia. Zachowuje za to cenną zasadę: „zero autonomicznych zapisów, każdy finding wymaga akceptacji”.
- **[WYNIK]** Praxis świadomie wyłączył Sleeping Matyldę i homeostazę ze swojego zakresu (`MIGRATION_MANIFEST.md`). Słusznie dla protokołu, ale przez to sen nie ma dziś żadnego właściciela.
- **[WYNIK]** Najbliższym działającym zalążkiem pętli badacza jest KG-0b (`kg/kg0b_magmy.py`): proponujący z małego okna, weryfikator, który umie tylko obalać, pamięć w trzech wariantach (A0 brak, A1 dziennik, A2 graf).

Dlatego rdzeń nie wymaga nowej architektury. Wymaga nazwania pętli i przesunięcia snu z „porządków w notatkach” na „przebudowę wiedzy”.

## 3. Pętla badacza

```
        ┌──────────── CZUWANIE ────────────┐
        │ obserwacja → hipoteza → próba     │
        │ obalenia (weryfikator) → zapis    │
        │ krawędzi i kontrprzykładów w KG   │
        └───────────────┬───────────────────┘
                        │  koniec budżetu / brak nowych kandydatów
        ┌───────────────▼─── SEN ───────────┐
        │ bez dostępu do świata i weryfikatora:
        │ 1. konsolidacja (scalanie, redukcja)
        │ 2. rekombinacja (nowe kandydatury)
        │ 3. przycinanie (pamięć porażek)   │
        └───────────────┬───────────────────┘
                        │
        ┌───────────────▼─ PRZEBUDZENIE ────┐
        │ kilka intuicji z uzasadnieniem    │
        │ „skąd to przyszło” → seed w Praxis│
        │ → wraca do czuwania jako zadanie  │
        └───────────────────────────────────┘
```

### 3.1. Czuwanie (eksploracja i hipotezy)

Matylda patrzy na świat przez ograniczone okno, stawia hipotezy jako krawędzie grafu (A ⇒ B), a twardy weryfikator próbuje je obalić. Przetrwanie oznacza status „skontrowana do N”, nigdy WYNIK. Kontrprzykłady zapisuje się jako pełnoprawne węzły: to paliwo snu.
Tę fazę już umiemy zbudować (KG-0, KG-0b). **[WYNIK]**

### 3.2. Sen (konsolidacja, rekombinacja, przycinanie)

Sen jest fazą **offline**: zero wywołań weryfikatora, zero nowych obserwacji. Pracuje wyłącznie na tym, co już jest w pamięci.

1. **Konsolidacja.** Scalenie klas równoważności pojęć, redukcja przechodnia grafu, kompresja kontrprzykładów do małego zbioru „hubów”, które obalają najwięcej. Detale znikają, struktura zostaje. (To jest „forget” z roadmapy Lab, przeniesione na graf wiedzy.)
2. **Rekombinacja.** Generowanie kandydatów, których nie było w oknie czuwania: złożenia krawędzi, koniunkcje przesłanek (A ∧ B ⇒ C), analogie między klasami o podobnym profilu kontrprzykładów, „prawie-udane” krawędzie z jednym wyjątkiem przerobione na wersję z dodatkowym warunkiem.
3. **Przycinanie.** Każdy kandydat jest najpierw konfrontowany z zapamiętanymi kontrprzykładami (obalenie za darmo). Zostaje kilka najlepszych wg prostej, z góry ustalonej oceny (ogólność, liczba źródeł, nowość względem domknięcia).

Ograniczenie twarde: **sen nie zmienia statusu żadnego twierdzenia.** Może tylko proponować i porządkować indeksy. Zgodne z Masterplanem 5.2 („konsolidacja nie może wymazać linii dowodowej”).

### 3.3. Przebudzenie (nowa intuicja do sprawdzenia)

Na wyjściu snu są nieliczne intuicje, każda z „genealogią” (z których krawędzi i kontrprzykładów powstała). Trafiają do Praxis jako `seed`, czyli hipoteza bez domniemania poprawności, i wracają do czuwania jako zadania dla weryfikatora. Intuicja, którą weryfikator obali, jest wynikiem negatywnym snu, a nie porażką systemu.

### 3.4. Intuicja: miejsce LMM

LMM jest intuicją Matyldy. Nie czyta kodu ani tekstu linijka po linijce: dostaje **tokeny zależności**, czyli strukturę tego, co od czego zależy i co z czego wynika, i na tej podstawie podpowiada, w którą stronę warto iść. Dzięki temu Matylda nie musi przegryzać się przez miliony linii, żeby wybrać kierunek badań. **[DECYZJA Michała, 23.11]**

- **[WYNIK]** Koder LMM (`lmm/bsd2/models.py`, `PosetEncoder`) przyjmuje boolowską macierz relacji N × N (`Fut`), a dane LMM to porządki częściowe (`bsd2/structures.py`, `is_partial_order`).
- **[WNIOSK.]** Graf wiedzy po konsolidacji snu (klasy równoważności pojęć + implikacje między nimi) jest właśnie porządkiem częściowym. Sen produkuje więc wejście w formacie, który LMM już umie czytać. To jest naturalny „token zależności” w świecie KG.
- **[HIPOTEZA]** Intuicja oparta na LMM wybiera lepsze kandydatury do przebudzenia niż prosta heurystyka (ogólność, wsparcie w pamięci). To osobny eksperyment S-1, po S-0 i po wynikach V0/V1/V2.

W prototypie intuicja jest portem: dziś wypełnia go heurystyka, jutro LMM. Pętla działa bez LMM, ale LMM bez pętli nie ma czego wskazywać.

### 3.5. Co wiemy już teraz o wąskim gardle

**[WYNIK]** Agregat `kg/kg0b_wyniki.json` (5 praw podłożonych × 20 ziaren):

| Prawo H | Redukcja przechodnia (prawdziwa) | Pokryte na koniec (A0 = A1 = A2) | Wywołania A0 → A2 |
|---|---|---|---|
| idempotentna | 28 | 7,0 | 19,1 → 12,8 |
| komutatywna | 19 | 7,1 | 32,6 → 17,5 |
| x(xy)=y | 21 | 12,4 | 37,5 → 22,1 |
| łączna | 30 | 12,2 | 78,7 → 26,9 |
| medialna | 47 | 14,9 | 34,0 → 20,1 |

**[WNIOSK.]** Pamięć grafowa oszczędza 33–66% wywołań weryfikatora, ale *nie zwiększa tego, co da się odkryć*: wszystkie ramiona kończą na tym samym pokryciu, rzędu 25–60% prawdziwej struktury. Sufit wyznacza proponujący (czego nie było w oknie, tego nikt nie zaproponował), nie weryfikator ani pamięć.
To jest dokładnie miejsce, w które ma uderzyć sen. Pierwotna intuicja Michała i dane z KG-0b wskazują ten sam brakujący element.

## 4. Minimalny pierwszy eksperyment snu (S-0)

Status: **[HIPOTEZA]**, eksploracyjne, niezamrożone. Do zamrożenia przed uruchomieniem.

**Hipoteza H-sen.** Offline'owa konsolidacja z rekombinacją pamięci podnosi sufit odkryć: przy tym samym budżecie wywołań weryfikatora ramię ze snem pokrywa więcej prawdziwej redukcji przechodniej niż ramię, które zamiast snu dostaje więcej obserwacji.

**Świat.** Dokładnie KG-0b: magmy rozmiaru 3, 5 praw podłożonych, 20 ziaren, ten sam słownik pojęć i ten sam weryfikator. Bez LLM i bez LMM (pętla ma działać sama; model to późniejsza wymiana proponującego).

**Ramiona (identyczny budżet weryfikatora B ∈ {25, 50, 100}):**

| Ramię | Co robi po wyczerpaniu kandydatów z okna | Co izoluje |
|---|---|---|
| A2 | Nic (stan obecny) | Punkt odniesienia |
| W+ | Dostaje drugie okno k nowych magm i proponuje dalej | Czy wystarczy po prostu „więcej dnia” |
| S-los | Losowa rekombinacja pojęć, przycinanie kontrprzykładami | Czy liczy się sama liczba nowych kandydatów |
| **S** | Konsolidacja → rekombinacja → przycinanie (3.2) | Główny treatment: sen |
| S−K | Jak S, bez konsolidacji (rekombinacja na surowym dzienniku) | Wartość konsolidacji |

**Miary.** Główna: pokrycie redukcji przechodniej przy budżecie B (jak w KG-0b). Pomocnicze: pokrycie krawędzi podłożonych (to te są „odkryciem”, nie tłem M3), trafność intuicji (odsetek kandydatów ze snu, które przetrwały weryfikator), koszt CPU snu raportowany osobno.

**Warunki falsyfikacji (do zamrożenia, propozycja):**
- H-sen **obalona w tym świecie**, jeżeli S nie przewyższa W+ przy B = 50 (sparowana różnica na ziarnach, dolna granica 95% CI ≤ 0) w co najmniej 3 z 5 praw.
- Konsolidacja **zbędna**, jeżeli S nie przewyższa S−K.
- Sen to tylko **generator szumu**, jeżeli S nie przewyższa S-los.
- Wynik pozytywny dotyczy wyłącznie magm rzędu 3 i tego słownika. Nie jest twierdzeniem o „intuicji” w ogóle (deflacja z góry).

**Ryzyko przecieku.** Rekombinacja nie może korzystać z prawdziwego grafu ani z listy praw podłożonych. Kandydaci ze snu muszą być generowani przed jakimkolwiek kontaktem z weryfikatorem, a ich lista hashowana przed przebudzeniem.

**Koszt.** Jeden skrypt obok `kg0b_magmy.py`, numpy, minuty CPU. Nie wymaga GPU, LMM, Lab ani Praxis. **[WNIOSK.]**

Jeżeli S-0 wyjdzie negatywnie, rozróżniamy (wg metodologii, pkt 4): zła rekombinacja (spróbować innych operatorów), za mały świat (magmy rzędu 4), czy realny brak efektu. Jeden wynik negatywny nie zamyka wizji, ale zamyka *tę* wersję snu.

### 4.1. Wyniki S-0 i S-0b po niezależnej recenzji (23.11, `matylda-lab/rdzen/`)

Obie prerejestracje zamrożono przed uruchomieniem. Niezależny recenzent (osobny agent) i przegląd automatyczny znaleźli dwa błędy w ramionach kontrolnych oraz błąd interpretacyjny miary. Po poprawkach wnioski brzmią inaczej niż pierwsze odczytanie S-0. Szczegóły: `rdzen/wyniki/RECENZJA_I_WNIOSKI_S0_S0B.md`.

- **[WYNIK NEGATYWNY]** Powtórka własnych porażek (kontrprzykładów) nie ma wartości ponad tyle samo świeżych epizodów. Przy równym zużytym budżecie jest wręcz gorsza (istotnie ujemne w 3–4 z 5 praw). Wersja snu „powtórka” odpada.
- **[WYNIK NEGATYWNY]** Sen nie jest wydajniejszy na jedno wywołanie weryfikatora niż dzień. Dopóki proponujący dnia ma kandydatów, jego kandydatury są lepsze. Pierwszy werdykt S-0 („S > W+”) wynikał z tego, że dzień przestawał proponować i zostawiał niewydany budżet.
- **[WYNIK, eksploracyjny, wąski świat]** Sen działa jako generator, gdy dzień gaśnie: dzięki śmiałym przeczuciom wciąż ma co proponować, a na jedno wywołanie bije losowy przegląd w obu rzędach magm. Wyczerpuje się jednak wcześniej niż losowy przegląd.
- **[WNIOSKOWANIE]** Wąskim gardłem nie jest pamięć ani powtórka, tylko **wybór, które śmiałe przeczucie sprawdzić**. To jest zadanie intuicji, czyli miejsce LMM. Kolejność pętli: najpierw dzień, potem sen jako generator przestrzeni hipotez, z intuicją jako filtrem.
- **[RYZYKO]** W obecnych światach losowa para po przycięciu jest prawdziwa w ~90%, więc intuicja nie ma czego rozstrzygać. Przed S-1 (LMM jako intuicja) potrzebny jest świat, w którym śmiałe przeczucia są w większości fałszywe.

### 4.2. Świat T1 dla intuicji (23.11, `rdzen/SWIAT_T1_PROJEKT.md`)

Kryteria trudności zapisano przed kalibracją: losowe i śmiałe przeczucia mają być w większości fałszywe, a dzień nie może rozwiązywać świata sam.
- **[WYNIK NEGATYWNY]** Mniej kontrprzykładów i negacje pojęć nie wystarczają; negacje czynią świat wręcz łatwiejszym.
- **[WYNIK]** Działa słownik z **literałami** `a·b=c` (pojedyncze wpisy tablicy działania), czyli zależnościami najniższego poziomu, plus weryfikator, który zwraca jeden kontrprzykład. **T1** (rząd 3): trafność losowa 0,25, śmiałe przeczucia 0,47 (tuż pod progiem, różnie między prawami). **T1-4** (rząd 4): 0,26 i 0,20. S-1 ma wymagać zgodności w obu.
- **[WNIOSKOWANIE]** Literały są naturalnymi „tokenami zależności” dla LMM: prawo podłożone jest siecią zależności między wpisami tablicy, którą intuicja ma wyczuć.

### 4.3. S-1: prerejestracja (24.11, `rdzen/PREREJESTRACJA_S1.md`, zamrożona w commicie 7676f1b)

Pytanie: czy intuicja wybiera lepsze przeczucia niż los? Ramiona różnią się tylko portem `Intuicja`: losowa, heurystyka ogólności,
dwie wyrocznie kalibracyjne (bramka „czy wybór w ogóle się opłaca”). Miara: pole pod krzywą pokrycia po dniu 1 przy równym zużytym budżecie,
80 ziaren, werdykt wymaga zgodności w T1 i T1-4, trzy kategorie (lepsza / pomijalna / nierozstrzygnięta). Niezależna recenzja przed uruchomieniem
odrzuciła wersję 1 (moc ok. 1%), wersja 2 ma moc ≥ 0,99 na prawach spoza S-0. LMM dołącza osobną poprawką, na świeżych ziarnach 600–679,
bez danych ze światów praw S-0. Status: **zamrożona, nieuruchomiona**.

## 5. Czemu służy każdy istniejący element

| Element | Rola wobec rdzenia |
|---|---|
| **KG (`kg0.py`, `kg0b_magmy.py`)** | Pamięć badacza i pierwszy świat, w którym pętla czuwanie–sen–przebudzenie może naprawdę działać; to tu powstaje S-0. |
| **Matylda Praxis** | Brama przebudzenia: intuicja ze snu wchodzi jako `seed`, a status może zmienić tylko weryfikator lub człowiek, więc sen nigdy nie promuje wiedzy sam. |
| **Matylda Lab** | Okno człowieka na pętlę: pokazuje, co Matylda śniła i co zaproponowała; jej Sleeping Matylda daje rdzeniowi zasadę „findings wymagają akceptacji”, ale silnik snu przechodzi na KG. |
| **Benchmark GSI** | Sędzia: odpowiada, czy pętla ze snem odkrywa więcej nowych, poprawnych krawędzi (NPH) niż bez snu; sen to naturalne kolejne ramię obok A/B/C. |
| **Sprawdzacz wynikania / hard checker** | Jedyny, kto w czuwaniu może obalić intuicję; bez niego sen byłby generowaniem narracji. |
| **LMM** | **Intuicja Matyldy** (rola nadana przez Michała, DECYZJA 23.11): model działający na tokenach zależności, a nie na surowym tekście, który wskazuje kierunek badań bez przegryzania się przez miliony linii kodu; w pętli siedzi na styku snu i przebudzenia jako port `Intuicja`, który ocenia rekombinacje i wybiera, co obudzić (zob. 3.4). |
| **H1 (rejected trajectories)** | Pytanie, czy pamięć porażek ma wartość, to pytanie o paliwo snu; S-0 testuje wąską wersję tego samego na kontrprzykładach. |
| **microgpt-attractor** | Formalna metafora konsolidacji (stany ściągane do atraktora μ jak epizody do prototypu) **[SPEKULACJA]**; nie budujemy z niego nic, dopóki nie da się go przełożyć na operator na grafie. |
| **Repo Matylda (monorepo)** | Archiwum; z niego bierzemy tylko zasadę „no autonomous self-modification” ze skilla `self_memory_consolidation`. |
| **Matylda Lite** | Archiwum, przodek Lab. |
| **FTAR, Riemann, engrenage** | Przyszłe dziedziny, w których badacz może kiedyś śnić; nie są częścią rdzenia. |

## 6. Czego nie budujemy (dla rdzenia)

Uzupełnia listę z Masterplanu, rozdz. 11.

- **Snu opartego na LLM-owej syntezie dnia** („day_synthesis” w `synthesis.py`) jako rdzenia. Streszczenie nie jest rekombinacją wiedzy i nie da się go sfalsyfikować.
- **Snu, który zapisuje.** Żadnej automatycznej promocji, usuwania krawędzi ani zmiany statusów w nocy.
- **Homeostazy, zmęczenia, budżetu uwagi, Focus Mode, briefingów, dashboardu** jako warunku pętli. Mogą wrócić jako warstwa Lab, gdy pętla zadziała.
- **Graph Governora, uczonej topologii, self-mutation/evolution** (monorepo Matylda), routera modeli UCB1.
- **Wielu agentów i person** (Gustaw, Serafin, sześciu recenzentów) w pętli rdzenia. Pętla ma jednego proponującego, jednego weryfikatora i jedną pamięć.
- **LMM czytającego surowy kod lub tekst.** Intuicja ma działać na tokenach zależności; przepisanie jej na model językowy nad kodem byłoby powrotem do „przegryzania się przez miliony linii”.
- **Podpięcia prawdziwego LMM do portu `Intuicja` przed S-0** i przed wynikami V0/V1/V2. Port istnieje od razu, model wchodzi po wynikach.
- **Integracji Lab ↔ Praxis ↔ KG „na zapas”**, zanim S-0 da wynik. Najpierw wynik, potem framework (reguła ochronna Masterplanu).

## 7. Status dokumentu i następny krok

- Wizja pętli: **[HIPOTEZA]** z mocnym punktem zaczepienia w danych (sufit proponującego w KG-0b).
- Następny krok: zamrozić S-0 (operatory snu, próg, B) w prerejestracji prototypu i uruchomić go. Bez nowej infrastruktury.
- DECYZJA Michała (23.11): rdzeń dopisany do Masterplanu jako rozdział 0 „Po co jest Matylda”, S-0 jako priorytet P1 obok etapów 0–2 GSI. Prototyp pętli powstaje w `matylda-lab/rdzen/`.
