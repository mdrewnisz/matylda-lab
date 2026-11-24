# S-1: raport (24.11)

Przebieg prerejestrowany: `PREREJESTRACJA_S1.md` (zamrożona w 7676f1b), uruchomiony z commita a6f9d59 (różnica: tylko `MATYLDA_RDZEN.md`).
Hashe prerejestracji, kodu i U4 zgodne z commitem zamrożenia (sprawdził niezależny recenzent). Dane: `s1_wyniki.json`, 3 200 przebiegów, ziarna 100–179.
Wnioski poniżej uwzględniają niezależną recenzję wyników (osobny agent); jego dodatkowe analizy są oznaczone jako eksploracyjne.

## Werdykt prerejestrowany

**NIEINFORMATYWNY: bramka nie przeszła w T1-4.** Zgodnie z sekcją 6 kontrasty heurystyki są tylko eksploracyjne.

| Świat | Bramka (wyrocznia pokrycia − losowa, dolna CI > 0) | Heurystyka − losowa, dolna CI > 0 |
|---|---|---|
| T1 | 5/5 (efekty 2,1–5,3 krawędzi TR) | 4/5 (idempotentna 0,89; komutatywna 1,11; x(xy)=y 0,74; łączna 1,66; medialna 0,22 [−0,02; 0,48]) |
| T1-4 | **2/5** (idempotentna 3,62; medialna 3,66; pozostałe ≈ 0) | 2/5 (idempotentna 0,93; medialna 0,66) |

Kategoria „pomijalna” wypisana przez runner dla T1-4 **nie ma znaczenia** (bramka nie przeszła, δ zaniżona przez zera strukturalne). Nie piszemy „WYNIK NEGATYWNY w T1-4”.

## Ustalenia

1. **[WYNIK] Przy budżecie 100 bramka w T1-4 nie przechodzi, bo sen prawie się nie odbywa.** W komutatywnej, x(xy)=y i łącznej
   dzień 1 wyczerpuje budżet w 100% / 95% / 96% przebiegów (średnio 83 z 100 wywołań w T1-4 wobec 57 w T1), pula pierwszego snu jest pusta,
   a pole daje różnicę dokładnie 0. To zera strukturalne, nie brak efektu.
2. **[WNIOSKOWANIE, eksploracyjne] To artefakt budżetu, nie brak miejsca na wybór w T1-4.** Po dniu 1 brakuje 21–33 krawędzi TR.
   Recenzent na 3 prawach z budżetem 200 i 300 (świeże ziarna 700–729, poza prerejestracją): wyrocznia − losowa 2,9–8,6 krawędzi TR,
   heurystyka − losowa 0,66–1,75 (wszystkie dolne CI > 0). 200 i 300 dają to samo, bo przebiegi same wyczerpują pulę przed 200.
   Ryzyko zapisaliśmy w sekcji 5 prerejestracji, ale przyczyny nie zdiagnozowaliśmy przed zamrożeniem (ślad był w analizie mocy: wyrocznia ≈ 0 na 2 prawach T1-4).
3. **[HIPOTEZA] W T1 heurystyka ogólności przyspiesza pokrycie TR względem losu** (4/5 praw; 20–35% efektu wyroczni, medialna 6%).
   Jeden świat, bramka nieprzepuszczona w drugim, więc tylko hipoteza do replikacji.
4. **[WNIOSKOWANIE, eksploracyjne] Efekt heurystyki pochodzi głównie z reguły „powtórka przed śmiałymi”, nie z trafniejszego wyboru wśród śmiałych.**
   M2: wśród śmiałych trafność heurystyki ≈ trafność puli (T1: 0,47/0,46; 0,28/0,32; 0,72/0,65; 0,56/0,70; 0,35/0,36).
   Dekompozycja recenzenta (ramię „warstwy”: los w obrębie warstwy, powtórka przed śmiałymi): w łącznej, idempotentnej i x(xy)=y warstwy wyjaśniają większość efektu;
   w komutatywnej działa głównie porządek wsparcia w obrębie powtórki (+0,94 [0,70; 1,17]) przy niezmienionej trafności, czyli ten porządek wybiera
   krawędzie ważniejsze dla TR, a nie trafniejsze.
5. **[WYNIK] Wybór ma w tych światach dużą wartość.** Wyrocznia pokrycia daje 2–5 krawędzi TR w T1 i ok. 3,6 w T1-4 tam, gdzie sen się odbywa;
   heurystyka osiąga ok. ćwierć tego. Miejsce na prawdziwą intuicję (LMM) jest, a prosta heurystyka go nie wyczerpuje.
6. **Opisowo:** pokrycie w punkcie b (M1-koniec) dla medialnej jest u heurystyki istotnie niższe niż u losowej (T1 −0,55 [−1,04; −0,06], T1-4 −0,66 [−1,04; −0,30]):
   szybszy start, gorszy koniec. M2 liczy kandydatury wybrane, nie faktycznie sprawdzone (drobne).

## Błędy

Recenzent nie znalazł asymetrii ani wycieku: ramiona bez wyroczni nie widzą świata, strumienie losowe są rozdzielone, pole liczone symetrycznie do min(wywołań).

## Następny krok (propozycja, wymaga nowej prerejestracji S-1b)

- Werdykt S-1 zostaje **NIEINFORMATYWNY** na stałe.
- S-1b: budżet powiązany z mechanizmem, nie z liczbą dobraną po wyniku: osobny budżet po dniu 1 (np. 50 wywołań od końca dnia 1) albo budżet nieograniczający (≥ 200).
- Nowy warunek ważności przed porównaniem ramion: sen odbywa się (wydatek po dniu 1 > 0) w ≥ 90% przebiegów w każdym prawie.
- Oba światy od nowa, świeże ziarna 800–879 (100–179 użyte, 600–679 dla LMM, 700–729 obejrzane w recenzji).
- Jawnie zapisać: budżet zmieniony po obejrzeniu S-1, a podgląd recenzenta (ziarna 700–729) jest eksploracyjny i nie może być potwierdzeniem.
- Ryzyko „przestawiania bramki po wyniku”: umiarkowane, łagodzone tym, że diagnoza opiera się na zużyciu budżetu (M3), nie na kontrastach ramion.
