# Heurystyka przyrostu pokrycia z nową bramką: raport (27.11)

Prerejestracja: `PREREJESTRACJA_PRZYROST.md`, zamrożona w 85f6d4d. Wynik: `wyniki/przyrost_walidacja.json`, commit 6fa9438, jedno uruchomienie.
Kod od zamrożenia bez zmian; kod_sha256 zgodne. Recenzent puścił walidację drugi raz i dostał wynik identyczny co do bitu.
Recenzje: `wyniki/PRZYROST_RECENZJA_PRZED.md` (przed zamrożeniem), `wyniki/PRZYROST_RECENZJA_PO.md` (po wyniku).

## Werdykt (wg §6)

**WYNIK CZĘŚCIOWY: heurystyka przyrostu (m = 1) jest lepsza od heurystyki grafu w rzędzie 4. W rzędzie 3 przewaga nierozstrzygnięta.**

| Świat | Ważne prawa | Bramka (wyrocznia przyrostu > grafu) | Lepsza | Gorsza | Kategoria |
|---|---|---|---|---|---|
| T1-4 (rząd 4) | 5/5 | 5/5 | **5/5** | 0/5 | lepsza |
| T1 (rząd 3) | 5/5 | 5/5 | 2/5 | 0/5 | nierozstrzygnięta |

Nowa bramka przeszła we wszystkich 10 komórkach. Test był więc informatywny, czego stara bramka w HEUR4 nie zapewniła.

## M1: heur_przyrostu − heur_grafu (średnia, 95% CI) i część luki do wyroczni przyrostu (stałe okno)

| Prawo | T1-4 M1 | T1-4 luka | T1 M1 | T1 luka |
|---|---|---|---|---|
| y(yy) = (x(yx))(yy) | +2,28 [1,94; 2,61] | 0,60 | +0,65 [0,43; 0,90] | 0,18 |
| x(z(xx)) = z(xx) | +1,24 [1,09; 1,38] | 0,18 | +0,15 [−0,01; 0,32] | 0,14 |
| ((zx)x)x = (xz)x | +1,19 [1,02; 1,36] | 0,51 | +0,03 [−0,09; 0,17] | ≈ 0 |
| ((xz)x)(zx) = x | +1,90 [1,53; 2,29] | 0,90 | +3,21 [2,81; 3,63] | 0,95 |
| (yx)(yx) = (yx)(yy) | +0,13 [0,04; 0,22] | 0,06 | −0,11 [−0,31; 0,09] | ≈ 0 |

Pokrycie końcowe jest w praktyce równe. Zysk dotyczy tempa pokrywania, nie tego, ile ostatecznie odkryto.
W T1-4 dla x(z(xx)) = z(xx) obie heurystyki, nowa i grafu, są istotnie gorsze od starej heurystyki ogólności.
„Luka” to część luki do zachłannej wyroczni przyrostu. Nie jest to „% do optimum”. CI są w JSON.

## Ustalenia

| Ustalenie | Status |
|---|---|
| Rząd 4: lepsza od heurystyki grafu w 5/5 nowych praw (klasa większych termów), nigdzie istotnie gorsza | **WYNIK** (prerejestrowany) |
| Rząd 3: lepsza 2/5, gorsza 0/5. Hipoteza H nie jest tam potwierdzona, ale nie jest też obalona | WYNIK (nierozstrzygnięty) |
| Nowa bramka (wyrocznia przyrostu) przechodzi w 10/10 komórek | WYNIK |
| Rozbieżność z pilotem w rzędzie 3 wynika z rozmiaru świata, nie z klasy termów. Światy walidacyjne miały 529–1845 magm w 4/5 praw, pilot miał medianę ok. 135. Jedyny mały świat walidacji dał lukę 0,95 | HIPOTEZA (post hoc, moderacja przez świat) |
| Mechanizm: w dużych światach rzędu 3 badacz zna 2–8% magm. Ê ma wtedy precyzję 0,60–0,77, a pula snu jest prawdziwa w 35–42%. Tam, gdzie przyrost ≈ graf, wyrocznia wygrywa w 91–95% dzięki znajomości prawdy, nie dzięki kolejności | WYNIK (diagnostyka recenzenta, ziarna 1990–1999, nieprerejestrowana) |
| Wąskim gardłem jest rozpoznanie, które przeczucia z puli są prawdziwe, a nie lepsze TR̂ (przy danej prawdzie TR̂ prawie wystarcza) | WNIOSKOWANIE |
| Kierunek: oczekiwany zysk = szacowane P(prawda) × zysk TR̂ | SPEKULACJA |

## Rekomendacja (do decyzji Michała)

- Wg §6 przy WYNIKU CZĘŚCIOWYM domyślna intuicja zostaje bez zmian.
- Recenzent rekomenduje jawną decyzję poza §6: heur_przyrostu jako domyślna intuicja **tylko w rzędzie 4**, z zastrzeżeniami (efekt w tempie, wielkość 0,06–0,90 luki). W rzędzie 3 bez zmian.
- Rozstrzygnięcie rzędu 3 wymaga nowej prerejestracji: prawa podzielone po rozmiarze świata, z góry zapisana hipoteza moderacji, więcej praw i ziaren.
- Merytorycznie warto rozwijać rozpoznawanie prawdziwości w puli. Bramkę warto raportować rozbitą na „prawdę” i „kolejność”.

## Zużyte ziarna

1900–1919 (dev), 1920–1979 (walidacja), 1980–1989 (recenzja przed), 1990–1999 (recenzja po), 2000–2009 (pilot). Generatory praw: 9191 (0 praw), 9292 (walidacja), 9393 (pilot). Wolne od 2010.

## Decyzja (27.11)

Michał wybrał: **heurystyka przyrostu jako domyślna intuicja tylko w rzędzie 4**, w rzędzie 3 bez zmian. Wprowadzone w `petla.domyslna_intuicja`. Runnery wcześniejszych eksperymentów mają intuicje przypięte jawnie.
