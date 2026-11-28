# Pilot odniesienia na zamrożonym NPH-1 (2026-11-28)

Ramiona bez modelu (C, E, R0) z parametrami przyjętymi 28.11; runner `lmm_bench/odniesienie.py`,
dane `odniesienie_2026-11-28.json`, czas 22 min. Pilot, nie test (ziarna pilotowe).

## D2 wersja 2 (20 rodzin, 2250–2269, K = 20)

| Ramię | Generalizacja | NPH* |
|---|---|---|
| C' (CRT) | 1,00 | 0 |
| E, R0 | 0,00 | 0 |

WYNIK: sufit narzędziowy 1,00, kontrole 0,00 – cała skala jest dostępna dla A i B1.

## D1' (10 par, 2110–2129, K = 30, |H| = 20)

| Ramię | NPH* reguł | Najwięcej zgłoszeń |
|---|---|---|
| C | 10,9 (sd 3,7) | 22 |
| C wariant N | 12,1 (sd 8,0) | 28 |
| E | 1,0 | 30 |
| E wariant N | 0,0 | 30 |
| R0 | 0,4 | 30 |
| R0 wariant N | 0,1 | 30 |

- WYNIK: przy K = 30 pętla C nadal dochodzi blisko limitu w wariancie N (28/30) w jednej parze.
- WYNIK (ważny dla mocy): odchylenie NPH* pętli C w wariancie N wynosi 8,0, a prerejestracja założyła
  odchylenie różnic par ≤ 4,9 (z pilota 5 par: 4,0). WNIOSKOWANIE: jeśli odchylenie różnic B1 − A będzie
  podobne do odchylenia C, 40 par daje moc wyraźnie poniżej 0,8 dla efektu 2 (dla sd 8 potrzeba ok. 125 par).
  To nie jest wynik testu, tylko przesłanka do aneksu przed etapem 3.

## D1-W (60 światów, 2000–2059, K = 20), NPH* z wynikaniem (dolna–górna)

| Rodzaj | C | E | R0 |
|---|---|---|---|
| afiniczne | 1,57–2,00, domknięte 17/30 | 0,50–0,50 | 0,97–1,07 |
| losowe | 0,43–0,43, domknięte 30/30 | 0,03 | 0,00 |

WYNIK: zgodne z CEGAR_2026-11-28 (afiniczne C 1,57–2,00); w losowych przedział domknięty wszędzie.
