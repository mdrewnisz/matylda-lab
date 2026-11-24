# Plan: heurystyka grafu zależności (po odłożeniu LMM)

Status: **zapisany przed walidacją** (24.11). Decyzja Michała: zatrzymać LMM, wzmocnić heurystykę.

## 1. Reguła (zamrożona)

`heurystyki.HeurystykaGrafu("oa+ob+kara")`: ocena kandydatury a ⇒ b = out(a) + out(b) − 3·[śmiałe] (+ 0,001·wsparcie/n na remisy),
gdzie out(x) = liczba klas, które wiadomo, że wynikają z klasy x (tokeny zależności po konsolidacji). Z kandydatur o tej samej parze klas liczy się tylko najlepsza.
Bez uczenia. Intuicja (HIPOTEZA): krawędzie redukcji przechodniej prowadzą do klas „niskich”, z których już dużo wynika.

## 2. Jak wybrana (jawnie, cała eksploracja)

Wyłącznie na światach deweloperskich: losowe prawa z `dane/swiaty_v3.json` (uniwersa 3T/4T, bez magm praw S-0 i walidacyjnych). Praw walidacyjnych nie używano.
- Odrzucone: sama deduplikacja (≈ 0), kwota śmiałych wg częstości (średnio gorsza) — `heur_dev --plus`, ziarna 1600–1609.
- Analiza cech na pulach snu (ziarna 1610–1613): out(b) i out(a) najlepiej przewidują krawędź TR (AUC 0,65–0,73 wśród śmiałych).
- 5 wzorów, 120 światów, ziarna 1600–1609 (`wyniki/heur_dev_grafu.json`); 2 najlepsze potwierdzone na **203 innych światach i ziarnach 1620–1629**
  (`wyniki/heur_dev_potw.json`): „oa+ob+kara” − heurystyka = **+0,45 luki do wyroczni w 4T** (mediana +0,32, 58% światów > 0), **+0,07 w 3T** (mediana ≈ 0).

## 3. Walidacja

5 praw spoza S-0 (`PRAWA_MOCY`), światy T1 i T1-4, protokół S-1b, **ziarna 1640–1679** (nowe). Ramiona: losowa, heurystyka, heur_grafu, wyrocznia_pokrycia.
`python -m matylda_rdzen.heur_walidacja`, jedno uruchomienie. Uwaga: te prawa były oglądane przy LMM v0–v3 (przez badacza, nie przy wyborze tej reguły).

## 4. Kryteria (rozstrzygające)

Miara M1, bootstrap sparowany 95%, tylko prawa ważne.
- **Główne (T1-4):** heur_grafu − heurystyka, dolna CI > 0 w ≥ 3/5 praw → **WYNIK** (lepsza w rzędzie 4); inaczej **WYNIK NEGATYWNY**.
- **T1 (oczekiwane ≈ 0, z dewelopmentu):** górna CI < 0 w ≥ 3/5 → WYNIK NEGATYWNY dla rzędu 3 (szkodzi); dolna > 0 w ≥ 3/5 → lepsza; inaczej bez rozstrzygnięcia.
Raportujemy zawsze: ułamek luki per prawo, heur_grafu − los.

## 5. Ziarna

Zużyte: 1600–1613, 1620–1629 (dewelopment), 1640–1679 (walidacja). 600–679 nadal nieużyte.
