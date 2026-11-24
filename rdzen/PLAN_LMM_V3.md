# Plan LMM v3: intuicja przenoszalna na nowe prawa

Status: **zapisany przed treningiem v3** (24.11). Kryterium z sekcji 4 jest rozstrzygające i nie zmienia się po zobaczeniu wyników.
Kontekst: v2 (32 światy z 4 praw treningowych i 7 własności) nie uogólnił się na prawa walidacyjne (AUC 0,53, w pętli gorszy od heurystyki
w 3/5 praw, `wyniki/LMM_RAPORT_v0_v2.md`). Michał wybrał przeprojektowanie pod przenoszalność; test na S-0 dopiero po przejściu walidacji.

## 1. Hipoteza robocza (poziom: HIPOTEZA)

Porażka v2 wynika głównie ze zbyt wąskiego rozkładu światów treningowych (model uczy się specyfiki kilku praw, nie struktury grafu wiedzy).
Jeśli tak, trening na setkach światów z losowych praw równościowych powinien dać intuicję, która przenosi się na prawa niewidziane.
Alternatywa, którą test też może wskazać: tokeny zależności po dniu 1 po prostu nie niosą informacji ponad heurystykę wsparcia
(wtedy więcej danych nie pomoże, a wynik będzie negatywny także dla v3).

## 2. Co się zmienia względem v2 (tylko dane)

| Element | v2 | v3 |
|---|---|---|
| Światy treningowe | 32, z 4 praw + 7 własności + koniunkcji | **losowe prawa równościowe** l = r (zmienne x, y, z; 1–3 działania na stronę, łącznie ≤ 4), generator `prawa_losowe.losuj_prawa(2000, ziarno 31337)` |
| Uniwersa | 3T i 4T | bez zmian: 3T i 4T (bez magm praw S-0 i praw walidacyjnych; 4T rozłączne z U4) |
| Filtr światów | ≥ 20 magm, \|TR\| ≥ 15, bez duplikatów | bez zmian; **323 światy** (230 w 3T, 93 w 4T), lista zamrożona w `dane/swiaty_v3.json`, sha256 `4274db93f25be7b3f8b5f13af1979fcd844e38449a3ed37313cb1f299257bb31` |
| Ziarna | 60 na świat (1100–1159) | **8 na świat (1500–1507)** |
| Wybór epoki | strata na odłożonych ziarnach tych samych światów | strata na **odłożonych światach** (15% = 48 z 323 światów, podział losowy, ziarno 77): mierzy przenoszenie na nowe prawa |
| Architektura, cechy, etykiety, hiperparametry | PosetEncoder B d=64 L=4 + cechy; BCE; 10 epok; LR 1e-3 → 1e-5; ziarno 2024 | **bez zmian** (żeby różnica dotyczyła danych) |
| Ablacja | bez grafu | bez zmian (`v3_bez_grafu`) |

Reprezentacja już teraz nie zawiera nazw pojęć ani literałów (tylko typ pojęcia). Zmianę reprezentacji odkładamy: jeśli v3 przegra,
nie będziemy wiedzieć, czy winne były dane, czy reprezentacja, gdybyśmy zmienili obie naraz.

## 3. Walidacja (jedna, czysta)

- Prawa walidacyjne: te same 5 praw spoza S-0 (elastyczna, lewa i prawa samodystr., x(xy)=xy, (yx)x=y), światy T1 i T1-4.
  Ich magm nie ma w żadnym świecie treningowym (test `test_lmm_v3_bez_praw_wykluczonych`).
- **Nowe ziarna 1520–1559** (40), nigdy nieużyte. Protokół S-1b (dzień 1 do 300, sen 50), ramiona: losowa, heurystyka, lmm, lmm_bez_grafu,
  wyrocznia_pokrycia, wyrocznia_trafnosci. `python -m matylda_rdzen.s1lmm --walidacja v3`, jedno uruchomienie, bez nadpisywania.
- Prawa walidacyjne nie były użyte do wyboru v3 (wybór epoki tylko na odłożonych światach treningowych).

## 4. Kryterium przejścia (rozstrzygające)

Miara M1 i bootstrap jak w S-1b. W każdym świecie (T1, T1-4), tylko prawa ważne:

- **PRZESZŁA**: dolna granica 95% CI(LMM − heurystyka) > 0 w ≥ 3/5 praw **w obu światach**.
- **NIE PRZESZŁA**: w przeciwnym razie.

Skutek: PRZESZŁA → niezależna recenzja, potem prerejestracja testu S-0 (ziarna 600–679) z wagami v3 zamrożonymi hashem.
NIE PRZESZŁA → WYNIK NEGATYWNY dla v3, ziarna 600–679 zostają nietknięte, raport i decyzja Michała co dalej.

Raportujemy zawsze (opisowo): LMM − los, LMM − ablacja (czy graf pomaga), prawa z LMM istotnie gorszą od heurystyki, ułamek luki
(LMM − heur) / (wyrocznia − heur), AUC offline na odłożonych światach.

## 5. Zużycie ziaren

1500–1507: dane treningowe v3. 1520–1559: walidacja v3. Nadal zarezerwowane i nieużyte: 600–679 (test S-0).
