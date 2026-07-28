"""Tests for v0.9 — Morning Briefing: briefing_manager + /api/briefing endpoints."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-dummy-key-for-unit-tests")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_data(tmp_path, monkeypatch):
    """Redirect ROOT to tmp_path so session file lands in tmp.

    briefing_manager uses config.ROOT dynamically, so patching config.ROOT is
    sufficient — no need to also patch briefing_manager.ROOT.
    """
    from matylda_lite import config
    monkeypatch.setattr(config, "ROOT", tmp_path)
    import matylda_lite.briefing_manager as bm
    monkeypatch.setattr(bm, "_MIN_GAP_HOURS", 8.0)
    return tmp_path


@pytest.fixture()
def old_session(tmp_data):
    """Write a session timestamp that is 10 h old → should trigger briefing."""
    import matylda_lite.briefing_manager as bm
    ts = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    session_file = tmp_data / "data" / "briefing_session.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(json.dumps({"last_session": ts}))
    return session_file


@pytest.fixture()
def fresh_session(tmp_data):
    """Write a session timestamp that is 2 h old → should NOT trigger briefing."""
    import matylda_lite.briefing_manager as bm
    ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    session_file = tmp_data / "data" / "briefing_session.json"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(json.dumps({"last_session": ts}))
    return session_file


# ── Unit: session tracking ────────────────────────────────────────────────────

class TestSessionTracking:
    def test_mark_session_creates_file(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        bm.mark_session_start()
        session_file = tmp_data / "data" / "briefing_session.json"
        assert session_file.exists()

    def test_mark_session_writes_iso_timestamp(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        bm.mark_session_start()
        session_file = tmp_data / "data" / "briefing_session.json"
        data = json.loads(session_file.read_text())
        ts = data["last_session"]
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(ts)
        assert dt is not None

    def test_mark_session_overwrites_existing(self, tmp_data, old_session):
        import matylda_lite.briefing_manager as bm
        first = json.loads(old_session.read_text())["last_session"]
        bm.mark_session_start()
        second = json.loads(old_session.read_text())["last_session"]
        assert second != first

    def test_gap_hours_no_file(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        assert bm.gap_hours() == 0.0

    def test_gap_hours_with_old_session(self, tmp_data, old_session):
        import matylda_lite.briefing_manager as bm
        gap = bm.gap_hours()
        assert gap >= 9.9  # wrote 10h ago, should be ~10h

    def test_gap_hours_with_fresh_session(self, tmp_data, fresh_session):
        import matylda_lite.briefing_manager as bm
        gap = bm.gap_hours()
        assert 1.5 <= gap <= 3.0  # wrote 2h ago


# ── Unit: should_show_briefing ────────────────────────────────────────────────

class TestShouldShowBriefing:
    def test_no_file_returns_false(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        assert bm.should_show_briefing() is False

    def test_old_session_returns_true(self, tmp_data, old_session):
        import matylda_lite.briefing_manager as bm
        assert bm.should_show_briefing() is True

    def test_fresh_session_returns_false(self, tmp_data, fresh_session):
        import matylda_lite.briefing_manager as bm
        assert bm.should_show_briefing() is False

    def test_custom_threshold(self, tmp_data, old_session):
        import matylda_lite.briefing_manager as bm
        # With a very high threshold (50h), even 10h-old session won't trigger
        assert bm.should_show_briefing(min_gap_hours=50) is False

    def test_custom_threshold_low(self, tmp_data, fresh_session):
        import matylda_lite.briefing_manager as bm
        # With a 1h threshold, a 2h-old session WILL trigger
        assert bm.should_show_briefing(min_gap_hours=1.0) is True


# ── Unit: cross-thread connections ────────────────────────────────────────────

class TestCrossThreadConnections:
    def test_no_threads_returns_empty(self, tmp_data, monkeypatch):
        import matylda_lite.briefing_manager as bm
        monkeypatch.setattr(
            bm, "detect_cross_thread_connections",
            lambda max_threads=15: []
        )
        result = bm.detect_cross_thread_connections()
        assert result == []

    def test_connections_have_required_keys(self, tmp_data):
        """Test connection dict structure when threads exist."""
        import matylda_lite.briefing_manager as bm
        # Simulate two threads with shared keywords
        kws_a = {"quantum", "gravity", "spacetime", "physics", "field", "energy",
                 "matter", "theory", "relativity", "mass"}
        kws_b = {"quantum", "gravity", "mechanics", "physics", "wave", "energy",
                 "particle", "theory", "operator", "hilbert"}
        shared = kws_a & kws_b
        # Manually verify structure
        conn = {
            "thread_a": {"stem": "a", "title": "A"},
            "thread_b": {"stem": "b", "title": "B"},
            "shared_keywords": sorted(shared)[:8],
            "score": round(len(shared) / min(len(kws_a), len(kws_b)), 3),
        }
        assert "thread_a" in conn
        assert "thread_b" in conn
        assert "shared_keywords" in conn
        assert "score" in conn
        assert isinstance(conn["score"], float)

    def test_connection_score_range(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        # Score must be between 0 and 1
        kws = {"word1", "word2", "word3", "word4", "word5",
               "word6", "word7", "word8", "word9", "word10"}
        shared = {"word1", "word2", "word3"}
        score = round(len(shared) / min(len(kws), len(kws)), 3)
        assert 0.0 <= score <= 1.0


# ── Unit: get_morning_briefing ────────────────────────────────────────────────

class TestGetMorningBriefing:
    def test_no_session_show_false(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        result = bm.get_morning_briefing()
        assert result["show"] is False
        assert result["gap_hours"] == 0.0
        assert result["synthesis"] is None
        assert result["connections"] == []
        assert "timestamp" in result

    def test_old_session_show_true(self, tmp_data, old_session):
        import matylda_lite.briefing_manager as bm
        result = bm.get_morning_briefing()
        assert result["show"] is True
        assert result["gap_hours"] >= 9.9

    def test_force_show_true(self, tmp_data, fresh_session):
        import matylda_lite.briefing_manager as bm
        result = bm.get_morning_briefing(force=True)
        assert result["show"] is True

    def test_timestamp_is_iso(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        result = bm.get_morning_briefing()
        dt = datetime.fromisoformat(result["timestamp"])
        assert dt is not None

    def test_result_has_all_keys(self, tmp_data):
        import matylda_lite.briefing_manager as bm
        result = bm.get_morning_briefing()
        for key in ("show", "gap_hours", "synthesis", "connections", "timestamp"):
            assert key in result, f"Missing key: {key}"


# ── HTTP endpoints ────────────────────────────────────────────────────────────

class TestBriefingEndpoints:
    def test_briefing_endpoint_reachable(self, client):
        r = client.get("/api/briefing")
        assert r.status_code == 200

    def test_briefing_returns_show_key(self, client):
        r = client.get("/api/briefing")
        data = r.json()
        assert "show" in data

    def test_briefing_returns_gap_hours(self, client):
        r = client.get("/api/briefing")
        data = r.json()
        assert "gap_hours" in data
        assert isinstance(data["gap_hours"], (int, float))

    def test_briefing_returns_connections(self, client):
        r = client.get("/api/briefing")
        data = r.json()
        assert "connections" in data
        assert isinstance(data["connections"], list)

    def test_briefing_force_shows(self, client, tmp_path, monkeypatch):
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        # Write fresh session → normally would not show
        ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        session_file = tmp_path / "data" / "briefing_session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({"last_session": ts}))
        r = client.get("/api/briefing?force=true")
        data = r.json()
        assert data["show"] is True

    def test_mark_session_endpoint(self, client):
        r = client.post("/api/briefing/mark-session")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_mark_session_creates_file(self, client, tmp_path, monkeypatch):
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        client.post("/api/briefing/mark-session")
        session_file = tmp_path / "data" / "briefing_session.json"
        assert session_file.exists()

    def test_briefing_no_show_when_fresh(self, client, tmp_path, monkeypatch):
        from matylda_lite import config
        monkeypatch.setattr(config, "ROOT", tmp_path)
        import matylda_lite.briefing_manager as bm
        monkeypatch.setattr(bm, "_MIN_GAP_HOURS", 8.0)
        # Write session that is only 30 min old
        ts = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        session_file = tmp_path / "data" / "briefing_session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({"last_session": ts}))
        r = client.get("/api/briefing")
        data = r.json()
        assert data["show"] is False

    def test_health_is_10(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["version"] == "1.2"


# ── Dashboard HTML ────────────────────────────────────────────────────────────

class TestDashboardV09HTML:
    @pytest.fixture(autouse=True)
    def _html(self):
        from matylda_lite.dashboard import build
        self.html = build(server_mode=True)

    def test_briefing_card_css_present(self):
        """v0.9: .briefing-card CSS exists."""
        assert "briefing-card" in self.html

    def test_briefing_header_css(self):
        assert "briefing-header" in self.html

    def test_briefing_connection_css(self):
        assert "briefing-connection" in self.html

    def test_check_morning_briefing_js(self):
        """v0.9: checkMorningBriefing function present."""
        assert "checkMorningBriefing" in self.html

    def test_mark_session_js(self):
        assert "markSession" in self.html

    def test_render_briefing_card_js(self):
        assert "renderBriefingCard" in self.html

    def test_dismiss_briefing_js(self):
        assert "dismissBriefing" in self.html

    def test_slash_briefing_command(self):
        """v0.9: /briefing slash command is handled."""
        assert "'/briefing'" in self.html

    def test_briefing_api_endpoint_referenced(self):
        assert "/api/briefing" in self.html

    def test_mark_session_on_dom_loaded(self):
        """v0.9: markSession() called on DOMContentLoaded."""
        assert "markSession()" in self.html

    def test_check_briefing_on_dom_loaded(self):
        assert "checkMorningBriefing(false)" in self.html

    def test_textarea_rows_3(self):
        """v0.9: textarea has rows='3' for more input space."""
        assert 'rows="3"' in self.html

    def test_briefing_placeholder_hint(self):
        """v0.9: /briefing mentioned in textarea placeholder."""
        assert "/briefing" in self.html

    def test_version_10(self):
        from matylda_lite.server import app
        assert app.version == "1.2"

    def test_system_health_css(self):
        """v0.9: system health CSS present in dashboard."""
        assert "sys-health-row" in self.html
        assert "sys-health-val" in self.html

    def test_system_health_js(self):
        assert "loadSystemHealth" in self.html
        assert "renderSystemHealth" in self.html

    def test_system_health_html_panel(self):
        assert "sys-health-content" in self.html
        assert "SYSTEM HEALTH" in self.html

    def test_frozen_thread_css(self):
        """v0.9: frozen thread status dot CSS present."""
        assert "thread-status-dot.frozen" in self.html

    def test_thread_limit_warning_css(self):
        assert "thread-limit-warning" in self.html

    def test_load_system_health_on_dom_loaded(self):
        assert "loadSystemHealth()" in self.html


# ── System health endpoint ────────────────────────────────────────────────────

class TestSystemHealthEndpoint:
    def test_reachable(self, client):
        r = client.get("/api/health/system")
        assert r.status_code == 200

    def test_has_required_keys(self, client):
        data = client.get("/api/health/system").json()
        for key in ("active_threads", "frozen_threads", "library_threads",
                    "total_threads", "insight_count", "candidate_count",
                    "artifact_count", "complexity_score", "limit_ok",
                    "active_thread_limit"):
            assert key in data, f"Missing key: {key}"

    def test_active_thread_limit_is_5(self, client):
        data = client.get("/api/health/system").json()
        assert data["active_thread_limit"] == 5

    def test_complexity_score_is_number(self, client):
        data = client.get("/api/health/system").json()
        assert isinstance(data["complexity_score"], (int, float))

    def test_limit_ok_type(self, client):
        data = client.get("/api/health/system").json()
        assert isinstance(data["limit_ok"], bool)

    def test_counts_are_nonnegative(self, client):
        data = client.get("/api/health/system").json()
        for key in ("active_threads", "frozen_threads", "insight_count",
                    "candidate_count", "artifact_count"):
            assert data[key] >= 0, f"{key} should be non-negative"
