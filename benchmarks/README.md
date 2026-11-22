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
| `lmm_bench/worlds.py` | Magmy rozmiaru 4–7: losowe i afiniczne (`a x + b y + c mod n`), przemianowanie izomorficzne, pełne rodziny afiniczne; polityka ziaren |
| `lmm_bench/status.py` | Statusy z zakresem W / K / U: `TRUE_IN_WORLD`, `FALSE_IN_WORLD`, `NIEOBALONA_W_ZAKRESIE`, `PROVED_FROM_AXIOMS`, `DISPROVED`, `UNKNOWN` |
| `lmm_bench/proofcheck.py` | Sprawdzacz dowodów równaniowych (łańcuch przepisań z jawną pozycją i wynikiem); jedyna droga do `PROVED_FROM_AXIOMS` |
| `lmm_bench/basis.py` | NPH* dla implikacji między własnościami (dokładnie, domknięcie Horna) i dla praw w świecie (przedział dolna–górna); Novelty N1 |
| `lmm_bench/controls.py` | Kontrole bez modelu: enumerator E i losowe R0, ta sama gramatyka i ten sam limit K |

## Polityka ziaren i rozmiarów (uzgodniona z wątkiem KG, 2026-11-22)

- 0–19: pilot KG-0b (WIDZIANE), 1000–1049: zbiór potwierdzający KG-1 (zarezerwowany).
- Benchmark używa ziaren **≥ 2000**; `worlds.check_policy` odrzuca inne.
- Magmy rozmiaru 3 są zablokowane, dopóki KG-1 nie przejdzie.

## Poziomy pewności tego, co tu jest

- WYNIK: 25 testów kontrolnych przechodzi (`python -m pytest benchmarks/tests -c /dev/null`).
- WNIOSKOWANIE: dolna granica NPH* dla praw zależy od próby modeli referencyjnych; mała próba
  może uznać niezależne prawo za redundantne. Górna granica (tylko podstawienia) może zawyżać NPH*.
  Raportujemy oba końce.
- Z PAMIĘCI, DO SPRAWDZENIA: że Equational Theories Project objął prawa o ≤ 4 operacjach.
  Flaga `in_etp_size_range` opiera się na tym założeniu, a filtr dokładny wymaga pobrania listy ETP.

## Czego tu jeszcze nie ma (czeka na decyzje lub etap 2)

- Generator D1' (nowe pojęcia), rodzina D2 (wybór rodziny czeka na decyzję), detektor struktury.
- Filtr dokładny względem listy ETP, Novelty N2 (wymaga próby referencyjnej 1000 światów), profil DP.
- Jakiekolwiek ramię z modelem (etap 3; kodu LMM nie ma w repozytoriach).

Testy uruchamia się z katalogu repozytorium:

```
python -m pytest benchmarks/tests -c /dev/null
```

(`-c /dev/null` omija `pytest.ini` aplikacji Lab, którego testy wymagają FastAPI.)
