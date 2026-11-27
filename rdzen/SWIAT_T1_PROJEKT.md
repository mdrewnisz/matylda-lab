# Projekt świata T1: świat, w którym intuicja ma co rozstrzygać

Status: **projekt i kalibracja**, nie eksperyment. Kryteria trudności zapisane przed pomiarem.
Kontekst: S-0/S-0b (`wyniki/RECENZJA_I_WNIOSKI_S0_S0B.md`): w obecnych światach losowa para pojęć po przycięciu pamięcią
kontrprzykładów jest prawdziwa w ~90%, więc wybór przeczuć (rola intuicji, LMM) nie ma czego rozstrzygać. Decyzja Michała 23.11:
zaprojektować trudniejszy świat przed S-1.

## Diagnoza (HIPOTEZA, do sprawdzenia kalibracją)

Wysoka trafność przeczuć ma dwa źródła:
1. **Hojny weryfikator.** Każde obalenie zwraca do 50 kontrprzykładów. Po kilku obaleniach pamięć zawiera dużą, różnorodną próbkę świata
   i przycina prawie wszystkie fałszywe pary za darmo. Zostają głównie prawdziwe.
2. **Mały, „dodatni” słownik.** 24 pojęcia, prawie wyłącznie prawa i własności, które często się zawierają. Krawędzie wykluczające
   (A ⇒ nie-B) w ogóle nie istnieją jako kandydatury.

## Dźwignie

| Dźwignia | Wartości | Co zmienia |
|---|---|---|
| Kontrprzykłady na obalenie (`cex_cap`) | 50 (dotąd), 5, 1 | Weryfikator zwraca jeden kontrmodel, jak typowy prover/solver. Pamięć przycina mniej. |
| Słownik | „baza” (24 + ⊤), „negacje” (+ ¬X dla każdego pojęcia, 48 + ⊤) | Więcej par, wykluczenia, więcej fałszywych kandydatur. |
| Rząd magm | 3, 4 (U4) | Większy, rzadszy świat. |

Konfiguracje: pełna siatka 3 × 2 × 2 = 12, na prawach S-0 i ziarnach 0–19.

## Miary trudności (liczone ewaluatorem z prawdą podstawową; to kalibracja świata, nie porównanie ramion)

Po czuwaniu 1 (wspólnym dla wszystkich ramion):
- **p_los:** trafność puli losowej (pary nierozstrzygnięte, niewynikające z wiedzy, nieobalone pamięcią), czyli kandydatur S-los.
- **p_śm:** trafność puli śmiałych przeczuć (wsparcie 1 w znanych magmach, przycięte pamięcią).
- **p_pow:** trafność puli powtórki (wsparcie ≥ 2).
- **pokrycie_dnia:** odsetek |TR| pokryty przez czuwanie 1.
- **|TR|**, rozmiar puli śmiałych przeczuć.

„Prawdziwa” = weryfikator nie znajduje kontrprzykładu w świecie (także pusto, gdy przesłanka nie zachodzi).

## Kryteria wyboru T1 (zapisane przed pomiarem)

Świat nadaje się do S-1, jeśli (średnio po prawach i ziarnach):
1. p_los ≤ 0,30 (losowy przegląd jest w większości chybiony),
2. p_śm ≤ 0,50 (śmiałe przeczucia są w większości fałszywe, więc wybór ma znaczenie),
3. p_śm ≥ 0,05 i pula śmiałych przeczuć ≥ 20 (jest z czego wybierać i co trafić),
4. pokrycie_dnia ≤ 0,60 i |TR| ≥ 15 (dzień nie rozwiązuje świata sam).

Spośród spełniających wybieramy najprostszą konfigurację (kolejność: rząd 3 przed 4, „baza” przed „negacje”, większy `cex_cap` przed mniejszym),
żeby zmieniać jak najmniej względem S-0b. Jeśli żadna nie spełnia, raportujemy to jako wynik i proponujemy kolejną dźwignię (koniunkcje przesłanek).

---

## Wynik kalibracji (23.11, `wyniki/T1_KALIBRACJA.md`)

**[WYNIK] Pierwsza siatka (cex × słownik „baza”/„negacje” × rząd) nie dała żadnego świata spełniającego kryteria.**
- Po czuwaniu 1 losowa pula jest trafna w 37–49% („baza”), a śmiałe przeczucia w 58–79%. Wartość ~90% z S-0/S-0b dotyczyła
  późniejszych cykli, gdy pamięć kontrprzykładów już urosła.
- Mniej kontrprzykładów (`cex_cap` 1) obniża trafność tylko lekko.
- **Hipoteza o negacjach obalona:** zaprzeczenia czynią świat *łatwiejszym* (p_śm 0,83–1,00), bo wykluczenia między pojęciami są zwykle prawdziwe.

Zgodnie z ostatnim zdaniem kryteriów dodano kolejną dźwignię, zamiast koniunkcji przesłanek prostszą i bliższą idei LMM:
**literały** `a·b=c` (pojedyncze wpisy tablicy działania; 27 w rzędzie 3, 64 w rzędzie 4) jako dodatkowe pojęcia. To najniższy poziom
„tokenów zależności”: prawo H wymusza zależności między wpisami (np. komutatywność: `0·1=2 ⇒ 1·0=2`), a przypadkowe współwystępowania
dają fałszywe przeczucia. Wariant „tylko literały” okazał się za trudny: śmiałych przeczuć praktycznie nie ma (pula 0–8).

| Konfiguracja | p_los | p_śm | pula śm. | |TR| | pokrycie dnia | Kryteria |
|---|---|---|---|---|---|---|
| rząd 3, baza + literały, cex 1 | 0,25 | 0,47 | 71 | 62 | 0,39 | **spełnia (T1)** |
| rząd 4, baza + literały, cex 1 | 0,26 | 0,20 | 98 | 77 | 0,34 | spełnia (T1-4) |
| rząd 3, baza + literały, cex 5 | 0,37 | 0,58 | 45 | 62 | 0,40 | nie |

## Wybór

- **T1 = rząd 3, słownik „baza + literały”, weryfikator zwraca 1 kontrprzykład.** To najprostsza konfiguracja spełniająca kryteria (reguła wyboru zapisana z góry).
- **Zastrzeżenie:** p_śm = 0,47 leży tuż pod progiem 0,50 i różni się między prawami (komutatywna 0,31, łączna 0,64). W dwóch prawach śmiałe przeczucia są nadal częściej prawdziwe.
- **T1-4 = to samo w rzędzie 4** (p_śm = 0,20, wszystkie prawa ≤ 0,27) jako świat do replikacji S-1. Ewentualne wyniki S-1 powinny wymagać zgodności w T1 i T1-4.
- Test dymny pętli w T1 i T1-4 (prawo spoza S-0, ziarno 99) działa: dzień, sen i losowy przegląd kończą się poprawnie, ok. 0,1–0,5 s na przebieg.

## Szkic S-1 (do osobnej prerejestracji)

Pytanie: czy intuicja wybiera lepsze śmiałe przeczucia niż przypadek? Ramiona różnią się **tylko** portem `Intuicja`: losowy wybór,
`HeurystykaOgolnosci`, później LMM. Miary: trafność obudzonych przeczuć i pokrycie TR **przy równym zużytym budżecie** (lekcja z recenzji S-0b),
w T1 i T1-4. Adapter LMM musi czytać macierz zależności, której węzłami są także literały `a·b=c`.
