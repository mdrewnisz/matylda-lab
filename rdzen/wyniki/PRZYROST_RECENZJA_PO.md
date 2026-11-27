# Recenzja po wyniku: PRZYROST (walidacja heurystyki przyrostu pokrycia)

Niezależny recenzent (hostile review), nie autor testu. Przedmiot: `PREREJESTRACJA_PRZYROST.md` (zamrożona w 85f6d4d),
`matylda_rdzen/przyrost_walidacja.py`, `wyniki/przyrost_walidacja.json` (commit 6fa9438), kontekst: `wyniki/PRZYROST_RECENZJA_PRZED.md`,
`wyniki/przyrost_pilot*.json`, `wyniki/HEUR4_RECENZJA_PO.md`.
Skrypty i surowe wyjścia: `scratchpad/recenzja_przyrost_po/` (`repl.py` + `repl.log`: replikacja; `diag.py`, `an.py` + `an.out`: diagnostyka i dekompozycja;
`diag2.py` + `diag2.out`: pozycje z zyskiem 0). Diagnostyka mechanizmu używa **wyłącznie ziaren 1990–1999** (pula recenzji po; teraz zużyta).
Replikacja walidacji używa ziaren 1920–1979, ale przebiegi są deterministyczne, więc nie wnosi nowych danych, tylko sprawdza JSON.

**Werdykt integralności: czysto.** Kod między zamrożeniem a wynikiem jest niezmieniony. Hashe się zgadzają. Werdykt wynika z §6 i z danych.
Niezależna replikacja odtwarza JSON bit w bit. **Werdykt merytoryczny runnera jest poprawny:** WYNIK CZĘŚCIOWY (rząd 4: lepsza; rząd 3: nierozstrzygnięta).
Według §6 („Inaczej domyślna zostaje”) taki wynik **nie uruchamia** propozycji zmiany domyślnej intuicji.

---

## 1. Integralność

| Sprawdzenie | Wynik |
|---|---|
| `git diff --stat 85f6d4d 6fa9438` | zmienia się tylko `rdzen/wyniki/przyrost_walidacja.json` (nowy plik); HEAD = 6fa9438, drzewo czyste |
| `commit` w JSON | 85f6d4d…: uruchomienie na zacommitowanym zamrożeniu (runner odmawia przy brudnym drzewie) |
| `prerejestracja_sha256` w JSON | `0315429…1196` = sha256 obecnego `PREREJESTRACJA_PRZYROST.md` (plik nietknięty od 85f6d4d) |
| `kod_sha256` (14 plików z `KOD`) | identyczne z `przyrost_walidacja.SHA` i z sha256 plików w HEAD |
| `kod_sha256["przyrost_walidacja.py"]` | `9b5ad1a8…4506` = hash w §9 i hash pliku w HEAD |
| Parametry runnera | PRAWA = 5 praw z §4, SEEDS = 1920–1979, M = 1, 6 ramion (§5) |
| `pytest` | 32 passed (zgodnie z §8) |
| Replikacja (`repl.py`: `zbierz` + `analiza` z kodu zamrożonego) | 210/210 kontrastów identycznych (tolerancja 1e-9), `per_swiat` identyczne, `G` identyczne |

Ścieżka werdyktu według §6 (sprawdzona ręcznie z JSON):
- **T1 (rząd 3):** n = 5 ważnych (pula snu ≥ 0,98), próg 3.
  - gorsza: 0/5;
  - bramka: 5/5;
  - lepsza: 2/5 (`y(yy)=…`, `((xz)x)(zx)=x`).

  Kategoria: **nierozstrzygnięta**.
- **T1-4 (rząd 4):** n = 5 (pula ≥ 0,97); gorsza 0/5, bramka 5/5, lepsza 5/5. Kategoria: **lepsza**.
- Para (nierozstrzygnięta, lepsza) w tabeli Z1 daje WYNIK CZĘŚCIOWY dla rzędu 4. Zgodnie z `G`.

Uwagi drobne:
- „Jedno uruchomienie” jest niesprawdzalne kryptograficznie. Przy pełnym determinizmie (replikacja) ponowne uruchomienia nie mogłyby jednak zmienić wyniku bez zmiany kodu, a kod jest chroniony hashem. Ryzyko praktycznie zerowe.
- Pilot w §3 podaje dla rzędu 3 „< 0 w 0/10”. Dla `((xz)(zz)) = ((yx)(xy))` (231 magm) mam różnicę −0,24 i górną CI **dokładnie 0,0**, a pula snu była niepusta tylko w 6/10 ziaren, więc w walidacji to prawo byłoby nieważne.
  Opis jest formalnie prawdziwy, ale stoi na granicy. Na werdykt nie wpływa.

## 2. Interpretacja: co wolno, a czego nie wolno napisać

### Wolno (WYNIK, prerejestrowany)
- Na 5 prawach z **klasy większych termów**, w rzędzie 4, w protokole S-1b (sen 50 wywołań), `heur_przyrostu` (m = 1) jest lepsza od `heur_grafu` w M1 w 5/5 prawach.
  Bramka przeszła w 5/5.
- W rzędzie 3 wynik jest **nierozstrzygnięty**: 2/5 lepsza, 0/5 gorsza, bramka 5/5. Test był więc informatywny (bramka przeszła), a kryterium przewagi nie zostało spełnione.
- W żadnej z 10 komórek `heur_przyrostu` nie jest istotnie gorsza od `heur_grafu`. Najniższa średnia M1 to −0,11 [−0,31; 0,09] (T1, `(yx)(yx)=(yx)(yy)`).

### Wolno, ale z zastrzeżeniem (opisowe kontrasty z §6)
- **Wielkość efektu w rzędzie 4 jest bardzo niejednorodna.** Ułamek luki na stałym oknie (do zachłannej wyroczni przyrostu, nie „do optimum”) w kolejności praw z §4:
  - 0,60 [0,54; 0,65];
  - 0,18 [0,16; 0,21];
  - 0,51 [0,46; 0,54];
  - 0,90 [0,85; 0,94];
  - 0,06 [0,02; 0,10].

  Mediana 0,51. „Lepsza 5/5” nie znaczy „zamyka połowę luki”: dla `(yx)(yx)=(yx)(yy)` efekt jest realny, ale znikomy (M1 +0,13 [0,04; 0,22]).
- **Efekt dotyczy tempa, nie stanu końcowego.** Pokrycie końcowe `heur_przyrostu − heur_grafu` w rzędzie 4 wynosi 0,00–0,07, a w rzędzie 3 0,00–0,97 (wszystkie CI zawierają 0 albo dotykają 0).
  Wolno napisać „szybciej pokrywa TR w budżecie snu”. Nie wolno pisać „odkrywa więcej”.
- **Replikacja `heur_grafu − heurystyka`.** Lepsza w 9/10 komórek. W T1-4 `x(z(xx)) = z(xx)` jest istotnie gorsza: −1,84 [−2,11; −1,59].
  W tej samej komórce `heur_przyrostu − heurystyka` = −0,71 [−1,03; −0,40], czyli nowa reguła też przegrywa ze **starą** linią bazową.
  Kto proponuje zmianę domyślnej, musi to podać.
- **Nowa bramka nie dominuje starej wszędzie.** `wyrocznia_przyrostu − wyrocznia_pokrycia` jest w M1 dodatnia w 8/10 komórek. W T1 `((zx)x)x=(xz)x` wynosi −0,06 [−0,12; −0,01], a w T1-4 `(yx)(yx)` jest bliska 0.
  Pokrycie końcowe w T1 `y(yy)` wynosi −0,85 [−1,52; −0,27]. Zgodnie z §2: to dolne oszacowanie sufitu, nie sufit.

### Nie wolno
- Pisać, że H jest potwierdzona („lepsza w M1, w rzędzie 3 i w rzędzie 4”). H wymagała obu rzędów.
- Pisać, że w rzędzie 3 „nie ma efektu” albo że wynik jest „negatywny”. W tabeli §6 para (nierozstrzygnięta, lepsza) daje CZĘŚCIOWY, a nie NEGATYWNY dla rzędu 3.
  Średnie M1 w rzędzie 3 wynoszą +0,65, +0,15, +0,03, +3,21, −0,11. Żadna nie jest istotnie ujemna, dwie są istotnie dodatnie.
- Pisać, że heurystyka „działa w rzędzie 3”, bo 2/5 < 3/5.
- Przenosić wynik na klasę dev (≤ 4 działania), na inne słowniki, na rząd ≥ 5 albo na „intuicję” w ogóle. Wynik obejmuje 5 praw z jednej klasy i jednego generatora (§4, „Interpretacja z góry”).
- Używać ułamka luki jako „% do optimum” (§6, Z2).

### Rząd 3: „brak efektu”, „brak przeniesienia” czy coś innego?
§4 przewidział z góry tylko dwie lekcje: brak efektu albo brak przeniesienia na klasę większych termów. Dane wskazują na **trzecią możliwość, której §4 nie nazwał**:
efekt jest **moderowany przez świat**, a konkretnie przez to, jak duża część puli snu jest prawdziwa i jak dobrze znane magmy szacują porządek.
Status tej interpretacji: HIPOTEZA z mocnym wsparciem diagnostycznym (§3), nieprerejestrowana.

- **„Brak przeniesienia na klasę” jest mało prawdopodobny jako główne wyjaśnienie.** Pilot był z **tej samej klasy** (generator 9393) i w rzędzie 3 dał 9/10.
  Różnica między pilotem a walidacją leży w **rozmiarach światów**, nie w klasie termów (WYNIK, liczby z `przyrost_pilot_prawa.json` i §4):
  - pilot, rząd 3: 63–1242 magm, mediana ok. 135; tylko 1/10 ma ≥ 529;
  - walidacja, rząd 3: 105, 529, 854, 872, 1845; 4/5 ma ≥ 529.

  Jedyny duży świat pilotu (1242 magm) dał najmniejszy dodatni ułamek luki w pilocie rzędu 3 (ok. 0,14, opisowo, z pola).
  W walidacji jedyny mały świat (105 magm) dał 0,95, a duże ≤ 0,18. Dev rzędu 3 był mały (mediana 74/216 magm). Recenzja przed (B2) zgłosiła to przesunięcie, a pilot go nie pokrył.
- **Rozbieżność pilot (9/10) a walidacja (2/5) nie jest więc sprzecznością.** Pilot pochodził z innego rozkładu rozmiarów świata.
- **Sam rozmiar świata nie wystarcza jako wyjaśnienie.** W rzędzie 4 światy 494–585 magm dają ułamek 0,18–0,60, a w pilocie rzędu 4 światy 233 i 306 dawały ok. 0.
  Bliższą zmienną jest odsetek prawdziwych kandydatur w puli, czyli udział „prawdy” w przewadze wyroczni (§3 niżej).

## 3. Diagnostyka mechanizmu (WYNIK diagnostyczny, nieprerejestrowany; ziarna 1990–1999, wszystkie 10 komórek)

### 3.1. Dekompozycja przewagi wyroczni
Dodałem trzy ramiona kontrolne (`diag.py`; tylko w recenzji, nie w kodzie rdzenia):
- **prawda+graf**: prawdziwe kandydatury w kolejności grafu, fałszywe na końcu (sama wiedza o prawdzie, bez TR);
- **TR+wszystkie**: zachłanny przyrost na **prawdziwym** TR wśród wszystkich kandydatur, bez filtra prawdy (sama wiedza o porządku);
- **TRhat+prawda**: TR̂ badacza, ale tylko wśród prawdziwych (porządek szacowany plus prawda).

M1 względem `heur_grafu`, 10 ziaren, oraz udział w przewadze wyroczni (W):

| Komórka | magmy | M1 prz | M1 W | prawda+graf / W | TR+wszystkie / W | TRhat+prawda / W | ułamek luki (walidacja) |
|---|---|---|---|---|---|---|---|
| T1 `y(yy)=…` | 872 | 1,09 | 4,24 | 0,57 | 0,73 | 0,92 | 0,18 |
| T1 `x(z(xx))=z(xx)` | 854 | 0,20 | 3,27 | **0,94** | 0,62 | 0,98 | 0,14 |
| T1 `((zx)x)x=(xz)x` | 529 | 0,01 | 2,08 | **0,95** | 0,86 | 0,96 | 0,00 |
| T1 `((xz)x)(zx)=x` | 105 | 3,61 | 4,41 | **0,13** | 0,91 | 0,71 | 0,95 |
| T1 `(yx)(yx)=(yx)(yy)` | 1845 | 0,17 | 4,75 | **0,91** | 0,61 | 0,93 | −0,03 |
| T1-4 `y(yy)=…` | 565 | 2,69 | 4,83 | 0,60 | 1,02 | 0,62 | 0,60 |
| T1-4 `x(z(xx))=z(xx)` | 494 | 1,10 | 6,28 | 0,78 | 0,29 | 0,92 | 0,18 |
| T1-4 `((zx)x)x=(xz)x` | 585 | 1,14 | 2,63 | 0,55 | 0,85 | 0,92 | 0,51 |
| T1-4 `((xz)x)(zx)=x` | 58 | 0,96 | 1,09 | 0,29 | 1,10 | 1,00 | 0,90 |
| T1-4 `(yx)(yx)=(yx)(yy)` | 809 | 0,19 | 2,68 | 0,95 | 0,77 | 1,01 | 0,06 |

Na ziarnach recenzji kierunek `heur_przyrostu − heur_grafu` replikuje walidację w każdej komórce.

**Odpowiedź na pytanie „prawda czy wybór”.** Tam, gdzie `heur_przyrostu ≈ heur_grafu` (T1 `((zx)x)x`, T1 `(yx)(yx)`, T1 `x(z(xx))`), wyrocznia wygrywa **prawie wyłącznie dzięki prawdzie**:
sam filtr prawdy przy kolejności grafu daje 91–95% jej przewagi.
Tam, gdzie heurystyka działa (`((xz)x)(zx)=x`, 105 i 58 magm), przewaga wyroczni bierze się z **wyboru/kolejności** (sama prawda daje 13–29%), a TR̂ to odtwarza.
Korelacja rang (10 komórek) między ułamkiem luki w walidacji a udziałem „prawdy” wynosi **ρ = −0,89**; z odsetkiem prawdziwych w puli **+0,84**; ze zgodnością TR̂ z TR **+0,83**; z rozmiarem świata −0,62.
TRhat+prawda ≈ W (0,62–1,01): **gdy prawda jest dana, szacowany porządek prawie wystarcza.** Brakuje rozróżniania prawdziwych od fałszywych.

### 3.2. Dlaczego TR̂ nie może tego dać (WNIOSKOWANIE z kodu, potwierdzone liczbami)
Kandydatury puli snu (`SenPelny`: powtórka ze wsparciem ≥ 2, śmiałe ze wsparciem 1) są z definicji implikacjami **bez kontrprzykładu wśród znanych magm**.
Są więc wszystkie w Ê, które przy m = 1 liczy się z tych samych magm (`porzadek_empiryczny`).
TR̂ **nie zawiera żadnej informacji o tym, która kandydatura z puli jest prawdziwa**. Heurystyka przyrostu może odtworzyć tylko składową „kolejność” przewagi wyroczni, nigdy składową „prawda”.
W liczbach (pierwsze 3 komórki rzędu 3, ścieżka `heur_przyrostu`):
- z kandydatur z zyskiem TR̂ > 0 (15–22 na sen) **10–16 jest fałszywych**;
- z ok. 8 pozycji paczki wybranych po zysku TR̂ > 0 prawdziwe są ok. 3,2–3,7 (≈ 40%);
- w `((xz)x)(zx)=x` (T1) prawdziwe są 5,5/7,3 (75%).

### 3.3. Jakość TR̂ (pytanie zlecenia)
| Komórka (T1) | znane magmy / świat | precyzja Ê | \|TR̂\| / \|TR\| | Spearman zysków TR̂ ~ TR w puli |
|---|---|---|---|---|
| `x(z(xx))` | 43 / 854 | 0,77 | 43 / 69 | 0,21 |
| `((zx)x)x` | 42 / 529 | 0,73 | 36 / 70 | 0,39 |
| `(yx)(yx)` | 43 / 1845 | 0,60 | 37 / 74 | 0,21 |
| `((xz)x)(zx)` (kontrast) | 31 / 105 | 0,91 | 39 / 74 | 0,83 |

Badacz zna ok. 40 magm, czyli 2–8% dużego świata. Ê zawiera wtedy 23–40% fałszywych implikacji, a TR̂ ma mniej więcej połowę krawędzi TR (klasy są zlepione).
Zgodność zysków z prawdziwymi jest słaba. W małym świecie (30% świata znane) TR̂ jest dobrym przybliżeniem.

### 3.4. Zysk 0, wielkość i skład puli
- **Remisy nie dominują** (`diag2.out`). W paczce `heur_przyrostu` 7–9 z ok. 9–10 pozycji wybiera zysk TR̂ > 0. Na graf (zysk 0) przypada tylko 0,4–0,7 pozycji w nieudanych komórkach rzędu 3 i 2,4 w `((xz)x)(zx)`.
  `heur_przyrostu ≈ heur_grafu` nie wynika więc z tego, że reguła „oddaje” wybór grafowi. Obie reguły wybierają w 7,1–7,4 z 10 te same kandydatury, a różniące się 2–3 mają podobną (niską) prawdziwość.
  Zrealizowany zysk paczki na tej samej puli: `heur_przyrostu` +0,2–0,4 krawędzi TR na sen względem grafu, wyrocznia ok. +2–4.
- **Pula jest mała i w większości fałszywa:**

  | Komórka (T1) | kandydatur w puli | śmiałe | prawdziwe |
  |---|---|---|---|
  | `((zx)x)x` | 23 | 70% | 39% |
  | `(yx)(yx)` | 41 | 65% | 35% |
  | `x(z(xx))` | 27 | 38% | 42% |
  | `((xz)x)(zx)` (kontrast) | 48 | 47% | 81% |

  „Zdominowana przez śmiałe” pasuje do dwóch z trzech komórek. Prawdziwość śmiałych (37–38%) nie różni się jednak wyraźnie od prawdziwości powtórki (30–43%), więc to nie śmiałe są przyczyną.
  Przyczyną jest niski odsetek prawdziwych w całej puli.
- Czwarte pytanie zlecenia (czy wyrocznia wygrywa dzięki prawdzie, czy dzięki wyborowi) jest rozstrzygnięte w §3.1: w nieudanych komórkach rzędu 3 dzięki prawdzie.

Konsekwencja dla bramki (WNIOSKOWANIE): w dużych światach rzędu 3 „luka do wyroczni przyrostu” to w ok. 90% luka **wiedzy o prawdzie**, której żadna reguła oparta tylko na Ê nie zamknie.
Bramka spełniła swoją rolę (test był czuły), ale ułamek luki w takich światach zaniża to, co heurystyka osiągnęła w składowej „kolejność”.
Na przyszłość warto raportować bramkę rozbitą na prawda+graf i TR+wszystkie.

## 4. Rekomendacja (decyzja należy do Michała)

1. **Nie zastępować domyślnej intuicji w całości.** Prerejestracja (§6, „Skutek”) wiąże propozycję zmiany z werdyktem WYNIK. Werdykt jest CZĘŚCIOWY, więc zgodnie z §6 **domyślna zostaje**.
2. **Zmiana tylko w rzędzie 4 jest do obrony, ale tylko jako jawna decyzja poza §6.** Przemawia za nią: 5/5 lepsza, bramka 5/5 i 0/10 gorsza w obu rzędach.
   Przeciw albo ze zastrzeżeniem:
   - 5 praw z jednej klasy;
   - efekt w tempie, nie w pokryciu końcowym;
   - ułamek luki od 0,06 do 0,90;
   - w T1-4 `x(z(xx))` zarówno `heur_przyrostu`, jak i `heur_grafu` przegrywają ze starą heurystyką ogólności.

   Jeśli Michał się zdecyduje, w kodzie i w MATYLDA_RDZEN trzeba zapisać, że to decyzja na podstawie WYNIKU CZĘŚCIOWEGO, ograniczona do rzędu 4.
   Moja rekomendacja: **tak dla rzędu 4, z tym opisem; w rzędzie 3 bez zmian.** Argument pragmatyczny „jedna reguła wszędzie, bo nigdzie nie szkodzi” jest uczciwy, ale dowodu w rzędzie 3 nie ma.
3. **Co rozstrzygnęłoby rząd 3:**
   - (a) nowa prerejestracja z prawami **warstwowanymi po rozmiarze świata**, np. ≥ 5 praw < 300 magm i ≥ 5 praw ≥ 500 magm.
     Hipotezy osobno na warstwę i z góry zapisana hipoteza moderacji (ułamek luki maleje z odsetkiem fałszywych w puli). Nowe ziarna, bo 1990–1999 są zużyte;
   - (b) więcej praw: przy n = 5 i progu 3 wynik 2/5 jest kruchy, a w dużych światach efekt to +0,03–0,15 M1, więc potrzeba większej mocy (więcej ziaren albo praw);
   - (c) merytorycznie: brakującą składową jest **rozróżnianie prawdy w puli**, nie lepszy TR̂.
     Kierunek dev (HIPOTEZA): oczekiwany zysk = P̂(prawdziwa) × zysk TR̂, gdzie P̂ pochodzi np. z wsparcia przesłanki względem liczby znanych magm albo z sygnału grafu.
     Wymaga to osobnego dewelopmentu i bramki rozbitej na prawdę i kolejność (§3.4).

## 5. Klasyfikacja ustaleń

| Ustalenie | Klasa |
|---|---|
| Kod niezmieniony między 85f6d4d a 6fa9438; hashe (14 plików + runner, §9) i sha prerejestracji zgodne; 32 testy przechodzą | WYNIK |
| Replikacja odtwarza 210/210 kontrastów, kategorie i `G` bit w bit | WYNIK |
| Werdykt „WYNIK CZĘŚCIOWY (rz. 3 nierozstrzygnięta, rz. 4 lepsza)” wynika z §6 | WYNIK |
| Rząd 4: lepsza 5/5, bramka 5/5 (klasa większych termów) | WYNIK |
| Rząd 3: lepsza 2/5, gorsza 0/5, bramka 5/5, więc nierozstrzygnięta; H (oba rzędy) niepotwierdzona | WYNIK |
| 0/10 komórek istotnie gorszych od heur_grafu | WYNIK |
| Ułamek luki w rz. 4: 0,06–0,90 (mediana 0,51); pokrycie końcowe bez różnic | WYNIK (opisowe) |
| T1-4 `x(z(xx))`: heur_grafu i heur_przyrostu istotnie gorsze od starej heurystyki | WYNIK (opisowe) |
| Wyrocznia przyrostu nie dominuje starej wyroczni wszędzie (T1 `((zx)x)x`: −0,06) | WYNIK (opisowe) |
| Rząd 3 nie jest „wynikiem negatywnym” ani „brakiem efektu” w sensie §6 | WNIOSKOWANIE (z tabeli §6 i danych) |
| W nieudanych komórkach rz. 3 przewaga wyroczni pochodzi w 91–95% z wiedzy o prawdzie; w udanych z kolejności | WYNIK diagnostyczny (ziarna 1990–1999, nieprerejestrowany) |
| Pula snu ⊆ Ê, więc TR̂ nie niesie informacji o prawdzie kandydatur | WNIOSKOWANIE (z kodu) + WYNIK diagnostyczny (10–16 fałszywych z zyskiem TR̂ > 0 na sen) |
| Remisy (zysk 0) nie tłumaczą równości z grafem: 7–9 pozycji paczki z zyskiem > 0; nakładanie z grafem ok. 7/10 | WYNIK diagnostyczny |
| Jakość TR̂ w dużych światach słaba (precyzja Ê 0,60–0,77, Spearman 0,21–0,39) | WYNIK diagnostyczny |
| Pilot rz. 3 (9/10) a walidacja (2/5): różny rozkład rozmiarów świata (pilot mediana ok. 135, walidacja 4/5 ≥ 529) | WYNIK (liczby) |
| Efekt moderowany przez odsetek prawdziwych w puli / rozmiar świata, nie przez klasę termów | HIPOTEZA (post hoc, 10 komórek, ρ = −0,89 / +0,84) |
| W 3/5 praw rz. 3 (`x(z(xx))`, `((zx)x)x`, `(yx)(yx)`) heur_przyrostu nie odróżnia się od grafu (M1 −0,11…+0,15, ułamek luki −0,03…0,14): HIPOTEZA 13 (zamknięcie dużej części luki) nie sprawdza się w dużych światach rz. 3 | WYNIK NEGATYWNY (per prawo, opisowy; nie werdykt §6) |
| „Brak przeniesienia na klasę większych termów” jako główne wyjaśnienie rz. 3 | SPEKULACJA, mało prawdopodobna (pilot z tej samej klasy dał 9/10) |
| Kierunek P̂(prawdziwa) × zysk TR̂ zamknie lukę w dużych światach | SPEKULACJA |
| Zmiana domyślnej tylko w rz. 4 jako decyzja poza §6 | rekomendacja recenzenta (nie wynik) |
