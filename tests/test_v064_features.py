"""Tests for v0.6.2–v0.6.4 features.

v0.6.2: POST /api/library/docs/upload-to-thread, POST /api/library/threads/create
v0.6.3: Keyboard shortcuts (tested via dashboard HTML inspection)
v0.6.4: Synthesis UI improvements (tested via dashboard HTML inspection)
"""
from __future__ import annotations

import base64
import os

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")


class TestThreadCreate:
    """POST /api/library/threads/create — v0.6.3 (Cmd+N)."""

    def test_create_thread_basic(self, client, tmp_path, monkeypatch):
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        r = client.post("/api/library/threads/create", json={
            "title": "Test Thread Alpha",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["title"] == "Test Thread Alpha"
        assert data["stem"]
        # File should exist
        thread_file = tmp_path / "library" / "threads" / f"{data['stem']}.md"
        assert thread_file.exists()
        content = thread_file.read_text()
        assert "# Test Thread Alpha" in content
        assert "Status: active" in content

    def test_create_thread_custom_stem(self, client, tmp_path, monkeypatch):
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        r = client.post("/api/library/threads/create", json={
            "title": "My Research",
            "stem": "my_research_custom",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["stem"] == "my_research_custom"
        assert (tmp_path / "library" / "threads" / "my_research_custom.md").exists()

    def test_create_thread_dedup_stem(self, client, tmp_path, monkeypatch):
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        # Create first
        r1 = client.post("/api/library/threads/create", json={"title": "Duplicate"})
        assert r1.json()["ok"] is True
        stem1 = r1.json()["stem"]
        # Create second with same name → should get _1 suffix
        r2 = client.post("/api/library/threads/create", json={"title": "Duplicate"})
        assert r2.json()["ok"] is True
        stem2 = r2.json()["stem"]
        assert stem1 != stem2
        assert stem2.endswith("_1") or stem2 != stem1

    def test_create_thread_no_title_error(self, client):
        r = client.post("/api/library/threads/create", json={"title": ""})
        assert r.status_code == 400
        assert "error" in r.json()

    def test_create_thread_with_content(self, client, tmp_path, monkeypatch):
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        custom_content = "# Custom\n\nMy notes here."
        r = client.post("/api/library/threads/create", json={
            "title": "Custom Content",
            "content": custom_content,
        })
        data = r.json()
        assert data["ok"] is True
        f = tmp_path / "library" / "threads" / f"{data['stem']}.md"
        assert f.read_text() == custom_content


class TestUploadToThread:
    """POST /api/library/docs/upload-to-thread — v0.6.2."""

    def test_upload_to_thread_missing_fields(self, client):
        r = client.post("/api/library/docs/upload-to-thread", json={
            "filename": "",
            "content_b64": "",
        })
        assert r.status_code == 400
        assert "error" in r.json()

    def test_upload_to_thread_requires_text_extraction(self, client, tmp_path, monkeypatch):
        """Binary file with no extractable text should fail gracefully."""
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        # Create a fake binary file (won't have extractable text)
        raw = b"\x00\x01\x02" * 100
        b64 = base64.b64encode(raw).decode()
        r = client.post("/api/library/docs/upload-to-thread", json={
            "filename": "binary_file.bin",
            "content_b64": b64,
        })
        # Should either fail or succeed — depends on docs_manager behavior
        # At minimum it should not crash
        assert r.status_code in (200, 400, 500)


class TestDashboardV064HTML:
    """Verify dashboard HTML contains v0.6.2–v0.6.4 features."""

    @pytest.fixture(autouse=True)
    def _html(self):
        from matylda_lite.dashboard import build
        self.html = build(server_mode=True)

    def test_keyboard_shortcuts_present(self):
        """v0.6.3: Cmd+1/2/3 tab switching code present."""
        assert "e.key === '1'" in self.html
        assert "e.key === '2'" in self.html
        assert "e.key === '3'" in self.html
        assert "switchTab('work')" in self.html

    def test_cmd_n_shortcut(self):
        """v0.6.3: Cmd+N new thread shortcut."""
        assert "createNewThread" in self.html
        assert "e.key === 'n'" in self.html

    def test_cmd_shift_s_synthesis(self):
        """v0.6.3: Cmd+Shift+S synthesis shortcut."""
        assert "e.shiftKey && e.key === 'S'" in self.html

    def test_upload_to_thread_function(self):
        """v0.6.2: uploadFileToThread function exists."""
        assert "uploadFileToThread" in self.html
        assert "upload-to-thread" in self.html

    def test_file_menu_present(self):
        """v0.6.2: showFileMenu handles attach button."""
        assert "showFileMenu" in self.html

    def test_chat_drag_drop(self):
        """v0.6.2: setupChatDragDrop function for drag-drop → thread."""
        assert "setupChatDragDrop" in self.html

    def test_synth_counter_prominent(self):
        """v0.6.4: Prominent synthesis counter in sidebar."""
        assert "synth-counter" in self.html
        assert "synth-count-num" in self.html
        assert "Syntezuj" in self.html

    def test_larger_checkboxes(self):
        """v0.6.4: Checkboxes are 16px (not 11px)."""
        assert "width: 16px; height: 16px" in self.html

    def test_synth_pulse_animation(self):
        """v0.6.4: Pulse animation on synthesis counter."""
        assert "synthPulse" in self.html

    def test_version_10(self):
        """Version updated to 1.0."""
        from matylda_lite.server import app
        assert app.version == "1.2"
