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
