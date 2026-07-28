# Epistemic Preregistration Cycle — silo_1

> Dodane: 2026-05-19
> Cel: wyeliminować self-reporting circularity w claim_map.
> Wzorowane na s2t_config.yaml z AI_projekty.

---

## Problem który to rozwiązuje

Bez prerejestracji: claim_map ocenia twierdzenia i zwraca confidence. Nie ma żadnej
gwarancji że kluczowe kontrargumenty zostały w ogóle rozważone. AI może (nieświadomie)
potwierdzać twierdzenia które chce potwierdzić — szczególnie gdy tekst jest przekonujący.

Prerejestracja odwraca kolejność: najpierw określasz co mogłoby obalić twierdzenie,
potem dopiero analizujesz. Wynik "supported" oznacza wtedy: "wsparte przy aktywnie
szukanym kontrargumencie", nie "wsparte bez szukania dziur".

---

## Cykl (4 kroki)

```
Krok 1: paper_review
  ↓ wejście:  artykuł / tekst / twierdzenia
  ↓ wyjście:  mandatory_counterargument per claim
              + preregistration_export (gotowy blok YAML)

Krok 2: prerejestracja [RĘCZNIE — ty]
  ↓ przejrzyj preregistration_export
  ↓ dostosuj progi i kontrargumenty jeśli potrzeba
  ↓ skopiuj jako input do claim_map
  ↓ WAŻNE: od tego momentu nie zmieniaj progów po obejrzeniu wyników

Krok 3: claim_map z preregistered_counterarguments
  ↓ wejście:  tekst + preregistration_export z Kroku 2
  ↓ enforcement: każdy kontrargument musi być jawnie zaadresowany
              brak zaadresowania → confidence cap 0.5 automatycznie
  ↓ wyjście:  claim_entries z counterargument_addressed + epistemic_status

Krok 4: DARKROOM
  ↓ review wyników — sprawdza czy confidence_cap_applied jest uzasadniony
  ↓ flaguje twierdzenia z counterargument_addressed: false
```

---

## Progi (domyślne)

| Typ twierdzenia | suggested_threshold | level_isolation |
|---|---|---|
| Kauzalne ("X powoduje Y") | 0.90 | strict |
| Empiryczne / pomiarowe | 0.80 | strict |
| Interpretacyjne / teoretyczne | 0.70 | relaxed |
| Spekulatywne / hipoteza | 0.60 | relaxed |

**strict** = wyniki analizy NIE mogą uzasadniać zmiany progu ex-post.
**relaxed** = korekta progu dopuszczalna jeśli nowe dane ją uzasadniają
             (ale wymaga jawnego uzasadnienia w notatce).

---

## Format mandatory_counterargument

**Wzorzec:**
```
"Nawet jeśli [twierdzenie], może to wynikać z [alternatywna przyczyna].
Sprawdź: [konkretna operacja weryfikacyjna z oczekiwanym wynikiem]."
```

**Dobry przykład:**
```
"Nawet wysokie R²=0.91 może odzwierciedlać overfitting na małej próbie.
Sprawdź: czy wynik utrzymuje się przy 5-fold cross-validation
na niezależnym zbiorze walidacyjnym (oczekiwane: R² > 0.75)."
```

**Zły przykład (zbyt ogólny):**
```
"Wyniki mogą nie być generalizowalne na inne konteksty."
```
Zły dlatego że: nie wskazuje konkretnego testu, nie podaje kryterium sukcesu,
nie jest falsyfikowalny operacyjnie.

---

## Szablon prerejestracji (do wklejenia w claim_map)

```yaml
preregistered_counterarguments:
  - claim_id: "claim_01"
    counterargument: >
      Nawet jeśli [X], może to wynikać z [Y].
      Sprawdź: [konkretny test, oczekiwany wynik].
    confidence_threshold: 0.80
    level_isolation: strict

  - claim_id: "claim_02"
    counterargument: >
      ...
    confidence_threshold: 0.70
    level_isolation: relaxed
```

---

## Kiedy NIE stosować prerejestracji

- Wstępna eksploracja (chcesz zobaczyć co jest w tekście, nie oceniać hipotez)
- Analiza jakościowa bez twierdzeń falsyfikowalnych
- Szybka mapa literatury (użyj claim_map v1.0 bez prerejestracji)

W tych przypadkach: pomiń `preregistered_counterarguments`, a claim_map
wygeneruje `suggested_preregistration` do użycia w następnej rundzie.

---

*silo_1 / Science · epistemic preregistration v1.0 · 2026-05-19*
