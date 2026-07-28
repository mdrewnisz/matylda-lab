"""Document library manager for Matylda Lab.

Manages three document sources:
- library/docs/attached/  — user-uploaded files
- library/docs/generated/ — files Matylda creates explicitly
- artifacts/              — files auto-saved by secretary

v0.3e: expose load_knowledge_artifact() — structured YAML frontmatter parser.
"""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from pathlib import Path

from .config import ROOT
from .knowledge_artifact import (  # noqa: F401  re-exported
    KnowledgeArtifactDocument,
    load_knowledge_artifact,
    parse_frontmatter,
    extract_sections,
)
from .ocr import OCR_IMAGE_SUFFIXES, recognize_file

DOCS_ATTACHED_DIR  = ROOT / "library" / "docs" / "attached"
DOCS_GENERATED_DIR = ROOT / "library" / "docs" / "generated"
ARTIFACTS_DIR      = ROOT / "artifacts"

# Create dirs on import
for _d in (DOCS_ATTACHED_DIR, DOCS_GENERATED_DIR,
           DOCS_ATTACHED_DIR / "archive", DOCS_GENERATED_DIR / "archive"):
    _d.mkdir(parents=True, exist_ok=True)


def extract_text_details(path: Path) -> tuple[str, str, str | None]:
    """Return extracted text, method and an optional extraction error."""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pdf_error: str | None = None
        try:
            from pdfminer.high_level import extract_text as pdf_extract  # type: ignore
            text = pdf_extract(str(path))
            if _has_meaningful_text(text):
                return text[:30000], "pdf_text", None
        except ImportError:
            text = ""
        except Exception as exc:  # noqa: BLE001
            text = ""
            pdf_error = f"Błąd ekstrakcji PDF: {exc}"
        else:
            pdf_error = None

        result = recognize_file(path)
        if result.text:
            return result.text, result.engine or "ocr", None
        error = result.error or pdf_error or "PDF nie zawiera czytelnego tekstu."
        return "", "failed", error

    if suffix in OCR_IMAGE_SUFFIXES:
        result = recognize_file(path)
        if result.text:
            return result.text, result.engine or "ocr", None
        return "", "failed", result.error or "OCR nie wykrył czytelnego tekstu."

    if suffix == ".json":
        try:
            data = json.loads(path.read_bytes())
            text = json.dumps(data, ensure_ascii=False, indent=2)
            return text[:30000], "json", None
        except Exception:  # noqa: BLE001
            pass

    # .md, .txt, and anything else — try utf-8
    try:
        text = path.read_text(encoding="utf-8")
        return text[:30000], "text", None
    except UnicodeDecodeError:
        return "", "failed", f"Plik binarny bez obsługi ekstrakcji: {path.suffix}"


def extract_text(path: Path) -> str:
    """Extract plain text from a file. Limit to 30k chars."""
    text, _method, error = extract_text_details(path)
    return text if text else f"[{error or 'Nie udało się wyekstrahować tekstu'}]"


def _has_meaningful_text(text: str | None) -> bool:
    if not text:
        return False
    letters_and_digits = sum(char.isalnum() for char in text)
    words = text.split()
    return letters_and_digits >= 40 and len(words) >= 5


def _doc_dict(path: Path, source: str, archived: bool = False) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "path_rel": str(path.relative_to(ROOT)),
        "source": source,
        "size_chars": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "archived": archived,
    }


def list_docs() -> list[dict]:
    """Scan all three dirs and return list of doc dicts sorted by last_modified desc."""
    docs: list[dict] = []

    # Attached (active + archive)
    for p in DOCS_ATTACHED_DIR.iterdir():
        if p.is_file():
            docs.append(_doc_dict(p, "attached", archived=False))
    arch_att = DOCS_ATTACHED_DIR / "archive"
    if arch_att.exists():
        for p in arch_att.iterdir():
            if p.is_file():
                docs.append(_doc_dict(p, "attached", archived=True))

    # Generated (active + archive)
    for p in DOCS_GENERATED_DIR.iterdir():
        if p.is_file():
            docs.append(_doc_dict(p, "generated", archived=False))
    arch_gen = DOCS_GENERATED_DIR / "archive"
    if arch_gen.exists():
        for p in arch_gen.iterdir():
            if p.is_file():
                docs.append(_doc_dict(p, "generated", archived=True))

    # Artifacts
    if ARTIFACTS_DIR.exists():
        for p in ARTIFACTS_DIR.iterdir():
            if p.is_file():
                docs.append(_doc_dict(p, "artifact", archived=False))

    docs.sort(key=lambda d: d["last_modified"], reverse=True)
    return docs


def save_doc(name: str, content: str, source: str = "generated") -> dict:
    """Save content to DOCS_GENERATED_DIR/name with a header. Return doc dict."""
    today = date.today().isoformat()
    header = f"# {name}\n\n_Utworzono: {today} · Źródło: {source}_\n\n---\n\n"
    full = header + content

    path = DOCS_GENERATED_DIR / name
    path.write_text(full, encoding="utf-8")
    return _doc_dict(path, "generated", archived=False)


def save_uploaded(filename: str, raw_bytes: bytes) -> dict:
    """Save raw bytes to DOCS_ATTACHED_DIR/filename. Return doc dict with extracted_text."""
    path = DOCS_ATTACHED_DIR / filename
    path.write_bytes(raw_bytes)
    text, method, error = extract_text_details(path)
    d = _doc_dict(path, "attached", archived=False)
    d["extracted_text"] = text
    d["extraction_method"] = method
    d["extraction_error"] = error
    return d


def read_doc_content(path_rel: str) -> str:
    """Read and return text content of a doc given its path relative to ROOT."""
    path = ROOT / path_rel
    if not path.exists():
        return "[Plik nie istnieje]"
    return extract_text(path)


def archive_doc(path_rel: str) -> bool:
    """Move doc to appropriate archive subdir. Return True on success."""
    try:
        path = ROOT / path_rel
        if not path.exists():
            return False

        # Determine archive directory
        try:
            rel_to_attached = path.relative_to(DOCS_ATTACHED_DIR)
            archive_dir = DOCS_ATTACHED_DIR / "archive"
        except ValueError:
            try:
                rel_to_generated = path.relative_to(DOCS_GENERATED_DIR)
                archive_dir = DOCS_GENERATED_DIR / "archive"
            except ValueError:
                # Artifact or unknown — put in generated archive
                archive_dir = DOCS_GENERATED_DIR / "archive"

        archive_dir.mkdir(parents=True, exist_ok=True)
        dest = archive_dir / path.name

        # Avoid overwrite collision
        if dest.exists():
            stem = path.stem
            suffix = path.suffix
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            dest = archive_dir / f"{stem}_{ts}{suffix}"

        shutil.move(str(path), str(dest))
        return True
    except Exception:  # noqa: BLE001
        return False
