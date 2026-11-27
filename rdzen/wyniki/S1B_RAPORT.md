# S-1b: raport (24.11)

Przebieg prerejestrowany: `PREREJESTRACJA_S1B.md`, zamrożona i uruchomiona z commita efd969f (hashe prerejestracji, 9 plików kodu i U4 zgodne;
sprawdził niezależny recenzent, który odtworzył wszystkie kontrasty deterministycznie). Dane: `s1b_wyniki.json`, 3 200 przebiegów, ziarna 800–879.
Budżet: dzień 1 do 300 (nigdy nie wiązał), po dniu 1 osobno 50 wywołań. Analizy recenzenta poza prerejestracją są oznaczone jako eksploracyjne.

## Werdykt prerejestrowany

**WYNIK: heurystyka lepsza od losowej w obu światach.** Wszystkie 10 par świat–prawo ważne (sen odbył się w 97,5–100% ziaren), bramka 5/5 w obu światach.

| Prawo | T1: wyrocznia − los | T1: heurystyka − los | T1-4: wyrocznia − los | T1-4: heurystyka − los |
|---|---|---|---|---|
| idempotentna | 4,74 | 0,99 [0,66; 1,32] | 3,61 | 0,80 [0,61; 1,00] |
| komutatywna | 3,48 | 1,15 [0,87; 1,41] | 2,69 | 0,70 [0,47; 0,94] |
| x(xy)=y | 2,03 | 0,70 [0,43; 0,97] | 3,28 | 0,58 [0,35; 0,82] |
| łączna | 6,03 | 2,31 [1,86; 2,75] | 7,79 | 1,65 [1,31; 1,99] |
| medialna | 3,78 | 0,28 [−0,01; 0,57] | 3,56 | 0,70 [0,47; 0,92] |

(krawędzie TR, pole pod krzywą pokrycia po dniu 1, 95% CI; wszystkie kontrasty wyroczni mają dolną granicę > 0)

## Wnioski

1. **[WYNIK]** Heurystyka ogólności przyspiesza pokrycie TR w pierwszych ≤ 50 wywołaniach snu względem wyboru losowego: T1 4/5 praw, T1-4 5/5.
   To **replikacja na świeżych ziarnach tych samych praw S-0**; budżet wybrano po podglądzie (sekcja 0 prerejestracji), więc to nie jest niezależny test
   ani test uogólnienia. T1 praktycznie powtarza S-1 (0,89 / 1,11 / 0,74 / 1,66 / 0,22 wobec 0,99 / 1,15 / 0,70 / 2,31 / 0,28; medialna nie przechodzi w obu).
2. **[WYNIK]** Efekt jest mały względem idealnego wyboru: 7–38% efektu wyroczni pokrycia w T1, 18–26% w T1-4. W T1-4 górna granica CI jest poniżej δ w 4/5 praw,
   ale prerejestrowane pierwszeństwo daje kategorię „lepsza”. Uczciwe brzmienie: **istotnie lepsza od losu, rzędu jednej piątej do jednej trzeciej tego, co daje idealny wybór.**
3. **[WNIOSKOWANIE]** Limit snu 50 nie tworzy artefaktu w kontraście heurystyka − los: wiązanie jest podobne w obu ramionach, a przy stałym oknie [d1, d1+50]
   (eksploracyjnie) kierunek i istotność 9/10 kontrastów się utrzymują, ułamek efektu wyroczni bez zmian. „Pomijalność” w T1-4 nie jest odporna:
   δ zawyża łączna (wyrocznia kończy tam wcześnie z pełnym TR); bez niej δ = 0,82 i górna < δ tylko w 1/5 praw.
4. **[WNIOSKOWANIE, eksploracyjne]** Zysk heurystyki to głównie reguła „powtórka przed śmiałymi” (mediana ok. 70% efektu), reszta to porządek według wsparcia w powtórce
   (istotny w 6/10 par). **Wśród śmiałych przeczuć heurystyka jest losem z konstrukcji** (wszystkie mają wsparcie 1 i tę samą ocenę).
5. **[HIPOTEZA]** Efekt uogólnia się na inne prawa (analiza mocy, 5 praw spoza S-0: dodatnia średnia w 9/10 par; wyjątek (yx)x=y w T1-4, −0,12).
6. **[HIPOTEZA, eksploracyjne]** Idealny wybór wśród śmiałych przy zachowanym porządku warstw daje 0,24–1,69 krawędzi TR ponad heurystykę (ok. 40% luki do wyroczni, mediana).
   To realistyczny cel dla LMM.
7. **[SPEKULACJA]** Większość pozostałej luki wymaga stawiania prawdziwych śmiałych przeczuć przed fałszywą powtórką, czyli rankingu przez całą pulę, a nie tylko wewnątrz warstw.

## Konsekwencje dla ramienia LMM (do poprawki prerejestracji, sekcja 7 S-1)

- Kryterium główne: LMM − heurystyka > 0 (dolna CI) w ≥ 3/5 praw w obu światach, ziarna 600–679, budżet jak w S-1b.
- Minimalny istotny efekt: ok. 0,25 luki wyrocznia − heurystyka per prawo. δ liczyć medianą lub per prawo, nie średnią.
- Ułamek efektu wyroczni na dwóch oknach (min wywołań i stałe [d1, d1+50]).
- Miara offline na całej puli pierwszego snu: AUC i precyzja@k ocen LMM osobno dla śmiałych i powtórki, z etykietą prawdy i wkładu w TR; punkt odniesienia „los”.
- Kontrola: ramię „warstwy + LMM wśród śmiałych”, żeby oddzielić zysk z wyboru śmiałych od zysku z przestawienia warstw.
