"""Memory manager — persistent insights across sessions.

Trzy poziomy:
  memory/candidates/  — staging area (jeszcze nie zatwierdzone)
  memory/insights/    — durable memory (zatwierdzone)
  memory/insights/archive/ — zarchiwizowane

v0.3e:
  - MemoryKind enum (7 kategorii)
  - score_memory_dict() — formuła wagowana confidence/usefulness/stability/risk
  - recommend_candidate_promotion() — promote / reject / keep_candidate / manual_review
  - save_candidate() przyjmuje kind + metryki jakości
  - save_insight() przyjmuje kind
  - promote_candidate() zwraca auto-score i rekomendację
"""
from __future__ import annotations

import json
import uuid
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Literal

from .config import ROOT

MEMORY_DIR         = ROOT / "memory" / "insights"
MEMORY_ARCHIVE_DIR = ROOT / "memory" / "insights" / "archive"
CANDIDATES_DIR     = ROOT / "memory" / "candidates"

for _d in (MEMORY_DIR, MEMORY_ARCHIVE_DIR, CANDIDATES_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── MemoryKind enum (#9) ───────────────────────────────────────────────────────

class MemoryKind(str, Enum):
    """Kategorie trwałych insightów.

    Pozwala routować insighty do odpowiednich promptów:
    FAILURE_PATTERN jest używany inaczej niż USER_PREFERENCE.
    """
    USER_PREFERENCE    = "user_preference"
    PROJECT_FACT       = "project_fact"
    PROCEDURAL_LESSON  = "procedural_lesson"
    FAILURE_PATTERN    = "failure_pattern"
    STYLE_RULE         = "style_rule"
    DOMAIN_CONSTRAINT  = "domain_constraint"
    TEMPORARY_CONTEXT  = "temporary_context"


# Human-readable labels for the dashboard
MEMORY_KIND_LABELS: dict[str, str] = {
    "user_preference":   "Preferencja",
    "project_fact":      "Fakt",
    "procedural_lesson": "Lekcja",
    "failure_pattern":   "Błąd",
    "style_rule":        "Styl",
    "domain_constraint": "Ograniczenie",
    "temporary_context": "Tymczasowe",
}

# Badge colours (CSS var names) per kind
MEMORY_KIND_COLORS: dict[str, str] = {
    "user_preference":   "var(--blue)",
    "project_fact":      "var(--ok)",
    "procedural_lesson": "var(--purple, #9c6ef8)",
    "failure_pattern":   "var(--red)",
    "style_rule":        "var(--warning)",
    "domain_constraint": "var(--text2)",
    "temporary_context": "var(--text3)",
}


# ── Memory scoring & promotion (#1) ───────────────────────────────────────────

PromotionRecommendation = Literal["promote", "reject", "keep_candidate", "manual_review"]

# Scoring weights (from Matylda Full memory/scoring.py)
_W_CONFIDENCE = 0.35
_W_USEFULNESS = 0.35
_W_STABILITY  = 0.20
_W_RISK       = 0.30  # subtracted


def score_memory_dict(d: dict) -> float:
    """Score a candidate dict using the weighted formula.

    score = 0.35*confidence + 0.35*usefulness + 0.20*stability - 0.30*risk

    Returns float in range roughly [-0.30, 0.90]. Candidates without explicit
    metrics default to 0.5 confidence/usefulness/stability, 0.2 risk → score ≈ 0.54.
    """
    confidence = float(d.get("confidence", 0.5))
    usefulness = float(d.get("usefulness", 0.5))
    stability  = float(d.get("stability",  0.5))
    risk       = float(d.get("risk",       0.2))
    return (
        _W_CONFIDENCE * confidence
        + _W_USEFULNESS * usefulness
        + _W_STABILITY  * stability
        - _W_RISK       * risk
    )


def recommend_candidate_promotion(d: dict) -> PromotionRecommendation:
    """Recommend whether to promote, reject, keep, or manually review a candidate.

    Rules (from Matylda Full memory/promotion.py):
    - risk >= 0.65 → manual_review (regardless of score)
    - score >= 0.70 → promote
    - score < 0.30 → reject
    - otherwise → keep_candidate
    """
    risk = float(d.get("risk", 0.2))
    if risk >= 0.65:
        return "manual_review"
    score = score_memory_dict(d)
    if score >= 0.70:
        return "promote"
    if score < 0.30:
        return "reject"
    return "keep_candidate"


def score_candidate(candidate_id: str) -> dict | None:
    """Return score report for a candidate by id, or None if not found."""
    for p in CANDIDATES_DIR.glob("*.json"):
        if not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("id") == candidate_id:
            sc = score_memory_dict(d)
            rec = recommend_candidate_promotion(d)
            return {
                "candidate_id": candidate_id,
                "score": round(sc, 4),
                "recommendation": rec,
                "confidence": d.get("confidence", 0.5),
                "usefulness": d.get("usefulness", 0.5),
                "stability":  d.get("stability",  0.5),
                "risk":       d.get("risk",       0.2),
            }
    return None


# ── Insights (durable memory) ─────────────────────────────────────────────────

def save_insight(
    content: str,
    topic: str = "",
    linked_thread: str = "",
    linked_project: str = "",
    kind: str = "",
) -> dict:
    """Save a new durable insight and return its dict.

    Args:
        kind: optional MemoryKind value (e.g. "failure_pattern").
    """
    insight_id = "insight_" + uuid.uuid4().hex[:8]
    data = {
        "id": insight_id,
        "content": content,
        "topic": topic,
        "kind": kind or "",
        "linked_thread": linked_thread,
        "linked_project": linked_project,
        "created": str(date.today()),
        "status": "active",
    }
    path = MEMORY_DIR / f"{date.today()}_{insight_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def list_insights(
    include_archived: bool = False,
    kind_filter: str = "",
) -> list[dict]:
    """Return all insights sorted by created desc.

    Args:
        include_archived: Include archived insights.
        kind_filter: If set, return only insights with matching MemoryKind.
    """
    results: list[dict] = []

    for p in MEMORY_DIR.glob("*.json"):
        if p.is_file():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                d["archived"] = False
                results.append(d)
            except Exception:  # noqa: BLE001
                pass

    if include_archived:
        for p in MEMORY_ARCHIVE_DIR.glob("*.json"):
            if p.is_file():
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    d["archived"] = True
                    results.append(d)
                except Exception:  # noqa: BLE001
                    pass

    if kind_filter:
        results = [r for r in results if r.get("kind") == kind_filter]

    results.sort(key=lambda x: x.get("created", ""), reverse=True)
    return results


def archive_insight(insight_id: str) -> bool:
    """Move insight to archive dir. Return True on success."""
    for p in MEMORY_DIR.glob("*.json"):
        if not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("id") == insight_id:
            dest = MEMORY_ARCHIVE_DIR / p.name
            p.rename(dest)
            return True
    return False


def load_relevant_insights(
    task: str,
    n: int = 5,
    kind_filter: str = "",
) -> str:
    """Return top-n insights relevant to task as a formatted string.

    Args:
        kind_filter: If set, only consider insights of this MemoryKind.
    """
    words = [w for w in task.lower().split() if len(w) > 3]
    if not words:
        return ""

    active = [
        i for i in list_insights(include_archived=False, kind_filter=kind_filter)
        if not i.get("archived")
    ]
    if not active:
        return ""

    scored: list[tuple[int, dict]] = []
    for insight in active:
        text = (insight.get("content", "") + " " + insight.get("topic", "")).lower()
        score = sum(1 for w in words if w in text)
        if score > 0:
            scored.append((score, insight))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:n]
    if not top:
        return ""

    lines = ["=== PAMIĘĆ KONTEKSTOWA ==="]
    for _, ins in top:
        topic = ins.get("topic", "")
        kind  = ins.get("kind", "")
        content = ins.get("content", "")[:200]
        prefix_parts = []
        if kind:
            prefix_parts.append(f"[{kind}]")
        if topic:
            prefix_parts.append(topic)
        prefix = ": ".join(prefix_parts) + ": " if prefix_parts else ""
        lines.append(f"{prefix}{content}")

    return "\n".join(lines)


# ── Candidates (staging area) ──────────────────────────────────────────────

def save_candidate(
    content: str,
    topic: str = "",
    note: str = "",
    linked_thread: str = "",
    kind: str = "",
    confidence: float = 0.5,
    usefulness: float = 0.5,
    risk: float = 0.2,
    stability: float = 0.5,
) -> dict:
    """Save insight candidate to staging area (not yet durable).

    Args:
        kind: optional MemoryKind value (e.g. "procedural_lesson").
        confidence: estimated correctness 0.0–1.0 (default 0.5).
        usefulness: estimated usefulness 0.0–1.0 (default 0.5).
        risk: estimated risk/harm 0.0–1.0 (default 0.2).
        stability: estimated long-term stability 0.0–1.0 (default 0.5).
    """
    # Clamp to [0,1]
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    confidence = _clamp(confidence)
    usefulness = _clamp(usefulness)
    risk       = _clamp(risk)
    stability  = _clamp(stability)

    cid = "candidate_" + uuid.uuid4().hex[:8]
    data = {
        "id": cid,
        "content": content,
        "topic": topic,
        "kind": kind or "",
        "note": note,
        "linked_thread": linked_thread,
        "confidence": confidence,
        "usefulness": usefulness,
        "risk": risk,
        "stability": stability,
        "created": str(date.today()),
        "status": "candidate",
    }
    # Pre-compute score and recommendation for convenience
    data["_score"] = round(score_memory_dict(data), 4)
    data["_recommendation"] = recommend_candidate_promotion(data)

    path = CANDIDATES_DIR / f"{date.today()}_{cid}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def list_candidates(kind_filter: str = "") -> list[dict]:
    """Return all candidates sorted by created desc, with auto-scores.

    Args:
        kind_filter: If set, return only candidates with matching MemoryKind.
    """
    results: list[dict] = []
    for p in sorted(CANDIDATES_DIR.glob("*.json"), reverse=True):
        if p.is_file():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                # Ensure score fields present (backwards compat with old candidates)
                if "_score" not in d:
                    d["_score"] = round(score_memory_dict(d), 4)
                if "_recommendation" not in d:
                    d["_recommendation"] = recommend_candidate_promotion(d)
                results.append(d)
            except Exception:  # noqa: BLE001
                pass

    if kind_filter:
        results = [r for r in results if r.get("kind") == kind_filter]

    return results


def promote_candidate(candidate_id: str) -> dict | None:
    """Promote candidate → durable insight.

    Returns new insight dict with added scoring metadata, or None if not found.
    The insight includes: auto_score, recommendation, kind (from candidate).
    """
    for p in CANDIDATES_DIR.glob("*.json"):
        if not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("id") == candidate_id:
            score = score_memory_dict(d)
            rec   = recommend_candidate_promotion(d)
            insight = save_insight(
                content=d["content"],
                topic=d.get("topic", ""),
                linked_thread=d.get("linked_thread", ""),
                kind=d.get("kind", ""),
            )
            # Enrich returned insight with scoring data
            insight["promoted_from"] = candidate_id
            insight["auto_score"] = round(score, 4)
            insight["recommendation_at_promotion"] = rec
            # Update stored file with promotion metadata
            stored_path = MEMORY_DIR / f"{date.today()}_{insight['id']}.json"
            if stored_path.exists():
                try:
                    stored = json.loads(stored_path.read_text(encoding="utf-8"))
                    stored.update({
                        "promoted_from": candidate_id,
                        "auto_score": insight["auto_score"],
                        "recommendation_at_promotion": rec,
                    })
                    stored_path.write_text(
                        json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                except Exception:  # noqa: BLE001
                    pass
            p.unlink()
            return insight
    return None


def discard_candidate(candidate_id: str) -> bool:
    """Remove candidate without promoting. Returns True on success."""
    for p in CANDIDATES_DIR.glob("*.json"):
        if not p.is_file():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("id") == candidate_id:
            p.unlink()
            return True
    return False
