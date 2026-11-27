# Prerejestracja: heurystyka grafu ze wsparciem (wzmocnienie w rzędzie 4)

Status: **ZAMROŻONA** (27.11) po recenzji przed zamrożeniem (`wyniki/HEUR4_RECENZJA_PRZED.md`); poprawki B1–B5 wprowadzone (§2, §3, §5, §7). Seria samodzielna za zgodą Michała (27.11); cel programu bez zmian.
Zamrożenie = commit tego pliku z `heur4_walidacja.H4_SHA` = sha256 `heurystyki4.py` przed pierwszym `python -m matylda_rdzen.heur4_walidacja`.

## 1. Pytanie i hipoteza

Test S-0 (`wyniki/S0_HEUR_RAPORT.md`): heurystyka grafu w rzędzie 4 lepsza tylko w 3/5 praw (kruche). Recenzja wskazała HIPOTEZĘ: reguła pomija wsparcie.
**H:** wariant `HeurystykaGrafuWsparcie(λ = 1)` = out(a) + out(b) + λ·m·wsparcie/n − 3·[śmiałe] (m = liczba klas, deduplikacja par klas)
jest lepszy od `HeurystykaGrafu("oa+ob+kara")` w rzędzie 4.

## 2. Jak wybrany (jawnie)

Dewelopment wyłącznie na losowych prawach na U4 (żywe węzły-prawa; `heur4_dev.py`):
- 60 światów, ziarna 1800–1809, λ ∈ {0,25; 0,5; 1; 2} i wariant bez out(a): wszystkie > grafu (λ = 1: średnio +0,30, 65% światów > 0) — `wyniki/heur4_dev.json`;
- potwierdzenie: kolejne 60 światów, ziarna 1810–1819, λ ∈ {0,5; 1}: λ = 1 średnio +0,61, mediana +0,25, 80% światów > 0 — `wyniki/heur4_dev_potw.json`.
Wybrano λ = 1: w dewelopmencie średnia λ = 2 była nieco wyższa (+0,31 vs +0,30), ale λ = 1 miało wyższą medianę (+0,12 vs +0,08) i mniej światów < 0; w potwierdzeniu λ = 1 > λ = 0,5. Wybór między λ = 1 i 2 jest więc słabo uzasadniony.
Opisowo (znak: heur_grafu minus stara heurystyka): +1,73 (dev) i +0,92 (potwierdzenie), czyli heurystyka grafu lepsza.

## 3. Prawa walidacyjne (nowe)

Tylko z generatora `losuj_prawa(5000, ziarno 9090)` (jedyne użyte ziarno generatora), reguła w `wyniki/heur4_wybor_praw_kod.py.txt`:
świat ≥ 20 magm i |TR| ≥ 15 w rzędzie 3 i 4; prawo nie jest na liście zakazanej (prawa S-0, 5 praw walidacyjnych LMM, prawa treningowe LMM i własności,
323 prawa `swiaty_v3.json`, 120 praw deweloperskich rzędu 4); świat ani jego transpozycja (prawo dualne) nie ma **Jaccarda ≥ 0,5** ze światem żadnego z nich
ani z innym prawem zbioru, i **nie zawiera całego świata** prawa S-0 lub walidacyjnego LMM (poprawki B2, B3). Z 5 000 kandydatów przeszło 5:

| Prawo | rząd 3: magmy / TR | rząd 4: magmy / TR |
|---|---|---|
| x(xx) = y(yy) | 1620 / 53 | 274 / 82 |
| x(x(yx)) = x | 75 / 87 | 20 / 134 |
| (yz)y = (zy)z | 712 / 64 | 299 / 108 |
| y(x(xy)) = y | 26 / 75 | 33 / 128 |
| (z(zx))x = x | 31 / 34 | 35 / 58 |

Ograniczenie: izomorfizm przez permutację elementów nie jest sprawdzany (tylko równość i transpozycja zbiorów tablic).

## 4. Przebieg

Światy T1 (rząd 3) i T1-4 (U4), protokół S-1b (dzień 1 do 300, sen 50), **ziarna 1820–1879** (60, nowe).
Ramiona: losowa, heurystyka, heur_grafu, heur_grafu_wsp, wyrocznia_pokrycia. 3 000 przebiegów, jedno uruchomienie.

## 5. Kryteria (rozstrzygające)

M1, bootstrap sparowany 95%. W każdym świecie, tylko prawa ważne (niepusta pula 1. snu w ≥ 90% ziaren), n = ich liczba:
Kolejność (B1: szkoda rozpoznawana niezależnie od bramki):
1. n < 4 → **nieinformatywny**;
2. górna CI(heur_grafu_wsp − heur_grafu) < 0 w ≥ 60% n → **gorsza**;
3. bramka (wyrocznia_pokrycia − heur_grafu, dolna CI > 0) w < 60% n → **nieinformatywny**;
4. dolna CI > 0 w ≥ 60% n → **lepsza**; inaczej **nierozstrzygnięta** (= nie wykazano przewagi, nie „brak efektu”).

Progi 60% n: n = 4 → 3; n = 5 → 3. Moc (szacunek recenzji z dewelopmentu): ok. 0,6 (0,45–0,75), więc wynik negatywny jest słabym dowodem braku efektu.

**Werdykt główny (T1-4):** lepsza → WYNIK; gorsza → WYNIK NEGATYWNY; nierozstrzygnięta → WYNIK NEGATYWNY (brak przewagi); nieinformatywny → NIEINFORMATYWNY.
**T1 (wtórnie):** raportowana kategoria; „gorsza” = wariant szkodzi w rzędzie 3 (WYNIK NEGATYWNY dla rzędu 3).
Skutek: WYNIK w T1-4 i T1 nie „gorsza” → propozycja (do decyzji Michała), by wariant zastąpił domyślną intuicję. Inaczej domyślna zostaje bez zmian.

Zawsze raportujemy: stałe okno [d1, d1 + 50], pokrycie końcowe, heur_grafu − heurystyka (replikacja poprzedniego wyniku na nowych prawach), ułamek luki (bez CI; wyrocznia jest zachłanna, nie optimum).

## 6. Ziarna

Zużyte: 1780 (demonstracja prototypu), 1800–1819 (dewelopment), 1820–1879 (ta walidacja), 1880–1885 (recenzja przed). Recenzent po: 1886–1899.

## 7. Kontrola jakości

`pytest`; runner sprawdza sha256 `heurystyki4.py` (`dcb0a4b2…`) i `heurystyki.py` (`bbbf3a71…`, B4); niezależny recenzent przed zamrożeniem i po wyniku; raport z pustym `git diff` rdzen/ między zamrożeniem a commitem w JSON.
