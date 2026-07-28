"""consolidation.py — v0.9 autonomous background consolidation agent.

Design principle:
  "Zamierzam zrobić X — nie już zrobiłam X."

Sleeping Matylda wakes up every BOUNDS.sleeping_matylda_min_gap_hours, analyses
the workspace, and produces **findings** — structured proposals that require
explicit user approval before anything is written.

Zero autonomous writes:
  Every finding has an action that is executed ONLY after approve_finding().
  dismiss_finding() records the rejection without side-effects.

Finding types:
  reflection_candidate      — thread with ≥N diary entries → promote to reflection
  synthesis_opportunity     — tag shared by ≥2 threads → enqueue synthesis task
  stale_question            — open question unresolved for > stale_item_age_hours
  graph_orphan              — entity with no relations in knowledge graph
  graph_duplicate_candidate — two entities with high label similarity
  forgotten_object          — Forgetroom object below prune threshold (v0.8)
  nogo_territory            — trajectory crossing risk threshold first time (v0.8)
  meta_drift_alert          — system changing at >2× baseline rate (v0.9)
  question_focus            — focus mode: open question targeted for resolution (v1.2)
  tension_analysis          — focus mode: DARKROOM tension with pro/contra + resolution (v1.2)
  step_proposal             — focus mode: concrete next step from stale trace / open goal (v1.2)
  nogo_recheck              — focus mode: validity check on a NO-GO trajectory (v1.2)

Finding lifecycle:
  pending → approved (action executed) | dismissed

Fatigue awareness:
  fatigue >= fatigue_high_threshold → reduced scope (half lookback days, skip graph)
  attention over_budget              → cycle skipped entirely

State file: data/sleeping_matylda_state.json
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..config import ROOT
from ..constitutional import BOUNDS

log = logging.getLogger(__name__)

_STATE_FILE     = ROOT / "data" / "sleeping_matylda_state.json"
_SNAPSHOTS_FILE = ROOT / "data" / "identity_snapshots.json"
_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

_FINDING_TERMINAL_STATES = frozenset({"approved", "dismissed"})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> dict:
    if not _STATE_FILE.exists():
        return {
            "last_cycle_start": None,
            "last_cycle_end":   None,
            "last_cycle_findings": 0,
            "total_cycles":     0,
            "findings":         [],
        }
    try:
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"last_cycle_start": None, "last_cycle_end": None,
                "last_cycle_findings": 0, "total_cycles": 0, "findings": []}


def _save_state(state: dict) -> None:
    from ..atomic_state import atomic_write_json  # noqa: PLC0415
    atomic_write_json(_STATE_FILE, state)


def _fire(event_type: str, **kwargs: Any) -> None:
    try:
        from ..hooks import fire  # noqa: PLC0415
        fire(event_type, **kwargs)
    except Exception:  # noqa: BLE001
        pass


def _making_id() -> str:
    return f"finding_{uuid.uuid4().hex[:8]}"


# ── Structural state snapshot (for meta_drift) ────────────────────────────────

def _count_structural_state() -> dict:
    """Lightweight count of key structural elements. Used for meta_drift tracking."""
    counts: dict[str, int] = {"reflections": 0, "entities": 0, "goals": 0}
    try:
        from ..diary_manager import REFLECTIONS_DIR  # noqa: PLC0415
        counts["reflections"] = len(list(REFLECTIONS_DIR.glob("*.json")))
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..knowledge_graph import load_graph  # noqa: PLC0415
        counts["entities"] = len(load_graph())
    except Exception:  # noqa: BLE001
        pass
    try:
        from ..homeostasis import list_goals  # noqa: PLC0415
        counts["goals"] = sum(1 for g in list_goals() if g.get("status") == "active")
    except Exception:  # noqa: BLE001
        pass
    return counts


def _compute_meta_drift(state: dict) -> dict:
    """Compute meta_drift_score from cycle_history over the rolling window.

    meta_drift_score = structural_change_rate_now / structural_change_rate_baseline
    where "structural change" = |reflections_delta| + |entities_delta| + |goals_delta|
                                + findings_generated

    Score interpretation:
      1.0 = changing at historical baseline rate (neutral)
      2.0 = changing at 2× baseline → BOUNDS.meta_drift_alert_threshold by default
      0.5 = quieter period
    """
    history = state.get("cycle_history", [])
    if not history:
        return {
            "meta_drift_score":          1.0,
            "window_days":               BOUNDS.meta_drift_window_days,
            "avg_confidence_modifier":   0.0,
            "cycles_in_window":          0,
            "cycles_in_baseline":        0,
            "alert":                     False,
        }

    now             = datetime.now(timezone.utc)
    window          = timedelta(days=BOUNDS.meta_drift_window_days)
    window_start    = (now - window).isoformat()
    baseline_start  = (now - window * 2).isoformat()

    current_cycles  = [c for c in history if c.get("timestamp", "") >= window_start]
    baseline_cycles = [
        c for c in history
        if baseline_start <= c.get("timestamp", "") < window_start
    ]

    def _change_units(cycles: list[dict]) -> float:
        return sum(
            abs(c.get("reflections_delta", 0))
            + abs(c.get("entities_delta", 0))
            + abs(c.get("goals_delta", 0))
            + c.get("findings_count", 0)
            for c in cycles
        )

    current_change  = _change_units(current_cycles)
    baseline_change = _change_units(baseline_cycles)

    if baseline_change == 0:
        score = 1.0  # no historical baseline → neutral
    else:
        score = round(current_change / baseline_change, 3)

    modifiers = [
        c["avg_confidence_modifier"]
        for c in current_cycles
        if c.get("avg_confidence_modifier") is not None
    ]
    avg_modifier = round(sum(modifiers) / len(modifiers), 4) if modifiers else 0.0

    return {
        "meta_drift_score":        score,
        "window_days":             BOUNDS.meta_drift_window_days,
        "avg_confidence_modifier": avg_modifier,
        "cycles_in_window":        len(current_cycles),
        "cycles_in_baseline":      len(baseline_cycles),
        "alert":                   score >= BOUNDS.meta_drift_alert_threshold,
    }


def get_meta_drift() -> dict:
    """Return current meta_drift summary for external callers."""
    return _compute_meta_drift(_load_state())


# ── Identity Snapshot ─────────────────────────────────────────────────────────

def snapshot_identity(label: str = "") -> dict:
    """Take a lightweight structural snapshot of Matylda's current state.

    Not a brain copy — a 'sylwetka': counts and tag distributions.
    Use as a reference point for detecting identity drift over time.

    Returns the snapshot dict (also persisted to data/identity_snapshots.json).
    """
    snap: dict[str, Any] = {
        "snapshot_id": f"snap_{uuid.uuid4().hex[:8]}",
        "label":       label.strip() or f"snapshot_{_now()[:10]}",
        "created":     _now(),
    }

    # Reflections
    try:
        from ..diary_manager import REFLECTIONS_DIR  # noqa: PLC0415
        refl_files = list(REFLECTIONS_DIR.glob("*.json"))
        snap["reflection_count"] = len(refl_files)
        all_tags: list[str] = []
        for f in refl_files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                all_tags.extend(data.get("tags", []))
            except Exception:  # noqa: BLE001
                pass
        tag_counts: dict[str, int] = {}
        for t in all_tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
        snap["top_tags"] = sorted(tag_counts, key=lambda x: -tag_counts[x])[:10]
    except Exception:  # noqa: BLE001
        snap["reflection_count"] = 0
        snap["top_tags"] = []

    # Knowledge graph
    try:
        from ..knowledge_graph import load_graph  # noqa: PLC0415
        graph = load_graph()
        snap["entity_count"]   = len(graph)
        snap["relation_count"] = sum(len(e.relations) for e in graph.values())
    except Exception:  # noqa: BLE001
        snap["entity_count"]   = 0
        snap["relation_count"] = 0

    # Active goals
    try:
        from ..homeostasis import list_goals  # noqa: PLC0415
        snap["goal_count"] = sum(1 for g in list_goals() if g.get("status") == "active")
    except Exception:  # noqa: BLE001
        snap["goal_count"] = 0

    # Meta drift at snapshot time
    snap["meta_drift_score_at_snapshot"] = _compute_meta_drift(_load_state()).get(
        "meta_drift_score", 1.0
    )

    # Persist
    try:
        existing = json.loads(_SNAPSHOTS_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        existing = {"snapshots": []}
    existing["snapshots"].append(snap)
    _SNAPSHOTS_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return snap


def list_snapshots() -> list[dict]:
    """Return all identity snapshots, newest first."""
    try:
        data = json.loads(_SNAPSHOTS_FILE.read_text(encoding="utf-8"))
        return list(reversed(data.get("snapshots", [])))
    except Exception:  # noqa: BLE001
        return []


def compare_snapshots(snapshot_id_a: str, snapshot_id_b: str) -> dict:
    """Compare two snapshots — returns structural deltas.

    Args:
        snapshot_id_a: Reference snapshot (earlier, 'before').
        snapshot_id_b: Comparison snapshot (later, 'after').

    Returns:
        Delta dict with numeric diffs and tag changes.
    """
    snaps = {s["snapshot_id"]: s for s in list_snapshots()}
    a = snaps.get(snapshot_id_a)
    b = snaps.get(snapshot_id_b)
    if not a:
        raise KeyError(f"Snapshot not found: {snapshot_id_a!r}")
    if not b:
        raise KeyError(f"Snapshot not found: {snapshot_id_b!r}")

    numeric_fields = ["reflection_count", "entity_count", "relation_count", "goal_count"]
    return {
        "snapshot_a":         snapshot_id_a,
        "snapshot_b":         snapshot_id_b,
        "label_a":            a.get("label"),
        "label_b":            b.get("label"),
        "created_a":          a.get("created"),
        "created_b":          b.get("created"),
        "deltas":             {f: b.get(f, 0) - a.get(f, 0) for f in numeric_fields},
        "tags_gained":        [t for t in b.get("top_tags", [])
                               if t not in a.get("top_tags", [])],
        "tags_lost":          [t for t in a.get("top_tags", [])
                               if t not in b.get("top_tags", [])],
        "meta_drift_delta":   round(
            b.get("meta_drift_score_at_snapshot", 1.0)
            - a.get("meta_drift_score_at_snapshot", 1.0),
            3,
        ),
    }


# ── Analysis: diary patterns ──────────────────────────────────────────────────

def _analyze_diary_patterns(days: int) -> list[dict]:
    """Scan diary entries and return finding dicts (no writes)."""
    try:
        from ..diary_manager import list_diary_entries  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    entries = list_diary_entries(days=days)
    if not entries:
        return []

    findings: list[dict] = []
    stale_cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=BOUNDS.stale_item_age_hours)
    ).isoformat()

    # ── Branch evaluator (v0.8) — loaded once, used per stem/tag ────────────────
    try:
        from ..branch_evaluator import evaluate_branch as _eval_branch  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        _eval_branch = None  # type: ignore[assignment]

    # 1. Threads with N+ entries → reflection candidates
    by_thread: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        stem = e.get("thread_stem") or "unassigned"
        by_thread[stem].append(e)

    for stem, stem_entries in sorted(
        by_thread.items(), key=lambda x: len(x[1]), reverse=True
    ):
        if len(stem_entries) < BOUNDS.sleeping_matylda_pattern_min_count:
            continue
        key_findings = [e.get("key_finding", "") for e in stem_entries[-3:] if e.get("key_finding")]
        open_qs = list({q for e in stem_entries for q in e.get("open_questions", [])})
        tags     = list({t for e in stem_entries for t in e.get("tags", [])})
        dominant_tag = tags[0] if tags else "untagged"
        conf     = min(0.95, 0.5 + len(stem_entries) * 0.08)

        # v1.1: Pattern resurfaces → keep it alive in Forgetroom (fire-and-forget)
        _activate_reflection_pattern_if_exists(stem)

        # Apply branch evaluator cost modifier
        exploration: dict = {}
        if _eval_branch is not None:
            try:
                exploration = _eval_branch(stem, dominant_tag, len(stem_entries), 0)
                conf = max(0.05, round(conf + exploration.get("confidence_modifier", 0.0), 3))
            except Exception:  # noqa: BLE001
                pass

        findings.append({
            "finding_id":    _making_id(),
            "type":          "reflection_candidate",
            "title":         f"Wątek '{stem}': {len(stem_entries)} wpisów → kandydat na refleksję",
            "description":   (
                f"Wątek '{stem}' zgromadził {len(stem_entries)} wpisów dziennika "
                f"(próg: {BOUNDS.sleeping_matylda_pattern_min_count}). "
                "Wzorzec kwalifikuje się do awansu na refleksję."
            ),
            "thread_stem":   stem,
            "entry_count":   len(stem_entries),
            "entry_ids":     [e.get("entry_id", "") for e in stem_entries],
            "key_findings":  key_findings,
            "open_questions": open_qs[:5],
            "tags":          tags,
            "confidence":    conf,
            "created":       _now(),
            "state":         "pending",
            "action":        "create_reflection",
            **({"exploration_cost": exploration["exploration_cost"]} if exploration else {}),
        })

    # 2. Tags shared across ≥2 threads → synthesis opportunity
    tag_threads: dict[str, set[str]] = defaultdict(set)
    for e in entries:
        stem = e.get("thread_stem") or "unassigned"
        for tag in e.get("tags", []):
            tag_threads[tag].add(stem)

    for tag, stems in sorted(tag_threads.items(), key=lambda x: len(x[1]), reverse=True):
        if len(stems) < 2:
            continue
        conf = min(0.90, 0.40 + len(stems) * 0.15)

        # Apply branch evaluator for the dominant stem in this tag cluster
        dominant_stem = sorted(stems)[0]
        if _eval_branch is not None:
            try:
                exploration = _eval_branch(dominant_stem, tag, 0, 0)
                conf = max(0.05, round(conf + exploration.get("confidence_modifier", 0.0), 3))
            except Exception:  # noqa: BLE001
                pass

        findings.append({
            "finding_id":  _making_id(),
            "type":        "synthesis_opportunity",
            "title":       f"Tag '{tag}' łączy {len(stems)} wątki",
            "description": (
                f"Wspólny temat '{tag}' pojawia się w wątkach: "
                f"{', '.join(sorted(stems)[:5])}{'...' if len(stems) > 5 else ''}. "
                "Okazja do syntezy cross-thread."
            ),
            "tag":             tag,
            "threads":         sorted(stems),
            "confidence":      round(conf, 3),
            "created":         _now(),
            "state":           "pending",
            "action":          "enqueue_synthesis",
            "estimated_tokens": 2500,  # synthesis is expensive → goes through approval gate
        })

    # 3. Unresolved open questions older than stale threshold
    for e in entries:
        if e.get("open_questions") and e.get("timestamp", "") < stale_cutoff:
            stem = e.get("thread_stem", "?")
            findings.append({
                "finding_id":  _making_id(),
                "type":        "stale_question",
                "title":       f"Nierozwiązane pytania w wątku '{stem}'",
                "description": (
                    f"Pytania bez odpowiedzi od >{BOUNDS.stale_item_age_hours:.0f}h: "
                    f"{e['open_questions'][:2]}"
                ),
                "thread_stem":  stem,
                "questions":    e.get("open_questions", []),
                "entry_id":     e.get("entry_id"),
                "confidence":   0.70,
                "created":      _now(),
                "state":        "pending",
                "action":       "flag_attention",
            })

    return findings


# ── Analysis: graph opportunities ─────────────────────────────────────────────

def _find_graph_opportunities() -> list[dict]:
    """Scan knowledge graph and return finding dicts (no writes)."""
    try:
        from ..knowledge_graph import load_graph  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    graph = load_graph()
    if not graph:
        return []

    findings: list[dict] = []
    entities = list(graph.values())

    # 1. Orphan entities — no outgoing relations AND not referenced as a target
    #    An entity is considered "connected" if it either has outgoing relations
    #    or appears as the target of another entity's relation.
    referenced_as_target: set[str] = set()
    for e in entities:
        for rel in e.relations:
            referenced_as_target.add(rel.target)

    orphans = [
        e for e in entities
        if not e.relations and e.entity_id not in referenced_as_target
    ]
    for orphan in orphans[:3]:
        findings.append({
            "finding_id":  _making_id(),
            "type":        "graph_orphan",
            "title":       f"Encja '{orphan.label}' nie ma relacji",
            "description": (
                f"Encja {orphan.entity_id} ({orphan.kind}) nie jest połączona "
                "z żadną inną encją w grafie wiedzy."
            ),
            "entity_id":   orphan.entity_id,
            "label":       orphan.label,
            "kind":        orphan.kind,
            "confidence":  0.60,
            "created":     _now(),
            "state":       "pending",
            "action":      "suggest_connection",
        })

    # 2. Potential duplicates (token-overlap >= threshold)
    label_pairs: list[tuple[Any, Any, float]] = []
    for i, e1 in enumerate(entities):
        for e2 in entities[i + 1:]:
            t1 = set(e1.label.lower().split())
            t2 = set(e2.label.lower().split())
            if not t1 or not t2:
                continue
            overlap = len(t1 & t2) / max(len(t1), len(t2))
            if overlap >= BOUNDS.sleeping_matylda_graph_similarity_threshold:
                label_pairs.append((e1, e2, overlap))

    for e1, e2, score in sorted(label_pairs, key=lambda x: x[2], reverse=True)[:2]:
        findings.append({
            "finding_id":   _making_id(),
            "type":         "graph_duplicate_candidate",
            "title":        f"Możliwy duplikat: '{e1.label}' ↔ '{e2.label}'",
            "description":  (
                f"Podobieństwo etykiet: {score:.0%}. "
                "Rozważ ręczne scalenie encji w grafie wiedzy."
            ),
            "entity_id_1":  e1.entity_id,
            "entity_id_2":  e2.entity_id,
            "label_1":      e1.label,
            "label_2":      e2.label,
            "similarity":   round(score, 3),
            "confidence":   round(score, 3),
            "created":      _now(),
            "state":        "pending",
            "action":       "suggest_merge",
        })

    return findings


# ── Analysis: forgotten objects (v0.8) ───────────────────────────────────────

def _find_forgotten_objects() -> list[dict]:
    """Return findings for objects whose Forgetroom weight fell below prune threshold."""
    try:
        from ..forgetroom import get_forgotten_candidates  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    candidates = get_forgotten_candidates()
    if not candidates:
        return []

    findings: list[dict] = []
    for obj in candidates[:3]:  # cap at 3 per cycle
        oid   = obj["object_id"]
        otype = obj["object_type"]
        ew    = obj["effective_weight"]
        days  = obj.get("days_since_activation", 0.0)

        action_map = {
            "entity":             "remove_entity",
            "reflection":         "remove_reflection",
            "reflection_pattern": "remove_reflection",  # v1.1: pattern → same action
            "tension":            "remove_tension",
        }
        action = action_map.get(otype, "acknowledge_forgotten")

        findings.append({
            "finding_id":          _making_id(),
            "type":                "forgotten_object",
            "title":               f"Zapomniany obiekt: {oid} ({otype})",
            "description":         (
                f"Obiekt '{oid}' ({otype}) nie był aktywowany od {days:.0f} dni. "
                f"Efektywna waga: {ew:.3f} "
                f"(próg: {BOUNDS.forgetroom_prune_threshold}). "
                "Rozważ usunięcie lub reaktywację."
            ),
            "object_id":           oid,
            "object_type":         otype,
            "effective_weight":    ew,
            "days_since_activation": days,
            "confidence":          round(1.0 - ew, 3),  # lower weight → higher confidence to prune
            "created":             _now(),
            "state":               "pending",
            "action":              action,
        })
    return findings


def _find_nogo_territories() -> list[dict]:
    """Surface newly risky trajectories as informational findings."""
    try:
        from ..nogo_room import list_risky_trajectories  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    risky = list_risky_trajectories()
    if not risky:
        return []

    findings: list[dict] = []
    for traj in risky[:2]:  # cap at 2 per cycle — informational only
        findings.append({
            "finding_id":    _making_id(),
            "type":          "nogo_territory",
            "title":         f"Ryzykowna trajektoria: {traj['trajectory_id']}",
            "description":   (
                f"Trajektoria {traj['thread_stem']}::{traj['tag']} "
                f"(kategoria: {traj['category']}) "
                f"ma effective_risk {traj['effective_risk']:.2f} "
                f"(próg: {BOUNDS.nogo_risk_threshold}). "
                f"Dotychczas: {traj.get('evidence_count', 0)} zdarzeń."
            ),
            "trajectory_id": traj["trajectory_id"],
            "thread_stem":   traj["thread_stem"],
            "tag":           traj["tag"],
            "category":      traj["category"],
            "effective_risk": traj["effective_risk"],
            "evidence_count": traj.get("evidence_count", 0),
            "confidence":    round(traj["effective_risk"], 3),
            "created":       _now(),
            "state":         "pending",
            "action":        "acknowledge_nogo",  # informational — no side effects
        })
    return findings


# ── Finding execution ─────────────────────────────────────────────────────────

def _execute_finding(finding: dict) -> str:
    """Execute approved finding. Returns short result string."""
    action = finding.get("action")

    if action == "create_reflection":
        from ..diary_manager import save_reflection  # noqa: PLC0415
        reflection = {
            "pattern":    finding["title"],
            "confidence": finding["confidence"],
            "patterns": [{
                "occurrences":   finding["entry_count"],
                "counterexample": "Do weryfikacji przez użytkownika (awansowano przez Sleeping Matylda)",
                "key_findings":  finding.get("key_findings", []),
            }],
            "tags":          finding.get("tags", []),
            "source_entries": finding.get("entry_ids", []),
            "thread_stem":   finding.get("thread_stem"),
            "source":        "sleeping_matylda",
        }
        rid = save_reflection(reflection)
        return f"reflection:{rid}"

    elif action == "enqueue_synthesis":
        from ..task_queue import enqueue  # noqa: PLC0415
        tag     = finding.get("tag", "")
        threads = ", ".join(finding.get("threads", []))
        task = enqueue(
            intent=f"Synteza cross-thread: temat '{tag}'",
            payload=(
                f"Przeprowadź syntezę wiedzy na temat '{tag}' "
                f"z następujących wątków: {threads}. "
                "Zidentyfikuj wspólne wzorce, sprzeczności i luki."
            ),
            estimated_tokens=finding.get("estimated_tokens", 2500),
            created_by="sleeping_matylda",
            tags=["synthesis", "sleeping_matylda", tag],
        )
        return f"task:{task['task_id']}:{task['state']}"

    elif action == "flag_attention":
        from ..homeostasis import register_attention_item  # noqa: PLC0415
        iid = register_attention_item(
            label=finding["title"],
            thread_stem=finding.get("thread_stem"),
        )
        return f"attention_item:{iid}"

    elif action in ("suggest_connection", "suggest_merge"):
        # Informational — no automated write; return acknowledgement
        return "acknowledged:manual_action_required"

    elif action == "remove_entity":
        # Forgetroom: forgotten entity — user approved removal
        try:
            from ..knowledge_graph import delete_entity  # noqa: PLC0415
            delete_entity(finding["object_id"])
            return f"deleted_entity:{finding['object_id']}"
        except Exception as exc:  # noqa: BLE001
            return f"remove_entity_failed:{exc}"

    elif action == "remove_reflection":
        # Forgetroom: forgotten reflection — log removal, actual file delete is manual
        return f"acknowledged:remove_reflection:{finding['object_id']}"

    elif action == "remove_tension":
        # Forgetroom: forgotten tension — informational (darkroom manages tensions)
        return f"acknowledged:remove_tension:{finding['object_id']}"

    elif action in ("acknowledge_forgotten", "acknowledge_nogo", "acknowledge_meta_drift",
                    "acknowledge_nogo_recheck"):
        # Informational findings — no side effects
        return "acknowledged:no_action"

    elif action == "resolve_question":
        # Enqueue a task to work on the question
        try:
            from ..task_queue import enqueue  # noqa: PLC0415
            question = finding.get("question") or finding.get("title", "")
            task = enqueue(
                intent=f"Odpowiedz na pytanie: {question[:80]}",
                payload=question,
                estimated_tokens=1500,
                created_by="sleeping_matylda_focus",
                tags=["focus", "question"],
            )
            return f"task:{task['task_id']}"
        except Exception as exc:  # noqa: BLE001
            return f"resolve_question_failed:{exc}"

    elif action == "propose_resolution":
        # Archive the tension with the proposed resolution
        try:
            from ..darkroom.tension import archive  # noqa: PLC0415
            tid = finding.get("tension_id") or ""
            note = finding.get("proposed_resolution") or "Rozwiązanie zaproponowane przez focus mode."
            if tid:
                archive(tid, resolution_note=note)
                return f"tension_archived:{tid}"
            return "propose_resolution:no_tension_id"
        except Exception as exc:  # noqa: BLE001
            return f"propose_resolution_failed:{exc}"

    elif action == "log_step":
        # Chronicle the step as taken
        try:
            from ..chronicle import log_and_build  # noqa: PLC0415
            step = finding.get("step") or finding.get("title", "")
            log_and_build(
                source="sleeping_matylda_focus",
                event_type="step_logged",
                context_ref=finding.get("trace_id") or "focus",
                metadata={"step": step, "focus_session_id": finding.get("focus_session_id")},
            )
            return f"step_logged:{step[:60]}"
        except Exception as exc:  # noqa: BLE001
            return f"log_step_failed:{exc}"

    elif action == "close_goal":
        try:
            from ..homeostasis import close_goal  # noqa: PLC0415
            gid = finding.get("goal_id") or ""
            if gid:
                close_goal(gid, resolution="Zamknięty przez focus mode — krok zaproponowany.")
                return f"goal_closed:{gid}"
            return "close_goal:no_goal_id"
        except Exception as exc:  # noqa: BLE001
            return f"close_goal_failed:{exc}"

    elif action == "reopen_trajectory":
        # Reset risk score in nogo_room to allow re-exploration
        try:
            from ..nogo_room import _load as _nogo_load, _save as _nogo_save  # noqa: PLC0415
            data = _nogo_load()
            tid = finding.get("trajectory_id") or ""
            if tid and tid in data.get("trajectories", {}):
                data["trajectories"][tid]["risk_score"] = 0.0
                data["trajectories"][tid]["reopen_note"] = (
                    f"Reopened by focus session {finding.get('focus_session_id','?')}"
                )
                _nogo_save(data)
                return f"trajectory_reopened:{tid}"
            return "reopen_trajectory:not_found"
        except Exception as exc:  # noqa: BLE001
            return f"reopen_trajectory_failed:{exc}"

    return f"unknown_action:{action}"


# ── Cycle ─────────────────────────────────────────────────────────────────────

def run_cycle(*, force: bool = False, focus_config: Any = None) -> dict:
    """Run one consolidation cycle. Returns cycle summary dict.

    When focus_config (FocusSessionConfig) is provided:
      - Gap check is skipped (focus session manages its own timing)
      - Only focus engines are run (see focus_engine._AREA_ENGINES)
      - All findings carry focus_session_id + provenance fields

    Respects:
      - BOUNDS.sleeping_matylda_min_gap_hours (unless force=True or focus_config set)
      - homeostasis attention budget (skips if over budget)
      - fatigue level (reduces scope if high)
    """
    # Focus mode: delegate entirely to focus_engine to keep a single execution path
    if focus_config is not None:
        try:
            from .focus_engine import run_focused_cycle  # noqa: PLC0415
            return run_focused_cycle(focus_config)
        except Exception:  # noqa: BLE001
            log.exception("Focus cycle delegation failed — falling back to normal cycle")

    state = _load_state()

    # Gap check
    last = state.get("last_cycle_start")
    if not force and last:
        gap = (
            datetime.now(timezone.utc) - datetime.fromisoformat(last)
        ).total_seconds() / 3600
        if gap < BOUNDS.sleeping_matylda_min_gap_hours:
            return {
                "status": "skipped",
                "reason": f"Last cycle {gap:.1f}h ago (min: {BOUNDS.sleeping_matylda_min_gap_hours}h)",
                "next_cycle_in_hours": round(BOUNDS.sleeping_matylda_min_gap_hours - gap, 1),
            }

    # Homeostasis checks
    try:
        from ..homeostasis import attention_status, fatigue_status  # noqa: PLC0415
        attn = attention_status()
        fat  = fatigue_status()
    except Exception:  # noqa: BLE001
        attn, fat = {}, {}

    if attn.get("over_budget"):
        return {"status": "skipped", "reason": "attention over budget"}

    reduced_scope = fat.get("high", False)

    # Counterfactual evaluation (v1.0) — run before analysis so corrections
    # affect Positive Room before branch_evaluator reads it this cycle
    try:
        from ..counterfactual_room import evaluate_counterfactuals  # noqa: PLC0415
        evaluate_counterfactuals()
    except Exception:  # noqa: BLE001
        log.debug("Sleeping Matylda: counterfactual evaluation skipped (import error)")

    # Structural snapshot before cycle (for meta_drift delta)
    pre_snap = _count_structural_state()

    # Mark cycle start
    state["last_cycle_start"] = _now()
    state["total_cycles"]     = state.get("total_cycles", 0) + 1
    _save_state(state)

    _fire("sleeping_matylda.cycle_start",
          cycle=state["total_cycles"], reduced_scope=reduced_scope)
    log.info("Sleeping Matylda: cycle %d started (reduced_scope=%s)",
             state["total_cycles"], reduced_scope)

    days = (BOUNDS.sleeping_matylda_diary_lookback_days // 2
            if reduced_scope else BOUNDS.sleeping_matylda_diary_lookback_days)

    all_findings: list[dict] = []

    try:
        all_findings.extend(_analyze_diary_patterns(days=days))
    except Exception:  # noqa: BLE001
        log.exception("Sleeping Matylda: diary analysis failed")

    if not reduced_scope:
        try:
            all_findings.extend(_find_graph_opportunities())
        except Exception:  # noqa: BLE001
            log.exception("Sleeping Matylda: graph analysis failed")

        try:
            all_findings.extend(_find_forgotten_objects())
        except Exception:  # noqa: BLE001
            log.exception("Sleeping Matylda: forgetroom analysis failed")

        try:
            all_findings.extend(_find_nogo_territories())
        except Exception:  # noqa: BLE001
            log.exception("Sleeping Matylda: nogo territory analysis failed")

    # Sort by confidence desc, cap at max
    all_findings.sort(key=lambda f: f.get("confidence", 0), reverse=True)
    all_findings = all_findings[:BOUNDS.sleeping_matylda_max_findings_per_cycle]

    # ── Cycle history record (v0.9) ───────────────────────────────────────────
    post_snap = _count_structural_state()
    history   = state.get("cycle_history", [])
    prev_snap = history[-1].get("structural_snapshot", {}) if history else pre_snap

    modifiers = [
        f.get("exploration_cost", 0.0) * -0.5
        for f in all_findings
        if "exploration_cost" in f
    ]
    avg_modifier = round(sum(modifiers) / len(modifiers), 4) if modifiers else 0.0

    cycle_record: dict[str, Any] = {
        "cycle":                 state["total_cycles"],
        "timestamp":             _now(),
        "findings_count":        len(all_findings),
        "avg_confidence_modifier": avg_modifier,
        "reflections_delta":     post_snap.get("reflections", 0) - prev_snap.get("reflections", 0),
        "entities_delta":        post_snap.get("entities", 0)    - prev_snap.get("entities", 0),
        "goals_delta":           post_snap.get("goals", 0)       - prev_snap.get("goals", 0),
        "structural_snapshot":   post_snap,
    }
    history.append(cycle_record)
    state["cycle_history"] = history[-100:]  # keep last 100 cycles

    # ── Meta drift check (v0.9) — appended AFTER cap so it's never crowded out ─
    drift = _compute_meta_drift(state)
    if drift.get("alert"):
        all_findings.append({
            "finding_id":        _making_id(),
            "type":              "meta_drift_alert",
            "title":             (
                f"Meta-drift alert: system zmienia się "
                f"{drift['meta_drift_score']:.1f}× szybciej niż baseline"
            ),
            "description":       (
                f"W ciągu ostatnich {BOUNDS.meta_drift_window_days} dni tempo zmian strukturalnych "
                f"wynosi {drift['meta_drift_score']:.2f}× historyczny baseline "
                f"(próg: {BOUNDS.meta_drift_alert_threshold}). "
                f"avg_confidence_modifier: {drift['avg_confidence_modifier']:.3f}. "
                "Rozważ spowolnienie cykli lub przegląd zatwierdzonych findingów."
            ),
            "meta_drift_score":  drift["meta_drift_score"],
            "avg_confidence_modifier": drift["avg_confidence_modifier"],
            "cycles_in_window":  drift["cycles_in_window"],
            "confidence":        0.90,
            "created":           _now(),
            "state":             "pending",
            "action":            "acknowledge_meta_drift",
        })

    # Merge with existing pending findings
    existing_pending = [
        f for f in state.get("findings", [])
        if f.get("state") == "pending"
    ]
    state["findings"] = existing_pending + all_findings
    state["last_cycle_end"]      = _now()
    state["last_cycle_findings"] = len(all_findings)
    _save_state(state)

    _fire("sleeping_matylda.cycle_complete",
          findings=len(all_findings), reduced_scope=reduced_scope)
    log.info("Sleeping Matylda: cycle %d complete — %d new findings",
             state["total_cycles"], len(all_findings))

    try:
        from ..chronicle import log_and_build  # noqa: PLC0415
        log_and_build(
            source="sleeping_matylda",
            event_type="cycle_complete",
            context_ref="sleeping_matylda",
            metadata={"cycle": state["total_cycles"],
                      "findings": len(all_findings),
                      "reduced_scope": reduced_scope},
        )
    except Exception:  # noqa: BLE001
        pass

    return {
        "status":        "completed",
        "cycle":         state["total_cycles"],
        "findings_new":  len(all_findings),
        "reduced_scope": reduced_scope,
        "days_analysed": days,
        "findings":      all_findings,
    }


# ── NoGo Room signal feedback (v1.1) ─────────────────────────────────────────

def _nogo_feedback(finding: dict, decision: str) -> None:
    """Accumulate approve/dismiss signal for nogo_territory findings.

    Only fires for finding_type == "nogo_territory". Uses record_signal()
    which accumulates signals before updating risk (threshold-based, not
    one-shot). Fire-and-forget — exceptions silently swallowed.
    """
    if finding.get("type") != "nogo_territory":
        return
    thread_stem = finding.get("thread_stem", "")
    tag         = finding.get("tag", "")
    if not thread_stem or not tag:
        return
    try:
        from ..nogo_room import record_signal  # noqa: PLC0415
        record_signal(thread_stem, tag, decision)
    except Exception:  # noqa: BLE001
        pass


# ── Reflection pattern registration (v1.1) ───────────────────────────────────

def _register_reflection_pattern(finding: dict) -> None:
    """Register or update exploration pattern in Forgetroom when a reflection
    candidate is approved.

    Uses thread_stem as object_id (tożsamość wzorca, nie dokumentu).
    Fire-and-forget — exceptions silently swallowed.
    """
    if finding.get("type") != "reflection_candidate":
        return
    thread_stem = finding.get("thread_stem", "")
    if not thread_stem:
        return
    try:
        from ..forgetroom import register_object  # noqa: PLC0415
        register_object(
            object_id=thread_stem,
            object_type="reflection_pattern",
            initial_weight=round(finding.get("confidence", 0.5), 4),
        )
    except Exception:  # noqa: BLE001
        pass


def _activate_reflection_pattern_if_exists(thread_stem: str) -> None:
    """Activate an existing reflection_pattern in Forgetroom if one is tracked.

    Called when the same stem resurfaces with enough diary entries.
    Raises KeyError → no entry exists → silently skip (not an error).
    """
    try:
        from ..forgetroom import activate_object  # noqa: PLC0415
        activate_object(thread_stem)
    except KeyError:
        pass  # pattern not yet registered — fine, will be registered on first approval
    except Exception:  # noqa: BLE001
        pass


# ── Counterfactual Room recording (v1.0) ─────────────────────────────────────

def _record_cf_for_finding(finding: dict, decision: str) -> None:
    """Fire-and-forget: record approve/dismiss decision in Counterfactual Room.

    Only trajectory-linked finding types are recorded (reflection_candidate,
    synthesis_opportunity). All exceptions are silently swallowed.
    """
    try:
        from ..counterfactual_room import record_counterfactual  # noqa: PLC0415
        record_counterfactual(finding, decision)
    except Exception:  # noqa: BLE001
        pass


# ── Positive Room feedback ────────────────────────────────────────────────────

def _positive_feedback(finding: dict, success: bool) -> None:
    """Register approve/dismiss with Positive Room for trajectory-linked findings.

    Only fires for finding types that represent a trajectory judgement
    (reflection_candidate, synthesis_opportunity). Purely fire-and-forget —
    any exception is silently swallowed.
    """
    finding_type = finding.get("type", "")
    if finding_type not in ("reflection_candidate", "synthesis_opportunity"):
        return

    # Extract trajectory coordinates
    thread_stem  = finding.get("thread_stem") or ""
    tags         = finding.get("tags") or []
    tag          = finding.get("tag") or (tags[0] if tags else "")
    dominant_tag = tag or "untagged"
    if not thread_stem:
        # synthesis_opportunity lists threads; use dominant stem
        threads = finding.get("threads", [])
        thread_stem = threads[0] if threads else "unassigned"

    try:
        if success:
            from ..positive_room import record_success as _pos  # noqa: PLC0415
            _pos(thread_stem, dominant_tag)
        else:
            from ..positive_room import record_failure as _pos  # noqa: PLC0415
            _pos(thread_stem, dominant_tag)
    except Exception:  # noqa: BLE001
        pass


# ── Finding mutations ─────────────────────────────────────────────────────────

def get_findings(state_filter: str | None = None) -> list[dict]:
    """Return findings, optionally filtered by state ('pending'|'approved'|'dismissed')."""
    state = _load_state()
    findings = state.get("findings", [])
    if state_filter:
        findings = [f for f in findings if f.get("state") == state_filter]
    return findings


# ── Eisenhower triage ─────────────────────────────────────────────────────────

def _get_active_stems() -> set[str]:
    """Read active thread stems from desk/ACTIVE_THREADS.md."""
    import re
    active_md = ROOT / "desk" / "ACTIVE_THREADS.md"
    if not active_md.exists():
        return set()
    text = active_md.read_text(encoding="utf-8", errors="ignore")
    return {m.group(1) for m in re.finditer(r'\(.*?/([^/]+)\.md\)', text)}


def _eisenhower_score(finding: dict, active_stems: set[str]) -> dict:
    """Assign Eisenhower importance (0-1), urgency (0-1) and quadrant (1-4)."""
    ftype   = finding.get("type", "")
    conf    = float(finding.get("confidence", 0.5))
    source  = finding.get("source_thread", "") or ""
    action  = finding.get("action", "") or ""

    # Base scores by finding type
    importance_base = {
        "nogo_recheck":        0.90,
        "step_proposal":       0.75,
        "tension_analysis":    0.70,
        "question_focus":      0.60,
        "reflection_candidate":0.55,
        "stale_question":      0.30,
        "graph_orphan":        0.20,
    }.get(ftype, 0.45)

    urgency_base = {
        "nogo_recheck":        0.85,
        "step_proposal":       0.60,
        "tension_analysis":    0.55,
        "question_focus":      0.45,
        "reflection_candidate":0.35,
        "stale_question":      0.20,
        "graph_orphan":        0.10,
    }.get(ftype, 0.35)

    # Active thread boost
    if source and source in active_stems:
        importance_base = min(1.0, importance_base + 0.12)
        urgency_base    = min(1.0, urgency_base    + 0.18)

    # Confidence modifier: higher confidence → more important
    importance = importance_base * (0.65 + 0.35 * conf)
    urgency    = urgency_base

    # Action-specific boosts
    if action == "close_goal":
        urgency = min(1.0, urgency + 0.20)
    if action in ("reopen_trajectory",):
        importance = min(1.0, importance + 0.10)
        urgency    = min(1.0, urgency    + 0.10)

    importance = round(importance, 2)
    urgency    = round(urgency,    2)

    # Quadrant: I=imp≥0.50 & urg≥0.45, II=imp≥0.50, III=urg≥0.45, IV=rest
    if importance >= 0.50 and urgency >= 0.45:
        q = 1
    elif importance >= 0.50:
        q = 2
    elif urgency >= 0.45:
        q = 3
    else:
        q = 4

    return {"eisenhower_importance": importance, "eisenhower_urgency": urgency, "eisenhower_quadrant": q}


def triage_findings(auto_archive_q4: bool = True) -> dict:
    """Score all unscored pending findings, deduplicate by title, auto-archive Q4.

    Duplicate findings (same normalised title + type) are collapsed: the
    highest-confidence copy is kept as the 'champion', gets a `repeat_count`
    field and an importance boost (+0.04 per extra copy, capped at 1.0).
    All other copies are archived with reason 'eisenhower_deduped'.

    Returns a summary dict with counts per quadrant.
    """
    from collections import Counter, defaultdict

    state        = _load_state()
    findings     = state.get("findings", [])
    active_stems = _get_active_stems()
    scored = archived = deduped = 0

    # ── 1. Score unscored pending findings ────────────────────────────────────
    for f in findings:
        if f.get("state") != "pending":
            continue
        if "eisenhower_quadrant" in f:
            continue
        scores = _eisenhower_score(f, active_stems)
        f.update(scores)
        scored += 1

    # ── 2. Auto-archive Q4 ────────────────────────────────────────────────────
    if auto_archive_q4:
        for f in findings:
            if f.get("state") != "pending":
                continue
            if f.get("eisenhower_quadrant") == 4:
                f["state"]           = "archived"
                f["archived_reason"] = "eisenhower_q4_auto"
                archived += 1

    # ── 3. Deduplicate pending by normalised title + type ─────────────────────
    def _key(f: dict) -> str:
        return (f.get("type", "") + "|" + (f.get("title") or "").strip().lower())[:200]

    groups: dict[str, list] = defaultdict(list)
    for f in findings:
        if f.get("state") == "pending":
            groups[_key(f)].append(f)

    for key, group in groups.items():
        if len(group) <= 1:
            if group:
                group[0]["repeat_count"] = group[0].get("repeat_count", 1)
            continue
        # Champion = highest confidence; ties broken by created desc
        group.sort(key=lambda x: (-(x.get("confidence") or 0), x.get("created", "")))
        champion = group[0]
        duplicates = group[1:]

        repeat_n = len(group)
        champion["repeat_count"] = repeat_n
        # Boost importance for repeated findings (each extra copy = +0.04)
        boost = 0.04 * (repeat_n - 1)
        champion["eisenhower_importance"] = round(
            min(1.0, (champion.get("eisenhower_importance") or 0.5) + boost), 2
        )
        # Re-evaluate quadrant after boost
        imp = champion["eisenhower_importance"]
        urg = champion.get("eisenhower_urgency", 0.35)
        if imp >= 0.50 and urg >= 0.45:
            champion["eisenhower_quadrant"] = 1
        elif imp >= 0.50:
            champion["eisenhower_quadrant"] = 2
        elif urg >= 0.45:
            champion["eisenhower_quadrant"] = 3
        else:
            champion["eisenhower_quadrant"] = 4

        for dup in duplicates:
            dup["state"]           = "archived"
            dup["archived_reason"] = "eisenhower_deduped"
            deduped += 1
            archived += 1  # included in total archived count

    _save_state(state)

    pending = [f for f in findings if f.get("state") == "pending"]
    qc = Counter(f.get("eisenhower_quadrant", 0) for f in pending)
    return {
        "scored":        scored,
        "auto_archived": archived - deduped,
        "deduped":       deduped,
        "pending_total": len(pending),
        "by_quadrant":   {"q1": qc[1], "q2": qc[2], "q3": qc[3]},
    }


def approve_finding(finding_id: str, approved_by: str = "user") -> dict:
    """Approve a pending finding and execute its action."""
    state = _load_state()
    findings = state.get("findings", [])
    finding  = next((f for f in findings if f["finding_id"] == finding_id), None)

    if not finding:
        raise KeyError(f"Finding not found: {finding_id}")
    if finding["state"] != "pending":
        raise ValueError(f"Finding {finding_id} is in state {finding['state']!r}, not pending")

    result = _execute_finding(finding)

    finding["state"]            = "approved"
    finding["approved_by"]      = approved_by
    finding["approved_at"]      = _now()
    finding["execution_result"] = result

    _save_state(state)
    _fire("sleeping_matylda.finding_approved",
          finding_id=finding_id, action=finding.get("action"), result=result)

    # Positive Room feedback (v0.9) — register success for trajectory-linked findings
    _positive_feedback(finding, success=True)

    # NoGo Room signal (v1.1) — accumulate approve signal for nogo_territory findings
    _nogo_feedback(finding, "approve")

    # Reflection pattern registration (v1.1) — register pattern on reflection approval
    _register_reflection_pattern(finding)

    # Counterfactual Room recording (v1.0) — track decision for later evaluation
    _record_cf_for_finding(finding, "approve")

    log.info("Sleeping Matylda: finding approved: %s → %s", finding_id, result)
    return finding


def dismiss_finding(finding_id: str, reason: str = "") -> dict:
    """Dismiss a pending finding (no side effects)."""
    state = _load_state()
    findings = state.get("findings", [])
    finding  = next((f for f in findings if f["finding_id"] == finding_id), None)

    if not finding:
        raise KeyError(f"Finding not found: {finding_id}")
    if finding["state"] != "pending":
        raise ValueError(f"Finding {finding_id} is in state {finding['state']!r}, not pending")

    finding["state"]        = "dismissed"
    finding["dismissed_at"] = _now()
    finding["dismiss_reason"] = reason

    _save_state(state)

    # Positive Room feedback (v0.9) — register failure for trajectory-linked findings
    _positive_feedback(finding, success=False)

    # NoGo Room signal (v1.1) — accumulate dismiss signal for nogo_territory findings
    _nogo_feedback(finding, "dismiss")

    # Counterfactual Room recording (v1.0) — track decision for later evaluation
    _record_cf_for_finding(finding, "dismiss")

    log.info("Sleeping Matylda: finding dismissed: %s reason=%r", finding_id, reason)
    return finding


# ── Status ────────────────────────────────────────────────────────────────────

def get_status() -> dict:
    """Return full Sleeping Matylda status for dashboard."""
    state   = _load_state()
    pending = [f for f in state.get("findings", []) if f.get("state") == "pending"]

    by_type: dict[str, int] = {}
    for f in pending:
        t = f.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "last_cycle_start":    state.get("last_cycle_start"),
        "last_cycle_end":      state.get("last_cycle_end"),
        "last_cycle_findings": state.get("last_cycle_findings", 0),
        "total_cycles":        state.get("total_cycles", 0),
        "pending_findings":    len(pending),
        "pending_by_type":     by_type,
        "bounds": {
            "min_gap_hours":          BOUNDS.sleeping_matylda_min_gap_hours,
            "diary_lookback_days":    BOUNDS.sleeping_matylda_diary_lookback_days,
            "pattern_min_count":      BOUNDS.sleeping_matylda_pattern_min_count,
            "max_findings_per_cycle": BOUNDS.sleeping_matylda_max_findings_per_cycle,
        },
    }


def prune_old_findings(days: int = 30) -> int:
    """Remove terminal findings older than `days`. Returns count pruned."""
    state   = _load_state()
    cutoff  = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    before  = len(state.get("findings", []))
    state["findings"] = [
        f for f in state.get("findings", [])
        if not (
            f.get("state") in _FINDING_TERMINAL_STATES
            and (f.get("approved_at") or f.get("dismissed_at") or f.get("created", "")) < cutoff
        )
    ]
    pruned = before - len(state["findings"])
    if pruned:
        _save_state(state)
        log.info("Sleeping Matylda: pruned %d old findings", pruned)
    return pruned


# ── Background worker ─────────────────────────────────────────────────────────

_worker_task: asyncio.Task | None = None


async def _sm_worker_loop() -> None:
    """Asyncio background loop — runs cycle every sleeping_matylda_min_gap_hours."""
    log.info("Sleeping Matylda background worker started")
    interval = BOUNDS.sleeping_matylda_min_gap_hours * 3600
    while True:
        await asyncio.sleep(interval)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, run_cycle)
        except Exception:  # noqa: BLE001
            log.exception("Sleeping Matylda: background cycle error")


def start_background_worker() -> None:
    """Start the periodic background worker. Safe to call multiple times."""
    global _worker_task  # noqa: PLW0603
    if _worker_task and not _worker_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
        _worker_task = loop.create_task(_sm_worker_loop())
        log.info("Sleeping Matylda background worker task created")
    except RuntimeError:
        pass  # No running event loop during import / tests


def stop_background_worker() -> None:
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()


def worker_status() -> dict:
    return {
        "running": bool(_worker_task and not _worker_task.done()),
    }
