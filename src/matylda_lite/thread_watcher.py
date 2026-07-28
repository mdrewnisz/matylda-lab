"""Matylda Lab — ThreadWatcher + wbudowane handlery OnThreadWrite (v1.0).

Watcher:
  - Odpytuje library/threads/*.md co POLL_INTERVAL sekund
  - Wykrywa zmiany przez mtime
  - Odpala hook `thread.write` dla każdego zmienionego pliku
  - Zero dodatkowych zależności (brak watchdog)

Wbudowane handlery OnThreadWrite:
  1. _rebuild_search_index   — inwaliduje BM25 FTS5 po zapisie
  2. _update_thread_links    — aktualizuje data/thread_links.json

Reguła logowania: każdy hook = jedna linia w chronicle.jsonl.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import Counter
from pathlib import Path

from .config import ROOT
from .constitutional import BOUNDS
from .hooks import fire, on_event

log = logging.getLogger(__name__)

# ── Konfiguracja ─────────────────────────────────────────────────────────────

POLL_INTERVAL = BOUNDS.thread_watcher_poll_interval
_THREADS_DIR  = ROOT / "library" / "threads"
_LINKS_FILE   = ROOT / "data" / "thread_links.json"

# Minimalna długość słowa kluczowego
_MIN_KEYWORD_LEN = 5

# Stopwords PL + EN (najczęstsze słowa bez wartości semantycznej)
_STOPWORDS: frozenset[str] = frozenset({
    # PL
    "przez", "także", "które", "który", "która", "można", "będzie",
    "jednak", "tylko", "tego", "tych", "więc", "kiedy", "gdzie",
    "czego", "czyli", "sobie", "jeszcze", "między", "ponad",
    "każdy", "każda", "każde", "dlatego", "zawsze", "nigdy",
    "bardzo", "bardziej", "najbardziej", "wszystkich", "wszystko",
    "nowych", "takich", "takie", "takiego", "takiej",
    # EN
    "which", "where", "their", "there", "these", "those", "would",
    "could", "should", "about", "after", "before", "during", "while",
    "other", "every", "between", "because", "however", "although",
    "within", "without", "through", "against", "another", "whether",
    "further", "therefore", "research", "analysis", "system", "model",
    "approach", "method", "process", "result", "study", "topic",
})


# ── Watcher ─────────────────────────────────────────────────────────────────

class _ThreadWatcher:
    def __init__(self) -> None:
        self._mtimes: dict[Path, float] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_stale_scan: float = 0.0   # monotonic timestamp of last scan

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        # Snapshot aktualnych mtime — nie odpala hooków dla istniejących plików
        self._snapshot()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="matylda-thread-watcher",
        )
        self._thread.start()
        log.info(
            "ThreadWatcher uruchomiony — %s co %.1fs",
            _THREADS_DIR, POLL_INTERVAL,
        )

    def stop(self) -> None:
        self._stop_event.set()

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Internals ────────────────────────────────────────────────────────────

    def _snapshot(self) -> None:
        if not _THREADS_DIR.exists():
            return
        for p in _THREADS_DIR.glob("*.md"):
            try:
                self._mtimes[p] = p.stat().st_mtime
            except OSError:
                pass

    def _run(self) -> None:
        while not self._stop_event.wait(POLL_INTERVAL):
            self._check()
            self._maybe_stale_scan()

    def _maybe_stale_scan(self) -> None:
        """Run stale-thread scan if enough time has passed (default 24h)."""
        import time as _time  # local import to avoid module-level shadowing
        now = _time.monotonic()
        interval_secs = BOUNDS.stale_scan_interval_hours * 3600
        if now - self._last_stale_scan < interval_secs:
            return
        self._last_stale_scan = now
        try:
            from .stale_scanner import run_scan_and_save  # noqa: PLC0415
            from .chronicle import log_and_build          # noqa: PLC0415
            suggestions = run_scan_and_save()
            log_and_build(
                source="hook:stale_scan",
                event_type="stale_scan_complete",
                context_ref="thread_watcher",
                metadata={"suggestions": len(suggestions)},
            )
            if suggestions:
                log.info("stale_scan: %d suggestion(s) generated", len(suggestions))
        except Exception:  # noqa: BLE001
            log.exception("stale_scan failed")

    def _check(self) -> None:
        if not _THREADS_DIR.exists():
            return
        try:
            current: dict[Path, float] = {
                p: p.stat().st_mtime
                for p in _THREADS_DIR.glob("*.md")
                if p.is_file() and "archive" not in p.parts
            }
        except OSError as exc:
            log.warning("ThreadWatcher błąd skanowania: %s", exc)
            return

        changed = [p for p, mtime in current.items() if self._mtimes.get(p) != mtime]
        self._mtimes = current

        for p in changed:
            log.debug("ThreadWatcher: %s zmieniony → fire thread.write", p.stem)
            fire("thread.write", stem=p.stem, path=p)


# ── Singleton ────────────────────────────────────────────────────────────────

_watcher: _ThreadWatcher | None = None


def start_watcher() -> None:
    """Uruchom watcher jako daemon thread. Bezpieczne do wielokrotnego wywołania."""
    global _watcher  # noqa: PLW0603
    if _watcher is None:
        _watcher = _ThreadWatcher()
    _watcher.start()


def stop_watcher() -> None:
    """Zatrzymaj watcher (przy shutdown serwera)."""
    if _watcher:
        _watcher.stop()


def watcher_status() -> dict:
    """Stan watchera (dla /api/health/system)."""
    return {
        "running": _watcher.is_alive() if _watcher else False,
        "poll_interval": POLL_INTERVAL,
        "watched_dir": str(_THREADS_DIR),
    }


# ── Wbudowane handlery OnThreadWrite ─────────────────────────────────────────

@on_event("thread.write")
def _rebuild_search_index(stem: str, path: Path, **_) -> None:
    """Inwaliduj i przebuduj indeks BM25 po zapisie wątku."""
    try:
        from .search_index import rebuild_index    # noqa: PLC0415
        from .chronicle import log_and_build       # noqa: PLC0415

        count = rebuild_index()
        log_and_build(
            source="hook:thread.write",
            event_type="index_rebuild",
            context_ref=stem,
            metadata={"stem": stem, "docs_indexed": count},
        )
        log.info("hook:thread.write stem=%s → reindex(%d docs)", stem, count)
    except Exception:  # noqa: BLE001
        log.exception("hook:thread.write reindex failed dla %s", stem)


@on_event("thread.write")
def _update_thread_links(stem: str, path: Path, **_) -> None:
    """Zaktualizuj thread_links.json — powiązania semantyczne między wątkami."""
    try:
        from .chronicle import log_and_build  # noqa: PLC0415

        links = _compute_links_for(stem)
        _write_links_patch(stem, links)

        log_and_build(
            source="hook:thread.write",
            event_type="links_updated",
            context_ref=stem,
            metadata={"stem": stem, "connections": len(links)},
        )
        log.info(
            "hook:thread.write stem=%s → links_updated(%d connections)",
            stem, len(links),
        )
    except Exception:  # noqa: BLE001
        log.exception("hook:thread.write links failed dla %s", stem)


@on_event("thread.write")
def _register_thread_in_graph(stem: str, path: Path, **_) -> None:
    """v0.5: Auto-register thread as entity in knowledge graph, surface relation suggestions."""
    try:
        from .knowledge_graph import auto_register_thread, suggest_relations_from_links  # noqa: PLC0415
        from .chronicle import log_and_build  # noqa: PLC0415

        entity = auto_register_thread(stem)
        suggestions = suggest_relations_from_links(stem)

        log_and_build(
            source="hook:thread.write",
            event_type="graph_entity_registered",
            context_ref=stem,
            metadata={
                "entity_id":   entity.entity_id,
                "suggestions": len(suggestions),
            },
        )
        if suggestions:
            log.info(
                "hook:thread.write stem=%s → graph: %d relation suggestion(s)",
                stem, len(suggestions),
            )
    except Exception:  # noqa: BLE001
        log.exception("hook:thread.write graph registration failed dla %s", stem)


@on_event("response.done")
def _proactive_connections(stem: str | None = None, **_) -> None:
    """v0.5 section 2.2 — after response done: check semantic overlap, propose graph relations.

    Only runs when:
    - A thread stem was saved (save_as was set)
    - Attention budget is not exhausted
    - Similarity > BOUNDS.proactive_connection_threshold

    Proposals stored as graph entities (NOT auto-applied as relations — user confirms).
    """
    if not stem:
        return
    try:
        from .homeostasis import attention_status  # noqa: PLC0415
        if attention_status().get("over_budget", False):
            log.debug("response.done: attention over budget — skipping proactive connections")
            return

        from .knowledge_graph import (  # noqa: PLC0415
            auto_register_thread, suggest_relations_from_links, load_graph,
        )

        auto_register_thread(stem)
        suggestions = suggest_relations_from_links(
            stem,
            min_similarity=BOUNDS.proactive_connection_threshold,
        )

        for sug in suggestions:
            target_stem = sug["to_id"].removeprefix("thread:")
            if sug["to_id"] not in load_graph():
                auto_register_thread(target_stem)

        if suggestions:
            log.info(
                "response.done stem=%s → %d proactive connection suggestion(s)",
                stem, len(suggestions),
            )
            from .chronicle import log_and_build  # noqa: PLC0415
            log_and_build(
                source="hook:response.done",
                event_type="proactive_connections",
                context_ref=stem,
                metadata={"stem": stem, "suggestions": len(suggestions)},
            )
    except Exception:  # noqa: BLE001
        log.exception("response.done proactive connections failed dla %s", stem)


# ── Semantyczne powiązania wątków ─────────────────────────────────────────────

def _extract_keywords(text: str) -> Counter:
    """Wyciągnij słowa kluczowe z tekstu — słowa > MIN_KEYWORD_LEN, bez stopwords."""
    words = re.findall(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{" + str(_MIN_KEYWORD_LEN) + r",}", text.lower())
    return Counter(w for w in words if w not in _STOPWORDS)


def _read_thread_keywords(p: Path) -> Counter:
    """Wczytaj wątek i zwróć jego counter słów kluczowych."""
    try:
        if p.stat().st_size > 200 * 1024:   # pomijaj pliki > 200 KB
            return Counter()
        text = p.read_text(encoding="utf-8", errors="replace")
        return _extract_keywords(text)
    except OSError:
        return Counter()


def _compute_links_for(stem: str) -> list[dict]:
    """Oblicz powiązania semantyczne zmodyfikowanego wątku z innymi wątkami.

    Zwraca listę {"stem": ..., "score": N, "shared": [...top keywords...]},
    posortowaną malejąco po score. Zwraca tylko powiązania z score ≥ 2.
    """
    if not _THREADS_DIR.exists():
        return []

    changed_path = _THREADS_DIR / f"{stem}.md"
    if not changed_path.exists():
        return []

    changed_kw = _read_thread_keywords(changed_path)
    if not changed_kw:
        return []

    links: list[dict] = []
    for p in _THREADS_DIR.glob("*.md"):
        if p.stem == stem or "archive" in p.parts:
            continue
        other_kw = _read_thread_keywords(p)
        if not other_kw:
            continue

        # Iloczyn — wspólne słowa kluczowe, ważone min(count_a, count_b)
        shared = changed_kw & other_kw
        score = sum(shared.values())
        if score < 2:
            continue

        top_shared = [w for w, _ in shared.most_common(5)]
        links.append({
            "stem":   p.stem,
            "score":  score,
            "shared": top_shared,
        })

    links.sort(key=lambda x: x["score"], reverse=True)
    return links[:20]   # max 20 powiązań na wątek


def _write_links_patch(stem: str, links: list[dict]) -> None:
    """Zaktualizuj wpis `stem` w thread_links.json (atomic patch)."""
    _LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if _LINKS_FILE.exists():
        try:
            existing = json.loads(_LINKS_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            existing = {}

    existing[stem] = links
    _LINKS_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_thread_links(stem: str) -> list[dict]:
    """Zwróć powiązania dla wątku stem z thread_links.json."""
    if not _LINKS_FILE.exists():
        return []
    try:
        data = json.loads(_LINKS_FILE.read_text(encoding="utf-8"))
        return data.get(stem, [])
    except Exception:  # noqa: BLE001
        return []
