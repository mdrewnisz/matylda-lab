"""Tests for validation_lab.py — the silo_3 closed validation loop.

These exercise the real sandbox (they spawn python subprocesses), so they
verify ground-truth verdict logic end to end. Feedback is disabled by default
so tests don't pollute model_performance.jsonl / DARKROOM state.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from matylda_lite import validation_lab


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    """Point validation_lab state file at a temp location."""
    state_file = tmp_path / "validation_lab.json"
    monkeypatch.setattr(validation_lab, "_STATE_FILE", state_file)
    return state_file


# ── Verdict logic against the real interpreter ───────────────────────────────

def test_confirmed_real_bug_with_working_fix(isolated_state):
    """Original raises, fix is clean → confirmed."""
    finding = {
        "finding_id": "f_confirmed",
        "repro_call": "print(divide(1, 0))",
        "fixed_code": "def divide(a, b):\n    return a / b if b else 0",
    }
    original = "def divide(a, b):\n    return a / b"
    rec = validation_lab.validate_finding(finding, original, enable_feedback=False)
    assert rec["verdict"] == "confirmed"
    assert rec["original_exec"]["raised"] is True
    assert rec["fixed_exec"]["raised"] is False


def test_unreproducible_false_positive(isolated_state):
    """Original does NOT raise → the claimed bug is a false positive."""
    finding = {
        "finding_id": "f_false",
        "repro_call": "print(add_one(5))",   # no error — function is fine
        "fixed_code": "def add_one(x):\n    return x + 1",
    }
    original = "def add_one(x):\n    return x + 1"
    rec = validation_lab.validate_finding(finding, original, enable_feedback=False)
    assert rec["verdict"] == "unreproducible"
    assert rec["original_exec"]["raised"] is False


def test_fix_failed_bug_real_but_fix_bad(isolated_state):
    """Original raises and the 'fix' still raises → fix_failed."""
    finding = {
        "finding_id": "f_badfix",
        "repro_call": "print(divide(1, 0))",
        "fixed_code": "def divide(a, b):\n    return a / b",   # unchanged — still bad
    }
    original = "def divide(a, b):\n    return a / b"
    rec = validation_lab.validate_finding(finding, original, enable_feedback=False)
    assert rec["verdict"] == "fix_failed"
    assert rec["original_exec"]["raised"] is True
    assert rec["fixed_exec"]["raised"] is True


def test_inconclusive_missing_repro_call(isolated_state):
    """No repro_call → cannot run → inconclusive, no crash."""
    finding = {"finding_id": "f_norepro", "repro_call": "", "fixed_code": "def f(): pass"}
    rec = validation_lab.validate_finding(finding, "def f(): pass", enable_feedback=False)
    assert rec["verdict"] == "inconclusive"
    assert rec["original_exec"] is None


def test_unsupported_language(isolated_state):
    finding = {
        "finding_id": "f_js",
        "language": "javascript",
        "repro_call": "f()",
        "fixed_code": "function f() {}",
    }
    rec = validation_lab.validate_finding(finding, "function f() {}", enable_feedback=False)
    assert rec["verdict"] == "inconclusive"
    assert "nieobsługiwany" in rec["rationale"]


def test_timeout_is_inconclusive(isolated_state):
    """An infinite loop in the original should time out → inconclusive."""
    finding = {
        "finding_id": "f_hang",
        "repro_call": "loop_forever()",
        "fixed_code": "def loop_forever():\n    return None",
    }
    original = "def loop_forever():\n    while True:\n        pass"
    rec = validation_lab.validate_finding(finding, original, enable_feedback=False, timeout=2.0)
    assert rec["verdict"] == "inconclusive"
    assert rec["original_exec"]["timed_out"] is True


# ── State persistence ────────────────────────────────────────────────────────

def test_record_persisted(isolated_state):
    finding = {
        "finding_id": "f_persist",
        "repro_call": "print(divide(1, 0))",
        "fixed_code": "def divide(a, b):\n    return a / b if b else 0",
    }
    validation_lab.validate_finding(finding, "def divide(a, b):\n    return a / b", enable_feedback=False)
    data = json.loads(Path(isolated_state).read_text(encoding="utf-8"))
    assert len(data["records"]) == 1
    assert data["records"][0]["finding_id"] == "f_persist"


def test_list_and_status(isolated_state):
    for i in range(3):
        validation_lab.validate_finding(
            {"finding_id": f"f{i}", "repro_call": "print(add_one(5))",
             "fixed_code": "def add_one(x):\n    return x + 1"},
            "def add_one(x):\n    return x + 1",
            enable_feedback=False,
        )
    listed = validation_lab.list_validations()
    assert len(listed) == 3
    assert listed[0]["finding_id"] == "f2"   # newest first
    status = validation_lab.validation_status()
    assert status["total"] == 3
    assert status["by_verdict"].get("unreproducible") == 3


# ── Sandbox isolation ────────────────────────────────────────────────────────

def test_sandbox_blocks_network_when_available(isolated_state):
    """If sandbox-exec is present, network egress must be denied at OS level."""
    if not validation_lab._sandbox_available():
        pytest.skip("sandbox-exec not available on this platform")
    net_code = (
        "import socket\n"
        "socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
        "print('NETWORK_OK')\n"
    )
    result = validation_lab._run_sandboxed(net_code, timeout=8.0)
    assert result["network_isolated"] is True
    assert result["raised"] is True            # connection blocked → non-zero exit
    assert "NETWORK_OK" not in result["stdout"]


def test_feedback_disabled_leaves_no_trace(isolated_state):
    finding = {
        "finding_id": "f_nofb",
        "repro_call": "print(add_one(5))",
        "fixed_code": "def add_one(x):\n    return x + 1",
    }
    rec = validation_lab.validate_finding(finding, "def add_one(x):\n    return x + 1", enable_feedback=False)
    assert rec["feedback"] is None
