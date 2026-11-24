# LMM v3: niezależna, krytyczna recenzja wyniku walidacji

Recenzent: niezależny agent (hostile review), 24.11. Przedmiot: `PLAN_LMM_V3.md` (fc3b3fd), trening (`lmm_trening.main_v3`, `wyniki/lmm_trening_v3.json`, wagi w 077062a),
walidacja w pętli `wyniki/lmm_walidacja_w_petli_v3.json` (commit cfe7936). Nie zmieniałem kodu ani danych. Własne diagnostyki liczyłem na
**ziarnach 1560–1599** (40 ziaren, te same 5 praw, T1 i T1-4, ramiona: losowa, heurystyka, lmm, lmm_bez_grafu, obie wyrocznie). Te ziarna
są teraz **zużyte** (diagnostyka recenzenta). Ziaren 600–679 nie ruszałem. Skrypty: katalog roboczy recenzenta (poza repo), opis metod niżej.

Etykiety: **WYNIK** (bezpośrednio zmierzone), **WYNIK NEGATYWNY**, **WNIOSKOWANIE** (wynika z wyników przy jawnych założeniach),
**HIPOTEZA** (spójna z danymi, ale nieprzetestowana wprost), **SPEKULACJA** (słabe oparcie).

---

## 1. Werdykt i zgodność z planem

### 1.1 Werdykt: NIE PRZESZŁA. Potwierdzam (WYNIK NEGATYWNY)

Reguła z sekcji 4 planu: dolna granica 95% CI(LMM − heurystyka) > 0 w ≥ 3/5 ważnych praw **w obu** światach.

| Świat | prawa ważne | dolna > 0 | istotnie gorszy (górna < 0) |
|---|---|---|---|
| T1 | 5/5 | **0/5** | 4/5 (lewa i prawa samodystr., x(xy)=xy, (yx)x=y) |
| T1-4 | 5/5 | **1/5** (prawa samodystr., +1,02 [0,53; 1,52]) | 3/5 (elastyczna, x(xy)=xy, (yx)x=y) |

- Twój odczyt liczb jest poprawny. Dwa przypadki leżą na granicy i warto o tym napisać: T1 x(xy)=xy ma górną granicę −0,0024 (ledwo „istotnie gorszy”), T1-4 lewa samodystr. ma górną +0,030 (ledwo „nieistotny”).
- Pole `G` jest liczone regułą kategorii z S-1b („lepsza / pomijalna / nierozstrzygnięta”), a nie dosłownie regułą z sekcji 4. Tutaj obie dają ten sam skutek: 0/5 i 1/5 < 3/5, więc NIE PRZESZŁA, a etykieta w `G` brzmi „WYNIK NEGATYWNY”. W raporcie trzeba podać werdykt według sekcji 4, a `G` tylko jako opis.
- Bramka jest spełniona: wyrocznia pokrycia − heurystyka ma dolną granicę > 0 we wszystkich 10 parach. Test jest więc informatywny, a porażka nie wynika z braku luki.
- **Pominąłeś coś istotnego: LMM jest istotnie gorszy od *losowego* wyboru w 4/10 par** (T1 lewa −1,94, T1 prawa −0,84, T1-4 x(xy)=xy −0,94, T1-4 (yx)x=y −0,68). Tego nie da się zbyć słowem „pomijalny”: intuicja w tych światach szkodzi.
- **Replikacja na ziarnach 1560–1599 (WYNIK):** LMM − heurystyka wychodzi istotnie ujemne w 4/5 T1 i 4/5 T1-4, dodatnie w żadnej parze (T1-4 prawa samodystr. +0,58 [−0,10; 1,20]). Wynik negatywny jest stabilny względem ziaren.

### 1.2 Zgodność kodu z planem (WYNIK, z jednym zastrzeżeniem)

| Punkt planu | Stan | Uwagi |
|---|---|---|
| Kolejność commitów: plan → wagi → walidacja | OK | fc3b3fd (16:18) → 077062a (16:57) → plik walidacji 17:18, commit cfe7936. Hash wag w JSON walidacji = hash z raportu treningu (c09b8e80…, 373a22af…). |
| Lista światów zamrożona | OK | sha256 `swiaty_v3.json` zgodny z planem; 323 światy (230 × 3T, 93 × 4T); wszystkie prawa pochodzą z `losuj_prawa(2000, 31337)`; min \|W\| = 20, min \|TR\| = 18. **Skryptu, który przefiltrował 2000 praw do 323, nie ma w repo**: listę da się sprawdzić, ale nie da się jej odtworzyć. Drobny brak. |
| Podział światów 275/48, ziarno 77, bez części wspólnej | OK | **Zastrzeżenie:** 20 z 48 odłożonych światów ma to samo prawo co któryś świat treningowy, tylko na innym uniwersum (3T ↔ 4T). „Odłożone światy” nie są więc w całości „nowymi prawami”. Sprawdziłem, czy to zawyża AUC: na odłożonych światach z prawem obecnym w treningu AUC prawdziwości = 0,916, a z prawem nowym = 0,913 (ziarna 1560–1561). **W praktyce zawyżenia nie ma.** |
| Ziarna 1500–1507 (trening), 1520–1559 (walidacja) | OK | `SEEDS_V3`, `SEEDS_WALID["v3"]`. |
| Brak magm praw wykluczonych | OK | `zbuduj_swiat` dla 3T/4T odejmuje magmy wszystkich 10 praw z `WYKLUCZONE` (S-0 + walidacyjne) dla **każdego** świata, nie tylko dla próbki z testu. Do tego `assert` na nazwach. Test sprawdza co 25. świat, ale maska działa w kodzie zawsze. |
| Brak wycieku praw walidacyjnych do treningu i wyboru epoki | OK | Wybór epoki (v3: epoka 6, ablacja: epoka 3) tylko po stracie na odłożonych światach. `main_v3`, w odróżnieniu od `main` (v2), nie liczy niczego na prawach walidacyjnych. |
| Architektura i hiperparametry bez zmian | OK | Konfiguracja d=64, L=4, 10 epok, LR 1e-3 → 1e-5, ziarno 2024. |
| Walidacja: jedno uruchomienie, bez nadpisywania | OK | Strażnik `wyj.exists()`. `walidacja()` nie sprawdza czystości drzewa ani hasha wag (robi to tylko `main`), ale hash jest zapisany w wyniku i się zgadza. |

**Uwaga metodologiczna (WNIOSKOWANIE):** te same 5 praw walidacyjnych służyło już do oceny v0, v1 i v2, a projekt v3 powstał po obejrzeniu porażki v2 właśnie na nich. Nie są to więc prawa „dziewicze” dla badacza, tylko dla modelu. Przy wyniku negatywnym nie ma to znaczenia. Przy przyszłym wyniku pozytywnym trzeba będzie to uwzględnić.

---

## 2. Czy „rozjazd celu” wyjaśnia porażkę?

Twoja hipoteza: model uczy się prawdziwości, a pokrycie wymaga nowych krawędzi TR; etykieta 0,5 dla „prawdziwa poza TR” nagradza trywialne prawdy.

### 2.1 Co ją wspiera

1. **Sama trafność daje niewiele pokrycia (WYNIK, ziarna 1560–1599).** Wyrocznia trafności (100% prawdziwych przeczuć) wypada względem heurystyki tak:
   - T1: +2,57, +1,01, +0,91, +2,15, −0,05 (ostatnie nieistotne);
   - T1-4: +1,04, +0,24 (nieistotne), +4,87, +3,90, +0,32.

   Wyrocznia pokrycia (najpierw TR) daje w tych samych parach +0,9 do +10,9. Idealna trafność odzyskuje więc tylko około **−3% do 60% luki** heurystyka → wyrocznia pokrycia (T1: 0,50 / 0,22 / 0,17 / 0,51 / −0,03; T1-4: 0,47 / 0,08 / 0,45 / 0,60 / 0,37). Model uczony prawdziwości ma sufit na poziomie wyroczni trafności, a ten sufit jest niski. To najmocniejszy argument za Twoją hipotezą. **WNIOSKOWANIE:** nawet doskonały v3 dałby w części praw efekt poniżej progu 0,25 luki.
2. **Wśród prawdziwych kandydatur LMM na prawach walidacyjnych woli krawędzie spoza TR niż krawędzie TR (WYNIK).** AUC „TR wśród prawdziwych” na puli 1. snu wynosi dla LMM:
   - T1: 0,58 / 0,53 / 0,51 / **0,39** / 0,58;
   - T1-4: **0,27** / 0,50 / **0,44** / **0,34** / **0,39**.

   Heurystyka ma w tych parach 0,44–0,68. Model jest więc gorszy od heurystyki właśnie w tym rozróżnieniu, które decyduje o pokryciu.
3. **Nawet w rozkładzie treningowym to rozróżnienie jest słabe (WYNIK).** Na odłożonych światach v3 AUC „TR wśród prawdziwych” = 0,66 (heurystyka 0,48–0,56), przy AUC prawdziwości 0,91. Etykieta 1 / 0,5 / 0 z BCE uczy przede wszystkim „prawda vs fałsz”, a rozróżnienie TR i nie-TR jest dla straty drugorzędne. Pasuje to do rozjazdu celu.

### 2.2 Co jej przeczy albo jej nie wystarcza

1. **Pierwszy sen sam w sobie nie przegrywa (WYNIK).** W 1. śnie stan jest identyczny we wszystkich ramionach. W T1 lewa samodystr. LMM wybiera średnio 4,0 krawędzi TR (heurystyka 3,3) i zyskuje +3,42 pokrycia TR po 1. przebudzeniu (heurystyka +3,10). Mimo to M1 wynosi −2,36. Podobnie T1 elastyczna (+4,03 vs +2,88) i T1 (yx)x=y (+2,52 vs +2,33). Strata powstaje **w późniejszych snach**: przyrost pokrycia na wywołanie w przebudzeniach 2+ w T1 lewa to 0,33 dla LMM i 0,45 dla heurystyki, w T1 prawa 0,39 vs 0,47. Sam „rozjazd celu” w punktowym wyborze tego nie tłumaczy. Potrzebny jest mechanizm dynamiczny (2.3).
2. **LMM bywa gorszy od losowego, choć jest trafniejszy.** Losowy wybór też nie celuje w TR. Gdyby chodziło tylko o „prawda zamiast TR”, LMM powinien być co najmniej na poziomie losowego. Jest istotnie gorszy w 4/10 par, więc działa coś więcej.
3. **Offline AUC 0,91 nie przenosi się na prawa walidacyjne (WYNIK).** Na pulach 1. snu w światach walidacyjnych AUC prawdziwości LMM wynosi 0,64–0,84 (T1: 0,77 / 0,64 / 0,67 / 0,72 / 0,83; T1-4: 0,84 / 0,80 / 0,73 / 0,62 / 0,78), a AUC TR (TR vs reszta) 0,54–0,75. „Nauczył się prawdziwości” jest prawdą w rozkładzie treningowym i tylko częściowo prawdą na walidacji. Wyższa trafność wybranych w pętli (np. 88% vs 68%) bierze się w dużej części z tego, że heurystyka karze śmiałe przeczucia i wybiera powtórki z dużym wsparciem (często fałszywe). LMM po prostu omija część fałszywek.

### 2.3 Alternatywy i współprzyczyny (ocenione)

| Alternatywa | Status | Dowód |
|---|---|---|
| **A. Przesunięcie rozkładu: węzły-prawa martwe w treningu** | **WYNIK** (przesunięcie jest), **HIPOTEZA** (że szkodzi) | Usunięcie magm 10 praw z 3T/4T sprawia, że węzły typu „prawo” są w treningu prawie zawsze puste: niepuste są średnio 2 z 17 (maks. 3). W światach walidacyjnych niepustych jest 10–16 z 16. Krawędzie TR z udziałem węzła-prawa to w treningu ~20% TR, a w T1 **60–66%**, w T1-4 20–69%. Wpływu na wybór nie potwierdziłem wprost: w T1 LMM wybiera krawędzie TR z prawem w podobnej proporcji jak heurystyka, w T1-4 elastyczna rzadziej (1,7 vs 3,2). To **konstrukcyjny skutek uboczny ochrony przed wyciekiem**, nie „3T vs pełne T1” jako takie. |
| **B. Przesunięcie rozmiaru i składu puli** | **WYNIK** (przesunięcie), **HIPOTEZA** (skutek) | Pula 1. snu w treningu (odłożone światy): średnio 37–52 kandydatury, TR 36–53%, fałszywe ~26–43%. W walidacji T1: ~58–104 kandydatury, z tego TR 16–31%. W T1 elastyczna fałszywe stanowią 74% puli. Inne proporcje klas i dłuższe listy psują kalibrację rankingu. |
| **C. Nadmiarowość top-k (duplikaty krawędzi TR)** | **WYNIK** w części praw | Wynik modelu jest liczony punktowo, bez uwzględniania nakładania się kandydatur. W T1-4 (yx)x=y LMM wybiera 5,1 kandydatur TR, ale tylko **1,8 różnych** par klas (heurystyka 5,0 → 2,8). W T1 (yx)x=y: 4,7 → 2,5, w T1 prawa: 2,5 → 1,9. Wyjaśnia to część strat w małych światach, ale nie T1-4 x(xy)=xy (bez duplikatów, a strata −4,0). |
| **D. Ekspozycja (stany poza rozkładem w snach 2+)** | **HIPOTEZA** (dobrze wsparta) | Migawki treningowe pochodzą wyłącznie z trajektorii prowadzonych przez ramię losowe i heurystykę (`Nagrywacz`). W walidacji od 2. snu LMM ocenia stany wytworzone przez siebie. Zgodnie z tym 1. sen jest neutralny albo lepszy, a sny 2+ wyraźnie gorsze (2.2.1). Nie przetestowałem tego wprost, np. trenując na trajektoriach LMM. |
| **E. Mniej kontrprzykładów (fałszywki jako źródło informacji)** | **SPEKULACJA** / częściowo obalona | LMM zbiera w oknie snu mniej nowych kontrprzykładów (T1 lewa 4,3 vs 5,4; T1-4 prawa 8,7 vs 17,2). Ale wyrocznia trafności zbiera ich jeszcze mniej i wygrywa z heurystyką, a w T1-4 prawa LMM ma najmniej kontrprzykładów i jedyny dodatni wynik. To nie jest główny mechanizm. |
| **F. Proporcja śmiałe/powtórka** | **WNIOSKOWANIE** | Heurystyka karze śmiałe przeczucia o −1, więc prawie ich nie wybiera (0–1,6 na sen). LMM wybiera 0–4 na sen. Wyrocznia pokrycia wybiera ich dużo (1,5–8,4), więc wybieranie śmiałych samo w sobie nie szkodzi. Różnica w trafności „88% vs 68%” w dużej mierze odzwierciedla tę karę, a nie „intuicję”. |
| **G. Kalibracja / skala ocen** | nieistotna dla mechanizmu | Sen używa tylko porządku ocen (top-10 + losowe remisy), więc kalibracja liczy się tylko jako ranking. Problemem jest ranking (2.1.2), nie skala. |

### 2.4 Graf vs ablacja

- **WYNIK:** LMM − ablacja ma dolną granicę > 0 w 7/10 par (T1: 4/5, T1-4: 3/5, przy czym T1-4 prawa samodystr. ledwo, +0,034). Istotnie ujemne jest w 2/10 (T1-4 lewa −1,01, T1-4 x(xy)=xy −0,48). Na ziarnach 1560–1599: 5/10 dodatnich, 1/10 ujemnych.
- **WNIOSKOWANIE:** „graf pomaga” znaczy tu „przepływ przez tokeny zależności poprawia model, który jako całość jest gorszy od heurystyki i miejscami od losowego”. Offline graf dodaje niewiele (AUC 0,91 vs 0,89). Nie wolno tego raportować jako dowodu, że graf niesie użyteczną intuicję: oba warianty są pod heurystyką. Pierwotna alternatywa planu („tokeny po dniu 1 nie niosą informacji ponad heurystykę”) **nie jest obalona**. Należy ją raportować jako niewyjaśnioną, a nie odrzuconą.

### 2.5 Ocena zbiorcza wyjaśnienia

„Rozjazd celu” to **częściowo poparta HIPOTEZA, nie wyjaśnienie**. Dobrze tłumaczy, dlaczego nawet idealny model prawdziwości dałby mały zysk (sufit wyroczni trafności) i dlaczego LMM źle rozróżnia TR i nie-TR. Nie tłumaczy natomiast, dlaczego LMM jest gorszy od losowego ani dlaczego wygrywa w 1. śnie, a przegrywa w kolejnych. Uczciwy opis: **co najmniej trzy współdziałające przyczyny**, czyli cel (prawda zamiast przyrostu pokrycia), przesunięcie rozkładu (martwe węzły-prawa, inny skład puli) i dynamika pętli (ekspozycja, duplikaty). Ich udziałów obecne dane nie rozdzielają.

---

## 3. Klasyfikacja ustaleń

| # | Ustalenie | Klasa |
|---|---|---|
| 1 | Kryterium sekcji 4 nie przeszło (0/5 T1, 1/5 T1-4); replikacja na 1560–1599 też ujemna | **WYNIK NEGATYWNY** |
| 2 | LMM istotnie gorszy od heurystyki w 4/5 T1 i 3/5 T1-4; gorszy od losowego w 4/10 | **WYNIK** |
| 3 | Kod zgodny z planem: kolejność, hashe, ziarna, wykluczenie magm, wybór epoki bez praw walidacyjnych | **WYNIK** |
| 4 | 20/48 odłożonych światów dzieli prawo z treningiem; AUC się przez to nie zawyża | **WYNIK** |
| 5 | Brak skryptu filtrującego 2000 → 323 prawa (lista sprawdzalna, ale nieodtwarzalna) | **WYNIK** (brak) |
| 6 | Wyrocznia trafności odzyskuje tylko −3% do 60% luki → sufit celu „prawda” | **WYNIK**; „v3 nie mógł przejść” → **WNIOSKOWANIE** |
| 7 | LMM na walidacji: AUC TR wśród prawdziwych 0,27–0,58 (gorzej niż heurystyka) | **WYNIK** |
| 8 | Offline 0,91 → na walidacji 0,64–0,84 (prawdziwość) | **WYNIK** |
| 9 | 1. sen LMM ≥ heurystyka w części praw, straty w snach 2+ | **WYNIK**; przyczyna „ekspozycja” → **HIPOTEZA** |
| 10 | Węzły-prawa martwe w treningu (2/17 niepustych vs 10–16/16); TR z prawami 20% vs 60–66% | **WYNIK**; że to szkodzi → **HIPOTEZA** |
| 11 | Duplikaty par klas w top-k | **WYNIK** (część praw) |
| 12 | Etykieta 0,5 nagradza trywialne prawdy | **HIPOTEZA** (spójna z #6, #7) |
| 13 | Graf poprawia względem ablacji w większości par | **WYNIK**, ale bez wartości dowodowej dla „intuicji z grafu” (#2) |
| 14 | Mniej kontrprzykładów jako przyczyna | **SPEKULACJA**, częściowo obalona |

---

## 4. Rekomendacja

**Nie robić testu S-0.** Ziarna 600–679 zostają nietknięte, zgodnie z planem. v3 zamknąć jako WYNIK NEGATYWNY.

Przeprojektowanie ma sens tylko jako nowa, wieloczynnikowa iteracja z nowym planem przed treningiem. Sugerowana kolejność:

1. **Najpierw tanie interwencje bez treningu.** (a) Deduplikacja top-k po parach klas (wybór zachłanny, jedna kandydatura na parę) dla *wszystkich* ramion, łącznie z heurystyką. Jeśli heurystyka z deduplikacją sama zamyka część luki, zmienia się punkt odniesienia. (b) Pomiar na *nowych* ziarnach, nie 1520–1599.
2. **Cel = przyrost pokrycia, ale jako ranking, nie BCE punktowe.** Najprościej: etykieta 1 tylko dla TR jeszcze niepokrytych, 0 dla pozostałych (bez 0,5). Lepiej: imitacja wyroczni pokrycia (strata listwise lub parami na kolejności wyroczni, z deduplikacją par klas). Ostrzeżenia:
   - przyrost pokrycia jest **funkcją zbioru** (zależy od innych wybranych i od stanu), a nie cechą pojedynczej krawędzi; etykieta punktowa znów rozjedzie się z M1;
   - etykieta TR zależy od klas prawdziwego świata, których model nie widzi; sygnał jest szumny, a sufit nieznany;
   - wyrocznia pokrycia też nie jest optimum M1 (ignoruje wartość kontrprzykładów), ale przy luce 1–11 punktów jest dobrym celem.
3. **Dane on-policy (DAgger):** zbierać migawki z trajektorii prowadzonych przez bieżący model i etykietować wyrocznią. Bez tego sny 2+ pozostaną poza rozkładem (#9).
4. **Usunąć martwe węzły-prawa:** zamiast tylko wycinać magmy 10 praw, podmienić w słowniku treningowym nazwane prawa na losowe prawa jako pojęcia typu „prawo”, aktywne na świecie. Wtedy typ węzła „prawo” będzie w treningu niosił informację. Uwaga: to zmiana danych *i* słownika naraz.
5. **Konflikt z zasadą „jedna zmiana naraz”:** zmiana samego celu przy zostawionym przesunięciu rozkładu może dać fałszywy negatyw, a zmiana obu naraz uniemożliwi atrybucję. Proponuję w planie układ 2 × 2 (cel × dane) oceniany **offline na zbiorze deweloperskim**, np. losowe prawa na pełnym rzędzie 3 z wykluczeniem tylko magm praw S-0. Taki zbiór wymaga osobnego ustalenia, czy magmy praw walidacyjnych mogą w nim być. Mierzyć AUC TR wśród prawdziwych, liczbę różnych TR@10 i przyrost pokrycia w 1. śnie. Dopiero zwycięzcę puścić raz na walidację w pętli, na nowym zakresie ziaren (np. 1700–1739), z kryterium jak w sekcji 4.
6. **Ostrzeżenie o proxy:** przyrost pokrycia w 1. śnie **nie przewiduje** M1 (T1 lewa: lepszy 1. sen, M1 −2,4). Każde proxy offline trzeba skalibrować względem M1, zanim posłuży do wyboru modelu.
7. **Zatrzymanie:** jeśli kolejna iteracja nie zbliży się nawet do wyroczni trafności, uznać, że tokeny zależności po dniu 1 nie niosą informacji ponad heurystykę wsparcia (alternatywa z sekcji 1 planu), i zamknąć wątek LMM-jako-intuicja.

---

## Metody diagnostyk recenzenta (dla odtworzenia)

- Pętla jak w `s1lmm.zbierz` (protokół S-1b: dzień 1 do 300, sen 50, `cex_cap = 1`, słownik „literały”), ziarna 1560–1599, cztery procesy po 10 ziaren (około 5 min każdy).
- Owinięty `petla.czuwanie` zapisywał (wywołania, pokrycie TR, liczbę kontrprzykładów) po każdym przebudzeniu. Owinięta intuicja zapisywała pulę i oceny każdego snu.
- Etykieta kandydatury: TR / prawdziwa poza TR / fałszywa, liczona względem `sw.TR` i `sw.cls` świata.
- M1 liczone funkcjami `s1b.roznice` i `s0.ci95` bez zmian.
- AUC funkcją `lmm_trening.auc`.
- Analiza odłożonych światów: `lmm_trening.zbierz` na 48 odłożonych światach, ziarna 1560–1561, z wagami v3.
