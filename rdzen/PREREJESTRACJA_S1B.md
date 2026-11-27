# Prerejestracja S-1b: S-1 z osobnym budżetem snu

Status: **zamrożona** (24.11), po niezależnej recenzji przed uruchomieniem (`wyniki/S1B_RECENZJA_PRZED.md`). Zamrożenie = commit tego pliku z kodem przed pierwszym `python -m matylda_rdzen.s1b`.
Runner odmawia przy niezacommitowanych zmianach w `rdzen/`, istniejących wynikach lub złym hashu U4; zapisuje commit, sha256 tego pliku i kodu.

## 0. Dlaczego S-1b i co zmieniono po obejrzeniu S-1 (jawnie)

S-1 (`wyniki/S1_RAPORT.md`) dał werdykt NIEINFORMATYWNY: w T1-4 przy wspólnym budżecie 100 dzień 1 zużywał cały budżet w 3 z 5 praw
(95–100% przebiegów), więc sen się nie odbywał, a bramka nie mogła przejść. Werdykt S-1 zostaje bez zmian.

Po obejrzeniu S-1 zmieniamy **tylko budżet** i dodajemy warunek ważności. Diagnoza opiera się na zużyciu budżetu (M3), nie na kontrastach ramion.
Zastrzeżenia (jawnie):
- Recenzent S-1 eksploracyjnie widział już efekty wyroczni i heurystyki w T1-4 przy budżecie 200 i 300 na **prawach S-0** (komutatywna, x(xy)=y, łączna;
  ziarna 700–729), czyli na tych samych prawach, które S-1b ma rozstrzygnąć. Budżet S-1b wybrano **po** tym podglądzie.
- W S-1 (T1, budżet 100) heurystyka > los w 4/5 praw.
- S-1b jest więc **replikacją na świeżych ziarnach tych samych praw**, nie niezależnym testem. Ryzyko „przestawiania bramki po wyniku” oceniamy jako umiarkowane.
  Łagodzą je: zmiana dotyczy tylko budżetu, diagnoza opiera się na zużyciu budżetu, werdykt S-1 zostaje, świeże ziarna i zamrożenie przed przebiegiem.
- Warunek ważności to „niepusta pula pierwszego snu”, a nie proponowane w raporcie S-1 „wydatek po dniu 1 > 0”, bo pula nie zależy od ramion.

## 1. Hipotezy

Jak w S-1 (`PREREJESTRACJA_S1.md`, sekcja 1): H-bramka (dobry wybór się opłaca), H-G (heurystyka ogólności bije los), w T1 i w T1-4.

## 2. Ramiona, światy, miary

Bez zmian względem S-1 (sekcje 2–4 `PREREJESTRACJA_S1.md`): ramiona losowa, heurystyka, wyrocznia_pokrycia (bramka), wyrocznia_trafnosci (opisowa);
światy T1 i T1-4 (baza + literały, 1 kontrprzykład); prawa `PRAWA_S0`; miara główna M1 = pole pod krzywą pokrycia od końca dnia 1 do
b = min(wywołania_x, wywołania_y); M2 trafność w pierwszym śnie; bootstrap sparowany 95%, 10 000, ziarno 12345.

**Zmiany:**

| Element | S-1 | S-1b |
|---|---|---|
| Budżet | wspólny 100 | dzień 1: limit 300; po dniu 1 osobno **50** wywołań (`uruchom(..., budzet=300, budzet_snu=50)`) |
| Ziarna | 100–179 | **800–879** (świeże: 100–179 S-1, 500–579 moc, 600–679 zarezerwowane dla LMM, 700–729 obejrzane w recenzji S-1) |
| Ważność | brak | prawo jest **ważne** w świecie, jeśli pula pierwszego snu (identyczna dla ramion) jest niepusta w ≥ 90% ziaren |

Uzasadnienie wartości (przed przebiegiem): limit dnia 300 nie wiązał w analizie mocy (0% przebiegów); gdyby związał na prawach S-0, prawo nie traci ważności,
bo sen i tak dostaje 50 wywołań. 50 wywołań po dniu 1 to rząd wielkości, jaki sen zużywał w S-1 w T1 (ok. 30) i w eksploracji recenzenta w T1-4 (31–52).
**Limit 50 wiąże w części praw** (analiza mocy: średnie zużycie 48–50 w dwóch prawach T1-4; test dymny recenzenta: 7–100% przebiegów na limicie
w 4 z 10 par świat–prawo). M1 mierzy wtedy tempo pokrycia w pierwszych 50 wywołaniach snu, symetrycznie dla ramion. Runner raportuje opisowo,
jak często każde ramię dochodzi do limitu.

## 3. Analiza mocy (przed zamrożeniem, prawa SPOZA S-0, ziarna 500–579)

`python -m matylda_rdzen.s1b --moc`, wynik w `wyniki/s1b_moc_prawa_spoza_s0.txt`.
- Ważność: sen odbywa się w 96–100% ziaren we wszystkich 10 parach (świat, prawo); dzień 1 nigdy nie dochodzi do limitu 300.
- P(dolna granica CI > 0 w ≥ 3 z 5 praw) przy n = 20 / 40 / 80: wyrocznia 1,00 / 1,00 / 1,00 w obu światach; heurystyka T1 0,54 / 0,93 / 1,00, T1-4 1,00 / 1,00 / 1,00.
- Efekty (krawędzie TR): wyrocznia T1 2,2–5,6, T1-4 1,0–12,9; heurystyka T1 0,35–1,37, T1-4 −0,12–2,94.
Mocy dla kategorii „pomijalna” nie szacowano. Prawdopodobieństwa z 200 losowań podprób (błąd MC ok. ±0,035); plik `.txt` to przeformatowane wyjście `--moc`.

## 4. Kryteria (rozstrzygające)

Jak w sekcji 6 `PREREJESTRACJA_S1.md`, z jedną zmianą: **liczą się tylko prawa ważne**. Prawo nieważne nie zalicza bramki ani kategorii
(próg 3 z 5 praw pozostaje; nieważne prawo działa jak niezaliczone). δ(W) = 0,25 × średni efekt wyroczni pokrycia po prawach ważnych.

- Bramka nie przeszła w którymś świecie → **NIEINFORMATYWNY**.
- „lepsza” w obu światach → **WYNIK**: heurystyka wybiera lepiej niż los (replikacja w dwóch światach).
- „pomijalna” w którymkolwiek → **WYNIK NEGATYWNY** (efekt pomijalny, nie zerowy) w tym świecie.
- inaczej → **NIEROZSTRZYGNIĘTY**.

Raport podaje zawsze: ułamek efektu wyroczni osiągany przez heurystykę, prawa z górną granicą < 0 (pole i, opisowo, pokrycie w b), M2 dla śmiałych i powtórki.
Pola opisowe liczone po wszystkich prawach oznaczamy w raporcie, które prawa są nieważne. Ograniczenie odziedziczone po S-1: δ jest średnią po prawach,
więc jedno prawo z dużym efektem wyroczni może je zawyżyć. Analizy spoza tej listy są eksploracyjne (np. dekompozycja „powtórka przed śmiałymi” vs porządek wsparcia).

## 5. Kontrola jakości

`pytest` (w tym test osobnego budżetu snu); niezależny recenzent przed zamrożeniem i po wynikach; raport z poziomami pewności.
Ramię LMM: zasady z sekcji 7 `PREREJESTRACJA_S1.md` (świeże ziarna 600–679, zakaz danych ze światów praw S-0), z budżetem jak w S-1b.
