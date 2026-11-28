# Prerejestracja: benchmark harnessu LMM (spec 2.0) – ZAMROŻONA 2026-11-28

Status: ZAMROŻONA 2026-11-28 (zgoda Michała na pakiet decyzji, D2 wersja 2 i próg θ = 0,2).
Zamrożenie = commit tego pliku; hash commitu jest w historii git i zostanie podany w raporcie testu.
Runner testu (etap 3, ramiona z modelem) jeszcze nie istnieje: przed uruchomieniem dopisujemy go
ANEKSEM (osobny commit z jego hashem i hashami z sekcji 10), bez zmiany sekcji 1–9. Specyfikacja: Claude Doc „Specyfikacja:
benchmark harnessu LMM inspirowany GSI” (wersja 2.0 z decyzjami z 22–28.11).

## 1. Pytanie

Czy harness (B1) poprawia zdolność odkrywczą tego samego modelu względem samego modelu (A),
przy równym budżecie modelu (E1)? Trening LMM się nie zmienia.

## 2. Hipotezy główne (kontrast B1 − A, jednostronnie)

| Id | Klasa | Metryka | Minimalny ważny efekt | Jednostka |
|---|---|---|---|---|
| H1 | D1', wariant N | NPH* reguł (dokładne, domknięcie Horna) | 2 | para rodzin F/H |
| H2 | D2 (wersja 2) | generalizacja (ułamek z 28 przypadków n = 13..40) | θ = 0,2 (decyzja Michała 28.11) | rodzina |

Ogłaszamy „harness poprawia odkrywanie” tylko wtedy, gdy H1 lub H2 przejdzie po korekcie Holma
(α = 0,05 łącznie) ORAZ precyzja B1 nie jest niższa od A o więcej niż 0,05 (test równoważności po stronie spadku).
Kontrasty pozostałe (B0, B−KL, A+, C, R0, E, D1-W) są opisowe i nie mogą uzasadnić ogłoszenia.

## 3. Ramiona i budżet

- A, A+, B0, B1, B−KL – jak w spec 2.0. Ten sam model, te same prompty bazowe, te same limity.
- Kontrole bez modelu: C (pętla narzędziowa; w D2: C' = układy mod n + CRT), R0, E.
- E1: równy budżet modelu (wywołania i tokeny) dla A i B1; E2 (równy koszt całkowity) raportowany obok.
- Limit zgłoszeń K: 20 w D1-W i D2, 30 w D1'.

## 4. Klasy i parametry (zamrożone razem z tym plikiem)

- D1-W (diagnostyka): magmy afiniczne i losowe rozmiaru 4–6, pula praw ≤ 4 działań, NPH* z wynikaniem
  sprawdzaczem NPH-1 (`lmm_bench/zamrozenie.py`, hash kodu 8ece1804…46b1, twee 2.4.2).
- D1': |F| = |H| = 20 magm rozmiaru 5–7 (`d1prime.make_family`), 8 pojęć podanych, warunki (a)–(c),
  wariant N = pojęcia spoza ETP (`etp.py`, SHA256 danych e30e1a67…c8010).
- D2 wersja 2 (`d2.make_family(seed, wersja=2)`): a, c < 13 860; b, d, e, f < 27 720; uczenie n = 4..12;
  test n = 13..40 z niezależnego generatora (`d2._tabela_niezalezna`).
- Magmy rozmiaru 3 wykluczone wszędzie (blokada KG-1); w D2 także n = 2.

## 5. Ziarna (zarezerwowane, nieużyte przed testem)

| Klasa | Ziarna testu | Liczność |
|---|---|---|
| D1' | 3000–3079 (pary F = parzyste, H = nieparzyste) | 40 par |
| D2 | 3100–3195 | 96 rodzin |
| D1-W | 3300–3359 (30 afinicznych, 30 losowych) | 60 światów |

Recenzja przed: 3400–3409; recenzja po: 3410–3419. Ziarna pilotowe 2000–2999 nie wchodzą do testu.

## 6. Analiza

- H1: średnia sparowana różnica NPH* (B1 − A) na 40 parach; test permutacyjny znaków (10 000 permutacji),
  jednostronny; przejście = p < α_Holm ORAZ średnia ≥ 2.
- H2: średnia sparowana różnica generalizacji na 96 rodzinach; ten sam test; przejście = p < α_Holm ORAZ średnia ≥ θ.
- Liczności z tabeli mocy specyfikacji (moc 0,8): D1' przy odchyleniu różnic ≤ 4,9 (pilot C: 4,0 w wariancie N);
  D2 przy odchyleniu różnic ≈ 0,7.
- Brak analiz pośrednich i brak zatrzymania wcześniejszego. Rodzina z błędem wykonania (nie z błędem modelu)
  jest powtarzana raz z tym samym ziarnem; drugi błąd = wykluczenie i raport.
- Raport zawsze podaje obie granice NPH* (górna = metryka główna) tam, gdzie NPH* liczone wynikaniem.

## 7. Integralność

- Runner testu sprawdza PRZED startem: hash własnego pliku względem hasha zapisanego tutaj przy zamrożeniu,
  `zamrozenie.sprawdz()` (kod sprawdzacza i twee) oraz że żadne ziarno testu nie występuje w `wyniki/`.
- Wynik testu ocenia niezależny recenzent (osobny agent) przed interpretacją.

## 8. Warunki falsyfikacji i odczyt wyników

- H1 i H2 niepotwierdzone przy spełnionej mocy → WYNIK NEGATYWNY dla harnessu w tej konfiguracji
  (przed wnioskiem: test formatu zadań z etapu 3, spec 2.0).
- B1 ≈ C (lub C') w D1'/D2 jest oczekiwanym sufitem narzędziowym, nie porażką; B1 ≈ E w D1'/D2 = WYNIK NEGATYWNY dla modelu.

## 9. Pilot odniesienia (przed testem)

`lmm_bench/odniesienie.py` na ziarnach pilotowych (D1-W 2000–2059, D1' 2110–2129, D2 2250–2269):
wartości C, E, R0 na zamrożonym NPH-1. Wyniki: `wyniki/odniesienie_2026-11-28.json` i raport.

## 10. Hashe zamrożonego kodu (SHA256)

| Plik | SHA256 |
|---|---|
| kod sprawdzacza NPH-1 (terms, proofcheck, entail, basis, twee) | 8ece1804866dfde32518429aa3ab41c9ca6d8ef00e768d66bf7504285db746b1 |
| lmm_bench/zamrozenie.py | 5e09ba20c19ba0e5e0a0a8fea61a69bc54a7cd7b73eb4c4f386009e9ef74c98c |
| lmm_bench/d1prime.py | 0ab71574fcc4dda090bd91c1315cb1be315b24d0610c476676eafbb4aa98afaa |
| lmm_bench/d2.py | 5368b4236ca448d3ebe9ef1121b35d0aa6bcf63a2d1c72e4ab3091484cce3482 |
| lmm_bench/etp.py | f41bf129ccb75535b2209854987a63edc63fcc414219cdfa667bc91a89d03994 |
| lmm_bench/controls.py | 73855097a6b20d5fb63c9594b4bb5f3b15cccaa3ccfd222f1d315b8aad91273d |
| twee 2.4.2 (binarka) | 75e69a47166f7f5c54facde4a8c71a33552b4cb20bdac8b7ece9536f94e07e6e |
