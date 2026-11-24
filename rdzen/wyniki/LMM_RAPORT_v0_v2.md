# Intuicja LMM: trening v0–v2 i walidacja (24.11)

Status: **przed testem na prawach S-0** (ziarna 600–679 NIEużyte). `PREREJESTRACJA_S1_LMM.md` to projekt, niezamrożony.

## Co zbudowano

Port `Intuicja` wypełniony architekturą LMM: `bsd2.PosetEncoder` (wariant B) + `MRPHead`, kopia bez zmian z mdrewnisz/LMM@39bd217.
Wejście: skonsolidowany graf wiedzy (klasy pojęć; znane wynikanie, znane wykluczenie, pary ukryte), cechy węzła (częstość na znanych magmach,
rozmiar klasy, typ pojęcia) i kandydatury (wsparcie, śmiałość, obalony kierunek odwrotny). Bez nazw pojęć i bez dostępu do prawdy świata.
Wagi uczone tutaj od zera (wagi z Asusa niedostępne). Kod: `lmm_intuicja.py`, `lmm_trening.py`, `uniwersum4t.py`, `s1lmm.py`.

## Przebieg prac (jawnie, z wynikami odrzuconymi)

| Wersja | Dane treningowe | Walidacja (prawa spoza S-0) | Los |
|---|---|---|---|
| v0 | 7 światów praw spoza S-0, U3 i U4 | offline AUC prawdy 0,82; w pętli (ziarna 1300–1339) reguła sekcji 5 → WYNIK NEGATYWNY (gorszy na 2/5 praw) | odrzucony |
| v1 | + własności strukturalne i koniunkcje (54 światy), U3 i U4 | offline AUC 0,83; w pętli lepszy od heurystyki w 4/5 praw w obu światach | **odrzucony przez recenzję**: światy treningowe w U4 to w 76–100% magmy z próbek praw S-0 (np. lewa alternat. ⊃ łączne, lewo-skracalne ⊃ x(xy)=y) |
| v2 | 32 światy na uniwersach rozłącznych z magmami praw S-0 **i praw walidacyjnych** („3T”, nowe „4T”); procedura ustalona z góry (10 epok, LR kosinusowo, wybór epoki na odłożonych ziarnach treningowych) | offline AUC prawdy **0,53** (heurystyka 0,52, los 0,50); w pętli (ziarna 1440–1479): **gorszy od heurystyki** w 3/5 praw w obu światach | test czysty |

## Wnioski

1. **[WYNIK NEGATYWNY]** Intuicja LMM v2, uczona na światach bez wspólnych magm ze światami testowymi, **nie uogólnia się** na nowe prawa:
   w pętli LMM − heurystyka istotnie < 0 w 3/5 praw walidacyjnych w T1 i w T1-4 (np. x(xy)=xy: −1,81 i −2,80 krawędzi TR), istotnie > 0 tylko w 1/10 par.
   Dla v2 prawa walidacyjne były czystym testem (nieużyte do wyboru modelu ani treningu, magmy wykluczone z treningu).
2. **[WNIOSKOWANIE]** Dobre wyniki v0/v1 (AUC 0,82–0,83, wygrana w 4/5 praw) wynikały najpewniej z **nakładania się magm** między światami treningowymi
   a walidacyjnymi, nie z przenoszalnej intuicji. Po rozdzieleniu magm AUC spada do poziomu losu. (Nie jest to dowód przyczynowy: v2 zmienił też procedurę treningu.)
3. **[WYNIK]** Graf jest używany: LMM z grafem bije ablację „bez grafu” w 9/10 par (np. +1,9 i +2,2 w lewej samodystr.), a ablacja jest gorsza od heurystyki wszędzie.
   Tokeny zależności niosą więc sygnał, ale model z nich wyuczony nie przenosi się między rodzinami magm.
4. **[HIPOTEZA]** Intuicja na tokenach zależności wymaga treningu na znacznie szerszym i bardziej zróżnicowanym zbiorze światów (albo innej reprezentacji,
   np. niezmienniczej względem tego, które literały występują), żeby przenosić się na nowe prawa. W obecnej skali „intuicja” to pamięć konkretnych rodzin magm.
5. **[WYNIK]** Heurystyka ogólności na prawach walidacyjnych (ziarna 1440–1479) bije los w 8/10 par: replikacja S-1b poza prawami S-0 (por. hipoteza 5 w raporcie S-1b).

## Czego nie zrobiono

Testu prerejestrowanego na prawach S-0 (ziarna 600–679) nie uruchomiono: v2 nie przeszedł czystej walidacji, a v1 nie jest dopuszczalny.
Ziarna 600–679 pozostają nienaruszone.

Recenzja przed zamrożeniem (osobny agent) dla v1: uwaga blokująca B1 (skażenie danych), ważne W1–W4 (opis wyboru modelu, ablacja, niestabilny trening, AUC i scipy);
wszystkie uwzględnione w v2.
