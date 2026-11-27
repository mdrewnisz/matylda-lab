# S-0: wynik (generowany automatycznie przez matylda_rdzen.s0)

Prerejestracja sha256: `f70e76f3d625d64203010f9e273bcc1b851b65b9505adbacf1869e03238debd9`

## Werdykt wg prerejestracji

- **H-sen (S > W+ przy B=50, >=3 z 5 praw)**: NIE OBALONA (wsparta w tym świecie)
- **prawa z dolną granicą CI > 0 (S-W+)**: ['idempotentna', 'komutatywna', 'x(xy)=y', 'łączna', 'medialna']
- **konsolidacja potrzebna (S > S-K)**: True
- **sen lepszy od szumu (S > S-los)**: True

## Średnie pokrycie redukcji przechodniej (20 ziaren)

| Prawo | |TR| | B | A2 | W+ | S-los | S | S-K |
|---|---|---|---|---|---|---|---|
| idempotentna | 28 | 25 | 7.0 | 11.7 | 9.3 | 11.8 | 10.7 |
| idempotentna | 28 | 50 | 7.0 | 12.3 | 15.8 | 20.1 | 17.1 |
| idempotentna | 28 | 100 | 7.0 | 12.3 | 28.0 | 21.2 | 22.1 |
| komutatywna | 19 | 25 | 6.3 | 7.3 | 7.2 | 8.4 | 7.4 |
| komutatywna | 19 | 50 | 7.1 | 10.0 | 12.6 | 15.9 | 12.2 |
| komutatywna | 19 | 100 | 7.1 | 10.0 | 19.0 | 16.5 | 16.2 |
| x(xy)=y | 21 | 25 | 11.8 | 12.6 | 12.1 | 13.1 | 12.2 |
| x(xy)=y | 21 | 50 | 12.4 | 13.3 | 14.9 | 19.9 | 16.9 |
| x(xy)=y | 21 | 100 | 12.4 | 13.3 | 21.0 | 20.2 | 20.2 |
| łączna | 30 | 25 | 9.8 | 9.8 | 9.9 | 9.9 | 9.8 |
| łączna | 30 | 50 | 12.2 | 14.4 | 17.9 | 21.0 | 12.2 |
| łączna | 30 | 100 | 12.2 | 14.4 | 29.9 | 24.9 | 18.9 |
| medialna | 47 | 25 | 14.8 | 18.6 | 16.5 | 18.3 | 17.4 |
| medialna | 47 | 50 | 14.9 | 23.2 | 31.9 | 28.4 | 27.2 |
| medialna | 47 | 100 | 14.9 | 23.2 | 40.0 | 28.8 | 28.8 |

## Kontrasty sparowane przy B = 50: średnia [95% CI bootstrap]

| Prawo | S−W+ | S−S-K | S−S-los | S−A2 | W+−A2 |
|---|---|---|---|---|---|
| idempotentna | +7.85 [+5.30, +10.75] | +3.00 [+1.75, +4.20] | +4.35 [+1.80, +6.80] | +13.10 [+10.30, +15.75] | +5.25 [+3.25, +7.30] |
| komutatywna | +5.95 [+3.60, +8.45] | +3.80 [+2.85, +4.75] | +3.40 [+1.80, +4.90] | +8.85 [+6.75, +10.95] | +2.90 [+1.40, +4.60] |
| x(xy)=y | +6.60 [+5.25, +7.90] | +3.05 [+2.25, +3.85] | +5.00 [+3.90, +6.05] | +7.50 [+6.15, +8.80] | +0.90 [+0.25, +1.70] |
| łączna | +6.60 [+4.35, +8.90] | +8.80 [+6.95, +10.55] | +3.15 [+1.35, +4.70] | +8.80 [+6.95, +10.55] | +2.20 [+0.75, +3.90] |
| medialna | +5.20 [+3.00, +7.60] | +1.15 [+0.40, +2.15] | -3.55 [-5.70, -1.45] | +13.50 [+12.00, +14.90] | +8.30 [+6.20, +10.35] |

## Trafność intuicji ze snu (odsetek kandydatur ze snu, które przetrwały weryfikator)

| Prawo | S | S-K | S-los |
|---|---|---|---|
| idempotentna | 526/615 (86%) | 1038/1127 (92%) | 1143/1285 (89%) |
| komutatywna | 517/571 (91%) | 1140/1195 (95%) | 995/1073 (93%) |
| x(xy)=y | 470/483 (97%) | 1296/1309 (99%) | 945/1045 (90%) |
| łączna | 530/548 (97%) | 1364/1382 (99%) | 855/960 (89%) |
| medialna | 392/418 (94%) | 535/561 (95%) | 685/790 (87%) |

## Pokrycie krawędzi podłożonych przy B = 50 (średnio)

| Prawo | |TR podł.| | A2 | W+ | S-los | S | S-K |
|---|---|---|---|---|---|---|
| idempotentna | 14 | 4.2 | 7.5 | 8.5 | 11.9 | 10.8 |
| komutatywna | 8 | 3.1 | 4.3 | 6.0 | 7.7 | 6.5 |
| x(xy)=y | 18 | 10.0 | 10.8 | 12.4 | 16.9 | 13.9 |
| łączna | 20 | 10.2 | 11.0 | 13.2 | 16.6 | 10.2 |
| medialna | 5 | 3.5 | 4.9 | 4.5 | 5.0 | 5.0 |
