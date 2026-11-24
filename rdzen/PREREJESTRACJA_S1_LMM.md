# Prerejestracja S-1 LMM: czy intuicja LMM wybiera lepiej niż heurystyka?

Status: **projekt do zamrożenia** (24.11). Poprawka zapowiedziana w sekcji 7 `PREREJESTRACJA_S1.md`, w protokole S-1b (`PREREJESTRACJA_S1B.md`).
Zamrożenie = commit tego pliku z kodem i wagami przed pierwszym `python -m matylda_rdzen.s1lmm`. Runner odmawia przy brudnym drzewie,
istniejących wynikach, złym hashu U4 lub wag; zapisuje commit, sha256 tego pliku, wag i kodu.

## 1. Pytanie i hipotezy

S-1b: heurystyka ogólności bije los, ale daje 1/5–1/3 efektu idealnego wyboru, a wśród śmiałych przeczuć jest losem z konstrukcji.
Pytanie: czy LMM, czytający tokeny zależności (graf wiedzy), wybiera lepiej niż heurystyka?

- **H-bramka:** jest luka do zamknięcia: wyrocznia pokrycia − heurystyka > 0.
- **H-LMM (główna):** LMM − heurystyka > 0, w T1 i T1-4.
Poziom: HIPOTEZA.

## 2. Model (zamrożony)

| Element | Wartość |
|---|---|
| Koder | architektura LMM: `bsd2.PosetEncoder` wariant B (d = 64, L = 4, 4 głowice) + `MRPHead`; kopia bez zmian z mdrewnisz/LMM@39bd217 (`lmm_bsd2_models.py`, sha256 treści sprawdza test) |
| Wejście | macierz zależności między klasami pojęć (z konsolidacji), znane wykluczenia (obalone w obu kierunkach), pary ukryte |
| Cechy węzła | częstość pojęcia na znanych magmach, rozmiar klasy, **typ pojęcia** (prawo / własność strukturalna / literał / ⊤); **bez nazw pojęć** |
| Cechy kandydatury | wsparcie / liczba znanych magm, czy śmiałe, czy odwrotny kierunek obalony |
| Ocena | głowica na stanach węzłów, logicie MRP i cechach kandydatury |
| Wagi | `dane/lmm_intuicja_v1.pt`, sha256 `0b7eef57b850e209ee3372374fc93f43685423224eb4755bc1f34c81fccaf438`, uczone **tutaj od zera** (wagi z Asusa niedostępne) |
| Inferencja | CPU, float32, 1 wątek, deterministyczna (test); torch 2.15.0 |

Zastrzeżenie: to **architektura** LMM uczona na naszych danych, nie wytrenowany LMM z V0/V1/V2. Cechy węzła i kandydatury wykraczają poza czysty koder posetów.

## 3. Dane treningowe i wybór modelu (jawnie)

- Tylko światy praw spoza S-0 (test `test_lmm_trening_bez_praw_s0`): 54 światy (`lmm_trening.swiaty_v1`): unipotentna, lewa i prawa alternatywność,
  półsymetryczność, 7 własności strukturalnych i koniunkcje (prawo ∧ własność, prawo ∧ prawo), rząd 3 i 4, ≥ 20 magm i |TR| ≥ 15. Żaden człon nie jest prawem S-0.
  Uwaga: U4 zawiera magmy próbkowane pod prawa S-0; światy treningowe w rzędzie 4 to ich podzbiory spełniające inne prawa.
- Migawki: pętla S z budżetami S-1b, ramiona losowa i heurystyka, ziarna 1100–1139; 19 786 migawek. Etykieta kandydatury: 1 prawdziwa i na TR, 0,5 prawdziwa poza TR, 0 fałszywa.
- Trening: BCE, Adam 1e-3, 8 epok, ziarno 2024 (`wyniki/lmm_trening_v1.json`).
- **Wybór modelu:** v0 (7 światów) przegrywał z heurystyką na 2 z 5 praw walidacyjnych (małe światy). v1 dodał światy strukturalne i koniunkcje.
  Walidacja w pętli v1 (prawa analizy mocy, ziarna 1300–1339, `wyniki/lmm_walidacja_w_petli_v1.json`): LMM − heurystyka dolna CI > 0 w 4/5 praw w T1 i w T1-4;
  (yx)x=y w T1 istotnie gorzej (−0,74). Prawa walidacyjne posłużyły do wyboru v1, więc **nie są już niezależnym testem**. Testem są prawa S-0 na ziarnach 600–679.
- Ocena offline (AUC) w JSON treningu liczyła remisy źle (AUC heurystyki zaniżone; poprawione w kodzie po treningu). Nie używamy jej do wniosków.

## 4. Przebieg

Protokół S-1b bez zmian (dzień 1 do 300, sen 50, światy T1 i T1-4, prawa `PRAWA_S0`, warunek ważności ≥ 90% ziaren z niepustą pulą snu).
Ramiona: losowa, heurystyka, **lmm**, wyrocznia_pokrycia, wyrocznia_trafnosci. **Ziarna 600–679** (zarezerwowane, nieużywane). 4 000 przebiegów.

## 5. Kryteria (rozstrzygające)

Miara: M1 (pole pod krzywą pokrycia po dniu 1, b = min wywołań), bootstrap sparowany 95%. Dla każdego świata, tylko prawa ważne:
1. **Bramka:** wyrocznia_pokrycia − heurystyka, dolna CI > 0 w ≥ 3/5 praw.
2. Próg per prawo: τ_H = 0,25 × (wyrocznia_pokrycia − heurystyka)_H (zalecenie recenzji S-1b: per prawo, nie średnią).
3. Kategoria LMM: **lepsza**, gdy dolna CI(LMM − heurystyka) > 0 w ≥ 3/5 praw; inaczej **pomijalna**, gdy górna CI < τ_H w ≥ 3/5; inaczej **nierozstrzygnięta**.

Werdykt: bramka nie przeszła → NIEINFORMATYWNY; „lepsza” w obu światach → **WYNIK**; „pomijalna” w którymś → **WYNIK NEGATYWNY**; inaczej NIEROZSTRZYGNIĘTY.
Zawsze raportujemy: prawa z LMM istotnie gorszą od heurystyki, LMM − los, ułamek luki (LMM − heur) / (wyrocznia − heur), kontrasty na stałym oknie [d1, d1 + 50],
M2 dla śmiałych i powtórki. Pozostałe analizy są eksploracyjne.

## 6. Kontrola jakości

`pytest` (w tym: zgodność kopii kodera, determinizm LMM w pętli, brak praw S-0 w treningu); niezależny recenzent przed zamrożeniem i po wynikach.
