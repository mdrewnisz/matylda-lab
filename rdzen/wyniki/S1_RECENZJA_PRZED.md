# S-1: niezależna recenzja przed uruchomieniem (24.11) i odpowiedzi

Recenzent: osobny agent, bez udziału w budowie. Nie uruchamiał S-1; testy dymne tylko na prawach spoza S-0 (ziarna 200–219, 300–379, 400–419).
Werdykt recenzji wersji 1: **nie zamrażać** (2 uwagi blokujące). Poniżej uwagi i co zmieniono w wersji 2.

| # | Waga | Uwaga | Odpowiedź (wersja 2) |
|---|---|---|---|
| 1 | BLOKUJĄCA | Miara „pokrycie w b = min(cx, cy)” przy 20 ziarnach ma znikomą moc (szansa na ≥ 3/5 praw ok. 1%), bo przebiegi wyczerpują pulę, a końcowe pokrycia się zbiegają. Werdykt „obalona” byłby artefaktem. | Miara główna = pole pod krzywą pokrycia od końca dnia 1 do b. 80 ziaren (100–179). Analiza mocy na prawach spoza S-0 zapisana w sekcji 5 (moc ≥ 0,99 dla bramki i H-G przy n = 80). |
| 2 | BLOKUJĄCA | Kryterium utożsamiało brak dowodu z obaleniem. | Trzy kategorie: lepsza / nie lepsza (górna granica < δ = 0,25 efektu wyroczni) / nierozstrzygnięta. |
| 3 | WAŻNA | M2 (trafność po całym przebiegu) nie mierzy wyboru, bo pule się wyczerpują. | M2 = trafność k obudzonych w pierwszym śnie wobec trafności tej samej puli, osobno dla powtórki i śmiałych. |
| 4 | WAŻNA | Wyrocznia trafności nie jest górną granicą pokrycia; bramka mogła nie przejść z przyczyn mechanicznych. | Dodano wyrocznię pokrycia (najpierw krawędzie na TR) jako bramkę; wyrocznia trafności przemianowana i opisowa. |
| 5 | WAŻNA | Kod niezamrożony, runner nie sprawdza git ani hashy. | Runner odmawia przy brudnym drzewie, istniejących wynikach lub złym hashu U4 (pełny); zapisuje commit i sha plików kodu. |
| 6 | WAŻNA | Sekcja LMM: zakaz danych tylko dla ziaren 100–119 nic nie chroni; LMM oceniany na znanych ziarnach. | Zakaz danych z W_H dla praw S-0 (rząd 3 i U4) niezależnie od ziarna; świeże ziarna 600–679 z ponownymi ramionami kontrolnymi; adapter bez nazw pojęć. |
| 7 | DROBNA | Budżet 50 i M1-stały prawie nic nie powiedzą. | Budżet 50 usunięty; M1-stały opisowy. |
| 8 | DROBNA | Brak testów S-1. | 4 testy (wspólne czuwanie i pula w rzędzie 3 i 4, determinizm losowej, brak świata w nie-wyroczniach, pole pod krzywą). |
| 9 | DROBNA | Wyjście runnera nie pokrywa kryteriów 3–4. | Flagi i kategorie per świat, prawa istotnie ujemne, jednoznaczne komunikaty werdyktu. |
| 10 | DROBNA | Heurystyka wśród śmiałych to zwykły los. | Zapisane w sekcji 2 jako ograniczenie interpretacji. |
| 11 | DROBNA | Ścieżka wyboru świata na tych samych prawach; tylko wskazane kontrasty decydują. | Zapisane w sekcjach 3 i 4. |

Pełny tekst recenzji: w historii wątku projektu (24.11).

## Ponowna kontrola wersji 2 (ten sam recenzent)

Werdykt: **można zamrozić** po zmianie sformułowania. Poprawki 1–6 wykonane poprawnie, 18 testów przechodzi (w tym regresja KG-0b).
- WAŻNA: kategoria „nie lepsza” przy δ = 0,25 efektu wyroczni nie znaczy „nie lepsza od losowej”. Zmieniono na „pomijalna”, z δ i prawami z dolną granicą > 0 w komunikacie.
- DROBNE: brak mocy dla „pomijalna”, ryzyko bramki w T1-4, przypis o wyroczni pokrycia: dopisane w sekcji 5. `uniwersum4.py` dodany do hashowanych plików.
