"""Diary Manager — v0.4 episodic memory layer.

Hierarchy:
  memory/diary/          — raw session entries (JSONL, one per day)
  memory/reflections/    — distilled insights from diary (JSON, weekly)
  memory/rules/rules.md  — promoted procedural rules (injected into system prompt)
  memory/negative/       — failed assumptions, no-go patterns, hallucination log

Diary format (one JSON object per line in YYYY-MM-DD.jsonl):
  {
    "entry_id":      "diary_<8hex>",
    "session_id":    str,           # server session id
    "timestamp":     ISO str,       # UTC
    "thread_stem":   str | None,
    "query_summary": str,           # 1-2 sentences — what was asked
    "key_finding":   str | None,    # most important thing learned/done
    "open_questions": list[str],    # unresolved questions from this session
    "contradicts":   list[str],     # insight / rule ids this entry questions
    "model_used":    str | None,
    "tags":          list[str],
  }

Reflection format (memory/reflections/YYYY-MM-DD.json):
  {
    "reflection_id":  str,
    "created":        ISO str,
    "period_start":   "YYYY-MM-DD",
    "period_end":     "YYYY-MM-DD",
    "diary_count":    int,
    "patterns":       list[ReflectionPattern],
    "confidence":     float,        # 0.0-1.0; < 0.6 → excluded from injection
    "promoted_to_rule": bool,
  }

ReflectionPattern:
  {
    "pattern":        str,          # observed pattern / lesson
    "occurrences":    int,          # must be >= 3 to qualify for promotion
    "counterexample": str,          # mandatory before promotion
    "source_entries": list[str],    # entry_ids
  }
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT
from .constitutional import BOUNDS

# ── Directory setup ────────────────────────────────────────────────────────────

DIARY_DIR       = ROOT / "memory" / "diary"
REFLECTIONS_DIR = ROOT / "memory" / "reflections"
RULES_FILE      = ROOT / "memory" / "rules" / "rules.md"
NEGATIVE_DIR    = ROOT / "memory" / "negative"

for _d in (DIARY_DIR, REFLECTIONS_DIR, RULES_FILE.parent, NEGATIVE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── Diary: write ──────────────────────────────────────────────────────────────

def _today_diary_path() -> Path:
    return DIARY_DIR / f"{date.today().isoformat()}.jsonl"


def write_diary_entry(
    *,
    session_id: str,
    thread_stem: str | None = None,
    query_summary: str,
    key_finding: str | None = None,
    open_questions: list[str] | None = None,
    contradicts: list[str] | None = None,
    model_used: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Append one diary entry to today's JSONL file.

    Returns the entry_id of the new entry.

    Called at session end (or whenever a meaningful exchange completes).
    Do NOT call more than once per session unless the session has clearly
    distinct phases — diary is for episodic, not transactional, memory.
    """
    entry_id = f"diary_{uuid.uuid4().hex[:8]}"
    entry: dict[str, Any] = {
        "entry_id":      entry_id,
        "session_id":    session_id,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "thread_stem":   thread_stem,
        "query_summary": query_summary.strip(),
        "key_finding":   key_finding.strip() if key_finding else None,
        "open_questions": open_questions or [],
        "contradicts":   contradicts or [],
        "model_used":    model_used,
        "tags":          tags or [],
    }
    path = _today_diary_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry_id


# ── Diary: read ───────────────────────────────────────────────────────────────

def list_diary_entries(days: int = 30) -> list[dict]:
    """Return diary entries from the last `days` days, newest first."""
    entries: list[dict] = []
    for path in sorted(DIARY_DIR.glob("*.jsonl"), reverse=True):
        # Parse date from filename
        try:
            file_date = date.fromisoformat(path.stem)
        except ValueError:
            continue
        if (date.today() - file_date).days > days:
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    # Sort newest first (by timestamp)
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries


def get_recent_diary_for_briefing(n: int = BOUNDS.max_diary_briefing_entries) -> list[dict]:
    """Return the `n` most recent diary entries for morning briefing context.

    Strips fields that are too verbose for the briefing card.
    """
    entries = list_diary_entries(days=7)[:n]
    return [
        {
            "entry_id":      e["entry_id"],
            "timestamp":     e["timestamp"],
            "thread_stem":   e.get("thread_stem"),
            "query_summary": e.get("query_summary", ""),
            "key_finding":   e.get("key_finding"),
            "tags":          e.get("tags", []),
        }
        for e in entries
    ]


# ── Reflections ───────────────────────────────────────────────────────────────

def save_reflection(reflection: dict) -> str:
    """Persist a reflection JSON to memory/reflections/.

    Returns the reflection_id.
    `reflection` should match the ReflectionPattern schema above.
    Confidence < 0.6 is stored but NOT injected into system prompt.
    Occurrences < 3 per pattern → pattern is excluded from injection too.
    """
    reflection_id = reflection.get("reflection_id") or f"reflection_{uuid.uuid4().hex[:8]}"
    reflection["reflection_id"] = reflection_id
    reflection.setdefault("created", datetime.now(timezone.utc).isoformat())

    path = REFLECTIONS_DIR / f"{reflection_id}.json"
    path.write_text(json.dumps(reflection, ensure_ascii=False, indent=2))
    return reflection_id


def list_reflections(days: int = 90) -> list[dict]:
    """Return reflections from the last `days` days, newest first."""
    reflections: list[dict] = []
    cutoff = (datetime.now(timezone.utc).timestamp() - days * 86400)
    for path in REFLECTIONS_DIR.glob("*.json"):
        try:
            r = json.loads(path.read_text(encoding="utf-8"))
            created = r.get("created", "")
            if created:
                ts = datetime.fromisoformat(created).timestamp()
                if ts < cutoff:
                    continue
            reflections.append(r)
        except Exception:  # noqa: BLE001
            continue
    reflections.sort(key=lambda r: r.get("created", ""), reverse=True)
    return reflections


def get_injectable_reflections() -> list[dict]:
    """Return reflections that meet the injection criteria:
    - confidence >= BOUNDS.reflection_min_confidence
    - at least one pattern with occurrences >= BOUNDS.reflection_min_occurrences

    Used by system prompt builder.
    """
    result = []
    for r in list_reflections(days=BOUNDS.reflection_retention_days):
        if r.get("confidence", 0) < BOUNDS.reflection_min_confidence:
            continue
        injectable_patterns = [
            p for p in r.get("patterns", [])
            if p.get("occurrences", 0) >= BOUNDS.reflection_min_occurrences
            and p.get("counterexample")
        ]
        if injectable_patterns:
            result.append({**r, "patterns": injectable_patterns})
    return result


# ── Rules ─────────────────────────────────────────────────────────────────────

def load_rules_for_injection(max_tokens: int = BOUNDS.max_rules_injection_tokens) -> str:
    """Return rules.md content truncated to ~max_tokens (≈ chars/4).

    Only active rules are included. Called by system prompt builder.
    Approximate token cap: 500 tokens ≈ 2000 chars.
    """
    if not RULES_FILE.exists():
        return ""
    content = RULES_FILE.read_text(encoding="utf-8")
    # Real entries start AFTER the sentinel comment line.
    # Everything above that (header, format examples) is boilerplate.
    sentinel = "<!-- Reguły poniżej"
    if sentinel in content:
        after_sentinel = content.split(sentinel, 1)[1]
        # Strip the closing --> and any leading blank lines
        after_sentinel = re.sub(r"^.*?-->", "", after_sentinel, count=1, flags=re.DOTALL)
        rules_text = after_sentinel.strip()
    else:
        # Fallback: look for first actual rule_id entry that isn't inside a code block
        in_code_block = False
        active_lines: list[str] = []
        in_rule = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if stripped.startswith("- rule_id:"):
                in_rule = True
            if in_rule:
                active_lines.append(line)
        rules_text = "\n".join(active_lines).strip()
    if not rules_text:
        return ""

    # Truncate to approximate token budget
    max_chars = max_tokens * 4
    if len(rules_text) > max_chars:
        rules_text = rules_text[:max_chars] + "\n… (truncated)"

    return rules_text


# ── Negative memory: read helpers ─────────────────────────────────────────────

def load_negative_summary() -> dict[str, str]:
    """Return {filename: first_N_chars} for each negative memory file.

    Used in briefing to surface known failure patterns.
    Returns empty strings for missing files (not an error).
    """
    result: dict[str, str] = {}
    for fname in ("failed_assumptions.md", "no_go_patterns.md", "hallucination_patterns.md"):
        path = NEGATIVE_DIR / fname
        if path.exists():
            content = path.read_text(encoding="utf-8")
            # Return everything after the last "---" separator (the actual entries)
            parts = content.split("---")
            entries_section = parts[-1].strip() if len(parts) > 1 else ""
            result[fname] = entries_section[:BOUNDS.negative_excerpt_chars]
        else:
            result[fname] = ""
    return result


# ── Stats ─────────────────────────────────────────────────────────────────────

def diary_stats() -> dict[str, Any]:
    """Return basic statistics about the diary for the dashboard."""
    all_entries = list_diary_entries(days=365)
    total_entries = len(all_entries)
    diary_files = list(DIARY_DIR.glob("*.jsonl"))
    reflection_files = list(REFLECTIONS_DIR.glob("*.json"))
    has_rules = RULES_FILE.exists() and bool(load_rules_for_injection())

    tags: dict[str, int] = {}
    for e in all_entries:
        for t in e.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
    top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_diary_entries": total_entries,
        "diary_files":         len(diary_files),
        "reflection_files":    len(reflection_files),
        "has_active_rules":    has_rules,
        "top_tags":            top_tags,
        "last_entry":          all_entries[0].get("timestamp") if all_entries else None,
    }
