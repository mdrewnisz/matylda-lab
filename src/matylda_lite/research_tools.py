"""Specialized research prompt builders for Matylda Lab."""
from __future__ import annotations
from datetime import date


def build_literature_map_prompt(topic: str) -> str:
    return f"""Utwórz mapę literatury dla tematu: **{topic}**

Struktura OBOWIĄZKOWA — użyj dokładnie tych sekcji:

## 1. Kluczowe prace i nurty
Podziel na buckety tematyczne (3-6 bucketów). Każdy bucket: nazwa, 2-4 kluczowe pozycje (autor, rok, tytuł lub opis), jedna zdaniowa charakterystyka.

## 2. Główne spory i napięcia
Wymień 2-4 aktywne spory. Format: [Pozycja A] vs [Pozycja B] — co jest stawką.

## 3. Luki i obszary niezbadane
Konkretne pytania bez odpowiedzi. Min. 3 luki.

## 4. Metodologie
Dominujące podejścia metodologiczne, ich ograniczenia.

## 5. Punkty wejścia
3-5 prac, od których warto zacząć (różne poziomy zaawansowania).

## 6. Status epistemiczny mapy
Co jest pewne / co jest sporne / czego nie wiesz o tej literaturze.

Zasady:
- Nie wymyślaj tytułów ani autorów. Opisuj kierunki bez fałszywych cytowań.
- Oznacz jawnie: [SPEKULACJA] gdy szacujesz, [LUKA] gdy czegoś brak.
- Język: dopasuj do tematu (PL/EN).
- Output gotowy do zapisu jako wątek biblioteczny."""


def build_stress_test_prompt(hypothesis: str) -> str:
    return f"""TRYB: STRESS-TEST HIPOTEZY

Hipoteza do analizy:
> {hypothesis}

Wykonaj pełną analizę w strukturze OBOWIĄZKOWEJ:

## 1. Rekonstrukcja hipotezy
Sformułuj hipotezę precyzyjnie. Wskaż co dokładnie twierdzi.

## 2. Ukryte założenia
Wymień wszystkie założenia niezbędne do działania hipotezy. Oceń każde: [UGRUNTOWANE / WĄTPLIWE / NIESPRAWDZALNE].

## 3. Failure modes
Konkretne scenariusze, w których hipoteza jest fałszywa lub bezużyteczna. Min. 4 failure modes z oceną prawdopodobieństwa.

## 4. Alternatywne wyjaśnienia
Co jeszcze mogłoby wyjaśniać te same obserwacje / motywować tę samą konkluzję?

## 5. Minimalne warunki przeżycia
Jakie warunki muszą być spełnione, żeby hipoteza była salvageable? Co minimum musi być prawdą?

## 6. Propozycja falsyfikacji
Jaki eksperyment / obserwacja / argument mógłby definitywnie obalić hipotezę?

## 7. Werdykt epistemiczny
Jedna z trzech opcji z uzasadnieniem:
- **WEAK** — hipoteza nie przeżywa podstawowej krytyki
- **SALVAGEABLE** — hipoteza wymaga istotnych modyfikacji
- **STRUCTURALLY_SOUND** — hipoteza jest odporna na standardową krytykę

Zasady: Bądź precyzyjny i bezlitosny. Nie dyplomatyczny. Nieuzasadniona pewność = błąd."""


def build_synthesis_prompt(threads: list[dict]) -> str:
    threads_text = ""
    for t in threads:
        threads_text += f"\n\n=== WĄTEK: {t['title']} ===\n{t['content'][:8000]}"
        if len(t['content']) > 8000:
            threads_text += f"\n[... skrócono do 8000 znaków z {len(t['content'])}]"

    return f"""TRYB: SYNTEZA CROSS-THREAD

Analizowane wątki ({len(threads)}):
{threads_text}

Wykonaj syntezę w strukturze OBOWIĄZKOWEJ:

## 1. Wspólne wzorce
Co łączy te wątki? Powtarzające się pojęcia, struktury, problemy.

## 2. Napięcia i sprzeczności
Gdzie wątki są ze sobą w konflikcie lub napięciu? Co jest nierozwiązane?

## 3. Luki zbiorowe
Czego brakuje WSZYSTKIM wątkom łącznie? Co jest pominięte systemowo?

## 4. Emergentne pytania
Jakie nowe pytania pojawiają się z zestawienia tych wątków, których nie widać w żadnym z osobna?

## 5. Potencjalne syntezy
3-5 konkretnych propozycji: jak można połączyć te wątki w spójną całość lub projekt?

## 6. Rekomendacja następnego kroku
Jeden konkretny krok, który najlepiej wykorzystuje synergię między tymi wątkami.

Zasady: Szukaj nieoczywistych połączeń. Nie streszczaj — syntezuj."""


def suggested_filename_for_tool(tool: str, subject: str) -> str:
    safe = subject[:40].replace(" ", "_").replace("/", "-")
    today = date.today().isoformat()
    prefixes = {
        "literature_map": f"LITERATURA_{safe}_{today}",
        "stress_test":    f"STRESS_{safe}_{today}",
        "synthesis":      f"SYNTEZA_{safe}_{today}",
    }
    return prefixes.get(tool, f"{tool}_{safe}_{today}") + ".md"
