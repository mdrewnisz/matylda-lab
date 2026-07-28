"""Sleeping Matylda package.

Submodules:
  synthesis.py        — v0 LLM-based reflective synthesis (existing)
  bridge.py           — socket/WebSocket IPC listener (existing)
  protocol.py         — message types (existing)
  sync.py             — state sync (existing)
  consolidation.py    — v1.0 autonomous consolidation agent
  focus_engine.py     — v1.2 Focus Mode (directed attention sessions)

Public API (v1.0 consolidation):
"""
# Re-export consolidation API so callers can do:
#   from matylda_lite.sleeping_matylda import run_cycle, get_status, ...
from .consolidation import (  # noqa: F401
    run_cycle,
    get_status,
    get_findings,
    approve_finding,
    dismiss_finding,
    prune_old_findings,
    start_background_worker,
    stop_background_worker,
    worker_status,
    # v0.9 additions
    get_meta_drift,
    snapshot_identity,
    list_snapshots,
    compare_snapshots,
    # test helpers
    _load_state,
    _save_state,
    _STATE_FILE,
    _SNAPSHOTS_FILE,
)

# v1.2 Focus Mode API
from .focus_engine import (  # noqa: F401
    FocusSessionConfig,
    start_focus_session,
    get_focus_status,
    pause_focus_session,
    resume_focus_session,
    stop_focus_session,
    VALID_FOCUS_AREAS,
)
