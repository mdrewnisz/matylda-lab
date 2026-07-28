"""v0.7 — SQLite FTS5 search index for cross-source semantic search.

Indexes: threads, memory insights, memory candidates, notebooks, attached/generated docs, artifacts.
Uses BM25 ranking built into FTS5 for relevance scoring.

The index is in-memory by default, rebuilt on first search or when explicitly triggered.
Rebuild is fast (<50ms for hundreds of documents) since we scan local files.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from .config import ROOT
from .constitutional import BOUNDS

# ── Index configuration ─────────────────────────────────────────────────────

_MAX_FILE_SIZE = BOUNDS.search_max_file_size_kb * 1024

# (glob_pattern relative to ROOT, source_type)
_SCAN_SOURCES: list[tuple[str, str]] = [
    ("library/threads/*.md",               "thread"),
    ("library/docs/attached/*.md",         "doc"),
    ("library/docs/attached/*.txt",        "doc"),
    ("library/docs/attached/*.json",       "doc"),
    ("library/docs/attached/*.pdf",        "doc"),
    ("library/docs/generated/*.md",        "doc"),
    ("artifacts/*.md",                     "artifact"),
    ("memory/insights/*.json",             "insight"),
    ("memory/candidates/*.json",           "candidate"),
    # v0.4 memory tiers
    ("memory/diary/*.jsonl",               "diary"),
    ("memory/reflections/*.json",          "reflection"),
    ("memory/rules/rules.md",              "rules"),
    ("memory/negative/*.md",               "negative"),
    # v0.5 knowledge graph
    ("data/knowledge_graph.json",          "knowledge_graph"),
]

# ── Module state ─────────────────────────────────────────────────────────────

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()
_last_build: float = 0
_INDEX_TTL = BOUNDS.search_index_ttl_seconds


# ── File reading helpers ─────────────────────────────────────────────────────

def _read_file_content(p: Path) -> tuple[str, str, str]:
    """Read file and return (title, body_text, domain).

    For JSON files (insights/candidates), extract structured fields.
    For markdown, extract first heading as title.
    """
    try:
        if p.stat().st_size > _MAX_FILE_SIZE:
            return ("", "", "")
        raw = p.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ("", "", "")

    title = p.stem.replace("_", " ").replace("-", " ").title()
    domain = ""
    body = raw

    if p.suffix.lower() == ".jsonl":
        # Diary: one JSON object per line — concatenate searchable fields
        parts: list[str] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if isinstance(entry, dict):
                    for field in ("query_summary", "key_finding", "open_questions",
                                  "tags", "thread_stem"):
                        val = entry.get(field)
                        if isinstance(val, list):
                            parts.append(" ".join(str(v) for v in val))
                        elif val:
                            parts.append(str(val))
            except Exception:  # noqa: BLE001
                parts.append(line)
        body = " ".join(parts)
        title = f"Diary {p.stem}"
        domain = "diary"
    elif p.suffix.lower() == ".json":
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                # knowledge_graph.json — special structure
                if "entities" in d and isinstance(d["entities"], dict):
                    body_parts: list[str] = []
                    for eid, edata in d["entities"].items():
                        if isinstance(edata, dict):
                            body_parts.append(edata.get("label", ""))
                            body_parts.append(edata.get("description", ""))
                            body_parts.extend(edata.get("tags", []))
                            for rel in edata.get("relations", []):
                                if isinstance(rel, dict):
                                    body_parts.append(rel.get("rel_type", ""))
                                    body_parts.append(rel.get("note", ""))
                    body = " ".join(filter(None, body_parts))
                    title = "Knowledge Graph"
                    domain = "knowledge_graph"
                else:
                    title = d.get("topic", "") or d.get("title", "") or title
                    body_parts = []
                    for field in ("content", "topic", "note", "linked_thread",
                                  "pattern", "query_summary", "key_finding"):
                        val = d.get(field)
                        if val:
                            body_parts.append(str(val))
                    # reflections: extract patterns list
                    for pat in d.get("patterns", []):
                        if isinstance(pat, dict):
                            body_parts.append(pat.get("pattern", ""))
                            body_parts.append(pat.get("counterexample", ""))
                    body = " ".join(filter(None, body_parts))
                    domain = d.get("kind", "") or d.get("domain", "") or d.get("reflection_id", "")
        except Exception:  # noqa: BLE001
            pass
    elif p.suffix.lower() == ".md":
        # Extract first heading
        for line in raw.splitlines()[:10]:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
        # Extract domain from metadata
        for line in raw.splitlines()[:20]:
            if line.strip().lower().startswith("- domain:"):
                domain = line.split(":", 1)[1].strip()
                break

    return (title, body[:50_000], domain)


# ── Index management ─────────────────────────────────────────────────────────

def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS search_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE search_fts USING fts5(
            title,
            body,
            source_type,
            domain,
            path_rel,
            name,
            tokenize = 'unicode61 remove_diacritics 2'
        )
    """)


def _build_index(conn: sqlite3.Connection) -> int:
    """Scan all sources and populate FTS5 index. Returns document count."""
    _create_tables(conn)
    count = 0

    for glob_pattern, source_type in _SCAN_SOURCES:
        for p in ROOT.glob(glob_pattern):
            if "archive" in p.parts or not p.is_file():
                continue
            title, body, domain = _read_file_content(p)
            if not body.strip():
                continue
            path_rel = str(p.relative_to(ROOT))
            name = p.stem
            conn.execute(
                "INSERT INTO search_fts (title, body, source_type, domain, path_rel, name) VALUES (?, ?, ?, ?, ?, ?)",
                (title, body, source_type, domain, path_rel, name),
            )
            count += 1

    # Also index silo notebooks if they exist
    for silo_dir in (ROOT / "silos").glob("*/notebooks"):
        for nb_file in silo_dir.glob("*.md"):
            if not nb_file.is_file():
                continue
            title, body, domain = _read_file_content(nb_file)
            if not body.strip():
                continue
            silo_id = nb_file.parent.parent.name
            path_rel = str(nb_file.relative_to(ROOT))
            conn.execute(
                "INSERT INTO search_fts (title, body, source_type, domain, path_rel, name) VALUES (?, ?, ?, ?, ?, ?)",
                (title, body, f"notebook_{silo_id}", domain, path_rel, nb_file.stem),
            )
            count += 1

    conn.commit()
    return count


def _get_conn() -> sqlite3.Connection:
    """Get or create the search index connection, rebuilding if stale."""
    global _conn, _last_build  # noqa: PLW0603
    now = time.monotonic()

    if _conn is not None and (now - _last_build) < _INDEX_TTL:
        return _conn

    with _lock:
        # Double-check after acquiring lock
        if _conn is not None and (now - _last_build) < _INDEX_TTL:
            return _conn

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _build_index(conn)
        _conn = conn
        _last_build = time.monotonic()
        return conn


def rebuild_index() -> int:
    """Force rebuild of the search index. Returns document count."""
    global _conn, _last_build  # noqa: PLW0603
    with _lock:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        count = _build_index(conn)
        _conn = conn
        _last_build = time.monotonic()
        return count


# ── Query ────────────────────────────────────────────────────────────────────

def _fts5_escape(query: str) -> str:
    """Escape query for FTS5 — wrap each token as a prefix search."""
    tokens = query.strip().split()
    if not tokens:
        return ""
    # Each word becomes a prefix match; words are AND-ed
    escaped = []
    for t in tokens:
        # Remove FTS5 special chars
        clean = t.replace('"', '').replace("'", "").replace("*", "").replace("(", "").replace(")", "")
        if clean:
            escaped.append(f'"{clean}"*')
    return " ".join(escaped)


def fts_search(query: str, limit: int = 25, source_filter: str | None = None) -> list[dict]:
    """Search across all indexed sources using BM25 ranking.

    Args:
        query: User search query.
        limit: Max results.
        source_filter: Optional — only return results of this source_type.

    Returns:
        List of result dicts with: type, name, path_rel, title, snippet, score, domain.
    """
    if not query or not query.strip():
        return []

    conn = _get_conn()
    fts_query = _fts5_escape(query)
    if not fts_query:
        return []

    try:
        if source_filter:
            rows = conn.execute(
                """SELECT name, path_rel, source_type, title, domain,
                          snippet(search_fts, 1, '»', '«', '…', 40) AS snippet,
                          bm25(search_fts) AS rank
                   FROM search_fts
                   WHERE search_fts MATCH ? AND source_type = ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts_query, source_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT name, path_rel, source_type, title, domain,
                          snippet(search_fts, 1, '»', '«', '…', 40) AS snippet,
                          bm25(search_fts) AS rank
                   FROM search_fts
                   WHERE search_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts_query, limit),
            ).fetchall()
    except sqlite3.OperationalError:
        # Fallback: if FTS5 query fails (e.g. special chars), return empty
        return []

    results = []
    for row in rows:
        # BM25 returns negative scores (lower = better match)
        score = -row["rank"] if row["rank"] is not None else 0
        snippet = row["snippet"] or ""
        # Clean snippet markers
        snippet = snippet.replace("»", "**").replace("«", "**")

        results.append({
            "type": row["source_type"],
            "name": row["name"],
            "path_rel": row["path_rel"],
            "title": row["title"] or row["name"],
            "snippet": snippet,
            "score": round(score, 6),
            "domain": row["domain"] or "",
        })

    return results


def index_stats() -> dict:
    """Return stats about the current index."""
    conn = _get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM search_fts").fetchone()[0]
    except Exception:  # noqa: BLE001
        count = 0

    type_counts: dict[str, int] = {}
    try:
        for row in conn.execute("SELECT source_type, COUNT(*) as cnt FROM search_fts GROUP BY source_type"):
            type_counts[row["source_type"]] = row["cnt"]
    except Exception:  # noqa: BLE001
        pass

    return {
        "total_documents": count,
        "by_type": type_counts,
        "ttl_seconds": _INDEX_TTL,
        "age_seconds": round(time.monotonic() - _last_build, 1) if _last_build > 0 else None,
    }
