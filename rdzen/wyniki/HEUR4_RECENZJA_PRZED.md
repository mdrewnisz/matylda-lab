# Recenzja przed zamrożeniem: `PREREJESTRACJA_HEUR4.md` (niezależna, krytyczna)

Data: 27.11. Przedmiot: `PREREJESTRACJA_HEUR4.md` (projekt, commit 6006e76), `matylda_rdzen/heur4_walidacja.py`, `matylda_rdzen/heurystyki4.py`,
`matylda_rdzen/heur4_dev.py`, `wyniki/heur4_dev.json`, `wyniki/heur4_dev_potw.json`, `wyniki/heur4_wybor_praw_kod.py.txt`.
Kontekst: `PREREJESTRACJA_S0_HEUR.md`, `wyniki/S0_HEUR_RAPORT.md`, `wyniki/S0_HEUR_RECENZJA_PRZED.md`, `wyniki/S0_HEUR_RECENZJA_PO.md`,
`wyniki/s0_heur_wyniki.json`, `wyniki/heur_grafu_walidacja.json`, `matylda_rdzen/{heurystyki,fazy,pamiec,intuicja,s1,s1b,swiat,uniwersum4,lmm_trening}.py`, `dane/swiaty_v3.json`.

**Czego nie robiłem:** nie uruchamiałem `python -m matylda_rdzen.heur4_walidacja`. Nie użyłem ziaren 1820–1879 w żadnej formie.
Nie budowałem światów praw z `heur4_walidacja.PRAWA` i nie liczyłem na nich niczego. Jedyny kontakt z tymi prawami to lektura ich zapisu
oraz porównanie napisów (nazw) z listą `dane/swiaty_v3.json` (bez budowania światów).
**Czego użyłem:** (a) przeliczenia na opublikowanych JSON-ach (`heur4_dev*.json`, `s0_heur_wyniki.json`, `heur_grafu_walidacja.json`);
(b) struktura światów deweloperskich `heur4_dev.swiaty_dev(120)` na U4 (bez ziaren); (c) test dymny runnera: `heur4_walidacja.zbierz` +
`analiza` na 4 pierwszych prawach deweloperskich, **ziarna 1880–1885**, oba światy, 5 ramion (240 przebiegów); (d) wywołania `kategoria`
na danych syntetycznych. Skrypty w scratchpadzie sesji, poza repo. Jedyny zmieniony plik repo: ten.

Klasyfikacja: **WYNIK** (sprawdzone), **WNIOSKOWANIE**, **HIPOTEZA**, **SPEKULACJA**.
Skróty: G = `HeurystykaGrafu("oa+ob+kara")` (heur_grafu, domyślna), GW = `HeurystykaGrafuWsparcie(1)` (heur_grafu_wsp), H = stara heurystyka,
W = wyrocznia_pokrycia.

---

## 0. Werdykt w skrócie

Kod robi to, co mówi prerejestracja, w każdym punkcie formalnym: ramiona, ziarna, budżety, ważność, bramka, próg 60%, mapowanie werdyktu,
kontrasty opisowe, zabezpieczenia. Wariant jest dobrze zdefiniowany i nie widzi prawdy świata. Porównanie z G (a nie z H) jest właściwe.

Problemy są trzy i wszystkie dotyczą **projektu**, nie implementacji:

1. **Furtka w T1 (rząd 3).** Wykrycie szkody w rzędzie 3 przechodzi przez bramkę W − G. Na prawach S-0 w T1 wyrocznia nie była lepsza od G
   w 3/5 praw, więc bramka w T1 najpewniej nie przejdzie. Wtedy T1 = „nieinformatywny”, a to spełnia warunek „T1 nie gorsza”. Szkoda
   w rzędzie 3 staje się niewykrywalna akurat wtedy, gdy G jest już blisko wyroczni.
2. **Dobór praw nie jest w pełni rozłączny ani w pełni regułowy.** Reguła łapie dokładne duplikaty i duale poprawnie, ale (a) lewa alternatywność
   jest wstawiona ręcznie na początek listy kandydatów, (b) dwa prawa nie są „nowe” w programie (lewa alternat. to prawo treningowe LMM v1/v2;
   x(xx)=x jest w `dane/swiaty_v3.json`, czyli wśród światów, na których dobierano wzór G), (c) co najmniej 3 z 8 światów są nadzbiorami
   całego świata prawa S-0, w tym lewa alternat. ⊇ łączna — dokładnie przypadek, w którym G przegrała w rzędzie 4 i który zmotywował wariant.
3. **Moc umiarkowana:** z dewelopmentu P(„lepsza”) ≈ 0,45–0,75 przy 8 ważnych prawach (środek ≈ 0,6). Wynik „nierozstrzygnięta” ma więc
   ≈ 40% szans nawet wtedy, gdy wariant jest średnio lepszy. Prerejestracja powinna to powiedzieć wprost.

Do zamrożenia potrzeba **5 poprawek blokujących** (sekcja 7). Są tanie: żadna nie wymaga nowych przebiegów na ziarnach walidacyjnych.

---

## 1. Zgodność kodu z prerejestracją

| Punkt | Prerejestracja | Kod | Ocena |
|---|---|---|---|
| Ramiona | losowa, heurystyka, heur_grafu, heur_grafu_wsp, wyrocznia_pokrycia | `RAMIONA` identyczne; G = `HeurystykaGrafu("oa+ob+kara")`, GW = `HeurystykaGrafuWsparcie(LAMBDA=1.0)` | WYNIK: zgodne |
| Ziarna | 1820–1879 (60) | `SEEDS = range(1820, 1880)` | zgodne |
| Prawa | 8 praw z §3 | `PRAWA` = te same 8 napisów, w tej samej kolejności; rozłączne z `swiaty_dev(120)` po nazwie (asercja w teście dymnym) | zgodne |
| Światy, protokół | T1 (rz. 3), T1-4 (U4), dzień 1 do 300, sen 50 | `SWIATY`, `BUDZET_DNIA=300`, `BUDZET_SNU=50` z `s1b`; `SLOWNIK="literaly"`, `CEX=1` z `s1` | zgodne |
| Liczba przebiegów | 4 800 | 2 × 8 × 60 × 5 = 4 800 | zgodne |
| M1 | pole od d1 do b = min wywołań, bootstrap sparowany 95% | `s1b.roznice` (pole, b = min z pary, asercja wspólnego d1) + `s0.ci95` (10 000 prób, ziarno 12345) | zgodne; liczbę prób i ziarno bootstrapu warto wpisać do §5 (Z1) |
| Ważność | niepusta pula 1. snu w ≥ 90% ziaren | `s1b.waznosc` na ramieniu `losowa` (pula identyczna we wszystkich ramionach), `PROG_WAZNOSCI = 0.9` | zgodne |
| Bramka | W − G, dolna CI > 0 | `wyrocznia_pokrycia-heur_grafu`, `glo > 0` | zgodne (ale zob. §4.2 i B1) |
| Kategorie | n < 4 lub bramka < 60% n → X; lepsza / gorsza ≥ 60% n; inaczej N | `kategoria()`: `len(x) >= 0.6*n`, kolejność X → L → G → N | zgodne |
| Próg 60% | — | n = 4 → 3; 5 → 3; 6 → 4; 7 → 5; 8 → 5 (sprawdzone wywołaniami `kategoria`; 0,6·5 = 3,0 dokładnie w IEEE) | WYNIK: jednoznaczne, ale tabela powinna być w tekście (B5) |
| L i G naraz | niemożliwe | 60% + 60% > 100%, a listy są rozłączne (`lo > 0` wyklucza `hi < 0`) | zgodne |
| Werdykt | T1-4: L → WYNIK; G, N → WYNIK NEGATYWNY; X → NIEINFORMATYWNY; T1 wtórnie | słownik `g` + dopisek `; T1: …` i „(szkodzi w rzędzie 3)” | zgodne |
| Kontrasty opisowe | stałe okno [d1, d1+50], pokrycie końcowe, G − H, ułamek luki | `_okno`, `_koniec`, para `heur_grafu-heurystyka`, `ulamek_luki = m/g`; dodatkowo GW − H, GW − L | zgodne; ale liczone **tylko dla praw ważnych** (Z3) |
| Skutek („propozycja zastąpienia”) | WYNIK w T1-4 i T1 nie „gorsza” | poza kodem (decyzja) | zgodne; zob. B1 |

Test dymny (ziarna 1880–1885, 4 prawa deweloperskie, oba światy): `zbierz` i `analiza` przechodzą bez błędów, asercja wspólnego d1 nie pęka,
struktura JSON kompletna, werdykt generuje się poprawnie. Szczegóły w §8.

---

## 2. Zabezpieczenia

| Zabezpieczenie | Stan | Ocena |
|---|---|---|
| `H4_SHA = None` | `_sha(heurystyki4.py) != None` zawsze prawdziwe → runner odmawia, dopóki hash nie zostanie wpisany. Bezpieczny stan domyślny. | WYNIK: dobre |
| Hash w prerejestracji | §0 mówi „H4_SHA = sha256 heurystyki4.py”, ale sama wartość nie jest wpisana w tekst (w S-0 była). | B4 |
| Czyste drzewo | `git status --porcelain .` z `cwd=ROOT` (= `rdzen/`) obejmuje też pliki nieśledzone; `__pycache__/` jest w `.gitignore`. Uwaga: ta recenzja jest nieśledzona i zablokuje runner, dopóki nie zostanie zacommitowana — to pożądane. | dobre |
| Nadpisanie | odmowa, gdy `wyniki/heur4_walidacja.json` istnieje | dobre |
| Hash U4 | `uniwersum4.sha256(np.load(PLIK)) == U4_SHA` (uint8, jak w S-0b) | dobre |
| Hash G (linia odniesienia) | **brak.** GW dziedziczy po G ideę, a G jest ramieniem porównawczym; runner nie sprawdza `s0_heur.HEUR_SHA` dla `heurystyki.py`. | B4 |
| Hashe kodu | runner zapisuje tylko `commit` i `prerejestracja_sha256`; runner S-0 zapisywał `kod_sha256` 12 plików. §7 opiera się na `git diff`, więc to wystarcza formalnie, ale kopiowanie bloku `kod_sha256` z `s0_heur` kosztuje 1 linię. | Z2 |
| „Jedno uruchomienie” | nie do wymuszenia kodem (jak w S-0); przebieg deterministyczny, więc powtórka dałaby ten sam JSON | WNIOSKOWANIE: akceptowalne |
| Testy | w `tests/test_rdzen.py` nie ma żadnego testu dla `heurystyki4` ani `heur4_walidacja` (grep pusty) | Z4 |

---

## 3. Dobór praw walidacyjnych

### 3.1 Co reguła robi poprawnie

Klucz świata to zbiór tablic działania (bajty macierzy) w danym rzędzie, porównywany osobno w rzędzie 3 i 4; prawo odpada, gdy jego świat
**albo jego transpozycja** równa się którymkolwiek zakazanemu w **którymkolwiek** rzędzie. Zakazane: 5 praw S-0, 5 praw `PRAWA_MOCY`
(walidacja G i LMM), 120 praw deweloperskich `swiaty_dev(120)` (dokładnie te, na których badano GW: 60 dev + 60 potw), oraz wcześniej przyjęte
prawa zbioru. Reguła nie używa żadnej informacji o wyniku (tylko |świat| i |TR|). **WYNIK.**

**Izomorfizm / permutacja elementów (pytanie zlecającego).** Nie jest luką:
- W rzędzie 3 uniwersum to wszystkie 3^9 tablic. Klasa modeli dowolnego prawa jest zamknięta na permutację elementów, więc dwa prawa
  „równe z dokładnością do izomorfizmu” mają *ten sam* zbiór tablic i porównanie zbiorów je łapie. Jedyna dodatkowa symetria, która zmienia
  prawo, to anty-izomorfizm (dualność), a ten łapie transpozycja. **WNIOSKOWANIE (ścisłe).**
- Dwa różne prawa nie mogą mieć światów różniących się tylko permutacją elementów: świat jest wyznaczony przez prawo, a nie wybrany.
  Równoważność praw = równość klas modeli; reguła wymaga różnicy w obu rzędach, więc prawa równoważne na rzędzie 3 lub na próbce U4 odpadają.
- W rzędzie 4 transpozycja w kluczu jest praktycznie martwa: U4 nie jest zamknięte na transpozycję (próbki z nawrotami + 2 000 losowych),
  więc `At` prawie nigdy nie trafi. Dualność łapie jednak rząd 3 (pełne uniwersum), a reguła odrzuca przy trafieniu w dowolnym rzędzie.
  Tak odpadła prawa alternatywność. **WNIOSKOWANIE.**

### 3.2 Czego reguła nie łapie

**(a) Ręcznie nazwane kandydatki na początku listy.** `named = ['unipotentna xx=yy', 'lewa alternat. …', 'prawa alternat. …']` idą przed
losowymi prawami z `losuj_prawa(600, 9090)`. To trzy z czterech praw `lmm_trening._L`. Prerejestracja nie uzasadnia, dlaczego te trzy
i dlaczego przed losowymi. To stopień swobody badacza, który wpływa na skład zbioru (z 8 praw jedno jest „ręczne”). Nie wiadomo też,
czy ziarno 9090 było pierwszym i jedynym próbowanym. **WYNIK** (kod) + **WNIOSKOWANIE** (wpływ).

**(b) Prawa „nowe” tylko względem listy zakazanej, nie względem programu.**
- `lewa alternat. x(xy)=(xx)y` jest prawem treningowym LMM v1/v2 (`lmm_trening._L`; `PREREJESTRACJA_S1_LMM.md`, wiersz 32: „lewa i prawa alternatywność”).
  Na uniwersach 3T/4T, nie T1/U4, i bez ramienia G. **WYNIK.**
- `L:(x*(x*x))=x` występuje dosłownie w `dane/swiaty_v3.json` (`['L:(x*(x*x))=x', '3T', 2401, 35]` i `[…, '4T', 651, 76]`), czyli
  wśród światów, na których `heur_dev.py` wybrał wzór `oa+ob+kara` dla G (i trenowano LMM v3). **WYNIK** (porównanie napisów).
  Pozostałych 6 napisów w `swiaty_v3.json` nie ma; równoważności (różne napisy, ten sam świat) nie sprawdzałem, bo wymagałoby to budowy
  światów praw walidacyjnych.
- Wpływ: dla kontrastu GW − G to raczej faworyzuje **G** (ramię odniesienia było strojone na tym świecie), więc nie jest to wyciek na korzyść H.
  Ale §3 nazywa prawa „nowymi”, co jest nieprawdą dla 2/8. **WNIOSKOWANIE.**

**(c) Nadzbiory światów S-0 (bliskie duplikaty, nie duplikaty).** Reguła porównuje równość zbiorów. Implikacje algebraiczne (z samych praw,
bez obliczeń):
- łączność ⇒ lewa alternatywność (x(xy) = (xx)y), więc **W(łączna) ⊆ W(lewa alternat.)** w obu rzędach;
- idempotentność ⇒ x(xx) = x·x = x, więc **W(idempotentna) ⊆ W(x(xx)=x)**;
- idempotentność ⇒ x(xx) = xx, więc **W(idempotentna) ⊆ W(xx=x(xx))**.

To ma znaczenie z dwóch powodów:
1. **U4 jest zbudowane z próbek praw S-0** (`uniwersum4.py`: po 1 000 magm na prawo S-0 + 2 000 jednostajnie losowych). Na 120 światach
   deweloperskich mediana udziału magm spełniających jakieś prawo S-0 wynosi **1,00** (minimum 0,89; ≥ 0,9 w 99% światów); 4% światów dev
   zawiera cały świat któregoś prawa S-0, a co najmniej jeden świat dev ma Jaccard 1,00 ze światem S-0. **WYNIK** (prawa dev, U4).
   Światy T1-4 praw walidacyjnych są więc z konstrukcji wyciętymi kawałkami próbek S-0, a trzy z nich zawierają całą próbkę jednego prawa.
   Udział nadzbiorów S-0 w zbiorze walidacyjnym (≥ 3/8 ≈ 38%) jest wyraźnie wyższy niż w dev (4%). **WNIOSKOWANIE.**
2. **Lewa alternat. ⊇ łączna jest przypadkiem motywującym.** Wynik S-0 w T1-4 łącznej: G − H = −0,97 [−1,28; −0,67], W − G ≈ +6,8 —
   największa luka i porażka G, którą wsparcie (kryterium H) naprawia z konstrukcji. Prawo z tym podzbiorem zostało wstawione ręcznie
   po znanym wyniku S-0. Nie twierdzę, że celowo; twierdzę, że reguła doboru tego nie wyklucza, a prerejestracja tego nie ujawnia.
   **HIPOTEZA** (że wpływa na wynik): jeśli świat lewej alternat. w U4 jest zdominowany przez 1 000 łącznych próbek, to w tym prawie GW
   ma przewagę „pożyczoną” z S-0.

Ile z tego to problem: kryterium wymaga ≥ 5/8 praw, więc jedno prawo nie przesądza. Ale przy kategorii na granicy (jak S-0: dokładnie 3/5)
takie prawo może przesądzić. Stąd B2 i B3.

---

## 4. Wybór linii odniesienia i progi

### 4.1 GW − G zamiast GW − H: właściwe

G jest domyślną intuicją rdzenia od 3e46f5c. Pytanie decyzyjne brzmi „czy zastąpić domyślną”, więc kontrastem rozstrzygającym musi być GW − G.
Porównanie z H byłoby łatwiejsze (dev: G − H = −1,73 i −0,92 w rzędzie 4, czyli H jest tu silna) i nie odpowiadałoby na pytanie. G − H i GW − H
jako opisowe są dobrym uzupełnieniem: GW jest mieszanką G i kryterium H, więc warto pokazać, czy GW bije *obie* składowe. **WNIOSKOWANIE.**

Zalecenie (Z5): w raporcie pokazać też GW − max(G, H) per prawo (opisowo), bo „lepsza od G” w rzędzie 4, gdzie H > G, może znaczyć tylko
„mniej gorsza od H”.

### 4.2 Bramka W − G zamiast W − H

Sens bramki: „czy w ogóle jest miejsce na poprawę ponad G”. To logiczne dla T1-4: w dev W − G > 0 w 92% światów, bramka przechodzi
w symulacji mocy w 99% przypadków (§5). **WYNIK** (dev).

W T1 jest inaczej. Z `s0_heur_wyniki.json` (punktowo, M1): W − G w T1 = +1,53 (idemp.), −0,09 (komut.), −0,21 (x(xy)=y), −0,25 (łączna),
+2,10 (medialna) — bramka przeszłaby co najwyżej w 2/5 < 60%. Z `heur_grafu_walidacja.json`: T1 W − G = 4,25; 1,61; 1,88; 2,85; 0,00 → ≈ 4/5.
**WYNIK** (przeliczenie). Prawdopodobieństwo, że T1 wyjdzie „nieinformatywny”, jest więc znaczne (rzędu połowy, WNIOSKOWANIE).

Kod sprawdza bramkę **przed** „gorsza”: `if n < 4 or len(bramka) < 0.6*n: return "nieinformatywny"`. Gdy G jest już blisko lub powyżej W
(a to typowe w T1), GW może być istotnie gorsza od G we wszystkich prawach, a T1 i tak wyjdzie „nieinformatywny”. Prerejestracja (§5, „Skutek”)
traktuje to jako „T1 nie gorsza” i dopuszcza propozycję zastąpienia domyślnej. **To jest furtka** — B1.

Bramka ma sens dla *wykazania przewagi* (bez miejsca na poprawę „lepsza” jest niemożliwa), ale nie ma sensu dla *wykrycia szkody*:
szkoda względem G jest mierzalna niezależnie od tego, gdzie leży W.

### 4.3 Próg 60%

Jednoznaczny w kodzie (`>=`, zmiennoprzecinkowo bez niespodzianek dla n = 4…8). Prerejestracja powinna jednak podać tabelę n → wymagana liczba,
bo „60% n” czytane jako „> 60%” albo z zaokrągleniem w dół dałoby inne progi (np. n = 5 → 3 vs 4; n = 8 → 5 vs 4). Sugeruję zapis całkowitoliczbowy
`5·k ≥ 3·n` w kodzie (Z6) i tabelę w tekście (B5). Przy n = 8 próg 5/8 = 62,5% jest ostrzejszy niż S-0 (3/5 = 60%) — świadomie, i dobrze.

---

## 5. Moc przy 60 ziarnach (z dewelopmentu)

Metoda: dla każdego z 120 światów dev średnia i SD różnicy GW(λ=1) − G na 10 ziarnach (tak samo W − G). Symulacja: losuję n światów bez zwracania,
średnia z 60 ziaren ~ N(μ, SD/√60), prawo „lepsze”, gdy μ̂ − 1,96·SE > 0; bramka analogicznie; kategoria wg `kategoria()`. 20 000 powtórzeń.
Wariant „EB”: μ ściągnięte empirycznym Bayesem (τ ≈ 0,8) — koryguje to, że μ z 10 ziaren jest zaszumione. **WYNIK** (symulacja), z zastrzeżeniami niżej.

| zbiór dev | śr. GW − G | P(L), n = 8 | P(N), n = 8 | P(L), n = 6 | P(L), n = 5 | P(X) |
|---|---|---|---|---|---|---|
| dev (1800–1809) | +0,30 | 0,46 | 0,52 | 0,42–0,43 | 0,58 | ≤ 0,04 |
| potw (1810–1819) | +0,61 | 0,71–0,75 | 0,25–0,29 | 0,64–0,69 | 0,76–0,80 | ≤ 0,01 |
| oba (120) | +0,45 | 0,58–0,60 | 0,39–0,41 | 0,53–0,55 | 0,67–0,69 | ≤ 0,02 |

P(„gorsza”) ≈ 0 we wszystkich wariantach.

Wnioski:
- **Moc ≈ 0,6 (zakres 0,45–0,75).** Wąskim gardłem jest heterogeniczność między prawami (τ ≈ 0,8 przy średniej ≈ 0,45; w dev 18–23% światów
  ma GW < G), a nie liczba ziaren: więcej ziaren niewiele pomoże, więcej praw — trochę. **WNIOSKOWANIE.**
- Oszacowanie jest raczej optymistyczne: λ = 1 wybrano na tych danych (efekt zwycięzcy w zestawie dev; potw jest wolny od wyboru między λ,
  ale nie od wyboru wariantu), a dev używa b = min po *wszystkich* ramionach, runner — po parze. Z drugiej strony prawa walidacyjne
  zawierają nadzbiory S-0 (§3.2c), co może podnosić efekt. **SPEKULACJA** co do kierunku netto.
- Konsekwencja dla interpretacji: „nierozstrzygnięta → WYNIK NEGATYWNY (brak przewagi)” znaczy „nie wykazano przewagi wg kryterium”,
  nie „wariant nie pomaga”. Prerejestracja musi to powiedzieć, razem z liczbą ≈ 0,6 (B5).
- Zalecenie (Z7): opisowo (nie rozstrzygająco) raportować też średnią GW − G po prawach z bootstrapem po ziarnach i prawach — przy takiej
  heterogeniczności to najbardziej informatywna liczba.

---

## 6. Definicja λ·m·wsparcie/n

| Składnik | Źródło | Wyciek prawdy? |
|---|---|---|
| out(a), out(b) | `kons.macierz_zaleznosci.sum(1)`; konsolidacja z `p.prawdziwe` = implikacje **sprawdzone** w pamięci badacza (`pamiec.konsolidacja`) | nie |
| m | `len(kons.reprezentanci)` = liczba klas równoważności w tej samej konsolidacji (z ⊤) | nie |
| wsparcie | `Kandydat.wsparcie` = na ilu znanych magmach zachodzi przesłanka a, bez kontrprzykładu (`kandydaci_z_obserwacji`) | nie |
| n | `ctx.liczba_znanych_magm = len(znane)`, znane = obserwacje + kontrprzykłady (`SenPelny._znane`) | nie (kontrprzykłady przyszły z weryfikatora jawnie, jak dla G i H) |
| kara | −3 dla `sen:smiale`, jak w G | — |
| deduplikacja | najlepsza kandydatura na parę klas, reszta −1e6, jak w G | — |

**WYNIK:** wariant korzysta wyłącznie z `KontekstIntuicji` (konsolidacja, liczba znanych magm) i pól kandydatury; nie dotyka `sw`, `pamiec.concepts`
na nieznanych magmach ani weryfikatora. Jedynym ramieniem z dostępem do świata jest W.

Dobrze zdefiniowane: m ≥ 1 i n ≥ 1 (zabezpieczone `max(…, 1)`), wsparcie/n ∈ (0, 1], więc człon wsparcia ∈ (0, λ·m] — ta sama skala co out(a) + out(b)
(oba ≤ m − 1). m jest stałe w obrębie jednego snu, więc działa jak skala, nie jak cecha kandydatury: ranking zależy od λ·m względem stopni.
Dwie uwagi opisowe (Z8):
- Przy λ = 0 wariant **nie** odtwarza G: G ma remisujący człon +0,001·wsparcie/n, wariant go nie ma. Bez znaczenia dla λ = 1, ale opis
  „G + człon wsparcia” jest ścisły tylko z dokładnością do tego remisu.
- Nazwa „m = liczba klas” powinna doprecyzować: „klas równoważności po konsolidacji sprawdzonych implikacji, łącznie z klasą ⊤”.

**Uczciwość opisu doboru λ (§2 prerejestracji).** „Wybrano λ = 1 (wyższa średnia w obu zestawach)” jest nieścisłe. W zestawie dev średnie:
λ = 0,25: +0,214; 0,5: +0,283; **1: +0,297; 2: +0,309**; bez out(a): +0,191 (mediany: 0,068; **0,157**; 0,117; 0,076; 0,104). Najwyższą średnią
w dev miało λ = 2, najwyższą medianę — λ = 0,5. „Wyższa w obu” jest prawdą tylko względem λ = 0,5 (potw: +0,495 vs +0,610). **WYNIK.**
To nie podważa wyboru (różnice 1 → 2 są w szumie, a λ = 2 ma więcej światów < 0: 27% vs 23%), ale tekst musi to mówić (B5).
Pozostałe liczby §2 zgadzają się z JSON: +0,30 / 65%; +0,61 / mediana +0,25 / 80%; G − H = −1,73 i −0,92 (w §2 podane jako „+1,73 i +0,92”
z dopiskiem „heurystyka grafu − stara heurystyka” — **znak jest odwrotny**: to G jest gorsza od H w tych światach). **WYNIK.**

---

## 7. Poprawki

### BLOKUJĄCE (przed zamrożeniem)

- **B1. Zamknąć furtkę w T1.** Szkoda w rzędzie 3 ma być oceniana bez bramki. Propozycja: w T1 (i dla symetrii w T1-4) liczyć „gorsza”
  przed bramką, tj. `if n >= 4 and len(gorsza) >= 0,6·n: "gorsza"`, a bramka blokuje tylko „lepsza”. Dodatkowo (w duchu Z4 z recenzji S-0)
  warunek „Skutek” zaostrzyć: propozycja zastąpienia tylko wtedy, gdy w T1 najwyżej jedno ważne prawo ma górną CI(GW − G) < 0
  (niezależnie od bramki). Jeśli autor woli zostawić kategorie bez zmian, to „T1 nieinformatywny” musi blokować propozycję tak samo jak „gorsza”.
  Uzasadnienie wzmacnia fakt, że GW **nigdy nie był oceniany w rzędzie 3** (dev tylko na U4), a test dymny (§8) pokazuje w T1 prawo z GW − G = −1,25.
- **B2. Dobór praw: usunąć swobodę i rozszerzyć listę zakazaną.** (a) Usunąć ręczne `named` albo jawnie uzasadnić w §3, dlaczego te trzy
  i dlaczego przed losowymi; (b) dopisać do zakazanych światy `dane/swiaty_v3.json` (dewelopment G) i światy treningowe LMM v1/v2 (`_L`, `_S`,
  koniunkcje) — albo, jeśli autor ich nie wyklucza, napisać w §3, że lewa alternat. i x(xx)=x nie są nowe w programie; (c) zadeklarować,
  że `losuj_prawa(600, 9090)` to jedyne użyte ziarno generatora. Ponowne puszczenie reguły jest dozwolone przed zamrożeniem: nie używa wyników.
- **B3. Bliskie duplikaty S-0.** Do reguły dodać kryterium nadzbioru/podzbioru albo progu Jaccarda (np. odrzucić, gdy świat zawiera cały świat
  prawa S-0 lub ma Jaccard ≥ 0,5 z jakimkolwiek zakazanym światem, w którymkolwiek rzędzie) — albo zostawić prawa, ale (i) wpisać do §3
  tabelę: dla każdego prawa |świat|, udział magm z próbek S-0 w U4, max Jaccard i relację ⊆/⊇ ze światami S-0, i (ii) prerejestrować
  analizę wrażliwości „bez praw-nadzbiorów S-0” (opisowo, jak „bez x(xy)=y” w S-0). Te wielkości autor może policzyć bez ziaren.
- **B4. Hashe.** Wpisać wartość `H4_SHA` także w tekst §0/§1 prerejestracji; w `main()` dodać sprawdzenie `heurystyki.py` względem
  `s0_heur.HEUR_SHA` (linia odniesienia G).
- **B5. Tekst prerejestracji.** (a) §2: poprawić „wyższa średnia w obu zestawach” (λ = 2 miało w dev wyższą średnią, λ = 0,5 wyższą medianę)
  i znak „+1,73 i +0,92” (to G − H = −1,73 i −0,92); (b) §5: tabela progów n → k (4→3, 5→3, 6→4, 7→5, 8→5); (c) §5: oszacowana moc ≈ 0,6
  i zdanie, że „nierozstrzygnięta” znaczy „nie wykazano przewagi”, nie „brak efektu”.

### ZALECENIA (nieblokujące)

- **Z1.** Wpisać parametry bootstrapu (10 000 prób, ziarno 12345, percentylowy) i formułę M1 (b = min wywołań w parze) w §5.
- **Z2.** Zapisywać `kod_sha256` plików jak runner S-0 (`heur4_walidacja, heurystyki4, heurystyki, intuicja, fazy, petla, pamiec, swiat, s0, s1, s1b, uniwersum4, prawa_losowe`).
- **Z3.** Kontrasty opisowe liczyć dla **wszystkich** praw, nie tylko ważnych (§5 mówi „zawsze raportujemy”); w JSON oznaczyć ważność.
- **Z4.** Dodać do `pytest`: (i) `kategoria` na tabeli progów i przypadkach brzegowych; (ii) GW deterministyczny i bez dostępu do świata
  (np. ten sam wynik `ocen` przy podmienionym `sw`); (iii) `PRAWA` rozłączne ze `swiaty_dev(120)` i `PRAWA_S0` po nazwie.
- **Z5.** Opisowo GW − max(G, H) per prawo w rzędzie 4.
- **Z6.** Próg zapisać całkowitoliczbowo: `5 * len(x) >= 3 * n`.
- **Z7.** Opisowo: średnia GW − G po prawach z bootstrapem dwupoziomowym (prawa × ziarna).
- **Z8.** Doprecyzować definicję m (klasy po konsolidacji sprawdzonych implikacji, z ⊤) i uwagę o braku członu remisowego 0,001 przy λ → 0.
- **Z9.** W §6 dopisać do rejestru ziarna recenzenta faktycznie użyte: 1880–1885 (test dymny tej recenzji); 1886–1899 pozostają wolne.
- **Z10.** W raporcie wyniku powtórzyć ograniczenie z §3.2c: światy T1-4 są wycinkami próbek S-0 w U4, więc „uogólnienie na nowe prawa”
  w rzędzie 4 znaczy „na nowe podzbiory U4”, nie „na nowe magmy rzędu 4”.

---

## 8. Test dymny (ziarna 1880–1885)

4 pierwsze prawa `swiaty_dev(120)`, ziarna 1880–1885 (6), oba światy, 5 ramion, 240 przebiegów, 140 s (1 rdzeń). **WYNIK** (techniczny):
`zbierz` i `analiza` działają, asercja wspólnego d1 nie pęka, werdykt składa się poprawnie. Liczby poniżej mają 6 ziaren i służą tylko
ilustracji mechaniki, nie ocenie efektu.

| Świat | ważne | bramka (W − G) | lepsza | gorsza | kategoria |
|---|---|---|---|---|---|
| T1 | 3/4 | 1/3 | 0 | 0 | nieinformatywny (n < 4) |
| T1-4 | 4/4 | 3/4 | 2 | 1 | nierozstrzygnięta |

GW − G (M1, średnia [95% CI]): T1: −1,25 [−2,93; 0,01], −0,05 [−0,45; 0,39], 0,00 [0; 0]; T1-4: +1,65 [1,24; 2,14], −1,26 [−2,09; −0,40],
+0,34 [0,11; 0,59], +0,04 [−0,03; 0,15]. Werdykt: „WYNIK NEGATYWNY: brak przewagi w rzędzie 4; T1: nieinformatywny”.

Obserwacje: (i) w T1 bramka W − G przeszła w 1/3 ważnych praw — zgodnie z §4.2 to realny scenariusz, a nie przypadek brzegowy (B1);
(ii) w T1 jedno ważne prawo ma GW − G = −1,25 z górną CI ≈ 0 — przy 60 ziarnach byłoby prawdopodobnie istotnie gorsze, a przy niezdanej bramce
i tak nie trafiłoby do kategorii „gorsza” (B1); (iii) w T1-4 jedno prawo jest istotnie gorsze (−1,26) — heterogeniczność z §5 widać już na 4 prawach;
(iv) jedno prawo ma wszystkie różnice równe 0 (CI [0; 0]) — `ci95` to obsługuje, prawo liczy się do n, ale nie do L ani G.

Kategoria `kategoria()` na danych syntetycznych: minimalna liczba praw „lepszych” = 3, 3, 4, 5, 5 dla n = 4, 5, 6, 7, 8; przy bramce 2/5
zwraca „nieinformatywny” także wtedy, gdy 3/5 praw jest „gorszych” — co potwierdza furtkę z B1 bezpośrednio w kodzie.

Drzewo `rdzen/` po recenzji: jedyna zmiana to ten plik (nieśledzony; przed uruchomieniem runnera trzeba go zacommitować).
