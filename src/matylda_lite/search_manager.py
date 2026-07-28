"""Full-text search across library, artifacts, docs, memory.

v0.7: Upgraded to SQLite FTS5 with BM25 ranking for relevance-scored results.
Falls back to simple substring search if FTS5 fails.
"""
from __future__ import annotations


def search(query: str, limit: int = 25, source_filter: str | None = None) -> list[dict]:
    """Search all indexed sources. Returns results sorted by BM25 relevance."""
    try:
        from .search_index import fts_search  # noqa: PLC0415
        return fts_search(query, limit=limit, source_filter=source_filter)
    except Exception:  # noqa: BLE001
        # Fallback to simple search if FTS5 module fails
        return _fallback_search(query, limit)


def _fallback_search(query: str, limit: int = 20) -> list[dict]:
    """Simple substring-based fallback search."""
    import json  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    from .config import ROOT  # noqa: PLC0415

    words = [w for w in query.lower().split() if len(w) > 1]
    if not words:
        return []

    _SCAN_LOCATIONS = [
        ("library/threads/*.md",               "thread"),
        ("library/docs/attached/*.md",         "doc"),
        ("library/docs/generated/*.md",        "doc"),
        ("artifacts/*.md",                     "artifact"),
        ("memory/insights/*.json",             "insight"),
    ]

    results: list[dict] = []
    for glob_pattern, result_type in _SCAN_LOCATIONS:
        for p in ROOT.glob(glob_pattern):
            if "archive" in p.parts or not p.is_file():
                continue
            try:
                if p.stat().st_size > 200_000:
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue

            lower_text = text.lower()
            score = sum(lower_text.count(w) for w in words)
            if score == 0:
                continue

            # Extract snippet
            snippet = ""
            for w in words:
                idx = lower_text.find(w)
                if idx != -1:
                    start = max(0, idx - 40)
                    end = min(len(text), start + 150)
                    snippet = text[start:end].strip()
                    if start > 0:
                        snippet = "…" + snippet
                    break
            if not snippet:
                snippet = text[:150].strip()

            path_rel = str(p.relative_to(ROOT))
            results.append({
                "type": result_type,
                "name": p.stem,
                "path_rel": path_rel,
                "title": p.stem.replace("_", " ").replace("-", " ").title(),
                "snippet": snippet,
                "score": score,
                "domain": "",
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
