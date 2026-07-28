"""Tests for v1.0 — Thread append, set-status, freeze/thaw UI, draft persistence."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")

_SAMPLE_THREAD = """\
# Quantum Research

## Metadata
- Domain: Physics
- Status: active
- Last updated: 2024-01-01

---

## Notatki

Some initial notes here.
"""


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def thread_workspace(tmp_path, monkeypatch):
    """Create a temp workspace with one thread file."""
    from matylda_lite import config
    import matylda_lite.library_manager as lm

    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(lm, "ROOT", tmp_path)
    monkeypatch.setattr(lm, "_THREADS_DIR", tmp_path / "library" / "threads")
    monkeypatch.setattr(lm, "_THREADS_ARCHIVE_DIR", tmp_path / "library" / "threads" / "archive")

    threads_dir = tmp_path / "library" / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    (threads_dir / "archive").mkdir(exist_ok=True)

    (threads_dir / "quantum_research.md").write_text(_SAMPLE_THREAD)
    return tmp_path


# ── library_manager.append_to_thread ─────────────────────────────────────────

class TestAppendToThread:
    def test_append_adds_section(self, thread_workspace):
        from matylda_lite.library_manager import append_to_thread, read_thread
        result = append_to_thread("quantum_research", "Wynik AI", "Nowy wniosek badań.")
        assert result["ok"] is True
        assert result["section_added"] == "Wynik AI"
        content = read_thread("quantum_research")
        assert "## Wynik AI" in content
        assert "Nowy wniosek badań." in content

    def test_append_includes_datestamp(self, thread_workspace):
        from matylda_lite.library_manager import append_to_thread, read_thread
        import datetime
        append_to_thread("quantum_research", "Test", "Content.")
        content = read_thread("quantum_research")
        today = str(datetime.date.today())
        assert today in content

    def test_append_does_not_destroy_existing_content(self, thread_workspace):
        from matylda_lite.library_manager import append_to_thread, read_thread
        append_to_thread("quantum_research", "Sekcja 1", "Część pierwsza.")
        content = read_thread("quantum_research")
        assert "Some initial notes here." in content
        assert "Część pierwsza." in content

    def test_append_multiple_times(self, thread_workspace):
        from matylda_lite.library_manager import append_to_thread, read_thread
        append_to_thread("quantum_research", "Sekcja A", "Treść A.")
        append_to_thread("quantum_research", "Sekcja B", "Treść B.")
        content = read_thread("quantum_research")
        assert "Treść A." in content
        assert "Treść B." in content

    def test_append_returns_updated_at(self, thread_workspace):
        from matylda_lite.library_manager import append_to_thread
        import datetime
        result = append_to_thread("quantum_research", "Test", "Content.")
        assert result["updated_at"] == str(datetime.date.today())

    def test_append_nonexistent_raises(self, thread_workspace):
        from matylda_lite.library_manager import append_to_thread
        with pytest.raises(FileNotFoundError):
            append_to_thread("does_not_exist", "Title", "Content")

    def test_append_updates_last_updated(self, thread_workspace):
        from matylda_lite.library_manager import append_to_thread, read_thread
        import datetime
        append_to_thread("quantum_research", "Update", "Content.")
        content = read_thread("quantum_research")
        today = str(datetime.date.today())
        assert today in content  # last_updated should be updated in metadata


# ── library_manager.set_thread_status ────────────────────────────────────────

class TestSetThreadStatus:
    def test_set_status_active_to_frozen(self, thread_workspace):
        from matylda_lite.library_manager import set_thread_status, read_thread
        ok = set_thread_status("quantum_research", "frozen")
        assert ok is True
        content = read_thread("quantum_research")
        assert "frozen" in content.lower()

    def test_set_status_frozen_to_active(self, thread_workspace):
        from matylda_lite.library_manager import set_thread_status, read_thread
        set_thread_status("quantum_research", "frozen")
        set_thread_status("quantum_research", "active")
        content = read_thread("quantum_research")
        # Should say active, not frozen
        import re
        status_match = re.search(r"- Status:\s*(\S+)", content, re.IGNORECASE)
        assert status_match is not None
        assert status_match.group(1).lower() == "active"

    def test_set_status_to_library(self, thread_workspace):
        from matylda_lite.library_manager import set_thread_status
        ok = set_thread_status("quantum_research", "library")
        assert ok is True

    def test_set_status_to_canonical(self, thread_workspace):
        from matylda_lite.library_manager import set_thread_status
        ok = set_thread_status("quantum_research", "canonical")
        assert ok is True

    def test_invalid_status_raises(self, thread_workspace):
        from matylda_lite.library_manager import set_thread_status
        with pytest.raises(ValueError, match="Nieprawidłowy status"):
            set_thread_status("quantum_research", "invalid_status")

    def test_nonexistent_thread_returns_false(self, thread_workspace):
        from matylda_lite.library_manager import set_thread_status
        result = set_thread_status("does_not_exist", "frozen")
        assert result is False

    def test_set_status_idempotent(self, thread_workspace):
        from matylda_lite.library_manager import set_thread_status
        # Setting same status twice should not error
        set_thread_status("quantum_research", "frozen")
        ok = set_thread_status("quantum_research", "frozen")
        assert ok is True


# ── HTTP: /api/library/threads/{stem}/append ─────────────────────────────────

class TestThreadAppendEndpoint:
    def test_append_200(self, client, thread_workspace):
        r = client.post("/api/library/threads/quantum_research/append", json={
            "section_title": "Wynik testu",
            "content": "To jest treść testowa.",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["section_added"] == "Wynik testu"

    def test_append_empty_content_400(self, client):
        r = client.post("/api/library/threads/some_thread/append", json={
            "section_title": "X",
            "content": "",
        })
        assert r.status_code == 400
        assert "error" in r.json()

    def test_append_no_content_key_400(self, client):
        r = client.post("/api/library/threads/some_thread/append", json={
            "section_title": "X",
        })
        assert r.status_code == 400

    def test_append_nonexistent_thread_404(self, client, thread_workspace):
        r = client.post("/api/library/threads/nonexistent_xyz/append", json={
            "section_title": "Test",
            "content": "Content here.",
        })
        assert r.status_code == 404

    def test_append_default_section_title(self, client, thread_workspace):
        r = client.post("/api/library/threads/quantum_research/append", json={
            "content": "Some content without title.",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["section_added"] == "Wynik AI"  # default title

    def test_append_content_persists(self, client, thread_workspace):
        client.post("/api/library/threads/quantum_research/append", json={
            "section_title": "Sekcja HTTP",
            "content": "Treść przez HTTP.",
        })
        # Verify by reading the file directly
        thread_file = thread_workspace / "library" / "threads" / "quantum_research.md"
        content = thread_file.read_text()
        assert "Sekcja HTTP" in content
        assert "Treść przez HTTP." in content


# ── HTTP: /api/library/threads/{stem}/set-status ─────────────────────────────

class TestThreadSetStatusEndpoint:
    def test_set_status_200(self, client, thread_workspace):
        r = client.post("/api/library/threads/quantum_research/set-status", json={
            "status": "frozen",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["status"] == "frozen"
        assert data["stem"] == "quantum_research"

    def test_set_status_no_body_400(self, client):
        r = client.post("/api/library/threads/some/set-status", json={})
        assert r.status_code == 400

    def test_set_status_invalid_400(self, client, thread_workspace):
        r = client.post("/api/library/threads/quantum_research/set-status", json={
            "status": "bogus_status",
        })
        assert r.status_code == 400
        assert "error" in r.json()

    def test_set_status_nonexistent_404(self, client, thread_workspace):
        r = client.post("/api/library/threads/nonexistent_xyz/set-status", json={
            "status": "frozen",
        })
        assert r.status_code == 404

    def test_set_status_roundtrip(self, client, thread_workspace):
        # freeze then thaw
        r1 = client.post("/api/library/threads/quantum_research/set-status", json={"status": "frozen"})
        assert r1.json()["ok"] is True
        r2 = client.post("/api/library/threads/quantum_research/set-status", json={"status": "active"})
        assert r2.json()["ok"] is True
        assert r2.json()["status"] == "active"

    def test_all_valid_statuses(self, client, thread_workspace):
        for status in ("active", "frozen", "library", "canonical"):
            r = client.post("/api/library/threads/quantum_research/set-status",
                            json={"status": status})
            assert r.status_code == 200, f"Failed for status: {status}"
            assert r.json()["ok"] is True


# ── Dashboard HTML v1.0 ───────────────────────────────────────────────────────

class TestDashboardV10HTML:
    @pytest.fixture(autouse=True)
    def _html(self):
        from matylda_lite.dashboard import build
        self.html = build(server_mode=True)

    def test_version_10(self):
        from matylda_lite.server import app
        assert app.version == "1.2"

    def test_append_to_thread_js(self):
        """v1.0: appendToThread function present."""
        assert "appendToThread" in self.html
        assert "/append" in self.html

    def test_toggle_thread_status_js(self):
        """v1.0: toggleThreadStatus function present."""
        assert "toggleThreadStatus" in self.html
        assert "/set-status" in self.html

    def test_freeze_button_in_thread_item(self):
        """v1.0: freeze/thaw toggle button in thread items."""
        assert "toggleThreadStatus" in self.html
        # Both frozen and active states
        assert "Zamroź wątek" in self.html
        assert "Odblokuj wątek" in self.html

    def test_frozen_ctx_badge(self):
        """v1.0: frozen badge shown in context bar."""
        assert "thread-ctx-frozen" in self.html
        assert "zamrożony" in self.html

    def test_append_btn_css(self):
        """v1.0: append button CSS present."""
        assert "append-btn" in self.html

    def test_draft_persistence_js(self):
        """v1.0: localStorage draft persistence."""
        assert "matylda-chat-draft" in self.html
        assert "localStorage.setItem" in self.html
        assert "localStorage.removeItem" in self.html
        assert "localStorage.getItem" in self.html

    def test_do_watku_button(self):
        """v1.0: 'Do wątku' button label present."""
        assert "Do wątku" in self.html

    def test_frozen_status_dot_in_thread_item(self):
        """v1.0: frozen status dot referenced in threadItemHtml."""
        assert "frozen" in self.html  # dot class

    def test_frozen_thread_section_label(self):
        """v1.0: Zamrożone section in sidebar."""
        assert "Zamrożone" in self.html
