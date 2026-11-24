# LMM v3: raport (24.11)

Plan z kryterium zapisanym przed treningiem: `PLAN_LMM_V3.md` (fc3b3fd). Wagi zacommitowane przed walidacją (077062a), wynik walidacji w cfe7936.
Niezależna recenzja: `wyniki/LMM_V3_RECENZJA.md`.

## Werdykt (wg sekcji 4 planu)

**NIE PRZESZŁA → WYNIK NEGATYWNY dla v3.** LMM − heurystyka, dolna granica 95% CI > 0: T1 0/5 praw, T1-4 1/5 (prawa samodystr.).
LMM istotnie gorszy od heurystyki: T1 4/5, T1-4 3/5; istotnie gorszy od **losowego** w 4/10 par. Bramka (wyrocznia − heurystyka) spełniona w 10/10,
więc test był informatywny. Replikacja recenzenta na ziarnach 1560–1599: ten sam obraz. **Test na S-0 nie zostanie uruchomiony; ziarna 600–679 nietknięte.**

## Co się zmieniło względem v2

Tylko dane: 323 światy z losowych praw równościowych (zamiast 32), 8 ziaren na świat, wybór epoki na odłożonych światach. Architektura bez zmian.

## Ustalenia

| Ustalenie | Status |
|---|---|
| Offline na odłożonych światach treningowych LMM rozpoznaje prawdziwość przeczuć (AUC 0,91; heurystyka 0,56). Dla praw nowych i powtórzonych na innym uniwersum tak samo (0,913 vs 0,916) | WYNIK |
| Na prawach walidacyjnych ta zdolność słabnie (AUC 0,64–0,84), a rozróżnienie „krawędź TR vs inna prawda” jest gorsze niż u heurystyki (0,27–0,58) | WYNIK |
| W pętli LMM wybiera więcej prawdziwych przeczuć niż heurystyka (np. T1 lewa samodystr. 88% vs 68%), a mimo to pokrycie jest gorsze. Część tej różnicy to kara heurystyki za śmiałe przeczucia, nie „intuicja” | WYNIK / WNIOSKOWANIE |
| Nawet idealna trafność (wyrocznia trafności) odzyskuje tylko od −3% do 60% luki do wyroczni pokrycia: cel „prawdziwość” ma niski sufit | WYNIK (ziarna 1560–1599) |
| W 1. śnie (stan wspólny) LMM bywa lepszy od heurystyki; traci w snach 2+ | WYNIK |
| Graf pomaga względem ablacji (7/10 par), ale oba warianty są pod heurystyką | WYNIK; nie dowodzi, że graf niesie intuicję |

## Możliwe przyczyny (do sprawdzenia, nie rozstrzygnięte)

1. **Rozjazd celu:** etykieta 1 / 0,5 / 0 uczy głównie „prawda vs fałsz”, a pokrycie wymaga nowych krawędzi TR. HIPOTEZA, częściowo poparta (niski sufit wyroczni trafności).
2. **Ekspozycja:** trening tylko na trajektoriach ramion losowego i heurystyki; od 2. snu model ocenia stany, jakich nie widział. HIPOTEZA, dobrze wsparta przez wzór „1. sen dobry, dalsze złe”.
3. **Przesunięcie rozkładu z ochrony przed wyciekiem:** po usunięciu magm 10 praw węzły-prawa w treningu są prawie zawsze puste (2 z 17), w walidacji 10–16 z 16. WYNIK (przesunięcie), HIPOTEZA (że szkodzi).
4. **Duplikaty w top-k:** w części praw wybrane krawędzie TR to te same pary klas. WYNIK w części praw.

## Co dalej (propozycja recenzenta, do decyzji Michała)

Deduplikacja top-k dla wszystkich ramion; cel = ranking imitujący wyrocznię pokrycia (bez etykiety 0,5); dane zbierane też na trajektoriach samego modelu;
słownik treningowy z aktywnymi węzłami-prawami; układ 2×2 (cel × dane) najpierw offline, potem jedna walidacja na nowych ziarnach.
Ostrzeżenie: przyrost pokrycia zależy od całego wybranego zbioru i stanu, a zysk w 1. śnie nie przewiduje M1.
Uwaga metodologiczna: 5 praw walidacyjnych widział już badacz (v0–v3); przy przyszłym wyniku pozytywnym potrzebny będzie nowy zestaw praw.

## Zużyte ziarna

1500–1507 (trening v3), 1520–1559 (walidacja v3), 1560–1599 (diagnostyka recenzenta). Nadal zarezerwowane i nieużyte: 600–679.
