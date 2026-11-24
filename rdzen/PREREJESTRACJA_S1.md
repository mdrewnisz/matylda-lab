# Prerejestracja S-1: czy intuicja wybiera lepsze przeczucia niż przypadek?

Status: **zamrożona** (24.11), wersja 2 po niezależnej recenzji przed uruchomieniem (`wyniki/S1_RECENZJA_PRZED.md`).
Zamrożenie = commit tego pliku razem z kodem przed pierwszym przebiegiem `python -m matylda_rdzen.s1`. Runner odmawia pracy,
gdy `rdzen/` ma niezacommitowane zmiany, gdy wyniki już istnieją albo gdy hash U4 się nie zgadza; do wyników zapisuje commit,
sha256 tego pliku i sha256 plików kodu. Kontekst: `wyniki/RECENZJA_I_WNIOSKI_S0_S0B.md`, `SWIAT_T1_PROJEKT.md`.

## 1. Pytanie i hipotezy

S-0/S-0b pokazały, że sen jest generatorem przeczuć, a wąskim gardłem jest **wybór**, które z nich obudzić. To rola portu `Intuicja` (docelowo LMM).
S-1 pyta, czy intuicja bez dostępu do prawdy wybiera lepiej niż los, w światach, gdzie los zwykle chybia (T1, T1-4).

- **H-bramka (warunek ważności):** w T1 i T1-4 dobry wybór się opłaca, tzn. wyrocznia pokrycia bije wybór losowy.
- **H-G (główna):** `HeurystykaOgolnosci` daje większe pokrycie TR niż wybór losowy, w obu światach.
- **H-LMM (później, osobna poprawka):** to samo dla `IntuicjaLMM` (sekcja 7).

Poziom: HIPOTEZA. Wynik negatywny dla heurystyki jest równie informatywny (prosta ogólność nie wystarcza, LMM ma realne zadanie).

## 2. Ramiona

Wszystkie ramiona to ta sama pętla `S` (`SenPelny`: konsolidacja, powtórka kontrprzykładów, śmiałe przeczucia ze wsparciem 1, przycinanie).
Różnią się **wyłącznie** obiektem portu `Intuicja`, który ustala, które `k = 10` kandydatur z puli snu obudzić:

| Ramię | Klasa | Rola |
|---|---|---|
| losowa | `IntuicjaLosowa(ziarno)` | kontrola: wybór na ślepo (strumień `[ziarno, 2]`) |
| heurystyka | `HeurystykaOgolnosci()` | testowana: wsparcie przesłanki / liczba znanych magm; śmiałe przeczucia z karą −1 |
| wyrocznia_pokrycia | `IntuicjaWyroczniaPokrycia(świat)` | **kalibracja, bramka**: zna prawdę; najpierw prawdziwe krawędzie na redukcji przechodniej (para klas w TR), potem inne prawdziwe, na końcu fałszywe |
| wyrocznia_trafnosci | `IntuicjaWyrocznia(świat)` | **kalibracja, opisowa**: prawdziwe przed fałszywymi, bez względu na TR |

Wyrocznie nie są intuicją ani górną granicą w ścisłym sensie (np. fałszywe sprawdzenia dają kontrprzykłady, które też przycinają pulę).
Mierzą tylko, czy w danym świecie wybór w ogóle ma znaczenie.

Zapisane z góry ograniczenie interpretacji: kara −1 sprawia, że heurystyka budzi najpierw powtórkę (wsparcie ≥ 2), a wśród śmiałych przeczuć
wybiera praktycznie losowo (równe oceny, remis rozstrzyga strumień snu). H-G testuje więc regułę „ogólne przed śmiałymi”,
nie trafność wyboru wśród śmiałych. To drugie mierzy M2 (opisowo) i docelowo LMM.

Czuwanie 1 jest identyczne we wszystkich ramionach (to samo `default_rng(seed)`), pula pierwszego snu także (test `test_s1_czuwanie_i_pula_wspolne`).
Sen nie woła weryfikatora (asercja w `petla.uruchom`).

## 3. Światy i próbka

| Świat | Rząd | Słownik | Kontrprzykłady na obalenie |
|---|---|---|---|
| T1 | 3 (wszystkie 3^9 magm) | baza + literały `a·b=c` | 1 |
| T1-4 | 4 (U4, sha256 uint8 `dca6e9968ef62587d7e2c4f274771753da81800a635a71b9c9e5fbc275001e37`) | baza + literały | 1 |

Prawa: `PRAWA_S0` (idempotentna, komutatywna, x(xy)=y, łączna, medialna). **Ziarna 100–179** (80 na prawo).
Ścieżka wyboru, jawnie: świat T1 wybrano kalibracją na tych samych prawach (ziarna 0–19), po dodaniu dźwigni „literały” po porażce pierwszej siatki;
kalibracja mierzyła trudność świata, nie porównywała ramion. Budżet 100 wywołań weryfikatora; reszta jak w S-0b (`K_WINDOW` 20, `ILE_INTUICJI` 10, `MAX_CYKLI` 50).
Łącznie 2 × 5 × 80 × 4 = 3 200 przebiegów (ok. 20 minut).

## 4. Miary

- **M1 (główna): pole pod krzywą pokrycia po dniu 1, przy równym zużytym budżecie.** Dla pary (x, y) i ziarna s: d1 = wywołania po czuwaniu 1 (wspólne),
  b = min(wywołania_x, wywołania_y, 100), wartość ramienia = średnia z pokrycia(t) dla t = d1 … b (pokrycie(t) = krawędzie TR wynikające z wiedzy
  po ostatnim punkcie krzywej z ≤ t wywołaniami; gdy b ≤ d1, pokrycie(b)). d_s = wartość_x − wartość_y.
  Uzasadnienie: przebiegi zwykle wyczerpują pulę przed budżetem i końcowe pokrycia się zbiegają; wybór zmienia, *jak szybko* rośnie pokrycie.
  Pole mierzy to wprost i nie nagradza samego wydawania wywołań.
- **M1-koniec, M1-stały (opisowe):** pokrycie w b oraz w 100.
- **M2 (opisowa): trafność wyboru w pierwszym śnie.** Pula pierwszego snu jest identyczna w ramionach; porównujemy trafność k obudzonych
  z trafnością całej puli, łącznie i osobno dla `sen:powtorka` i `sen:smiale`.
- **M3 (opisowa):** średnie wywołania, w tym dnia 1.

Przedział: bootstrap sparowany po ziarnach, 95%, 10 000 losowań, ziarno 12345 (`s0.ci95`). Werdykt zależy wyłącznie od kontrastów M1
`wyrocznia_pokrycia − losowa` i `heurystyka − losowa`; pozostałe pola JSON są opisowe.

## 5. Analiza mocy (przed zamrożeniem, na prawach SPOZA S-0)

`python -m matylda_rdzen.s1 --moc`, prawa: elastyczna, lewa i prawa samodystr., x(xy)=xy, (yx)x=y; ziarna 500–579; wynik w `wyniki/s1_moc_prawa_spoza_s0.json`.
Prawdopodobieństwo spełnienia „dolna granica CI > 0 w ≥ 3 z 5 praw” w podpróbach n ziaren:

| Kontrast, miara | T1, n = 20 / 40 / 80 | T1-4, n = 20 / 40 / 80 |
|---|---|---|
| wyrocznia_pokrycia − losowa, M1 (pole) | 1,00 / 1,00 / 1,00 | 1,00 / 1,00 / 1,00 |
| heurystyka − losowa, M1 (pole) | 0,60 / 0,95 / 1,00 | 0,99 / 1,00 / 1,00 |
| heurystyka − losowa, pokrycie w b | 0,02 / 0,01 / 0,00 | 0,39 / 0,90 / 1,00 |

Efekty na tych prawach (średnia, krawędzie TR): wyrocznia 2,1–5,6 (T1), 0–7,0 (T1-4); heurystyka 0,4–1,4 (T1), 0–1,7 (T1-4).
To uzasadnia zmianę miary głównej i n = 80. Wniosek o prawach S-0 nie jest stąd przenoszony; to tylko kalibracja mocy.
Mocy dla kategorii „pomijalna” nie szacowano. Znane ryzyko: w T1-4 na dwóch z pięciu praw spoza S-0 wyrocznia nie daje nic (efekt 0,06 i 0,00),
więc na prawach S-0 bramka w T1-4 może nie przejść i cały werdykt będzie NIEINFORMATYWNY. Przypis: wyrocznia pokrycia sprawdza parę klas w TR;
krawędź między nie-reprezentantami może nic nie pokryć, dopóki równoważność nie jest znana (bez znaczenia dla kalibracji).

## 6. Kryteria (rozstrzygające, w tej kolejności)

Dla każdego świata W osobno:
1. **Bramka(W):** wyrocznia_pokrycia − losowa, M1: dolna granica CI > 0 w ≥ 3 z 5 praw.
2. δ(W) = 0,25 × średni (po prawach) efekt wyroczni pokrycia w W: „efekt pomijalny” to mniej niż ćwierć tego, co daje idealny wybór.
3. Kategoria heurystyki w W:
   - **lepsza:** dolna granica CI(heurystyka − losowa) > 0 w ≥ 3 z 5 praw;
   - **pomijalna:** w przeciwnym razie, jeśli górna granica CI < δ(W) w ≥ 3 z 5 praw. To nie znaczy „nie lepsza od losowej”, tylko
     „zysk poniżej ćwierci zysku idealnego wyboru”; δ liczy się z tych samych danych. Przy tej kategorii raportujemy też prawa z dolną granicą > 0;
   - **nierozstrzygnięta:** pozostałe przypadki.

Werdykt S-1 dla H-G:
- bramka nie przeszła w którymś świecie → **NIEINFORMATYWNY** (raportujemy jako WYNIK o świecie; ewentualne kontrasty heurystyki tylko eksploracyjnie);
- „lepsza” w obu światach → **WYNIK**: heurystyka wybiera lepiej niż los;
- „pomijalna” w którymkolwiek świecie → **WYNIK NEGATYWNY** dla H-G w tym świecie (efekt pomijalny, nie zerowy);
- inaczej → **NIEROZSTRZYGNIĘTY**; wynik w jednym świecie bez drugiego to najwyżej HIPOTEZA do replikacji.

Zawsze raportujemy prawa z górną granicą CI < 0 (heurystyka istotnie gorsza od losu) i wielkość efektu heurystyki jako ułamek efektu wyroczni.
Nie dodajemy praw, ziaren ani miar po obejrzeniu wyników; inne analizy są eksploracyjne.

## 7. Ramię LMM (osobna poprawka, nie część tego przebiegu)

`IntuicjaLMM` dołącza tylko przez commit-poprawkę zrobioną **przed** pierwszym przebiegiem LMM, który zamraża:
- commit adaptera (wejście: `macierz_zaleznosci` i indeksy pary klas; **bez nazw pojęć**), sha256 wag, wersję kodera, deterministyczną inferencję;
- listę danych treningowych. **Zakaz** jakichkolwiek danych pochodnych ze światów W_H dla H ∈ `PRAWA_S0` w rzędzie 3 i w U4,
  niezależnie od ziarna (prawda świata nie zależy od ziarna). Trening tylko na innych prawach lub innych rzędach.
- **Świeże ziarna 600–679** do oceny LMM, z ponownie uruchomionymi na nich ramionami losowym, heurystyką i obiema wyroczniami
  (S-1 zna już wyniki na 100–179, więc ocena na tych samych ziarnach dawałaby miejsce na strojenie). Zakresy 1000–1049 i ≥ 2000 są zarezerwowane gdzie indziej.
- Kryteria jak w sekcji 6 z LMM w miejscu heurystyki; kontrast LMM − heurystyka opisowo.

## 8. Kontrola jakości przed wnioskami

- `pytest` przechodzi (w tym testy S-1: wspólne czuwanie i pula, determinizm ramienia losowego, ramiona nie-wyrocznie bez obiektu świata).
- Niezależny recenzent (osobny agent) czyta kod i wyniki przed wnioskami; jego uwagi trafiają do `wyniki/`.
- Raport rozdziela WYNIK / WNIOSKOWANIE / HIPOTEZA / SPEKULACJA / WYNIK NEGATYWNY.
