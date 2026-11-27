# Recenzja przed zamrożeniem: ROZMIAR3 (rząd 3 według rozmiaru świata)

Niezależny recenzent (hostile review), nie autor. Przedmiot: `PREREJESTRACJA_ROZMIAR3.md` (SZKIC, commit 4cd1ad3), `matylda_rdzen/rozmiar3_walidacja.py`,
`matylda_rdzen/rozmiar3_wybor_praw.py`, `wyniki/rozmiar3_prawa.json`. Kontekst: `wyniki/PRZYROST_RAPORT.md`, `wyniki/PRZYROST_RECENZJA_PO.md`,
`PREREJESTRACJA_PRZYROST.md`, `matylda_rdzen/przyrost_walidacja.py`, `heur4_walidacja.kategoria`, `s1b.roznice` i `s1b.waznosc`.

Skrypty i surowe wyjścia recenzji są poza repo, w `scratchpad/recenzja_rozmiar3/`:
- `moc.py`, `moc_rows.json`: moc dla pojedynczych praw z danych pilota i dev;
- `sym.py`, `sym.out`: symulacja werdyktu;
- `zakaz.py`, `zakaz.out`: kompletność listy zakazanej;
- `proxy.py`, `proxy.json`, `proxy.out`: co badacz widzi z rozmiaru świata.

Nowe przebiegi pętli puściłem **wyłącznie na ziarnach 2070–2079** (pula recenzji przed, od teraz zużyta), **wyłącznie na 10 prawach pilota i 40 prawach dev rzędu 3** (`swiaty_dev3(40)`) i tylko w ramieniu `heur_grafu`.
Na 10 prawach z `rozmiar3_prawa.json` liczyłem tylko statystyki świata, bez pętli: rozmiar, |TR|, liczbę zmiennych i działań oraz odtworzenie wyboru.

**Werdykt ogólny:** projekt jest sensowny i dobrze zakotwiczony w recenzji PRZYROST. Wybór praw jest poprawny i odtwarzalny bit w bit.
Przed zamrożeniem trzeba jednak poprawić **4 rzeczy blokujące**:
- jedna kontrola integralności jest pusta;
- werdykt w kodzie przeczy tekstowi §4 przy wyniku, który jest najbardziej prawdopodobny;
- etykieta „NEGATYWNY” stoi przy wyniku nierozstrzygniętym;
- przy 5 prawach na przedział jest ok. 15% ryzyka, że test w ogóle nie będzie informatywny, a da się to tanio usunąć.

---

## 1. Blokujące

### B1. Kontrola statusu „ZAMROŻONA” jest pusta
`main()` sprawdza tylko `"ZAMROŻONA" not in prer`. Słowo „ZAMROŻONA” **już jest** w szkicu: w linii 4 („…commit tego pliku ze statusem „ZAMROŻONA”…”) i w §6.
Sprawdziłem: `'ZAMROŻONA' in prer == True`, choć linia statusu brzmi `Status: **SZKIC**`. Runner przepuściłby więc prerejestrację w stanie SZKIC.
Zabezpieczają ją wtedy tylko RUNNER_SHA256 i `SHA`. Te dwa da się wpisać bez zmiany statusu.

**Poprawka:** sprawdzać linię statusu, np. `re.search(r"^Status: \*\*ZAMROŻONA\*\*", prer, re.M)`, i odmawiać, gdy w pliku występuje `Status: **SZKIC**`.
Dodać test w `tests/test_rdzen.py` na obecnym szkicu, sprawdzający, że kontrola statusu odrzuca SZKIC (wyodrębnić ją do funkcji, aby dało się ją przetestować bez uruchamiania przebiegów).

### B2. Werdykt w kodzie przeczy §4, gdy oba przedziały są „lepsza”, a to jest najbardziej prawdopodobny wynik
§4 mówi: „Jeśli DUŻE też »lepsza«, to wynik przemawia za heurystyką przyrostu w całym rzędzie 3, **a nie za moderacją**”.
`werdykt()` nie patrzy na `kd`. Przy `km = "lepsza"` i dolnej CI(I) > 0 zwraca „WYNIK: … **moderacja rozmiarem**”, także gdy `kd = "lepsza"`.
Do tego definicja H_mod („lepsza w małych **i** efekt większy niż w dużych”) jest w takim układzie spełniona dosłownie. Tekst, H_mod i kod mówią więc trzy różne rzeczy.

To nie jest przypadek brzegowy. Symulacja (`sym.py`, §5) z danych pilota i walidacji PRZYROST daje P(MAŁE lepsza i DUŻE lepsza) ≈ 0,46, a P(obie lepsza i dolna CI(I) > 0) ≈ 0,42.
To najczęstszy pojedynczy wynik.

**Poprawka:** zapisać pełną tabelę (km × kd × CI(I)) i zakodować ją jawnie. Proponuję:
- km = lepsza, kd ∈ {nierozstrzygnięta, gorsza}, dolna CI(I) > 0 → „lepsza w małych; moderacja rozmiarem” (H_mod potwierdzona);
- km = lepsza, kd = lepsza, dolna CI(I) > 0 → „lepsza w obu przedziałach; efekt większy w małych” (H_mod formalnie spełniona, ale skutkiem jest propozycja dla całego rzędu 3, nie reguła zależna od rozmiaru);
- km = lepsza, kd = lepsza, CI(I) ∋ 0 → „lepsza w obu; moderacja niewykazana”;
- km = lepsza, CI(I) ∋ 0, kd ≠ lepsza → „lepsza w małych; moderacja niewykazana”;
- km = lepsza, kd = nieinformatywny → wolno mówić tylko o „lepsza w małych”. Interakcję raportować opisowo, a nie jako „moderację”: przy nieudanej bramce w DUŻYCH mały efekt tam może wynikać z niewrażliwości testu.

Skutki z §4 muszą się odwoływać do tych samych etykiet. Werdykt powinien zwracać osobne pole `kategoria_G` (kod), a nie tylko napis.

### B3. „MAŁE nierozstrzygnięta → WYNIK NEGATYWNY” łamie konwencję programu
Recenzja po PRZYROST (§2, „Nie wolno”) ustaliła, że „nierozstrzygnięta” **nie jest** wynikiem negatywnym. Przykład: 2/5 lepsza, 0/5 gorsza, wszystkie średnie ≥ −0,11.
Szkic nazywa tę samą sytuację „WYNIK NEGATYWNY dla H_mod”. Przy 5 prawach i progu 3 wynik „nierozstrzygnięta” może oznaczać 2/5 istotnie lepsze i 3/5 dodatnie, ale nieistotne. Etykieta „negatywny” byłaby wtedy nadużyciem.

**Poprawka:** „H_mod NIEPOTWIERDZONA (małe: nierozstrzygnięta)”. „WYNIK NEGATYWNY” zostawić dla „gorsza”.
Ewentualnie, jeśli autor chce mocniejszej negacji, prerejestrować dodatkowo próg pomijalności, np. górna CI średniej po prawach w MAŁYCH < δ. Taki próg jest w s1b: `DELTA_UL`.

### B4. Przy n = 5 jedno-dwa nieważne prawa robią z MAŁYCH test nieinformatywny; brak reguły rezerwy
`kategoria` wymaga n ≥ 4 ważnych praw. Ważność to niepusta pula 1. snu w ≥ 90% ziaren. W małych światach pula bywa pusta częściej:
- w pilocie prawo 231 magm miało pulę w 6/10 ziaren;
- w dev rzędu 3 światy < 60 magm mają pulę w 30–90% ziaren (`proxy.out`, ziarna 2070–2079).

Symulacja (§5) daje **P(MAŁE nieinformatywny) ≈ 0,15** przy rozkładzie praw z klasy większych termów (pilot + walidacja) i ≈ 0,5 przy domieszce praw dev. Oszacowanie z domieszką dev jest pesymistyczne, bo wybrane małe światy mają |TR| 48–82, czyli więcej niż typowy mały świat dev.
Test może więc z sensownym prawdopodobieństwem spalić 3 000 przebiegów i pulę ziaren bez odpowiedzi.

Ważność nie zależy od ramienia. Pula 1. snu jest identyczna we wszystkich ramionach, bo dzień 1 jest wspólny (`assert` w `roznice`, docstring `waznosc`).
Zastąpienie nieważnego prawa następnym z rezerwy nie niesie więc żadnej informacji o kontraście ramion.

**Poprawka (jedna z dwóch):**
- (a) prerejestrować po **2 prawa rezerwowe** w każdym przedziale, kolejne z generatora 9494 w tej samej regule, z listą i hashem w JSON. Reguła: nieważne prawo zastępuje pierwsze nieużyte prawo rezerwowe z tego przedziału. Kod musi to robić automatycznie, a raport podaje każdą zamianę;
- (b) podnieść liczbę praw do 7 na przedział (próg 60% → 5/7) i przyjąć wynikający z tego koszt.

Wariant (a) jest tańszy i zostawia definicję kategorii bez zmian.

---

## 2. Zalecane

**Z1. Skala interakcji.** I liczona jest w surowym M1. M1 to średnie pokrycie TR na wywołanie, w krawędziach TR, więc jego skala zależy od |TR| i od zapasu wyroczni.
- |TR| w DUŻYCH 71–90 (średnio 78), w MAŁYCH 48–82 (średnio 61).
- Zapas wyroczni `wyrocznia_przyrostu − graf` w dużych światach rzędu 3 to w danych 2,2–6,0, w małych 1,2–5,5.

Na surowej skali błąd działa raczej **przeciw** H_mod (konserwatywnie), ale „efekt większy” nie znaczy wtedy „większa część osiągalnego zysku”.
Zalecam pozostawić I na M1 jako rozstrzygające, ale prerejestrować i zawsze raportować dwie interakcje drugorzędne:
- na ułamku luki (stałe okno, jak w PRZYROST);
- na M1/|TR|.

Zalecam też zapis w §4, że rozstrzyga skala surowa.

**Z2. Wnioskowanie o I przy 5 prawach.** Bootstrap dwupoziomowy przy 5 prawach w grupie ma tylko 126 różnych multizbiorów praw, a percentylowe CI przy tak małym n zwykle za mało pokrywa.
Drugi poziom (ziarna) dodaje z kolei wariancję szumu, który już jest w średnich praw, więc częściowo to kompensuje. Netto pokrycie jest nieznane.
Zalecam opisowo (nie rozstrzygająco) **dokładny test permutacyjny** etykiet przedziałów na poziomie praw: C(10,5) = 252 podziały, I na średnich po prawach. Raportować p.
Funkcję `interakcja` sprawdziłem: robi to, co mówi tekst. Losuje ze zwracaniem prawa w przedziale, potem ziarna w każdym wylosowanym prawie, osobno dla obu grup, na sparowanych różnicach z `roznice`.
Estymator to różnica średnich ze średnich praw. Ziarno `12345` jest stałe. Błędów nie znalazłem.

**Z3. Konfundery: raportować, nie tylko wspomnieć.** Przedziały różnią się nie tylko rozmiarem:
- |TR|: średnio 61 wobec 78;
- liczba zmiennych: 3/5 praw z 3 zmiennymi w MAŁYCH wobec 2/5 w DUŻYCH;
- przede wszystkim mechanizm z recenzji PRZYROST: odsetek prawdziwych kandydatur w puli. W `proxy.out` (pilot + dev, ziarna 2070–2079) ma on ze rozmiarem świata korelację rang Spearmana **−0,81**: 0,34–1,00 w 20–300 wobec 0,16–0,42 w ≥ 500.

Test nie odróżni „rozmiaru” od „odsetka prawdy w puli”, i dobrze, że §2 to przyznaje.
Runner **nie zapisuje jednak składu puli** (`pula = bool(...)`), więc dekompozycji „prawda czy kolejność”, zaleconej w recenzji PRZYROST (§3.4), nie da się zrobić bez ponownego uruchomienia.
Zalecam zapisywać w `_komorka`, jak w `s1b.zbierz`:
- `pula` i `wybrane` jako listę (źródło, `prawdziwa`);
- liczbę znanych magm po dniu 1 (obserwacje ∪ kontrprzykłady).

Raport ma podać per prawo: odsetek prawdziwych w puli i znane/świat. Zalecam także zapisać per ziarno surowe różnice M1, nie tylko CI, żeby recenzja po nie musiała replikować.

**Z4. Zakres interpretacji.** Wylosowane MAŁE mają 67–146 magm, a nie 20–300. DUŻE mają 545–1516.
Wynik dotyczy zrealizowanego zakresu: w pilocie prawa 231 i 251 magm dały słabe efekty (−0,24 i +0,40). §4 powinien to zapisać z góry.
Luka 301–499 jest rozsądna, bo rozdziela przedziały wyraźnie i ułatwia kontrast. Ceną jest brak informacji, gdzie leży przejście. Raport nie może więc podawać progu.

**Z5. KOD a zależności.** Zamknięcie importów runnera (`ast`, rekursywnie) obejmuje moduły spoza `KOD`:
- `heurystyki4.py`: importowany na poziomie modułu przez `heur4_walidacja`, w tym teście nieużywany;
- `uniwersum4.py`, `uniwersum4t.py`: leniwie, tylko dla rzędu 4;
- `lmm_intuicja.py`, `lmm_bsd2_models.py`: leniwie, w `s1.intuicja`, tu nieużywane.

Na przebieg rzędu 3 nie wpływają, a świat rzędu 3 buduje się z 3^9 magm bez plików danych. Dla porządku warto dodać `heurystyki4.py`, bo jest wykonywany przy imporcie.
`rozmiar3_wybor_praw.py` i `przyrost_wybor_praw.py` są w `KOD`, choć runner ich nie wykonuje. Ich zależności nie są w `KOD`: `heur4_dev.py`, `przyrost_dev.py`, `przyrost_walidacja.py` (jej `PRAWA`), `lmm_trening.py` (`_L`, `_S`), `s1.PRAWA_MOCY`, `swiat.PRAWA_S0`, `dane/swiaty_v3.json`, `wyniki/przyrost_pilot_prawa.json`.
Nie jest to luka integralności, bo listę praw chroni bezpośrednio PRAWA_SHA256, a ja odtworzyłem JSON bit w bit (sha `99284c61…3651`).
To jednak luka audytowa: po zmianie którejś z tych zależności nie da się już pokazać, że lista wynika z reguły.
Zalecam albo dopisać te pliki do `KOD`, albo dodać test (pytest, oznaczony jako wolny, ok. 3 min), który odtwarza `rozmiar3_prawa.json` i porównuje sha.
Opcjonalnie: po `zbierz` sprawdzać, że `{m for m in sys.modules if m.startswith("matylda_rdzen.")}` ⊆ `KOD ∪ {runner, …}` z jawną listą wyjątków.

**Z6. Dodatkowe zabezpieczenia runnera (drobne).**
- Regex RUNNER_SHA256 bierze pierwsze trafienie w pliku. Lepiej wymagać dokładnie jednego (`len(re.findall(...)) == 1`).
- Zapisywać w wyniku wersje Pythona i numpy. Wynik jest deterministyczny przy danym środowisku, ale nie musi być między środowiskami.
- `git status --porcelain .` obejmuje tylko `rdzen/`. To wystarcza, bo runner nie czyta nic spoza niego.

**Z7. Skutki (§4) i dostępność rozmiaru.** Zdanie „badacz nie zna rozmiaru świata, zna tylko liczbę znanych magm” jest uczciwe i trzeba je zachować.
Rozmiar świata w rzędzie 3 jest obliczalny wprost: wystarczy przejrzeć 3^9 tabel. W modelu badacza byłaby to jednak informacja wyroczni, więc reguła domyślna nie może z niego korzystać.
Moja diagnostyka (`proxy.out`) pokazuje, że **widoczny sygnał istnieje, ale jest zgrubny**. Liczba znanych magm, czyli prawie wyłącznie liczba kontrprzykładów, bo obserwacji jest zawsze 20, rośnie z rozmiarem (Spearman 0,89):
- 20–46 w światach 20–300 magm;
- 45–51 w światach ≥ 500.

Przedziały nachodzą na siebie na granicy. Mierzyłem na końcu przebiegu, czyli po śnie, a nie po dniu 1.
Wniosek: ewentualna reguła zależna od rozmiaru wymaga osobnej walidacji jakiegoś proxy, np. kontrprzykładów po dniu 1 albo tempa nowych magm.
§4 powinien to zapisać jako warunek, obok „po replikacji”. Zalecam też, żeby runner zapisywał to proxy (Z3), bo wtedy ten test da pierwsze dane do takiej reguły.
Skutek „obie lepsza → propozycja domyślnej w rzędzie 3” jest uczciwy, ale lista praw ma celowo 50/50 małych i dużych i pomija 301–499, więc nie odzwierciedla naturalnego rozkładu.
Propozycja powinna o tym mówić i podawać też „gorsza” per prawo w DUŻYCH.

**Z8. Opis H_mod.** Pilot PRZYROST na tej samej klasie (ziarna 2000–2009) dał w małych światach 8/9 praw z przewagą, która przy 60 ziarnach byłaby istotna (§5).
Część „lepsza w małych” jest więc w dużej mierze replikacją. Nowa informacja leży w DUŻYCH i w I. To w porządku, ale warto to napisać w §1, żeby wynik „lepsza w małych” nie był w raporcie przedstawiany jako odkrycie.

---

## 3. Uwagi

- **Wybór praw** (`rozmiar3_wybor_praw.py`) jest poprawny:
  - pomija prawa z listy zakazanej po napisie;
  - filtr |TR| ≥ 15 i przedział rozmiaru działa przed Jaccardem;
  - Jaccard (świat i transpozycja, próg 0,5) liczony jest względem wszystkich zużytych światów rzędu 3 i wcześniej wybranych praw;
  - nadzbiór sprawdzany jest tylko względem praw testowanych, a lista testowanych obejmuje PRZYROST.

  Przekroczenie limitu w jednym przedziale nie dopisuje świata do `ref`, co jest poprawne. Odtworzenie: `main()` daje JSON identyczny z plikiem (sha zgodne).
- **Lista zakazana jest kompletna** względem wszystkiego, co repo przechowuje jako napis prawa. W `wyniki/*.json`, `wyniki/*.txt`, `dane/*.json` i `matylda_rdzen/*.py` jest 420 różnych praw, a spoza listy zakazanej jest tylko jedno (przykład w `prawa_losowe.py`), bez kolizji Jaccarda ≥ 0,5 z 10 nowymi prawami (`zakaz.out`).
  Wszystkie 5 praw walidacyjnych PRZYROST i 10 praw pilota są na liście. Ograniczenie: światy dev generowane w kodzie, a niezapisane jako napisy, wychwytuje tylko to, co odtwarzają `swiaty_dev(120)` i `swiaty_dev3(40)`.
- **Filtr tylko w rzędzie 3** jest uzasadniony, bo test dotyczy tylko rzędu 3. Uwaga: te prawa mogą się pokrywać ze zużytymi światami rzędu 4, więc **nie wolno** ich później użyć w teście rzędu 4 bez ponownego filtra. Warto dopisać to do §5 („zużyte”).
- „Izomorfizm nie jest sprawdzany” jest w rzędzie 3 bez znaczenia dla światów. Świat (wszystkie magmy 3-elementowe spełniające prawo) jest z definicji zamknięty na przenumerowanie elementów, więc prawa o izomorficznie „tym samym” świecie mają ten sam zbiór i Jaccard 1.
- `kategoria` przy n = 4 wymaga 3/4 (0,6·4 = 2,4). Raport powinien to podać, gdy n = 4.
- Kontrola PRAWA_SHA256 (`"PRAWA_SHA256: " + sha in prer`) jest szczelna. Hash w szkicu zgadza się z plikiem.
- Łańcuch hashy jest poprawny i nie ma cyklu: RUNNER_SHA256 w prerejestracji chroni runner, runner zawiera `SHA`, a `SHA` chroni `KOD`.
- Numeracja sekcji przeskakuje z §6 na §9. To kosmetyka, ale runner i tekst odwołują się do „§9”.
- `pytest`: przechodzi (34 testy). Brak testów dla `rozmiar3_walidacja` (`werdykt`, `interakcja`, kontrola statusu). Zalecam choć test tabeli werdyktu po B2.
- Uruchamiając `proxy.py`, przez chwilę zapisałem w `rdzen/` dwa pliki robocze recenzji (`proxy.json`, `moc_rows.json`). Przeniosłem je do scratchpadu, a `git status` jest czysty, poza tym plikiem.

---

## 4. Moc (pytanie 5)

**Per prawo** (`moc.py`). Przybliżenie normalne: P(dolna CI > 0 przy 60 ziarnach) = Φ(średnia/(sd/√60) − 1,96), z per-ziarnowych różnic `prz_m1 − grafu` z 10 ziaren.
- **Pilot, małe (63–251 magm, 9 praw):** P ≈ 1,00 dla 8/9. Wyjątek to prawo 231 magm: średnia −0,24, pula w 6/10 ziaren, więc byłoby nieważne.
- Walidacyjne 105 magm: +3,21 [2,81; 3,63].
- Dev rzędu 3 (inna klasa, ≤ 4 działania), 20–300 magm: przeważnie P ≈ 1. Kilka światów < 60 magm ma pulę < 0,9.
- **Duże (≥ 500):** pilot 1242: +0,50, P ≈ 1; walidacja: 1/4 istotnie (872), 854 na granicy (dolna −0,01); dev: 589 (P ≈ 1), 1590 (0,98), 2187 (0,90), 967 (0,24), 1736 (0,06), 1138 i 2005 istotnie ujemne lub ≈ 0.

**Symulacja werdyktu** (`sym.py`, 400 powtórzeń). Założenia:
- losuję po 5 praw na przedział ze zwracaniem z puli empirycznej;
- prawdziwą średnią prawa losuję z N(średnia, sd/√10);
- puste pule odwzorowuję zerami;
- ważność liczę jak w runnerze, bramkę przyjmuję jako zaliczoną, bo dotąd przechodziła 10/10;
- I liczę bootstrapem dwupoziomowym jak w runnerze (1000 prób).

| Pula praw | P(MAŁE lepsza) | P(MAŁE nieinf.) | P(DUŻE lepsza) | P(dolna CI(I) > 0) | P(MAŁE lepsza ∧ I > 0) | P(obie lepsza) | P(obie lepsza ∧ I > 0) |
|---|---|---|---|---|---|---|---|
| klasa większych termów (pilot 10 małych + 1 walid.; duże: 1 pilot + 4 walid.) | **0,85** | 0,15 | 0,54 | 0,94 | 0,81 | 0,46 | 0,42 |
| + prawa dev (41 małych, 12 dużych) | 0,49 | 0,51 | 0,46 | 0,70 | 0,37 | 0,22 | 0,15 |

Wnioski:
- (a) Przy ważnych prawach MAŁE prawie na pewno wyjdą „lepsza”. Moc dla tej części jest wysoka, a jedynym realnym ryzykiem jest nieinformatywność (B4).
- (b) Najbardziej prawdopodobny wynik to „obie lepsza i I > 0”, a dokładnie tu kod i tekst się rozjeżdżają (B2).
- (c) DUŻE są blisko połowy między „lepsza” a „nierozstrzygnięta”, więc rozstrzygnięcie między „moderacją” a „lepsza w całym rzędzie 3” zależy od 1–2 praw.

Ograniczenia: pula „dużych” z tej klasy ma tylko 5 praw. Pilot daje 10 ziaren na prawo. Symulacja jest diagnostyczna i nieprerejestrowana.

---

## 5. Klasyfikacja ustaleń

| Ustalenie | Klasa |
|---|---|
| Kontrola „ZAMROŻONA” przepuszcza szkic (słowo występuje w linii 4 i w §6) | WYNIK (sprawdzone na pliku) |
| `werdykt()` ignoruje `kd`; przy (lepsza, lepsza, I > 0) zwraca „moderacja”, wbrew §4 | WYNIK (z kodu) |
| „Nierozstrzygnięta → NEGATYWNY” jest niezgodne z konwencją z recenzji po PRZYROST | WNIOSKOWANIE |
| `interakcja` robi to, co opisuje tekst (prawa w grupie, potem ziarna; sparowane różnice) | WYNIK (z kodu) |
| `rozmiar3_prawa.json` odtwarza się z kodu bit w bit (sha 99284c61…) | WYNIK |
| Lista zakazana obejmuje 5 praw walidacyjnych i 10 praw pilota PRZYROST; brak kolizji z innymi prawami zapisanymi w repo | WYNIK |
| Zależności runnera spoza `KOD` (heurystyki4, uniwersum4/4t, lmm_*) nie wpływają na przebieg rzędu 3 | WNIOSKOWANIE (z kodu) |
| Zależności wyboru praw spoza `KOD` to luka audytowa, nie luka integralności | WNIOSKOWANIE |
| P(MAŁE lepsza) ≈ 0,85, P(MAŁE nieinf.) ≈ 0,15, P(obie lepsza ∧ I > 0) ≈ 0,42 | WYNIK diagnostyczny (symulacja z danych pilota i walidacji; nieprerejestrowany) |
| Odsetek prawdziwych w puli maleje z rozmiarem świata (ρ = −0,81); liczba znanych magm rośnie z rozmiarem (ρ = 0,89), ale przedziały nachodzą na siebie | WYNIK diagnostyczny (ziarna 2070–2079, pilot + dev, jedno ramię) |
| Test nie oddzieli rozmiaru od odsetka prawdy w puli ani od \|TR\| | WNIOSKOWANIE |
| Liczba znanych magm (kontrprzykładów) mogłaby posłużyć jako proxy rozmiaru dla reguły domyślnej | HIPOTEZA |
| Efekt w MAŁYCH dotyczy zrealizowanego zakresu 67–146 magm, nie całego 20–300 | WNIOSKOWANIE |
| Reguła zależna od rozmiaru dałaby zysk w praktyce | SPEKULACJA |

---

## Streszczenie

Szkic jest merytorycznie dobrze postawiony. Wybór praw jest poprawny, kompletny i odtwarzalny, a łańcuch hashy (runner → SHA → KOD, PRAWA_SHA256) jest szczelny, z jednym wyjątkiem.
Moc dla „lepsza w MAŁYCH” jest wysoka (≈ 0,85; ryzykiem jest głównie nieważność praw). Najbardziej prawdopodobny wynik to „lepsza w obu przedziałach, I > 0”.

**Blokujące:**
- **B1.** Kontrola statusu jest pusta: „ZAMROŻONA” już jest w tekście szkicu. Trzeba sprawdzać linię `Status: **ZAMROŻONA**` i dodać test.
- **B2.** `werdykt()` ignoruje kategorię DUŻE. Przy (lepsza, lepsza, I > 0) ogłasza „moderację”, wbrew §4, a to jest najczęstszy przewidywany wynik (≈ 0,42). Potrzebna jest pełna tabela km × kd × I w tekście i w kodzie, ze skutkami przypiętymi do etykiet.
- **B3.** „MAŁE nierozstrzygnięta → WYNIK NEGATYWNY” trzeba zmienić na „H_mod niepotwierdzona”, zgodnie z konwencją programu.
- **B4.** Przy 5 prawach ok. 15% szans na nieinformatywne MAŁE. Trzeba prerejestrować 2 prawa rezerwowe na przedział, z automatyczną zamianą nieważnych. Ważność nie zależy od ramienia, więc zamiana nie wprowadza obciążenia.

Najważniejsze zalecane: interakcje drugorzędne na ułamku luki i M1/|TR| (Z1); test permutacyjny I (Z2); zapis składu puli, znanych magm i surowych różnic per ziarno (Z3); zakres 67–146 w interpretacji (Z4); domknięcie `KOD` albo test odtworzenia listy (Z5); proxy rozmiaru jako warunek skutku (Z7).
