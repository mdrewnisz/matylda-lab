"""branch_evaluator.py — v0.9 branch expansion cost evaluator.

Evaluates a thread+tag trajectory before Sleeping Matylda generates findings.
Returns a continuous exploration_cost in [0.0, 1.0] and a confidence_modifier
applied to finding confidence.

Design:
  - No binary block ("never go there")
  - exploration_cost is a weighted blend: NoGo + length + dependencies - Positive
  - confidence_modifier = -(exploration_cost * 0.5), so max penalty is -0.5
  - should_prune = exploration_cost >= 0.9 (a hint, not a hard gate)

Cost formula (v0.9):
  raw_cost = (
      0.40 * nogo_component        # effective_risk / nogo_risk_threshold
    + 0.30 * length_component      # entry_count / (lookback_days * 3)
    + 0.30 * dependency_component  # dep_count / max_threads_for_link_detection
  )
  positive_discount = positive_component * novelty_factor
    where:
      positive_component = effective_success / positive_success_threshold (capped 0..1)
      novelty_factor = max(positive_novelty_floor, 1 / (1 + log(1 + reuse_count)))
      max positive_discount = 0.3 (so cost stays meaningful even for beloved trajectories)

  exploration_cost = max(0.0, raw_cost - positive_discount)
"""
from __future__ import annotations

import math

from .constitutional import BOUNDS


def evaluate_branch(
    thread_stem: str,
    dominant_tag: str,
    entry_count: int,
    dependency_count: int,
) -> dict:
    """Score a branch before expansion.

    Args:
        thread_stem:       The thread being evaluated.
        dominant_tag:      Primary tag for this trajectory.
        entry_count:       Number of diary entries in the thread.
        dependency_count:  Number of outgoing graph relations for entities in thread.

    Returns:
        {
          "exploration_cost":    float,   # 0.0–1.0 (main output)
          "confidence_modifier": float,   # applied to finding confidence (≤ 0)
          "should_prune":        bool,    # exploration_cost >= 0.9 (derived hint)
          "effective_risk":      float,   # raw NoGo effective_risk
          "effective_success":   float,   # raw Positive effective_success (v0.9)
          "positive_discount":   float,   # how much Positive Room reduced cost (v0.9)
          "novelty_factor":      float,   # novelty multiplier for Positive discount (v0.9)
          "reason":              str|None, # label for dominant cost driver
          "checks": {
            "branch_length_ok":    bool,
            "dependency_count_ok": bool,
            "nogo_ok":             bool,
            "positive_ok":         bool,  # True if Positive Room contributed discount
          }
        }
    """
    # ── NoGo component ────────────────────────────────────────────────────────
    try:
        from .nogo_room import get_risk_score  # noqa: PLC0415
        effective_risk = get_risk_score(thread_stem, dominant_tag)
    except Exception:  # noqa: BLE001
        effective_risk = 0.0

    nogo_component = min(1.0, effective_risk / max(BOUNDS.nogo_risk_threshold, 1e-6))

    # ── Length component ──────────────────────────────────────────────────────
    max_length = BOUNDS.sleeping_matylda_diary_lookback_days * 3
    length_component = min(1.0, entry_count / max(max_length, 1))

    # ── Dependency component ──────────────────────────────────────────────────
    max_dep = BOUNDS.max_threads_for_link_detection
    dependency_component = min(1.0, dependency_count / max(max_dep, 1))

    # ── Raw cost ──────────────────────────────────────────────────────────────
    raw_cost = (
        0.40 * nogo_component
        + 0.30 * length_component
        + 0.30 * dependency_component
    )

    # ── Positive Room discount (v0.9) ─────────────────────────────────────────
    try:
        from .positive_room import get_success_score, get_trajectory  # noqa: PLC0415
        effective_success = get_success_score(thread_stem, dominant_tag)
        pos_traj = get_trajectory(thread_stem, dominant_tag)
        reuse_count = pos_traj["reuse_count"] if pos_traj else 0
    except Exception:  # noqa: BLE001
        effective_success = 0.0
        reuse_count = 0

    novelty_factor = max(
        BOUNDS.positive_novelty_floor,
        1.0 / (1.0 + math.log(1.0 + reuse_count)),
    )
    positive_component = min(
        1.0, effective_success / max(BOUNDS.positive_success_threshold, 1e-6)
    )
    # Max discount capped at 0.3 — costs stay meaningful even for well-known paths
    positive_discount = round(min(0.30, positive_component * novelty_factor * 0.30), 4)

    # ── Final cost ────────────────────────────────────────────────────────────
    exploration_cost = round(max(0.0, raw_cost - positive_discount), 4)

    # ── Checks ────────────────────────────────────────────────────────────────
    checks = {
        "branch_length_ok":    entry_count <= max_length,
        "dependency_count_ok": dependency_count <= max_dep,
        "nogo_ok":             effective_risk < BOUNDS.nogo_risk_threshold,
        "positive_ok":         positive_discount > 0.0,
    }

    # ── Reason label (dominant cost driver) ───────────────────────────────────
    if exploration_cost < 0.3:
        reason = None
    else:
        components = [
            ("nogo",         0.40 * nogo_component),
            ("branch_length", 0.30 * length_component),
            ("dependencies",  0.30 * dependency_component),
        ]
        reason = max(components, key=lambda x: x[1])[0]

    confidence_modifier = round(-exploration_cost * 0.5, 4)
    should_prune        = exploration_cost >= 0.9

    return {
        "exploration_cost":    exploration_cost,
        "confidence_modifier": confidence_modifier,
        "should_prune":        should_prune,
        "effective_risk":      round(effective_risk, 4),
        "effective_success":   round(effective_success, 4),
        "positive_discount":   positive_discount,
        "novelty_factor":      round(novelty_factor, 4),
        "reason":              reason,
        "checks":              checks,
    }
