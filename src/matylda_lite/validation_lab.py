"""validation_lab.py — closed validation loop for silo_3 (Programming).

The missing loop most agent systems lack: experiment → measurement → belief
update. Matylda has narrow instances of this already (counterfactual_room.py
tracks decision outcomes against a *proxy* signal), but no place where a claim
is checked against *ground truth*.

silo_3 is the one place where ground truth is free: the Python interpreter.
A `code_review` finding makes a falsifiable claim — "this code has bug X,
reproducible by repro_call, fixed by fixed_code". That claim is mechanically
checkable:

    run(original_code + repro_call)  → should RAISE   (bug reproduces)
    run(fixed_code    + repro_call)  → should be CLEAN (fix works)

The verdict comes from the interpreter, not from an LLM grading its own
homework. The model cannot fake a crash — `python` is the independent oracle.

This is deliberately Level 1 only: it measures *reproducibility + absence of
crash*, NOT *correctness of the result* (that would need an oracle = a future
phase). We never claim more than the interpreter actually proves.

Verdicts:
  confirmed       — original raised, fixed clean        → real bug, working fix
  unreproducible  — original did NOT raise              → false positive
  fix_failed      — original raised, fixed still raised  → real bug, bad fix
  inconclusive    — timeout / missing inputs / both broke → operator reviews

Feedback (Phase 2), only on clear verdicts:
  confirmed       → update_model_performance(success=True)
  unreproducible  → update_model_performance(success=False) + DARKROOM tension
  fix_failed      → update_model_performance(success=False)
  inconclusive    → no automated feedback

Safety: LLM-generated code runs in a macOS sandbox-exec jail with network
DENIED at the OS level, a wall-clock timeout, a throwaway temp cwd, and a
stripped environment (so snippets can't read inherited secrets like
ANTHROPIC_API_KEY). Filesystem reads are NOT fully isolated in this MVP —
validation is opt-in per finding on code the operator has already seen, never
an automatic background sweep. AI proposes the verdict; the operator decides.

State file: data/validation_lab.json
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT

log = logging.getLogger(__name__)

_STATE_FILE = ROOT / "data" / "validation_lab.json"
_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# macOS sandbox profile: allow everything python needs to start, deny network.
_SANDBOX_PROFILE = "(version 1)(allow default)(deny network*)"

_DEFAULT_TIMEOUT = 5.0
_OUTPUT_CAP = 2000


# ── Helpers ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> dict:
    if not _STATE_FILE.exists():
        return {"records": []}
    try:
        import json
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"records": []}


def _save_state(state: dict) -> None:
    from .atomic_state import atomic_write_json  # noqa: PLC0415
    atomic_write_json(_STATE_FILE, state)


def _sandbox_available() -> bool:
    """True if macOS sandbox-exec is present (real network isolation)."""
    return Path("/usr/bin/sandbox-exec").exists()


# ── Sandboxed execution (the ground-truth oracle) ───────────────────────────

def _run_sandboxed(code: str, timeout: float = _DEFAULT_TIMEOUT) -> dict:
    """Run a self-contained Python snippet in an isolated subprocess.

    Returns dict: raised(bool), exit_code, stdout, stderr, timed_out(bool),
    network_isolated(bool). `raised` is True iff the interpreter exited
    non-zero (uncaught exception) or timed out.
    """
    # Minimal env: no inherited secrets reach the snippet. -I isolates python
    # from PYTHON* env vars and user site-packages.
    minimal_env = {"PATH": "/usr/bin:/bin", "HOME": tempfile.gettempdir()}

    with tempfile.TemporaryDirectory(prefix="vlab_") as tmpdir:
        script = Path(tmpdir) / "snippet.py"
        script.write_text(code, encoding="utf-8")

        sandboxed = _sandbox_available()
        if sandboxed:
            cmd = ["/usr/bin/sandbox-exec", "-p", _SANDBOX_PROFILE,
                   sys.executable, "-I", str(script)]
        else:
            # Non-macOS / no sandbox-exec: plain isolated subprocess.
            # Timeout + temp cwd + stripped env still apply; network is NOT
            # isolated in this fallback (flagged in the result).
            cmd = [sys.executable, "-I", str(script)]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir,
                env=minimal_env,
            )
            return {
                "raised":           proc.returncode != 0,
                "exit_code":        proc.returncode,
                "stdout":           proc.stdout[:_OUTPUT_CAP],
                "stderr":           proc.stderr[:_OUTPUT_CAP],
                "timed_out":        False,
                "network_isolated": sandboxed,
            }
        except subprocess.TimeoutExpired:
            return {
                "raised":           True,
                "exit_code":        None,
                "stdout":           "",
                "stderr":           f"TIMEOUT after {timeout}s",
                "timed_out":        True,
                "network_isolated": sandboxed,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "raised":           True,
                "exit_code":        None,
                "stdout":           "",
                "stderr":           f"sandbox launch error: {exc}",
                "timed_out":        False,
                "network_isolated": sandboxed,
            }


def _verdict(orig: dict, fixed: dict) -> tuple[str, str]:
    """Derive verdict + one-line rationale from two execution results."""
    if orig["timed_out"] or fixed["timed_out"]:
        return "inconclusive", "Egzekucja przekroczyła limit czasu (możliwa pętla nieskończona)."
    if not orig["raised"]:
        return "unreproducible", "Oryginalny kod NIE rzucił błędu — finding wygląda na false positive."
    # original raised:
    if not fixed["raised"]:
        return "confirmed", "Oryginał rzucił błąd, fix przeszedł czysto — bug realny, fix działa."
    return "fix_failed", "Oryginał rzucił błąd i fix nadal rzuca — bug realny, ale fix nie naprawia."


# ── Phase 2: feedback into the system ───────────────────────────────────────

def _apply_feedback(verdict: str, model: str, finding: dict) -> dict:
    """Feed the measured verdict back into UCB1 + DARKROOM. Returns summary."""
    applied = {"ucb1": None, "tension_id": None}

    # UCB1 — a measured outcome, not a self-report
    success_map = {"confirmed": True, "unreproducible": False, "fix_failed": False}
    if verdict in success_map:
        try:
            from .models import update_model_performance  # noqa: PLC0415
            update_model_performance(
                task_type="coding",
                model=model,
                success=success_map[verdict],
                project_id="silo_3_validation",
            )
            applied["ucb1"] = success_map[verdict]
        except Exception:  # noqa: BLE001
            log.debug("validation_lab: UCB1 feedback skipped (import error)")

    # DARKROOM tension only for hallucinated bugs (unreproducible)
    if verdict == "unreproducible":
        try:
            from .darkroom import tension as tens  # noqa: PLC0415
            t = tens.create(
                description=(
                    "silo_3 code_review wyprodukował niereprodukowalny finding: "
                    f"{(finding.get('title') or finding.get('description') or '')[:160]}"
                ),
                tension_type="hallucination_pattern",
                severity=0.55,
                source_task="validation_lab:silo_3",
            )
            applied["tension_id"] = t.get("id")
        except Exception:  # noqa: BLE001
            log.debug("validation_lab: DARKROOM tension skipped (import error)")

    return applied


# ── Public API ──────────────────────────────────────────────────────────────

def validate_finding(
    finding: dict,
    original_code: str,
    *,
    enable_feedback: bool = True,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict:
    """Validate one code_review finding against the Python interpreter.

    Args:
        finding: a finding dict; must carry `repro_call` and `fixed_code`.
        original_code: the code that was reviewed (the repro runs against it).
        enable_feedback: if True, apply Phase-2 feedback (UCB1 + DARKROOM).
        timeout: per-execution wall-clock limit (seconds).

    Returns:
        A record dict (also appended to data/validation_lab.json) with the
        verdict, both execution results, and any feedback applied.
    """
    language   = (finding.get("language") or "python").lower()
    repro_call = (finding.get("repro_call") or "").strip()
    fixed_code = (finding.get("fixed_code") or "").strip()
    model      = finding.get("model") or "opus"

    record: dict = {
        "validation_id": "vlab_" + uuid.uuid4().hex[:8],
        "finding_id":    finding.get("finding_id", ""),
        "validated_at":  _now(),
        "language":      language,
        "verdict":       "inconclusive",
        "rationale":     "",
        "original_exec": None,
        "fixed_exec":    None,
        "feedback":      None,
        "duration_ms":   0,
    }

    # Guard rails — only python in MVP, need both repro_call + fixed_code
    if language != "python":
        record["rationale"] = f"Język '{language}' nieobsługiwany (MVP: tylko python)."
        _persist(record)
        return record
    if not repro_call or not fixed_code:
        record["rationale"] = "Brak repro_call lub fixed_code — nie da się uruchomić walidacji."
        _persist(record)
        return record

    started = time.monotonic()
    orig_script  = f"{original_code}\n\n{repro_call}\n"
    fixed_script = f"{fixed_code}\n\n{repro_call}\n"

    orig  = _run_sandboxed(orig_script,  timeout=timeout)
    fixed = _run_sandboxed(fixed_script, timeout=timeout)

    verdict, rationale = _verdict(orig, fixed)
    record["verdict"]       = verdict
    record["rationale"]     = rationale
    record["original_exec"] = orig
    record["fixed_exec"]    = fixed
    record["duration_ms"]   = round((time.monotonic() - started) * 1000)

    if enable_feedback:
        record["feedback"] = _apply_feedback(verdict, model, finding)

    _persist(record)
    log.info("validation_lab: finding %s → %s", record["finding_id"] or "?", verdict)
    return record


def _persist(record: dict) -> None:
    state = _load_state()
    state.setdefault("records", []).append(record)
    _save_state(state)


def list_validations(limit: int = 50) -> list[dict]:
    """Return the most recent validation records (newest first)."""
    records = _load_state().get("records", [])
    return list(reversed(records))[:limit]


def validation_status() -> dict:
    """Summary for dashboard/briefing."""
    from collections import Counter
    records = _load_state().get("records", [])
    verdicts = Counter(r.get("verdict") for r in records)
    return {
        "total":           len(records),
        "by_verdict":      dict(verdicts),
        "sandbox_active":  _sandbox_available(),
    }
