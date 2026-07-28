"""Knowledge artifact parser — YAML frontmatter + markdown sections.

Zaadaptowane z Matylda Full (knowledge_base/documents.py).
Standalone — zero zależności poza stdlib.

Przykład użycia:
    from matylda_lite.knowledge_artifact import load_knowledge_artifact
    doc = load_knowledge_artifact("library/docs/generated/moj_dokument.md")
    print(doc.artifact_title, doc.sections.keys())
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class KnowledgeArtifactDocument:
    """Parsed representation of a markdown document with optional YAML frontmatter."""
    path: str
    artifact_title: str
    artifact_kind: str | None
    workflow_kind: str | None
    status: str | None
    review_required: bool
    sources_used: tuple[str, ...]
    metadata: dict[str, object]
    bullet_fields: dict[str, str]
    sections: dict[str, str]
    body: str


def load_knowledge_artifact(path: str | Path) -> KnowledgeArtifactDocument:
    """Parse a markdown file with optional YAML frontmatter.

    Args:
        path: Path to the markdown file.

    Returns:
        KnowledgeArtifactDocument with parsed metadata, sections, bullet fields.

    Raises:
        ValueError: If file does not exist.
    """
    artifact_path = Path(path)
    if not artifact_path.exists():
        raise ValueError(f"Knowledge artifact does not exist: {artifact_path}")

    text = artifact_path.read_text(encoding="utf-8")
    frontmatter_text, body = _split_frontmatter(text)
    metadata = _parse_frontmatter(frontmatter_text)
    bullet_fields = _extract_top_bullets(body)
    sections = _extract_sections(body)

    return KnowledgeArtifactDocument(
        path=str(artifact_path),
        artifact_title=_extract_title(body) or artifact_path.stem,
        artifact_kind=_clean_optional_text(metadata.get("artifact_kind")),
        workflow_kind=_clean_optional_text(metadata.get("workflow_kind")),
        status=_clean_optional_text(metadata.get("status")),
        review_required=bool(metadata.get("review_required", False)),
        sources_used=tuple(str(item) for item in metadata.get("sources_used", []) if str(item).strip()),
        metadata=metadata,
        bullet_fields=bullet_fields,
        sections=sections,
        body=body,
    )


def parse_frontmatter(text: str) -> dict[str, object]:
    """Parse only the YAML frontmatter from a markdown string.

    Convenience function — returns empty dict if no frontmatter present.
    """
    frontmatter_text, _ = _split_frontmatter(text)
    return _parse_frontmatter(frontmatter_text)


def extract_sections(body: str) -> dict[str, str]:
    """Extract ## sections from markdown body text.

    Returns dict mapping section title → section content (stripped).
    """
    return _extract_sections(body)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    return "", text


def _parse_frontmatter(text: str) -> dict[str, object]:
    metadata: dict[str, object] = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if current_list_key and line.startswith("  - "):
            metadata.setdefault(current_list_key, []).append(line[4:].strip())
            continue
        current_list_key = None
        if ": " in line:
            key, value = line.split(": ", 1)
            metadata[key.strip()] = _parse_scalar(value)
            continue
        if line.endswith(":"):
            key = line[:-1].strip()
            metadata[key] = []
            current_list_key = key
    return metadata


def _extract_title(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _extract_top_bullets(body: str) -> dict[str, str]:
    bullet_fields: dict[str, str] = {}
    in_header = False
    for line in body.splitlines():
        if line.startswith("# "):
            in_header = True
            continue
        if not in_header:
            continue
        if line.startswith("## "):
            break
        if line.startswith("- ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            bullet_fields[key.strip()] = value.strip()
    return bullet_fields


def _extract_sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## (.+?)\s*$", body, flags=re.MULTILINE))
    if not matches:
        return {}
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[title] = body[start:end].strip()
    return sections


def _parse_scalar(value: str) -> object:
    text = value.strip()
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    return text


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
