# Recenzja przed zamrożeniem: PREREJESTRACJA_PRZYROST (szkic, commit 794ddf3)

Niezależny recenzent (hostile review). Ocena: szkic prerejestracji, `wyrocznie.py`, `heurystyki_przyrostu.py`, `przyrost_walidacja.py`,
`przyrost_dev.py`, `przyrost_wybor_praw.py`, `wyniki/przyrost_dev*.json`.
Diagnostyki uruchamiałem tylko na prawach dev (`przyrost_dev_potw.json`, 2 światy rzędu 4 i 2 rzędu 3) i na ziarnach 1980–1981 (z puli 1980–1989).
Na 5 prawach walidacyjnych liczyłem **tylko statystyki świata** (rozmiar, |TR|, Jaccard) i ponownie przeliczyłem filtr wyboru. Pętli na nich nie uruchamiałem.
Skrypty: `scratchpad/recenzja_przyrost/` (dev_stat.py, moc.py, moc2.py, diag.py, filtr.py, filtr9191.py, jacc.py, pula.py, swiaty_stat.py, wielkosc.py).

**Werdykt recenzji:** projekt jest w zasadzie poprawny. Wyrocznia liczy tę samą miarę co `Swiat.pokrycie`. Heurystyka nie podgląda świata.
Filtr praw daje dokładnie 5 praw z tabeli. Przed zamrożeniem trzeba poprawić trzy rzeczy (B1–B3). Wszystkie trzy to poprawki tekstu lub runnera, bez nowych danych.

---

## Blokujące

### B1. Runner chroni hashem za mało plików, a §8 odsyła do nieistniejącego „§0”

`przyrost_walidacja.SHA` obejmuje tylko `heurystyki.py`, `heurystyki_przyrostu.py` i `wyrocznie.py`. Logika werdyktu leży w innych plikach i nie jest chroniona:
`heur4_walidacja.kategoria`, `_okno`, `_koniec`, `s1b.roznice`, `waznosc`, `PROG_WAZNOSCI`, `BUDZETY` i `s0.ci95` (ziarno i liczba prób bootstrapu).
Niechronione są też sama pętla (`petla.py`, `fazy.py`, `pamiec.py`, `swiat.py`, `intuicja.py`, `s1.py`) i sam runner (`PRAWA`, `SEEDS`, `M`, `analiza`).
Sprawdzenie czystego drzewa nie wystarcza: zmiana zacommitowana po zamrożeniu przejdzie, a werdykt może się zmienić.
Runner nie zapisuje też `kod_sha256` w wyniku, choć `s1.py`, `s1b.py`, `s0_heur.py` i `s1lmm.py` to robią. To regresja względem wcześniejszych serii.
§8 obiecuje odmowę „przy zmienionym pliku z §0”, ale prerejestracja nie ma §0.

**Poprawka:**
- dodać `KOD = ("przyrost_walidacja.py", "heurystyki.py", "heurystyki_przyrostu.py", "wyrocznie.py", "heur4_walidacja.py", "s1b.py", "s1.py", "s0.py", "intuicja.py", "fazy.py", "petla.py", "pamiec.py", "swiat.py", "prawa_losowe.py", "uniwersum4.py")`;
- zapisywać `kod_sha256` dla każdego pliku z KOD w `przyrost_walidacja.json`;
- hashe wszystkich plików z KOD poza samym runnerem wpisać do `SHA` i sprawdzać przed startem. Hash runnera wpisać do prerejestracji i porównać po fakcie;
  ewentualnie runner może sprawdzać `git diff --quiet <commit zamrożenia> HEAD -- matylda_rdzen/`;
- w §8 zastąpić „pliku z §0” listą plików z KOD.

Przy okazji: ta recenzja jest nieśledzonym plikiem w `rdzen/`. `git status --porcelain .` zablokuje runner, dopóki jej się nie zacommituje. Tak ma być, wystarczy o tym pamiętać.

### B2. Przesunięcie klasy praw: brak z góry ustalonej interpretacji wyniku

Prawa walidacyjne pochodzą z klasy, której dewelopment nie widział: 2–4 działania po lewej, łącznie do 6.
Przesunięcie jest też ilościowe (WYNIK, `swiaty_stat.py`):
- rząd 3: światy walidacyjne mają 105–1845 magm (4 z 5 prawa ≥ 529) i |TR| 69–74. Dev rzędu 3 ma medianę 74 (runda 1) i 216 (potwierdzenie) magm oraz medianę |TR| 42–50;
- rząd 4: |TR| 91–100 wobec mediany dev 78–81, rozmiary porównywalne.

§4 mówi, że „test sprawdza też przenoszenie”, ale §1 (H) i §6 tego nie uwzględniają.
Wynik negatywny albo częściowy nie rozróżni więc dwóch przypadków: „heurystyka nie działa” i „heurystyka nie przenosi się na większe termy”.
Pozytywny wynik zostanie z kolei odczytany szerzej, niż pozwalają dane.

**Poprawka (tekst, obowiązkowa):**
- w §1 dopisać, że H testujemy na prawach z klasy większych termów;
- w §6 lub §9 dopisać zdanie interpretacyjne: „wynik NEGATYWNY lub CZĘŚCIOWY nie odróżnia braku efektu od braku przeniesienia na nową klasę;
  WYNIK dotyczy tej klasy praw i rzędów 3 i 4”.

**Zalecane:** przed zamrożeniem zrobić pilot dev na klasie większych termów:
- inne ziarno generatora, np. 9393; wykluczyć 5 praw walidacyjnych i wszystko z listy zakazanej;
- ziarna dev, m = 1 bez zmian;
- tylko sprawdzić bramkę i kierunek efektu, zaraportować jako dev.

To nie jest nowa ścieżka rozwidlenia, jeśli wariant zostaje zamrożony przed pilotem.

### B3. Wybór praw: deklarowana ścieżka „ziarno 9191 → 0 praw” nie jest odtwarzalna z kodu

Docstring `przyrost_wybor_praw.py` mówi „Jedyne ziarno generatora: 9191”. To nieprawda: `main()` używa wyłącznie `ZIARNO_DUZE = 9292`, a `ZIARNO` nie jest nigdzie używane.
Liczby z §4 nie mają artefaktu w `wyniki/`:
- „2762/5000 odpadło na Jaccardzie w rzędzie 3”;
- „1864 na rozmiarze”.

Ścieżkę 9191 odtwarzałem niezależnie, podmieniając generator w `main()` na `losuj_prawa(5000, 9191)`. Wynik jest w „Aneksie”.

**Poprawka:**
- w `przyrost_wybor_praw.py` dodać tryb (np. `--maly`), który odtwarza próbę 9191 i liczy odrzucenia według przyczyny: rozmiar/TR, Jaccard w rz. 3, Jaccard w rz. 4, nadzbiór;
- zapisać oba przebiegi (9191 i 9292) z licznikami do `wyniki/przyrost_wybor_praw.json` i zacommitować przed zamrożeniem;
- poprawić docstring: „9191: 0 praw; 9292: jedyne ziarno klasy większych termów”.

Bez tego decyzja o zmianie klasy praw opiera się na liczbach, których nie da się sprawdzić.

---

## Zalecane

**Z1. Werdykt: dopisać mapowanie dla wszystkich par kategorii.** Kod robi to, co mówi tekst §6. Sprawdziłem wszystkie 16 par (k3, k4):
- (L, L) → WYNIK;
- dowolne G → NEGATYWNY, także (L, G);
- (N, N) i (N, R) → NIEINFORMATYWNY;
- (L, N) i (L, R) → CZĘŚCIOWY;
- (R, R) → NEGATYWNY.

Dwie słabości:
- (N, R) daje NIEINFORMATYWNY, choć w jednym rzędzie test był informatywny i wyszedł zerowy. Etykieta powinna to mówić, np. „NIEINFORMATYWNY w X; brak przewagi w Y”;
- (L, N), czyli lepsza plus nieinformatywny, daje CZĘŚCIOWY. To jest do przyjęcia, ale §6 powinien jawnie mówić, że w drugim rzędzie bramka zawiodła.

Ciąg `G` zawiera kategorie obu rzędów, więc informacja nie ginie. Warto jednak dopisać tabelę 16 par do §6.
Uwaga: per prawo „lepsza” nie wymaga, by bramka przeszła dla tego samego prawa. Tak samo było w HEUR4, w porządku, ale warto to napisać wprost.

**Z2. Ułamek luki bez CI.** Recenzja HEUR4 (§4) zalecała ułamek „z CI bootstrapu ilorazu”, a szkic pisze „bez CI”. Proponuję sparowany bootstrap ilorazu średnich na stałym oknie.
Kod liczy też `mo/go` ze średnich, nie średnią ilorazów. Trzeba to nazwać w §6.

**Z3. Klucz remisów w `zachlanny_przyrost`.** Klucz to `zysk*1e3 + remis/(1+max|remis|)`. Kolejność według zysku jest zachowana zawsze, bo |składnik remisowy| < 1, a różnica zysku ≥ 1 daje ≥ 1e3, także przy wadze 0,5.
W wyroczni wśród prawdziwych kandydatur mogą jednak być duplikaty z dedup heurystyki grafu (−1e6). Wtedy mianownik ≈ 1e6 i rozstrzyganie po wsparciu ginie w precyzji float64:
- dodatek do oceny to `1e-3·Δ(wsparcie/n)`, rzędu 1e-6–1e-5;
- po podzieleniu przez 1e6 daje 1e-12–1e-11;
- przy |klucz| ≥ ok. 1,5·10⁴ (zysk ≥ 15) to poniżej ULP.

Skutek jest deterministyczny i drobny: w 38 wywołaniach snu diagnostyki 0 przypadków. Heurystyki to nie dotyczy, bo wyklucza dedup.
Zalecam `np.lexsort((remis, zysk))` zamiast sumy. Zmiana jest bezpieczna przed zamrożeniem, bo wyrocznia to ramię kalibracyjne.

**Z4. Garden of forking paths: dopisać trzy fakty do §3.**
- m = 1 nie było w rundzie 1. Dodano je w rundzie 2 po zobaczeniu, że m = 2 > m = 3 (adaptacyjnie, na tych samych światach i ziarnach).
  Potwierdzenie na nowych światach i ziarnach to właściwa ochrona i jest uczciwie zrobione;
- `prz_m2w5` daje wyniki identyczne z `prz_m2` w każdym świecie i ziarnie. Śmiałe przeczucia mają wsparcie 1 < m, więc ich zysk jest ≈ 0 i waga nic nie zmienia.
  Efektywnie było 5 wariantów, nie 6;
- nieliczone wybory projektowe: definicja Ê, TR̂ zamiast domknięcia, wykluczenie dedup, remisy wg grafu.
  Pomysł pochodzi z diagnostyki recenzji HEUR4 na ówczesnych prawach walidacyjnych. Te prawa są teraz na liście zakazanej, więc nie ma przecieku, ale trzeba to napisać.

Dalsze poprawki do §3:
- „0,45–0,65 luki” łączy przebiegi z różnym `b`: w dev `b` = min po **wszystkich** ramionach, w walidacji po parze.
  Do tego bierze wyr_prz z rundy 1 i m = 1 z rundy 2. Z samego potwierdzenia wychodzi: iloraz średnich 0,58 w rz. 4 i 0,44 w rz. 3, a mediana per świat 0,56 i 0,52;
- 6 z 20 światów dev rzędu 3 (runda 1) i 4 z 20 (potwierdzenie) nie spełnia progu ważności 0,9. W dev były liczone, w walidacji byłyby wykluczone. Warto to podać.

**Z5. Dokumentacja światów dev.** Docstring `przyrost_dev.py` mówi „światy 20–59 …, 0–19 zużyte w HEUR4”. To nieprawda:
- `heur4_dev.json` zawiera 60 światów (indeksy 0–59, ziarna 1800–1809);
- `heur4_dev_potw.json` zawiera kolejne 60 (60–119, ziarna 1810–1819).

Światy dev tej serii (20–39 i 60–79) były już użyte w HEUR4 dev. Walidacja na tym nie cierpi, bo lista zakazana bierze `swiaty_dev(120)`, a ja sprawdziłem, że `swiaty_dev(40)` i `swiaty_dev(80)` są prefiksami `swiaty_dev(120)`.
Wszystkie 79 praw użytych w `przyrost_dev*.json` jest na liście zakazanej. W §3 lepiej pisać „nowe w tej serii (użyte w HEUR4 dev)”.

**Z6. Brzegowy Jaccard.** Filtr jest poprawny. Prawo `((zx)x)x = (xz)x` przechodzi jednak w rzędzie 4 z Jaccardem 0,485 wobec świata HEUR4-dev nr 17 `((yx)x) = (xz)x`.
Oba prawa różnią się jednym czynnikiem po lewej. `y(yy) = (x(yx))(yy)` ma 0,494 wobec świata z `swiaty_v3`.
To mieści się w regule, ale trzeba to wpisać jako ograniczenie, np. kolumnę „max Jaccard do listy zakazanej” w tabeli §4. Ewentualnie zaostrzyć próg do 0,4, ale tylko przed zamrożeniem i jawnie.

**Z7. Test „nie zna świata” jest słaby.** `test_wyrocznia_przyrostu_i_heurystyka_przyrostu_w_petli` sprawdza tylko determinizm.
Zalecam dodać test z `diag.py`: zaszumić `pamiec.concepts` poza znanymi magmami i sprawdzić, że oceny są identyczne.

**Z8. Domyślne `m = 2` w `HeurystykaPrzyrostu.__init__`**, a testujemy m = 1. Jeśli H przejdzie i klasa trafi do domyślnej intuicji, łatwo o pomyłkę. Zalecam zmienić domyślne na `m = 1` przed zamrożeniem hasha.

**Z9. Domknięcie Ê ∪ potwierdzone.** `klasy_i_redukcja` liczy TR z `E`, które musi być przechodnio domknięte (usuwa tylko krawędzie z dwukrokową drogą w CE).
- dla m = 1 Ê ∪ P jest domknięte: potwierdzone krawędzie mają wsparcie ≥ 1, a wsparcie nie maleje. W diagnostyce 38/38 przypadków było domkniętych;
- dla m ≥ 2 nie jest to gwarantowane.

Testowane jest m = 1, więc to tylko uwaga. Bezpieczniej przekazać do `klasy_i_redukcja` domknięcie.

---

## Uwagi (bez wpływu na zamrożenie)

- **U1 (pkt 1 zlecenia): wyrocznia liczy dokładnie miarę `Swiat.pokrycie`.**
  - Zysk dla A ⇒ B to liczba par (x, y) ∈ TR jeszcze niepokrytych z R[x, A] ∧ R[B, y]. To dokładnie przyrost `Swiat.pokrycie` po dodaniu krawędzi.
  - Aktualizacja `R |= outer(R[:,a], R[b,:])` zachowuje zwrotno-przechodnie domknięcie: jeśli R jest domknięte, nowa ścieżka używa krawędzi a → b co najwyżej raz,
    a R' jest znów domknięte. Kolejne kroki są więc poprawne.
  - Sprawdzenie brute force (diag.py): w 38 wywołaniach snu na 4 prawach dev i ziarnach 1980–1981 przeliczyłem dla każdego kroku zysk przez `Swiat.pokrycie(P ∪ prefiks ∪ {e})`.
    Wynik: 0 naruszeń zachłanności, 0 rozbieżności, 0 zgubionych remisów. Krzywe z opakowaniem i bez niego są identyczne.
  - Klasy: TR to pary reprezentantów (pierwszy w `names`), a pokrycie wymaga ścieżki właśnie między reprezentantami. Wyrocznia robi to samo.
- **U2 (pkt 2): heurystyka nie podgląda świata.**
  - Czyta tylko `p.names`, `p.concepts[·][znane]`, `p.prawdziwe`, `ctx.znane_magmy`, `ctx.konsolidacja` (przez heurystykę grafu) i `k.zrodlo`.
  - Test zaszumienia `concepts` poza znanymi magmami: 38/38 identycznych ocen.
  - Wykluczenie dedup (`g > -1e5`) nic nie traci. Kandydatury z tą samą parą klas badacza mają identyczne wiersze/kolumny R, więc identyczny zysk; po wyborze najlepszej reszta ma zysk 0.
    Próg −1e5 bezpiecznie oddziela −1e6 od kary −3 i ocen rzędu dziesiątek.
- **U3 (pkt 3): filtr praw poprawny i odtwarzalny.**
  - Ponowne `przyrost_wybor_praw.main()` daje dokładnie te 5 praw w tej samej kolejności i z tymi samymi statystykami (`filtr.py`).
  - Lista zakazana obejmuje S-0, PRAWA_MOCY, LMM `_L`/`_S`, `swiaty_v3`, `swiaty_dev(120)` (pokrywa HEUR4 dev 0–119 i przyrost dev rz. 4), HEUR4 oraz `swiaty_dev3(40)`.
  - Nie obejmuje koniunkcji `_L ∧ _S` z treningu LMM v0–v2, ale ich maksymalny Jaccard z prawami walidacyjnymi to 0,13 (rz. 3) i 0,31 (rz. 4). Bez znaczenia.
  - Maksymalny Jaccard per grupa (rz. 3 / rz. 4): S-0+MOCY 0,30 / 0,39; LMM 0,15 / 0,32; swiaty_v3 0,47 / 0,49; swiaty_dev120 0,42 / 0,49; HEUR4 0,18 / 0,30; dev3 0,33 / 0,44.
  - Warunek nadzbioru (`b <= x` tylko dla TESTOWANE) jest zgodny z regułą HEUR4.
- **U4:** ograniczenie z §4 („izomorfizm przez permutację elementów nie jest sprawdzany”) jest właściwie bezprzedmiotowe.
  Świat prawa równościowego jest zamknięty na przenumerowanie elementów, a oba zbiory porównujemy w tym samym uniwersum (pełne M3 albo ta sama próbka U4).
  Prawdziwe ograniczenie jest inne: Jaccard nie wychwytuje praw bliskich składniowo (Z6) ani zawierania w prawach dev (warunek nadzbioru tylko dla TESTOWANE).
- **U5:** `porzadek_empiryczny` wymaga wsparcia ≥ m także dla B. Przy braku kontrprzykładu wsparcie B ≥ wsparcie A, więc warunek jest redundantny. Docstring („wsparcie A ≥ m”) i §1 („A i B”) są równoważne.
- **U6:** pozostałe ustalenia zgodne z deklaracjami szkicu:
  - `pytest` zbiera 30 testów, zgodnie z §8;
  - liczby dev z §3 odtworzyłem z JSON-ów co do setnej części (`dev_stat.py`);
  - ziarna 1920–1979 i 1990–1999 nie są użyte w kodzie dev.

---

## Moc (pkt 4 zlecenia)

Ruch był taki: dla każdego świata dev z ≥ 90% ważności losowałem 60 ziaren ze zwracaniem z 10 obserwowanych różnic `prz_m1 − grafu` i liczyłem bootstrapową dolną CI.
Potem losowałem 5 światów i liczyłem P(≥ 3 z 5 z dolną CI > 0). Wyniki (`moc.py`, `moc2.py`):

| Źródło | rz. 4: P(lo>0) śr. / P(„lepsza”) | rz. 3: P(lo>0) śr. / P(„lepsza”) |
|---|---|---|
| potwierdzenie (ziarna 1910–1919), wszystkie ważne światy | 0,82 / 0,98 | 0,93 / 1,00 |
| runda 2 (1900–1909; wybór wariantu, optymistyczne) | 0,71 / 0,89 | 0,79 / 0,97 |
| potwierdzenie, tylko światy ≥ 100 magm (bliżej walidacji) | 0,73 / 0,92 | 0,92 / 1,00 |
| bramka `wyr_prz − grafu`, potwierdzenie | 1,00 / 1,00 | 1,00 / 1,00 |

WNIOSKOWANIE: jeśli efekt na nowej klasie praw jest jak w dev, P(WYNIK) w obu rzędach wynosi ok. 0,8–0,95.
To górne oszacowanie: bootstrap z 10 ziaren zaniża rozrzut, a przesunięcie klasy (B2) jest niewiadomą.
Ryzyko „nieinformatywny przez ważność” jest niskie: w dev wszystkie światy poniżej progu 0,9 miały ≤ 60 magm (`pula.py`), a światy walidacyjne rzędu 3 mają ≥ 105.
Rząd 4 jest słabszy: najmniejszy świat walidacyjny ma 58 magm, ale wszystkie światy dev rzędu 4 były ważne.
Przy zerowym efekcie fałszywa „lepsza” w rzędzie ma P ≈ 10·0,025³ ≈ 1,6·10⁻⁴. Kryterium jest konserwatywne.

---

## Klasyfikacja ustaleń

| Ustalenie | Klasa |
|---|---|
| Wyrocznia = przyrost `Swiat.pokrycie`; aktualizacja domknięcia poprawna; 0 rozbieżności w brute force (38 wywołań) | WYNIK |
| Heurystyka bez podglądu (test zaszumienia 38/38) | WYNIK |
| Filtr odtwarza dokładnie 5 praw z §4; dev rz. 4 ⊂ `swiaty_dev(120)`; 79/79 praw dev na liście zakazanej | WYNIK |
| Max Jaccard 0,485 / 0,494 w rz. 4 (prawa brzegowe) | WYNIK |
| Liczby dev z §3 odtworzone; `prz_m2w5` ≡ `prz_m2` | WYNIK |
| Światy 20–39 i 60–79 użyte wcześniej w HEUR4 dev (docstring błędny) | WYNIK |
| Runner nie chroni logiki werdyktu ani pętli hashem; brak `kod_sha256`; §0 nie istnieje | WYNIK |
| Ścieżka 9191 nieodtwarzalna z kodu | WYNIK |
| Przesunięcie rozkładu (rozmiar świata, |TR|) między dev a walidacją | WYNIK (liczby); jego wpływ: HIPOTEZA |
| Utrata remisu po wsparciu w float64 przy dedup i zysku ≥ 15 | WNIOSKOWANIE (analiza; 0 przypadków w diagnostyce) |
| Ê ∪ P domknięte dla m = 1, niegwarantowane dla m ≥ 2 | WNIOSKOWANIE (dowód) + WYNIK (38/38) |
| P(WYNIK) ≈ 0,8–0,95 | WNIOSKOWANIE (górne oszacowanie z dev) |
| Niskie ryzyko nieważności praw walidacyjnych | WNIOSKOWANIE |
| Negatywny wynik nieodróżnialny od braku przeniesienia na klasę większych termów | WNIOSKOWANIE |
| Efekt na klasie większych termów będzie podobny jak w dev | SPEKULACJA (dlatego zalecany pilot, B2) |

## Aneks: odtworzenie ścieżki 9191

Uruchomiłem `przyrost_wybor_praw.main()` z generatorem podmienionym na `losuj_prawa(5000, 9191)`, czyli klasę do 4 działań.
Wynik: **0 praw** (`filtr9191.py`, ok. 19 min). WYNIK: deklaracja z §4 się potwierdza.
Rozbicia na przyczyny odrzucenia (2762 na Jaccardzie w rz. 3, 1864 na rozmiarze) nie liczyłem.
B3 pozostaje w mocy, bo ścieżka ma być odtwarzalna z repozytorium, a nie z mojego skryptu.
