"""Library manager — threads and projects.

Threads: markdown files in library/threads/ parsed for metadata.
Projects: JSON files in library/projects/ grouping threads.
Archive: move to library/threads/archive/ or library/projects/archive/.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date
from pathlib import Path

from .config import ROOT

_THREADS_DIR         = ROOT / "library" / "threads"
_THREADS_ARCHIVE_DIR = ROOT / "library" / "threads" / "archive"
_PROJECTS_DIR        = ROOT / "library" / "projects"
_PROJECTS_ARCHIVE_DIR = ROOT / "library" / "projects" / "archive"

for _d in (_THREADS_ARCHIVE_DIR, _PROJECTS_DIR, _PROJECTS_ARCHIVE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── Threads ───────────────────────────────────────────────────────────────────

def _parse_thread_file(p: Path) -> dict:
    """Extract metadata from a thread markdown file."""
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return {}

    # Title from first # heading
    title_m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else p.stem.replace("_", " ").title()

    # Metadata section key-value pairs
    meta: dict = {"filename": p.name, "stem": p.stem, "title": title}
    meta_section = re.search(
        r"##\s+Metadata\s*\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL | re.IGNORECASE
    )
    if meta_section:
        for line in meta_section.group(1).splitlines():
            m = re.match(r"-\s+(\w[\w\s]+):\s*(.+)", line.strip())
            if m:
                key = m.group(1).strip().lower().replace(" ", "_")
                meta[key] = m.group(2).strip()

    # Status from active desk
    meta.setdefault("status", "library")
    meta.setdefault("domain", "—")
    meta.setdefault("value", "—")
    meta.setdefault("last_updated", "—")
    return meta


def read_thread(stem: str) -> str:
    """Return full markdown content of a thread file by stem."""
    p = _THREADS_DIR / f"{stem}.md"
    if not p.exists():
        p = _THREADS_ARCHIVE_DIR / f"{stem}.md"
    if not p.exists():
        raise FileNotFoundError(f"Thread '{stem}' nie znaleziony")
    return p.read_text(encoding="utf-8")


def list_threads(include_archived: bool = False) -> list[dict]:
    """Return all thread metadata dicts, sorted by last_updated desc."""
    threads = []
    for p in _THREADS_DIR.glob("*.md"):
        if p.name == "THREAD_INDEX.md":
            continue
        t = _parse_thread_file(p)
        if t:
            t["archived"] = False
            threads.append(t)

    if include_archived:
        for p in _THREADS_ARCHIVE_DIR.glob("*.md"):
            t = _parse_thread_file(p)
            if t:
                t["archived"] = True
                threads.append(t)

    return sorted(threads, key=lambda x: x.get("last_updated", ""), reverse=True)


def archive_thread(filename: str) -> bool:
    """Move thread .md to archive. Returns True on success."""
    src = _THREADS_DIR / filename
    if not src.exists():
        return False
    dst = _THREADS_ARCHIVE_DIR / filename
    src.rename(dst)

    # Also remove from ACTIVE_THREADS.md if present
    _remove_from_active_desk(filename)
    return True


def restore_thread(filename: str) -> bool:
    src = _THREADS_ARCHIVE_DIR / filename
    if not src.exists():
        return False
    (src).rename(_THREADS_DIR / filename)
    return True


def append_to_thread(stem: str, section_title: str, content: str) -> dict:
    """Append a new markdown section to a thread file.

    Adds a horizontal rule, a `## section_title` heading with datestamp,
    and the content. Updates `last_updated` in the Metadata block.

    Returns:
        {"ok": True, "section_added": section_title, "updated_at": today}

    Raises:
        FileNotFoundError: if the thread does not exist.
    """
    p = _THREADS_DIR / f"{stem}.md"
    if not p.exists():
        raise FileNotFoundError(f"Thread '{stem}' nie znaleziony")

    today = str(date.today())
    existing = p.read_text(encoding="utf-8").rstrip()
    section = f"\n\n---\n\n## {section_title}\n\n> {today}\n\n{content}\n"
    p.write_text(existing + section, encoding="utf-8")

    # Update last_updated in Metadata block if present
    text = p.read_text(encoding="utf-8")
    updated = re.sub(
        r"(- last_updated:\s*)(\S+)",
        lambda m: m.group(1) + today,
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    if updated != text:
        p.write_text(updated, encoding="utf-8")

    return {"ok": True, "section_added": section_title, "updated_at": today}


_VALID_STATUSES = frozenset({"active", "frozen", "library", "canonical"})


def set_thread_status(stem: str, status: str) -> bool:
    """Set the Status field in a thread's Metadata section.

    If the Status line already exists it is updated in-place.
    If no Metadata section exists, the function still tries a top-level
    `Status:` line.

    Returns:
        True  — file updated
        False — file not found

    Raises:
        ValueError: for unrecognised status values.
    """
    if status not in _VALID_STATUSES:
        raise ValueError(f"Nieprawidłowy status '{status}'. Dozwolone: {sorted(_VALID_STATUSES)}")

    p = _THREADS_DIR / f"{stem}.md"
    if not p.exists():
        return False

    text = p.read_text(encoding="utf-8")

    # Try updating an existing `- Status: <value>` line in Metadata
    new_text, n = re.subn(
        r"(- Status:\s*)(\S+)",
        lambda m: m.group(1) + status,
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    if n == 0:
        # Fall back: bare `Status: <value>` line
        new_text, n = re.subn(
            r"(^Status:\s*)(\S+)",
            lambda m: m.group(1) + status,
            text,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    if n == 0:
        # No Status line — inject after ## Metadata heading
        new_text = re.sub(
            r"(##\s+Metadata\s*\n)",
            r"\g<1>- Status: " + status + "\n",
            text,
            count=1,
            flags=re.IGNORECASE,
        )

    p.write_text(new_text, encoding="utf-8")
    return True


def _remove_from_active_desk(filename: str) -> None:
    active_file = ROOT / "desk" / "ACTIVE_THREADS.md"
    if not active_file.exists():
        return
    stem = Path(filename).stem
    lines = active_file.read_text(encoding="utf-8").splitlines()
    filtered = [l for l in lines if stem not in l]
    active_file.write_text("\n".join(filtered) + "\n", encoding="utf-8")


# ── Projects ──────────────────────────────────────────────────────────────────

def list_projects(include_archived: bool = False) -> list[dict]:
    projects = []
    for p in _PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["archived"] = False
            projects.append(data)
        except Exception:
            pass
    if include_archived:
        for p in _PROJECTS_ARCHIVE_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                data["archived"] = True
                projects.append(data)
            except Exception:
                pass
    return sorted(projects, key=lambda x: x.get("created", ""), reverse=True)


def create_project(name: str, description: str = "", threads: list[str] | None = None) -> dict:
    pid = f"proj_{uuid.uuid4().hex[:10]}"
    project = {
        "id": pid,
        "name": name.strip(),
        "description": description.strip(),
        "threads": threads or [],
        "status": "active",
        "created": str(date.today()),
        "last_updated": str(date.today()),
    }
    p = _PROJECTS_DIR / f"{pid}.json"
    p.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
    return project


def archive_project(project_id: str) -> bool:
    src = _PROJECTS_DIR / f"{project_id}.json"
    if not src.exists():
        return False
    dst = _PROJECTS_ARCHIVE_DIR / f"{project_id}.json"
    src.rename(dst)
    return True


def restore_project(project_id: str) -> bool:
    src = _PROJECTS_ARCHIVE_DIR / f"{project_id}.json"
    if not src.exists():
        return False
    src.rename(_PROJECTS_DIR / f"{project_id}.json")
    return True


def add_thread_to_project(project_id: str, thread_stem: str) -> bool:
    p = _PROJECTS_DIR / f"{project_id}.json"
    if not p.exists():
        return False
    data = json.loads(p.read_text(encoding="utf-8"))
    if thread_stem not in data["threads"]:
        data["threads"].append(thread_stem)
        data["last_updated"] = str(date.today())
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return True


def remove_thread_from_project(project_id: str, thread_stem: str) -> bool:
    p = _PROJECTS_DIR / f"{project_id}.json"
    if not p.exists():
        return False
    data = json.loads(p.read_text(encoding="utf-8"))
    data["threads"] = [t for t in data["threads"] if t != thread_stem]
    data["last_updated"] = str(date.today())
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return True
