# Recenzja przed zamrożeniem: `PREREJESTRACJA_S0_HEUR.md` (niezależna, krytyczna)

Data: 26.11. Przedmiot: `PREREJESTRACJA_S0_HEUR.md` (projekt, nieśledzony), `matylda_rdzen/s0_heur.py` (nieśledzony),
`matylda_rdzen/heur_walidacja.py` (`zbierz`), `matylda_rdzen/heurystyki.py` (`HeurystykaGrafu("oa+ob+kara")`).
Kontekst: `PLAN_HEURYSTYKA_GRAFU.md`, `wyniki/HEUR_GRAFU_RAPORT.md`, `wyniki/HEUR_GRAFU_RECENZJA.md`, `PREREJESTRACJA_S1B.md`,
`wyniki/S1B_RAPORT.md`, `wyniki/s1b_wyniki.json`, `wyniki/heur_grafu_walidacja.json`.

**Czego nie robiłem:** nie uruchamiałem `python -m matylda_rdzen.s0_heur` i nie użyłem ziaren 600–679 w żadnej formie.
Żadnego ramienia nie uruchamiałem na prawach S-0 (z żadnymi ziarnami).
**Czego użyłem:** ziarna **1724–1739** (16) na 5 prawach spoza S-0 (`PRAWA_MOCY`), oba światy, 4 ramiona, 640 przebiegów, 290 s:
`heur_walidacja.zbierz` + `s0_heur.analiza` (test dymny analizy). Do tego bez ziaren: struktura światów `zbuduj_swiat` (rozmiary, TR, klasy)
dla wszystkich 10 praw oraz przeliczenia na opublikowanych JSON-ach. Skrypty leżą poza repo (scratchpad sesji).
Jedyny zmieniony plik repo: ten.

Klasyfikacja: **WYNIK** (sprawdzone), **WNIOSKOWANIE**, **HIPOTEZA**, **SPEKULACJA**.

---

## 0. Werdykt w skrócie

Projekt jest dobry i bliski gotowości. Kod robi to, co prerejestracja, w każdym punkcie rozstrzygającym (ramiona, ziarna, budżety,
ważność, bramka, kategorie, werdykt). Moc jest z dużym zapasem. Logika werdyktu jest jednoznaczna i nie ma furtki „lepsza i gorsza naraz”.
Zastrzeżenia dotyczą głównie **rejestru ziaren i procedury zamrożenia** oraz **opisu ograniczeń** (prawo S-0 x(xy)=y w T1 jest lustrzaną
kopią prawa walidacyjnego (yx)x=y). Do zamrożenia potrzeba **5 poprawek blokujących** (sekcja 6). Wszystkie są tanie i nie zmieniają kryterium.

---

## 1. Zgodność kodu z prerejestracją

| Punkt | Prerejestracja | Kod | Ocena |
|---|---|---|---|
| Ramiona | losowa, heurystyka, heur_grafu, wyrocznia_pokrycia | `heur_walidacja.RAMIONA`, fabryka w `zbierz`; `HeurystykaGrafu(WZOR)`, `WZOR = "oa+ob+kara"`, `dedup=True` domyślnie | WYNIK: zgodne |
| Reguła | sha256 `bbbf3a71…8931`, niezmieniona od 459a097 | `sha256sum heurystyki.py` = `bbbf3a71c2da07d94391a35c8f865ba0c99f12d53f60e7510d0075bca5ed8931`; `git log` pliku: tylko 459a097 | WYNIK: zgodne |
| Prawa, światy | `PRAWA_S0`, T1 (rząd 3), T1-4 (U4) | `zbierz(PRAWA_S0, SEEDS)`, `s1.SWIATY = {"T1": 3, "T1-4": 4}`, słownik `literaly`, `CEX = 1` | WYNIK |
| Budżet | dzień 1 ≤ 300, sen 50, k = 10, cex_cap 1 | `BUDZET_DNIA=300`, `BUDZET_SNU=50` z `s1b`; `ILE_INTUICJI=10` domyślne w `uruchom` | WYNIK |
| Ziarna | 600–679 | `SEEDS = range(600, 680)` | WYNIK (ale patrz §2.3) |
| Czuwanie 1 wspólne | asercją | `s1b.roznice`: `assert rx["d1"] == ry["d1"]` — wykonuje się **tylko dla praw ważnych** (kontrasty liczone tylko dla nich) | WYNIK: drobna luka, bez znaczenia praktycznego |
| M1 | pole od d1 do b = min wywołań, bootstrap sparowany 95%, 10 000, ziarno 12345 | `s1b.roznice(..., "pole")`, `s0.ci95` (`BOOT=10_000`, `BOOT_SEED=12345`, percentyle) | WYNIK |
| Ważność | niepusta pula 1. snu w ≥ 90% ziaren | `s1b.waznosc` na ramieniu `losowa` (pula wspólna); `zbierz` zapisuje `pula=bool(...)` | WYNIK |
| Bramka | wyrocznia − heurystyka, dolna CI > 0 w ≥ 3/5; < 3 ważnych → nieinformatywny | `glo > 0`, `len(bramka_prawa) >= 3`, `nieinformatywny if not bramka or len(wazne) < 3` (drugi warunek redundantny, nieszkodliwy) | WYNIK |
| Kategorie | lepsza: dolna > 0 w ≥ 3/5; gorsza: górna < 0 w ≥ 3/5 | jak w tekście; listy rozłączne, więc oba ≥ 3 z 5 są niemożliwe | WYNIK |
| Werdykt | §4 | `analiza()` — pełna tabela w §3; zgodna z tekstem czytanym po kolei | WYNIK |
| Stałe okno | [d1, d1+50] | `_okno`: średnia `pokr(krzywa, t)` dla t = d1…d1+50 (51 punktów, ostatnia wartość przenoszona) — identycznie jak w recenzji heurystyki | WYNIK: poprawne |
| „koncowe” | różnica pokrycia końcowego | `krzywa[-1][1]` | WYNIK: poprawne, patrz niżej |

**„koncowe” = `krzywa[-1][1]` jest poprawne.** Uzasadnienie z kodu (WNIOSKOWANIE) i sprawdzenie (WYNIK):
`fazy.czuwanie` dopisuje punkt krzywej po **każdym** wywołaniu weryfikatora i przerywa, gdy `wywolania >= budzet`, więc budżet nie jest
przekraczany (`wyw ≤ d1 + 50`). Pokrycie jest monotoniczne (`p.prawdziwe` tylko rośnie). Zatem `krzywa[-1][1] = pokr(krzywa, d1 + 50)`
również wtedy, gdy przebieg kończy się wcześniej przez wyczerpanie puli (później nic już nie przybywa). W teście dymnym (640 przebiegów):
`wyw ≤ d1+50` zawsze, krzywe posortowane i monotoniczne, `krzywa[-1][1] ≠ pokr(krzywa, d1+50)` w **0** przypadkach.
Uwaga definicyjna: to **nie** jest S-1b-owe „koniec” (`pokr` w b = min wywołań pary), tylko pokrycie po d1+50 — dokładnie to, o co prosiła
recenzja heurystyki (§7.2). Prerejestracja powinna to napisać wprost (zalecenie Z3).

**Test dymny analizy (WYNIK, ziarna 1724–1739, prawa spoza S-0, n = 16):** `analiza()` działa end-to-end, wszystkie 10 par ważnych, bramka 5/5
w obu światach, kategorie T1 „lepsza” 5/5, T1-4 „lepsza” 3/5 (x(xy)=xy „gorsza”, elastyczna 0,00 [−0,20; 0,19]). Kierunek i wielkości jak
w walidacji i replikacji. Dla zdegenerowanych różnic (wszystkie 0, np. „koncowe” gdy oba ramia wyczerpują pulę) `ci95` zwraca [0, 0, 0]
i nie liczy się ani jako lepsza, ani gorsza — poprawnie. Te wartości **nie** są informacją o S-0.

Drobne niezgodności/braki (nie zmieniają werdyktu):
- §5 mówi „per prawo”, ale kontrasty opisowe (stałe okno, koncowe, heur_grafu − los) liczone są **tylko dla praw ważnych**; S-1b liczyło
  pola opisowe dla wszystkich praw. Jeśli któreś prawo wypadnie z ważności, zniknie z raportu (Z5).
- JSON nie zapisuje: hasha U4 (S-1b zapisywało), odsetka przebiegów na limicie snu per ramię (S-1b zapisywało), trafności 1. snu,
  ani **surowych krzywych per ziarno** (Z1).
- „Ułamek luki” dzieli średnie z dwóch różnych okien b (znane z recenzji heurystyki); prerejestracja świadomie podaje go „bez CI” — dopuszczalne,
  ale zalecam liczyć go także na wspólnym stałym oknie (Z6).

---

## 2. Zabezpieczenia

### 2.1 Co działa (WYNIK, z kodu)
- **Brudne drzewo:** `git status --porcelain .` w `rdzen/` obejmuje też pliki nieśledzone (nie ma `.gitignore` dla `dane/`); dziś odmówiłby
  (oba pliki są `??`). Dobrze.
- **Nadpisanie:** odmowa przy istniejącym `wyniki/s0_heur_wyniki.json`.
- **U4:** pełny hash porównywany z `s1.U4_SHA`.
- **`HEUR_SHA = None`:** porównanie `_sha(...) != None` jest zawsze prawdziwe, więc runner **nie ruszy przed wpisaniem hasha**. To dobry
  bezpiecznik (fail-safe), ale wpisanie wartości w commicie zamrożenia jest warunkiem koniecznym (B1).

### 2.2 Luki
- **Sprawdzany jest tylko `heurystyki.py`.** Zmiana po zamrożeniu w `heur_walidacja.py` (np. `WZOR`, `RAMIONA`), `intuicja.py`, `fazy.py`,
  `petla.py`, `s1b.py` (budżety, próg ważności), `s1.py` (`SWIATY`, `CEX`, `SLOWNIK`) czy w samym `s0_heur.py` (np. `SEEDS`) przejdzie
  przez runner, jeśli zostanie zacommitowana. Wykrywalne jest to tylko post hoc (pola `commit` i `kod_sha256`). To ten sam poziom co S-1b
  i tam wystarczył, bo recenzent po wyniku porównał commit. Warunek: raport po wyniku **musi** wykazać, że `git diff <commit zamrożenia>
  <commit z JSON> -- rdzen/` jest pusty (B4). Mocniejsza opcja (zalecenie): runner sprawdza, że ostatni commit dotykający
  `PREREJESTRACJA_S0_HEUR.md` jest równy ostatniemu commitowi dotykającemu `rdzen/matylda_rdzen/` (czyli kod nie zmieniał się po prerejestracji).
- `prerejestracja_sha256` jest zapisywane, ale nie weryfikowane — j.w., kontrola post hoc.

### 2.3 Rejestr ziaren: konflikt z LMM (WYNIK)
Ziarna 600–679 są nadal zarezerwowane w **dwóch innych miejscach**: `matylda_rdzen/s1lmm.py` (`SEEDS = range(600, 680)`, docstring
„Uruchamiać na ziarnach 600–679…”) i `PREREJESTRACJA_S1_LMM.md` (projekt), a także w komentarzu `s1b.py` („600–679 LMM”) i w raportach LMM.
Po S0_HEUR ramiona `losowa`, `heurystyka`, `wyrocznia_pokrycia` na tych ziarnach i prawach będą **już obejrzane** (deterministycznie te same
przebiegi), więc ewentualny przyszły test LMM na 600–679 nie byłby świeży. Prerejestracja musi to jawnie przesądzić (B2).

Ponadto §6 zapowiada test dymny na ziarnach **1720–1723**, a w repo nie ma po nim śladu; ta recenzja zużyła **1724–1739**. Oba zakresy
trzeba wpisać do rejestru ziaren (B3).

---

## 3. Jednoznaczność reguły werdyktu

Pełna tabela tego, co robi `analiza()` (sprawdzone na kodzie, WYNIK). Kolejność reguł w §4 jest kolejnością rozstrzygania:

| T1 \ T1-4 (bez kolejności) | wynik |
|---|---|
| lepsza + lepsza | WYNIK |
| lepsza + nierozstrzygnięta | WYNIK CZĘŚCIOWY |
| lepsza + nieinformatywny | WYNIK CZĘŚCIOWY |
| lepsza + gorsza | WYNIK NEGATYWNY (gorsza) |
| gorsza + cokolwiek | WYNIK NEGATYWNY (gorsza) |
| nierozstrzygnięta + nierozstrzygnięta | WYNIK NEGATYWNY (brak przewagi) |
| nierozstrzygnięta + nieinformatywny | WYNIK NEGATYWNY (brak przewagi) |
| nieinformatywny + nieinformatywny | NIEINFORMATYWNY |

- **Furtka „lepsza i gorsza” w jednym świecie:** nie istnieje (≥ 3 + ≥ 3 > 5, listy rozłączne). **Między światami:** „gorsza” wygrywa,
  co jest zgodne z tekstem („gorsza w którymś”) i z zaleceniem recenzji heurystyki. WYNIK.
- **< 3 praw ważnych:** zawsze nieinformatywny (bramka nie może przejść). Prawo nieważne działa jak niezaliczone; próg 3/5 jest bezwzględny,
  więc przy 4 ważnych prawach kryterium jest ostrzejsze — konserwatywne, akceptowalne. WYNIK.
- **Asymetria (zalecenie Z2):** świat nieinformatywny obok „lepszej” daje CZĘŚCIOWY, a obok „nierozstrzygniętej” daje NEGATYWNY.
  Etykieta „WYNIK NEGATYWNY (brak przewagi)” dla „nierozstrzygnięta + nieinformatywny” jest za mocna: o drugim świecie nic nie wiadomo.
  Proponuję albo zostawić, ale wpisać tabelę powyżej do prerejestracji dosłownie (B5), albo nazwać ten przypadek
  „NIEROZSTRZYGNIĘTY (X: brak przewagi, Y: nieinformatywny)”. Zmiana nazwy przed zamrożeniem jest dozwolona; ważne, by była ustalona teraz.
- **„lepsza” przy 2 prawach istotnie gorszych:** kategoria „lepsza” jest możliwa przy 3 lepszych i 2 istotnie gorszych. Prerejestracja
  raportuje to tylko opisowo. Proponuję z góry ustalić brzmienie: „lepsza w ≥ 3/5, ale istotnie gorsza w …” i nie nazywać reguły
  „domyślną intuicją” bez zastrzeżenia, gdy w którymś świecie są ≥ 2 prawa „gorsza” (Z4). W walidacji było to 1/5 (x(xy)=xy w T1-4).
- Hipoteza H w §1 („> 0 na prawach S-0”) jest mierzona kryterium „≥ 3/5 praw”, nie średnią po prawach — w porządku, ale warto to zdanie
  przy H dopisać.

---

## 4. Moc

Na podstawie `wyniki/heur_grafu_walidacja.json` (n = 40): SE przy n = 80 ≈ (górna − dolna)/3,92/√2.

| Świat | prawo (walidacja) | efekt | SD różnic | SE₈₀ | MDE₈₀ (80% mocy) | P(dolna > 0) przy n = 80, gdyby efekt był taki sam |
|---|---|---|---|---|---|---|
| T1 | elastyczna | +1,02 | 1,00 | 0,11 | 0,31 | ≈ 1 |
| T1 | lewa | +2,83 | 1,79 | 0,20 | 0,56 | ≈ 1 |
| T1 | prawa | +2,85 | 1,34 | 0,15 | 0,42 | ≈ 1 |
| T1 | x(xy)=xy | +1,17 | 1,10 | 0,12 | 0,34 | ≈ 1 |
| T1 | (yx)x=y | +1,73 | 1,38 | 0,15 | 0,43 | ≈ 1 |
| T1-4 | elastyczna | +0,17 | 0,50 | 0,06 | 0,16 | 0,84 |
| T1-4 | lewa | +1,59 | 0,74 | 0,08 | 0,23 | ≈ 1 |
| T1-4 | prawa | +4,18 | 1,28 | 0,14 | 0,40 | ≈ 1 |
| T1-4 | x(xy)=xy | −1,04 | 1,54 | 0,17 | 0,48 | P(górna < 0) ≈ 1 |
| T1-4 | (yx)x=y | +0,60 | 0,71 | 0,08 | 0,22 | ≈ 1 |

- **WYNIK (przeliczenie):** przy 80 ziarnach minimalny wykrywalny efekt to ok. **0,16–0,56 krawędzi TR**, czyli ok. 5–15% luki
  wyrocznia − heurystyka (luki 0,8–11; na S-0 z S-1b: wyr − heur ≈ 1,3–3,8 w T1 i 2,0–6,1 w T1-4, na różnych oknach — WNIOSKOWANIE).
  Gdyby efekty na S-0 były jak na walidacji, P(„lepsza”) ≈ 1,00 w obu światach. **80 ziaren wystarcza z zapasem.** Bramka (wyrocznia − heurystyka)
  przejdzie niemal na pewno: w S-1b wszystkie kontrasty wyroczni miały dolne CI daleko od 0 (WNIOSKOWANIE).
- **Odwrotna strona mocy (zalecenie Z6):** test wykryje także efekty praktycznie pomijalne (≈ 0,15 krawędzi, kilka procent luki) i nazwie je
  „lepsza” lub „gorsza”. Nie ma progu istotności praktycznej (S-1b miał δ). Nie proponuję zmieniać kryterium, ale z góry zapisać, że
  per prawo raportujemy ułamek luki i że efekt < 0,1 luki opisujemy jako „istotny statystycznie, praktycznie mały”.
- Ważność: w S-1b na prawach S-0 sen odbył się w 97,5–100% ziaren; najniżej T1 komutatywna (0,9875) i T1-4 x(xy)=y (0,975). Ryzyko
  utraty ważności niskie (WNIOSKOWANIE).

---

## 5. Czy coś w S-0 może uczynić test nieinformatywnym lub stronniczym

Struktura światów (bez ziaren, `zbuduj_swiat(H, rząd, "literaly")`, WYNIK):

| Świat | prawo | \|W\| | żywe węzły nieliterałowe /23 | klasy | \|TR\| | TR dotykające węzła nieliterałowego | TR podłożone |
|---|---|---|---|---|---|---|---|
| T1 | idempotentna | 729 | 21 | 43 | 64 | 64 | 40 |
| T1 | komutatywna | 729 | 21 | 34 | 39 | 39 | 23 |
| T1 | x(xy)=y | 64 | 20 | 36 | 47 | 38 | 39 |
| T1 | łączna | 113 | 22 (4 ≡ ⊤) | 45 | 72 | 72 | 59 |
| T1 | medialna | 369 | 23 | 51 | 88 | 64 | 5 |
| T1 | *(yx)x=y (walid.)* | 64 | 20 | 36 | 48 | 39 | 37 |
| T1-4 | idempotentna | 1196 | 18 | 81 | 67 | 67 | 60 |
| T1-4 | komutatywna | 1472 | 20 | 55 | 59 | 59 | 47 |
| T1-4 | x(xy)=y | 1024 | 18 | 60 | 72 | 72 | 58 |
| T1-4 | łączna | 1027 | 20 (4 ≡ ⊤) | 84 | 91 | 91 | 81 |
| T1-4 | medialna | 1880 | 20 | 88 | 97 | 37 | 5 |

Walidacyjne T1-4 dla porównania: \|W\| 38–2232, TR 52–111, TR z węzłem nieliterałowym 30–73.

1. **x(xy)=y w T1 to lustrzane odbicie walidacyjnego (yx)x=y (WYNIK + WNIOSKOWANIE).** Świat x(xy)=y jest transpozycją świata (yx)x=y
   (op′(x,y) = op(y,x) przeprowadza jedno prawo w drugie); \|W\| 64 = 64, klasy 36 = 36, TR 47 wobec 48. Słownik jest prawie zamknięty
   na dualność (literały a·b=c ↔ b·a=c, lewa/prawa samodystr., lewa/prawa alternat., xy=x/xy=y, skracalności; bez dualu: x(xy)=xy,
   półsymetr., „ma lewy neutralny”). Wynik heur_grafu w T1 x(xy)=y będzie więc **w przybliżeniu replikacją** walidacji (+1,73; replikacja +1,56),
   a nie testem uogólnienia. W T1 realnie nowe są 4 prawa, a „≥ 3/5” wymaga 2 z 4 nowych + tego dualnego. Nie zmienia to ważności testu,
   ale **musi być jawnie opisane w prerejestracji** (B5) i w raporcie. W T1-4 problem nie występuje (\|W\| 1024 wobec 38). Analogicznie
   w walidacji lewa i prawa samodystr. były parą dualną — warto to też odnotować (walidacja miała w T1 realnie ~4 niezależne prawa).
2. **U4 zbudowano wokół praw S-0 (WYNIK).** Światy S-0 w T1-4 to ~1000 magm z próbnika z nawrotami (niejednostajne) na prawo, a światy
   walidacyjne były „produktem ubocznym” tych próbek. Do tego silne nakładanie: 885 z 1027 łącznych jest medialnych, 382 komutatywnych.
   To cecha świata, wspólna dla ramion, więc **nie tworzy stronniczości między ramionami**; ogranicza jedynie zakres twierdzenia
   („na U4”, jak w S-0b §50). WNIOSKOWANIE.
3. **Inny reżim struktury (WYNIK + HIPOTEZA).** W idempotentnej, komutatywnej, x(xy)=y (T1-4) i łącznej **każda** krawędź TR dotyka węzła
   nieliterałowego (literały są tam niezależne albo równoważne), a dużą część TR stanowią krawędzie podłożone. Recenzja heurystyki wiązała
   zysk z „żywymi węzłami-prawami”, więc te światy mogą sprzyjać regule (HIPOTEZA). Z kolei medialna (TR w większości literałowe, 5 podłożonych)
   przypomina elastyczną, w której reguła w T1-4 była na granicy zera — to najbardziej prawdopodobny kandydat na „nierozstrzygnięte”
   (SPEKULACJA). Nie jest to stronniczość protokołu, tylko powód, by z góry zapisać, że wynik dotyczy tych 5 struktur.
4. **Obserwacje z S-1b w T1-4 (WYNIK z `s1b_wyniki.json`).** Łączna: wyrocznia kończy wcześnie z pełnym TR (na limicie snu 2,5% wobec 45%
   u heurystyki), więc bramkowa różnica wyrocznia − heurystyka jest liczona na krótkim oknie b = min — nadal duża (S-1b: 7,79 − 1,65 wobec losu),
   bramka bezpieczna. Limit snu 50 wiąże w T1 idempotentnej (57–69%) i łącznej (86–98%), w T1-4 łącznej (45%): tam M1 mierzy tempo, a „koncowe”
   = pokrycie po 50 wywołaniach, nie po wyczerpaniu puli. Symetryczne dla ramion; stałe okno i „koncowe” to obejmą. Runner nie raportuje
   jednak odsetka „na limicie snu” per ramię (Z1).
5. **Ekspozycja badacza na S-0 (SPEKULACJA, ryzyko niskie).** Prawa S-0 były oglądane w S-0, S-0b, S-1, S-1b (heurystyka, wyrocznia) i przy
   LMM v0–v1. Pomysł „out(b)” mógł być pośrednio inspirowany tą wiedzą. Przemawia przeciw: reguła zamrożona 459a097 przed walidacją, wybrana
   na dev bez S-0; w repo nie ma żadnego przebiegu `HeurystykaGrafu` na prawach S-0 (sprawdziłem `heur_dev*.json`, `heur_grafu_walidacja.json`,
   `heur_dev.py`). Wystarczy jedno zdanie w prerejestracji.
6. **Heurystyka bazowa jest ta sama co w S-1b**, ale ziarna różne (800–879 wobec 600–679), więc nie ma „podglądu” kontrastu na ziarnach testowych.
   WYNIK.

Nic z powyższego nie czyni testu nieinformatywnym; jedynym realnym ograniczeniem niezależności jest punkt 1.

---

## 6. Wymagane poprawki

### BLOKUJĄCE (przed zamrożeniem)

- **B1. Zamrożenie technicznie:** wpisać `HEUR_SHA = "bbbf3a71c2da07d94391a35c8f865ba0c99f12d53f60e7510d0075bca5ed8931"` w `s0_heur.py`
  i zacommitować razem `PREREJESTRACJA_S0_HEUR.md`, `s0_heur.py` i tę recenzję; status w prerejestracji zmienić na „zamrożona”
  z odwołaniem do recenzji. Bez tego runner (słusznie) odmówi.
- **B2. Rejestr ziaren 600–679 a LMM:** w prerejestracji zapisać, że S0_HEUR **zużywa** 600–679, a ewentualny test LMM na S-0 dostanie nowe,
  świeże ziarna wyznaczone w jego własnej prerejestracji. W tym samym commicie zmienić `s1lmm.SEEDS` (np. na `None` z odmową uruchomienia albo
  na nowy zakres) i adnotować `PREREJESTRACJA_S1_LMM.md` — inaczej repo nadal deklaruje te same ziarna dla dwóch testów.
- **B3. Rejestr pozostałych ziaren:** wpisać 1720–1723 (test dymny — wykonać i odnotować wynik albo usunąć zdanie z §6) oraz 1724–1739
  (ta recenzja, prawa spoza S-0) jako zużyte.
- **B4. Kontrola zgodności po wyniku:** dopisać do §6, że raport po wyniku musi wykazać pusty `git diff <commit zamrożenia> <commit z JSON> -- rdzen/`
  oraz zgodność `kod_sha256` i `prerejestracja_sha256` z commitem zamrożenia (runner sprawdza tylko hash reguły).
- **B5. Jednoznaczność i ograniczenia w tekście:** (a) wpisać do §4 tabelę z §3 tej recenzji (10 kombinacji kategorii, „reguły stosowane po kolei”),
  ewentualnie z przemianowaniem przypadku „nierozstrzygnięta + nieinformatywny” (Z2) — decyzja przed zamrożeniem;
  (b) dopisać do §1/§3, że x(xy)=y w T1 jest dualną kopią walidacyjnego (yx)x=y, więc w T1 test uogólnienia opiera się realnie na 4 prawach.

### Zalecenia (nieblokujące)

- **Z1.** Zapisywać surowe dane per ziarno (`wyw`, `d1`, `krzywa`, `pula`) do osobnego pliku oraz hash U4 i odsetek przebiegów na limicie snu per ramię
  (jak S-1b). Bez tego każda analiza po wyniku wymaga ponownego przeliczenia ziaren testowych.
- **Z2.** Rozważyć etykietę „NIEROZSTRZYGNIĘTY” zamiast „WYNIK NEGATYWNY (brak przewagi)”, gdy drugi świat jest nieinformatywny.
- **Z3.** Zdefiniować „koncowe” wprost: pokrycie TR po d1 + 50 wywołaniach (lub po wyczerpaniu puli) = `krzywa[-1][1]`; odróżnić od S-1b-owego
  „koniec” (pokrycie w b = min).
- **Z4.** Z góry ustalić brzmienie przy kategorii „lepsza” z ≥ 2 prawami „gorsza” w tym samym świecie (nie ogłaszać wtedy reguły domyślną bez zastrzeżenia).
- **Z5.** Liczyć kontrasty opisowe (stałe okno, koncowe, − los) także dla praw nieważnych, z oznaczeniem, jak w S-1b.
- **Z6.** Ułamek luki liczyć dodatkowo na wspólnym stałym oknie [d1, d1+50] (licznik i mianownik na tym samym oknie) i opisywać efekty < 0,1 luki
  jako praktycznie małe; opcjonalnie dopisać, że H jest oceniana kryterium „≥ 3/5”, a nie średnią po prawach.
- **Z7.** Mocniejszy bezpiecznik kodu: runner sprawdza, że kod w `matylda_rdzen/` nie zmienił się po ostatnim commicie prerejestracji
  (np. `git log -1 --format=%H -- PREREJESTRACJA_S0_HEUR.md` = `git log -1 --format=%H -- matylda_rdzen/` lub późniejszy tylko dla `wyniki/`).
- **Z8.** Czas: 640 przebiegów = 290 s, więc pełny przebieg 3 200 ≈ 25 min — warto to podać, żeby recenzent po wyniku mógł ocenić „jedno uruchomienie”
  po odstępie między commitami.

---

## 7. Tabela ustaleń

| # | Ustalenie | Klasyfikacja |
|---|---|---|
| 1 | Kod zgodny z prerejestracją we wszystkich punktach rozstrzygających; hash reguły się zgadza | WYNIK |
| 2 | „koncowe” = `krzywa[-1][1]` = pokrycie po d1+50; stałe okno poprawne (0 rozbieżności na 640 przebiegach) | WYNIK |
| 3 | `HEUR_SHA = None` blokuje runner do zamrożenia (fail-safe); poza regułą kod chroniony tylko post hoc | WYNIK |
| 4 | Ziarna 600–679 nadal zarezerwowane w `s1lmm.py` / `PREREJESTRACJA_S1_LMM.md` | WYNIK |
| 5 | Werdykt jednoznaczny; brak furtki lepsza+gorsza; < 3 ważnych → nieinformatywny | WYNIK |
| 6 | Etykieta NEGATYWNY dla „nierozstrzygnięta + nieinformatywny” za mocna | WNIOSKOWANIE |
| 7 | Moc: MDE 0,16–0,56 krawędzi TR przy n = 80; zapas duży; brak progu praktycznego | WYNIK |
| 8 | x(xy)=y w T1 to dual (yx)x=y z walidacji → w T1 realnie 4 nowe prawa | WYNIK + WNIOSKOWANIE |
| 9 | Światy S-0 w T1-4 to cel konstrukcji U4; silne nakładanie łączna/medialna/komutatywna; bez stronniczości między ramionami | WYNIK + WNIOSKOWANIE |
| 10 | W 4/5 światów S-0 cała TR dotyka węzłów-praw — reżim, który może sprzyjać regule; medialna najbliższa „trudnej” elastycznej | HIPOTEZA / SPEKULACJA |
| 11 | Brak śladu przebiegu `HeurystykaGrafu` na prawach S-0 | WYNIK |
