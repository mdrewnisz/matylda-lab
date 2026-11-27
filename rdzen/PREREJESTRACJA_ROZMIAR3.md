# Prerejestracja: heurystyka przyrostu w rzędzie 3 według rozmiaru świata

Status: **SZKIC** (27.11), przed recenzją. Seria samodzielna za zgodą Michała (27.11: „Dalej, rozwija projekt zgodnie z master planem”); cel programu bez zmian.
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
Lista zakazana: jak w PRZYROST + 5 praw walidacyjnych PRZYROST + 10 praw pilota. Pierwsze 5 praw w każdym przedziale, w kolejności generatora.
Lista: `wyniki/rozmiar3_prawa.json`, PRAWA_SHA256: 99284c61613c03fca4fcc2da74a80d6d06c471dc9f5cf1f9a73e6082a51b3651

| Przedział | Prawo | Magmy | TR | maks. Jaccard |
|---|---|---|---|---|
| małe | y(zz) = (xz)((xx)x) | 99 | 48 | 0,455 |
| małe | (xx)x = x((zx)(xy)) | 133 | 59 | 0,376 |
| małe | x(y(xy)) = (yx)x | 146 | 57 | 0,439 |
| małe | ((yx)(xy))z = y(yy) | 67 | 60 | 0,440 |
| małe | (((yy)x)y)y = xy | 132 | 82 | 0,471 |
| duże | y((xx)(xy)) = y(yy) | 1516 | 90 | 0,328 |
| duże | (zz)((zy)z) = z | 766 | 72 | 0,249 |
| duże | x(zx) = z(x(zx)) | 774 | 80 | 0,400 |
| duże | (x(x(xy)))y = yy | 545 | 78 | 0,394 |
| duże | x(zy) = x(z((zy)x)) | 711 | 71 | 0,451 |

Odrzucenia: 59 rozmiar lub luka, 28 Jaccard lub nadzbiór. Ograniczenia jak w PRZYROST: izomorfizm nie jest sprawdzany, Jaccard nie wychwytuje bliskości składniowej.
Uwaga: |TR| jest w dużych światach nieco wyższy (71–90 wobec 48–82). Rozmiar nie jest jedyną różnicą między przedziałami, co ogranicza interpretację przyczynową.

## 3. Przebieg

Świat T1 (rząd 3), protokół S-1b (dzień 1 do 300, sen 50, słownik „literaly”, cex_cap 1), **ziarna 2010–2069** (60, nowe).
Ramiona: losowa, heurystyka (stara), heur_grafu, heur_przyrostu (m = 1), wyrocznia_przyrostu (bramka). 10 praw × 60 × 5 = 3 000 przebiegów, jedno uruchomienie.

## 4. Kryteria (rozstrzygające)

M1 i bootstrap sparowany jak w PRZYROST. W każdym przedziale osobno (n = liczba ważnych praw, próg 60% n), kategorie jak w PRZYROST §6:
nieinformatywny (n < 4 lub bramka < 60% n) / gorsza / lepsza / nierozstrzygnięta.

Interakcja: I = średnia po prawach M1(przyrost − graf) w małych − to samo w dużych, CI 95% z bootstrapu dwupoziomowego (prawa w przedziale, potem ziarna;
10 000 prób, ziarno 12345). Przy 5 prawach na przedział CI interakcji jest szerokie.

**Werdykt** (`rozmiar3_walidacja.werdykt`, decyduje przedział MAŁE):
- MAŁE nieinformatywny → NIEINFORMATYWNY;
- MAŁE gorsza → WYNIK NEGATYWNY (heurystyka przyrostu gorsza w małych światach);
- MAŁE nierozstrzygnięta → WYNIK NEGATYWNY dla H_mod (brak przewagi w małych światach);
- MAŁE lepsza i dolna CI(I) > 0 → WYNIK: lepsza w małych i efekt większy niż w dużych (moderacja rozmiarem);
- MAŁE lepsza, CI(I) obejmuje 0 → WYNIK: lepsza w małych; moderacja niewykazana.
Kategoria DUŻE jest zawsze raportowana. Jeśli DUŻE też „lepsza”, to wynik przemawia za heurystyką przyrostu w całym rzędzie 3, a nie za moderacją.

Skutek (propozycje do decyzji Michała, nie automatycznie):
- MAŁE i DUŻE „lepsza” → propozycja domyślnej heurystyki przyrostu także w rzędzie 3;
- tylko MAŁE „lepsza” → propozycja reguły zależnej od rozmiaru dopiero po replikacji. Próg zależy od świata, a badacz nie zna rozmiaru świata, zna tylko liczbę znanych magm.
Inaczej domyślna zostaje bez zmian.

Zawsze raportujemy: stałe okno [d1, d1 + 50], pokrycie końcowe, przyrost − heurystyka i − losowa, graf − heurystyka, bramkę.

## 5. Ziarna

Zużyte: 2010–2069 (ta walidacja). Recenzja przed: 2070–2079. Recenzja po: 2080–2089. Uwaga: pilot PRZYROST zużył 2000–2009.
Benchmark GSI ma ziarna od 2000 w innym kodzie i innych światach; w rdzeniu od teraz unikamy tej puli i zaczynamy od 2010.

## 6. Kontrola jakości

`pytest`; runner odmawia przy brudnym drzewie, istniejącym wyniku, statusie innym niż ZAMROŻONA, niezgodnym hashu runnera (§9), praw lub dowolnego pliku z `KOD`.
Zapisuje `kod_sha256` w wyniku. Niezależny recenzent przed zamrożeniem i po wyniku.

## 9. Hash runnera

RUNNER_SHA256: (wpisywany przy zamrożeniu)
