# Recenzja po wyniku: ROZMIAR3 (rząd 3 według rozmiaru świata)

Niezależny recenzent (hostile review), nie autor testu. Przedmiot: `PREREJESTRACJA_ROZMIAR3.md` (zamrożona w 7029a27), `matylda_rdzen/rozmiar3_walidacja.py`,
`wyniki/rozmiar3_walidacja.json` (commit 1ed301b), `wyniki/rozmiar3_prawa.json`. Kontekst: `wyniki/ROZMIAR3_RECENZJA_PRZED.md`, `wyniki/PRZYROST_RAPORT.md`,
`wyniki/PRZYROST_RECENZJA_PO.md`, `wyniki/przyrost_walidacja.json`, `wyniki/przyrost_pilot*.json`.

Skrypty i surowe wyjścia leżą poza repo, w `scratchpad/recenzja_rozmiar3_po/`:
- `repl.py` + `repl.log`: replikacja walidacji;
- `diag.py`, `an.py` + `an.out`, `d_T1_*.pkl`: diagnostyka mechanizmu.

Diagnostyka używa **wyłącznie ziaren 2080–2089** (pula recenzji po, od teraz zużyta). Replikacja używa ziaren 2010–2069, ale przebiegi są deterministyczne, więc tylko sprawdza JSON i nie wnosi nowych danych.

**Werdykt integralności: czysto.** Między zamrożeniem a wynikiem kod się nie zmienił, a wszystkie hashe się zgadzają. Replikacja odtwarza JSON bit w bit.
Werdykt runnera wynika z tabeli §4.
Znalazłem trzy usterki opisu, żadna nie wpływa na werdykt:
- błędna etykieta pola JSON;
- inna liczba podziałów w teście permutacyjnym niż w tekście;
- inny zrealizowany zakres MAŁYCH niż w tekście.

**Werdykt merytoryczny runnera jest poprawny:** „WYNIK: lepsza w małych i w dużych; różnica wielkości niewykazana”.
H_mod (efekt większy w małych) **nie jest potwierdzona**: I = +0,30, p_perm = 0,40.

---

## 1. Integralność

| Sprawdzenie | Wynik |
|---|---|
| `git diff --stat 7029a27 1ed301b` | jedyna zmiana to nowy plik `rdzen/wyniki/rozmiar3_walidacja.json`; drzewo czyste |
| `commit` w JSON | `7029a27…`, czyli uruchomienie na zacommitowanym zamrożeniu |
| `prerejestracja_sha256` w JSON | `220e9e44…63fc` = sha256 `PREREJESTRACJA_ROZMIAR3.md` w 7029a27 i w HEAD |
| `kod_sha256` (20 plików z `KOD`) | identyczne z `rozmiar3_walidacja.SHA` i z sha256 plików w HEAD |
| `kod_sha256["rozmiar3_walidacja.py"]` | `7f119a4b…654f` = RUNNER_SHA256 w §9 = sha pliku w 7029a27 i w HEAD |
| Lista praw | sha256 `wyniki/rozmiar3_prawa.json` = `5bf95814…9eb3` = PRAWA_SHA256 w §2 |
| Status | linia `Status: **ZAMROŻONA**` (B1); runner sprawdza ją regexem |
| `pytest` | 35 passed (zgodnie z §6) |
| Replikacja (`repl.py`: `zbierz` + `analiza` z zamrożonego kodu) | 135/135 kontrastów identycznych (tol. 1e-9); `grupy`, `G`, `interakcja` i `roznice_per_ziarno` identyczne |

### Ścieżka werdyktu (sprawdzona ręcznie z JSON wobec §4 i `heur4_walidacja.kategoria`)
- **MAŁE.** Z 7 praw ważne są 4. Odpadły `y(zz)=…` (99 magm, pula 1. snu w 0,85 ziaren), `(xx)x=…` (133 magm, 0,85) i `((yx)(xy))z=…` (67 magm, 0,75).
  - Analizowane: `x(y(xy))=(yx)x`, `(((yy)x)y)y=xy` oraz **obie rezerwy**: `(z(yx))(yz)=(zz)z` i `y(xy)=(yz)((zy)y)`.
  - n = 4, więc reguła „n < 4 → nieinformatywny” nie zachodzi.
  - Próg 0,6 · 4 = 2,4, czyli trzeba 3 praw.
  - gorsza 0/4, bramka 4/4, lepsza 3/4. Kategoria: **lepsza**. Zgodne z §4 („n = liczba ważnych praw, próg 60% n”) i z kodem `kategoria`.
- **DUŻE.** Ważne są wszystkie 7; analizowane pierwsze 5. gorsza 0/5, bramka 5/5, lepsza 5/5. Kategoria: **lepsza**.
- **Interakcja.** I = 0,301; p_perm = 50/126 = 0,397; bootstrap CI95 [−1,77; 2,44]. Brak moderacji.
- Rząd tabeli §4: (lepsza, lepsza, nie). Wynika z niego „WYNIK: lepsza w obu, różnica wielkości niewykazana”, a skutek to „heurystyka przyrostu domyślna w całym rzędzie 3 (propozycja do decyzji Michała)”. Zgodne z `G`.

### Usterki (nieblokujące)
1. **Pole `rezerwowe_niewykorzystane` jest źle nazwane.** Kod liczy `[H for H in lista if H not in wazne]`, czyli sumę praw nieważnych i ważnych, ale nieużytych.
   - W MAŁYCH są tam 3 prawa **nieważne** z pierwszej piątki. Żadna rezerwa nie została niewykorzystana, bo obie weszły do analizy.
   - W DUŻYCH etykieta jest akurat prawdziwa: dwie ważne rezerwy, nieanalizowane.

   To **tylko błąd etykiety**. Analiza i werdykt biorą `prawa_wazne`, a pole `waznosc` pozwala odtworzyć prawdę.
   Raport musi jednak wprost podać zamiany (wymagał tego B4 w recenzji przed): „w MAŁYCH 3 z 5 pierwszych praw nieważne; weszły obie rezerwy; n = 4”.
2. **Test permutacyjny ma 126, a nie 252 podziały.** §4 pisze „wszystkie C(10, 5) = 252 podziały” i „najmniejsze osiągalne p = 1/252”, zakładając 5 + 5 praw.
   Zamrożony kod liczy C(n_m + n_d, n_m), zgodnie z własnym docstringiem, czyli C(9, 4) = 126 przy 4 + 5. Najmniejsze osiągalne p wynosi więc 1/126.
   Kod realizuje intencję tekstu („wszystkie podziały”); liczba w tekście była warunkowa i nie przewidziała n = 4. Przy p = 0,40 rozbieżność nie ma znaczenia.
   Raport powinien ją odnotować.
3. **Zrealizowany zakres MAŁYCH to 118–172 magm (średnio 142),** a nie 67–146, jak podaje §2 (Z4).
   Odpadły trzy z czterech najmniejszych światów (67, 99, 133). Wynik MAŁYCH dotyczy więc wąskiego pasma około 120–170 magm, a nie przedziału 20–300.
   Do tego są to światy, w których pula 1. snu jest niemal zawsze niepusta.
4. (drobne) **Zalecenia Z1 i Z6 nie zostały wdrożone.** §4 nie zawiera interakcji na ułamku luki ani na M1/|TR|. Podaję je niżej opisowo.
   Runner nie zapisuje też składu puli. Dlatego §3 tej recenzji musiała puścić osobne przebiegi.

**Kruchość kategorii MAŁE (WNIOSKOWANIE).** n = 4 to dolna granica. Wystarczyłoby jedno prawo nieważne więcej i MAŁE byłyby nieinformatywne, a cały test dałby NIEINFORMATYWNY.
Wystarczyłoby też jedno prawo z „lepsza” mniej (2/4 < 2,4), żeby werdykt brzmiał „H_mod NIEPOTWIERDZONA”.
Najsłabsze „lepsza” w MAŁYCH to `y(xy)=…`: M1 +0,51 [0,20; 0,87], więc nie leży na granicy. Kategoria jest formalnie poprawna, ale stoi na 3 prawach.

---

## 2. Interpretacja: co wolno napisać

### Wolno (WYNIK, prerejestrowany)
- W rzędzie 3, na prawach z klasy większych termów (generator 9494), `heur_przyrostu` (m = 1) jest w M1 lepsza od `heur_grafu`:
  - w **3/4** ważnych praw MAŁYCH (118–172 magm);
  - w **5/5** praw DUŻYCH (545–1516 magm).
- Bramka przeszła 9/9. Żadne prawo nie jest istotnie gorsze.
- Różnica wielkości efektu między przedziałami **nie jest wykazana** (I = +0,30 M1, p = 0,40; CI bootstrapu [−1,77; 2,44]).

### Wolno, z zastrzeżeniem (opisowo, z JSON)

| Prawo | magmy | \|TR\| | M1 przyrost − graf | luka (stałe okno) | zapas wyroczni (M1) | pokrycie końcowe |
|---|---|---|---|---|---|---|
| małe `x(y(xy))=(yx)x` | 146 | 57 | +0,04 [−0,06; 0,13] | 0,09 | 0,70 | 0,00 |
| małe `(((yy)x)y)y=xy` | 132 | 82 | +4,64 [4,34; 4,98] | 0,83 | 5,68 | 0,00 |
| małe `(z(yx))(yz)=(zz)z` (rez.) | 172 | 78 | +2,73 [2,23; 3,23] | 0,68 | 4,07 | +0,02 |
| małe `y(xy)=(yz)((zy)y)` (rez.) | 118 | 80 | +0,51 [0,20; 0,87] | 0,40 | 1,93 | −0,03 |
| duże `y((xx)(xy))=y(yy)` | 1516 | 90 | +0,34 [0,04; 0,64] | 0,11 | 4,49 | **+1,68 [0,88; 2,50]** |
| duże `(zz)((zy)z)=z` | 766 | 72 | +1,33 [0,90; 1,78] | 0,25 | 5,09 | **+1,73 [0,38; 2,93]** |
| duże `x(zx)=z(x(zx))` | 774 | 80 | +4,06 [3,17; 4,94] | 0,75 | 5,98 | **+4,38 [3,13; 5,67]** |
| duże `(x(x(xy)))y=yy` | 545 | 78 | +1,68 [1,40; 1,98] | 0,30 | 5,74 | **+0,87 [0,27; 1,47]** |
| duże `x(zy)=x(z((zy)x))` | 711 | 71 | +0,98 [0,81; 1,15] | 0,27 | 3,19 | −0,07 |

- **„Lepsza 5/5” w DUŻYCH to w 4/5 praw efekt mały, ale precyzyjnie oszacowany** (60 ziaren): od 0,11 do 0,30 luki. Tylko `x(zx)=z(x(zx))` zamyka dużą część luki (0,75).
  Kategoria „lepsza” znaczy „CI > 0”, a nie „duża przewaga”.
- **Interakcje drugorzędne (Z1; nieprerejestrowane, opisowe).**
  - Średni ułamek luki: MAŁE 0,50, DUŻE 0,34 (mediany 0,54 i 0,27).
  - M1/|TR|: 0,025 wobec 0,022.

  Na skali względnej różnica idzie w kierunku H_mod, ale jest mała i bez testu. Na skali surowej DUŻE mają większy zapas wyroczni (3,2–6,0 wobec 0,7–5,7), co działa przeciw H_mod.
- **W DUŻYCH efekt nie dotyczy tylko tempa.** Pokrycie końcowe jest wyższe w 4/5 praw DUŻYCH (CI > 0), a w MAŁYCH równe, bo małe światy się nasycają.
  To odróżnia ROZMIAR3 od PRZYROST, gdzie pokrycie końcowe było „w praktyce równe”. Formuła „zysk tylko w tempie” nie przenosi się więc na duże światy rzędu 3 z tego testu.
- **Jedyne „zero” w MAŁYCH (`x(y(xy))=(yx)x`) to efekt sufitu, nie porażka heurystyki.** Zapas wyroczni wynosi tylko 0,70 M1. Na ziarnach 2080–2089:
  - pokrycie TR na starcie snu wynosi średnio 51 z 57 krawędzi;
  - jest średnio 1,9 snu na przebieg.

  Prawie nie ma czego wygrywać (§3).

### Nie wolno
- Pisać, że H_mod jest potwierdzona, ani że „efekt jest większy w małych światach”. Prerejestrowane kryterium (p_perm < 0,05) nie jest spełnione.
- Pisać, że wykazano **brak** moderacji. Moc była niska: przy 4 + 5 prawach i rozrzucie M1 między prawami 0,04–4,6 test praktycznie nie wykryłby umiarkowanej interakcji.
  Właściwe sformułowanie: „różnica niewykazana”.
- Przypisywać cokolwiek **rozmiarowi** jako przyczynie. §2 zastrzegło, że przedziały różnią się też |TR| i trafnością puli. §3 pokazuje, że trafność puli rozjeżdża się z rozmiarem.
- Uogólniać „MAŁE” na 20–300 magm. Zrealizowano 118–172 (pkt 1.3).
- Pisać, że „wynik PRZYROST w rzędzie 3 był błędny” albo że „ROZMIAR3 obala PRZYROST” (niżej).
- Przenosić wynik na klasę dev (≤ 4 działania), inne słowniki, rząd ≥ 5 albo na „intuicję” w ogóle.
- Czytać ułamek luki jako „% do optimum”.

### Jak pogodzić PRZYROST (duże ≈ 0 w 3/4) z ROZMIAR3 (duże 5/5 lepsza)?

To **ani replikacja niepowodzenia, ani jego obalenie**. Najprostsze wyjaśnienie zgodne z danymi (WNIOSKOWANIE):
efekt w dużych światach rzędu 3 jest **silnie niejednorodny między prawami**, zwykle mały i dodatni, czasem zerowy, a rzadko duży.
Która kategoria wyjdzie przy 4–5 losowych prawach, to w dużej mierze kwestia tego, **które prawa wylosowano**.

- **Prawa są inne.** Żadne prawo nie powtarza się między testami: lista zakazana wykluczała prawa PRZYROST, a Jaccard < 0,5.
  ROZMIAR3 nie powtarzał więc pomiaru na tych samych prawach. Zerowe prawa PRZYROST pozostają zerowe: na nowych ziarnach 2080–2089 `((zx)x)x` daje +0,07 [−0,10; 0,26], a `(yx)(yx)` −0,27 [−0,95; 0,29].
  Zero w tamtych prawach jest więc **replikowalną cechą prawa**, nie przypadkiem ziaren (WYNIK diagnostyczny).
- **Wielkość efektu w obu testach jest podobna.** Niezerowe duże prawa PRZYROST miały lukę 0,14 i 0,18, a 4/5 dużych ROZMIAR3 ma 0,11–0,30.
  Różnica kategorii wynika głównie z tego, że PRZYROST trafił **dwa prawa z dokładnym zerem** (luka ≈ 0) i jedno graniczne (`x(z(xx))`: +0,15 [−0,01; 0,32]). ROZMIAR3 nie trafił żadnego zerowego i trafił jedno silne.
- **Losowość praw wystarcza jako wyjaśnienie (SPEKULACJA ilościowa).** Łącznie 7 z 10 dużych praw (niżej) ma CI > 0. Jeśli przyjąć p ≈ 0,7 na prawo, to:
  - P(≤ 1/4 lepsza) ≈ 0,08;
  - P(5/5 lepsza) ≈ 0,17.

  Oba wyniki są mało prawdopodobne, ale nie na tyle, żeby wymagały różnych mechanizmów. Recenzja przed szacowała P(DUŻE lepsza) ≈ 0,54.
- **Inne cechy światów.**
  - |TR| w DUŻYCH ROZMIAR3 wynosi 71–90, w dużych PRZYROST ok. 69–74 (tam, gdzie znane z diagnostyki). Różnica jest niewielka.
  - Zrealizowane rozmiary są porównywalne: 545–1516 wobec 529–1845.

  Rozmiar ani |TR| nie odróżniają więc prawa z efektem od prawa bez niego. Odróżnia je **trafność puli i precyzja Ê** (§3).
- **Co z hipotezy moderacji zostaje (HIPOTEZA, osłabiona):** zmienną moderującą nie jest rozmiar świata, tylko to, jak dobrze badacz szacuje porządek z ok. 40 znanych magm.
  Rozmiar jest z tym skorelowany, ale słabo. Kontrprzykład to `x(zx)=z(x(zx))`: 774 magm, a zachowuje się jak „mały świat” (§3).

### Łączna suma dowodów dla rzędu 3, klasa większych termów (agregacja POST HOC, opisowa, bez testu)

Źródła są niejednorodne:
- pilot PRZYROST: 10 ziaren, pole M1 z `przyrost_pilot.json`;
- PRZYROST T1 i ROZMIAR3: 60 ziaren.

PRZYROST i pilot **wygenerowały** hipotezę, więc wliczanie ich do jej „potwierdzenia” jest podwójnym użyciem danych. Konfirmacyjny jest wyłącznie ROZMIAR3.
„Istotnie > 0” oznacza dla pilota |t| > 2 przy 10 ziarnach, dla pozostałych CI95 > 0.

| Przedział | Prawa (źródła) | Istotnie > 0 | ≈ 0 / niejasne | Istotnie < 0 | M1 średnio (mediana) | ułamek luki, mediana |
|---|---|---|---|---|---|---|
| < 300 magm | 14: PRZYROST 1 (105), pilot 9 (63–251), ROZMIAR3 4 | 10 | 4: `x(y(xy))` (sufit); pilot 67 i 75 (t ≈ 1,8–1,9); pilot 231 (−0,40, t ≈ −1,8, pula 6/10, czyli nieważne) | 0 | 2,03 (2,26) | ≈ 0,75 |
| ≥ 500 magm | 10: PRZYROST 4, pilot 1 (1242), ROZMIAR3 5 | 7 | 3: `((zx)x)x`, `(yx)(yx)`, `x(z(xx))` (granica) | 0 | 0,96 (0,58) | ≈ 0,16 |

Dla pilota ułamek luki liczyłem na polu M1, a nie na stałym oknie, więc wartości są tylko orientacyjne.

Opis:
- Na 24 prawach rzędu 3 z tej klasy **żadne nie jest istotnie gorsze** od grafu.
- Przewaga występuje w ok. 70% praw w obu przedziałach.
- Typowa wielkość efektu w dużych światach jest wyraźnie mniejsza: mediana M1 ok. 4 razy, a mediana ułamka luki ok. 4–5 razy niższa.

Ten obraz **sprzyja** H_mod na skali wielkości efektu, ale prerejestrowany test na jedynych danych konfirmacyjnych tego nie wykazał.
Status: WNIOSKOWANIE opisowe / HIPOTEZA, a nie WYNIK.
Dla pełności, z klasy dev (≤ 4 działania, małe światy, potwierdzenie PRZYROST, m = 1): rząd 3 15/20 lepsza, 1/20 gorsza. Klasa jest inna i nie wliczam jej do tabeli.

---

## 3. Diagnostyka (nieprerejestrowana; WYŁĄCZNIE ziarna 2080–2089, 10 ziaren na prawo)

Użyłem ramion kontrolnych z recenzji PRZYROST:
- **prawda+graf**: sama wiedza o prawdzie;
- **TR+wszystkie**: sam prawdziwy porządek, bez filtra prawdy;
- **TRhat+prawda**: szacowany porządek wśród prawdziwych.

Logowałem też skład puli na ścieżce `heur_przyrostu`.
Prawa:
- 2 duże z ROZMIAR3: najsilniejsze `x(zx)=z(x(zx))` i najsłabsze `y((xx)(xy))=y(yy)`;
- 2 duże zerowe z PRZYROST T1: `((zx)x)x=(xz)x` i `(yx)(yx)=(yx)(yy)`;
- dodatkowo, jako kontrast, zerowe prawo małe z ROZMIAR3: `x(y(xy))=(yx)x`.

| Prawo | magmy | znane magmy (% świata) | pula / prawdziwe | precyzja Ê | \|TR̂\| / \|TR\| | Spearman zysków TR̂~TR | pokrycie TR na starcie snu (średnio po snach) / \|TR\| | M1 przyrost − graf | M1 W | prawda+graf / W | TR+wszystkie / W |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R3 duże `x(zx)=z(x(zx))` | 774 | 46 (5,9%) | 100 / **86%** | **0,92** | 78/80 | **0,74** | 54/80 | +4,20 [1,95; 6,54] | 6,75 | **0,29** | 0,87 |
| R3 duże `y((xx)(xy))=y(yy)` | 1516 | 39 (2,6%) | 62 / 45% | 0,63 | 33/90 | 0,31 | 15/90 | +1,08 [0,38; 1,78] | 5,88 | 0,61 | 0,53 |
| PRZ T1 `((zx)x)x=(xz)x` | 529 | 41 (7,8%) | 25 / 31% | 0,70 | 33/70 | 0,25 | 17/70 | +0,07 [−0,10; 0,26] | 2,50 | **0,92** | 0,73 |
| PRZ T1 `(yx)(yx)=(yx)(yy)` | 1845 | 40 (2,2%) | 40 / 34% | 0,62 | 34/74 | 0,30 | 14/74 | −0,27 [−0,95; 0,29] | 4,19 | **0,89** | 0,63 |
| R3 małe `x(y(xy))=(yx)x` (kontrast) | 146 | 37 (25%) | 18 / 60% | 0,93 | 63/57 | 0,53 | **51/57** | −0,01 [−0,15; 0,13] | **0,45** | 0,89 | 0,62 |

Kierunek M1 na ziarnach recenzji jest zgodny z walidacją w każdym prawie.
Wartości dla obu praw PRZYROST odtwarzają diagnostykę z ziaren 1990–1999 (tam: precyzja 0,73/0,60, prawdziwe 39%/35%, udział prawdy 0,95/0,91).

**Co odróżnia światy z efektem od światów bez efektu (WYNIK diagnostyczny, 4 + 1 praw):**
1. **Liczba znanych magm nie odróżnia.** We wszystkich dużych światach jest to 39–46, czyli 2–8% świata. Widoczne proxy z Z7 nie rozdzieliłoby więc `x(zx)` (efekt duży) od `((zx)x)x` (efekt zerowy).
2. **Odróżnia trafność puli i jakość porządku.**
   - Z efektem dużym: 86% prawdziwych, precyzja Ê 0,92, TR̂ ≈ TR, Spearman 0,74.
   - Z efektem małym: 45%, 0,63, 0,31.
   - Bez efektu: 31–34%, 0,62–0,70, 0,25–0,30.

   W `x(zx)` sama prawda daje tylko 29% przewagi wyroczni, a reszta to kolejność, którą TR̂ odtwarza. W zerowych prawach PRZYROST prawda daje ~90%, a tej składowej TR̂ z definicji nie dostarcza.
   Mechanizm opisany w recenzji PRZYROST (§3.1–3.2) potwierdza się na nowych ziarnach i na nowych prawach.
3. **Pośrodku leży `y((xx)(xy))`.** Pula jest prawdziwa w 45%, a udział prawdy wynosi 0,61. Efekt jest mały, ale dodatni. Wygląda to na **gradient**, a nie na dychotomię „mały/duży świat”.
4. **Duży świat może mieć łatwy porządek.** `x(zx)=z(x(zx))` przy 6% znanych magm ma Ê prawie bezbłędne, a na starcie snu ma pokryte średnio 68% TR.
   Struktura implikacji tego prawa jest grubsza i lepiej uchwytna z próby niż w pozostałych. Rozmiar świata jest tu złym proxy.
5. **Małe prawo zerowe** to sufit: na starcie snu pokryte jest średnio 51/57 krawędzi TR, przewaga wyroczni wynosi 0,45, a snów jest 1,9 na przebieg.
   Gdzie nie ma zapasu, żadna heurystyka nie wygra. Nie jest to ani dowód przeciw heurystyce, ani dowód za H_mod.

**Widoczne kandydatki na proxy (HIPOTEZA):** |Ê| (178 wobec 45–85) i rozmiar puli snu (100 wobec 25–62) są dostępne badaczowi i w tych 4 dużych prawach porządkują efekt.
Wymagałoby to prerejestrowanej walidacji, analogicznie do Z7. Przy n = 4 to tylko trop.

---

## 4. Rekomendacja dla Michała

**Werdykt §4 uruchamia propozycję:** heurystyka przyrostu (m = 1) jako domyślna intuicja **w całym rzędzie 3**.
Rekomenduję **przyjąć ją**, jako decyzję w zgodzie z §4, a nie jako wyjątek od niego. Opis w `petla.domyslna_intuicja` i w MATYLDA_RDZEN powinien zawierać te zastrzeżenia:

1. **Podstawa:** 9 ważnych praw z klasy większych termów (8/9 lepsza, 0/9 gorsza). W agregacji post hoc z PRZYROST i pilotem: 24 prawa rzędu 3, 0 istotnie gorszych, ok. 70% istotnie lepszych.
   Argument „nie szkodzi i zwykle pomaga” ma teraz pokrycie danymi, którego w PRZYROST brakowało.
2. **Wielkość efektu:** w dużych światach typowo 0,1–0,3 luki do wyroczni; w ok. 30% dużych praw zero. „Domyślna” znaczy „niegorsza i zwykle lepsza”, a nie „istotnie lepsza wszędzie”.
3. **Charakter efektu:** w małych światach to tempo (pokrycie końcowe równe). W dużych z ROZMIAR3 także pokrycie końcowe (4/5).
4. **Bez reguły zależnej od rozmiaru.** H_mod niepotwierdzona, a diagnostyka pokazuje, że rozmiar (ani liczba znanych magm) nie jest właściwą zmienną.
5. **Zakres:** klasa większych termów, słownik „literaly”, protokół S-1b, rząd 3. Na klasie dev (≤ 4 działania) dowody są tylko deweloperskie: 15/20 lepsza, 1/20 gorsza.
6. **Linia bazowa:** we wszystkich 9 prawach ROZMIAR3 i 5 prawach PRZYROST T1 `heur_przyrostu` jest też lepsza od starej `HeurystykaOgolnosci` (CI > 0).

**Czy wynik PRZYROST T1 to zmienia?**
- Nie zmienia kierunku decyzji: jego 3 „zera” to zera, nie szkody, a na ziarnach 2080–2089 replikują się jako zera.
- Zmienia sposób opisu. Nie wolno pisać, że heurystyka „działa w każdym dużym świecie rzędu 3”. PRZYROST pokazał prawa, w których działa nie lepiej niż graf, i to stabilnie.
- Gdyby Michał chciał bardziej konserwatywnie: zostawić graf w rzędzie 3 do czasu walidacji proxy. Taka decyzja kosztowałaby oczekiwany zysk w ok. 70% praw, a według danych niczego nie chroni.

**Kierunek dalszy (SPEKULACJA / HIPOTEZA):** brakuje składowej „prawda”, nie lepszego TR̂.
Rozwój P̂(prawdziwa) na kandydaturze, z |Ê|, rozmiarem puli i wsparciem jako widocznymi sygnałami, to naturalny następny dev. Bramka powinna być w nim rozbita na prawdę i kolejność.
Runner następnej walidacji powinien zapisywać skład puli (Z3), żeby recenzja po nie musiała puszczać osobnych przebiegów.

---

## 5. Klasyfikacja ustaleń

| Ustalenie | Klasa |
|---|---|
| Kod niezmieniony między 7029a27 a 1ed301b; hashe (20 plików, runner §9, lista praw, prerejestracja) zgodne; 35 testów przechodzi | WYNIK |
| Replikacja odtwarza 135/135 kontrastów, kategorie, interakcję i `G` bit w bit | WYNIK |
| Werdykt „lepsza w obu; różnica wielkości niewykazana” wynika z tabeli §4; kategoria MAŁE przy n = 4 (próg 3) zgodna z §4 i z `kategoria` | WYNIK |
| `rezerwowe_niewykorzystane` w MAŁYCH zawiera prawa nieważne (błąd etykiety, bez wpływu na analizę) | WYNIK (usterka opisu) |
| Test permutacyjny: 126 podziałów (4 + 5), nie 252; kod zgodny z intencją tekstu; p = 0,40 | WYNIK (rozbieżność opisu) |
| Zrealizowane MAŁE: 118–172 magm, w tym obie rezerwy; 3 z 4 najmniejszych światów nieważne | WYNIK |
| MAŁE: lepsza 3/4; DUŻE: lepsza 5/5; bramka 9/9; 0/9 gorsza | WYNIK (prerejestrowany) |
| H_mod (efekt większy w małych) niepotwierdzona: I = +0,30, p_perm = 0,40 | WYNIK NEGATYWNY dla kryterium interakcji (nie dowód braku moderacji: niska moc) |
| DUŻE: 4/5 praw z luką 0,11–0,30; pokrycie końcowe wyższe w 4/5 | WYNIK (opisowe) |
| Interakcja na ułamku luki (0,50 wobec 0,34) i na M1/\|TR\| (0,025 wobec 0,022) | WYNIK opisowy, nieprerejestrowany |
| Zerowe prawo małe `x(y(xy))` to efekt sufitu (pokrycie na starcie snu 51/57, zapas wyroczni 0,45–0,70) | WYNIK diagnostyczny (2080–2089) |
| Zera PRZYROST (`((zx)x)x`, `(yx)(yx)`) replikują się na nowych ziarnach; są cechą prawa | WYNIK diagnostyczny |
| Efekt różnicuje trafność puli i precyzja Ê, nie rozmiar ani liczba znanych magm (`x(zx)`, 774 magm: 86% prawdziwych, precyzja 0,92) | WYNIK diagnostyczny (4 + 1 praw) |
| PRZYROST a ROZMIAR3 to niejednorodność między prawami, nie sprzeczność; ani replikacja niepowodzenia, ani obalenie | WNIOSKOWANIE |
| Agregacja 24 praw rz. 3: 0 istotnie gorszych, ~70% lepszych w obu przedziałach; efekt w dużych ~4× mniejszy (mediany) | WNIOSKOWANIE opisowe (post hoc, podwójne użycie danych) |
| Moderatorem jest jakość szacowania porządku i trafność puli; rozmiar to słabe proxy | HIPOTEZA |
| \|Ê\| lub rozmiar puli snu jako widoczne proxy efektu | HIPOTEZA (n = 4) |
| Różne kategorie DUŻYCH w PRZYROST i ROZMIAR3 da się wyjaśnić samą losowością praw (p ≈ 0,7 na prawo) | SPEKULACJA (rachunek orientacyjny) |
| P̂(prawdziwa) × zysk TR̂ zamknie lukę w dużych światach | SPEKULACJA |
| Heurystyka przyrostu domyślna w całym rzędzie 3, z zastrzeżeniami z §4 | rekomendacja recenzenta (zgodna z §4; decyzja Michała) |

---

## Streszczenie

**Integralność: czysto.** Kod, runner, lista praw i prerejestracja mają zgodne hashe. Replikacja daje wynik identyczny bit w bit, a werdykt wynika z §4.
Trzy usterki opisu nie wpływają na werdykt:
- w MAŁYCH `rezerwowe_niewykorzystane` to w rzeczywistości prawa nieważne;
- test permutacyjny ma 126, nie 252 podziały;
- zrealizowane MAŁE mają 118–172 magm.

Ustalenia:
1. Heurystyka przyrostu jest lepsza od grafu w 3/4 małych i 5/5 dużych praw, nigdzie gorsza. Moderacji rozmiarem nie wykazano (p = 0,40).
2. W dużych światach efekt jest zwykle mały (0,1–0,3 luki), ale obejmuje też pokrycie końcowe.
3. PRZYROST i ROZMIAR3 się nie wykluczają: efekt jest niejednorodny między prawami. Zera z PRZYROST replikują się jako cecha tamtych praw.
4. Diagnostyka (ziarna 2080–2089): efekt zależy od trafności puli i precyzji Ê, a nie od rozmiaru ani liczby znanych magm. Świat 774 magm z łatwym porządkiem zachowuje się jak „mały”.
5. W agregacji post hoc 24 praw rzędu 3 żadne nie jest istotnie gorsze, a ok. 70% jest lepszych.

**Rekomendacja:** przyjąć heurystykę przyrostu jako domyślną w całym rzędzie 3, zgodnie z §4. Zastrzeżenia:
- „niegorsza i zwykle lepsza”;
- efekt mały w dużych światach;
- bez reguły zależnej od rozmiaru;
- zakres ograniczony do klasy większych termów.

Następny krok to dev rozpoznawania prawdziwości w puli.
