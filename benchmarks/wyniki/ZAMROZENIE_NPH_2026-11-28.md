# Zamrożenie sprawdzacza metryki głównej NPH* (2026-11-28)

Decyzja Michała (2026-11-28, „tak”): parametry sprawdzacza zamrożone razem z metryką
(specyfikacja 2.0). Metryka główna bez zmian: GÓRNA granica NPH* z wynikaniem, dolna zawsze obok.

## Co jest zamrożone (`lmm_bench/zamrozenie.py`, wersja NPH-1)

| Parametr | Wartość | Uzasadnienie (raport) |
|---|---|---|
| rozmiary kontrmodeli | 2, 4, 5 | rozmiar 6 nic nie daje (ETAP2_CD) |
| node_limit | 50000 | NPH_GRANICE |
| pakowanie kontrmodeli | tak | ETAP2_CD |
| podstawienia zmiennych wolnych | tak | ETAP2_CD |
| harmonogram dowodnika | wąski (2 op.) → twee → szeroki (4 op.) | NPH_GRANICE, TWEE |
| pary kontrmodeli | nie | WYNIK NEGATYWNY: +0,07 za 10× koszt |
| twee | 2.4.2, SHA256 75e69a47…7e6e, 3 s na prawo, `--no-lemmas` | TWEE |
| pętla kontrprzykładów | tak (max 60 iteracji) | CEGAR |
| kod sprawdzacza | SHA256 8ece1804…46b1 z terms, proofcheck, entail, basis, twee | – |

## Jak to działa

- Runnery liczą NPH* przez `zamrozenie.nph_zamrozone(accepted, initial)` i zapisują `zamrozenie.opis()` w wyniku.
- `sprawdz()` uruchamia się PRZED liczeniem: inny kod sprawdzacza, inna wersja twee albo brak twee
  kończą się błędem `ZamrozenieNaruszone` (bez twee metryka jest niedostępna, nie „słabsza”).
- Każda zmiana modułów sprawdzacza wymaga świadomego ponownego zamrożenia (nowa WERSJA i hash);
  test `test_zamrozenie_kod_i_parametry` pilnuje tego w CI/lokalnie.

## Kontrola odtworzenia

WYNIK: `nph_zamrozone` odtwarza zapisane granice z `cegar_2026-11-28.json` na światach 2000–2005
(6/6 zgodnych). 62 testy przechodzą.

## Czego zamrożenie nie zmienia

- Na 30 światach afinicznych przedział średnio 1,57–2,00, domknięte 17/30 (CEGAR_2026-11-28).
  13 światów ma lukę 1; górna granica w nich może być zawyżona o 1 (WNIOSKOWANIE z definicji).
- Otwarte decyzje specyfikacji (rodzina D2, limit K, minimalny ważny efekt, rozmiar H w D1') bez zmian.
