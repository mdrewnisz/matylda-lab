# Heurystyka grafu zależności: raport (24.11)
> **Erratum (27.11, `wyniki/HEUR4_RAPORT.md`):** wyrocznia pokrycia nie jest sufitem (40–50% jej sprawdzeń nic nie wnosi). Bramki stoją, ale „ułamki luki do wyroczni” i wnioski o „suficie” są nieważne.

Decyzja Michała po LMM v3: zatrzymać LMM, wzmocnić heurystykę. Plan z kryterium przed walidacją: `PLAN_HEURYSTYKA_GRAFU.md` (459a097).
Walidacja: `wyniki/heur_grafu_walidacja.json` (b9d7ef6). Niezależna recenzja z replikacją na ziarnach 1680–1719: `wyniki/HEUR_GRAFU_RECENZJA.md`.

## Reguła

Ocena kandydatury a ⇒ b = out(a) + out(b) − 3·[śmiałe]; out(x) = ile klas wiadomo, że wynika z x (tokeny zależności). Bez uczenia.

## Werdykt (wg sekcji 4 planu)

**WYNIK: lepsza od dotychczasowej heurystyki w rzędzie 4** (T1-4: dolna CI > 0 w 4/5 praw) **i w rzędzie 3** (T1: 5/5). Replikacja recenzenta: to samo.
Wyjątek: x(xy)=xy w T1-4 istotnie gorsza w tempie (−1,04 [−1,52; −0,57]), choć pokrycie końcowe wyższe.

| Świat | prawo | grafu − heur [95% CI] | ułamek luki do wyroczni |
|---|---|---|---|
| T1 | elastyczna | +1,02 [0,70; 1,32] | 0,19 |
| T1 | lewa samodystr. | +2,83 [2,28; 3,39] | 0,64 |
| T1 | prawa samodystr. | +2,85 [2,44; 3,27] | 0,60 |
| T1 | x(xy)=xy | +1,17 [0,83; 1,51] | 0,29 |
| T1 | (yx)x=y | +1,73 [1,32; 2,18] | 1,0 (szum; replikacja 0,73) |
| T1-4 | elastyczna | +0,17 [0,01; 0,32] | 0,08 (kruche) |
| T1-4 | lewa samodystr. | +1,59 [1,35; 1,81] | 0,52 |
| T1-4 | prawa samodystr. | +4,18 [3,78; 4,57] | 0,38 |
| T1-4 | x(xy)=xy | −1,04 [−1,52; −0,57] | −0,14 |
| T1-4 | (yx)x=y | +0,60 [0,39; 0,83] | 0,77 |

## Ustalenia recenzji

| Ustalenie | Status |
|---|---|
| Sygnał niesie out(b) (krawędź TR prowadzi do „niskiej” klasy, z której już dużo wynika); out(a) ≈ 0; deduplikacja nic nie zmienia; odwrócona reguła szkodzi wszędzie | WYNIK (ablacje) |
| W 4–5 z 10 światów pokrycie końcowe jak u heurystyki: zysk to głównie tempo | WYNIK |
| Dewelopment w 3T przewidywał ≈ 0, bo tam węzły-prawa są prawie martwe (3,7 żywych vs 19–23 w T1) i luka do wyroczni mała | WYNIK + WNIOSKOWANIE |
| Słabość w x(xy)=xy T1-4: reguła pomija wsparcie, budzi tylko 33% prawdziwych kandydatur | HIPOTEZA |
| Uogólnienie na S-0 | niesprawdzone |

## Rekomendacja

Przyjąć jako domyślną intuicję rdzenia jawnie (`HeurystykaOgolnosci` zostaje linią bazową, nazwaną). Ogólne twierdzenie dopiero po
prerejestrowanym teście na S-0 (ziarna 600–679, protokół S-1b, ramiona: losowa, heurystyka, heur_grafu, wyrocznia_pokrycia, reguła zamrożona,
kryterium ≥ 3/5 praw w każdym świecie, obowiązkowo stałe okno i pokrycie końcowe).

Zużyte ziarna: 1600–1613, 1620–1629, 1640–1679, 1680–1719 (recenzja). 600–679 nadal nieużyte.
