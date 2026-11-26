# Heurystyka grafu na prawach S-0: raport (26.11)

Prerejestracja `PREREJESTRACJA_S0_HEUR.md` zamrożona w 1183968 po recenzji przed zamrożeniem (`wyniki/S0_HEUR_RECENZJA_PRZED.md`, poprawki B1–B5).
Przebieg: ziarna 600–679, 3 200 przebiegów, `wyniki/s0_heur_wyniki.json` (7c53e43). `git diff` rdzen/ między commitem zamrożenia a commitem w JSON: pusty.
Recenzja wyniku z replikacją na ziarnach 1740–1779: `wyniki/S0_HEUR_RECENZJA_PO.md`.

## Werdykt (wg §4)

**WYNIK: heurystyka grafu lepsza od dotychczasowej heurystyki na prawach S-0 w obu światach.** Wszystkie 10 komórek ważnych, bramka 5/5 w obu światach.

| Świat | prawo | grafu − heur, M1 [95% CI] | stałe okno | pokrycie końcowe |
|---|---|---|---|---|
| T1 | idempotentna | +2,32 [2,01; 2,66] | +2,17 | +3,02 |
| T1 | komutatywna | +2,44 [2,20; 2,67] | +1,88 | +0,46 |
| T1 | x(xy)=y | +1,50 [1,23; 1,78] | +1,00 | +0,01 |
| T1 | łączna | +4,12 [3,93; 4,32] | +4,68 | +5,74 |
| T1 | medialna | +1,34 [1,10; 1,58] | +0,74 | +0,04 |
| T1-4 | idempotentna | −0,09 [−0,26; 0,07] | +0,05 | +0,42 |
| T1-4 | komutatywna | +0,87 [0,70; 1,03] | +0,15 | **−0,65** |
| T1-4 | x(xy)=y | +1,03 [0,81; 1,27] | +0,96 | +0,57 |
| T1-4 | łączna | **−0,97 [−1,28; −0,67]** | −0,54 | +1,02 |
| T1-4 | medialna | +0,66 [0,51; 0,80] | +0,35 | 0,00 |

## Ocena (po recenzji)

| Ustalenie | Status |
|---|---|
| Rząd 3 (T1): przewaga 5/5, także na stałym oknie i bez prawa x(xy)=y (dualnego do walidacyjnego (yx)x=y); replikacja 5/5 | **WYNIK, odporny** |
| Rząd 4 (T1-4): kryterium spełnione dokładnie 3/5; bez któregokolwiek z trzech praw albo na stałym oknie → nierozstrzygnięte; replikacja daje te same 3 prawa | **WYNIK, kruchy** (zależny od doboru praw) |
| Część zysku to samo tempo (pokrycie końcowe równe w T1 x(xy)=y i medialnej) | WYNIK |
| Łączna w T1-4: wolniej, ale wyżej na końcu; komutatywna w T1-4: szybciej, ale niżej na końcu | WYNIK; przyczyna — HIPOTEZA |
| Ułamek luki > 1 w T1 jest prawdziwy: wyrocznia pokrycia jest zachłanna (najpierw krawędzie TR), nie jest optimum | WYNIK; ułamka nie czytać jako „% do optimum” |
| Heurystyka grafu nigdzie nie jest gorsza od losowej | WYNIK |

## Wniosek dla programu

Heurystyka grafu jest pierwszą intuicją, która przeszła walidację i prerejestrowany test na S-0. W rzędzie 3 przewaga jest wyraźna i stabilna,
w rzędzie 4 jest na granicy kryterium i zależy od prawa. Rekomendacja recenzji: przyjąć jako domyślną intuicję rdzenia z zastrzeżeniem dla rzędu 4.
Otwarte: słabość w łącznej i x(xy)=xy (rząd 4), niższe pokrycie końcowe w komutatywnej, zachowanie w protokole wielodniowym.

Ziarna zużyte: 600–679 (ten test), 1720–1739 (przygotowanie), 1740–1779 (recenzja po).
