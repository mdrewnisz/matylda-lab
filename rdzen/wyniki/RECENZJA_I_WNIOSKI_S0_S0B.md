# S-0 i S-0b: niezależna recenzja, poprawki i wnioski

Data: 23.11.2026. Recenzent: osobny agent bez kontekstu konstrukcji (czytał kod, prerejestracje i wyniki; uruchamiał własne skrypty kontrolne, nie zmieniał repo). Dodatkowo automatyczny przegląd Codex na PR #2.

## Co recenzja potwierdziła

- Prerejestracje poprzedzają wyniki w historii git; sumy sha256 zgadzają się; U4 odtwarza się bit w bit; losowe wiersze wyników odtwarzają się bez różnic.
- Niezależne przeliczenie TR, klas i krawędzi podłożonych zgadza się we wszystkich 10 światach.
- **Brak przecieków:** ramiona snu nie widzą weryfikatora, prawdy podstawowej ani świata; czuwanie 1 jest wspólne.

## Co recenzja znalazła (i co z tym zrobiono)

| # | Znalezisko | Waga | Działanie |
|---|---|---|---|
| 1 | Miara przy stałym B nagradza **wydawanie budżetu**: pętla kończy się, gdy ramię nie ma kandydatów, więc kontrole zostawiają niewydane wywołania. | BŁĄD interpretacyjny | Dodana miara „równy faktycznie zużyty budżet” (`korekta.py`). |
| 2 | W+ i W+S dopisywały świeże magmy w każdym cyklu od nowa: 2,5–4× więcej niż „tyle samo” z prerejestracji. | BŁĄD implementacji | Poprawione: łączna liczba świeżych magm = liczba unikalnych kontrprzykładów. |
| 3 | S-los w kółko proponował krawędzie wynikające z wiedzy, które czuwanie pomijało; dochodził do limitu 50 cykli z niewydanym budżetem (Codex). | BŁĄD implementacji | Poprawione: S-los nie proponuje krawędzi wynikających z wiedzy. |
| 4 | Rząd 4 jest „trudniejszy” głównie przez rzadsze okno; „podłożone” znaczy tylko „fałszywe gdzieś w U4”. | RYZYKO | Zapisane jako ograniczenie. |
| 5 | Kontrprzykłady to pierwsze 50 wg indeksu, nadreprezentują rzadkie bloki U4; S−K bez pomijania krawędzi wynikających jest bliskie tautologii. | RYZYKO | Zapisane jako ograniczenie. |
| 6 | Część TR (krawędzie do klasy ⊤) jest nieosiągalna dla każdego ramienia. | UWAGA | Nie zmienia kontrastów. |

## Wyniki po poprawkach (`wyniki/KOREKTA_RAPORT.md`, POST HOC)

| Pytanie | Stały B (jak w prerejestracji) | Równy zużyty budżet |
|---|---|---|
| S > W+ (rząd 3, S-0) | TAK 5/5 | NIE 0/5; **istotnie ujemne w 4/5** |
| S > W+ (rząd 4, G1) | TAK 5/5 | NIE 0/5; istotnie ujemne w 2/5 |
| Powtórka > świeże epizody, S > W+S (G2, rząd 4) | NIE 2/5 | NIE 0/5; **istotnie ujemne w 3/5** |
| S > W+S (P1, rząd 3) | TAK 4/5 | NIE 0/5; istotnie ujemne w 4/5 |
| Generator snu na świeżych > dzień, W+S > W+ (P2) | TAK 5/5 | NIE 0/5 |
| Śmiałe przeczucia, S > S−Ś (P3) | TAK 5/5 | NIE 0/5 |
| Sen > losowy przegląd (S-0, rząd 3, B = 50) | TAK 4/5 | **TAK 5/5** |
| Sen > losowy przegląd (P4, rząd 4, B = 100) | NIE 0/5 (losowy dochodzi dalej) | **TAK 5/5** |
| Konsolidacja, S > S−K | TAK 5/5 | TAK 5/5 (bliskie tautologii) |

## Wnioski (z poziomami pewności)

- **WYNIK NEGATYWNY:** powtórka własnych porażek nie ma wartości ponad tyle samo świeżych epizodów. Przy równym budżecie jest wręcz gorsza. Hipoteza „sen = powtórka kontrprzykładów” odpada w tej formie.
- **WYNIK NEGATYWNY:** sen nie jest wydajniejszy na jedno wywołanie weryfikatora niż dzień. Dopóki proponujący dnia ma kandydatów, jego kandydatury są lepsze.
- **WYNIK (eksploracyjny, wąski świat):** sen jest generatorem, który działa, gdy dzień gaśnie. Przy stałym budżecie pokrywa więcej, bo wciąż ma co proponować (głównie dzięki śmiałym przeczuciom). Na jedno wywołanie bije losowy przegląd w obu rzędach, ale wyczerpuje się wcześniej niż losowy przegląd.
- **WNIOSKOWANIE dla rdzenia:** kolejność ma znaczenie: najpierw dzień (wydajny), potem sen jako generator przestrzeni hipotez, gdy dzień nic już nie proponuje. Wąskim gardłem nie jest pamięć ani powtórka, tylko **wybór, które śmiałe przeczucie sprawdzić**. To dokładnie zadanie intuicji (port pod LMM).
- **RYZYKO dla S-1:** w obu rzędach losowa para po przycięciu pamięcią jest prawdziwa w ~90%. W takim świecie intuicja nie ma czego rozstrzygać. Przed testem LMM potrzebny jest świat, w którym śmiałe przeczucia są w większości fałszywe (np. większy słownik pojęć, koniunkcje przesłanek).
