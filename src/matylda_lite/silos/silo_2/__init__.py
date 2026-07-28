"""Silo 2 — Privacy Lab (zamknięty silos badawczy).

Typ: closed — wszystkie wejścia anonimizowane przed wysłaniem do LLM.

Różnice względem silo_1 (Science / open):
  ✗ Brak Sleeping Matylda (zbyt refleksyjne, może ujawnić wzorce)
  ✓ Anonimizacja PII przed każdym wywołaniem LLM
  ✓ Audit log każdego uruchomienia skilla
  ✓ DARKROOM obowiązkowy (zawsze aktywny)
  ✓ Model: claude-haiku-4-5 (szybszy, mniejszy ślad kontekstu)
  ✓ Hashtag labeling i Notebooks jak w silo_1

Konfiguracja: silos/silo_2/config.json (runtime).
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel


# ── Pydantic models ───────────────────────────────────────────────────────────

class _HashtagBody(BaseModel):
    hashtag: str

class _SkillRunBody(BaseModel):
    skill_id: str
    inputs: dict = {}

class _SkillCreateBody(BaseModel):
    id: str
    name: str
    description: str = ""
    prompt_template: str
    tags: list[str] = []

class _NotebookCreateBody(BaseModel):
    title: str
    context: str = ""
    tags: list[str] = []
    project_id: str = "lite"

class _NotebookUpdateBody(BaseModel):
    content: str | None = None
    title: str | None = None
    tags: list[str] | None = None
    body: str | None = None

class _PipelineRunBody(BaseModel):
    skill_id: str
    inputs: dict = {}
    project_id: str = "lite"
    title: str = ""


# ── Ścieżki ───────────────────────────────────────────────────────────────────

_ROOT       = Path(__file__).parent.parent.parent.parent.parent
_SILO_DATA  = _ROOT / "silos" / "silo_2"
_CONFIG     = _SILO_DATA / "config.json"
_SKILLS_DIR = _SILO_DATA / "skills"
_NB_DIR     = _SILO_DATA / "notebooks"
_AUDIT_LOG  = _SILO_DATA / "audit.jsonl"

for _d in [_SILO_DATA, _SKILLS_DIR, _NB_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ── Config ────────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG: dict = {
    "name": "Legal",
    "hashtag": "#legal",
    "type": "closed",
    "description": "Zamknięty silos prawny — pisma procesowe, wezwania, pełnomocnictwa. Anonimizacja PII przed LLM. Human review obowiązkowy.",
    "llm_policy": {
        "external_llm": True,
        "external_providers": ["anthropic"],
        "internal_llm": True,
        "anonymize": True,
        "sleeping_matylda": False,
        "darkroom": True,
        "legal_advice": False,
        "human_review": "required",
        "executor_policy": "manual_only",
    },
    "features": ["skills", "notebooks", "darkroom", "anonymizer", "audit_log"],
    "enabled": True,
    "version": "0.4b",
}


def _load_config() -> dict:
    if _CONFIG.exists():
        try:
            return json.loads(_CONFIG.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return _DEFAULT_CONFIG.copy()


def _save_config(cfg: dict) -> None:
    _CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ── SILO_META ─────────────────────────────────────────────────────────────────

def _make_meta() -> dict:
    cfg = _load_config()
    return {
        "id":          "silo_2",
        "name":        cfg.get("name", "Legal"),
        "hashtag":     cfg.get("hashtag", "#legal"),
        "type":        cfg.get("type", "closed"),
        "enabled":     cfg.get("enabled", True),
        "description": cfg.get("description", ""),
        "llm_policy":  cfg.get("llm_policy", {}),
        "features":    cfg.get("features", []),
        "version":     cfg.get("version", "0.4b"),
    }


SILO_META: dict = _make_meta()


# ── Audit log ─────────────────────────────────────────────────────────────────

def _audit_log(event: str, skill_id: str, entity_count: int,
               types_found: list[str], ok: bool, project_id: str = "lite") -> None:
    """Append one audit entry to silos/silo_2/audit.jsonl."""
    row = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "event":        event,
        "skill_id":     skill_id,
        "project_id":   project_id,
        "entity_count": entity_count,
        "types_found":  types_found,
        "ok":           ok,
    }
    with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_audit_log(limit: int = 50) -> list[dict]:
    """Return the last *limit* audit entries (most recent first)."""
    if not _AUDIT_LOG.exists():
        return []
    lines = _AUDIT_LOG.read_text(encoding="utf-8").strip().splitlines()
    rows = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass
        if len(rows) >= limit:
            break
    return rows


# ── Skills ────────────────────────────────────────────────────────────────────

def _list_skills() -> list[dict]:
    skills = []
    for f in sorted(_SKILLS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                skills.append({
                    k: data[k]
                    for k in ("id", "name", "description", "tags", "version")
                    if k in data
                })
        except Exception:  # noqa: BLE001
            pass
    return skills


def _load_skill(skill_id: str) -> dict | None:
    p = _SKILLS_DIR / f"{skill_id}.yaml"
    if not p.exists():
        return None
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return None


def _save_skill(skill_id: str, data: dict) -> None:
    p = _SKILLS_DIR / f"{skill_id}.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")


# ── Notebooks ─────────────────────────────────────────────────────────────────

_NB_INDEX = _SILO_DATA / "notebooks_index.json"


def _load_nb_index() -> list[dict]:
    if _NB_INDEX.exists():
        try:
            return json.loads(_NB_INDEX.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return []


def _save_nb_index(index: list[dict]) -> None:
    _NB_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter. Returns (meta_dict, body_str)."""
    if not content.startswith("---\n"):
        return {}, content
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content
    fm_str = content[4:end]
    body = content[end + 5:]
    try:
        meta = yaml.safe_load(fm_str) or {}
    except Exception:  # noqa: BLE001
        meta = {}
    return meta, body


def _serialize_frontmatter(meta: dict, body: str) -> str:
    """Serialize meta dict + body to frontmatter markdown."""
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
    return f"---\n{fm}\n---\n{body}"


def _create_notebook(title: str, context: str = "", tags: list[str] | None = None, project_id: str = "lite") -> dict:
    nb_id = f"nb_{uuid.uuid4().hex[:8]}"
    ts = datetime.now(timezone.utc).isoformat()

    fm_meta = {
        "title": title,
        "tags": tags or [],
        "created": ts,
        "modified": ts,
        "project_id": project_id,
        "silo": "legal",
    }
    body = f"""## Opis sprawy

{context or '_Do uzupełnienia._'}

## Strony

## Kluczowe fakty

## Zastrzeżenia prawne

## Status: SZKIC DO WERYFIKACJI

"""
    content = _serialize_frontmatter(fm_meta, body)
    nb_file = _NB_DIR / f"{nb_id}.md"
    nb_file.write_text(content, encoding="utf-8")
    meta = {
        "id":         nb_id,
        "title":      title,
        "created":    ts,
        "modified":   ts,
        "tags":       tags or [],
        "project_id": project_id,
        "file":       nb_file.name,
    }
    index = _load_nb_index()
    index.append(meta)
    _save_nb_index(index)
    return meta


def _read_notebook(nb_id: str) -> dict | None:
    index = _load_nb_index()
    meta = next((n for n in index if n["id"] == nb_id), None)
    if not meta:
        return None
    nb_file = _NB_DIR / meta["file"]
    if not nb_file.exists():
        return None
    raw = nb_file.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(raw)
    return {
        **meta,
        "content": raw,        # full file (for backward compat)
        "body": body,          # body without frontmatter
        "frontmatter": fm,     # parsed meta
    }


def _update_notebook(nb_id: str, content: str | None = None, title: str | None = None, tags: list[str] | None = None, body: str | None = None) -> bool:
    index = _load_nb_index()
    meta_idx = next((i for i, n in enumerate(index) if n["id"] == nb_id), None)
    if meta_idx is None:
        return False
    meta = index[meta_idx]
    nb_file = _NB_DIR / meta["file"]

    ts = datetime.now(timezone.utc).isoformat()

    if body is not None or title is not None or tags is not None:
        # Structured update — parse existing frontmatter
        raw = nb_file.read_text(encoding="utf-8") if nb_file.exists() else ""
        fm, existing_body = _parse_frontmatter(raw)
        if title is not None:
            fm["title"] = title
            meta["title"] = title
            index[meta_idx]["title"] = title
        if tags is not None:
            fm["tags"] = tags
            meta["tags"] = tags
            index[meta_idx]["tags"] = tags
        fm["modified"] = ts
        new_body = body if body is not None else existing_body
        nb_file.write_text(_serialize_frontmatter(fm, new_body), encoding="utf-8")
    elif content is not None:
        # Raw content update (backward compat)
        nb_file.write_text(content, encoding="utf-8")

    index[meta_idx]["modified"] = ts
    _save_nb_index(index)
    return True


def _delete_notebook(nb_id: str) -> bool:
    index = _load_nb_index()
    new_index = [n for n in index if n["id"] != nb_id]
    if len(new_index) == len(index):
        return False
    meta = next(n for n in index if n["id"] == nb_id)
    nb_file = _NB_DIR / meta["file"]
    if nb_file.exists():
        nb_file.unlink()
    _save_nb_index(new_index)
    return True


# ── Skill runner (closed — anonymized) ───────────────────────────────────────

def _run_skill(skill_id: str, inputs: dict, project_id: str = "lite") -> dict:
    """Uruchom skill przez LLM z anonimizacją wejścia (polityka closed).

    Różnice od silo_1._run_skill:
      1. Wejście (inputs) anonimizowane przed wysłaniem do LLM
      2. Brak Sleeping Matylda
      3. Model: claude-haiku-4-5 (szybszy, mniejsza pamięć kontekstu)
      4. Audit log każdego uruchomienia
    """
    from .anonymizer import anonymize_dict  # noqa: PLC0415

    skill = _load_skill(skill_id)
    if not skill:
        _audit_log("skill_not_found", skill_id, 0, [], ok=False, project_id=project_id)
        return {"error": f"Skill '{skill_id}' nie istnieje w Privacy Lab"}

    cfg = _load_config()
    llm_policy = cfg.get("llm_policy", {})

    if not llm_policy.get("external_llm", True):
        return {"error": "Zewnętrzne LLM wyłączone dla tego silosu"}

    # ── Anonimizacja wejścia ──────────────────────────────────────────────────
    anon_inputs, anon_result = anonymize_dict(inputs)

    prompt_template = skill.get("prompt_template", "")
    prompt = (
        f"{prompt_template}\n\n"
        f"## Dane wejściowe (zanonimizowane):\n"
        f"{json.dumps(anon_inputs, ensure_ascii=False, indent=2)}\n\n"
        f"Zwróć WYŁĄCZNIE obiekt JSON bez żadnego dodatkowego tekstu."
    )

    # ── LLM ───────────────────────────────────────────────────────────────────
    try:
        import anthropic  # noqa: PLC0415
        from ...config import get_api_key  # noqa: PLC0415
        from ...models import call_with_model_fallback  # noqa: PLC0415
        client = anthropic.Anthropic(api_key=get_api_key())
        msg = call_with_model_fallback(
            client, "haiku",   # closed silo: minimal attack surface
            max_tokens=3000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
    except Exception as exc:  # noqa: BLE001
        _audit_log("llm_error", skill_id, anon_result.entity_count,
                   anon_result.types_found, ok=False, project_id=project_id)
        return {"error": f"External LLM error: {exc}"}

    # ── Wytnij JSON ───────────────────────────────────────────────────────────
    raw_json = raw
    if "```" in raw_json:
        raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json.strip())
        raw_json = re.sub(r"\s*```$", "", raw_json.strip())

    try:
        result_data: dict = json.loads(raw_json)
    except json.JSONDecodeError:
        result_data = {"raw_output": raw}

    # ── DARKROOM (mandatory w closed silo) ────────────────────────────────────
    darkroom_flags: list[str] = []
    try:
        from ...darkroom import pipeline as drpipeline  # noqa: PLC0415
        dr_result = drpipeline.run(raw[:1000], str(anon_inputs)[:500], [])
        darkroom_flags = [t.get("description", "") for t in dr_result.get("tensions", [])]
    except Exception:  # noqa: BLE001
        pass

    # ── Audit ─────────────────────────────────────────────────────────────────
    _audit_log(
        "skill_run", skill_id,
        anon_result.entity_count, anon_result.types_found,
        ok=True, project_id=project_id,
    )

    return {
        "skill_id":      skill_id,
        "skill_name":    skill.get("name", skill_id),
        "llm_used":      f"anthropic/{msg.model}",
        "anonymized":    True,
        "anonymization": {
            "entity_count": anon_result.entity_count,
            "types_found":  anon_result.types_found,
            "summary":      anon_result.summary(),
        },
        "result":         result_data,
        "darkroom_flags": darkroom_flags,
        "sm_reflection":  None,   # closed silo — brak Sleeping Matylda
        "sm_next_steps":  [],
    }


# ── Hashtag labeling ──────────────────────────────────────────────────────────

def apply_hashtag(hashtag: str) -> dict:
    tag = hashtag.strip()
    if not tag.startswith("#"):
        tag = f"#{tag}"
    name = tag.lstrip("#").capitalize()
    cfg = _load_config()
    cfg["hashtag"] = tag
    cfg["name"] = name
    _save_config(cfg)
    global SILO_META
    SILO_META = _make_meta()
    return {"hashtag": tag, "name": name, "updated": True}


def detect_hashtag(text: str) -> str | None:
    cfg = _load_config()
    current_tag = cfg.get("hashtag", "#legal")
    if current_tag.lower() in text.lower():
        return current_tag
    m = re.match(r"^(#\w+)\s", text.strip())
    if m:
        return m.group(1)
    return None


# ── FastAPI Router ────────────────────────────────────────────────────────────

def get_router() -> APIRouter:
    router = APIRouter(prefix="/api/silos/silo_2", tags=["silo_privacy"])

    @router.get("/info")
    async def silo_info():
        return {**_load_config(), "silo_id": "silo_2", "meta": _make_meta()}

    @router.post("/hashtag")
    async def silo_set_hashtag(body: _HashtagBody):
        return apply_hashtag(body.hashtag)

    # ── Skills ───────────────────────────────────────────────────────────────

    @router.get("/skills")
    async def list_skills_ep():
        return {"skills": _list_skills()}

    @router.post("/skills/run")
    async def run_skill_ep(body: _SkillRunBody):
        import asyncio  # noqa: PLC0415
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run_skill, body.skill_id, body.inputs)

    @router.post("/skills/create")
    async def create_skill_ep(body: _SkillCreateBody):
        data = {
            "id":              body.id,
            "name":            body.name,
            "description":     body.description,
            "prompt_template": body.prompt_template,
            "tags":            body.tags,
            "version":         "1.0",
            "llm_policy":      {"external_llm": True, "anonymize": True, "darkroom": True},
            "created":         datetime.now(timezone.utc).isoformat()[:10],
        }
        _save_skill(body.id, data)
        return {"created": True, "skill_id": body.id}

    @router.get("/skills/{skill_id}")
    async def get_skill_ep(skill_id: str):
        skill = _load_skill(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill nie znaleziony")
        return skill

    # ── Anonymizer endpoint ───────────────────────────────────────────────────

    @router.post("/anonymize")
    async def anonymize_ep(request: Request):
        """Anonymize arbitrary text or dict payload. Returns anonymized form + stats."""
        from .anonymizer import anonymize, anonymize_dict  # noqa: PLC0415
        body = await request.json()
        text = body.get("text")
        data = body.get("data")
        if text is not None:
            result = anonymize(str(text))
            return {
                "anonymized_text": result.anonymized_text,
                "entity_count":    result.entity_count,
                "types_found":     result.types_found,
                "summary":         result.summary(),
            }
        if data is not None:
            anon_data, result = anonymize_dict(data if isinstance(data, dict) else {"value": data})
            return {
                "anonymized_data": anon_data,
                "entity_count":    result.entity_count,
                "types_found":     result.types_found,
                "summary":         result.summary(),
            }
        return {"error": "Podaj 'text' lub 'data' w body"}

    # ── Audit log ─────────────────────────────────────────────────────────────

    @router.get("/audit")
    async def audit_log_ep(limit: int = 50):
        entries = load_audit_log(limit=limit)
        return {"entries": entries, "count": len(entries)}

    # ── Notebooks ─────────────────────────────────────────────────────────────

    @router.get("/notebooks")
    async def list_notebooks_ep(project_id: str = Query("")):
        nbs = _load_nb_index()
        if project_id:
            nbs = [n for n in nbs if n.get("project_id") == project_id]
        return {"notebooks": nbs}

    @router.post("/notebooks/create")
    async def create_notebook_ep(body: _NotebookCreateBody):
        meta = _create_notebook(body.title, body.context, body.tags, body.project_id)
        return {"created": True, **meta}

    @router.get("/notebooks/{nb_id}")
    async def get_notebook_ep(nb_id: str):
        nb = _read_notebook(nb_id)
        if not nb:
            raise HTTPException(status_code=404, detail="Notebook nie znaleziony")
        return nb

    @router.put("/notebooks/{nb_id}")
    async def update_notebook_ep(nb_id: str, body: _NotebookUpdateBody):
        ok = _update_notebook(nb_id, content=body.content, title=body.title, tags=body.tags, body=body.body)
        if not ok:
            raise HTTPException(status_code=404, detail="Notebook nie znaleziony")
        return {"updated": True}

    @router.delete("/notebooks/{nb_id}")
    async def delete_notebook_ep(nb_id: str):
        ok = _delete_notebook(nb_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Notebook nie znaleziony")
        return {"deleted": True}

    # ── Pipeline ──────────────────────────────────────────────────────────────

    @router.post("/run-pipeline")
    async def run_pipeline_ep(body: _PipelineRunBody):
        """Uruchom pełny ResearchPipeline z anonimizacją (closed silo)."""
        import asyncio  # noqa: PLC0415
        from ...research_pipeline import run_research_pipeline  # noqa: PLC0415

        def _run():
            return run_research_pipeline(
                body.skill_id,
                body.inputs,
                silo_id="silo_2",
                project_id=body.project_id,
                title=body.title,
            )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _run)
        return result.as_dict()

    # ── LLM policy ───────────────────────────────────────────────────────────

    @router.get("/llm-policy")
    async def get_llm_policy_ep():
        cfg = _load_config()
        return {
            "silo_id":   "silo_2",
            "silo_type": cfg.get("type", "closed"),
            "policy":    cfg.get("llm_policy", {}),
        }

    return router


# ── Dashboard widget ──────────────────────────────────────────────────────────

def get_dashboard_widget() -> str:
    cfg = _load_config()
    name    = cfg.get("name", "Legal")
    hashtag = cfg.get("hashtag", "#legal")

    return f"""<div class="silo-widget" id="silo-legal-widget">
  <div class="silo-widget-header">
    <span class="silo-widget-name">⚖️ {name}</span>
    <span class="silo-type-badge" style="background:#e76f5122;color:#e76f51">CLOSED</span>
    <span class="silo-hashtag">{hashtag}</span>
  </div>
  <div class="silo-policy-row">Anon ✓ &nbsp;·&nbsp; DARKROOM ✓ &nbsp;·&nbsp; SM ✗ &nbsp;·&nbsp; Human review ✓</div>
  <div class="silo-actions">
    <button onclick="loadSiloLegal()" class="silo-btn">↻</button>
    <button onclick="openLegalSkills()" class="silo-btn">📋 Skills</button>
    <button onclick="newLegalNotebook()" class="silo-btn">📓 Notebook</button>
    <button onclick="runLegalAnonymize()" class="silo-btn">🔏 Anonymize</button>
    <button onclick="runLegalPipeline()" class="silo-btn silo-btn-pipeline">⚡ Pipeline</button>
  </div>
  <div id="silo-legal-summary" class="silo-summary">ładowanie…</div>
</div>"""
