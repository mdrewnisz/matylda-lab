# Prerejestracja: heurystyka grafu ze wsparciem (wzmocnienie w rzędzie 4)

Status: **projekt do zamrożenia** (27.11). Seria samodzielna za zgodą Michała (27.11); cel programu bez zmian.
Zamrożenie = commit tego pliku z `heur4_walidacja.H4_SHA` = sha256 `heurystyki4.py` przed pierwszym `python -m matylda_rdzen.heur4_walidacja`.

## 1. Pytanie i hipoteza

Test S-0 (`wyniki/S0_HEUR_RAPORT.md`): heurystyka grafu w rzędzie 4 lepsza tylko w 3/5 praw (kruche). Recenzja wskazała HIPOTEZĘ: reguła pomija wsparcie.
**H:** wariant `HeurystykaGrafuWsparcie(λ = 1)` = out(a) + out(b) + λ·m·wsparcie/n − 3·[śmiałe] (m = liczba klas, deduplikacja par klas)
jest lepszy od `HeurystykaGrafu("oa+ob+kara")` w rzędzie 4.

## 2. Jak wybrany (jawnie)

Dewelopment wyłącznie na losowych prawach na U4 (żywe węzły-prawa; `heur4_dev.py`):
- 60 światów, ziarna 1800–1809, λ ∈ {0,25; 0,5; 1; 2} i wariant bez out(a): wszystkie > grafu (λ = 1: średnio +0,30, 65% światów > 0) — `wyniki/heur4_dev.json`;
- potwierdzenie: kolejne 60 światów, ziarna 1810–1819, λ ∈ {0,5; 1}: λ = 1 średnio +0,61, mediana +0,25, 80% światów > 0 — `wyniki/heur4_dev_potw.json`.
Wybrano λ = 1 (wyższa średnia w obu zestawach). Opisowo: heurystyka grafu − stara heurystyka w tych światach +1,73 i +0,92.

## 3. Prawa walidacyjne (nowe)

8 praw, dobranych regułą zapisaną w `wyniki/heur4_wybor_praw_kod.py.txt`: świat ≥ 20 magm i |TR| ≥ 15 w rzędzie 3 i 4; świat (ani jego transpozycja,
czyli prawo dualne) nie pokrywa się ze światem żadnego prawa S-0, 5 praw walidacyjnych LMM ani 120 praw deweloperskich, ani z innym prawem zbioru:
lewa alternat. x(xy)=(xx)y; (x(zx)) = (xx)y; ((xy)y) = (y(zz)); z((xy)x) = zy; x(xx) = x; (yy)(xy) = yy; (xz)y = (yx)y; xx = x(xx).
(Prawa alternat. odpadła jako dualna do lewej; unipotentna jako pokrywająca się ze światem deweloperskim.)

## 4. Przebieg

Światy T1 (rząd 3) i T1-4 (U4), protokół S-1b (dzień 1 do 300, sen 50), **ziarna 1820–1879** (60, nowe).
Ramiona: losowa, heurystyka, heur_grafu, heur_grafu_wsp, wyrocznia_pokrycia. 4 800 przebiegów, jedno uruchomienie.

## 5. Kryteria (rozstrzygające)

M1, bootstrap sparowany 95%. W każdym świecie, tylko prawa ważne (niepusta pula 1. snu w ≥ 90% ziaren), n = ich liczba:
- **nieinformatywny**, gdy n < 4 albo bramka (wyrocznia_pokrycia − heur_grafu, dolna CI > 0) w mniej niż 60% n;
- **lepsza**: dolna CI(heur_grafu_wsp − heur_grafu) > 0 w ≥ 60% n; **gorsza**: górna CI < 0 w ≥ 60% n; inaczej **nierozstrzygnięta**.

**Werdykt główny (T1-4):** lepsza → WYNIK; gorsza → WYNIK NEGATYWNY; nierozstrzygnięta → WYNIK NEGATYWNY (brak przewagi); nieinformatywny → NIEINFORMATYWNY.
**T1 (wtórnie):** raportowana kategoria; „gorsza” = wariant szkodzi w rzędzie 3 (WYNIK NEGATYWNY dla rzędu 3).
Skutek: WYNIK w T1-4 i T1 nie „gorsza” → propozycja (do decyzji Michała), by wariant zastąpił domyślną intuicję. Inaczej domyślna zostaje bez zmian.

Zawsze raportujemy: stałe okno [d1, d1 + 50], pokrycie końcowe, heur_grafu − heurystyka (replikacja poprzedniego wyniku na nowych prawach), ułamek luki (bez CI; wyrocznia jest zachłanna, nie optimum).

## 6. Ziarna

Zużyte: 1780 (demonstracja prototypu), 1800–1819 (dewelopment), 1820–1879 (ta walidacja). Recenzent: 1880–1899.

## 7. Kontrola jakości

`pytest`; niezależny recenzent przed zamrożeniem i po wyniku; raport z pustym `git diff` rdzen/ między zamrożeniem a commitem w JSON.
