# Heurystyka przyrostu w rzędzie 3 według rozmiaru świata: raport (27.11)

Prerejestracja: `PREREJESTRACJA_ROZMIAR3.md`, zamrożona w 7029a27. Wynik: `wyniki/rozmiar3_walidacja.json`, commit 1ed301b, jedno uruchomienie.
Integralność potwierdził recenzent: kod bez zmian, hashe zgodne, niezależna replikacja odtworzyła wynik bit w bit.
Recenzje: `wyniki/ROZMIAR3_RECENZJA_PRZED.md` i `wyniki/ROZMIAR3_RECENZJA_PO.md`.

## Werdykt (wg tabeli §4)

**WYNIK: heurystyka przyrostu jest lepsza od heurystyki grafu w małych i w dużych światach rzędu 3. Większego efektu w małych nie wykazano.**
Hipoteza moderacji rozmiarem (H_mod) nie jest więc potwierdzona. Moc testu interakcji była jednak niska, więc to nie dowodzi braku moderacji.

| Przedział | Ważne prawa | Bramka | Lepsza | Gorsza | Kategoria |
|---|---|---|---|---|---|
| MAŁE (zrealizowane 118–172 magm) | 4 z 7 | 4/4 | 3/4 | 0/4 | lepsza (krucha: jedno nieważne prawo więcej dałoby „nieinformatywny”) |
| DUŻE (545–1516 magm) | 5 z 7 | 5/5 | **5/5** | 0/5 | lepsza |

Interakcja (małe − duże): I = +0,30, dokładny test permutacyjny p = 0,40 (126 podziałów przy 4 + 5 prawach), bootstrap 95% [−1,77; 2,44].

## M1: przyrost − graf (średnia, 95% CI)

| Przedział | Prawo | M1 | Wyrocznia − graf |
|---|---|---|---|
| małe | x(y(xy)) = (yx)x | +0,04 [−0,06; 0,13] | +0,70 (sufit: mało miejsca na poprawę) |
| małe | (((yy)x)y)y = xy | +4,64 [4,34; 4,98] | +5,68 |
| małe | (z(yx))(yz) = (zz)z | +2,73 [2,23; 3,23] | +4,07 |
| małe | y(xy) = (yz)((zy)y) | +0,51 [0,20; 0,87] | +1,93 |
| duże | y((xx)(xy)) = y(yy) | +0,34 [0,04; 0,64] | +4,49 |
| duże | (zz)((zy)z) = z | +1,33 [0,90; 1,78] | +5,09 |
| duże | x(zx) = z(x(zx)) | +4,06 [3,17; 4,94] | +5,98 |
| duże | (x(x(xy)))y = yy | +1,68 [1,40; 1,98] | +5,74 |
| duże | x(zy) = x(z((zy)x)) | +0,98 [0,81; 1,15] | +3,19 |

W dużych światach efekt jest przeważnie mały: 0,11–0,30 luki do wyroczni przyrostu. Wyjątkiem jest x(zx) = z(x(zx)) z 0,75.
Inaczej niż w PRZYROST, w 4/5 dużych praw wyższe jest też pokrycie końcowe.

## Ustalenia

| Ustalenie | Status |
|---|---|
| Heurystyka przyrostu lepsza od grafu w rzędzie 3: 3/4 praw małych i 5/5 dużych, nigdzie gorsza | **WYNIK** (prerejestrowany) |
| Większego efektu w małych światach nie wykazano (p = 0,40) | WYNIK (słaby dowód braku moderacji) |
| PRZYROST (dwa duże prawa z efektem 0) i ROZMIAR3 nie przeczą sobie. To niejednorodność między prawami: zera PRZYROST powtarzają się na nowych ziarnach 2080–2089 | WNIOSKOWANIE |
| Efekt zależy od trafności puli snu i precyzji Ê, a nie od rozmiaru świata. Przy dużym efekcie 86% puli jest prawdziwe, a precyzja Ê wynosi 0,92; bez efektu 31–34% i 0,62–0,70 | WYNIK diagnostyczny (4 prawa, nieprerejestrowany) / HIPOTEZA (ogólność) |
| Agregacja post hoc na 24 prawach rzędu 3 z klasy większych termów (PRZYROST + pilot + ROZMIAR3): istotnie gorsze 0, lepsze 10/14 małych i 7/10 dużych; w dużych efekt ok. 4× mniejszy | WNIOSKOWANIE (podwójne użycie danych) |
| Widoczne dla badacza proxy trafności puli: \|Ê\| lub rozmiar puli snu | SPEKULACJA |

## Rekomendacja (do decyzji Michała)

Wg §4 („lepsza w obu”): **heurystyka przyrostu jako domyślna intuicja w całym rzędzie 3**, bez reguły zależnej od rozmiaru. Recenzent popiera tę zmianę.
Zastrzeżenia:
- przewaga oznacza „niegorsza i zwykle lepsza”, bo w ok. 30% dużych praw efekt jest zerowy;
- w dużych światach efekt jest mały;
- zakres to klasa większych termów; na klasie dev są tylko dane deweloperskie (15/20 lepsza, 1/20 gorsza).

Następny krok merytoryczny: rozpoznawanie prawdziwości kandydatur w puli snu (dev). W kolejnym runnerze zapisywać skład puli.

## Usterki opisu (bez wpływu na werdykt)

- Pole JSON `rezerwowe_niewykorzystane` zawiera w MAŁYCH 3 prawa **nieważne**; obie rezerwy weszły do analizy.
- Tekst §4 mówił o 252 podziałach, kod liczy wszystkie podziały C(9, 4) = 126, zgodnie z intencją.
- Zrealizowany zakres MAŁYCH to 118–172 magm, bo odpadły 3 z 4 najmniejszych światów.

## Zużyte ziarna

2010–2069 (walidacja), 2070–2079 (recenzja przed), 2080–2089 (recenzja po). Generator praw 9494 zużyty. Wolne od 2090.
