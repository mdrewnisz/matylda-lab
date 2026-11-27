# Recenzja: heurystyka grafu `HeurystykaGrafu("oa+ob+kara")` (niezależna, krytyczna)

Data: 24.11. Przedmiot: `PLAN_HEURYSTYKA_GRAFU.md` (commit 459a097), `matylda_rdzen/heurystyki.py`, `heur_dev.py`,
`heur_walidacja.py`, `wyniki/heur_dev*.json`, `wyniki/heur_grafu_walidacja.json` (commit b9d7ef6).
Własne diagnostyki: **ziarna 1680–1719** (40 na prawo), te same 5 praw `PRAWA_MOCY`, światy T1 i T1-4, protokół S-1b
(`BUDZET_DNIA=300`, `BUDZET_SNU=50`, `CEX=1`, słownik `literaly`). Żadnego pliku repo nie zmieniałem poza tym.
Skrypty diagnostyczne leżą poza repo (scratchpad sesji) i nie są częścią wyniku.

Klasyfikacja ustaleń: **WYNIK** (sprawdzone na danych), **WNIOSKOWANIE** (wynika z wyników i kodu),
**HIPOTEZA** (spójne z danymi, niesprawdzone wprost), **SPEKULACJA**, **WYNIK NEGATYWNY**.

---

## 0. Werdykt w skrócie

- Procedura była zgodna z planem. Werdykt walidacji jest poprawnie policzony i **replikuje się na niezależnych
  ziarnach 1680–1719**: T1 5/5 lepsza, T1-4 4/5 lepsza, x(xy)=xy w T1-4 istotnie gorsza. **WYNIK.**
- Zysk nie jest trywialnym artefaktem liczby wywołań, okna `b = min`, deduplikacji ani tie-breaku.
  Odwrócenie znaku reguły („anty”) daje istotną stratę we wszystkich 10 światach. Sygnał niesie kolejność
  wyznaczona przez stopnie w grafie, a prawie całą pracę wykonuje człon **out(b)**. **WYNIK.**
- Trzeba jednak uczciwie opisać, co zysk znaczy. W 5 z 10 światów oba ramiona kończą z **tym samym pokryciem
  końcowym**, bo pula snu wyczerpuje się przed budżetem. Zysk to wtedy **tempo** (pole pod krzywą), a nie więcej
  znalezionej struktury. **WYNIK.**
- Deduplikacja par klas jest **bezczynna**: jej wyłączenie nic nie zmienia. **WYNIK.**
- Ułamek luki 1,0 w T1 (yx)x=y to **górny ogon szumu**. Na nowych ziarnach wynosi 0,73, a wyrocznia jest istotnie lepsza.
  **WYNIK.**
- Rozjazd „dewelopment 3T ≈ 0, a T1 duży zysk” wyjaśniają martwe węzły-prawa. W dev 3T niepustych jest średnio
  3,7 z 24 pojęć nieliterałowych, a w T1 19–23. Do tego dochodzi mała luka do wyroczni w 3T (0,4 wobec 1,7–5,3).
  **WYNIK** (opis). Związek przyczynowy to **WNIOSKOWANIE**.
- Rekomendacja: można przyjąć regułę jako **domyślną intuicję rdzenia, ale jawnie**: parametrem, z zachowaniem
  `HeurystykaOgolnosci` jako nazwanej linii bazowej i bez cichej zmiany domyślnej w `petla.uruchom`. Przed
  ogłoszeniem ogólności trzeba wykonać prerejestrowany test na S-0 (ziarna 600–679), szczegóły w sekcji 7.

---

## 1. Zgodność kodu i przebiegu z planem

| Punkt | Stan | Klasyfikacja |
|---|---|---|
| Kolejność commitów | 459a097 (plan, kod walidacji, reguła, wyniki dev) → b9d7ef6 (tylko `heur_grafu_walidacja.json`, 273 linie). `git diff 459a097 HEAD` dotyka wyłącznie pliku wyników. Pole `commit` w JSON = 459a097. `plan_sha256` = sha bieżącego planu (`fcd49c48…`). | WYNIK |
| Jedno uruchomienie | Kod odmawia przy brudnym drzewie i przy istniejącym pliku wyników. Nie wyklucza to wcześniejszego, nieutrwalonego przebiegu, ale odstęp 13 min między commitami odpowiada czasowi jednego przebiegu (~1600 przebiegów × ~0,5 s). Nie ma śladu nadużycia. | WNIOSKOWANIE |
| Ziarna | Walidacja `range(1640,1680)` zgodnie z planem. Dev 1600–1609 i 1620–1629 zgodnie z `heur_dev.py`. Brak kolizji z 600–679. | WYNIK |
| Analiza cech 1610–1613 („AUC 0,65–0,73”) | **Kodu tej analizy nie ma w repo**, więc tego kroku nie da się odtworzyć. Drobny brak. Wybór wzoru opiera się jednak na odtwarzalnych `heur_dev_grafu.json` i `heur_dev_potw.json`. | WYNIK (brak) |
| Brak użycia praw walidacyjnych przy wyborze | `heur_dev.py` używa wyłącznie `SWIATY_V3`. `zbuduj_swiat` dla 3T/4T wycina magmy wszystkich 10 praw (`WYKLUCZONE`) i ma `assert`. Liczby z planu odtwarzają się z JSON-ów: 4T potw. +1,045 / luka 2,300 = 0,45; 3T +0,031 / 0,417 = 0,07. | WYNIK |
| Kontaminacja „przez badacza” | Prawa walidacyjne były oglądane przy LMM v0–v3, a recenzja LMM v3 opisywała rolę węzłów-praw w TR w T1. Pomysł „stopnie w grafie” mógł więc być inspirowany wiedzą o T1. **Przemawia przeciw temu**, że plan przewidywał w T1 wynik ≈ 0, a wybrany wzór był w dev 3T *gorszy* od odrzuconych wariantów `+ib` (+0,10, 70% światów > 0). Gdyby wzór dostrajano pod T1, nie wybrano by wzoru z zerem w 3T. | SPEKULACJA (ryzyko niskie) |
| Wspólne czuwanie 1 | `uruchom` wykonuje czuwanie 1 z `rng(seed)` niezależnie od intuicji. Sen ma osobny strumień `rng([seed,1])`, a jego zużycie (`rng.random(len(pula))`) nie zależy od ocen. `s1b.roznice` ma `assert rx["d1"] == ry["d1"]`, który przeszedł w walidacji i w mojej replikacji (11 ramion, 400 przebiegów na ramię). | WYNIK |
| Kontrasty i werdykt | `analiza()` liczy `heur_grafu − heurystyka` sparowanym bootstrapem (`ci95`, stałe ziarno), tylko na prawach ważnych (`waznosc ≥ 0,9`; wszystkie 5 ważne w obu światach). „Lepsza” = dolna > 0, „gorsza” = górna < 0, próg ≥ 3 (bezwzględnie, więc konserwatywnie przy mniejszej liczbie ważnych praw). Reguły T1 zgodne z §4 planu. Werdykt „T1-4: 4/5; T1: 5/5” wynika poprawnie z liczb. | WYNIK |
| Drobne usterki raportowania | (a) „Ułamek luki” dzieli dwie średnie liczone na **różnych oknach** (`b = min(G,heur)` i `b = min(wyr,heur)`), więc to iloraz szumów bez CI. (b) JSON walidacji nie zapisuje `waznosc`, liczby wywołań ani trafności. (c) W dev `b` to min po *wszystkich* ramionach, a w walidacji min parami, więc miary nie są identyczne. Żadna z usterek nie zmienia werdyktu. | WYNIK |

---

## 2. Replikacja i ablacje (ziarna 1680–1719, n = 40 na prawo)

Miara M1 (pole, `b = min` parami), różnica względem `heurystyka` (HeurystykaOgolnosci): średnia [95% CI].
`G` = reguła zamrożona. `G_noD` = bez deduplikacji. `G_nokara` = `oa+ob` z deduplikacją. `G_notie` = bez tie-breaku wsparciem.
`ob` = out(b) − 3·[śmiałe]. `oa` = out(a) − 3·[śmiałe]. `anty` = −(oa+ob) − 3·[śmiałe]. `heurD` = heurystyka + deduplikacja.

| Świat | Prawo | G | G_noD | G_nokara | G_notie | ob | oa | anty | heurD | wyr |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | elastyczna | +0,38 [+0,06,+0,71] | +0,38 | **+1,01** | +0,12 [−0,26,+0,53] | +0,69 | −0,36 | −0,87 | 0,00 | +4,91 |
| T1 | lewa samodystr. | +2,29 [+1,85,+2,76] | +2,36 | +2,35 | +2,43 | +2,06 | −0,41 | −2,81 | −0,01 | +4,03 |
| T1 | prawa samodystr. | +3,19 [+2,56,+3,82] | +3,19 | +3,39 | +3,03 | +2,72 | −0,57 | −2,96 | −0,11 | +5,18 |
| T1 | x(xy)=xy | +1,32 [+0,94,+1,71] | +1,32 | +0,81 | +1,04 | +1,42 | +0,13 | −1,88 | 0,00 | +4,27 |
| T1 | (yx)x=y | +1,56 [+1,14,+2,00] | +1,74 | +1,83 | +1,67 | +1,32 | −0,42 | −1,16 | +0,02 | +2,14 |
| T1-4 | elastyczna | +0,15 [+0,03,+0,27] | +0,15 | **−0,38** | **−0,30** [−0,53,−0,08] | +0,26 | −0,04 | −1,44 | 0,00 | +2,12 |
| T1-4 | lewa samodystr. | +1,48 [+1,15,+1,80] | +1,48 | +1,23 | +1,36 | +1,54 | −0,11 | −1,80 | 0,00 | +3,02 |
| T1-4 | prawa samodystr. | +4,37 [+3,93,+4,81] | +4,37 | +4,19 | +4,43 | +3,26 | −0,02 | −1,83 | 0,00 | +11,10 |
| T1-4 | x(xy)=xy | **−1,64** [−1,98,−1,31] | −1,64 | −2,11 | −2,10 | −0,80 | −0,09 | −1,52 | 0,00 | +6,57 |
| T1-4 | (yx)x=y | +0,79 [+0,53,+1,06] | +0,74 | +0,69 | +0,78 | +0,74 | +0,05 | −0,61 | +0,04 | +0,97 |

Wnioski:

1. **Replikacja (WYNIK).** Znaki i istotność kryterium głównego powtarzają się co do prawa: T1 5/5 lepsza,
   T1-4 4/5 lepsza i x(xy)=xy istotnie gorsza. Najsłabsze prawo to elastyczna. W walidacji T1-4 jej dolna CI
   wynosiła +0,0115, u mnie +0,03, więc stoi na krawędzi.
2. **Deduplikacja jest bezczynna (WYNIK).** `G_noD` ≈ `G` wszędzie, a `heurD` = `heur` (0,00 w 7/10 światów).
   Mechanizm (WNIOSKOWANIE z kodu): duplikat tej samej pary klas po sprawdzeniu pierwszego jest rozstrzygany
   za darmo. Gdy pierwszy jest prawdziwy, drugi zostaje pominięty jako wynikający z domknięcia. Gdy jest fałszywy,
   kontrprzykład obala też drugi, bo klasy są równoważne w świecie. Duplikaty zajmują co najwyżej miejsca w k = 10.
   Nazwa „deduplikacja par klas” sugeruje, że ten składnik działa, a nie działa.
3. **Kara za śmiałe i tie-break są bez znaczenia w 8/10 światów, ale przesądzają o T1-4 elastycznej (WYNIK).**
   Bez kary albo bez tie-breaku wsparciem T1-4 elastyczna jest istotnie *gorsza*. „Zwycięstwo” w tym prawie jest
   więc kruche i zależy od drobnych szczegółów wzoru. Kryterium główne (≥ 3/5) przeszłoby i bez niego (3/5),
   ale bez zapasu.
4. **Sygnał niesie out(b), a nie out(a) (WYNIK).** Samo `ob` daje 70–100% efektu `G`, a w T1-4 x(xy)=xy szkodzi
   o połowę mniej (−0,80 wobec −1,64). Samo `oa` jest ≈ 0 albo lekko ujemne. Interpretacja (HIPOTEZA): konsekwent b,
   z którego już dużo wynika, leży „nisko” w porządku, więc krawędź a ⇒ b jest krótka i częściej należy do TR.
   W pierwszym śnie G podnosi odsetek TR wśród obudzonych z 0,21–0,39 do 0,45–0,67 w 4/5 praw T1.
5. **To nie jest „dowolna deterministyczna zmiana kolejności” (WYNIK).** `anty` jest istotnie gorsze od heurystyki
   we wszystkich 10 światach. Kierunek uporządkowania ma znaczenie.

---

## 3. Artefakty: czy zysk może być trywialny?

| Podejrzenie | Sprawdzenie | Ocena |
|---|---|---|
| Różnica liczby wywołań, `b = min` | G często kończy wcześniej (np. T1 lewa: 33 wobec 43 wywołań po dniu 1), bo pula się wyczerpuje. Przeliczyłem M1 na **stałym oknie [d1, d1+50]** z przeniesieniem ostatniej wartości. Znak i istotność bez zmian w 10/10 światach. Wartości: T1 +0,36 / +2,39 / +3,27 / +1,12 / +0,99; T1-4 +0,11 / +0,86 / +4,42 / **−1,54** / +0,22. Okno `b = min` zawyża wartość bezwzględną tam, gdzie oba ramiona kończą wcześnie ((yx)x=y: 1,56 → 0,99 w T1, 0,79 → 0,22 w T1-4), ale ułamki luki prawie się nie zmieniają. | WYNIK: nie artefakt |
| „Wybiera krawędzie, które i tak byłyby znalezione” | **Częściowo tak.** Pokrycie końcowe przy d1+50 jest identyczne (różnica 0,00) w T1 (yx)x=y oraz w T1-4 elastycznej, lewej i (yx)x=y. W T1 elastycznej różnica wynosi +0,45 z dolną CI = 0,00. Tam zysk to wyłącznie **wcześniejsze** znalezienie tych samych krawędzi TR. M1 mierzy tempo zgodnie z planem, więc to uprawniony zysk, ale nie wolno go opisywać jako „więcej struktury”. Realny wzrost pokrycia końcowego jest w T1 lewej i prawej (+1,3 i +2,1), T1 x(xy)=xy (+0,8), T1-4 prawej (+7,8) i paradoksalnie w T1-4 x(xy)=xy (+1,4). | WYNIK |
| Interakcja z deduplikacją | Brak efektu deduplikacji (§2.2). | WYNIK |
| Tie-break wsparciem | Istotny tylko w T1-4 elastycznej (§2.3). Nie jest źródłem zysku w pozostałych prawach. | WYNIK |
| Zależność od słownika literałów | Wszystkie światy (dev i walidacja) używają `literaly`, a ~27 z ~51 pojęć to literały a·b=c. Stopnie out(·) liczone są na grafie, w którym przeważają literały. Nie testowałem słowników `baza` i `negacje`. Wynik dotyczy **tylko** tego słownika. | HIPOTEZA (że przenosi się na inne słowniki: niesprawdzone) |
| Ułamek luki 1,0 w T1 (yx)x=y | Na ziarnach 1680–1719 ułamek wynosi 0,73 (stałe okno 0,76), a G − wyrocznia = −0,54 [−1,02, −0,10]. 1,0 to górny ogon. Luka jest tam najmniejsza (1,7–2,1 jednostki), więc iloraz jest najbardziej zaszumiony. Wyrocznia pokrycia nie jest optymalna (zachłannie TR-pierwsze), więc ułamek ~1 jest *możliwy*, ale nie jest wiarygodnym oszacowaniem. Uczciwy przedział dla tego prawa to ~0,7–1,0. | WYNIK |

---

## 4. Dlaczego dewelopment 3T ≈ 0, a T1 duży zysk

Policzyłem skład pojęć w światach (bez ziaren). Dla dev wylosowałem 40 światów z `swiaty_v3` (`rng(1680)`).

| Zbiór | niepuste pojęcia nieliterałowe (z 23–24) | puste („martwe”) | \|TR\| | TR z węzłem nieliterałowym | klasy |
|---|---|---|---|---|---|
| dev 3T (29 światów) | **3,7** | **19,9** | **31** | 11,5 | 50 |
| dev 4T (11) | 6,2 | 17,0 | 89 | 58 | 84 |
| T1 (5 praw) | 19–23 | 0–3 | 48–90 | 39–72 | 36–51 |
| T1-4 (5 praw) | 14–20 | 3–9 | 52–111 | 30–73 | 54–88 |

- **WYNIK:** hipoteza się potwierdza. W dev 3T węzły-prawa są prawie wszystkie martwe: puste w świecie, a więc
  izolowane, bez krawędzi wychodzących. Graf to niemal sam podgraf literałów z ~31 krawędziami TR. Luka
  heurystyka → wyrocznia wynosi tam tylko **0,39–0,42**, wobec 1,7–5,3 w T1. Przy tak małym suficie +0,03 to
  „≈ 0” w jednostkach bezwzględnych i 7% w ułamku.
- **WNIOSKOWANIE:** zysk w T1 bierze się z obecności żywych węzłów-praw. To one tworzą głęboki porządek, w którym
  out(b) odróżnia krótkie krawędzie od długich. Dev 4T (6 żywych węzłów, TR 89) jest bliższy T1 i tam reguła
  dawała +0,45 luki, co zgadza się z kierunkiem wyniku walidacji.
- **WYNIK (proceduralny):** to samo przesunięcie rozkładu recenzja LMM v3 opisała już jako ustalenie A
  i zaleciła osobny zbiór dev („pełny rząd 3, wykluczone tylko magmy S-0”). Plan heurystyki użył mimo to
  starego zbioru i przewidział T1 ≈ 0 na podstawie środowiska, o którym było wiadomo, że jest niereprezentatywne.
  Wynik wyszedł korzystnie, ale **predykcja z dev była z góry mało warta**. Ten sam błąd przy kolejnej regule
  może dać wynik w przeciwną stronę.

---

## 5. Czy x(xy)=xy w T1-4 wskazuje na systematyczną słabość?

- **WYNIK:** słabość jest powtarzalna: walidacja −1,04 [−1,52, −0,57], replikacja −1,64 [−1,98, −1,31],
  stałe okno −1,54. Dotyczy tempa. Pokrycie końcowe przy d1+50 jest u G **wyższe** (+1,40 [+0,78, +2,00]).
  Krzywa: po 10 wywołaniach snu G ma przyrost 4,4, a heurystyka 6,8. G dogania ją ok. 40. wywołania
  i kończy wyżej (28,1 wobec 26,7).
- **WYNIK:** w pierwszym śnie G budzi w tym świecie tylko **33% prawdziwych** kandydatur (heurystyka 71%,
  wyrocznia 100%). Wśród nich jest 7% śmiałych, więc fałszywe pochodzą głównie z powtórki. To świat
  z najdłuższym dniem 1 (d1 = 109), dużą pulą (111) i 9 martwymi węzłami. Wsparcie jest tu najlepszym znanym
  sygnałem prawdziwości, a G używa go tylko do rozstrzygania remisów.
- **HIPOTEZA:** systematyczna słabość reguły polega na tym, że **ignoruje dowody prawdziwości**. Tam, gdzie pula
  zawiera dużo fałszywych kandydatur z wysokim out(·) (słabo potwierdzonych przesłanek), G marnuje pierwsze wywołania
  na obalenia. Kontrprzykłady z tych obaleń przycinają potem pulę, co tłumaczy lepszy koniec. Wariant `ob`
  ogranicza szkodę o połowę, co wskazuje na człon out(a), który nagradza silne, rzadko obserwowane przesłanki.
  Hipoteza nie jest sprawdzona wprost i **nie wolno jej teraz poprawiać na prawach walidacyjnych**.
- **SPEKULACJA:** naturalna poprawka to połączenie struktury i prawdziwości (np. out(b) + λ·wsparcie). Taką regułę
  trzeba wybrać na nowym, reprezentatywnym zbiorze dev (§4), nie na tych 5 prawach.

---

## 6. Tabela ustaleń

| # | Ustalenie | Klasyfikacja |
|---|---|---|
| 1 | Kolejność commitów, sha planu, ziarna 1640–1679 i wspólne czuwanie 1 są zgodne z planem. Werdykt jest poprawnie wyliczony. | WYNIK |
| 2 | Kodu analizy cech (1610–1613) nie ma w repo. Ułamek luki to iloraz bez CI, liczony na różnych oknach. | WYNIK (usterki drobne) |
| 3 | Kryterium główne i T1 replikują się na 1680–1719. | WYNIK |
| 4 | Zysk jest odporny na zmianę okna (`b = min` wobec stałego d1+50). | WYNIK |
| 5 | W 4–5/10 światów zysk to wyłącznie tempo, a pokrycie końcowe jest równe. | WYNIK |
| 6 | Deduplikacja nic nie wnosi. | WYNIK NEGATYWNY (dla składnika) |
| 7 | Sygnał niesie out(b). out(a) ≈ 0. Odwrócona reguła szkodzi wszędzie. | WYNIK |
| 8 | T1-4 elastyczna „wygrywa” tylko dzięki karze i tie-breakowi, więc jest krucha. | WYNIK |
| 9 | Ułamek luki 1,0 w T1 (yx)x=y jest zawyżony. Na nowych ziarnach wynosi 0,73 i wyrocznia jest istotnie lepsza. | WYNIK |
| 10 | Dev 3T ma martwe węzły-prawa (3,7 żywych wobec 19–23 w T1) i bardzo małą lukę (0,4). | WYNIK |
| 11 | Martwe węzły i mała luka wyjaśniają „≈ 0 w dev, duży zysk w T1”. | WNIOSKOWANIE |
| 12 | x(xy)=xy w T1-4: powtarzalnie gorsze tempo przy lepszym końcu. G budzi tam 33% prawdziwych. | WYNIK |
| 13 | Przyczyna 12: reguła ignoruje sygnał prawdziwości, głównie przez człon out(a). | HIPOTEZA |
| 14 | Przenośność na słowniki inne niż `literaly` i na S-0. | HIPOTEZA (niesprawdzone) |
| 15 | Inspiracja reguły wiedzą o T1 z czasu LMM. | SPEKULACJA (ryzyko niskie) |

---

## 7. Rekomendacja

### 7.1 Czy uczynić regułę domyślną intuicją rdzenia?

**Tak, warunkowo.** W obecnym zakresie (słownik `literaly`, T1/T1-4, protokół S-1b, prawa spoza S-0) reguła jest
lepsza od `HeurystykaOgolnosci` w 9/10 światów, a wynik replikuje się na niezależnych ziarnach. Warunki:

1. **Nie zmieniać po cichu** domyślnej w `petla.uruchom` (`intuicja or HeurystykaOgolnosci()`). Wcześniejsze
   wyniki S-0/S-1/S-1b są zdefiniowane względem starej heurystyki. Nową regułę wprowadzić jako jawną stałą
   (np. `INTUICJA_DOMYSLNA`), a starą zostawić jako nazwane ramię bazowe w każdym kolejnym eksperymencie.
2. **Zamrozić regułę bez zmian** (`oa+ob+kara`, `dedup=True`), łącznie z bezczynną deduplikacją i kruchym
   tie-breakiem. Każda „poprawka” (np. samo `ob`, usunięcie deduplikacji, dodanie wsparcia) to nowa reguła wybrana
   po obejrzeniu walidacji i wymaga nowego cyklu dev → walidacja.
3. **Opisywać zysk uczciwie:** „szybciej dochodzi do pokrycia TR (pole), w części światów do wyższego końcowego
   pokrycia”, a nie „znajduje więcej struktury”. Słabość w T1-4 x(xy)=xy podawać jawnie.
4. Ogólne twierdzenie („lepsza intuicja rdzenia”) dopiero po teście na S-0 (§7.2).

### 7.2 Test na S-0 (ziarna 600–679) z prerejestracją

Prawa S-0 (idempotentna, komutatywna, x(xy)=y, łączna, medialna) nie były używane przy wyborze tej reguły.
W S-1b (ziarna 800–879) wszystkie 5 były ważne w T1 i T1-4, a bramka wyroczni przeszła 5/5. Test jest więc
wykonalny. Propozycja prerejestracji (zamrozić **przed** uruchomieniem, commit z sha `heurystyki.py`, `petla.py`,
`fazy.py`, `s1b.py`):

- **Ramiona:** `losowa`, `heurystyka`, `heur_grafu` (dokładnie `HeurystykaGrafu("oa+ob+kara")`), `wyrocznia_pokrycia`.
  Opcjonalnie, wyłącznie jako **eksploracja oznaczona z góry**: `ob` (out(b) − 3·[śmiałe]), bez wpływu na werdykt.
- **Protokół:** S-1b bez zmian (`BUDZET_DNIA=300`, `BUDZET_SNU=50`, `CEX=1`, `literaly`), ziarna **600–679** (80),
  jedno uruchomienie, odmowa przy brudnym drzewie.
- **Warunki ważności:** sen w ≥ 90% ziaren. Bramka: `wyrocznia_pokrycia − heurystyka` z dolną CI > 0 w ≥ 3/5 praw
  ważnych na świat. Bez bramki wynik w danym świecie jest NIEINFORMATYWNY.
- **Kryterium główne (każdy świat osobno, oba zapisane z góry):** `heur_grafu − heurystyka`, M1 (pole, `b = min`
  parami), dolna CI > 0 w ≥ 3/5 → WYNIK. Górna CI < 0 w ≥ 3/5 → WYNIK NEGATYWNY (szkodzi). Inaczej bez
  rozstrzygnięcia. Regułę „domyślna intuicja rdzenia” utrzymać tylko wtedy, gdy w **żadnym** świecie nie wyjdzie
  „szkodzi”.
- **Raportowane obowiązkowo (bez wpływu na werdykt):** M1 na stałym oknie [d1, d1+50]; różnica pokrycia końcowego
  przy d1+50, żeby oddzielić tempo od końca; ułamek luki z CI z bootstrapu ilorazu na wspólnym oknie; trafność
  i odsetek TR w 1. śnie; liczba praw z istotnie ujemnym wynikiem (zapowiedziane jako sygnał słabości typu x(xy)=xy).
- **Moc:** na 40 ziarnach efekty 0,15–4,4 jednostki były wykrywalne. 80 ziaren wystarcza z zapasem. Ryzyko:
  x(xy)=y jest dualne do (yx)x=y (mały TR, wczesne wyczerpanie puli), więc spodziewać się tam małej luki
  i dużego szumu ilorazu.
- **Zakaz:** po teście S-0 nie strojenia wzoru na S-0. Ziarna 600–679 są po nim zużyte.

### 7.3 Dalej (poza S-0)

Zanim powstanie kolejna reguła (np. struktura + wsparcie), zbudować zbiór dev **bez martwych węzłów-praw**,
zgodnie z zaleceniem 5 z recenzji LMM v3: pełny rząd 3 i 4, wykluczone tylko magmy S-0, albo losowe prawa
w roli pojęć-praw. Obecny zbiór `swiaty_v3` systematycznie przewiduje ≈ 0 tam, gdzie T1 daje duże efekty.
