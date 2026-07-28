"""constitutional.py — single source of truth for all Matylda Lab limits.

This module is the ONE place where autonomy bounds are defined.
Every other module READS from here — none defines its own limits.

Design rules:
  1. Frozen dataclass — values cannot be mutated at runtime.
  2. No imports from other Matylda modules (prevents circular deps).
  3. All values documented with rationale and allowed range.
  4. Version-stamped — bump CONSTITUTIONAL_VERSION on any change.

Usage:
    from .constitutional import BOUNDS

    if active_threads > BOUNDS.max_active_threads:
        ...

Do NOT pass BOUNDS around as a mutable dict. Import it directly.
"""
from __future__ import annotations

from dataclasses import dataclass

CONSTITUTIONAL_VERSION = "1.2"


@dataclass(frozen=True)
class AutonomyBounds:
    """Immutable autonomy limits for Matylda Lab.

    Groups:
      threads       — thread lifecycle caps
      memory        — memory tier limits
      homeostasis   — fatigue / attention budget
      darkroom      — quality gate thresholds
      search        — index and retrieval limits
      briefing      — session gap and context limits
    """

    # ── Threads ───────────────────────────────────────────────────────────────
    max_active_threads: int = 5
    """Maximum number of non-frozen threads before warning.
    Dashboard shows orange at this value, red at max_active_threads_hard."""

    max_active_threads_hard: int = 8
    """Hard cap — above this ThreadWatcher logs a critical alert."""

    max_threads_for_link_detection: int = 15
    """How many recent threads are scanned for cross-thread connection detection."""

    thread_watcher_poll_interval: float = 2.0
    """Seconds between ThreadWatcher file-system polls."""

    # ── Memory ────────────────────────────────────────────────────────────────
    max_rules_injection_tokens: int = 500
    """Approximate token budget for injecting rules.md into system prompt.
    1 token ≈ 4 chars. Keeps rule injection lightweight."""

    max_diary_briefing_entries: int = 5
    """How many diary entries surface in the morning briefing card."""

    diary_retention_days: int = 30
    """Days of diary to load by default for list_diary_entries()."""

    reflection_retention_days: int = 90
    """Days of reflections included in list_reflections()."""

    reflection_min_confidence: float = 0.6
    """Minimum confidence for a reflection to be injected into system prompt."""

    reflection_min_occurrences: int = 3
    """Minimum observation count for a pattern before it qualifies for promotion."""

    negative_excerpt_chars: int = 2000
    """Max characters per negative memory file surfaced in briefing."""

    # ── Homeostasis ───────────────────────────────────────────────────────────
    attention_budget_per_session: int = 10
    """Max distinct topics / questions Matylda tracks in one session.
    Exceeding this → stale_items overflow, attention quality degrades."""

    max_open_goals: int = 5
    """Max concurrent active goals tracked in homeostasis/active_goals.json.
    Above this threshold new goals require closing an existing one."""

    fatigue_recovery_hours: float = 8.0
    """Hours of inactivity after which fatigue resets to 0.0."""

    fatigue_increment_per_session: float = 0.15
    """How much fatigue increases per session (0.0–1.0 scale).
    At fatigue >= fatigue_high_threshold → reduce synthesis depth."""

    fatigue_high_threshold: float = 0.75
    """Fatigue level above which Sleeping Matylda reduces cycle depth."""

    stale_item_age_hours: float = 72.0
    """Hours before an attention item is considered stale and moved to stale_items.json."""

    # ── DARKROOM ──────────────────────────────────────────────────────────────
    approval_severity_threshold: float = 0.5
    """Max severity score at which a review creates a PendingApproval.
    Was _APPROVAL_THRESHOLD in pipeline.py."""

    epistemic_limit_threshold: float = 0.7
    """Sum of task-relevant tension severities above which Epistemic Limit Mode activates.
    The global registry remains available for audit, but does not turn every
    conversation into an alarm state."""

    darkroom_context_max_tensions: int = 3
    """Maximum number of task-relevant tensions injected into a normal prompt.
    Keeps DARKROOM proportional and leaves room for constructive work."""

    failure_rate_amplifier: float = 0.3
    """Added to severity_sum when failure_rate > failure_rate_alarm_level."""

    failure_rate_alarm_level: float = 0.25
    """Failure rate above which the amplifier kicks in (was hardcoded 0.25)."""

    # ── Search / index ────────────────────────────────────────────────────────
    search_index_ttl_seconds: int = 30
    """Seconds before the in-memory FTS5 index is rebuilt."""

    search_max_file_size_kb: int = 300
    """Files larger than this (in KB) are skipped by the search indexer."""

    # ── Briefing ──────────────────────────────────────────────────────────────
    briefing_min_gap_hours: float = 8.0
    """Minimum hours since last session before showing morning briefing.
    Was _MIN_GAP_HOURS in briefing_manager.py."""

    briefing_max_connections: int = 5
    """Max cross-thread connections shown in briefing."""

    # ── Proactive suggestions (v0.5) ──────────────────────────────────────────
    max_proactive_suggestions: int = 3
    """Max stale-thread suggestions shown simultaneously (attention budget guard).
    Roadmap: 'max 3 sugestie jednocześnie'."""

    stale_thread_age_days: float = 7.0
    """Thread with no writes for this many days qualifies for a staleness suggestion."""

    proactive_connection_threshold: float = 0.75
    """Minimum semantic similarity (0–1) to propose a knowledge graph relation.
    Derived from thread_links integer score / 100."""

    stale_scan_interval_hours: float = 24.0
    """How often ThreadWatcher runs the proactive stale-thread scan."""

    snooze_default_days: int = 7
    """Default snooze period for ignored stale-thread suggestions."""

    # ── Task Queue (v0.6) ─────────────────────────────────────────────────────
    max_queued_tasks: int = 20
    """Hard cap on tasks in queue (queued + running). New enqueue fails above this."""

    max_running_tasks: int = 3
    """Max tasks in 'running' state simultaneously (maps to attention_budget parallel cap)."""

    task_approval_token_threshold: int = 2000
    """Tasks with estimated_tokens above this require explicit approval before running."""

    task_result_max_chars: int = 50_000
    """Max characters stored in task result field (truncated if exceeded)."""

    task_retention_days: int = 30
    """Days before completed/failed tasks are pruned from the queue file."""

    # ── Sleeping Matylda (v0.7) ───────────────────────────────────────────────
    sleeping_matylda_min_gap_hours: float = 6.0
    """Minimum hours between automatic consolidation cycles.
    Prevents Sleeping Matylda from overwhelming the workspace with findings."""

    sleeping_matylda_diary_lookback_days: int = 7
    """Days of diary entries analysed per cycle.
    Halved automatically when fatigue >= fatigue_high_threshold."""

    sleeping_matylda_pattern_min_count: int = 3
    """Minimum diary entries per thread before promoting to reflection candidate.
    Must be >= reflection_min_occurrences so promoted reflections pass injection guard."""

    sleeping_matylda_max_findings_per_cycle: int = 5
    """Hard cap on findings surfaced per cycle (attention budget guard).
    Excess findings are silently dropped (highest-confidence kept)."""

    sleeping_matylda_graph_similarity_threshold: float = 0.7
    """Min label token-overlap ratio for flagging potential duplicate graph entities."""

    # ── NoGo Room (v0.8) ──────────────────────────────────────────────────────────
    nogo_risk_threshold: float = 0.7
    """Effective risk above which a trajectory's findings get deprioritized.
    Does not block exploration — reduces confidence_modifier instead."""

    nogo_max_entries: int = 200
    """Hard cap on trajectory entries in NoGo Room. Oldest pruned when exceeded."""

    nogo_failure_weight: float = 0.30
    """Additive increase to stored_risk_score per failure event (capped at 1.0)."""

    nogo_success_weight: float = 0.20
    """Multiplicative reduction: risk *= (1 - nogo_success_weight). Never reaches 0."""

    nogo_drift_weight: float = 0.10
    """Per-unit weight of drift_score contribution to risk_score update."""

    nogo_decay_k: float = 0.02
    """Per-day decay of effective_risk: effective = stored * exp(-k * days_since_last_seen).
    k=0.02 → 50% at ~35 days, 5% at ~150 days. Prevents neurotic memory."""

    nogo_min_evidence_count: int = 5
    """Evidence count for full risk weight. Below this, effective_risk is discounted:
    evidence_discount = min(1.0, evidence_count / nogo_min_evidence_count)."""

    # ── Forgetroom (v0.8) ─────────────────────────────────────────────────────────
    forgetroom_decay_k: float = 0.05
    """Per-day decay constant: effective_weight = w0 * (1+log(1+reinf)) * exp(-k*t).
    k=0.05 → 50% at 14 days, 5% at ~60 days. Faster than NoGo (trash fades quicker)."""

    forgetroom_prune_threshold: float = 0.05
    """Effective weight below which object → 'forgotten_object' finding."""

    forgetroom_max_objects: int = 500
    """Hard cap on tracked objects. Lowest-weight objects pruned when exceeded."""

    # ── Positive Room (v0.9) ───────────────────────────────────────────────────────
    positive_success_weight: float = 0.25
    """Additive increase to success_score per success event (capped at 1.0).
    Mirrors nogo_failure_weight — symmetric architecture."""

    positive_failure_weight: float = 0.15
    """Multiplicative decay per failure: success *= (1 - weight). Never reaches 0.
    Mirrors nogo_success_weight but weaker — single failure shouldn't kill attraction."""

    positive_success_threshold: float = 0.5
    """Effective success above which trajectory contributes a positive discount
    to exploration_cost in branch_evaluator."""

    positive_novelty_floor: float = 0.25
    """Minimum novelty_factor for attraction discount: max(floor, 1/(1+log(1+reuse))).
    Prevents very familiar trajectories from losing all attraction.
    'Breathing is still attractive after 1000 repetitions.'"""

    positive_max_entries: int = 200
    """Hard cap on trajectory entries in Positive Room. Oldest pruned when exceeded."""

    # ── Meta Drift (v0.9) ─────────────────────────────────────────────────────────
    meta_drift_window_days: int = 30
    """Rolling window for meta_drift_score computation.
    Score = structural_change_rate_now / structural_change_rate_baseline."""

    meta_drift_alert_threshold: float = 2.0
    """meta_drift_score above this → surface 'meta_drift_alert' finding.
    Score > 2.0 means changing at 2× the historical baseline rate."""

    # ── NoGo Auto-Write (v1.1) ───────────────────────────────────────────────────
    nogo_auto_failure_threshold: int = 3
    """Number of dismiss signals on a nogo_territory finding before record_failure
    is called on the trajectory. Accumulation prevents single decisions from
    having outsized impact. Higher than success threshold: dismissing warnings
    repeatedly needs more signal before the system pushes back."""

    nogo_auto_success_threshold: int = 2
    """Number of approve signals on a nogo_territory finding before record_success
    is called on the trajectory. Approving (engaging with the risk) rehabilitates
    faster than repeatedly dismissing condemns: active engagement is rewarded."""

    # ── Counterfactual Room (v1.0) ────────────────────────────────────────────────
    counterfactual_evaluation_days: int = 14
    """Days after approve/dismiss before a counterfactual record is evaluated.
    Long enough that real signal can emerge, short enough to stay relevant."""

    counterfactual_min_signal: int = 2
    """Minimum new diary entries required to conclude a dismissed finding was wrong.
    Confounding guard: one stray entry ≠ the thread genuinely resurfaced.
    Also requires novel_entity_delta >= 1 (discovery vs rumination)."""

    counterfactual_correction_magnitude: float = 0.08
    """Bounded correction applied to Positive Room per evaluation.
    Weak signal — keeps corrections from dominating Positive Room history.
    Applied only to Positive Room; NoGo Room is never touched by Counterfactual."""


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this everywhere. Do NOT instantiate AutonomyBounds yourself.

BOUNDS = AutonomyBounds()
