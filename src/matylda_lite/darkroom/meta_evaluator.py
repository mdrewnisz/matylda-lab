"""Meta-evaluator: Matylda analyzes her own performance."""
from __future__ import annotations
import json
from collections import Counter
from datetime import date, datetime
from ..config import ROOT
from . import disposition as disp
from .pipeline import load_review_records, summarize_review_records

REPORTS_DIR = ROOT / "darkroom" / "meta" / "epistemic_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_recent_failures(n: int = 30) -> list[dict]:
    d = ROOT / "darkroom" / "context" / "failed_attempts"
    if not d.exists():
        return []
    files = sorted(d.glob("*.json"), reverse=True)[:n]
    results = []
    for p in files:
        try:
            results.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return results


def _load_metrics() -> dict:
    p = ROOT / "darkroom" / "meta" / "failure_metrics.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_recent_reviews(n: int = 20) -> list[dict]:
    reviews, _ = load_review_records(limit=n)
    return reviews


def _failure_issues(failures: list[dict]) -> tuple[list[str], Counter]:
    """Extract issue text and reviewer categories from current and legacy records."""
    issues: list[str] = []
    reviewers: Counter = Counter()
    for failure in failures:
        heuristic_failures = failure.get("heuristic_failures")
        if isinstance(heuristic_failures, list):
            for item in heuristic_failures:
                if not isinstance(item, dict):
                    continue
                issue = str(item.get("issue", "")).strip()
                if issue:
                    issues.append(issue)
                    reviewers[str(item.get("reviewer", "unknown"))] += 1

        legacy_issues = failure.get("issues")
        if isinstance(legacy_issues, list):
            issues.extend(
                str(issue).strip()
                for issue in legacy_issues
                if str(issue).strip()
            )
    return issues, reviewers


def _metrics_match(stored: dict, derived: dict) -> bool:
    keys = ("total_reviews", "total_passes", "total_flags", "total_failures")
    return all(stored.get(key) == derived.get(key) for key in keys)


def _review_age_days(timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    try:
        review_date = datetime.strptime(timestamp[:8], "%Y%m%d").date()
    except (TypeError, ValueError):
        return None
    return max(0, (date.today() - review_date).days)


def _build_analysis_data(
    failures: list[dict],
    stored_metrics: dict,
    recent_reviews: list[dict],
    all_reviews: list[dict],
    unreadable_logs: int,
    profile: dict,
) -> dict:
    failure_issues, issue_reviewers = _failure_issues(failures)
    pattern_counts = Counter(
        issue.lower().strip()
        for issue in failure_issues
        if len(issue) > 5
    ).most_common(10)

    recent_metrics = summarize_review_records(recent_reviews)
    all_metrics = summarize_review_records(all_reviews, unreadable_logs)
    quality_issues: list[str] = []
    if recent_metrics["unknown_reviews"]:
        quality_issues.append(
            f"{recent_metrics['unknown_reviews']} recent reviews have no valid verdict"
        )
    if all_metrics["unreadable_review_logs"]:
        quality_issues.append(
            f"{all_metrics['unreadable_review_logs']} review logs are unreadable"
        )
    if recent_metrics["reviewer_errors"]:
        quality_issues.append(
            f"{recent_metrics['reviewer_errors']} reviewer executions failed "
            "in the recent window"
        )
    if not _metrics_match(stored_metrics, all_metrics):
        quality_issues.append(
            "stored counters do not match verdicts derived from review logs"
        )
    review_age_days = _review_age_days(recent_metrics["last_review"])
    if review_age_days is not None and review_age_days > 7:
        quality_issues.append(
            f"latest review is stale ({review_age_days} days old)"
        )

    disposition = {
        key: profile.get(key)
        for key in (
            "skepticism_level",
            "uncertainty_tolerance",
            "falsification_preference",
            "narrative_risk_sensitivity",
            "review_strictness",
            "last_updated",
        )
    }
    return {
        "review_window": {
            "records_loaded": len(recent_reviews),
            "valid_verdicts": recent_metrics["total_reviews"],
            "first_review": recent_metrics["first_review"],
            "last_review": recent_metrics["last_review"],
            "age_days": review_age_days,
            "is_stale": review_age_days is not None and review_age_days > 7,
        },
        "reviews_analyzed": recent_metrics["total_reviews"],
        "pass": recent_metrics["total_passes"],
        "flag": recent_metrics["total_flags"],
        "fail": recent_metrics["total_failures"],
        "unknown_verdicts": recent_metrics["unknown_reviews"],
        "failure_rate": recent_metrics["failure_rate"],
        "flag_rate": recent_metrics["flag_rate"],
        "recent_total_issues": recent_metrics["total_issues"],
        "recent_reviewer_errors": recent_metrics["reviewer_errors"],
        "all_time_from_review_logs": all_metrics,
        "stored_metrics_match_logs": _metrics_match(stored_metrics, all_metrics),
        "telemetry_quality": "ok" if not quality_issues else "degraded",
        "telemetry_quality_issues": quality_issues,
        "top_issue_patterns": pattern_counts[:5],
        "issues_by_reviewer": dict(issue_reviewers.most_common()),
        "repeated_patterns": stored_metrics.get("repeated_patterns", []),
        "disposition": disposition,
    }


def generate_epistemic_report(client) -> dict:
    """Run Haiku self-evaluation. Returns report dict and saves to disk."""
    from ..models import call_with_model_fallback  # noqa: PLC0415

    failures = _load_recent_failures(20)
    metrics = _load_metrics()
    reviews = _load_recent_reviews(20)
    all_reviews, unreadable_logs = load_review_records()
    analysis_data = _build_analysis_data(
        failures,
        metrics,
        reviews,
        all_reviews,
        unreadable_logs,
        disp.load_profile(),
    )

    prompt = f"""Analiza własnej wydajności epistemicznej systemu Matylda Lab.

Dane z ostatnich sesji:
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

Wykonaj ocenę w strukturze:

## 1. Diagnoza głównych wzorców błędów
Na podstawie danych: jakie błędy dominują? Co jest powtarzalne?

## 2. Skuteczność obecnych ustawień disposition
Czy obecna konfiguracja jest właściwa? Oceniaj ją tylko wtedy, gdy dane są
spójne i porównywalne. W przeciwnym razie napisz, że brak podstaw do korekty.

## 3. Rekomendacje korekty
Konkretne propozycje (maks. 3):
- Najpierw wskaż poprawki pomiaru, jeśli telemetry_quality != "ok".
- Parametry disposition wolno zmieniać tylko przy wiarygodnym sygnale.
- Jakie nowe tensje warto obserwować?

## 4. Sygnały ostrzegawcze
Co powinno wymagać uwagi w następnych sesjach?

## 5. Ocena ogólna
Zdanie podsumowujące: czy system poprawia się, stagnuje, czy degeneruje?

Bądź precyzyjny. Nie dyplomatyczny. Opieraj się wyłącznie na dostarczonych danych.
Nie nazywaj dwóch różnych okien trendem. Nie podawaj percentyli bez benchmarku.
Brak lub uszkodzenie danych nie jest ani pass, ani dowodem poprawy."""

    try:
        resp = call_with_model_fallback(
            client, "haiku",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis_text = resp.content[0].text.strip()
    except Exception as e:  # noqa: BLE001
        analysis_text = f"[Błąd generowania raportu: {e}]"

    report = {
        "date": str(date.today()),
        "data": analysis_data,
        "analysis": analysis_text,
        "generated_by": "haiku",
    }

    # Save report
    fname = REPORTS_DIR / f"{date.today().isoformat()}_report.json"
    fname.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return report


def load_latest_report() -> dict | None:
    """Load the most recent epistemic report."""
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    if not files:
        return None
    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except Exception:
        return None
