# Prerejestracja S-0b: silniejsza kontrola i trudniejszy świat

Status: **EKSPLORACYJNE**, zamrożone przed pierwszym uruchomieniem ramion S-0b na prawach S-0.
Kontekst: wynik S-0 i jego krytyka (`wyniki/S0_KRYTYKA_I_DEFLACJA.md`); decyzja Michała 23.11: „najpierw S-0b”.

## Przed uruchomieniem sprawdzono tylko

1. Testy prototypu (13/13), w tym regresja czuwania względem KG-0b po uogólnieniu kodu pojęć na dowolny rząd.
2. Statystyki światów (bez ramion): |W_H|, |E|, |TR|, |TR podłożonych|, odsetek prawdziwych par.
   Rząd 4: |W_H| = 1024–1880, |TR| = 16–30, odsetek prawdziwych par 0,10–0,27 (rząd 3: 0,16–0,31).
3. Test dymny ramion S-0b na prawie spoza S-0 („lewa samodystr.” w rzędzie 3, „elastyczna” w rzędzie 4), ziarno 99, B = 60.

## Co się zmienia względem S-0

**Silniejsza kontrola W+S.** Ten sam generator co S (konsolidacja, wsparcie ≥ 2 i śmiałe przeczucia ze wsparciem 1,
przycinanie, ta sama intuicja), ale zamiast powtórki zapamiętanych kontrprzykładów dostaje tyle samo świeżych,
losowych magm ze świata. Różnica S − W+S izoluje wartość **powtórki własnych porażek**.

**Rozdzielenie śmiałości.** S−Ś = S bez śmiałych przeczuć.

**Trudniejszy świat.** Magmy rzędu 4 z zamrożonego uniwersum U4 (`dane/u4.npy`, 7 000 magm, sha256
`dca6e9968ef62587d7e2c4f274771753da81800a635a71b9c9e5fbc275001e37`): do 1 000 magm na każde prawo S-0
z próbnika z nawrotami (próbka niejednostajna) + 2 000 magm jednostajnie losowych. Świat W_H = magmy z U4 spełniające H.

## Ramiona

A2, W+, **W+S**, S-los, S, **S−Ś**. Stałe jak w S-0: okno 20, MIN_SUPPORT 2, do 50 kontrprzykładów na wywołanie,
10 kandydatur na sen, intuicja `HeurystykaOgolnosci`, ziarna 0–19, B ∈ {25, 50, 100}. Rzędy 3 i 4.

## Kryteria (dolna granica 95% CI bootstrap sparowanej różnicy > 0 w ≥ 3 z 5 praw)

| Id | Pytanie | Rząd | B | Kontrast |
|---|---|---|---|---|
| **G1** | Replikacja S-0 w trudniejszym świecie | 4 | 50 | S − W+ |
| **G2** | Czy wartość snu bierze się z powtórki porażek, a nie z samego generatora? | 4 | 50 | S − W+S |
| P1 | G2 w rzędzie 3 | 3 | 50 | S − W+S |
| P2 | Czy sam generator snu na świeżych danych bije zwykły dzień? | 4 | 50 | W+S − W+ |
| P3 | Czy śmiałe przeczucia pomagają? | 4 | 50 | S − S−Ś |
| P4 | Czy sen podnosi sufit ponad losowy przegląd? | 4 | 100 | S − S-los |

## Interpretacja z góry

- G1 TAK, G2 TAK: powtórka własnych porażek ma wartość ponad tyle samo świeżych epizodów; „sen” w sensie powtórki jest uzasadniony w tym świecie.
- G1 TAK, G2 NIE: zysk z S-0 pochodził z generatora (konsolidacja, śmiałość), nie z powtórki. Sen redukuje się do „lepszego proponującego”, co nadal jest wynikiem, ale nie o powtórce.
- G1 NIE: wynik S-0 nie replikuje się w rzędzie 4; S-0 był artefaktem łatwego świata.
- P4 NIE: sen nie podnosi sufitu ostatecznego (jak w S-0); wolno mówić tylko o wydajności przy umiarkowanym budżecie.

## Deflacja z góry

Wynik dotyczy U4 (próbka niejednostajna), tego słownika i tej heurystyki. Nie jest twierdzeniem o intuicji ani o śnie w ogóle.
Konstruktor jest też analitykiem: wynik przechodzi niezależną recenzję (osobny agent bez kontekstu konstrukcji) przed wpisem do dokumentów jako WYNIK.
