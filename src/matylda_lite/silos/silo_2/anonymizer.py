"""Regex-based PII anonymizer for Silo 2 (closed silo).

Replaces detected entities with reversible `[TYPE_N]` tokens.
No external calls — pure Python, no NLP dependencies.

Detected entity types:
  EMAIL   — user@domain.tld
  URL     — http(s):// links
  IP      — IPv4 addresses
  PHONE   — common phone number formats
  DATE    — ISO / slash / dot dates
  HEX     — long hex strings (hashes, API keys, UUIDs)
  APIKEY  — sk-ant-... / Bearer ... tokens

Usage:
    result = anonymize("Contact alice@example.com or 192.168.1.1")
    print(result.anonymized_text)   # "Contact [EMAIL_1] or [IP_1]"
    print(result.restore(result.anonymized_text))  # original text
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator


# ── Entity patterns (ordered: most specific first) ────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern]] = [
    # API / secret tokens — before generic hex/URL
    ("APIKEY", re.compile(
        r'\b(?:sk-ant-|sk-|Bearer\s+)[A-Za-z0-9\-_]{10,}',
        re.IGNORECASE,
    )),
    # Full URL
    ("URL", re.compile(
        r'https?://[^\s<>"\'`]+',
        re.IGNORECASE,
    )),
    # Email
    ("EMAIL", re.compile(
        r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
    )),
    # IPv4
    ("IP", re.compile(
        r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b',
    )),
    # Phone (international + US formats)
    ("PHONE", re.compile(
        r'\b(?:\+\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3}[\s\-]?\d{4,6}\b',
    )),
    # ISO / slash / dot dates
    ("DATE", re.compile(
        r'\b\d{4}[-/.]\d{2}[-/.]\d{2}\b'
        r'|\b\d{2}[-/.]\d{2}[-/.]\d{4}\b',
    )),
    # Long hex (32+ chars: MD5, SHA, UUIDs without dashes)
    ("HEX", re.compile(
        r'\b[0-9a-f]{32,64}\b',
        re.IGNORECASE,
    )),
]


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class AnonymizationResult:
    """Holds anonymized text, entity mapping, and statistics."""

    anonymized_text: str
    # placeholder → original value, e.g. "[EMAIL_1]" → "alice@example.com"
    entity_map: dict[str, str] = field(default_factory=dict)
    entity_count: int = 0
    types_found: list[str] = field(default_factory=list)

    def restore(self, text: str) -> str:
        """Replace placeholders back with original values."""
        for placeholder, original in self.entity_map.items():
            text = text.replace(placeholder, original)
        return text

    def summary(self) -> str:
        """Human-readable summary of what was anonymized."""
        if not self.entity_count:
            return "Brak wykrytych encji PII."
        counts: dict[str, int] = {}
        for p in self.entity_map:
            kind = p.split("_")[0].lstrip("[")
            counts[kind] = counts.get(kind, 0) + 1
        parts = [f"{k}: {v}" for k, v in sorted(counts.items())]
        return f"Zanonimizowano {self.entity_count} encji — " + ", ".join(parts)


# ── Core anonymizer ───────────────────────────────────────────────────────────

def anonymize(text: str) -> AnonymizationResult:
    """Scan *text* for PII patterns and replace with `[TYPE_N]` tokens.

    The replacement is deterministic within a single call:
    identical values always get the same placeholder.
    Counting is per entity type.

    Args:
        text: Raw input text (may contain PII).

    Returns:
        AnonymizationResult with anonymized_text and entity_map.
    """
    if not text or not text.strip():
        return AnonymizationResult(anonymized_text=text)

    # value → placeholder (ensures same value → same token within one call)
    value_to_placeholder: dict[str, str] = {}
    # type → running counter
    counters: dict[str, int] = {}

    result_text = text
    types_seen: set[str] = set()

    for entity_type, pattern in _PATTERNS:
        def _replace(m: re.Match, etype: str = entity_type) -> str:
            val = m.group(0)
            if val in value_to_placeholder:
                return value_to_placeholder[val]
            counters[etype] = counters.get(etype, 0) + 1
            placeholder = f"[{etype}_{counters[etype]}]"
            value_to_placeholder[val] = placeholder
            return placeholder

        result_text = pattern.sub(_replace, result_text)
        if counters.get(entity_type, 0) > 0:
            types_seen.add(entity_type)

    # Build reverse map: placeholder → original
    entity_map = {v: k for k, v in value_to_placeholder.items()}
    total = sum(counters.values())

    return AnonymizationResult(
        anonymized_text=result_text,
        entity_map=entity_map,
        entity_count=total,
        types_found=sorted(types_seen),
    )


def anonymize_dict(data: dict) -> tuple[dict, AnonymizationResult]:
    """Recursively anonymize all string values in *data*.

    Non-string values (ints, lists, nested dicts) are traversed recursively.
    Returns (anonymized_dict, combined_result).
    """
    import json
    serialized = json.dumps(data, ensure_ascii=False)
    result = anonymize(serialized)
    try:
        anon_data = json.loads(result.anonymized_text)
    except Exception:  # noqa: BLE001
        anon_data = {"_raw": result.anonymized_text}
    return anon_data, result
