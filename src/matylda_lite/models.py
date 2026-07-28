"""Model routing: task description → haiku / sonnet / fable / opus.

v0.3g: aktualne modele Claude 4.x + Fable 5.
  - update_model_performance() — zapisuje wynik po każdym użyciu modelu
  - calculate_model_scores()   — UCB1 score per model per task_type
  - recommend_model_ucb1()     — UCB1 + heurystyczny bias na treści zadania
  - route()                    — zachowuje LLM routing, wzbogacony o UCB1 feedback
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import ROOT

# ── Model IDs ─────────────────────────────────────────────────────────────────
MODELS: dict[str, str] = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "fable":  "claude-opus-4-8",   # fable-5 requires special access — fallback to opus
    "opus":   "claude-opus-4-8",
}

SUPPORTED_MODELS = list(MODELS.keys())  # ["haiku", "sonnet", "fable", "opus"]

# ── Resilient model calls ──────────────────────────────────────────────────────
# Anthropic's offering changes over time: model ids get retired, access tiers
# change (e.g. "fable" requiring special access), and accepted parameters
# change per-model (e.g. "temperature" deprecated on some models). Rather than
# hand-patching call sites every time this happens (as happened 3x in one
# session), call_with_model_fallback() absorbs these failures automatically:
#   1. Try the configured MODELS[tier].
#   2. If the model 404s (not available on this key) → fall through to the
#      next tier in _FALLBACK_CHAIN (e.g. fable → opus → sonnet).
#   3. If the model rejects a parameter as deprecated (400) → retry once
#      without that parameter.
#   4. As a last resort, query /v1/models for what's actually live and pick
#      the highest-version id matching the tier's name prefix.
# A successful resolution is cached in-memory so later calls in the same
# process skip straight to the working model id.

_FALLBACK_CHAIN: dict[str, list[str]] = {
    "fable":  ["fable", "opus", "sonnet"],
    "opus":   ["opus", "sonnet"],
    "sonnet": ["sonnet", "opus"],
    "haiku":  ["haiku", "sonnet"],
}

_resolved_model_cache: dict[str, str] = {}


def _discover_live_model_ids(client) -> list[str]:
    """Query the Anthropic API for model ids actually available on this key."""
    try:
        return [m.id for m in client.models.list(limit=100).data]
    except Exception:  # noqa: BLE001
        return []


def _pick_latest_for_tier(tier: str, live_ids: list[str]) -> str | None:
    """From live model ids, pick the highest-version id matching `claude-{tier}-*`."""
    import re as _re
    prefix = f"claude-{tier}-"
    candidates = [mid for mid in live_ids if mid.startswith(prefix)]
    if not candidates:
        return None
    candidates.sort(key=lambda mid: [int(n) for n in _re.findall(r"\d+", mid)], reverse=True)
    return candidates[0]


def call_with_model_fallback(client, tier: str, **kwargs):
    """client.messages.create() with automatic fallback across model/tier changes.

    Args:
        client: an anthropic.Anthropic instance.
        tier:   "haiku" | "sonnet" | "opus" | "fable" — desired capability tier.
        **kwargs: forwarded to client.messages.create() (messages, max_tokens, ...).

    Returns:
        The anthropic Message response.

    Raises:
        RuntimeError if no model in the fallback chain (including live
        discovery) could serve the request.
    """
    import anthropic as _anthropic  # noqa: PLC0415

    chain = _FALLBACK_CHAIN.get(tier, [tier])
    tried: list[str] = []

    for fallback_tier in chain:
        model_id = _resolved_model_cache.get(fallback_tier) or MODELS.get(fallback_tier, fallback_tier)
        if model_id in tried:
            continue
        tried.append(model_id)

        call_kwargs = dict(kwargs)
        for _attempt in range(2):
            try:
                msg = client.messages.create(model=model_id, **call_kwargs)
                _resolved_model_cache[tier] = model_id
                return msg
            except _anthropic.NotFoundError:
                break  # model not available on this key → try next tier
            except _anthropic.BadRequestError as exc:
                if "temperature" in str(exc).lower() and "temperature" in call_kwargs:
                    call_kwargs.pop("temperature")
                    continue  # retry same model without the deprecated param
                raise

    # Last resort: ask the API what's actually live and try those directly.
    live_ids = _discover_live_model_ids(client)
    for fallback_tier in chain:
        live_id = _pick_latest_for_tier(fallback_tier, live_ids)
        if not live_id or live_id in tried:
            continue
        tried.append(live_id)
        try:
            msg = client.messages.create(model=live_id, **kwargs)
            _resolved_model_cache[tier] = live_id
            return msg
        except Exception:  # noqa: BLE001
            continue

    raise RuntimeError(
        f"Nie udało się wywołać żadnego modelu dla tier={tier!r} (próbowano: {tried})"
    )


def resolve_model_id(client, tier: str) -> str:
    """Resolve which model id should serve `tier`, for callers that need the
    id upfront (e.g. client.messages.stream(), which this module can't wrap
    directly — a failure mid-stream can't be retried without risking
    duplicate/partial output already sent to the caller).

    Cached after first resolution. The first call per tier in a process costs
    one minimal (max_tokens=1) probe request that exercises the same
    fallback chain as call_with_model_fallback().
    """
    if tier in _resolved_model_cache:
        return _resolved_model_cache[tier]
    msg = call_with_model_fallback(
        client, tier, max_tokens=1, messages=[{"role": "user", "content": "."}],
    )
    return msg.model


# ── Performance log (UCB1) ────────────────────────────────────────────────────
PERFORMANCE_LOG = ROOT / "data" / "model_performance.jsonl"
PERFORMANCE_LOG.parent.mkdir(parents=True, exist_ok=True)

# Task types used in performance tracking
TASK_TYPES = ["routing", "synthesis", "review", "research", "coding", "planning", "general"]


# ── UCB1 functions ─────────────────────────────────────────────────────────────

def update_model_performance(
    task_type: str,
    model: str,
    success: bool,
    latency_ms: float | None = None,
    project_id: str = "",
) -> dict:
    """Append one performance observation to the JSONL log.

    Args:
        task_type: One of TASK_TYPES (or any string).
        model:     "haiku" | "sonnet" | "fable" | "opus"
        success:   Whether the model produced a satisfactory result.
        latency_ms: Optional response latency in milliseconds.
        project_id: Optional project for context.

    Returns:
        The logged row dict.
    """
    row = {
        "timestamp": datetime.now().isoformat(),
        "task_type": task_type,
        "model": model,
        "success": bool(success),
        "latency_ms": latency_ms,
        "project_id": project_id or "",
    }
    with PERFORMANCE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def calculate_model_scores(task_type: str) -> dict[str, dict]:
    """Calculate UCB1-adjusted success rates per model for a task_type.

    Returns:
        {model: {"successes": int, "calls": int, "success_rate": float, "ucb1": float}}
    """
    stats: dict[str, dict] = {
        m: {"successes": 0, "calls": 0, "success_rate": 0.0, "ucb1": 0.0}
        for m in SUPPORTED_MODELS
    }

    if not PERFORMANCE_LOG.exists():
        return stats

    try:
        for line in PERFORMANCE_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("task_type") != task_type:
                continue
            model = row.get("model")
            if model not in SUPPORTED_MODELS:
                continue
            stats[model]["calls"] += 1
            if bool(row.get("success")):
                stats[model]["successes"] += 1
    except Exception:  # noqa: BLE001
        return stats

    total_calls = sum(s["calls"] for s in stats.values())

    for model in SUPPORTED_MODELS:
        calls = stats[model]["calls"]
        if calls > 0:
            stats[model]["success_rate"] = stats[model]["successes"] / calls
            if total_calls > 0:
                stats[model]["ucb1"] = (
                    stats[model]["success_rate"]
                    + math.sqrt(2.0 * math.log(max(total_calls, 1)) / calls)
                )
        else:
            # Never tried → explore first (infinite bonus)
            stats[model]["ucb1"] = float("inf")

    return stats


def recommend_model_ucb1(task_type: str, task_text: str = "") -> str:
    """Recommend a model using UCB1 + heuristic bias on task content.

    UCB1 = success_rate + sqrt(2 * ln(total) / model_calls)
    Exploration: models never used get priority automatically.

    Heuristic biases for Lite models:
      - Hostile review / adversarial / krytyka → opus +0.15
      - Deep synthesis / narracja / długa forma → fable +0.12
      - Synthesis / research / literatura → sonnet +0.10, fable +0.08
      - Status / routing / lista / szybkie → haiku +0.05

    Returns "haiku" | "sonnet" | "fable" | "opus".
    """
    scores = calculate_model_scores(task_type)

    # Exploration-first — haiku eksplorujemy TYLKO dla task_type=routing.
    # Dla wszystkich innych typów haiku nie jest kandydatem do eksploracji.
    _haiku_ok_for_exploration = {"routing"}
    for model in SUPPORTED_MODELS:
        if scores[model]["ucb1"] == float("inf"):
            if model == "haiku" and task_type not in _haiku_ok_for_exploration:
                continue
            return model

    # Apply content-based bias
    text_lower = (task_text or "").lower()
    bias: dict[str, float] = {m: 0.0 for m in SUPPORTED_MODELS}

    _hostile_kw = ("hostile", "adversarial", "krytyk", "review", "recenzja", "wada", "błąd", "refute",
                   "stress-test", "falsyfik", "no-go", "obalić", "słabości")
    _fable_kw   = ("narracja", "narrative", "opowieść", "refleksja", "reflection", "mapa literatury",
                   "podsumuj całość", "długa forma", "long-form", "historia", "story",
                   "wielowątk", "multi-thread", "synteza narracyjna")
    _synth_kw   = ("synteza", "synthesis", "literatura", "mapa", "opracow", "analiz", "plan",
                   "napisz", "przygotuj", "zbadaj", "porównaj", "oceń", "wytłumacz", "explain",
                   "summarize", "draft", "outline", "design", "implement", "code", "algorithm")
    _fast_kw    = ("status", "lista", "check", "routing", "szybk", "ile", "kiedy", "who", "what is",
                   "co to", "ile jest", "jaki jest")

    if any(kw in text_lower for kw in _hostile_kw):
        bias["opus"] += 0.15
    if any(kw in text_lower for kw in _fable_kw):
        bias["fable"] += 0.12
    if any(kw in text_lower for kw in _synth_kw):
        bias["sonnet"] += 0.10
        bias["fable"]  += 0.08
    if any(kw in text_lower for kw in _fast_kw):
        bias["haiku"] += 0.05

    # task_type-level bias (niezależnie od treści)
    _type_bias: dict[str, dict[str, float]] = {
        "research":  {"sonnet": 0.10, "fable": 0.10, "haiku": -0.30},
        "synthesis": {"fable":  0.20, "sonnet": 0.05, "haiku": -0.30},
        "coding":    {"sonnet": 0.15, "haiku": -0.20},
        "planning":  {"sonnet": 0.10, "fable": 0.05, "haiku": -0.20},
        "review":    {"opus":   0.20, "haiku": -0.30},
        "routing":   {"haiku":  0.10},
        "general":   {"sonnet": 0.05, "fable": 0.03},
    }
    for model, delta in _type_bias.get(task_type, {}).items():
        if model in bias:
            bias[model] += delta

    # UCB1 + bias
    # Uwaga: float("inf") + bias nie daje sensownego wyniku — obsługujemy osobno.
    # Haiku z UCB1=inf (nieeksplorowany) w kontekście non-routing traktujemy jak 0.0.
    best_model = "sonnet"
    best_score = float("-inf")
    for model in SUPPORTED_MODELS:
        ucb1 = scores[model]["ucb1"]
        if ucb1 == float("inf"):
            if model == "haiku" and task_type not in _haiku_ok_for_exploration:
                # Blokada: haiku nieeksplorowane w ciężkim kontekście → skor minimalny
                score = 0.0 + bias[model]
            else:
                # Inny nieeksplorowany model: wysoki skor eksploracyjny (wysoki ale skończony)
                score = 2.0 + bias[model]
        else:
            score = ucb1 + bias[model]

        if score > best_score:
            best_score = score
            best_model = model

    return best_model


def get_model_performance_summary() -> dict:
    """Return a summary of model performance across all task types."""
    summary: dict[str, dict] = {}
    for tt in TASK_TYPES:
        scores = calculate_model_scores(tt)
        total_calls = sum(s["calls"] for s in scores.values())
        if total_calls == 0:
            continue
        summary[tt] = {
            model: {
                "calls": scores[model]["calls"],
                "success_rate": round(scores[model]["success_rate"], 3),
                "ucb1": round(scores[model]["ucb1"], 3) if scores[model]["ucb1"] != float("inf") else None,
            }
            for model in SUPPORTED_MODELS
            if scores[model]["calls"] > 0
        }
    return summary


# ── Routing prompt + LLM router ───────────────────────────────────────────────

_SYSTEM = """\
Jesteś warstwą routingu dla Matylda Lab — lokalnego systemu zarządzania wątkami badawczymi.

Otrzymujesz stan workspace i opis zadania. Twój jedyny output to JSON (bez prozy):

{
  "model": "haiku" | "sonnet" | "fable" | "opus",
  "task_type": "routing" | "synthesis" | "review" | "research" | "coding" | "planning" | "general",
  "needs_web": true | false,
  "urls": ["url1", "url2"],
  "should_save": true | false,
  "suggested_filename": "NAZWA_ARTEFAKTU.md",
  "reasoning": "jedno zdanie uzasadnienia"
}

REGUŁY DOBORU MODELU (rygorystyczne):
- haiku:  WYŁĄCZNIE dla meta-zapytań workspace: sprawdzenie statusu wątków, ile wątków, routing wewnętrzny. NIE dla pytań o treść — nawet krótkich.
- sonnet: DOMYŚLNY. Używaj dla WSZYSTKICH pytań o treść: research, analiza, pisanie, synteza, planowanie, kodowanie, wyjaśnienia, pytania faktyczne (nawet ≤2 zdania).
- fable:  Dla głębokiej syntezy i długich form narracyjnych: mapy literatury, refleksje wielowątkowe, opracowania wymagające narracji i spójności między wątkami.
- opus:   WYŁĄCZNIE gdy: hostile review, adversarial stress-test, strategiczna decyzja wymagająca głębokiego rozumowania.

WAŻNE: Każde pytanie zaczynające się od "co to", "jak", "wyjaśnij", "napisz", "porównaj", "dlaczego" → sonnet, fable lub opus. Nigdy haiku.
WAŻNE: task_type=research ZAWSZE → sonnet, fable lub opus. task_type=routing TYLKO dla meta-operacji (nie dla pytań o treść).
WAŻNE: jeśli masz wątpliwość między haiku a sonnet — wybierz sonnet.

task_type: wybierz jedną z wartości (routing/synthesis/review/research/coding/planning/general).

Reguły dotyczące sieci:
- needs_web=true tylko gdy zadanie wymaga aktualnych danych spoza workspace
- urls: podaj konkretne URLe tylko gdy jesteś pewien że istnieją i są trafne
- maksymalnie 4 URLe

Reguły zapisu:
- should_save=true gdy wynik to samodzielny artefakt (notatka, mapa literatury, review)
- suggested_filename: WIELKIE_LITERY_Z_PODKREŚLENIAMI.md, brak spacji

Odpowiedz WYŁĄCZNIE poprawnym JSON, bez markdown, bez wyjaśnień.
"""


@dataclass
class RoutingDecision:
    model: str
    task_type: str
    needs_web: bool
    urls: list[str]
    should_save: bool
    suggested_filename: str
    reasoning: str
    ucb1_suggestion: str = ""       # UCB1 recommendation (informational)
    ucb1_overrode_llm: bool = False  # True if UCB1 changed the LLM's choice


def route(task: str, workspace_summary: str, client) -> RoutingDecision:
    """Route a task to a model.

    Flow:
    1. LLM (Haiku) suggests model + task_type
    2. UCB1 calculates best model for that task_type based on history
    3. If UCB1 strongly disagrees (e.g., LLM says haiku but UCB1 says opus),
       override to UCB1 suggestion
    4. Log neither automatically here — caller should call
       update_model_performance() after receiving the result.
    """
    resp = client.messages.create(
        model=MODELS["haiku"],
        max_tokens=512,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"STAN WORKSPACE:\n{workspace_summary}\n\nZADANIE:\n{task}",
        }],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:]).rstrip("`").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}

    llm_model = data.get("model", "sonnet") if data.get("model") in MODELS else "sonnet"
    task_type = data.get("task_type", "general")
    if task_type not in TASK_TYPES:
        task_type = "general"

    # ── Hard rules (przed UCB1) ──────────────────────────────────────────────
    # research/synthesis/coding/planning/general nigdy nie powinno wylądować na haiku
    _heavy_types = {"research", "synthesis", "coding", "planning", "general"}
    if llm_model == "haiku" and task_type in _heavy_types:
        llm_model = "sonnet"  # silent upgrade

    # Haiku dozwolone TYLKO dla task_type="routing" i tylko gdy pytanie
    # wygląda jak meta-zapytanie (krótkie, brak słów kluczowych treści).
    # Każde pytanie o wyjaśnienie, opis, analizę → minimum sonnet.
    _content_kw = (
        "co to", "co jest", "jak ", "wyjaśnij", "wytłumacz", "napisz",
        "opowiedz", "opisz", "czym jest", "dlaczego", "kiedy ", "skąd",
        "what is", "what are", "how ", "explain", "describe", "write",
        "compare", "analyze", "tell me", "give me",
    )
    _task_lower = task.lower()
    _looks_like_content = any(kw in _task_lower for kw in _content_kw)
    if llm_model == "haiku" and (task_type != "routing" or _looks_like_content):
        llm_model = "sonnet"  # treść pytania → minimum sonnet

    # ── UCB1 override ────────────────────────────────────────────────────────
    ucb1_suggestion = recommend_model_ucb1(task_type, task)
    ucb1_overrode = False

    scores = calculate_model_scores(task_type)
    total_calls = sum(s["calls"] for s in scores.values())
    final_model = llm_model

    if total_calls >= 5 and ucb1_suggestion != llm_model:
        ucb1_score = scores[ucb1_suggestion]["ucb1"]
        llm_score  = scores[llm_model]["ucb1"] if scores[llm_model]["calls"] > 0 else 0.0

        if ucb1_score == float("inf"):
            # Model nieeksplorowany — wymuś eksplorację (to był bug: wcześniej blokowane)
            final_model = ucb1_suggestion
            ucb1_overrode = True
        elif llm_score != float("inf") and ucb1_score - llm_score > 0.20:
            # UCB1 zdecydowanie preferuje inny model na podstawie historii
            final_model = ucb1_suggestion
            ucb1_overrode = True

    # ── Final guard: hard rules nie mogą być cofnięte przez UCB1 ────────────
    # UCB1 może zasugerować haiku jeśli ma dobre wyniki historyczne,
    # ale hard rules są nieprzekraczalne.
    if final_model == "haiku" and (task_type in _heavy_types or _looks_like_content):
        final_model = "sonnet"
        ucb1_overrode = False  # to nie był override — to była blokada bezpieczeństwa

    return RoutingDecision(
        model=final_model,
        task_type=task_type,
        needs_web=bool(data.get("needs_web", False)),
        urls=data.get("urls", [])[:4],
        should_save=bool(data.get("should_save", False)),
        suggested_filename=data.get("suggested_filename", ""),
        reasoning=data.get("reasoning", ""),
        ucb1_suggestion=ucb1_suggestion,
        ucb1_overrode_llm=ucb1_overrode,
    )
