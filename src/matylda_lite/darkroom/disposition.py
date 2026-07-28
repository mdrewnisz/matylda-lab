"""Disposition layer — persistent heuristic weights.

This is NOT personality. These are calibration parameters that
adjust how the system approaches epistemic tasks.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..config import ROOT

_DIR = ROOT / "darkroom" / "disposition"
_PROFILE   = _DIR / "disposition_profile.json"
_WEIGHTS   = _DIR / "heuristic_weights.json"
_DRIFT_ADJ = _DIR / "drift_adjustments.json"

# Global disposition is the constructive Lab baseline. Explicit NO-GO mode has
# its own prompt and does not need to harden Matylda's normal voice.
CREATIVE_BASELINE = {
    "skepticism_level": 0.48,
    "uncertainty_tolerance": 0.85,
    "falsification_preference": 0.60,
    "verbosity_calibration": 0.45,
    "abstraction_preference": 0.50,
    "narrative_risk_sensitivity": 0.60,
    "simplicity_preference": 0.65,
    "review_strictness": 0.55,
}

_AUTOMATIC_APPROVAL_CEILINGS = {
    "skepticism_level": 0.65,
    "falsification_preference": 0.70,
    "narrative_risk_sensitivity": 0.70,
    "review_strictness": 0.70,
}

_PROFILE_KEYS = [
    "skepticism_level",
    "uncertainty_tolerance",
    "falsification_preference",
    "verbosity_calibration",
    "abstraction_preference",
    "narrative_risk_sensitivity",
    "simplicity_preference",
    "review_strictness",
]

_LABELS = {
    "skepticism_level":          "Sceptycyzm",
    "uncertainty_tolerance":     "Tolerancja niepewności",
    "falsification_preference":  "Preferencja falsyfikacji",
    "verbosity_calibration":     "Kalibracja obszerności",
    "abstraction_preference":    "Preferencja abstrakcji",
    "narrative_risk_sensitivity": "Czułość na drift narracyjny",
    "simplicity_preference":     "Preferencja prostoty",
    "review_strictness":         "Surowość recenzji",
}


def load_profile() -> dict:
    return json.loads(_PROFILE.read_text(encoding="utf-8"))


def load_weights() -> dict:
    return json.loads(_WEIGHTS.read_text(encoding="utf-8"))


def load_drift_adjustments() -> dict:
    return json.loads(_DRIFT_ADJ.read_text(encoding="utf-8"))


def save_profile(profile: dict) -> None:
    profile["last_updated"] = str(date.today())
    _PROFILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def automatic_approval_ceiling(key: str) -> float:
    """Maximum value an ordinary review may propose for a global setting."""
    return _AUTOMATIC_APPROVAL_CEILINGS.get(key, 1.0)


def apply_approval(proposed_changes: dict) -> dict:
    """Apply approved disposition changes. Returns updated profile."""
    profile = load_profile()
    for key, change in proposed_changes.items():
        if key in profile and isinstance(change, dict):
            value = change.get("to", profile[key])
        elif key in profile:
            value = change
        else:
            continue
        if isinstance(value, (int, float)):
            value = min(float(value), automatic_approval_ceiling(key))
        profile[key] = value
    profile["update_count"] = profile.get("update_count", 0) + 1
    save_profile(profile)
    return profile


def profile_labels() -> dict:
    """Return human-readable labels for profile keys."""
    return _LABELS


def log_disposition_snapshot(profile: dict, trigger: str = "") -> None:
    """Append a snapshot of the current disposition to the history log."""
    from datetime import date as _date  # noqa: PLC0415
    from ..config import ROOT as _ROOT  # noqa: PLC0415
    history_file = _ROOT / "darkroom" / "disposition" / "history.json"

    try:
        existing = json.loads(history_file.read_text(encoding="utf-8")) if history_file.exists() else []
    except Exception:
        existing = []

    snapshot = {
        "date": str(_date.today()),
        "trigger": trigger,
        "update_count": profile.get("update_count", 0),
        "values": {k: v for k, v in profile.items()
                   if isinstance(v, float) and k not in ("failure_rate",)},
    }
    existing.append(snapshot)
    # Keep last 100 snapshots
    existing = existing[-100:]
    history_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def load_disposition_history() -> list[dict]:
    """Return all disposition snapshots, oldest first."""
    from ..config import ROOT as _ROOT  # noqa: PLC0415
    history_file = _ROOT / "darkroom" / "disposition" / "history.json"
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def to_context_string(profile: dict, weights: dict) -> str:
    """Render disposition as a compact string for injection into prompts."""
    lines = [
        "[DARKROOM DISPOSITION — calibration, not personality]",
        "  default_mode: constructive_exploration",
        "  critique_policy: proportionate; hostile review only in explicit NO-GO",
    ]
    for k in _PROFILE_KEYS:
        v = profile.get(k, 0.5)
        lines.append(f"  {k}: {v:.2f}")
    lines.append(f"  failure_memory_weight: {weights.get('failure_memory_weight', 0.8):.2f}")
    lines.append(f"  drift_penalty: {weights.get('drift_penalty', 0.7):.2f}")
    return "\n".join(lines)
