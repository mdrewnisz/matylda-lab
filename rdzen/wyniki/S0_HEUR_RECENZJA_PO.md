# Recenzja po wyniku: test heurystyki grafu na prawach S-0 (niezależna, krytyczna)

Data: 26.11. Przedmiot: `PREREJESTRACJA_S0_HEUR.md` (zamrożona w 1183968), `matylda_rdzen/s0_heur.py`, `wyniki/s0_heur_wyniki.json`.
Kontekst: `wyniki/S0_HEUR_RECENZJA_PRZED.md`, `wyniki/HEUR_GRAFU_RAPORT.md`, `wyniki/HEUR_GRAFU_RECENZJA.md`, `wyniki/heur_grafu_walidacja.json`.

**Czego nie robiłem:** nie uruchamiałem `python -m matylda_rdzen.s0_heur`, nie dotykałem ziaren 600–679 i nie zmieniałem wyniku.
**Czego użyłem:** ziarna **1740–1779** (40) na prawach S-0, oba światy, te same 4 ramiona i protokół (`uruchom` z parametrami S-1b,
jak `heur_walidacja.zbierz`). To 1 600 przebiegów, około 9 minut na 4 rdzeniach. Do tego diagnostyka wyroczni z deduplikacją: T1, 3 prawa,
ziarna 1740–1759, około 3 minut. Ziarna 1740–1741 zużyłem też na test dymny skryptu. Skrypty i surowe dane leżą poza repo, w scratchpadzie
sesji (`repl.py`, `anal.py`, `wyr_dedup.py`, `run_*.pkl`). Jedyny plik zmieniony w repo: ten.

Klasyfikacja ustaleń: **WYNIK** (sprawdzone), **WNIOSKOWANIE**, **HIPOTEZA**, **SPEKULACJA**, **WYNIK NEGATYWNY**.
Skróty: G = heur_grafu, H = heurystyka (`HeurystykaOgolnosci`), W = wyrocznia_pokrycia, L = losowa. „Pole” = M1, „okno” = stałe okno
[d1, d1+50], „koniec” = pokrycie TR po d1+50 (`krzywa[-1][1]`).

---

## 0. Werdykt w skrócie

1. **Werdykt runnera jest poprawny względem §4.** Wszystkie 10 par świat × prawo są ważne, bramka przechodzi 5/5 w obu światach.
   Kategorie to T1 = L (5/5) i T1-4 = L (3/5), więc tabela daje WYNIK. Kod i prerejestracja nie zmieniły się od zamrożenia.
   **WYNIK** (prerejestrowany).
2. **T1 jest mocny i się replikuje:** 5/5 na ziarnach 1740–1779 z podobnymi efektami. Wynik nie zależy od prawa dualnego (4/4 bez x(xy)=y).
3. **T1-4 jest kruchy:**
   - Kategoria „lepsza” wisi na dokładnie 3 prawach. Usunięcie dowolnego z nich, w tym x(xy)=y, daje kategorię „nierozstrzygnięta”.
   - Inne miary dają inny obraz. Na stałym oknie T1-4 wychodzi „nierozstrzygnięta” (2 L, 1 G). Na pokryciu końcowym 3 prawa są lepsze,
     ale to **inne** prawa, a komutatywna jest istotnie **gorsza**.
   - Replikacja zachowała ten sam zbiór 3 praw „lepszych”. W tym sensie wynik T1-4 jest powtarzalny: kruchość dotyczy doboru praw,
     nie losowania ziaren.
4. **Część zysku to samo tempo.** W 4 komórkach (T1 x(xy)=y, T1 medialna, T1-4 medialna, T1-4 idempotentna) wszystkie ramiona kończą
   z tym samym lub prawie tym samym pokryciem. G jedynie szybciej porządkuje te same krawędzie. Prawdziwy zysk w pokryciu końcowym
   widać w T1 dla łącznej (+5,7) i idempotentnej (+3,0) oraz w T1-4 dla x(xy)=y (+0,6) i łącznej (+1,0).
5. **Ułamek luki > 1 jest prawdziwy, a nie artefaktem.** Wyrocznia pokrycia nie jest sufitem. W T1 łącznej G ma istotnie **wyższe**
   pokrycie końcowe niż W, i to na obu zestawach ziaren. Nie podważa to bramki, która mierzy tylko, czy wybór kandydatów w ogóle ma znaczenie.
   Podważa natomiast czytanie „ułamka luki” jako odsetka osiągalnego optimum.
6. **Rekomendacja:** przyjąć G jako **domyślną intuicję rdzenia**, z zastrzeżeniem dla rzędu 4. W żadnej z 10 komórek G nie jest gorsza
   od losowej, a w rzędzie 3 przewaga jest duża i stabilna. Nie ogłaszać jednak, że G „rozwiązuje” rząd 4. Tam zysk wynosi 0–40% luki,
   a reguła ma dwa powtarzalne słabe punkty (łączna tutaj, x(xy)=xy w walidacji). Szczegóły w §6.

---

## 1. Werdykt względem §4 (ważność, bramka, tabela)

| Punkt | Sprawdzenie | Ocena |
|---|---|---|
| Integralność | `commit` w JSON = 1183968 (commit zamrożenia). `git diff 1183968 HEAD -- matylda_rdzen PREREJESTRACJA_S0_HEUR.md` pusty. 7c53e43 dodaje tylko JSON. Wszystkie 12 `kod_sha256` zgodne z plikami. `prerejestracja_sha256` = sha256 pliku (07aef1ac…). Hash reguły bbbf3a71… zgodny. | WYNIK |
| „Jedno uruchomienie” | Zamrożenie 18:13:58, plik wyniku 18:35, log przebiegu w scratchpadzie 18:35:47. Odstęp ~21 min zgadza się z szacunkiem ~25 min na jeden przebieg. Test dymny (1720–1723, prawa spoza S-0) przeszedł 18:06–18:11, przed zamrożeniem. Wielokrotnego uruchomienia nie da się wykluczyć dowodowo, ale przebieg jest deterministyczny przy zamrożonym kodzie, więc powtórka dałaby ten sam JSON. | WYNIK + WNIOSKOWANIE |
| Ważność | pula 1. snu ≥ 0,9625 we wszystkich 10 komórkach; dzień 1 nigdy nie trafił w limit 300 | WYNIK |
| Bramka | W − H, dolna CI > 0 w 5/5 (T1) i 5/5 (T1-4); najmniejsza dolna to 1,06 (T1 x(xy)=y) | WYNIK |
| T1 | L: 5/5, G: 0 → „lepsza” | WYNIK |
| T1-4 | L: komutatywna [0,70; 1,03], x(xy)=y [0,81; 1,27], medialna [0,52; 0,80]; gorsza: łączna −0,97 [−1,28; −0,67]; idempotentna −0,09 [−0,26; 0,07] → 3 ≥ 3 → „lepsza” | WYNIK |
| Tabela | L × L → **WYNIK** | WYNIK |

Werdykt runnera wynika poprawnie z zamrożonej reguły. Zastrzeżenie Z4 z recenzji przed („nie ogłaszać domyślną bez zastrzeżenia przy ≥ 2 prawach
gorszych”) nie jest naruszone: w T1-4 jest jedno prawo gorsze.

Uwaga formalna: prerejestracja (§7) i recenzja przed (B4) wymagają, by *raport* po wyniku pokazał pusty `git diff`. W repo jest na razie tylko JSON,
bez raportu. Powyższe sprawdzenie może posłużyć raportowi.

---

## 2. Krytyczna ocena

### 2.1 Kruchość T1-4 (dokładnie 3/5)

Dolne granice CI trzech praw „lepszych” leżą daleko od zera (0,52–0,81). Losowanie ziaren raczej nie zmieni kategorii, co potwierdza replikacja
(§3). Kruchość dotyczy **doboru praw**:

- **Wynik leave-one-out (WYNIK, przeliczenie na JSON):** usunięcie dowolnego z praw komutatywna, x(xy)=y lub medialna daje 2/4.
  Przy bezwzględnym progu „≥ 3” byłaby to kategoria „nierozstrzygnięta”, a cały test dałby WYNIK CZĘŚCIOWY.
- **Rozkład efektów w T1-4:** jedno prawo istotnie gorsze, jedno ≈ 0, trzy umiarkowanie lepsze. Ułamek luki wynosi 0,23–0,42 dla trzech
  lepszych, −0,03 dla idempotentnej i −0,16 dla łącznej.
- **Z walidacją (WNIOSKOWANIE):** w rzędzie 4, na 10 prawach (5 walidacyjnych i 5 z S-0), G jest istotnie lepsza w 7, przy czym elastyczna
  ma dolną CI równą tylko 0,01. Istotnie gorsza jest w 2: x(xy)=xy −1,04 i łączna −0,97. W 1 wynik jest ≈ 0 (idempotentna).
  To spójny obraz umiarkowanej przewagi z regularnymi wyjątkami, a nie „lepsza wszędzie”.

### 2.2 Czy zysk to tylko tempo

Tabela z JSON (ziarna 600–679). Zakres to 95% CI; „=” oznacza, że wszystkie ramiona kończą z identycznym pokryciem.

| Świat | prawo | pole (M1) | stałe okno | koniec G − H |
|---|---|---|---|---|
| T1 | idempotentna | +2,32 | +2,17 [1,80; 2,54] | **+3,03** [2,24; 3,80] |
| T1 | komutatywna | +2,44 | +1,88 [1,63; 2,13] | +0,46 [0,01; 0,89] |
| T1 | x(xy)=y | +1,50 | +1,00 [0,75; 1,28] | +0,01 [0; 0,04] (≈ =) |
| T1 | łączna | +4,12 | +4,68 [4,44; 4,93] | **+5,74** [4,84; 6,68] |
| T1 | medialna | +1,34 | +0,74 [0,58; 0,92] | +0,04 [0; 0,11] (≈ =) |
| T1-4 | idempotentna | −0,09 (ns) | +0,05 [−0,07; 0,18] | +0,43 [0,24; 0,63] |
| T1-4 | komutatywna | +0,87 | +0,15 [−0,09; 0,37] **ns** | **−0,65** [−1,05; −0,28] |
| T1-4 | x(xy)=y | +1,03 | +0,96 [0,73; 1,20] | +0,58 [0,13; 1,08] |
| T1-4 | łączna | **−0,97** | **−0,54** [−0,86; −0,23] | **+1,03** [0,70; 1,39] |
| T1-4 | medialna | +0,66 | +0,35 [0,27; 0,44] | 0,00 (=) |

Wnioski:
- **T1 (WYNIK):** stałe okno daje 5/5 L. Wynik nie zależy więc od okna b = min. W 3/5 praw G ma też wyższe pokrycie końcowe.
  W x(xy)=y i medialnej zysk jest czystym tempem: wszystkie ramia wyczerpują pulę z tym samym zbiorem krawędzi, w medialnej 32,5/88.
- **T1-4 (WYNIK):** na stałym oknie są 2 L (x(xy)=y, medialna) i 1 G (łączna), czyli kategoria „nierozstrzygnięta”. Na pokryciu końcowym
  są 3 L (idempotentna, x(xy)=y, łączna) i 1 G (komutatywna), czyli „lepsza”, ale dla **innego** zbioru praw.
  - **Komutatywna:** zysk w M1 bierze się z okna b = min. Na stałym oknie jest nieistotny, a pokrycie końcowe jest istotnie gorsze.
    G zaczyna szybciej, potem H ją wyprzedza.
  - **Łączna:** obraz odwrotny. G startuje wolniej, ale kończy z pełnym TR. Na nowych ziarnach G dochodzi do 91/91 po średnio 38 wywołaniach
    snu, H do 90,1/91 po 46, i trafia w limit w 38% przebiegów.
  - **Medialna:** czyste tempo przy identycznym końcu, 30/97 we wszystkich ramionach.
  - Tylko **x(xy)=y** jest lepsze w T1-4 na wszystkich trzech miarach.
- **WNIOSKOWANIE:** M1 była prerejestrowana i werdykt jej się trzyma. Przy wniosku praktycznym („G daje więcej wiedzy”) T1-4 trzeba jednak
  opisać jako **niejednorodny**. G zmienia *kolejność* odkryć: w części praw na lepsze, w części na gorsze. Do tego w kilku światach pula snu
  wyczerpuje się przed budżetem (medialna, x(xy)=y w T1), więc przewaga w tempie nie przekłada się na wiedzę na końcu tego protokołu.
  Czy tempo zamieni się w wiedzę w protokole wielodniowym, to **HIPOTEZA** do sprawdzenia.

### 2.3 Wpływ dualności x(xy)=y

- **T1 bez x(xy)=y (WYNIK, opisowo zgodnie z §4):** 4/4 L, z dolnymi CI 1,10–3,93. Wynik T1 nie zależy od prawa dualnego.
  W JSON wynik x(xy)=y (+1,50, ułamek 1,16) jest bliski walidacyjnemu (yx)x=y (+1,73, replikacja +1,56). Zgadza się to z dualnością.
- **T1-4:** prerejestracja słusznie uznała, że dualność tu nie obowiązuje (|W| 1024 wobec 38). Mimo to wynik T1-4 **zależy** od x(xy)=y,
  tak samo jak od dwóch pozostałych praw „lepszych” (§2.1). Bez niego wychodzi 2/4, czyli „nierozstrzygnięta” i WYNIK CZĘŚCIOWY.
  Do tego x(xy)=y jest jedynym prawem T1-4 lepszym na wszystkich trzech miarach. WNIOSKOWANIE: najczystsze świadectwo w rzędzie 4 pochodzi
  z prawa, którego lustrzana wersja w rzędzie 3 była już w walidacji. Strukturalnie to inny świat, więc nie jest to błąd testu, ale osłabia
  wrażenie szerokiego uogólnienia.

### 2.4 Ułamki luki > 1 w T1 i definicja wyroczni

Wyrocznia (`intuicja.IntuicjaWyroczniaPokrycia`) daje kandydatom ocenę 2, gdy krawędź jest prawdziwa i należy do TR według klas *świata*,
ocenę 1, gdy jest prawdziwa poza TR, i 0, gdy jest fałszywa. Remisy rozstrzyga losowo. Nie ma deduplikacji, nie patrzy w przód i nie bierze
pod uwagę, że fałszywa kandydatura daje kontrprzykład, czyli nową magmę i nową pulę w następnym śnie. To zachłanna reguła „TR najpierw”,
**a nie górna granica**. Docstring tego nie twierdzi. Recenzja heurystyki (`HEUR_GRAFU_RECENZJA.md`, §ułamek luki) już to zauważyła.

Sprawdzenie:
- **WYNIK (JSON):** w T1 łącznej koniec G − H = +5,74, a W − H = +3,23. G kończy więc ~2,5 krawędzi TR **wyżej** niż wyrocznia.
  W komutatywnej (koniec 0,46 wobec 0,44) i x(xy)=y G i W są praktycznie równe.
- **WYNIK (replikacja 1740–1779):** w T1 łącznej G − W wynosi +0,43 [0,13; 0,75] dla pola i **+2,52 [1,85; 3,23]** dla końca.
  G zużywa średnio 40,6 wywołania snu i nigdy nie trafia w limit. W zużywa 49,9 i trafia w limit w 97% przebiegów.
  W komutatywnej G − W dla końca wynosi +0,50 [0,10; 1,00].
  Ułamek luki: 0,93 dla komutatywnej (stałe okno 0,91), 1,07 dla x(xy)=y (1,23) i 1,11 dla łącznej (1,27).
- **Diagnostyka (WYNIK, 20 ziaren):** deduplikacja wyroczni nie wyjaśnia przewagi G w łącznej. Zbadałem dwa warianty: dedup po klasach świata
  i dedup po klasach konsolidacji badacza. Oba są o ≈ 0 od W na stałym oknie i na końcu. G − W w łącznej wynosi tam +0,96 [0,48; 1,41]
  dla okna i +2,45 [1,65; 3,30] dla końca. W komutatywnej dedup po klasach świata poprawia W o +0,84 na oknie, czyli część luki
  „G ≈ W” w komutatywnej to marnowanie miejsc w k = 10 przez wyrocznię.
- **HIPOTEZA (mechanizm):** w łącznej przewaga G może brać się z kolejności, która prowadzi do kontrprzykładów i przycinania (`kons.wynika`).
  Te z kolei otwierają w kolejnych snach kandydatów z TR, których zachłanna wyrocznia nie dostaje do puli. Nie sprawdzałem tego.

Co to znaczy dla testu:
- **Bramka nie jest podważona (WNIOSKOWANIE).** Pyta tylko, czy dobry wybór w ogóle się opłaca (W > H). Przeszła 10/10 z dużym zapasem,
  więc to założenie jest spełnione.
- **Miara M1 nie jest podważona.** Nie odwołuje się do wyroczni.
- **Podważona jest interpretacja „ułamka luki” jako „odsetka osiągalnej poprawy” (WNIOSKOWANIE).** To iloraz dwóch kontrastów liczonych na
  różnych oknach b. Jego mianownik jest heurystyką z dostępem do prawdy, a nie optimum. Wartości > 1 w T1 znaczą: „G jest co najmniej tak dobra
  jak zachłanna wyrocznia TR-najpierw”. Nie znaczą: „G jest lepsza od najlepszej możliwej”. Wartości 0,2–0,4 w T1-4 mówią tylko, że zachłanna
  wyrocznia jest tam wyraźnie lepsza. Prawdziwy sufit jest wyżej. Raport nie powinien używać sformułowań typu „G zamyka X% luki do optimum”.

---

## 3. Replikacja na ziarnach 1740–1779 (n = 40, oba światy)

Pole (M1), G − H, 95% CI bootstrap (10 000, ziarno 12345, jak w teście). Ważność ≥ 0,975 wszędzie.

| Świat | prawo | test 600–679 (n = 80) | replikacja 1740–1779 (n = 40) | W − H (repl.) |
|---|---|---|---|---|
| T1 | idempotentna | +2,32 [2,01; 2,66] | +2,20 [1,77; 2,63] | +3,67 |
| T1 | komutatywna | +2,44 [2,20; 2,67] | +2,56 [2,18; 2,91] | +2,74 |
| T1 | x(xy)=y | +1,50 [1,23; 1,78] | +1,40 [1,14; 1,67] | +1,30 |
| T1 | łączna | +4,12 [3,93; 4,32] | +4,09 [3,70; 4,48] | +3,68 |
| T1 | medialna | +1,34 [1,10; 1,58] | +1,34 [1,00; 1,69] | +3,19 |
| T1-4 | idempotentna | −0,09 [−0,26; 0,07] | −0,07 [−0,31; 0,16] | +2,45 |
| T1-4 | komutatywna | +0,87 [0,70; 1,03] | +0,98 [0,73; 1,24] | +2,06 |
| T1-4 | x(xy)=y | +1,03 [0,81; 1,27] | +0,99 [0,68; 1,34] | +3,06 |
| T1-4 | łączna | **−0,97** [−1,28; −0,67] | −0,31 [−0,64; **+0,02**] | +6,04 |
| T1-4 | medialna | +0,66 [0,52; 0,80] | +0,67 [0,49; 0,87] | +2,81 |

- **WYNIK:** w replikacji kategorie to T1 L 5/5 i T1-4 L 3/5, z tym samym zbiorem praw. Bramka przechodzi 10/10, więc według reguły §4
  werdykt brzmiałby tak samo: WYNIK. Efekty są w 9/10 komórek bardzo bliskie testowi.
- **Łączna T1-4 w replikacji:** −0,31, nieistotne, wobec −0,97 w teście. Kierunek jest ten sam, wielkość mniejsza. Na nowych ziarnach
  stałe okno wynosi +0,14 (ns), a koniec +0,93 [0,47; 1,43]. WNIOSKOWANIE: „gorsza na łącznej w rzędzie 4” jest kierunkowo powtarzalne
  w M1, ale efekt jest mały i zależny od okna. Mocniejsze i powtarzalne jest to, że **G kończy łączną z pełnym TR szybciej niż H**.
- **Komutatywna T1-4 w replikacji:** stałe okno +0,50 [0,25; 0,77], tym razem istotne. Koniec znów istotnie gorszy: −0,40 [−0,78; −0,07].
  Spadek pokrycia końcowego w komutatywnej powtarza się (**WYNIK**, 2/2 zestawy ziaren).
- Replikacja jest diagnostyką na prawach S-0, nie prerejestrowanym testem, i niczego nie rozstrzyga ponad JSON.

---

## 4. Tabela ustaleń

| # | Ustalenie | Klasyfikacja |
|---|---|---|
| 1 | Werdykt „WYNIK: lepsza na S-0 w obu światach” wynika poprawnie z §4: ważność 10/10, bramka 5/5 + 5/5, T1 L 5/5, T1-4 L 3/5 | **WYNIK** (prerejestrowany) |
| 2 | Kod, prerejestracja i reguła nie zmieniły się między zamrożeniem a wynikiem (diff pusty, hashe zgodne) | WYNIK |
| 3 | T1: przewaga G replikuje się 5/5 (1740–1779), utrzymuje się na stałym oknie 5/5 i bez prawa dualnego 4/4 | WYNIK |
| 4 | T1-4: „lepsza” zależy od każdego z 3 praw (leave-one-out → nierozstrzygnięta). Ten sam zbiór 3 praw w replikacji | WYNIK |
| 5 | T1-4 na stałym oknie: nierozstrzygnięta (2 L / 1 G). Na końcu: 3 L / 1 G, ale dla innych praw | WYNIK |
| 6 | Komutatywna T1-4: G kończy z istotnie niższym pokryciem (−0,65; replikacja −0,40) | WYNIK NEGATYWNY (dla tej komórki) |
| 7 | Łączna T1-4: G gorsza w M1 (−0,97; replikacja −0,31 ns), ale kończy z wyższym pokryciem (+1,03; +0,93) | WYNIK |
| 8 | W T1 x(xy)=y, T1 medialnej i T1-4 medialnej zysk jest czystym tempem (identyczne pokrycie końcowe) | WYNIK |
| 9 | Wyrocznia pokrycia nie jest sufitem: w T1 łącznej G ma istotnie wyższe pokrycie końcowe niż W (+2,5, oba zestawy ziaren); deduplikacja wyroczni tego nie wyjaśnia | WYNIK |
| 10 | Ułamek luki > 1 nie podważa bramki ani M1; podważa czytanie ułamka jako „odsetka do optimum” | WNIOSKOWANIE |
| 11 | Mechanizm przewagi G nad W w łącznej: kontrprzykłady i przycinanie otwierają kandydatów TR | HIPOTEZA |
| 12 | Tempo przełoży się na wiedzę w protokole wielodniowym | HIPOTEZA |
| 13 | W rzędzie 4 G ma typowo umiarkowaną przewagę z powtarzalnymi wyjątkami (x(xy)=xy, łączna) zamiast przewagi uniwersalnej | WNIOSKOWANIE (z 10 praw) |
| 14 | Słabość w łącznej / x(xy)=xy wiąże się z regułą out(a)+out(b) premiującą krawędzie „hub”, które w gęstych porządkach (łączna: 4 pojęcia ≡ ⊤) dają mało nowego TR | SPEKULACJA |
| 15 | W żadnej z 10 komórek G nie jest gorsza od losowej (dolne CI G − L ≥ 0,50) | WYNIK |

---

## 5. Czego ta recenzja nie sprawdziła

- Nie uruchamiałem `pytest`.
- Nie odtworzyłem JSON z ziaren 600–679, bo to zabronione. Zgodność liczb z kodem przyjmuję na podstawie hashy, determinizmu
  i zgodności replikacji.
- Nie badałem mechanizmu ze wskazania 11. Nie testowałem wariantów reguły, bo każdy wariant byłby już nową, nieprerejestrowaną regułą.

---

## 6. Rekomendacja

1. **Przyjąć `HeurystykaGrafu("oa+ob+kara")` jako domyślną intuicję rdzenia**, zamiast `HeurystykaOgolnosci`. Uzasadnienie:
   - prerejestrowany WYNIK w obu światach;
   - zero komórek gorszych od losowej;
   - duża i stabilna przewaga w rzędzie 3.

   Przy przyjęciu zapisać w raporcie brzmienie: *„lepsza w T1 (5/5, odporne); w T1-4 lepsza w M1 w 3/5, niejednorodna: na stałym oknie
   nierozstrzygnięta, w komutatywnej niższe pokrycie końcowe, w łącznej wolniejszy start, ale pełne TR szybciej”*.
2. **Nie** formułować wniosku jako „G zamyka X% luki do optimum”. Wyrocznia pokrycia nie jest optimum (ustalenie 9). Jeśli potrzebny jest
   sufit, trzeba go zbudować osobno: wyrocznię z wyprzedzeniem, z symulacją puli kolejnego snu, albo przegląd wyczerpujący na małych światach.
   Do tego ułamek liczyć na wspólnym stałym oknie z CI z bootstrapu ilorazu (Z6 z recenzji przed, wciąż niewdrożone).
3. **Raport po wyniku** powinien:
   - pokazać tabelę z §2.2 (trzy miary) i dopisać leave-one-out dla T1-4;
   - wykazać pusty `git diff` (B4);
   - zarejestrować ziarna 1740–1779 jako zużyte przez tę recenzję.
4. **Dalsza praca nad rzędem 4** (eksploracyjnie, na prawach spoza S-0 i świeżych ziarnach; każdy wniosek dopiero po nowej prerejestracji):
   - **diagnoza słabości dla łącznej i x(xy)=xy:** które kandydatury G budzi tam wcześniej niż H, ile z nich to krawędzie spoza TR,
     prawdziwe lub fałszywe, i czy chodzi o premię za „hub” (out(a) duże przy już gęstym porządku);
   - **komutatywna T1-4:** dlaczego G traci pokrycie końcowe. Kandydat: wcześniejsze wyczerpanie puli (G zużywa mniej wywołań snu: 28,6 wobec 31,1);
   - **protokół wielodniowy albo większy budżet snu,** żeby sprawdzić, czy przewaga tempa (HIPOTEZA 12) przekłada się na wiedzę;
   - ewentualna hybryda (G z wyłącznikiem w gęstych porządkach) to **nowa reguła**, wymaga nowego dewelopmentu i walidacji,
     a nie poprawki przyjętej.
5. **Nie** traktować tego WYNIKU jako potwierdzenia mechanizmu z `HEUR_GRAFU_RAPORT.md` („żywe węzły-prawa”). W T1-4 komórki, w których cała TR
   dotyka węzłów nieliterałowych (idempotentna, komutatywna, x(xy)=y, łączna), dały cztery różne zachowania. Mechanizm pozostaje HIPOTEZĄ.
