"""Tension layer — persistent unresolved cognitive conflicts.

Tensions are first-class cognitive artifacts. They must NOT be
aggressively resolved. They influence future generation by
suppressing overconfidence and triggering additional review.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Literal

from ..config import ROOT

_ACTIVE_DIR  = ROOT / "darkroom" / "tension" / "active"
_ARCHIVE_DIR = ROOT / "darkroom" / "tension" / "archive"
_HAL_FILE    = ROOT / "darkroom" / "tension" / "hallucination_patterns.json"
_DRIFT_FILE  = ROOT / "darkroom" / "tension" / "drift_signatures.json"

TensionType = Literal[
    "conceptual_conflict",
    "unresolved_critique",
    "hallucination_pattern",
    "drift_signature",
    "boundary_violation",
    "contradiction",
]


def load_active() -> list[dict]:
    tensions = []
    for p in sorted(_ACTIVE_DIR.glob("*.json")):
        try:
            tensions.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return tensions


def create(
    description: str,
    tension_type: TensionType,
    severity: float,
    source_task: str = "",
) -> dict:
    tid = f"tension_{uuid.uuid4().hex[:8]}"
    t = {
        "id": tid,
        "created": str(date.today()),
        "type": tension_type,
        "description": description,
        "severity": round(max(0.0, min(1.0, severity)), 2),
        "source_task": source_task[:120],
        "review_count": 0,
        "status": "active",
    }
    (_ACTIVE_DIR / f"{tid}.json").write_text(
        json.dumps(t, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return t


# ── Tension lifecycle policy ───────────────────────────────────────────────────
# Operator policy (2026-06-21):
#   - trivial queries        → never create a tension at all
#   - ordinary (sev < CRITICAL) → auto-archive after 30 days
#   - critical (sev ≥ CRITICAL) → stay until the operator decides
CRITICAL_THRESHOLD = 0.8     # only genuinely critical conflicts persist indefinitely
MEDIUM_AGE_DAYS    = 30      # medium tensions expire after this many days
_TRIVIAL_QUERY_MAX_LEN = 40  # source queries shorter than this are throwaway

_TEST_SOURCE_MARKERS = (
    "smoke test", "smoke_test", "benchmark zerowy",
    "1+1", "co to jest haiku", "odpowiedz jednym zdaniem",
    "odpowiedz:", "test trace", "1+1=", "1 zdanie",
)

_CONTEXT_STOPWORDS = {
    "about", "after", "before", "będzie", "czyli", "danych", "dla",
    "jest", "jako", "jego", "kiedy", "która", "które", "który", "mają",
    "mamy", "może", "niego", "oraz", "przez", "tego", "tutaj", "using",
    "warto", "with", "wtedy", "which", "właśnie", "został", "została",
}


def is_trivial_query(task: str) -> bool:
    """True if `task` is a throwaway query that should NOT spawn a tension.

    Tensions track unresolved *cognitive conflicts*. A trivial lookup
    ("1+1=?", "what is haiku in one sentence") has no conflict to track, so
    creating a persistent tension for it is pure noise. The review still runs
    and still flags issues in the response — it just isn't persisted.
    """
    t = (task or "").strip().lower()
    if not t:
        return True
    if any(m in t for m in _TEST_SOURCE_MARKERS):
        return True
    return len(t) < _TRIVIAL_QUERY_MAX_LEN


def select_for_task(task: str, tensions: list[dict] | None = None, limit: int = 3) -> list[dict]:
    """Return only tensions materially connected to the current task.

    The active registry is an audit record, not a standing injunction against
    every future answer. Matching is intentionally conservative: without a
    meaningful shared term, a tension stays visible in DARKROOM but is not
    injected into the chat prompt.
    """
    task_terms = {
        term for term in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]{4,}", (task or "").lower())
        if term not in _CONTEXT_STOPWORDS
    }
    if not task_terms or limit <= 0:
        return []

    ranked: list[tuple[int, float, dict]] = []
    for tension in tensions if tensions is not None else load_active():
        text = " ".join((tension.get("description", ""), tension.get("source_task", ""))).lower()
        tension_terms = set(re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_]{4,}", text))
        overlap = len(task_terms & tension_terms)
        if overlap:
            ranked.append((overlap, float(tension.get("severity", 0.0)), tension))

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2].get("created", "")))
    return [item[2] for item in ranked[:limit]]


def _is_test_source(t: dict) -> bool:
    """A tension that came from a throwaway/benchmark query, not real work."""
    src  = (t.get("source_task") or "").lower()
    desc = (t.get("description") or "").lower()
    return any(m in src or m in desc for m in _TEST_SOURCE_MARKERS)


def _should_age_out(t: dict) -> bool:
    """Medium/low tension past its 30-day expiry → archive.

    Critical tensions (severity ≥ CRITICAL_THRESHOLD) are exempt: they stay
    active ad infinitum until the operator archives them manually. This is the
    deliberate asymmetry — only the genuinely critical conflicts persist."""
    if (t.get("severity") or 0) >= CRITICAL_THRESHOLD:
        return False  # critical → ad infinitum
    created = t.get("created") or ""
    try:
        age_days = (date.today() - date.fromisoformat(created)).days
    except Exception:  # noqa: BLE001
        return False
    return age_days >= MEDIUM_AGE_DAYS


def triage_tensions(*, drop_test_pollution: bool = True, drop_aged: bool = True) -> dict:
    """Apply the tension lifecycle policy to the active pool.

    Tensions are first-class cognitive artifacts (see module docstring) — this
    does NOT resolve genuine, live, critical tensions. It archives, with reasons:
      1. LITERAL duplicates (identical type+description) — keeps the highest-
         severity / most-reviewed copy.
      2. Test pollution — tensions from throwaway/benchmark queries.
      3. Aged-out — ordinary tensions (severity < 0.8) older than 30 days.
         Critical tensions (≥ 0.8) are never auto-archived.

    Returns counts: {deduped, test_archived, aged_archived, active_remaining}.
    """
    active = load_active()

    def _norm(t: dict) -> str:
        return (str(t.get("type", "")) + "|" + (t.get("description") or "").strip().lower())[:300]

    groups: dict[str, list] = {}
    for t in active:
        groups.setdefault(_norm(t), []).append(t)

    deduped = test_archived = aged_archived = 0
    for group in groups.values():
        # 1. test pollution — whole group from throwaway queries
        if drop_test_pollution and all(_is_test_source(t) for t in group):
            for t in group:
                if archive(t["id"], resolution_note="triage: test pollution"):
                    test_archived += 1
            continue
        # 2. dedup literal duplicates
        if len(group) > 1:
            group.sort(key=lambda x: (-(x.get("severity") or 0), -(x.get("review_count") or 0)))
            champion = group[0]
            for dup in group[1:]:
                if archive(dup["id"], resolution_note=f"triage: duplicate of {champion['id']}"):
                    deduped += 1
            group = [champion]
        # 3. aged-out medium/low survivor (critical exempt)
        if drop_aged:
            for t in group:
                if _should_age_out(t) and archive(t["id"], resolution_note="triage: aged out (>30d, medium/low)"):
                    aged_archived += 1

    return {
        "deduped":          deduped,
        "test_archived":    test_archived,
        "aged_archived":    aged_archived,
        "active_remaining": len(load_active()),
    }


def archive(tension_id: str, resolution_note: str = "") -> bool:
    src = _ACTIVE_DIR / f"{tension_id}.json"
    if not src.exists():
        return False
    t = json.loads(src.read_text(encoding="utf-8"))
    t["status"] = "archived"
    t["archived"] = str(date.today())
    t["resolution_note"] = resolution_note
    dst = _ARCHIVE_DIR / f"{tension_id}.json"
    dst.write_text(json.dumps(t, indent=2, ensure_ascii=False), encoding="utf-8")
    src.unlink()
    return True


def to_context_string(tensions: list[dict]) -> str:
    """Render active tensions as prompt-injectable string."""
    if not tensions:
        return "[DARKROOM TENSIONS]\n  brak aktywnych napięć"
    lines = [f"[DARKROOM TENSIONS — {len(tensions)} aktywnych]"]
    for t in sorted(tensions, key=lambda x: -x.get("severity", 0)):
        lines.append(
            f"  [{t['type']}] severity={t['severity']:.2f}: {t['description'][:100]}"
        )
    return "\n".join(lines)


def add_hallucination_pattern(pattern: str, trigger_task: str = "") -> None:
    data = json.loads(_HAL_FILE.read_text(encoding="utf-8"))
    existing = [p["pattern"] for p in data["patterns"]]
    if pattern not in existing:
        data["patterns"].append({
            "pattern": pattern,
            "first_seen": str(date.today()),
            "trigger_task": trigger_task[:80],
            "count": 1,
        })
        data["total_detected"] += 1
    else:
        for p in data["patterns"]:
            if p["pattern"] == pattern:
                p["count"] = p.get("count", 1) + 1
    _HAL_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add_drift_signature(signature: str, severity: float, trigger_task: str = "") -> None:
    data = json.loads(_DRIFT_FILE.read_text(encoding="utf-8"))
    data["signatures"].append({
        "signature": signature,
        "severity": round(severity, 2),
        "detected": str(date.today()),
        "trigger_task": trigger_task[:80],
    })
    data["total_detected"] += 1
    _DRIFT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_hallucination_patterns() -> list[dict]:
    return json.loads(_HAL_FILE.read_text(encoding="utf-8")).get("patterns", [])


def load_drift_signatures() -> list[dict]:
    return json.loads(_DRIFT_FILE.read_text(encoding="utf-8")).get("signatures", [])
