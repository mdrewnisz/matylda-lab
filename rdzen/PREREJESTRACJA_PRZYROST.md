# Prerejestracja: heurystyka przyrostu pokrycia z nową bramką (wyrocznia przyrostu)

Status: **SZKIC** (27.11), przed recenzją. Seria samodzielna za zgodą Michała (27.11, wybór „Scal PR, potem nowa wyrocznia”); cel programu bez zmian.
Zamrożenie = commit tego pliku z wypełnionymi `przyrost_walidacja.PRAWA` i `SHA` (sha256 `heurystyki.py`, `heurystyki_przyrostu.py`, `wyrocznie.py`)
przed pierwszym `python -m matylda_rdzen.przyrost_walidacja`.

## 1. Pytanie i hipoteza

Recenzja HEUR4 (`wyniki/HEUR4_RECENZJA_PO.md` §4) pokazała, że stara wyrocznia pokrycia nie jest sufitem, a zachłanna wyrocznia przyrostu pokrycia TR
bije heurystykę grafu wszędzie. HIPOTEZA 13 recenzji: heurystyka liczona tak samo, ale na **znanym** porządku badacza, zamknie dużą część tej luki.

**H:** `HeurystykaPrzyrostu(m = 1)` jest lepsza od domyślnej intuicji `HeurystykaGrafu("oa+ob+kara")` w M1, w rzędzie 3 i w rzędzie 4.

Reguła (`heurystyki_przyrostu.py`): badacz szacuje porządek świata jako Ê = {A ⇒ B : brak kontrprzykładu wśród znanych magm, wsparcie A i B ≥ m},
liczy z Ê ∪ potwierdzonych klasy i redukcję przechodnią TR̂ i wybiera zachłannie w paczce 10 kandydatury o największym przyroście pokrycia TR̂
względem domknięcia krawędzi już potwierdzonych. Remisy: heurystyka grafu. Bez prawdy świata i bez weryfikatora.

## 2. Nowa bramka

`wyrocznie.IntuicjaWyroczniaPrzyrostu` (ramię kalibracyjne, zna świat): to samo co wyżej, ale na prawdziwym TR świata i tylko wśród prawdziwych kandydatur;
fałszywe na końcu. Dolne oszacowanie sufitu, nie optimum. Stara `IntuicjaWyroczniaPokrycia` zostaje bez zmian i jest raportowana opisowo.

## 3. Jak wybrany wariant (jawnie)

Dewelopment wyłącznie na losowych prawach (≤ 4 działania), `przyrost_dev.py`:
- runda 1, ziarna 1900–1909, 20 światów rzędu 4 (U4, `heur4_dev.swiaty_dev`, światy 20–39) + 20 rzędu 3 (generator ziarno 4446): bramka wyr_prz − grafu
  istotnie > 0 w 19/20 (rz. 4) i 18/20 (rz. 3), nigdy < 0. Warianty m = 2, m = 3, m = 2 z wykluczeniem śmiałych: słabsze
  (m = 2: rz. 4 śr. +0,97, 11/20 istotnie >, 1 <; rz. 3 śr. +0,22, 9/20 >, 3 <) — `wyniki/przyrost_dev.json`;
- runda 2, te same światy i ziarna: m = 1 (rz. 4 śr. +1,85, 14/20 >, 0 <; rz. 3 +1,60, 15/20 >, 0 <); waga śmiałych 0,5 bez różnicy.
  Wybrano m = 1 bez wag (najprostszy) — `wyniki/przyrost_dev_r2.json`;
- potwierdzenie, nowe światy (rz. 4: 60–79, rz. 3: 20–39), ziarna 1910–1919: m = 1 rz. 4 śr. +2,10 (14/20 >, 1 <), rz. 3 +1,28 (15/20 >, 1 <);
  bramka 20/20 i 20/20 — `wyniki/przyrost_dev_potw.json`.
Opisowo: m = 1 zamyka w dev ok. 0,45–0,65 średniej luki do wyrocznii przyrostu (bez CI, wyrocznia nie jest optimum).
Liczba porównanych wariantów: 6 (m ∈ {1, 2, 3}, kara/waga śmiałych). Ryzyko dopasowania do dev ograniczają nowe prawa i nowe ziarna (§4).

## 4. Prawa walidacyjne (nowe)

Reguła jak w HEUR4 (`wyniki/heur4_wybor_praw_kod.py.txt`), kod `przyrost_wybor_praw.py`; lista zakazana poszerzona o 5 praw walidacyjnych HEUR4
i 40 praw dev rzędu 3 z `przyrost_dev`. Generator z prawami ≤ 4 działań (ziarno 9191) dał **0 praw** (pula wyczerpana: 2762/5000 odpadło na Jaccardzie
w rzędzie 3). Dlatego prawa walidacyjne pochodzą z **klasy większych termów** (2–4 działania po lewej, łącznie ≤ 6; ziarno 9292, jedyne użyte).
To przesunięcie rozkładu względem dev jest jawne: test sprawdza też przenoszenie na nową klasę praw.

Z 5 000 kandydatów pierwsze 5, które przeszły:

| Prawo | rząd 3: magmy / TR | rząd 4: magmy / TR |
|---|---|---|
| y(yy) = (x(yx))(yy) | 872 / 72 | 565 / 100 |
| x(z(xx)) = z(xx) | 854 / 69 | 494 / 91 |
| ((zx)x)x = (xz)x | 529 / 70 | 585 / 91 |
| ((xz)x)(zx) = x | 105 / 74 | 58 / 92 |
| (yx)(yx) = (yx)(yy) | 1845 / 74 | 809 / 93 |

Ograniczenie: izomorfizm przez permutację elementów nie jest sprawdzany (tylko równość i transpozycja zbiorów tablic).

## 5. Przebieg

Światy T1 (rząd 3) i T1-4 (U4), protokół S-1b (dzień 1 do 300, sen 50, słownik „literaly”, cex_cap 1), **ziarna 1920–1979** (60, nowe).
Ramiona: losowa, heurystyka (stara), heur_grafu, heur_przyrostu (m = 1), wyrocznia_przyrostu (bramka), wyrocznia_pokrycia (opisowo). 3 600 przebiegów, jedno uruchomienie.

## 6. Kryteria (rozstrzygające)

M1 (pole pod krzywą pokrycia TR od d1 do b = min wywołań pary), bootstrap sparowany 95% (10 000, ziarno 12345). W każdym świecie, tylko prawa ważne
(niepusta pula 1. snu w ≥ 90% ziaren), n = ich liczba, próg 60% n (n = 4 → 3, n = 5 → 3). Kolejność (szkoda niezależnie od bramki):
1. n < 4 → **nieinformatywny**;
2. górna CI(heur_przyrostu − heur_grafu) < 0 w ≥ 60% n → **gorsza**;
3. bramka (wyrocznia_przyrostu − heur_grafu, dolna CI > 0) w < 60% n → **nieinformatywny**;
4. dolna CI(heur_przyrostu − heur_grafu) > 0 w ≥ 60% n → **lepsza**; inaczej **nierozstrzygnięta**.

**Werdykt:** lepsza w T1 i T1-4 → WYNIK; gorsza w którymkolwiek → WYNIK NEGATYWNY; lepsza tylko w jednym → WYNIK CZĘŚCIOWY (dla tego rzędu);
nieinformatywny bez „lepszej” → NIEINFORMATYWNY; inaczej WYNIK NEGATYWNY (brak przewagi, słaby dowód braku efektu).
Skutek: WYNIK → propozycja (do decyzji Michała), by heur_przyrostu zastąpiła domyślną intuicję. Inaczej domyślna zostaje.

Zawsze raportujemy: stałe okno [d1, d1 + 50], pokrycie końcowe, heur_przyrostu − heurystyka / − losowa, heur_grafu − heurystyka (replikacja),
wyrocznia_przyrostu − wyrocznia_pokrycia, ułamek luki na stałym oknie „część luki do zachłannej wyroczni przyrostu” (bez CI, nigdy „% do optimum”).

## 7. Ziarna

Zużyte: 1900–1919 (dewelopment), 1920–1979 (ta walidacja). Recenzja przed: 1980–1989. Recenzja po: 1990–1999.

## 8. Kontrola jakości

`pytest` (30 testów); runner odmawia przy brudnym drzewie, istniejącym wyniku, złym hashu U4 lub zmienionym pliku z §0; niezależny recenzent przed zamrożeniem i po wyniku.
