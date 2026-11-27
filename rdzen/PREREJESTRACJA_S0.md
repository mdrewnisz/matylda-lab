# Prerejestracja S-0: czy sen podnosi sufit odkryć?

Status: **EKSPLORACYJNE**, zamrożone przed pierwszym uruchomieniem ramion snu na prawach S-0.
Kontekst: `raporty/Matylda_rdzen.md` (v0.2), Masterplan v1.1 rozdz. 0 i priorytet P1.

## Przed uruchomieniem sprawdzono tylko

1. Zgodność czuwania z KG-0b: ramię A2 odtwarza `kg/kg0b_wyniki.json` co do wywołań, liczby
   prawdziwych krawędzi i całej krzywej pokrycia we wszystkich 100 przebiegach (5 praw × 20 ziaren).
2. Test dymny wszystkich ramion na prawie spoza S-0 („lewa samodystr.”, ziarno 0), bez oglądania
   pokrycia na prawach S-0.

## Hipoteza

**H-sen.** Faza offline (konsolidacja pamięci, powtórka zapamiętanych kontrprzykładów, śmiałe przeczucia,
przycinanie i wybór przez intuicję) przy tym samym budżecie wywołań weryfikatora pokrywa więcej
prawdziwej redukcji przechodniej niż ramię, które zamiast snu dostaje tyle samo świeżych obserwacji.

## Świat i stałe

- Magmy rozmiaru 3; prawa podłożone: idempotentna, komutatywna, x(xy)=y, łączna, medialna; ziarna 0–19.
- Okno 20 magm, MIN_SUPPORT = 2, kontrprzykłady do 50 na wywołanie (jak KG-0b).
- Budżet weryfikatora B ∈ {25, 50, 100}; główny B = 50. Po każdym śnie budzi się najwyżej 10 kandydatur.
- Intuicja: `HeurystykaOgolnosci` (wsparcie przesłanki / liczba znanych magm, śmiałe przeczucia −1). Bez LLM, bez LMM.

## Ramiona

Czuwanie 1 jest identyczne we wszystkich ramionach (= A2 z KG-0b). Różnią się tym, co dzieje się, gdy
kandydaci z okna się wyczerpią, a budżet jeszcze zostaje.

| Ramię | Faza po czuwaniu 1 |
|---|---|
| A2 | Nic. Koniec. |
| W+ | Kontrola „więcej dnia”: tyle świeżych losowych magm ze świata, ile S mógłby powtórzyć (liczba zapamiętanych kontrprzykładów spoza obserwacji); zwykły proponujący dnia. |
| S-los | Losowe pary pojęć przycinane pamięcią kontrprzykładów. |
| **S** | Sen: konsolidacja (domknięcie, klasy) → powtórka okna i kontrprzykładów (wsparcie ≥ 2) + śmiałe przeczucia (wsparcie = 1) → przycinanie (pamięć porażek, krawędzie wynikające z wiedzy) → intuicja. |
| S−K | Jak S, ale bez konsolidacji (nie pomija krawędzi wynikających z wiedzy). |

Sen nie ma dostępu do weryfikatora (asercja w pętli), świata ani prawdy podstawowej.

## Miary

- Główna: pokrycie redukcji przechodniej prawdziwego grafu (na klasach) przy budżecie B.
- Pomocnicze: pokrycie krawędzi podłożonych; trafność intuicji ze snu; liczba wywołań i cykli.

## Analiza i warunki falsyfikacji

Dla każdego prawa: sparowane różnice po ziarnach, średnia i 95% CI bootstrap (10 000 losowań, ziarno 12345).

- **H-sen obalona w tym świecie**, jeśli dolna granica CI dla S − W+ przy B = 50 jest ≤ 0 w co najmniej 3 z 5 praw.
  W przeciwnym razie: nie obalona (wsparta w tym świecie, status eksploracyjny).
- **Konsolidacja zbędna**, jeśli S − S−K przy B = 50 nie ma dolnej granicy > 0 w co najmniej 3 z 5 praw.
- **Sen to szum**, jeśli S − S-los przy B = 50 nie ma dolnej granicy > 0 w co najmniej 3 z 5 praw.
- B = 25 i B = 100 oraz pokrycie podłożonych są raportowane pomocniczo, nie zmieniają werdyktu.

## Deflacja z góry

Wynik dotyczy wyłącznie magm rzędu 3, tego słownika pojęć i tej heurystyki intuicji. Nie jest twierdzeniem
o „intuicji” ani o śnie w ogóle. Powtórka kontrprzykładów to ponowne użycie epizodów zdobytych od
weryfikatora, nie nowa wiedza z niczego; dlatego kontrolą jest W+ z równą liczbą świeżych epizodów.
S-0 nie jest rekombinacją trajektorii LLM z Masterplanu (rozdz. 11) i nie omija bramek H1.

## Znane ograniczenia (przed wynikiem)

- Przy B = 25 czuwanie 1 często zużywa cały budżet, więc ramiona mogą się nie różnić.
- W+ jest dopasowany do *własnej* pamięci kontrprzykładów, nie do pamięci S (ramiona są niezależne).
- S dostaje śmiałe przeczucia, których W+ nie ma; jeśli S wygra, trzeba rozdzielić udział powtórki i śmiałości (następny eksperyment, nie zmiana werdyktu).
