"""Active project session context."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path

from .config import ROOT

_ACTIVE_FILE = ROOT / "library" / "projects" / "active_project.json"
_PROJECTS_DIR = ROOT / "library" / "projects"
_THREADS_DIR  = ROOT / "library" / "threads"

_MAX_TOTAL_CHARS = 6000
_MAX_THREAD_CHARS = 1000


def get_active_project() -> dict | None:
    """Read _ACTIVE_FILE, return dict or None if missing/invalid."""
    if not _ACTIVE_FILE.exists():
        return None
    try:
        return json.loads(_ACTIVE_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def set_active_project(project_id: str) -> dict | None:
    """Load project from projects dir, write active_project.json, return project dict."""
    proj_file = _PROJECTS_DIR / f"{project_id}.json"
    if not proj_file.exists():
        return None
    try:
        proj = json.loads(proj_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None

    _ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    active_data = {
        "project_id": project_id,
        "name": proj.get("name", project_id),
        "set_at": str(date.today()),
    }
    _ACTIVE_FILE.write_text(
        json.dumps(active_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return proj


def clear_active_project() -> None:
    """Delete _ACTIVE_FILE if it exists."""
    if _ACTIVE_FILE.exists():
        _ACTIVE_FILE.unlink()


def build_project_context_string() -> str:
    """Build a context string for the active project. Return '' if none."""
    active = get_active_project()
    if not active:
        return ""

    project_id = active.get("project_id", "")
    name       = active.get("name", project_id)

    # Load full project data
    proj_file = _PROJECTS_DIR / f"{project_id}.json"
    if not proj_file.exists():
        return ""
    try:
        proj = json.loads(proj_file.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return ""

    description = proj.get("description", "")
    thread_stems: list[str] = proj.get("threads", [])

    # Build header
    parts: list[str] = []
    header = f"=== AKTYWNY PROJEKT: {name} ==="
    if description:
        header += f"\n{description}"
    parts.append(header)

    # Thread titles summary
    thread_titles: list[str] = []
    thread_contents: list[tuple[str, str]] = []  # (title, content)

    for stem in thread_stems:
        for d in (_THREADS_DIR, _THREADS_DIR / "archive"):
            p = d / f"{stem}.md"
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8")
                    # Extract title from first heading or stem
                    title = stem
                    for line in content.splitlines():
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
                    thread_titles.append(title)
                    thread_contents.append((title, content))
                except Exception:  # noqa: BLE001
                    thread_titles.append(stem)
                break

    if thread_titles:
        parts.append("Wątki: " + ", ".join(thread_titles))

    # Thread content section
    if thread_contents:
        parts.append("=== TREŚĆ WĄTKÓW PROJEKTU ===")
        total_chars = sum(len(p) for p in parts)
        for title, content in thread_contents:
            section = f"--- {title} ---\n{content[:_MAX_THREAD_CHARS]}"
            if total_chars + len(section) > _MAX_TOTAL_CHARS:
                break
            parts.append(section)
            total_chars += len(section)

    result = "\n\n".join(parts)
    return result[:_MAX_TOTAL_CHARS]
