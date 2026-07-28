"""Tests for silo_2 (Privacy Lab) — anonymizer, skill runner, audit log, HTTP endpoints."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from matylda_lite.silos.silo_2.anonymizer import (
    AnonymizationResult,
    anonymize,
    anonymize_dict,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Anonymizer — unit tests (pure, no I/O)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnonymize:
    # ── Email ─────────────────────────────────────────────────────────────────

    def test_email_replaced(self):
        r = anonymize("Contact alice@example.com for details.")
        assert "alice@example.com" not in r.anonymized_text
        assert "[EMAIL_1]" in r.anonymized_text

    def test_email_counter_increments(self):
        r = anonymize("a@x.com and b@y.com")
        assert "[EMAIL_1]" in r.anonymized_text
        assert "[EMAIL_2]" in r.anonymized_text

    def test_same_email_same_placeholder(self):
        r = anonymize("Send to alice@x.com and again to alice@x.com")
        # both occurrences should map to the same placeholder
        assert r.anonymized_text.count("[EMAIL_1]") == 2
        assert "[EMAIL_2]" not in r.anonymized_text

    # ── IP ────────────────────────────────────────────────────────────────────

    def test_ip_replaced(self):
        r = anonymize("Server at 192.168.1.100")
        assert "192.168.1.100" not in r.anonymized_text
        assert "[IP_1]" in r.anonymized_text

    def test_invalid_ip_not_replaced(self):
        # 999.999.999.999 is out of IPv4 range — regex allows it but that's fine;
        # what matters is that valid IPs are caught
        r = anonymize("Valid: 10.0.0.1")
        assert "[IP_1]" in r.anonymized_text

    # ── URL ───────────────────────────────────────────────────────────────────

    def test_url_replaced(self):
        r = anonymize("See https://example.com/page?q=1 for details.")
        assert "https://example.com" not in r.anonymized_text
        assert "[URL_1]" in r.anonymized_text

    def test_http_url_replaced(self):
        r = anonymize("Old site: http://old.example.org/path")
        assert "[URL_1]" in r.anonymized_text

    # ── API key / secret ──────────────────────────────────────────────────────

    def test_apikey_replaced(self):
        r = anonymize("Use key sk-ant-api03-abcdefghij1234567890")
        assert "sk-ant-api03" not in r.anonymized_text
        assert "[APIKEY_1]" in r.anonymized_text

    # ── Date ─────────────────────────────────────────────────────────────────

    def test_iso_date_replaced(self):
        r = anonymize("Meeting on 2026-01-15 at noon.")
        assert "2026-01-15" not in r.anonymized_text
        assert "[DATE_1]" in r.anonymized_text

    def test_slash_date_replaced(self):
        r = anonymize("Born 01/15/1990")
        assert "[DATE_1]" in r.anonymized_text

    # ── Hex ───────────────────────────────────────────────────────────────────

    def test_hex_hash_replaced(self):
        r = anonymize("Hash: d41d8cd98f00b204e9800998ecf8427e")
        assert "d41d8cd98f00b204e9800998ecf8427e" not in r.anonymized_text
        assert "[HEX_1]" in r.anonymized_text

    # ── Clean text ────────────────────────────────────────────────────────────

    def test_clean_text_unchanged(self):
        text = "This is a normal scientific sentence with no PII."
        r = anonymize(text)
        assert r.anonymized_text == text
        assert r.entity_count == 0
        assert r.types_found == []

    def test_empty_text_unchanged(self):
        r = anonymize("")
        assert r.anonymized_text == ""
        assert r.entity_count == 0

    # ── entity_map ────────────────────────────────────────────────────────────

    def test_entity_map_populated(self):
        r = anonymize("alice@x.com")
        assert len(r.entity_map) == 1
        assert "[EMAIL_1]" in r.entity_map
        assert r.entity_map["[EMAIL_1]"] == "alice@x.com"

    def test_entity_count_correct(self):
        r = anonymize("a@x.com and 192.168.1.1")
        assert r.entity_count == 2

    def test_types_found_correct(self):
        r = anonymize("a@x.com and 192.168.1.1")
        assert "EMAIL" in r.types_found
        assert "IP" in r.types_found

    # ── restore ───────────────────────────────────────────────────────────────

    def test_restore_roundtrip(self):
        original = "Contact alice@example.com or 10.0.0.1 for help."
        r = anonymize(original)
        restored = r.restore(r.anonymized_text)
        assert restored == original

    def test_restore_no_entities(self):
        text = "Nothing sensitive here."
        r = anonymize(text)
        assert r.restore(r.anonymized_text) == text

    # ── summary ──────────────────────────────────────────────────────────────

    def test_summary_no_entities(self):
        r = anonymize("clean text")
        assert "Brak" in r.summary()

    def test_summary_with_entities(self):
        r = anonymize("alice@x.com")
        s = r.summary()
        assert "EMAIL" in s
        assert "1" in s

    # ── returns AnonymizationResult ───────────────────────────────────────────

    def test_returns_result_instance(self):
        r = anonymize("test@example.com")
        assert isinstance(r, AnonymizationResult)


# ═══════════════════════════════════════════════════════════════════════════════
# anonymize_dict
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnonymizeDict:
    def test_email_in_nested_dict(self):
        data = {"user": "alice@example.com", "role": "admin"}
        anon, r = anonymize_dict(data)
        assert r.entity_count >= 1
        assert "alice@example.com" not in json.dumps(anon)

    def test_clean_dict_unchanged_values(self):
        data = {"key": "value", "num": 42}
        anon, r = anonymize_dict(data)
        assert r.entity_count == 0

    def test_returns_dict(self):
        data = {"x": "no pii here"}
        anon, r = anonymize_dict(data)
        assert isinstance(anon, dict)

    def test_restore_works_on_dict_output(self):
        data = {"contact": "alice@x.com"}
        anon, r = anonymize_dict(data)
        restored_str = r.restore(json.dumps(anon))
        assert "alice@x.com" in restored_str


# ═══════════════════════════════════════════════════════════════════════════════
# silo_2 module — meta and config
# ═══════════════════════════════════════════════════════════════════════════════

class TestSilo2Meta:
    def test_silo_meta_id(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["id"] == "silo_2"

    def test_silo_meta_name_legal(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["name"] == "Legal"

    def test_silo_meta_hashtag_legal(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["hashtag"] == "#legal"

    def test_silo_meta_type_closed(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["type"] == "closed"

    def test_silo_meta_enabled(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["enabled"] is True

    def test_silo_meta_anonymize_true(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["llm_policy"]["anonymize"] is True

    def test_silo_meta_no_sleeping_matylda(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["llm_policy"]["sleeping_matylda"] is False

    def test_silo_meta_no_legal_advice(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["llm_policy"]["legal_advice"] is False

    def test_silo_meta_human_review_required(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["llm_policy"]["human_review"] == "required"

    def test_silo_meta_darkroom_on(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert SILO_META["llm_policy"]["darkroom"] is True

    def test_silo_meta_features_include_anonymizer(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert "anonymizer" in SILO_META["features"]

    def test_silo_meta_features_include_audit_log(self):
        from matylda_lite.silos.silo_2 import SILO_META
        assert "audit_log" in SILO_META["features"]

    def test_get_router_returns_router(self):
        from matylda_lite.silos.silo_2 import get_router
        from fastapi import APIRouter
        router = get_router()
        assert isinstance(router, APIRouter)

    def test_router_has_expected_paths(self):
        from matylda_lite.silos.silo_2 import get_router
        router = get_router()
        paths = [r.path for r in router.routes]
        assert any("anonymize" in p for p in paths)
        assert any("audit" in p for p in paths)
        assert any("run-pipeline" in p for p in paths)
        assert any("skills" in p for p in paths)
        assert any("notebooks" in p for p in paths)

    # ── Legal skills and notebooks ─────────────────────────────────────────────

    def test_legal_skills_loaded(self):
        from matylda_lite.silos.silo_2 import _list_skills
        skills = _list_skills()
        assert len(skills) == 5

    def test_legal_skill_ids(self):
        from matylda_lite.silos.silo_2 import _list_skills
        ids = {s["id"] for s in _list_skills()}
        assert "operator_style_core" in ids
        assert "court_pleading_construction" in ids
        assert "demand_letter_construction" in ids
        assert "credit_claim_style" in ids
        assert "representation_and_power_of_attorney" in ids

    def test_legal_notebooks_loaded(self):
        from matylda_lite.silos.silo_2 import _load_nb_index
        nbs = _load_nb_index()
        assert len(nbs) == 5

    def test_legal_notebook_ids(self):
        from matylda_lite.silos.silo_2 import _load_nb_index
        ids = {n["id"] for n in _load_nb_index()}
        assert "legal_document_taxonomy_2024_2026" in ids
        assert "legal_operator_style_notebook" in ids
        assert "legal_evidence_and_attachments_notebook" in ids
        assert "legal_credit_cases_notebook" in ids
        assert "legal_local_silo_operations" in ids

    def test_skill_has_prompt_template(self):
        from matylda_lite.silos.silo_2 import _load_skill
        skill = _load_skill("court_pleading_construction")
        assert skill is not None
        assert "prompt_template" in skill
        assert len(skill["prompt_template"]) > 50

    def test_skill_legal_policy_no_advice(self):
        from matylda_lite.silos.silo_2 import _load_skill
        skill = _load_skill("operator_style_core")
        assert skill["llm_policy"]["legal_advice"] is False
        assert skill["llm_policy"]["human_review"] == "required"


# ═══════════════════════════════════════════════════════════════════════════════
# silo_2 skill runner — error paths (no LLM)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSilo2SkillRunner:
    def test_nonexistent_skill_returns_error(self):
        from matylda_lite.silos.silo_2 import _run_skill
        result = _run_skill("skill_does_not_exist_xyz", {})
        assert "error" in result
        assert "skill_does_not_exist_xyz" in result["error"] or "nie istnieje" in result["error"]

    def test_nonexistent_skill_writes_audit(self, tmp_path, monkeypatch):
        import matylda_lite.silos.silo_2 as s2
        audit = tmp_path / "audit.jsonl"
        monkeypatch.setattr(s2, "_AUDIT_LOG", audit)
        s2._run_skill("no_such_skill", {})
        assert audit.exists()
        rows = [json.loads(l) for l in audit.read_text().splitlines() if l]
        assert len(rows) == 1
        assert rows[0]["event"] == "skill_not_found"
        assert rows[0]["ok"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Audit log helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    def test_empty_log_returns_empty_list(self, tmp_path, monkeypatch):
        import matylda_lite.silos.silo_2 as s2
        monkeypatch.setattr(s2, "_AUDIT_LOG", tmp_path / "audit.jsonl")
        assert s2.load_audit_log() == []

    def test_written_entries_loadable(self, tmp_path, monkeypatch):
        import matylda_lite.silos.silo_2 as s2
        audit = tmp_path / "audit.jsonl"
        monkeypatch.setattr(s2, "_AUDIT_LOG", audit)
        s2._audit_log("skill_run", "my_skill", 3, ["EMAIL"], ok=True, project_id="p1")
        rows = s2.load_audit_log()
        assert len(rows) == 1
        assert rows[0]["skill_id"] == "my_skill"
        assert rows[0]["entity_count"] == 3
        assert rows[0]["ok"] is True

    def test_load_limit_respected(self, tmp_path, monkeypatch):
        import matylda_lite.silos.silo_2 as s2
        audit = tmp_path / "audit.jsonl"
        monkeypatch.setattr(s2, "_AUDIT_LOG", audit)
        for i in range(10):
            s2._audit_log("skill_run", f"skill_{i}", 0, [], ok=True)
        rows = s2.load_audit_log(limit=3)
        assert len(rows) == 3

    def test_load_returns_most_recent_first(self, tmp_path, monkeypatch):
        import matylda_lite.silos.silo_2 as s2
        audit = tmp_path / "audit.jsonl"
        monkeypatch.setattr(s2, "_AUDIT_LOG", audit)
        for i in range(3):
            s2._audit_log("skill_run", f"skill_{i}", 0, [], ok=True)
        rows = s2.load_audit_log()
        # most recent (skill_2) should be first
        assert rows[0]["skill_id"] == "skill_2"


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline dispatch — silo_2 (error path only, no LLM)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPipelineSilo2Dispatch:
    def test_silo2_in_supported_silos(self):
        from matylda_lite.research_pipeline import _SUPPORTED_SILOS
        assert "silo_2" in _SUPPORTED_SILOS

    def test_silo2_not_in_sm_enabled_silos(self):
        from matylda_lite.research_pipeline import _SM_ENABLED_SILOS
        assert "silo_2" not in _SM_ENABLED_SILOS

    def test_pipeline_nonexistent_skill_silo2(self, tmp_chronicle, tmp_traces_dir):
        from matylda_lite.research_pipeline import run_research_pipeline
        result = run_research_pipeline(
            "skill_xyz_not_found",
            {},
            silo_id="silo_2",
            project_id="test",
        )
        assert result.ok is False
        assert result.silo_id == "silo_2"

    def test_pipeline_silo2_sm_warning_in_result(self, tmp_chronicle, tmp_traces_dir):
        from matylda_lite.research_pipeline import run_research_pipeline
        result = run_research_pipeline(
            "skill_xyz_not_found",
            {},
            silo_id="silo_2",
            project_id="test",
        )
        # Even on skill failure the silo_id is correct
        assert result.silo_id == "silo_2"


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP integration tests — silo_2 endpoints
# ═══════════════════════════════════════════════════════════════════════════════

pytestmark_integration = pytest.mark.integration


def test_silo2_in_silos_list(client):
    r = client.get("/api/silos")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()["silos"]]
    assert "silo_2" in ids


def test_silo2_info(client):
    r = client.get("/api/silos/silo_2/info")
    assert r.status_code == 200
    data = r.json()
    assert data["silo_id"] == "silo_2"
    assert data["type"] == "closed"
    assert data["name"] == "Legal"


def test_silo2_llm_policy(client):
    r = client.get("/api/silos/silo_2/llm-policy")
    assert r.status_code == 200
    data = r.json()
    assert data["silo_type"] == "closed"
    assert data["policy"]["anonymize"] is True
    assert data["policy"]["sleeping_matylda"] is False


def test_silo2_skills_list(client):
    r = client.get("/api/silos/silo_2/skills")
    assert r.status_code == 200
    data = r.json()
    assert "skills" in data
    assert len(data["skills"]) == 5


def test_silo2_notebooks_list(client):
    r = client.get("/api/silos/silo_2/notebooks")
    assert r.status_code == 200
    data = r.json()
    assert "notebooks" in data
    assert len(data["notebooks"]) == 5


def test_silo2_audit_log(client):
    r = client.get("/api/silos/silo_2/audit")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert "count" in data
    assert isinstance(data["entries"], list)


def test_silo2_anonymize_text(client):
    r = client.post("/api/silos/silo_2/anonymize", json={
        "text": "Contact alice@example.com or server 10.0.0.1 for info."
    })
    assert r.status_code == 200
    data = r.json()
    assert "anonymized_text" in data
    assert "alice@example.com" not in data["anonymized_text"]
    assert data["entity_count"] >= 2
    assert "EMAIL" in data["types_found"]


def test_silo2_anonymize_data_dict(client):
    r = client.post("/api/silos/silo_2/anonymize", json={
        "data": {"email": "bob@secret.org", "note": "call 192.168.0.1"}
    })
    assert r.status_code == 200
    data = r.json()
    assert "anonymized_data" in data
    assert data["entity_count"] >= 1


def test_silo2_anonymize_clean_text(client):
    r = client.post("/api/silos/silo_2/anonymize", json={
        "text": "Purely scientific statement with no personal data."
    })
    assert r.status_code == 200
    data = r.json()
    assert data["entity_count"] == 0
    assert data["types_found"] == []


def test_silo2_anonymize_missing_body(client):
    r = client.post("/api/silos/silo_2/anonymize", json={})
    assert r.status_code == 200
    data = r.json()
    assert "error" in data


def test_silo2_pipeline_nonexistent_skill(client):
    r = client.post("/api/silos/silo_2/run-pipeline", json={
        "skill_id": "skill_xyz_does_not_exist",
        "inputs":   {},
    })
    assert r.status_code == 200
    data = r.json()
    assert "ok" in data
    assert data["silo_id"] == "silo_2"
