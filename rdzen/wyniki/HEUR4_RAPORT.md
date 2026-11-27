# Rząd 4: heurystyka grafu ze wsparciem — raport (27.11)

Prerejestracja `PREREJESTRACJA_HEUR4.md` zamrożona w f30184c po recenzji przed (`wyniki/HEUR4_RECENZJA_PRZED.md`, poprawki B1–B5).
Przebieg: 5 nowych praw, ziarna 1820–1879, `wyniki/heur4_walidacja.json` (078ede0); `git diff` rdzen/ między zamrożeniem a commitem w JSON pusty.
Recenzja wyniku: `wyniki/HEUR4_RECENZJA_PO.md`.

## Werdykt (wg §5)

**NIEINFORMATYWNY w rzędzie 4** (bramka 1/5); T1: nierozstrzygnięta. Wariant ze wsparciem nie zastępuje heurystyki grafu; domyślna intuicja bez zmian.
Wariant − heur_grafu: T1-4 lepszy w 2/5 praw, gorszy w 1/5 (−0,06), reszta ≈ 0; T1 lepszy w 1/5.

## Ważniejsze ustalenie: „wyrocznia pokrycia” nie jest sufitem

Bramka nie przeszła, bo heurystyka grafu jest **istotnie lepsza od wyroczni pokrycia** w 4/5 praw T1-4 i 2/5 T1 (do −6,9).
Recenzja wyjaśniła mechanizm (WYNIK): wyrocznia stawia najwyżej każdą prawdziwą krawędź, której para klas świata leży na TR, ale pokrycie liczy się na
reprezentantach klas, więc krawędź między nie-reprezentantami nic nie daje, dopóki badacz nie zna równoważności. 41–54% sprawdzeń wyroczni we śnie
daje zerowy przyrost pokrycia (heurystyka grafu: ok. 10%).

Skutki dla wcześniejszych raportów (WNIOSKOWANIE recenzji):
- **Bramki** S-1b, S-0 heurystyki i LMM v3 nadal stoją (tam wyrocznia − porównywane ramię było istotnie > 0).
- **Podważone:** wszystkie „ułamki luki do wyroczni” i „% efektu wyroczni”; teza z LMM v3 o niskim suficie trafności; pomysł, by LMM imitował tę wyrocznię.
- Lepszy kandydat na sufit (diagnostyka nieprerejestrowana, ziarna 1886–1899): zachłanna wyrocznia **przyrostu pokrycia TR** bije heurystykę grafu
  w 10/10 komórek walidacyjnych (+1,0 do +9,0) i 20/20 światów deweloperskich. Miejsca na poprawę jest więc dużo (HIPOTEZA co do skali).

## Opisowo

Heurystyka grafu − stara heurystyka > 0 we wszystkich 10 komórkach (5 nowych praw × 2 światy, np. +7,9, +6,9): replikacja kierunku na nowych prawach,
nie kryterium i nie 10 niezależnych replikacji.

## Co dalej (propozycje)

1. Zamrozić nową wyrocznię (przyrost pokrycia TR) jako bramkę przed kolejną prerejestracją.
2. Heurystyka „przyrostu pokrycia na znanym porządku” (bez prawdy świata) jako kandydat na następną intuicję.
3. Jeśli kiedyś wróci LMM: cel = przyrost pokrycia, nie imitacja starej wyroczni.

Zużyte ziarna: 1780, 1800–1819, 1820–1879, 1880–1899.
