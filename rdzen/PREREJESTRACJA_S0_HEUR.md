# Prerejestracja: heurystyka grafu na prawach S-0

Status: **ZAMROŻONA** (26.11), po recenzji przed zamrożeniem (`wyniki/S0_HEUR_RECENZJA_PRZED.md`, poprawki B1–B5 wprowadzone). Decyzja Michała (24.11): test na S-0 z prerejestracją.
Zamrożenie = commit tego pliku z `s0_heur.HEUR_SHA` = sha256 `heurystyki.py` przed pierwszym `python -m matylda_rdzen.s0_heur`.
Runner odmawia przy brudnym drzewie, istniejącym wyniku, złym hashu U4 lub zmienionej regule; zapisuje commit i sha256 tego pliku oraz kodu.

## 1. Pytanie i hipoteza

Czy reguła zwalidowana na 5 prawach spoza S-0 (`wyniki/HEUR_GRAFU_RAPORT.md`) uogólnia się na prawa S-0?
**H (HIPOTEZA):** heurystyka grafu − dotychczasowa heurystyka > 0 (miara M1) na prawach S-0 w T1 i T1-4.

## 2. Reguła (zamrożona, bez zmian od walidacji)

`HeurystykaGrafu("oa+ob+kara")`: out(a) + out(b) − 3·[śmiałe] (+ 0,001·wsparcie/n), deduplikacja par klas.
Plik `matylda_rdzen/heurystyki.py`, sha256 `bbbf3a71c2da07d94391a35c8f865ba0c99f12d53f60e7510d0075bca5ed8931` (niezmieniony od commitu walidacji 459a097).

## 3. Przebieg

Prawa `PRAWA_S0` (idempotentna, komutatywna, x(xy)=y, łączna, medialna); światy T1 (rząd 3) i T1-4 (U4, sha256 `dca6e996…`).
Protokół S-1b: dzień 1 do 300 wywołań, sen 50, k = 10, słownik literałów, cex_cap 1. **Ziarna 600–679** (80, zarezerwowane, dotąd nieużyte).
Ramiona: losowa, heurystyka (`HeurystykaOgolnosci`), heur_grafu, wyrocznia_pokrycia. Czuwanie 1 wspólne (sprawdzane asercją). 3 200 przebiegów, jedno uruchomienie.

## 4. Kryteria (rozstrzygające)

Miara M1 = pole pod krzywą pokrycia TR od końca dnia 1 do b = min wywołań; bootstrap sparowany 95% (10 000, ziarno 12345).
Dla każdego świata osobno, tylko prawa ważne (niepusta pula 1. snu w ≥ 90% ziaren):
1. **Bramka:** wyrocznia_pokrycia − heurystyka, dolna CI > 0 w ≥ 3/5 praw; inaczej świat **nieinformatywny** (także gdy < 3 praw ważnych).
2. **lepsza:** dolna CI(heur_grafu − heurystyka) > 0 w ≥ 3/5 praw; **gorsza:** górna CI < 0 w ≥ 3/5; inaczej **nierozstrzygnięta**.

Werdykt: „lepsza” w obu światach → **WYNIK**; „gorsza” w którymś → **WYNIK NEGATYWNY**; „lepsza” w jednym, a drugi nierozstrzygnięty lub nieinformatywny →
**WYNIK CZĘŚCIOWY**; oba nieinformatywne → NIEINFORMATYWNY; inaczej → WYNIK NEGATYWNY (brak przewagi).

Pełna tabela (T1 × T1-4; L = lepsza, G = gorsza, N = nierozstrzygnięta, X = nieinformatywny; „lepsza” i „gorsza” naraz w jednym świecie są niemożliwe):

| T1 \ T1-4 | L | G | N | X |
|---|---|---|---|---|
| **L** | WYNIK | WYNIK NEGATYWNY | CZĘŚCIOWY | CZĘŚCIOWY |
| **G** | WYNIK NEGATYWNY | WYNIK NEGATYWNY | WYNIK NEGATYWNY | WYNIK NEGATYWNY |
| **N** | CZĘŚCIOWY | WYNIK NEGATYWNY | NEGATYWNY (brak przewagi) | NEGATYWNY (brak przewagi) |
| **X** | CZĘŚCIOWY | WYNIK NEGATYWNY | NEGATYWNY (brak przewagi) | NIEINFORMATYWNY |

**Zastrzeżenie (dualność):** świat x(xy)=y w T1 jest transpozycją świata walidacyjnego (yx)x=y (magmy z odwróconym działaniem),
więc w T1 test uogólnienia opiera się realnie na 4 nowych prawach. Raport poda wynik także bez x(xy)=y (opisowo; kryterium bez zmian).

## 5. Raportowane zawsze (opisowo)

Per prawo: kontrast na stałym oknie [d1, d1 + 50] i różnica pokrycia końcowego (zalecenie recenzji: zysk może być samym tempem);
prawa z heur_grafu istotnie gorszą; heur_grafu − los; ułamek luki (bez CI). Wszystko inne jest eksploracyjne.

## 6. Ziarna

Ten test **zużywa 600–679** (wcześniej zarezerwowane dla testu LMM na S-0; LMM odłożony decyzją Michała 24.11, `s1lmm.SEEDS` wyłączone).
Zużyte przy przygotowaniu: 1720–1723 (test dymny runnera), 1724–1739 (recenzja przed zamrożeniem), zawsze na prawach spoza S-0.

## 7. Kontrola jakości

`pytest`; niezależny recenzent przed zamrożeniem (`wyniki/S0_HEUR_RECENZJA_PRZED.md`) i po wyniku. Raport po wyniku pokaże pusty `git diff` rdzen/ między commitem zamrożenia a commitem zapisanym w JSON wyniku. Test dymny runnera na prawach spoza S-0, ziarna 1720–1723.
