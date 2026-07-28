"""Tests for v0.6 native app window module."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


class TestHealthCheck:
    def test_health_check_returns_false_when_no_server(self):
        from matylda_lite.app.window import _health_check
        # Port 19999 should have nothing running
        result = _health_check(port=19999)
        assert result is False

    def test_wait_for_server_returns_false_on_timeout(self):
        from matylda_lite.app.window import _wait_for_server
        # Very short timeout, no server on port 19998
        result = _wait_for_server(port=19998, timeout=0.1)
        assert result is False

    def test_wait_for_server_returns_true_when_server_up(self):
        """Mock the health check to simulate a running server."""
        from matylda_lite.app import window as win_mod
        call_count = [0]
        original = win_mod._health_check

        def mock_check(port=7474):
            call_count[0] += 1
            return call_count[0] >= 2  # fails first, succeeds second

        win_mod._health_check = mock_check
        try:
            result = win_mod._wait_for_server(port=7474, timeout=2.0)
            assert result is True
            assert call_count[0] >= 2
        finally:
            win_mod._health_check = original

    def test_health_check_false_on_connection_refused(self):
        from matylda_lite.app.window import _health_check
        assert _health_check(port=1) is False  # port 1 is privileged/closed

    def test_select_server_port_skips_an_incompatible_server(self, monkeypatch):
        from matylda_lite.app import window as win_mod

        monkeypatch.setattr(win_mod, "_server_version", lambda port: "1.0" if port == 7474 else None)
        monkeypatch.setattr(win_mod, "_port_is_available", lambda port: port == 7475)

        assert win_mod._select_server_port(7474) == 7475


class TestWindowModuleImport:
    def test_module_imports_ok(self):
        from matylda_lite.app import window
        assert hasattr(window, "run_window")
        assert hasattr(window, "_health_check")
        assert hasattr(window, "_wait_for_server")
        assert hasattr(window, "_start_server_thread")

    def test_port_constant(self):
        from matylda_lite.app.window import PORT
        assert PORT == 7474

    def test_ready_timeout_positive(self):
        from matylda_lite.app.window import _READY_TIMEOUT
        assert _READY_TIMEOUT > 0


class TestRunWindowImportError:
    def test_run_window_raises_systemexit_without_pywebview(self):
        """If webview isn't importable, run_window raises SystemExit."""
        import sys
        import importlib
        from matylda_lite.app import window as win_mod

        # Temporarily hide webview from imports
        real_webview = sys.modules.get("webview")
        sys.modules["webview"] = None  # makes import fail with ImportError

        try:
            import pytest
            with pytest.raises(SystemExit):
                win_mod.run_window(port=19997, start_server=False)
        finally:
            if real_webview is not None:
                sys.modules["webview"] = real_webview
            else:
                sys.modules.pop("webview", None)


class TestStartServerThread:
    def test_start_server_thread_no_error_when_server_running(self):
        """_start_server_thread should be a no-op if server already up."""
        from matylda_lite.app import window as win_mod
        original = win_mod._server_version
        win_mod._server_version = lambda port=7474: win_mod.SERVER_VERSION
        try:
            assert win_mod._start_server_thread(port=7474) == 7474
        finally:
            win_mod._server_version = original


class TestRunPyArgparse:
    """Test that run.py --window flag is parseable."""

    def test_run_py_has_window_flag(self):
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "run.py", "--help"],
            capture_output=True, text=True,
            cwd=ROOT,
        )
        assert "--window" in result.stdout

    def test_app_bundle_exists(self):
        bundle = ROOT / "Matylda Lite.app"
        assert bundle.exists(), "Matylda Lite.app nie istnieje"
        assert (bundle / "Contents" / "Info.plist").exists()
        assert (bundle / "Contents" / "MacOS" / "MatyldaLite").exists()

    def test_app_bundle_executable(self):
        import os
        launcher = ROOT / "Matylda Lite.app" / "Contents" / "MacOS" / "MatyldaLite"
        assert os.access(launcher, os.X_OK), "MatyldaLite nie jest wykonywalny"
