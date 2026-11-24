# Matylda: rdzeń (prototyp pętli badacza)

Prototyp pętli **czuwanie → sen → przebudzenie** z dokumentu „Matylda: rdzeń” (v0.2) i Masterplanu v1.1, rozdz. 0.
Samodzielny pakiet: Python + numpy, bez LLM, bez GPU, bez reszty Lab. Praxis jest zależnością opcjonalną.

```
czuwanie ──► sen (offline) ──► przebudzenie ──► czuwanie …
  okno,        konsolidacja,      seedy z           weryfikator
  proponujący, powtórka,          genealogią        sprawdza
  weryfikator  przycinanie,       → Praxis (SEED)   intuicje
               port Intuicja (LMM)
```

| Moduł | Co robi | Skąd |
|---|---|---|
| `swiat.py` | Świat zamknięty: magmy rzędu 3 z podłożonym prawem; prawda podstawowa tylko dla ewaluatora | przeniesione z `kg/kg0b_magmy.py` |
| `pamiec.py` | Graf wiedzy (statusy, kontrprzykłady, genealogia), konsolidacja, **tokeny zależności** (macierz porządku częściowego klas), weryfikator, który tylko obala | KG-0 / KG-0b |
| `fazy.py` | Proponujący dnia, czuwanie, strategie snu (S, S−K, S-los), kontrola W+, przebudzenie | nowe |
| `intuicja.py` | Port `Intuicja`: dziś `HeurystykaOgolnosci`, miejsce na `IntuicjaLMM` | nowe |
| `petla.py` | Pętla z budżetem weryfikatora; sen ma asercję „zero wywołań weryfikatora” | nowe |
| `praxis_most.py` | Seedy z przebudzenia → `HypothesisRecord.seed` w Praxis albo JSON | most do Praxis |
| `s0.py` | Eksperyment S-0 wg `PREREJESTRACJA_S0.md` | nowe |

## Zasady wbudowane w kod

- Weryfikator umie tylko obalać. Przetrwanie = `skontrowana` w tym świecie, nigdy WYNIK ogólny.
- Sen nie ma weryfikatora, świata ani prawdy podstawowej i nie zmienia statusów (test + asercja).
- Czuwanie 1 jest identyczne we wszystkich ramionach i odtwarza KG-0b co do krzywej (test regresji na 100 przebiegach).
- LMM jest intuicją Matyldy na tokenach zależności. Koder LMM (`lmm/bsd2/models.py`, `PosetEncoder`) czyta boolowską macierz relacji
  N × N; `Pamiec.konsolidacja().macierz_zaleznosci` ma ten format. Adapter wejdzie po S-0 i V0/V1/V2.

## Uruchomienie

```bash
cd rdzen
python -m pytest            # testy prototypu (Praxis opcjonalnie: pip install -e ../Matylda-praxis)
python -m matylda_rdzen.s0  # S-0: zapis do wyniki/s0_wyniki.json i wyniki/S0_RAPORT.md
```

## Stan wyników (23.11)

S-0 i S-0b mają prerejestracje i surowe wyniki w `wyniki/`. Po niezależnej recenzji poprawiono dwa błędy kontroli
(dopasowanie świeżych magm w W+/W+S, zapętlenie S-los) i dodano miarę przy równym zużytym budżecie:
**aktualne wnioski są w `wyniki/RECENZJA_I_WNIOSKI_S0_S0B.md`** (powtórka porażek: wynik negatywny; sen jako generator
po wygaśnięciu dnia: wynik eksploracyjny). `s0_wyniki.json` i `s0b_wyniki.json` pochodzą z kodu sprzed poprawek.

## Czego tu świadomie nie ma

GUI, dashboardu, homeostazy, Focus Mode, routera modeli, wielu agentów ani prawdziwego LMM. Najpierw wynik pętli, potem framework.
Weryfikator jest wymienny: kolejnym krokiem może być sprawdzacz wynikania z `benchmarks/lmm_bench/entail.py` (PR #1).

## S-1 (prerejestracja zamrożona 24.11)

`PREREJESTRACJA_S1.md`: czy intuicja (port `Intuicja`) wybiera lepsze przeczucia niż los, w T1 i T1-4. Ramiona: losowa, heurystyka,
wyrocznia pokrycia (bramka) i wyrocznia trafności (opisowa). Miara główna: pole pod krzywą pokrycia po dniu 1 przy równym zużytym budżecie,
80 ziaren (100–179). Recenzja przed uruchomieniem: `wyniki/S1_RECENZJA_PRZED.md`; analiza mocy na prawach spoza S-0: `wyniki/s1_moc_prawa_spoza_s0.json`.
Uruchomienie: `python -m matylda_rdzen.s1` (wymaga czystego drzewa). Ramię LMM tylko przez osobną poprawkę (sekcja 7).
