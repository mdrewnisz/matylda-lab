# Recenzja po wyniku: HEUR4 (heurystyka grafu ze wsparciem, rząd 4)

Recenzent niezależny, tryb krytyczny. Przedmiot: `PREREJESTRACJA_HEUR4.md` (zamrożona w `f30184c`), `matylda_rdzen/heur4_walidacja.py`,
`matylda_rdzen/heurystyki4.py`, wynik `wyniki/heur4_walidacja.json` (commit 078ede0, w JSON `commit = f30184c`).
Nie uruchamiałem ponownie `heur4_walidacja` i niczego nie nadpisałem. Moje diagnostyki: ziarna **1886–1899** (14), protokół S-1b
(dzień ≤ 300, sen 50), skrypty w scratchpadzie recenzenta (`diag.py`, `mech.py`, `an.py`; nie wchodzą do repo). Łącznie ok. 8 min na 4 rdzeniach.

Skróty: G = heur_grafu (`HeurystykaGrafu("oa+ob+kara")`), GW = heur_grafu_wsp (λ = 1), H = stara heurystyka (`HeurystykaOgolnosci`),
W = wyrocznia_pokrycia (`IntuicjaWyroczniaPokrycia`), M1 = pole pod krzywą pokrycia TR po dniu 1 do min wywołań pary.

## 0. Streszczenie

1. Werdykt runnera **„NIEINFORMATYWNY w rzędzie 4; T1: nierozstrzygnięta”** wynika poprawnie z §5 (kolejność B1). Integralność w porządku.
2. Bramka nie przeszła **nie dlatego, że nie ma miejsca na poprawę ponad G**, tylko dlatego, że W jest źle określonym sufitem.
   Mechanizm (WYNIK diagnostyczny): W daje najwyższą ocenę każdej prawdziwej krawędzi, której para **klas świata** leży w TR. Pokrycie liczy się jednak
   na **reprezentantach** klas w domknięciu wiedzy badacza. Krawędź a′⇒b′ między nie-reprezentantami nic nie daje, dopóki badacz nie zna równoważności
   a′⇔a i b′⇔b. Te krawędzie (wewnątrz klasy) W ocenia na 1, więc ich prawie nie budzi. Na prawach walidacyjnych rzędu 4 od 41% do 54% sprawdzeń W ze snu
   to prawdziwe krawędzie „TR” z zerowym przyrostem pokrycia.
3. Wyrocznia z patrzeniem w przód (zachłanna sekwencyjnie w paczce k = 10, kryterium: przyrost pokrycia TR liczony tak jak `sw.pokrycie`) bije G
   istotnie w **10/10** komórek walidacyjnych i **20/20** światów deweloperskich. Miejsce na poprawę ponad G jest więc duże: od +1,0 do +9,0 krawędzi TR (M1).
4. Wcześniejsze **bramki** (S-1b: W − L, S-0 heur: W − H, LMM v3: W − H) nie są podważone, bo tam W przechodziła z zapasem. Podważone są wszystkie
   **ułamki luki / „% efektu wyroczni”** oraz plan LMM, by uczyć model imitowania W.
5. G − H > 0 w 10/10 komórkach (dolna CI ≥ 0,36): wolno to raportować jako **prerejestrowaną opisową replikację kierunku na 5 nowych prawach**.
   To nie jest kryterium i nie jest 10 niezależnych replikacji.
6. Rekomendacja: domyślna intuicja (G) zostaje. GW nie zastępuje G. Przed następnym testem w rzędzie 4 trzeba wymienić bramkę na wyrocznię z przyrostem pokrycia.

## 1. Werdykt względem §5 (zadanie 1)

Integralność (WYNIK): sha256 `heurystyki4.py` = `dcb0a4b2…`, `heurystyki.py` = `bbbf3a71…`, `PREREJESTRACJA_HEUR4.md` = `b81c9067…`.
Wszystkie trzy zgadzają się z runnerem, z JSON i z wersją w `f30184c`. `git diff f30184c 078ede0` dotyka tylko `wyniki/heur4_walidacja.json`.
Ważność: 10/10 par (pula 1. snu 100%, dzień 1 nigdy na limicie 300).

| Świat | n | gorsza (górna CI < 0) | bramka W − G (dolna > 0) | lepsza (dolna > 0) | ścieżka §5 | kategoria |
|---|---|---|---|---|---|---|
| T1-4 | 5 | 1 (x(xx)=y(yy): −0,06 [−0,13; −0,01]) | **1/5** (tylko x(xx)=y(yy)) | 2 ((yz)y=(zy)z +1,17; y(x(xy))=y +0,50) | 1 < 3 → krok 3: 1 < 3 | **nieinformatywny** |
| T1 | 5 | 0 | 3/5 | 1 (x(x(yx))=x +0,40) | krok 2 nie; krok 3: 3 ≥ 3; krok 4: 1 < 3 | **nierozstrzygnięta** |

Werdykt runnera jest poprawny (WYNIK). Uwagi:

- „Nierozstrzygnięta” w T1 nie jest „gorsza”. Szkoda w rzędzie 3 nie została wykryta, a dzięki B1 test był na nią czuły. To realny zysk z recenzji przed.
- W T1-4 GW jest istotnie gorsza w 1/5 praw, ale efekt jest bardzo mały (−0,06 krawędzi TR). W 2/5 jest lepsza, a w 2/5 nie ma różnicy. To nie wystarcza
  ani do „lepsza”, ani do „gorsza”, **nawet gdyby bramka przeszła**.
- Kontrfaktycznie (WNIOSKOWANIE, nie do podmiany werdyktu): przy bramce, która by przeszła, T1-4 dałby „nierozstrzygnięta”, czyli WYNIK NEGATYWNY
  (brak przewagi). Decyzja praktyczna jest więc taka sama: GW nie zastępuje G. Werdykt formalny pozostaje **NIEINFORMATYWNY**.
- Ułamki luki w JSON są ujemne (np. −0,22, −0,07), bo mianownik W − G < 0. Nie mają żadnej interpretacji i nie należy ich raportować liczbowo.

## 2. Dlaczego prosta heurystyka bije „wyrocznię pokrycia” (zadanie 2)

### 2.1 Definicja

`IntuicjaWyroczniaPokrycia.ocen`: 0 = fałszywa, 2 = prawdziwa i `(sw.cls[a], sw.cls[b]) ∈ sw.TR`, 1 = pozostałe prawdziwe.
Wyrocznia nie deduplikuje i nie ma rozstrzygania remisów (decyduje losowy `tie` w `SenPelny`). Nie patrzy też na to, co badacz już wie.
Pokrycie (`Swiat.pokrycie`) to liczba par TR `(x, y)` (reprezentantów klas świata), dla których `R[x, y]` zachodzi w domknięciu **znanych prawdziwych**
krawędzi. Krawędź między nie-reprezentantami liczy się dopiero wtedy, gdy domknięcie zawiera też równoważności łączące ją z reprezentantami.

### 2.2 Pomiar (WYNIK diagnostyczny, ziarna 1886–1889, 4 prawa walidacyjne, rząd 4)

Każde sprawdzenie ze snu sklasyfikowałem według: prawda/fałsz, para klas świata w TR / wewnątrz klasy / poza TR, końce są reprezentantami lub nie, przyrost pokrycia.

| Prawo (rząd 4) | W: prawdziwe „TR”, nie-repy, zysk = 0 | W: sprawdzenia wewnątrz klasy | G: prawdziwe „TR”, nie-repy, zysk = 0 | G: sprawdzenia wewnątrz klasy |
|---|---|---|---|---|
| y(x(xy))=y | **107 / 200** | 0 | 17 / 200 | 28 |
| (yz)y=(zy)z | **83 / 169** | 0 | 15 / 169 | 14 |
| x(x(yx))=x | **100 / 200** | 0 | 23 / 200 | 30 |
| x(xx)=y(yy) | 12 / 78 | 24 | 11 / 77 | 24 |

Mechanizm (WYNIK dla tych przebiegów, WNIOSKOWANIE jako ogólne wyjaśnienie): W marnuje około połowy budżetu snu na krawędzie, które w klasach świata są
„krawędziami TR”, ale przy obecnej wiedzy badacza nie dokładają nic do pokrycia. Robi tak, bo pomija równoważności (ocena 1 < 2). G nie wie nic o świecie,
ale preferuje klasy o dużym stopniu wyjściowym. Dzięki temu budzi także krawędzie wewnątrz klas, które same mają zysk 0, ale „odblokowują” późniejsze krawędzie.
To rozstrzyga otwartą kwestię z `S0_HEUR_RECENZJA_PO.md` §2.4 („G uczy się równoważności… nie sprawdzałem”).

Odpowiedzi na hipotezy z polecenia:
- „W wybiera krawędzie TR, które potem i tak wynikają”: **nie to jest głównym mechanizmem**. Krawędzie wynikające są pomijane za darmo (`pomijaj_wynikajace`).
  Problemem są krawędzie, które **nie** dają pokrycia, bo brakuje równoważności.
- „Kara za brak kontrprzykładów”: **marginalna**. W tych prawach prawie wszystkie sprawdzenia ze snu są prawdziwe dla obu ramion. G ma od 0 do 23 fałszywych
  na prawo (4 ziarna), W od 0 do 22. Najwięcej jest ich w x(xx)=y(yy), czyli w jedynym prawie, gdzie W > G.
- „Różnica w wywołaniach / b = min”: **nie**. Oba ramiona zużywają pełne 50 wywołań snu, więc b = d1 + 50 dla obu.
- Brak deduplikacji: **częściowo**. Wariant W + dedup po klasach badacza + remisy według G (`wyr_dedup`) zmniejsza stratę, ale jej nie usuwa
  (tabela w §4: walidacja średnio −1,20 → +0,32, a w 4/10 komórek nadal istotnie < G).

### 2.3 Dlaczego w dewelopmencie W > G, a w walidacji nie

Na 20 światach deweloperskich (`heur4_dev.swiaty_dev(20)`, ziarna 1886–1899) W > G istotnie w 18/20, a W < G w 2/20. To zgadza się z „92%” z recenzji przed.
Na prawach walidacyjnych W > G tylko w 4/10 komórek (z ziaren 1886–1899; replikuje znaki JSON we wszystkich 10 komórkach).
Prawa walidacyjne są więc pod tym względem nietypowe (WYNIK). Dlaczego, nie ustaliłem. Duże |TR| (82–134) i liczne klasy nietrywialne (17–19 nazw w y(x(xy))=y
i x(x(yx))=x) pasują do obrazu, ale (yz)y=(zy)z ma tylko 6 takich nazw i W − G = −4,9 (HIPOTEZA: liczy się liczba par TR dotykających klas nietrywialnych,
a nie liczba tych klas). Szacunek mocy z recenzji przed zakładał, że bramka przejdzie, i to założenie zawiodło.

### 2.4 Co to znaczy dla wcześniejszych wyników

| Wynik | Co opierało się na W | Ocena |
|---|---|---|
| S-1b: „heurystyka lepsza od losowej”, bramka W − L 5/5 + 5/5 | bramka | **nie podważona** (WNIOSKOWANIE). Bramka mówi tylko, że wybór ma znaczenie, a W > L z dużym zapasem |
| S-1b pkt 2: „7–38% / 18–26% efektu wyroczni”, δ „pomijalności” | ułamek / δ z W | **podważone jako miara sufitu.** Prawdziwy sufit jest wyżej, więc te ułamki są *zawyżone* jako „% możliwej poprawy”. Kierunek wniosku („efekt mały”) raczej się wzmacnia, ale liczby nie mają tej interpretacji |
| S-1b pkt 6–7 (40% luki, ranking przez całą pulę) | luka do W | HIPOTEZA/SPEKULACJA do przeformułowania względem nowego sufitu |
| S-0 heur: „G lepsza od H”, bramka W − H 10/10 | bramka | **nie podważona**. Ułamek > 1 jest już wyjaśniony mechanizmem z §2.2 |
| HEUR_GRAFU_RAPORT: kolumna „ułamek luki do wyroczni” | ułamek | nie czytać jako % do optimum (to już było zalecone, teraz wiadomo dlaczego) |
| LMM v3: bramka W − H 10/10; „wyrocznia trafności odzyskuje −3%…60% luki do W: cel prawdziwość ma niski sufit” | bramka; mianownik | bramka nie podważona. Teza o „niskim suficie trafności” jest **osłabiona**: mianownik jest zły, a część luki W − trafność to pewnie właśnie równoważności (HIPOTEZA) |
| LMM v3, plan: „cel = ranking imitujący wyrocznię pokrycia” | cel uczenia | **podważony** (WNIOSKOWANIE). Imitacja W uczyłaby pomijania równoważności i budzenia bezużytecznych krawędzi między nie-reprezentantami. Celem powinna być wyrocznia z przyrostem (§4) |
| HEUR4: bramka 1/5 | bramka W − G | „nieinformatywny” jest formalnie poprawny, ale **nie znaczy „brak miejsca na poprawę”** |

## 3. G − H 10/10 jako replikacja (zadanie 3)

Dane (JSON, M1): T1: +0,70; +2,27; +1,54; +7,93; +1,86. T1-4: +0,52; +6,88; +1,11; +4,65; +1,20. Wszystkie dolne CI > 0, najmniejsza to 0,36.
Na stałym oknie wynik jest ten sam (10/10 > 0). Na pokryciu końcowym w T1-4 (z(zx))x=x wynosi 0,00, a x(xx)=y(yy) +0,02 [0,00; 0,05], czyli przewaga G
w tych prawach jest w tempie, nie w wyniku końcowym. Moje ziarna 1886–1899 na tych samych prawach: H − G < 0 w 10/10, istotnie w 8/10
(n.s. tylko (yz)y=(zy)z w obu rzędach). Na 20 prawach deweloperskich G > H istotnie w 13/20, w 0/20 gorzej.

Ocena (WNIOSKOWANIE): można to raportować jako **„prerejestrowana opisowa replikacja kierunku G > H na 5 nowych prawach, w obu rzędach”**, z zastrzeżeniami:
- §5 wymienia ten kontrast w „zawsze raportujemy”, a nie w kryteriach. Status: WYNIK opisowy, nie WYNIK testu.
- Jednostką jest prawo, a nie komórka. Te same 5 praw w dwóch rzędach to nie 10 niezależnych replikacji. CI są po ziarnach przy ustalonym prawie
  i nie uogólniają się na populację praw.
- Prawa przeszły ten sam filtr co dev (≥ 20 magm, |TR| ≥ 15) i są wolne od nakładania się ze zbiorami użytymi wcześniej (Jaccard < 0,5, bez izomorfizmu).
  Uogólnienie dotyczy więc tej klasy światów.
- Wolno napisać „G > H potwierdzone w rzędzie 4 na nowych prawach”. Nie wolno napisać „przewaga G w rzędzie 4 przestała być krucha”: w S-0 kruchość dotyczyła
  innego zbioru praw, a wielkości są tu bardzo zróżnicowane (0,5–6,9).

## 4. Lepsza bramka / sufit (zadanie 4)

Zbudowałem (w scratchpadzie, bez zmian w repo) trzy warianty wyroczni. Wszystkie mają tę samą znajomość świata co W:
- `wyr_dedup`: W + deduplikacja par klas badacza + remisy według oceny G;
- `wyr_tr` (**proponowana bramka**): zachłanna sekwencyjnie w paczce k = 10. Z prawdziwych kandydatur wybiera tę o największym przyroście pokrycia TR
  (dokładnie ta miara co `Swiat.pokrycie`, domknięcie aktualizowane przyrostowo `R | R[:,a]⊗R[b,:]`). Dodaje ją hipotetycznie i powtarza.
  Remisy (w tym zysk 0) rozstrzyga według G. Fałszywe idą na koniec;
- `wyr_dom`: to samo, ale maksymalizuje przyrost liczby par w domknięciu przechodnim.

Różnica M1 względem G, ziarna 1886–1899 (WYNIK diagnostyczny, nieprerejestrowany):

| Zbiór | W − G | wyr_dedup − G | **wyr_tr − G** | wyr_dom − G |
|---|---|---|---|---|
| Dev, 20 światów rzędu 4: średnia; istotnie > / < G | +1,18; 18 / 2 | +1,31; 18 / 1 | **+2,11; 20 / 0** | +1,12; 17 / 2 |
| Walidacja, 10 komórek: średnia; istotnie > / < G | −1,20; 4 / 5 | +0,32; 4 / 4 | **+5,05; 10 / 0** | +2,05; 8 / 0 |
| T1-4 per prawo (wyr_tr − G) | | | +1,01; +8,98; +6,19; +4,53; +2,05 | |
| Odsetek sprawdzeń po d1 bez przyrostu pokrycia (walidacja) | 0,54 | 0,50 | **0,29** | 0,30 (G: 0,43) |

Wnioski:
- (WYNIK) Wyrocznia z przyrostem pokrycia bije G wszędzie i z dużym zapasem. Miejsce na poprawę ponad G w rzędzie 4 jest duże, także w prawach,
  na których bramka W − G zawiodła (x(x(yx))=x: +9,0; y(x(xy))=y: +4,5).
- (WNIOSKOWANIE) `wyr_tr` też nie jest optimum (jest zachłanna na jeden krok, nie modeluje przyszłych pul snu ani kontrprzykładów). Jest jednak lepszym
  **dolnym oszacowaniem sufitu** i spójnym z miarą wynikową. Maksymalizacja domknięcia (`wyr_dom`) jest gorsza, bo nagradza pary spoza TR.
- Propozycja do następnych prerejestracji: bramka = `wyr_tr − G` (lub − ramię bazowe), dolna CI > 0. Ułamek luki liczyć tylko względem `wyr_tr`,
  na stałym oknie, z CI bootstrapu ilorazu. Opisywać go jako „część luki do zachłannej wyroczni przyrostu”, nigdy jako „% do optimum”.
  Kod wyroczni zamrozić hashem tak jak heurystyki. Nie podmieniać bramki w HEUR4 post hoc.
- (HIPOTEZA) Z `wyr_tr` da się zrobić heurystykę bez wyroczni: przyrost pokrycia liczony na **znanym** porządku badacza
  (preferować równoważności z klasami o dużym out i krawędzie między reprezentantami klas badacza). To naturalny następny kandydat zamiast dalszego strojenia λ.

## 5. Klasyfikacja ustaleń (zadanie 5)

| # | Ustalenie | Status |
|---|---|---|
| 1 | Werdykt „NIEINFORMATYWNY w rzędzie 4; T1: nierozstrzygnięta” wynika poprawnie z §5 (B1); integralność OK | **WYNIK** (prerejestrowany) |
| 2 | GW nie wykazała przewagi nad G w rzędzie 4 (2 lepsze, 1 gorsza o −0,06, 2 ≈ 0) ani w T1 (1/5) | **WYNIK NEGATYWNY** (słaby dowód braku efektu; moc ~0,6) |
| 3 | GW nie szkodzi w rzędzie 3 (gorsza 0/5, z bramką rozdzieloną od szkody) | WYNIK |
| 4 | W < G istotnie w 4/5 praw T1-4 i 2/5 T1; replikuje się na ziarnach 1886–1899 | WYNIK |
| 5 | Mechanizm: W marnuje 41–54% sprawdzeń snu na prawdziwe krawędzie „TR” między nie-reprezentantami (zysk 0), bo nie budzi równoważności | WYNIK (diagnostyka 4 praw × 4 ziarna) + WNIOSKOWANIE (ogólność) |
| 6 | Deduplikacja wyjaśnia tylko część straty W | WYNIK (diagnostyka) |
| 7 | Wyrocznia z przyrostem pokrycia bije G w 10/10 komórek walidacyjnych i 20/20 światów dev | WYNIK (diagnostyka, nieprerejestrowana) |
| 8 | „Nieinformatywny” tutaj ≠ „brak miejsca na poprawę”; przy dobrej bramce byłoby „nierozstrzygnięta” | WNIOSKOWANIE (kontrfaktyczne, nie zmienia werdyktu) |
| 9 | Bramki S-1b, S-0 heur, LMM v3 pozostają ważne; ułamki luki / „% efektu wyroczni” oraz teza o niskim suficie trafności są podważone | WNIOSKOWANIE |
| 10 | Plan LMM „imitować wyrocznię pokrycia” uczyłby złej strategii | WNIOSKOWANIE |
| 11 | G − H > 0 10/10: opisowa replikacja kierunku na 5 nowych prawach | WYNIK (opisowy, nie kryterium) |
| 12 | Nietypowość praw walidacyjnych wynika z liczby par TR przy klasach nietrywialnych | HIPOTEZA |
| 13 | Heurystyka „przyrostu pokrycia na znanym porządku” zamknie dużą część luki do `wyr_tr` | HIPOTEZA |
| 14 | Wybór λ = 2 zamiast 1 zmieniłby wynik | SPEKULACJA (brak danych; dev nie odróżniał λ) |

## 6. Rekomendacja (zadanie 6)

1. **Domyślna intuicja zostaje: G = `HeurystykaGrafu("oa+ob+kara")`.** GW nie spełniła warunku zastąpienia (§5: WYNIK w T1-4). Werdykt formalny to NIEINFORMATYWNY,
   ale WNIOSKOWANIE z §1 daje tę samą decyzję. Nie wracać do λ.
2. W raporcie HEUR4 napisać wprost, że bramka zawiodła, bo W nie jest sufitem (mechanizm z §2.2), a nie dlatego, że G osiągnęła sufit.
   Ułamków luki z tego testu nie podawać.
3. G − H podać jako opisową replikację (sformułowanie z §3).
4. Zanim powstanie kolejna prerejestracja w rzędzie 4: dodać do `intuicja.py` (jako nowe ramię kalibracyjne, bez ruszania W, którego używały wcześniejsze testy)
   wyrocznię przyrostu pokrycia, zamrozić ją hashem, a w dewelopmencie (ziarna spoza 1780–1899) sprawdzić, czy bramka przechodzi na typowych światach.
5. Kierunek merytoryczny (HIPOTEZA 13): heurystyka bez wyroczni, która ocenia przyrost pokrycia na znanym porządku i premiuje równoważności.
   Rozwijać ją na prawach dev, a testować na nowych prawach z bramką `wyr_tr`.
6. Dla programu LMM: zmienić cel imitacji z W na wyrocznię przyrostu. Przeliczyć sufit „wyroczni trafności” względem nowego mianownika, zanim teza o
   „niskim suficie trafności” trafi do wniosków.
7. Dopisek do korekty raportów S-1b i LMM v3 (erraty, bez zmiany werdyktów): ułamki i „% efektu wyroczni” odnoszą się do zachłannej wyroczni bez równoważności.
   Nie są to odsetki sufitu.

Ziarna zużyte przez tę recenzję: 1886–1899 (wszystkie).
