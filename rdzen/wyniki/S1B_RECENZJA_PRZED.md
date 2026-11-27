# S-1b: niezależna recenzja przed uruchomieniem (24.11)

Recenzent: osobny agent. Testy dymne tylko na prawach spoza S-0 (ziarna 900–914, teraz „obejrzane”). `pytest`: 19 testów, brak regresji.
Werdykt: kod poprawny i spójny z prerejestracją; zamrozić po dwóch poprawkach tekstu.

| # | Waga | Uwaga | Odpowiedź |
|---|---|---|---|
| 1 | WAŻNA | Zdanie „przebiegi wyczerpują pulę wcześniej” jest fałszywe: limit 50 wiąże w części praw (T1-4 prawa samodystr. 73–100% przebiegów, x(xy)=xy 73–93%, T1 lewa/prawa samodystr. 7–73%). | Wariant (a): 50 zostaje, uzasadnienie przepisane zgodnie z danymi; runner raportuje odsetek przebiegów na limicie snu per ramię i prawo. |
| 2 | WAŻNA | Podgląd recenzenta S-1 dotyczył praw S-0, a budżet wybrano po nim. | Dopisane w sekcji 0: S-1b to replikacja na świeżych ziarnach tych samych praw, ryzyko umiarkowane. |
| D1 | DROBNA | Docstring `waznosc`; limit dnia 300 a ważność. | Poprawione; zapisane, że limit dnia nie unieważnia prawa. |
| D2 | DROBNA | Zmiana warunku ważności względem raportu S-1. | Nazwana w sekcji 0. |
| D3 | DROBNA | Słaby test budżetu snu. | Dodany test: dzień wiąże przy limicie 10, sen i tak się odbywa; `budzet_snu=None` = stare zachowanie. |
| D4 | DROBNA | δ średnią po prawach może zawyżyć jedno prawo. | Wzmianka w ograniczeniach (sekcja 4). |
| D5 | DROBNA | Błąd MC analizy mocy. | Podany (±0,035). |
| D6 | DROBNA | Pola opisowe po wszystkich prawach. | Raport oznaczy prawa nieważne. |
