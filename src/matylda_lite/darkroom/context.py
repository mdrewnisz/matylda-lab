"""Context layer — persistent memory of failure trajectories and prompt history.

Stores:
- failed_attempts/  : why something failed, what heuristic, early signals
- prompt_history/   : every conversation with metadata
- no_go_results/    : explicit no-go conclusions reached

The Failure Reviewer reads from failed_attempts to detect repeated patterns.
Pattern detection fires when the same issue appears >= REPEAT_THRESHOLD times.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

from ..config import ROOT

_FAILED_DIR  = ROOT / "darkroom" / "context" / "failed_attempts"
_HISTORY_DIR = ROOT / "darkroom" / "context" / "prompt_history"
_NOGO_DIR    = ROOT / "darkroom" / "context" / "no_go_results"
_METRICS     = ROOT / "darkroom" / "meta" / "failure_metrics.json"

REPEAT_THRESHOLD = 3   # pattern fires when issue count >= this


# ── Failed attempts ───────────────────────────────────────────────────────────

def save_failed_attempt(
    task: str,
    result_preview: str,
    review_summary: dict,
    model_used: str,
    early_signals: list[str] | None = None,
) -> Path:
    """Persist a failed/flagged attempt with full diagnostic context."""
    ts  = datetime.now().strftime("%Y%m%dT%H%M%S")
    fid = f"fail_{ts}_{uuid.uuid4().hex[:6]}"

    reviews = review_summary.get("reviews", [])
    heuristic_failures = [
        {"reviewer": r["reviewer"], "issue": i}
        for r in reviews
        for i in r.get("issues", [])
    ]

    record = {
        "id": fid,
        "timestamp": ts,
        "task_preview": task[:200],
        "result_preview": result_preview[:400],
        "verdict": review_summary.get("verdict", "unknown"),
        "max_severity": review_summary.get("max_severity", 0.0),
        "model_used": model_used,
        "heuristic_failures": heuristic_failures,
        "early_signals": early_signals or [],
        "reviewer_notes": [r.get("notes", "") for r in reviews if r.get("notes")],
    }

    p = _FAILED_DIR / f"{fid}.json"
    p.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def load_recent_failures(n: int = 10) -> list[dict]:
    files = sorted(_FAILED_DIR.glob("*.json"), reverse=True)[:n]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return out


# ── Prompt history ────────────────────────────────────────────────────────────

def save_to_history(
    messages: list[dict],
    result: str,
    model_used: str,
    review_summary: dict,
    saved_to: str | None = None,
) -> Path:
    ts  = datetime.now().strftime("%Y%m%dT%H%M%S")
    hid = f"hist_{ts}_{uuid.uuid4().hex[:6]}"

    record = {
        "id": hid,
        "timestamp": ts,
        "turn_count": len(messages),
        "last_task": next(
            (m["content"][:200] for m in reversed(messages) if m["role"] == "user"), ""
        ),
        "result_preview": result[:400],
        "model_used": model_used,
        "verdict": review_summary.get("verdict", "pass"),
        "max_severity": review_summary.get("max_severity", 0.0),
        "saved_to": saved_to,
    }

    p = _HISTORY_DIR / f"{hid}.json"
    p.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def load_recent_history(n: int = 20) -> list[dict]:
    files = sorted(_HISTORY_DIR.glob("*.json"), reverse=True)[:n]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return out


# ── Pattern detection ─────────────────────────────────────────────────────────

def detect_repeated_patterns(threshold: int = REPEAT_THRESHOLD) -> list[dict]:
    """
    Scan all failure records and count issue occurrences.
    Returns patterns that have reached or exceeded `threshold`.
    """
    issue_records: dict[str, list[str]] = {}  # issue_text → [task_previews]

    for record in load_recent_failures(n=50):
        for hf in record.get("heuristic_failures", []):
            issue = hf.get("issue", "").strip()
            if not issue:
                continue
            # Normalize: lowercase, strip trailing punctuation
            key = issue.lower().rstrip(".!?,;")
            if key not in issue_records:
                issue_records[key] = []
            issue_records[key].append(record.get("task_preview", "")[:60])

    repeated = []
    for issue, tasks in issue_records.items():
        if len(tasks) >= threshold:
            repeated.append({
                "issue": issue,
                "count": len(tasks),
                "example_tasks": tasks[:3],
            })

    # Persist to failure_metrics
    _update_repeated_patterns(repeated)
    return repeated


def _update_repeated_patterns(patterns: list[dict]) -> None:
    try:
        data = json.loads(_METRICS.read_text(encoding="utf-8"))
        data["repeated_patterns"] = patterns
        _METRICS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


# ── No-go results ─────────────────────────────────────────────────────────────

def save_nogo(title: str, summary: str, task: str) -> Path:
    ts  = datetime.now().strftime("%Y%m%dT%H%M%S")
    nid = f"nogo_{ts}"
    record = {"id": nid, "timestamp": ts, "title": title,
              "summary": summary[:800], "task": task[:200]}
    p = _NOGO_DIR / f"{nid}.json"
    p.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return p
