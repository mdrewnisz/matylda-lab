# LMM-bench — etap 1 (sprawdzacze przed modelem)

Specyfikacja: „Specyfikacja 2.0: benchmark zdolności odkrywczej LMM z harnessem” (Claude Doc projektu Matylda LMM).
Status specyfikacji: **rewizja 2.0, NIEZAMROŻONA**. Ten katalog zawiera wyłącznie elementy etapu 1,
które nie zależą od otwartych decyzji ani od kodu LMM. Nie wywołuje żadnego modelu ani sieci.

Zasada „sprawdzacz najpierw”: kod oceniający powstaje i jest testowany na przypadkach kontrolnych
(znane przyjęte, podrzucone błędy odrzucone), zanim jakikolwiek model zgłosi pierwszą hipotezę.

## Moduły

| Moduł | Zawartość |
| --- | --- |
| `lmm_bench/terms.py` | DSL praw jednego działania `*`: parser, wypisywanie, ewaluacja wyczerpująca na tabeli, kanonizacja (przemianowanie zmiennych, orientacja, dualność), flaga zakresu ETP (≤ 4 operacje) |
| `lmm_bench/worlds.py` | Magmy rozmiaru 4–7: losowe, afiniczne (`a x + b y + c mod n`), jednoargumentowe (`f(x)` lub `f(y)`), izotopy `σ(x)+τ(y)`, przemianowanie izomorficzne, pełne rodziny afiniczne; polityka ziaren |
| `lmm_bench/status.py` | Statusy z zakresem W / K / U: `TRUE_IN_WORLD`, `FALSE_IN_WORLD`, `NIEOBALONA_W_ZAKRESIE`, `PROVED_FROM_AXIOMS`, `DISPROVED`, `UNKNOWN` |
| `lmm_bench/proofcheck.py` | Sprawdzacz dowodów równaniowych (łańcuch przepisań z jawną pozycją i wynikiem); jedyna droga do `PROVED_FROM_AXIOMS` |
| `lmm_bench/basis.py` | NPH* dla implikacji między własnościami (dokładnie, domknięcie Horna) i dla praw w świecie (przedział dolna–górna); Novelty N1 |
| `lmm_bench/entail.py` | Sprawdzacz wynikania Γ ⊨ L: dowodnik równaniowy (dowody sprawdza `proofcheck`) i kontrmodele SAT rozmiaru 2, 4, 5 (pysat) |
| `lmm_bench/pilot.py` | Pilot etapu 2 bez LMM: ramiona C, R0, E na zadaniu D1-W; wyniki w `wyniki/` |
| `lmm_bench/etp.py` | Filtr dokładny względem listy Equational Theories Project (`dane/etp_equations.txt`, hash sprawdzany) |
| `lmm_bench/d1prime.py` | Klasa D1': rodziny światów F/H, sprawdzacz nowego pojęcia (warunki a–c), implikacji nad rodziną i wynik; pilot ramion E, R0, C |
| `lmm_bench/zawezenie.py` | Pomiar zawężenia przedziału NPH* przy mocniejszych ustawieniach sprawdzacza |
| `lmm_bench/controls.py` | Kontrole bez modelu: enumerator E i losowe R0, ta sama gramatyka i ten sam limit K |

## Polityka ziaren i rozmiarów (uzgodniona z wątkiem KG, 2026-11-22)

- 0–19: pilot KG-0b (WIDZIANE), 1000–1049: zbiór potwierdzający KG-1 (zarezerwowany).
- Benchmark używa ziaren **≥ 2000**; `worlds.check_policy` odrzuca inne.
- Magmy rozmiaru 3 są zablokowane, dopóki KG-1 nie przejdzie.

## Poziomy pewności tego, co tu jest

- WYNIK: 52 testy kontrolne przechodzą (`python -m pytest benchmarks/tests -c /dev/null`).
- WYNIK: `basis.nph_star_laws_entail` daje obie granice NPH* z certyfikatami (dowód albo kontrmodel).
  Starsza `nph_star_laws` (modele referencyjne) zostaje tylko do porównania: jej dolna granica nie jest poprawna.
- Zależność: `python-sat` (pip). Bez niej kontrmodele tylko rozmiaru 2.
- WYNIK (sprawdzone 2026-11-27): lista ETP to 4694 prawa o ≤ 4 operacjach (do 6 zmiennych). Cała pula
  `law_pool(4)` (1476 praw, ≤ 3 zmienne) leży w ETP, więc wariant N wymaga praw o ≥ 5 operacjach
  (`d1prime.pool_variant_N`: 12 072 prawa ≤ 5 operacji spoza ETP).

## Czego tu jeszcze nie ma (czeka na decyzje lub etap 2)

- Rodzina D2 (wybór rodziny czeka na decyzję), detektor struktury.
- Novelty N2 (wymaga próby referencyjnej 1000 światów), profil DP.
- Jakiekolwiek ramię z modelem (etap 3; kodu LMM nie ma w repozytoriach).

Testy uruchamia się z katalogu repozytorium:

```
python -m pytest benchmarks/tests -c /dev/null
```

(`-c /dev/null` omija `pytest.ini` aplikacji Lab, którego testy wymagają FastAPI.)
