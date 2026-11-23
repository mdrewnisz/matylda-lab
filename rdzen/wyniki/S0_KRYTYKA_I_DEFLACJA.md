# S-0: krytyka i deflacja (po wyniku, POST HOC)

> **Zdezaktualizowane (23.11):** niezależna recenzja wykazała, że wniosek „sen jest wydajniejszy” jest sprzeczny z danymi przy równym zużytym budżecie, a W+ i S-los miały błędy implementacji. Aktualne wnioski: `RECENZJA_I_WNIOSKI_S0_S0B.md`.

Ten plik powstał **po** obejrzeniu wyniku. Nie zmienia werdyktu prerejestracji, tylko go zawęża.
Konstruktor pętli i analityk wyniku to ten sam agent, więc potrzebny jest niezależny recenzent (Hostile Review) przed promocją czegokolwiek.

## Co wyszło (WYNIK, wg prerejestracji `f70e76f3…`)

- H-sen **nie obalona** w tym świecie: S − W+ przy B = 50 ma dolną granicę 95% CI > 0 we **wszystkich 5** prawach (średnio +5,2 do +7,9 krawędzi redukcji przechodniej).
- Konsolidacja **potrzebna**: S − S−K > 0 w 5 z 5 praw.
- Sen **lepszy od szumu**: S − S-los > 0 w 4 z 5 praw; w prawie medialnym odwrotnie (−3,6 [−5,7; −1,5]).
- Krawędzie podłożone (te, które są „odkryciem”, bo istnieją dzięki H) przy B = 50: S pokrywa najwięcej w każdym prawie.

## Co osłabia interpretację (WNIOSKOWANIE, post hoc)

1. **Kontrola W+ głoduje.** Średnio zużywa tylko 21–30 wywołań z budżetu, bo zwykły proponujący dnia (wsparcie ≥ 2) przy nowych losowych obserwacjach prawie nic nowego nie znajduje. S zużywa 41–54. Kontrast S − W+ przy B = 50 mierzy więc przede wszystkim to, że sen w ogóle generuje sprawdzalne kandydatury, a „więcej dnia” nie. To jest zgodne z hipotezą (sufit wyznacza proponujący), ale W+ jest słabą kontrolą: nie ma w niej żadnego mechanizmu generowania poza oknem.
2. **Sen ma własny sufit.** Przy B = 100 losowe przeczucia (S-los) pokrywają więcej niż S w 4 z 5 praw (np. łączna 29,9 vs 24,9 z 30; idempotentna 28,0 vs 21,2 z 28). S nie proponuje krawędzi, których przesłanka nie wystąpiła w żadnej znanej magmie; S-los tak. Przy dużym budżecie przegląd siłowy wygrywa. Przewaga S to **wydajność przy umiarkowanym budżecie**, nie wyższy sufit ostateczny.
3. **Świat jest łatwy.** Około 25 pojęć, ~600 par; po przycięciu pamięcią kontrprzykładów nawet losowa para jest prawdziwa w 87–93% przypadków. Intuicja jest tu ledwo testowana: heurystyka ma niewiele do wyboru.
4. **Paliwem snu są kontrprzykłady od weryfikatora** (do 50 na wywołanie). Powtórka nie tworzy wiedzy z niczego: konsoliduje informację już zdobytą. W+ dostaje tyle samo magm, ale losowych; kontrprzykłady są z konstrukcji bardziej różnorodne. Wynik mówi „powtórka własnych porażek > tyle samo świeżych losowych epizodów”, nie „sen > dzień” w ogóle.
5. **S ma śmiałe przeczucia (wsparcie 1), których W+ nie ma.** Udziału powtórki i śmiałości nie rozdzielono (było to zapisane w prerejestracji jako znane ograniczenie).

## Status po deflacji

**HIPOTEZA wsparta eksploracyjnie w wąskim świecie** (magmy rzędu 3, ten słownik, ta heurystyka). Nie WYNIK ogólny o śnie ani intuicji.

Co można powiedzieć: w tym świecie faza offline oparta na powtórce kontrprzykładów i konsolidacji grafu przekracza sufit proponującego dnia i robi to wydajniej niż losowe przeczucia przy B = 50.
Czego nie można powiedzieć: że sen podnosi sufit ostateczny (przy B = 100 losowy przegląd go przewyższa) ani że intuicja jest dobra (świat zbyt łatwy, by to rozstrzygnąć).

## Następne kroki (propozycje, nie decyzje)

- **S-0b:** silniejsza kontrola W+ (ten sam generator snu, ale na świeżych losowych magmach zamiast powtórki) i rozdzielenie powtórki od śmiałości.
- **Trudniejszy świat:** magmy rzędu 4 albo większy słownik, żeby losowe pary przestały być w ~90% prawdziwe; dopiero tam intuicja (heurystyka, potem LMM w S-1) ma co rozstrzygać.
- **Niezależny recenzent** tego wyniku przed wpisaniem czegokolwiek do Masterplanu jako WYNIK.
