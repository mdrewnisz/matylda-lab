"""Secretary: orchestrate workspace tasks using Claude API.

Dwa tryby:
  chat(messages, save_as)       — multi-turn, pełny pipeline DARKROOM
  stream_chat(messages, save_as) — generator SSE chunks + metadata na końcu

Epistemic Limitation Mode:
  Gdy suma severity aktywnych napięć >= progu, system automatycznie
  instruuje model żeby dodał sekcję ograniczeń epistemicznych.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import Any, Generator

import anthropic

from .browser import fetch_url
from .config import ROOT, get_api_key
from .darkroom import pipeline as drpipeline
from .memory_manager import load_relevant_insights, save_insight  # noqa: F401
from .models import MODELS, RoutingDecision, call_with_model_fallback, resolve_model_id, route
from .project_context import build_project_context_string
from .thread_timeline import log_event as _timeline_log

_CONTEXT_FILES = [
    "desk/ACTIVE_THREADS.md",
    "desk/THIS_WEEK.md",
    "desk/PARKING_LOT.md",
    "desk/DECISION_LOG.md",
    "prompts/NEXT_PROMPTS.md",
]

_PERSONA_FILE = ROOT / "prompts" / "PERSONA_MATYLDA_LITE.md"

def _load_persona() -> str:
    """Load persona from file, fallback to minimal if missing."""
    if _PERSONA_FILE.exists():
        return _PERSONA_FILE.read_text(encoding="utf-8").strip()
    return "Jesteś Matylda Lab — konstruktywnym, lokalnym asystentem badawczym."

_BASE_SYSTEM = """\
{persona}

---

## Zasady operacyjne

- Nie wymyślaj cytatów ani referencji literaturowych.
- Bądź precyzyjny w kwestii niepewności — nie maskuj braków elokwencją.
- Outputy pisz gotowe do zapisu jako Markdown.
- Mapy literatury: organizuj według bucketów, zaznaczaj luki.
- Domyślnie rozwijaj użyteczną możliwość, zanim przejdziesz do krytyki.
- Krytykę dawkuj proporcjonalnie: nazwij ryzyko, ale nie zamieniaj odpowiedzi
  w hostile review. Ten tryb należy wyłącznie do jawnego NO-GO.
- Język outputu dopasuj do języka zadania (PL lub EN).
- Rozdzielaj dane od interpretacji; spekulacje oznaczaj jawnie.

{darkroom_context}
{epistemic_limit_section}"""

_EPISTEMIC_LIMIT_SECTION = """\

[EPISTEMIC LIMITATION MODE — AKTYWNY: severity_sum={sev_sum:.2f}]
Napięcia i historia błędów workspace wskazują na podwyższone ryzyko epistemiczne.
Jeśli ryzyko ma znaczenie dla decyzji użytkownika, dodaj na końcu krótką sekcję:

## Granice tej odpowiedzi
- Maksymalnie trzy konkretne punkty dotyczące bieżącego zadania.
- Wskaż najmniejszy test lub informację, która zmniejszy niepewność.

Nie powtarzaj historii DARKROOMU i nie zatrzymuj konstruktywnej eksploracji.
"""


class Secretary:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client or anthropic.Anthropic(api_key=get_api_key())

    # ── Public: one-shot ──────────────────────────────────────────────────────

    def run(self, task: str, save_as: str | None = None) -> dict:
        return self.chat([{"role": "user", "content": task}], save_as=save_as)

    # ── Public: multi-turn (blocking) ─────────────────────────────────────────

    def chat(self, messages: list[dict], save_as: str | None = None, no_go: bool = False) -> dict:
        task         = self._last_user(messages)
        workspace    = self._build_context(task)
        decision     = route(task, workspace, self.client)
        web_content, fetched_urls = self._fetch_web(decision)
        system       = self._build_system(task, web_content, no_go=no_go)
        aug_messages = self._augment(messages, workspace, web_content)

        resp = call_with_model_fallback(
            self.client, decision.model,
            max_tokens=4096,
            system=system,
            messages=aug_messages,
        )
        result = resp.content[0].text.strip()

        saved_to = self._maybe_save(result, task, save_as, decision)

        review = drpipeline.run_review(
            task=task, result=result, model_used=decision.model,
            client=self.client, messages=messages, saved_to=saved_to,
        )

        if not no_go:
            topology = drpipeline.run_confidence_topology(task, result, self.client)
        else:
            topology = {"no_go_mode": True}

        # ── Chronicle + UCB1 ────────────────────────────────────────────────
        try:
            from .chronicle import log_secretary_event  # noqa: PLC0415
            from .models import update_model_performance  # noqa: PLC0415
            _proj_id = ""
            try:
                from .project_context import get_active_project as _gap  # noqa: PLC0415
                _p = _gap(); _proj_id = (_p or {}).get("project_id", "") or ""
            except Exception:  # noqa: BLE001
                pass
            log_secretary_event(
                task=task, model=decision.model,
                saved_as=saved_to, project_id=_proj_id or "lite",
                success=bool(result),
            )
            update_model_performance(
                task_type=getattr(decision, "task_type", "general"),
                model=decision.model,
                success=bool(result),
                project_id=_proj_id,
            )
        except Exception:  # noqa: BLE001
            pass

        return {
            "result": result,
            "model_key": decision.model,
            "model_id": resp.model,
            "reasoning": decision.reasoning,
            "ucb1_suggestion": getattr(decision, "ucb1_suggestion", ""),
            "ucb1_overrode_llm": getattr(decision, "ucb1_overrode_llm", False),
            "fetched_urls": fetched_urls,
            "saved_to": saved_to,
            "review": review,
            "topology": topology,
        }

    # ── Public: streaming ─────────────────────────────────────────────────────

    def stream_chat(
        self,
        messages: list[dict],
        save_as: str | None = None,
        no_go: bool = False,
    ) -> Generator[dict, None, None]:
        """
        Generator yielding SSE-style dicts:
          {"type": "chunk",  "text": "..."}          — incremental text
          {"type": "done",   ...core result...}       — emitted RIGHT after stream ends
          {"type": "review", "review": ..., ...}      — emitted after DARKROOM pipeline
          {"type": "error",  "error": "..."}          — on hard failure (routing / stream fail)

        "done" is emitted before review/topology so the client can show the full
        result and re-enable the send button without waiting 20-30s for DARKROOM.
        "review" arrives later with DARKROOM metadata.  If review itself fails,
        only the review event is skipped — the "done" result is already shown.
        """
        # ── Routing + stream ──────────────────────────────────────────────────
        try:
            task         = self._last_user(messages)
            workspace    = self._build_context(task)
            decision     = route(task, workspace, self.client)
            web_content, fetched_urls = self._fetch_web(decision)
            system       = self._build_system(task, web_content, no_go=no_go)
            aug_messages = self._augment(messages, workspace, web_content)

            full_result = ""
            resolved_model = resolve_model_id(self.client, decision.model)
            with self.client.messages.stream(
                model=resolved_model,
                max_tokens=4096,
                system=system,
                messages=aug_messages,
            ) as stream:
                for chunk in stream.text_stream:
                    full_result += chunk
                    yield {"type": "chunk", "text": chunk}

        except Exception as e:  # noqa: BLE001
            # Hard failure (routing or stream itself) — no usable content yet
            yield {"type": "error", "error": str(e)}
            return

        # ── Save artifact ──────────────────────────────────────────────────────
        saved_to = self._maybe_save(full_result, task, save_as, decision)

        if saved_to:
            from .thread_timeline import log_event as _tl  # noqa: PLC0415
            try:
                from .project_context import get_active_project  # noqa: PLC0415
                proj = get_active_project()
                if proj and proj.get("threads"):
                    _tl(proj["threads"][0], "artifact_created", f"Artifact: {saved_to}")
            except Exception:  # noqa: BLE001
                pass

        # ── Emit "done" IMMEDIATELY — client shows result and re-enables button ─
        yield {
            "type": "done",
            "result": full_result,
            "model_key": decision.model,
            "model_id": resolved_model,
            "reasoning": decision.reasoning,
            "fetched_urls": fetched_urls,
            "saved_to": saved_to,
        }

        # ── v0.5: fire response.done — proactive connections hook ────────────────
        try:
            from .hooks import fire as _fire  # noqa: PLC0415
            # Pass stem derived from saved_to filename (strip path and extension)
            _stem = None
            if saved_to:
                import re as _re  # noqa: PLC0415
                _base = saved_to.split("/")[-1].split("\\")[-1]
                _stem = _re.sub(r"\.(md|txt|json)$", "", _base)
            _fire("response.done", stem=_stem, saved_to=saved_to)
        except Exception:  # noqa: BLE001
            pass

        # ── Chronicle + UCB1 (non-blocking — after done is already sent) ────────
        try:
            from .chronicle import log_secretary_event  # noqa: PLC0415
            from .models import update_model_performance  # noqa: PLC0415
            _proj_id = ""
            try:
                from .project_context import get_active_project as _gap  # noqa: PLC0415
                _p = _gap(); _proj_id = (_p or {}).get("project_id", "") or ""
            except Exception:  # noqa: BLE001
                pass
            log_secretary_event(
                task=task, model=decision.model,
                saved_as=saved_to, project_id=_proj_id or "lite",
                success=bool(full_result),
            )
            update_model_performance(
                task_type=getattr(decision, "task_type", "general"),
                model=decision.model,
                success=bool(full_result),
                project_id=_proj_id,
            )
        except Exception:  # noqa: BLE001
            pass

        # ── DARKROOM review + topology (after done — failures are non-fatal) ───
        try:
            review = drpipeline.run_review(
                task=task, result=full_result, model_used=decision.model,
                client=self.client, messages=messages, saved_to=saved_to,
            )
            topology = (
                drpipeline.run_confidence_topology(task, full_result, self.client)
                if not no_go else {"no_go_mode": True}
            )
            yield {
                "type": "review",
                "review": review,
                "topology": topology,
            }
        except Exception:  # noqa: BLE001
            # Review failed — silently skip; result is already shown in "done"
            pass

    # ── Public: utilities ─────────────────────────────────────────────────────

    def fetch(self, url: str) -> dict:
        return {"url": url, "content": fetch_url(url)}

    def status(self) -> dict:
        from .dashboard import artifact_list, inbox_status, parse_table, read  # noqa: PLC0415
        active = parse_table(read("desk/ACTIVE_THREADS.md"))
        empty, count = inbox_status()
        return {
            "active_threads": len(active),
            "inbox_empty": empty,
            "inbox_count": count,
            "artifacts": artifact_list(),
            "date": str(date.today()),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _last_user(messages: list[dict]) -> str:
        return next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )

    def _build_context(self, task: str = "") -> str:
        parts = []
        for rel in _CONTEXT_FILES:
            p = ROOT / rel
            if p.exists():
                parts.append(f"=== {rel} ===\n{p.read_text(encoding='utf-8')}")
        # Memory insights
        memory_ctx = load_relevant_insights(task)
        if memory_ctx:
            parts.append(memory_ctx)
        # Active project
        proj_ctx = build_project_context_string()
        if proj_ctx:
            parts.append(proj_ctx)
        return "\n\n".join(parts)

    def _fetch_web(self, decision: RoutingDecision) -> tuple[str, list[str]]:
        web_content, fetched_urls = "", []
        if decision.needs_web:
            for url in decision.urls:
                web_content += fetch_url(url) + "\n\n---\n\n"
                fetched_urls.append(url)
        return web_content, fetched_urls

    def _build_system(self, task: str, web_content: str, no_go: bool = False) -> str:
        if no_go:
            return drpipeline.build_nogo_system_prompt()
        darkroom_ctx = drpipeline.build_darkroom_context(task=task)
        epi_active, epi_sum = drpipeline.check_epistemic_limit_mode(task=task)
        epi_section = (
            _EPISTEMIC_LIMIT_SECTION.format(sev_sum=epi_sum) if epi_active else ""
        )
        return _BASE_SYSTEM.format(
            persona=_load_persona(),
            darkroom_context=darkroom_ctx,
            epistemic_limit_section=epi_section,
        )

    def _augment(
        self,
        messages: list[dict],
        workspace: str,
        web_content: str,
    ) -> list[dict]:
        prefix = f"STAN WORKSPACE:\n{workspace}"
        if web_content:
            prefix += f"\n\nPOBRANE TREŚCI Z SIECI:\n{web_content}"
        aug = list(messages)
        if aug and aug[0]["role"] == "user":
            aug = [
                {"role": "user", "content": f"{prefix}\n\n---\n\n{aug[0]['content']}"},
                *aug[1:],
            ]
        return aug

    def _maybe_save(
        self,
        result: str,
        task: str,
        save_as: str | None,
        decision: RoutingDecision,
    ) -> str | None:
        filename = save_as or (decision.suggested_filename if decision.should_save else None)
        if not filename:
            return None
        filename = re.sub(r"[^\w\-.]", "_", filename)
        if not filename.upper().endswith(".MD"):
            filename += ".md"
        p = ROOT / "artifacts" / filename
        header = (
            f"# {filename.replace('_', ' ').replace('.md', '').replace('.MD', '')}\n\n"
            f"_Wygenerowano: {date.today()} · "
            f"Model: {MODELS[decision.model]} · "
            f"Zadanie: {task[:80]}{'…' if len(task) > 80 else ''}_\n\n---\n\n"
        )
        p.write_text(header + result + "\n", encoding="utf-8")
        return str(p.relative_to(ROOT))
