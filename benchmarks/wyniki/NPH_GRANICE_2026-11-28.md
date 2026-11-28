# Granice NPH* w D1-W (2026-11-28): gdzie naprawdę jest luka

PILOT, NIE TEST. 30 światów afinicznych (ziarna 2000–2029, jak w pilocie 2026-11-23), ramię C, K = 20.
Surowe dane: `zawezenie_2026-11-28.json`.

Zmiany w sprawdzaczu (z testami kontrolnymi):
- `entail.countermodel_any`: magma spełniająca aksjomaty i łamiąca co najmniej jedno prawo z listy (SAT).
- Dolna granica: |E| + DOKŁADNY minimalny zbiór trafiający rodziny zbiorów łamanych praw (`basis.min_hitting_set`).
  Opcjonalnie (`pairs=True`) rodzina dostaje dla każdej pary praw magmę spełniającą wszystkie pozostałe.
- Górna granica: harmonogram dowodnika `extra_ops=(2, 4)`, czyli najpierw wąskie, potem szersze termy pośrednie.

| Konfiguracja | dolna | górna | domknięte | czas (30 światów) |
| --- | --- | --- | --- | --- |
| poprzednia (PR #5) | 1,17 | 3,30 | 10/30 | 198 s |
| + pary kontrmodeli | 1,23 | 3,30 | 10/30 | 2021 s |
| + harmonogram dowodnika | 1,17 | 2,63 | 11/30 | 648 s |
| oba | 1,23 | 2,63 | 12/30 | 2427 s |

- WYNIK: dolna granica nigdy nie przekroczyła górnej (0/120 par).
- WYNIK NEGATYWNY: pary kontrmodeli podnoszą dolną granicę tylko o 0,07 przy ~10 razy większym koszcie.
  Zostają wyłączone domyślnie (`pairs=False`).
- WYNIK: szerszy dowodnik obniża górną granicę o 0,67 (3,30 → 2,63) przy ~3 razy większym koszcie.
  Staje się domyślny (`extra_ops=(2, 4)`).
- WNIOSKOWANIE: w światach takich jak 2018 (x*y = x + 2y mod 5) żadna magma rozmiaru ≤ 5 nie oddziela dwóch
  zaakceptowanych praw przy pozostałych 18. Luka 1–10 leży więc najpewniej po stronie górnej. Prawa są tam
  wzajemnie wyprowadzalne, ale dowody wymagają termów pośrednich większych niż prawa.
- HIPOTEZA: prawdziwe NPH* w wielu takich światach wynosi 1–2. Dalsze zawężanie to sprawa dowodnika
  (uzupełnianie Knutha–Bendixa albo zewnętrzny Prover9/Twee), nie kontrmodeli.
- WNIOSKOWANIE dla metryki: główna metryka to górna granica, więc siła dowodnika jest częścią jej definicji.
  `extra_ops`, `node_limit` i rozmiary kontrmodeli trzeba zamrozić razem ze specyfikacją, przed testem właściwym.
