"""DARKROOM reviewers — all five (Phase 2).

Reviewers must disagree when appropriate.
Consensus is NOT required.
Each reviewer is a separate Haiku call with a specialized adversarial prompt.

Phase 1: Skeptic, Drift
Phase 2: Failure, Reduction, Boundary
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..models import call_with_model_fallback


@dataclass
class Review:
    reviewer: str
    verdict: str            # "pass" | "flag" | "fail"
    issues: list[str]
    severity: float         # 0.0 – 1.0
    confidence_adjustment: float  # -0.2 … +0.1
    notes: str
    critique_type: str = "epistemic"  # "epistemic" | "structural"

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "verdict": self.verdict,
            "issues": self.issues,
            "severity": self.severity,
            "confidence_adjustment": self.confidence_adjustment,
            "notes": self.notes,
            "critique_type": self.critique_type,
        }


# ── 1. Skeptic ────────────────────────────────────────────────────────────────

_SKEPTIC_SYSTEM = """\
Jesteś Skeptic Reviewer dla systemu DARKROOM.
Zadanie: znajdź nieuzasadnione założenia i twierdzenia w tekście.

Oceń:
- Czy twierdzenia są poparte dowodami?
- Czy autorowi brakuje epistemic humility?
- Czy tekst overclaims — mówi więcej niż może wiedzieć?
- Czy wnioski przekraczają dane?

Odpowiedz TYLKO poprawnym JSON (bez prozy, bez markdown):
{"verdict":"pass|flag|fail","issues":["issue1"],"severity":0.0-1.0,"confidence_adjustment":-0.2-0.1,"notes":"jedno zdanie"}

Werdykt: pass=brak problemów | flag=severity 0.3-0.6 | fail=severity>0.6
"""


def run_skeptic(task: str, result: str, client) -> Review:
    return _call(client, "skeptic", _SKEPTIC_SYSTEM,
                 f"ZADANIE:\n{task[:300]}\n\nODPOWIEDŹ:\n{result[:2000]}",
                 critique_type="epistemic")


# ── 2. Drift ──────────────────────────────────────────────────────────────────

_DRIFT_SYSTEM = """\
Jesteś Drift Reviewer dla systemu DARKROOM.
Zadanie: wykryj narrative drift i symbolic overfitting.

Szukaj:
- nadmiernej spójności symbolicznej (wszystko ładnie pasuje — podejrzane)
- inflacji narracyjnej (tekst staje się opowieścią zamiast analizą)
- języka antropomorficznego (system "czuje", "wie", "pragnie")
- recursive mythology (system opisuje siebie jako coś głębszego niż jest)
- overconfident abstraction
- estetycznej koherencji mylonej z prawdą

Odpowiedz TYLKO poprawnym JSON:
{"verdict":"pass|flag|fail","issues":["drift_pattern"],"severity":0.0-1.0,"confidence_adjustment":-0.2-0.0,"notes":"jedno zdanie"}

Werdykt: pass=brak driftu | flag=łagodny drift 0.2-0.5 | fail=poważny>0.5
"""


def run_drift(task: str, result: str, client) -> Review:
    return _call(client, "drift", _DRIFT_SYSTEM,
                 f"ZADANIE:\n{task[:300]}\n\nODPOWIEDŹ:\n{result[:2000]}",
                 critique_type="structural")


# ── 3. Failure ────────────────────────────────────────────────────────────────

_FAILURE_SYSTEM = """\
Jesteś Failure Reviewer dla systemu DARKROOM.
Zadanie: sprawdź czy ten błąd już był popełniony wcześniej.

Masz dostęp do historii poprzednich niepowodzeń systemu.
Porównaj bieżącą odpowiedź z wzorcami błędów z przeszłości.

Szukaj:
- powtórzenia tego samego błędu co w poprzednich próbach
- ignorowania wcześniejszych ostrzeżeń
- nawrotu do odrzuconych interpretacji
- powtarzania tych samych halucynacji

Odpowiedz TYLKO poprawnym JSON:
{"verdict":"pass|flag|fail","issues":["repeated_pattern"],"severity":0.0-1.0,"confidence_adjustment":-0.2-0.0,"notes":"jedno zdanie"}

Jeśli nie ma historii błędów do porównania — zwróć pass z severity=0.0.
"""


def run_failure(
    task: str,
    result: str,
    recent_failures: list[dict],
    client,
) -> Review:
    if not recent_failures:
        return Review(
            reviewer="failure", verdict="pass", issues=[],
            severity=0.0, confidence_adjustment=0.0,
            notes="brak historii błędów do porównania",
            critique_type="epistemic",
        )

    failure_summary = "\n".join(
        f"- [{f['verdict']}] {f['task_preview'][:60]} → "
        + ", ".join(
            hf["issue"] for hf in f.get("heuristic_failures", [])[:2]
        )
        for f in recent_failures[:5]
    )

    prompt = (
        f"HISTORIA POPRZEDNICH BŁĘDÓW:\n{failure_summary}\n\n"
        f"BIEŻĄCE ZADANIE:\n{task[:300]}\n\n"
        f"BIEŻĄCA ODPOWIEDŹ:\n{result[:1500]}"
    )
    return _call(client, "failure", _FAILURE_SYSTEM, prompt, critique_type="epistemic")


# ── 4. Reduction ──────────────────────────────────────────────────────────────

_REDUCTION_SYSTEM = """\
Jesteś Reduction Reviewer dla systemu DARKROOM.
Zadanie: oceń czy odpowiedź jest nadmiernie złożona.

Zasada: jeśli prostsze wyjaśnienie jest możliwe i wystarczające — złożone jest złe.

Szukaj:
- zbędnej złożoności pojęciowej
- wyjaśnień gdzie prostsze byłoby dokładniejsze
- niepotrzebnych warstw abstrakcji
- nadmiernej długości bez proporcjonalnej wartości
- terminologii użytej dla efektu, nie precyzji

Odpowiedz TYLKO poprawnym JSON:
{"verdict":"pass|flag|fail","issues":["complexity_issue"],"severity":0.0-1.0,"confidence_adjustment":-0.1-0.05,"notes":"jedno zdanie"}

Werdykt: pass=złożoność uzasadniona | flag=można uprościć | fail=złożoność maskuje braki
"""


def run_reduction(task: str, result: str, client) -> Review:
    return _call(client, "reduction", _REDUCTION_SYSTEM,
                 f"ZADANIE:\n{task[:300]}\n\nODPOWIEDŹ:\n{result[:2000]}",
                 critique_type="structural")


# ── 5. Boundary ───────────────────────────────────────────────────────────────

_BOUNDARY_SYSTEM = """\
Jesteś Boundary Reviewer dla systemu DARKROOM.
Zadanie: sprawdź czy wnioski przekraczają dostępne dane i wiedzę.

Oceń:
- Czy model twierdzi że wie coś czego nie może wiedzieć?
- Czy wnioski wykraczają poza to co było pytane?
- Czy spekulacja jest oznaczona jako spekulacja?
- Czy tekst wkracza w dziedziny bez odpowiednich zastrzeżeń?
- Gdzie kończy się wiedza, a zaczyna domysł?

Odpowiedz TYLKO poprawnym JSON:
{"verdict":"pass|flag|fail","issues":["boundary_violation"],"severity":0.0-1.0,"confidence_adjustment":-0.2-0.0,"notes":"jedno zdanie"}

Werdykt: pass=granice respektowane | flag=granice naciągnięte | fail=granice przekroczone
"""


def run_boundary(task: str, result: str, client) -> Review:
    return _call(client, "boundary", _BOUNDARY_SYSTEM,
                 f"ZADANIE:\n{task[:300]}\n\nODPOWIEDŹ:\n{result[:2000]}",
                 critique_type="epistemic")


# ── 6. Assumption ─────────────────────────────────────────────────────────────

_ASSUMPTION_SYSTEM = """\
You are an assumption auditor. Respond ONLY with JSON.

Examine the result for:
- hidden assumptions treated as facts
- unmarked speculation presented as analysis
- missing "I don't know" where appropriate
- unjustified confidence in uncertain areas

Respond ONLY with valid JSON (no prose, no markdown):
{"verdict":"pass|flag|fail","issues":["issue1"],"severity":0.0-1.0,"confidence_adjustment":-0.3-0.0,"notes":"one sentence"}

Verdict: pass=no problematic assumptions | flag=some unmarked assumptions | fail=pervasive assumption violations
"""


def run_assumption(task: str, result: str, client) -> Review:
    return _call(
        client, "assumption", _ASSUMPTION_SYSTEM,
        f"TASK:\n{task[:300]}\n\nRESULT:\n{result[:2000]}",
        critique_type="epistemic",
    )


# ── Shared call ───────────────────────────────────────────────────────────────

def _call(client, name: str, system: str, prompt: str, critique_type: str = "epistemic") -> Review:
    try:
        resp = call_with_model_fallback(
            client, "haiku",
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:]).rstrip("`").strip()
        data = json.loads(text)
        return Review(
            reviewer=name,
            verdict=data.get("verdict", "pass"),
            issues=data.get("issues", []),
            severity=float(data.get("severity", 0.0)),
            confidence_adjustment=float(data.get("confidence_adjustment", 0.0)),
            notes=data.get("notes", ""),
            critique_type=critique_type,
        )
    except Exception as e:  # noqa: BLE001
        return Review(
            reviewer=name, verdict="pass", issues=[],
            severity=0.0, confidence_adjustment=0.0,
            notes=f"[REVIEWER ERROR: {e}]",
            critique_type=critique_type,
        )


# ── Aggregation ───────────────────────────────────────────────────────────────

_STRUCTURAL_REVIEWERS  = {"drift", "reduction"}
_EPISTEMIC_REVIEWERS   = {"skeptic", "boundary", "failure", "assumption"}


def aggregate(reviews: list[Review], strictness: float = 1.0) -> dict:
    strictness = max(0.0, min(1.0, float(strictness)))
    review_threshold = round(0.70 - 0.40 * strictness, 2)
    if not reviews:
        return {
            "verdict": "pass", "max_severity": 0.0, "total_issues": 0, "reviews": [],
            "structural_score": 0.0, "epistemic_score": 0.0,
            "critique_breakdown": {"structural": [], "epistemic": []},
            "review_threshold": review_threshold,
            "review_strictness": strictness,
        }
    effective_reviews = [
        r for r in reviews
        if r.verdict in ("flag", "fail") and r.severity >= review_threshold
    ]
    verdicts    = [r.verdict for r in effective_reviews]
    verdict     = "fail" if "fail" in verdicts else "flag" if "flag" in verdicts else "pass"
    max_sev     = max(r.severity for r in reviews)
    all_issues  = [i for r in reviews for i in r.issues]

    structural_reviews = [r for r in reviews if r.reviewer in _STRUCTURAL_REVIEWERS]
    epistemic_reviews  = [r for r in reviews if r.reviewer in _EPISTEMIC_REVIEWERS]

    structural_score = (
        round(sum(r.severity for r in structural_reviews) / len(structural_reviews), 3)
        if structural_reviews else 0.0
    )
    epistemic_score = (
        round(sum(r.severity for r in epistemic_reviews) / len(epistemic_reviews), 3)
        if epistemic_reviews else 0.0
    )

    critique_breakdown = {
        "structural": [r.reviewer for r in structural_reviews if r in effective_reviews],
        "epistemic":  [r.reviewer for r in epistemic_reviews if r in effective_reviews],
    }

    return {
        "verdict": verdict,
        "max_severity": round(max_sev, 2),
        "total_issues": len(all_issues),
        "reviews": [r.to_dict() for r in reviews],
        "structural_score": structural_score,
        "epistemic_score": epistemic_score,
        "critique_breakdown": critique_breakdown,
        "review_threshold": review_threshold,
        "review_strictness": strictness,
    }
