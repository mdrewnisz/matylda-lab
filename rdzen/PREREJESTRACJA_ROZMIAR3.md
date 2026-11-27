# Prerejestracja: heurystyka przyrostu w rzędzie 3 według rozmiaru świata

Status: **ZAMROŻONA** (27.11) po recenzji przed zamrożeniem (`wyniki/ROZMIAR3_RECENZJA_PRZED.md`); wprowadzone B1–B4 oraz Z2–Z5, Z7, Z8. Seria samodzielna za zgodą Michała (27.11: „Dalej, rozwija projekt zgodnie z master planem”); cel programu bez zmian.
Zamrożenie = commit tego pliku ze statusem „ZAMROŻONA”, z wypełnionym `rozmiar3_walidacja.SHA` (pliki z `KOD`) i z linią RUNNER_SHA256 (§9) przed pierwszym
`python -m matylda_rdzen.rozmiar3_walidacja`. Runner sprawdza przed startem także własny hash i hash listy praw (zasada z recenzji PR #3).

## 1. Pytanie i hipoteza

Test PRZYROST (`wyniki/PRZYROST_RAPORT.md`) dał w rzędzie 3 wynik nierozstrzygnięty (2/5). Recenzja po wyniku postawiła HIPOTEZĘ post hoc:
efekt heurystyki przyrostu zależy od rozmiaru świata. W małych światach badacz zna większą część magm, więc szacowany porządek Ê jest trafniejszy.
Jedyny mały świat walidacji (105 magm) dał 0,95 luki do wyroczni, duże (≥ 529) co najwyżej 0,18.

**H_mod:** w rzędzie 3 `HeurystykaPrzyrostu(1)` jest lepsza od `HeurystykaGrafu("oa+ob+kara")` (M1) na światach małych (20–300 magm),
a efekt jest tam większy niż na światach dużych (≥ 500 magm).
Status: HIPOTEZA; ten test jest pierwszym prerejestrowanym sprawdzeniem.

Bez zmian w kodzie heurystyki (m = 1 zamrożone od PRZYROST), bez dewelopmentu.

## 2. Prawa (nowe)

`rozmiar3_wybor_praw.py`: klasa większych termów jak w PRZYROST (2–4 działania po lewej, łącznie ≤ 6), generator ziarno 9494 (jedyne użyte).
Filtr tylko w rzędzie 3: |TR| ≥ 15, rozmiar w przedziale MAŁE [20, 300] albo DUŻE [500, ∞); luka 301–499 jest celowo pominięta.
Wykluczenia: Jaccard ≥ 0,5 (świat lub transpozycja) z dowolnym zużytym światem rzędu 3 oraz zawieranie świata prawa testowanego.
Lista zakazana: jak w PRZYROST + 5 praw walidacyjnych PRZYROST + 10 praw pilota (recenzja: kompletna).
**7 praw na przedział (5 + 2 rezerwowe, B4).** Do analizy wchodzi pierwszych 5 **ważnych** praw przedziału w kolejności generatora.
Ważność (niepusta pula 1. snu w ≥ 90% ziaren) zależy tylko od wspólnego dnia 1, a nie od ramienia, więc zamiana nie obciąża porównania.
Lista: `wyniki/rozmiar3_prawa.json`, PRAWA_SHA256: 5bf958143116b6d965bda885ce724dfa1ed057d8e95c18cb9f4fe5020b229eb3

| Przedział | Prawo | Magmy | TR | maks. Jaccard |
|---|---|---|---|---|
| małe | y(zz) = (xz)((xx)x) | 99 | 48 | 0,455 |
| małe | (xx)x = x((zx)(xy)) | 133 | 59 | 0,376 |
| małe | x(y(xy)) = (yx)x | 146 | 57 | 0,439 |
| małe | ((yx)(xy))z = y(yy) | 67 | 60 | 0,440 |
| małe | (((yy)x)y)y = xy | 132 | 82 | 0,471 |
| małe (rezerwa 1) | (z(yx))(yz) = (zz)z | 172 | 78 | 0,369 |
| małe (rezerwa 2) | y(xy) = (yz)((zy)y) | 118 | 80 | 0,457 |
| duże | y((xx)(xy)) = y(yy) | 1516 | 90 | 0,328 |
| duże | (zz)((zy)z) = z | 766 | 72 | 0,249 |
| duże | x(zx) = z(x(zx)) | 774 | 80 | 0,400 |
| duże | (x(x(xy)))y = yy | 545 | 78 | 0,394 |
| duże | x(zy) = x(z((zy)x)) | 711 | 71 | 0,451 |
| duże (rezerwa 1) | (yy)(yy) = (xx)(xx) | 6561 | 57 | 0,474 |
| duże (rezerwa 2) | (z(yy))(zz) = yy | 733 | 64 | 0,464 |

Odrzucenia (dla 14 praw): 64 rozmiar lub luka, 37 Jaccard lub nadzbiór. Ograniczenia jak w PRZYROST: izomorfizm nie jest sprawdzany, Jaccard nie wychwytuje bliskości składniowej.
Uwaga: |TR| jest w dużych światach nieco wyższy (71–90 wobec 48–82, pierwsze 5), a odsetek prawdziwych kandydatur w puli maleje z rozmiarem (recenzja: ρ = −0,81).
Test nie oddziela rozmiaru od |TR| ani od trafności puli, więc „moderacja rozmiarem” znaczy tu „różnica między tymi przedziałami”, nie efekt przyczynowy samego rozmiaru.
Zrealizowany zakres MAŁYCH to 67–146 magm (do 172 z rezerwą), a nie cały przedział 20–300 (Z4).

## 3. Przebieg

Świat T1 (rząd 3), protokół S-1b (dzień 1 do 300, sen 50, słownik „literaly”, cex_cap 1), **ziarna 2010–2069** (60, nowe).
Ramiona: losowa, heurystyka (stara), heur_grafu, heur_przyrostu (m = 1), wyrocznia_przyrostu (bramka). 14 praw × 60 × 5 = 4 200 przebiegów, jedno uruchomienie.
Runner zapisuje też różnice M1 per ziarno (Z3). Skład puli z prawdziwością nie jest zapisywany: rozkład na „prawdę” i „kolejność” zostaje dla diagnostyki recenzenta po wyniku.

## 4. Kryteria (rozstrzygające)

M1 i bootstrap sparowany jak w PRZYROST. W każdym przedziale osobno (n = liczba ważnych praw, próg 60% n), kategorie jak w PRZYROST §6:
nieinformatywny (n < 4 lub bramka < 60% n) / gorsza / lepsza / nierozstrzygnięta.

Interakcja: I = średnia po prawach M1(przyrost − graf) w MAŁYCH − to samo w DUŻYCH. **Kryterium: dokładny, jednostronny test permutacyjny na poziomie
praw** (wszystkie C(10, 5) = 252 podziały; „moderacja” ⇔ p < 0,05; Z2). Bootstrap dwupoziomowy (prawa, potem ziarna; 10 000 prób, ziarno 12345)
podajemy opisowo. Najmniejsze osiągalne p = 1/252.

**Werdykt — pełna tabela (B2, B3; `rozmiar3_walidacja.werdykt`):**

| MAŁE | DUŻE | Moderacja (p < 0,05) | Werdykt | Skutek (propozycja do decyzji Michała) |
|---|---|---|---|---|
| nieinformatywny | dowolne | — | NIEINFORMATYWNY | bez zmian |
| gorsza | dowolne | — | WYNIK NEGATYWNY (gorsza w małych) | bez zmian |
| nierozstrzygnięta | dowolne | — | H_mod NIEPOTWIERDZONA | bez zmian |
| lepsza | lepsza | tak | WYNIK: lepsza w obu, efekt większy w małych | heurystyka przyrostu domyślna w całym rzędzie 3 |
| lepsza | lepsza | nie | WYNIK: lepsza w obu, różnica wielkości niewykazana | jw. |
| lepsza | nieinformatywny | dowolne | WYNIK: lepsza w małych; duże nieinformatywne | bez zmian; replikacja dużych |
| lepsza | nierozstrz./gorsza | tak | WYNIK: lepsza w małych, nie w dużych (moderacja) | reguła zależna od świata dopiero po walidacji widocznego proxy (Z7) |
| lepsza | nierozstrz./gorsza | nie | WYNIK: lepsza w małych; moderacja niewykazana | bez zmian |

**Z7:** rozmiar świata zna tylko wyrocznia. Widoczne proxy, czyli liczba znanych magm, rośnie z rozmiarem (recenzja: ρ = 0,89), ale przedziały
się nakładają (20–46 wobec 45–51). Reguła domyślna zależna od świata wymagałaby osobnej, prerejestrowanej walidacji takiego proxy.
**Z8:** „lepsza w MAŁYCH” jest w dużej mierze replikacją pilota PRZYROST; nową informację niosą DUŻE i interakcja.
Moc (szacunek recenzji, symulacja na prawach z tej klasy): P(MAŁE lepsza) ≈ 0,85, P(DUŻE lepsza) ≈ 0,54, P(obie lepsza i I > 0) ≈ 0,42.

Zawsze raportujemy: stałe okno [d1, d1 + 50], pokrycie końcowe, przyrost − heurystyka i − losowa, graf − heurystyka, bramkę.

## 5. Ziarna

Zużyte: 2010–2069 (ta walidacja), 2070–2079 (recenzja przed; tylko prawa pilota i dev). Recenzja po: 2080–2089. Uwaga: pilot PRZYROST zużył 2000–2009.
Benchmark GSI ma ziarna od 2000 w innym kodzie i innych światach; w rdzeniu od teraz unikamy tej puli i zaczynamy od 2010.

## 6. Kontrola jakości

`pytest` (35 testów); runner odmawia przy brudnym drzewie, istniejącym wyniku, linii statusu innej niż „Status: **ZAMROŻONA**” (B1), niezgodnym hashu runnera (§9), praw lub dowolnego pliku z `KOD`.
`KOD` obejmuje też zależności wyboru praw (heur4_dev, przyrost_dev, przyrost_walidacja, lmm_trening, heurystyki4; Z5). Zapisuje `kod_sha256` w wyniku. Niezależny recenzent przed zamrożeniem i po wyniku.

## 9. Hash runnera

RUNNER_SHA256: `7f119a4be0b94ad551c02637f720dab32198c336c704035cb21a1e9b57a9654f`
