"""DARKROOM pipeline — pre/post processing hooks for Secretary.

Phase 2:
- All 5 reviewers run in sequence
- Failed/flagged attempts saved to context layer
- Every conversation saved to prompt history
- Repeated pattern detection fires tensions automatically
- Epistemic Limitation Mode: severity sum triggers auto-limitations
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path

from ..config import ROOT
from ..constitutional import BOUNDS
from ..models import MODELS, call_with_model_fallback
from . import context as ctx
from . import disposition as disp
from . import tension as tens
from .reviewers import (
    Review, aggregate,
    run_assumption, run_boundary, run_drift, run_failure, run_reduction, run_skeptic,
)

_APPROVALS_FILE  = ROOT / "darkroom" / "meta" / "pending_approvals.json"
_METRICS_FILE    = ROOT / "darkroom" / "meta" / "failure_metrics.json"
_REVIEW_LOGS_DIR = ROOT / "darkroom" / "meta" / "review_logs"
_VALID_REVIEW_VERDICTS = frozenset({"pass", "flag", "fail"})

_APPROVAL_THRESHOLD  = BOUNDS.approval_severity_threshold   # max_severity >= this → PendingApproval
_EPI_LIMIT_THRESHOLD = BOUNDS.epistemic_limit_threshold      # severity sum >= this → Epistemic Limit Mode


# ── Pre-processing ────────────────────────────────────────────────────────────

def build_darkroom_context(task: str = "") -> str:
    """Build proportional DARKROOM context for injection into a chat prompt.

    The global tension registry remains an audit surface. A normal answer sees
    only a small, task-relevant slice so unrelated historical criticism cannot
    permanently dominate Matylda's voice.
    """
    profile    = disp.load_profile()
    weights    = disp.load_weights()
    tensions   = tens.select_for_task(task, limit=BOUNDS.darkroom_context_max_tensions)
    hal_pats   = tens.load_hallucination_patterns()
    drift_sigs = tens.load_drift_signatures()
    failures   = _relevant_failures(task)

    parts = [
        disp.to_context_string(profile, weights),
        tens.to_context_string(tensions),
    ]

    if hal_pats:
        parts.append(
            "[DARKROOM HALLUCINATION PATTERNS — unikaj]\n"
            + "\n".join(f"  - {p['pattern']}" for p in hal_pats[-3:])
        )

    if drift_sigs:
        parts.append(
            "[DARKROOM DRIFT SIGNATURES — wykryte wcześniej]\n"
            + "\n".join(
                f"  - {s['signature']} (severity={s['severity']})"
                for s in drift_sigs[-3:]
            )
        )

    if failures:
        parts.append(
            "[DARKROOM RECENT FAILURES — nie powtarzaj]\n"
            + "\n".join(
                f"  - [{f['verdict']}] {f['task_preview'][:60]}: "
                + ", ".join(
                    hf["issue"] for hf in f.get("heuristic_failures", [])[:2]
                )
                for f in failures
            )
        )

    return "\n\n".join(parts)


def check_epistemic_limit_mode(task: str | None = None) -> tuple[bool, float]:
    """Return (active, severity_sum), scoped to a task when one is supplied.

    ``None`` intentionally means the global health view used by the dashboard;
    a concrete chat task is evaluated only against related tensions.
    """
    tensions = (
        tens.load_active()
        if task is None
        else tens.select_for_task(task, limit=BOUNDS.darkroom_context_max_tensions)
    )
    sev_sum  = sum(t.get("severity", 0.0) for t in tensions)
    try:
        metrics  = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
        if task is None and metrics.get("failure_rate", 0.0) > BOUNDS.failure_rate_alarm_level:
            sev_sum += BOUNDS.failure_rate_amplifier
    except Exception:  # noqa: BLE001
        pass
    return sev_sum >= _EPI_LIMIT_THRESHOLD, round(sev_sum, 2)


def _relevant_failures(task: str, limit: int = 3) -> list[dict]:
    """Keep old failures local to the subject that produced them."""
    task_terms = set((task or "").lower().split())
    if not task_terms:
        return []
    matches = []
    for failure in ctx.load_recent_failures(n=10):
        preview_terms = set((failure.get("task_preview") or "").lower().split())
        if task_terms & preview_terms:
            matches.append(failure)
    return matches[:limit]


# ── Post-processing ───────────────────────────────────────────────────────────

def run_review(
    task: str,
    result: str,
    model_used: str,
    client,
    messages: list[dict] | None = None,
    saved_to: str | None = None,
) -> dict:
    """
    Run all 5 reviewers. Log. Update context. Detect patterns.
    Returns review summary dict.
    """
    recent_failures = ctx.load_recent_failures(n=10)

    reviews = [
        run_skeptic(task, result, client),
        run_drift(task, result, client),
        run_failure(task, result, recent_failures, client),
        run_reduction(task, result, client),
        run_boundary(task, result, client),
        run_assumption(task, result, client),
    ]
    profile = disp.load_profile()
    summary = aggregate(
        reviews,
        strictness=profile.get("review_strictness", 0.55),
    )

    # Log review
    _log_review(task, result, model_used, summary)

    # Update metrics
    _update_metrics(summary)

    # Save to context layer
    if summary["verdict"] in ("flag", "fail"):
        ctx.save_failed_attempt(
            task=task,
            result_preview=result,
            review_summary=summary,
            model_used=model_used,
            early_signals=_extract_early_signals(reviews),
        )

    # Always save to history
    ctx.save_to_history(
        messages=messages or [{"role": "user", "content": task}],
        result=result,
        model_used=model_used,
        review_summary=summary,
        saved_to=saved_to,
    )

    # Create tensions from reviews
    if summary["verdict"] in ("flag", "fail"):
        _create_tensions_from_reviews(
            reviews,
            task,
            min_severity=summary["review_threshold"],
        )

    # Repeated pattern detection
    repeated = ctx.detect_repeated_patterns()
    for pat in repeated:
        _ensure_pattern_tension(pat)

    # Pending approval if severity is high enough
    pending_approval = None
    if summary["max_severity"] >= _APPROVAL_THRESHOLD:
        pending_approval = _create_pending_approval(
            summary,
            task,
            repeated_patterns=repeated,
        )

    summary["pending_approval"] = pending_approval
    summary["repeated_patterns_detected"] = len(repeated)
    return summary


# ── Internal helpers ──────────────────────────────────────────────────────────

def _log_review(task: str, result: str, model_used: str, summary: dict) -> None:
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    log = {
        "schema_version": 2,
        "timestamp": ts,
        "task_preview": task[:120],
        "model_used": model_used,
        "result_preview": result[:300],
        "verdict": summary.get("verdict"),
        "max_severity": summary.get("max_severity"),
        "summary": summary,
    }
    (_REVIEW_LOGS_DIR / f"review_{ts}.json").write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def review_verdict(record: dict) -> str | None:
    """Read a review verdict from current and legacy log schemas."""
    verdict = record.get("verdict")
    if verdict not in _VALID_REVIEW_VERDICTS:
        summary = record.get("summary")
        verdict = summary.get("verdict") if isinstance(summary, dict) else None
    return verdict if verdict in _VALID_REVIEW_VERDICTS else None


def load_review_records(limit: int | None = None) -> tuple[list[dict], int]:
    """Load review logs and return records plus the unreadable-file count."""
    files = sorted(_REVIEW_LOGS_DIR.glob("*.json"))
    if limit is not None:
        files = files[-limit:]

    records: list[dict] = []
    unreadable = 0
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(record, dict):
                records.append(record)
            else:
                unreadable += 1
        except (OSError, json.JSONDecodeError):
            unreadable += 1
    return records, unreadable


def summarize_review_records(records: list[dict], unreadable: int = 0) -> dict:
    """Build counters without treating missing or malformed data as pass."""
    verdicts = [review_verdict(record) for record in records]
    valid_verdicts = [verdict for verdict in verdicts if verdict is not None]
    total = len(valid_verdicts)

    reviewer_errors = 0
    total_issues = 0
    for record in records:
        summary = record.get("summary")
        if not isinstance(summary, dict):
            continue
        reviews = summary.get("reviews")
        if not isinstance(reviews, list):
            reviews = []
        reviewer_errors += sum(
            1
            for review in reviews
            if isinstance(review, dict)
            and str(review.get("notes", "")).startswith("[REVIEWER ERROR:")
        )
        issues = summary.get("total_issues")
        if isinstance(issues, int):
            total_issues += issues
        else:
            total_issues += sum(
                len(review.get("issues", []))
                for review in reviews
                if isinstance(review, dict) and isinstance(review.get("issues"), list)
            )

    timestamps = [
        str(record["timestamp"])
        for record in records
        if record.get("timestamp")
    ]
    failure_timestamps = [
        str(record.get("timestamp", ""))
        for record, verdict in zip(records, verdicts)
        if verdict == "fail"
    ]
    last_failure = None
    if failure_timestamps and len(failure_timestamps[-1]) >= 8:
        raw = failure_timestamps[-1]
        last_failure = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"

    pass_count = valid_verdicts.count("pass")
    flag_count = valid_verdicts.count("flag")
    fail_count = valid_verdicts.count("fail")
    unknown = len(records) - total
    return {
        "schema_version": 2,
        "total_reviews": total,
        "total_review_logs": len(records) + unreadable,
        "total_passes": pass_count,
        "total_flags": flag_count,
        "total_failures": fail_count,
        "unknown_reviews": unknown,
        "unreadable_review_logs": unreadable,
        "failure_rate": round(fail_count / total, 3) if total else 0.0,
        "flag_rate": round(flag_count / total, 3) if total else 0.0,
        "pass_rate": round(pass_count / total, 3) if total else 0.0,
        "reviewer_errors": reviewer_errors,
        "total_issues": total_issues,
        "first_review": timestamps[0] if timestamps else None,
        "last_review": timestamps[-1] if timestamps else None,
        "last_failure": last_failure,
        "telemetry_status": (
            "ok"
            if unknown == 0 and unreadable == 0 and reviewer_errors == 0
            else "degraded"
        ),
    }


def current_review_metrics() -> dict:
    """Derive the current metrics snapshot from review logs."""
    records, unreadable = load_review_records()
    metrics = summarize_review_records(records, unreadable)
    try:
        stored = json.loads(_METRICS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        stored = {}
    metrics["repeated_patterns"] = stored.get("repeated_patterns", [])
    return metrics


def _update_metrics(summary: dict) -> None:
    del summary
    data = current_review_metrics()
    _METRICS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _extract_early_signals(reviews: list[Review]) -> list[str]:
    signals = []
    for r in reviews:
        if r.severity >= 0.3 and r.notes and "[REVIEWER ERROR" not in r.notes:
            signals.append(f"{r.reviewer}: {r.notes}")
    return signals


def _create_tensions_from_reviews(
    reviews: list[Review],
    task: str,
    min_severity: float = 0.3,
) -> None:
    # Lifecycle policy: trivial queries never spawn tensions. The review still
    # ran and still surfaced issues in the response — we just don't persist a
    # cognitive conflict for a throwaway lookup ("1+1=?", short one-liners).
    if tens.is_trivial_query(task):
        return
    existing = {t["description"][:60] for t in tens.load_active()}
    for r in reviews:
        if r.severity < min_severity or not r.issues:
            continue
        t_type = "drift_signature" if r.reviewer == "drift" else "unresolved_critique"
        for issue in r.issues[:2]:
            if issue[:60] not in existing:
                tens.create(
                    description=issue,
                    tension_type=t_type,
                    severity=r.severity,
                    source_task=task,
                )
        if r.reviewer == "drift" and r.issues:
            tens.add_drift_signature(r.issues[0], r.severity, task)


def _ensure_pattern_tension(pattern: dict) -> None:
    """Create a tension for a repeated pattern (if not already tracked)."""
    existing_descs = {t["description"][:50] for t in tens.load_active()}
    desc = f"Repeated pattern ({pattern['count']}×): {pattern['issue'][:80]}"
    if desc[:50] not in existing_descs:
        severity = min(1.0, 0.4 + pattern["count"] * 0.08)
        tens.create(
            description=desc,
            tension_type="hallucination_pattern",
            severity=severity,
            source_task=f"pattern_detection ({pattern['count']} occurrences)",
        )


def _create_pending_approval(
    summary: dict,
    task: str,
    repeated_patterns: list[dict] | None = None,
) -> dict | None:
    """Propose a global calibration change only from repeated, reliable evidence."""
    recent_records, unreadable = load_review_records(limit=20)
    recent_metrics = summarize_review_records(recent_records, unreadable)
    if not repeated_patterns or recent_metrics["telemetry_status"] != "ok":
        return None

    profile  = disp.load_profile()
    proposed = {}

    reviews_by_name = {r["reviewer"]: r for r in summary.get("reviews", [])}

    def propose_increase(key: str, delta: float) -> None:
        current = float(profile.get(key, 0.5))
        ceiling = disp.automatic_approval_ceiling(key)
        target = round(min(ceiling, current + delta), 2)
        if target > current:
            proposed[key] = {"from": current, "to": target}

    if reviews_by_name.get("drift", {}).get("severity", 0) >= 0.4:
        propose_increase("narrative_risk_sensitivity", 0.05)

    if reviews_by_name.get("skeptic", {}).get("severity", 0) >= 0.4:
        propose_increase("review_strictness", 0.05)

    if reviews_by_name.get("boundary", {}).get("severity", 0) >= 0.4:
        propose_increase("falsification_preference", 0.03)

    if reviews_by_name.get("reduction", {}).get("severity", 0) >= 0.4:
        k = "verbosity_calibration"
        c = profile.get(k, 0.5)
        proposed[k] = {"from": c, "to": round(max(0.0, c - 0.05), 2)}

    if not proposed:
        return None

    approval = {
        "id": f"approval_{uuid.uuid4().hex[:8]}",
        "created": str(date.today()),
        "trigger": f"max_severity={summary['max_severity']:.2f}, verdict={summary['verdict']}",
        "task_preview": task[:80],
        "proposed_changes": proposed,
        "review_summary": {k: v for k, v in summary.items() if k not in ("reviews", "pending_approval")},
        "status": "pending",
    }

    data = json.loads(_APPROVALS_FILE.read_text(encoding="utf-8"))
    data["approvals"].append(approval)
    _APPROVALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return approval


# ── Confidence topology ───────────────────────────────────────────────────────

def run_confidence_topology(task: str, result: str, client) -> dict:
    """Quick Haiku call to classify response stability. Returns topology dict."""
    _TOPO_SYSTEM = (
        "You are an epistemic classifier. Respond ONLY with valid JSON, no prose."
    )
    _TOPO_PROMPT = (
        f"Analyze this response and classify its claims by epistemic status.\n\n"
        f"TASK: {task[:200]}\n\nRESPONSE: {result[:1500]}\n\n"
        "Return JSON with exactly these keys:\n"
        '{"stable":["..."],"heuristic":["..."],"speculative":["..."],'
        '"data_required":["..."],"overall_stability":0.0}\n'
        "stable = well-supported claims; heuristic = estimates/analogies presented as such; "
        "speculative = hypotheses/extrapolations; data_required = claims needing empirical verification. "
        "overall_stability = fraction of content that is stable (0.0-1.0). "
        "Cap each list at 3 items."
    )
    try:
        resp = call_with_model_fallback(
            client, "haiku",
            max_tokens=512,
            system=_TOPO_SYSTEM,
            messages=[{"role": "user", "content": _TOPO_PROMPT}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:]).rstrip("`").strip()
        data = json.loads(text)
        # Cap each list at 3 items
        for key in ("stable", "heuristic", "speculative", "data_required"):
            if isinstance(data.get(key), list):
                data[key] = data[key][:3]
        if "overall_stability" not in data:
            data["overall_stability"] = 0.5
        return data
    except Exception:  # noqa: BLE001
        return {"error": "parse failed", "overall_stability": 0.5}


# ── NO-GO system prompt ───────────────────────────────────────────────────────

def build_nogo_system_prompt(hypothesis: str = "") -> str:
    """Returns a system prompt override for NO-GO mode."""
    darkroom_context = build_darkroom_context()
    return (
        "You are Matylda in NO-GO mode — active hypothesis destructor.\n\n"
        "Your ONLY job: find every way this argument/hypothesis can be wrong, "
        "incomplete, or unfalsifiable.\n\n"
        "Rules:\n"
        "- Do NOT be diplomatic. Be precise and ruthless.\n"
        "- Find hidden assumptions and name them explicitly.\n"
        "- Generate concrete failure modes, not vague concerns.\n"
        "- Propose the minimum conditions under which the hypothesis could survive (if any).\n"
        "- Structure: (1) Core vulnerabilities, (2) Hidden assumptions, "
        "(3) Failure modes, (4) Minimum survival conditions.\n"
        "- End with: Epistemic verdict: WEAK / SALVAGEABLE / STRUCTURALLY_SOUND\n\n"
        f"{darkroom_context}"
    )


# ── Approvals ─────────────────────────────────────────────────────────────────

def load_pending_approvals() -> list[dict]:
    data = json.loads(_APPROVALS_FILE.read_text(encoding="utf-8"))
    return [a for a in data["approvals"] if a.get("status") == "pending"]


def approve(approval_id: str) -> dict:
    data = json.loads(_APPROVALS_FILE.read_text(encoding="utf-8"))
    approved = None
    for a in data["approvals"]:
        if a["id"] == approval_id and a["status"] == "pending":
            a["status"] = "approved"
            a["approved"] = str(date.today())
            approved = a
            break
    if not approved:
        raise ValueError(f"Approval {approval_id} not found or not pending")
    _APPROVALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    updated_profile = disp.apply_approval(approved["proposed_changes"])
    from .disposition import log_disposition_snapshot  # noqa: PLC0415
    log_disposition_snapshot(updated_profile, trigger=f"approval:{approval_id}")
    return updated_profile


def reject(approval_id: str) -> None:
    data = json.loads(_APPROVALS_FILE.read_text(encoding="utf-8"))
    for a in data["approvals"]:
        if a["id"] == approval_id and a["status"] == "pending":
            a["status"] = "rejected"
            a["rejected"] = str(date.today())
            break
    _APPROVALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Status ────────────────────────────────────────────────────────────────────

def darkroom_status() -> dict:
    profile  = disp.load_profile()
    weights  = disp.load_weights()
    tensions = tens.load_active()
    metrics  = current_review_metrics()
    pending  = load_pending_approvals()
    epi_active, epi_sum = check_epistemic_limit_mode()

    last_review = None
    logs = sorted(_REVIEW_LOGS_DIR.glob("*.json"))
    if logs:
        try:
            last_review = json.loads(logs[-1].read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass

    recent_history = ctx.load_recent_history(n=10)

    structural_score = 0.0
    epistemic_score  = 0.0
    if last_review:
        summary = last_review.get("summary", {})
        structural_score = float(summary.get("structural_score", 0.0))
        epistemic_score  = float(summary.get("epistemic_score",  0.0))

    from .disposition import load_disposition_history  # noqa: PLC0415
    return {
        "disposition": profile,
        "weights": weights,
        "active_tensions": tensions,
        "metrics": metrics,
        "pending_approvals": pending,
        "last_review": last_review,
        "epistemic_limit_mode": {"active": epi_active, "severity_sum": epi_sum},
        "recent_history": recent_history,
        "structural_score": structural_score,
        "epistemic_score": epistemic_score,
        "disposition_history": load_disposition_history(),
    }


_VALIDATE_SYSTEM = """\
Jesteś niezależnym walidatorem epistemicznym systemu DARKROOM.
Oceń, czy podane twierdzenie jest wystarczająco poparte dostarczonymi źródłami/dowodami.

Odpowiedz TYLKO poprawnym JSON (bez prozy, bez markdown):
{"verdict":"supported"|"partial"|"unsupported","confidence":0.0-1.0,"missing_evidence":["brakujący dowód 1"],"notes":"jedno zdanie"}

Werdykt:
  supported   — twierdzenie solidnie poparte (confidence ≥ 0.7)
  partial     — częściowe wsparcie, luki w dowodach (confidence 0.3–0.7)
  unsupported — brak wystarczających dowodów (confidence < 0.3)
"""


def validate_finding(claim: str, sources: list[str], client) -> dict:
    """Validate a research claim with opus as independent epistemic reviewer.

    Returns dict with verdict, confidence, missing_evidence, notes.
    """
    import uuid as _uuid  # noqa: PLC0415

    sources_text = "\n".join(f"- {s}" for s in sources) if sources else "(brak źródeł)"
    user_msg = f"TWIERDZENIE:\n{claim}\n\nDOSTĘPNE ŹRÓDŁA/DOWODY:\n{sources_text}"
    raw = ""
    try:
        resp = call_with_model_fallback(
            client, "opus",
            max_tokens=512,
            system=_VALIDATE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "verdict": "unsupported",
            "confidence": 0.0,
            "missing_evidence": ["parse error — invalid opus response"],
            "notes": raw[:200],
        }
    except Exception as e:  # noqa: BLE001
        result = {
            "verdict": "unsupported",
            "confidence": 0.0,
            "missing_evidence": [],
            "notes": f"validation error: {e}",
        }

    result["claim_preview"] = claim[:120]
    result["source_count"] = len(sources)
    result["validation_id"] = "val_" + _uuid.uuid4().hex[:8]
    return result


def compare_models(task: str, client) -> dict:
    """Run task on haiku/sonnet/opus, review each. Returns comparison dict."""
    from .reviewers import run_skeptic, run_reduction, aggregate  # noqa: PLC0415

    results = {}
    for model_key in ("haiku", "sonnet", "opus"):
        try:
            resp = call_with_model_fallback(
                client, model_key,
                max_tokens=2048,
                messages=[{"role": "user", "content": task}],
            )
            result_text = resp.content[0].text.strip()
            # Quick 2-reviewer check (fast)
            skeptic   = run_skeptic(task, result_text, client)
            reduction = run_reduction(task, result_text, client)
            agg = aggregate([skeptic, reduction])
            topology = run_confidence_topology(task, result_text, client)
            results[model_key] = {
                "result":   result_text,
                "model_id": resp.model,
                "verdict":  agg["verdict"],
                "severity": agg["max_severity"],
                "issues":   agg["total_issues"],
                "topology": topology,
            }
        except Exception as e:  # noqa: BLE001
            results[model_key] = {"error": str(e), "model_id": MODELS[model_key]}

    return results
