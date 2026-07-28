"""Export: ZIP bundles, polished Markdown, self-contained share HTML.

v0.8 — three export modes:
  1. Polished MD:      thread → clean markdown with YAML frontmatter + ToC
  2. Research bundle:  thread + related insights/traces/artifacts/docs/timeline → ZIP
  3. Share HTML:       self-contained HTML with embedded CSS, no server needed
  4. Legacy ZIP:       simple ZIP (v0.4 compat)
"""
from __future__ import annotations

import html as html_mod
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .config import ROOT
from .library_manager import list_threads


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Polished Markdown
# ═══════════════════════════════════════════════════════════════════════════════

def export_polished_md(stem: str) -> str:
    """Return a polished Markdown string with YAML frontmatter, ToC, and clean body.

    Args:
        stem: thread filename stem (no .md).

    Returns:
        UTF-8 Markdown string ready for publication.
    """
    thread_path = _find_thread(stem)
    raw = thread_path.read_text(encoding="utf-8")

    meta = _parse_thread_metadata(raw, stem)
    body = _clean_body(raw)
    toc = _build_toc(body)
    frontmatter = _build_frontmatter(meta)

    parts = [frontmatter, ""]
    if toc:
        parts.append("## Spis treści\n")
        parts.append(toc)
        parts.append("")
    parts.append(body)

    # Footer
    parts.append("")
    parts.append("---")
    parts.append(f"*Wyeksportowano z Matylda Lab • {_now_iso()}*")

    return "\n".join(parts)


def _build_frontmatter(meta: dict) -> str:
    """Build YAML frontmatter block."""
    lines = ["---"]
    for key in ("title", "domain", "status", "created", "last_updated", "tags"):
        if key in meta and meta[key] and meta[key] != "—":
            val = meta[key]
            if isinstance(val, list):
                lines.append(f"{key}:")
                for item in val:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {val}")
    lines.append(f"exported: {_now_iso()}")
    lines.append("generator: Matylda Lab v1.2")
    lines.append("---")
    return "\n".join(lines)


def _build_toc(body: str) -> str:
    """Generate a Markdown table of contents from ## headings."""
    toc_lines = []
    for m in re.finditer(r"^(#{2,3})\s+(.+)$", body, re.MULTILINE):
        level = len(m.group(1)) - 2  # ## = 0, ### = 1
        title = m.group(2).strip()
        anchor = re.sub(r"[^\w\s-]", "", title.lower()).replace(" ", "-")
        indent = "  " * level
        toc_lines.append(f"{indent}- [{title}](#{anchor})")
    return "\n".join(toc_lines)


def _clean_body(raw: str) -> str:
    """Strip YAML frontmatter and normalise whitespace."""
    # Remove existing frontmatter if present
    body = re.sub(r"^---\n.*?^---\n", "", raw, count=1, flags=re.DOTALL | re.MULTILINE)
    # Collapse 3+ newlines into 2
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _parse_thread_metadata(raw: str, stem: str) -> dict:
    """Extract metadata from thread markdown."""
    meta: dict = {"stem": stem}

    # Title
    title_m = re.search(r"^#\s+(.+)", raw, re.MULTILINE)
    meta["title"] = title_m.group(1).strip() if title_m else stem.replace("_", " ").title()

    # Metadata section
    sec = re.search(r"##\s+Metadata\s*\n(.*?)(?=\n##\s|\Z)", raw, re.DOTALL | re.IGNORECASE)
    if sec:
        for line in sec.group(1).splitlines():
            m = re.match(r"-\s+(\w[\w\s]+):\s*(.+)", line.strip())
            if m:
                key = m.group(1).strip().lower().replace(" ", "_")
                meta[key] = m.group(2).strip()

    meta.setdefault("status", "active")
    meta.setdefault("domain", "")
    return meta


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  Research Bundle (ZIP)
# ═══════════════════════════════════════════════════════════════════════════════

def export_research_bundle(stem: str) -> bytes:
    """Return a ZIP research bundle containing:

    - thread markdown
    - timeline events
    - related insights & candidates
    - related research traces
    - related artifacts
    - attached docs
    - manifest.json

    All files organised in a folder named after the thread.
    """
    thread_path = _find_thread(stem)
    raw = thread_path.read_text(encoding="utf-8")
    meta = _parse_thread_metadata(raw, stem)
    folder = stem

    buf = io.BytesIO()
    manifest: dict = {
        "stem": stem,
        "title": meta.get("title", stem),
        "exported": _now_iso(),
        "generator": "Matylda Lab v1.2",
        "contents": {},
    }

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # ── Thread markdown (polished)
        polished = export_polished_md(stem)
        zf.writestr(f"{folder}/{stem}.md", polished)
        manifest["contents"]["thread"] = f"{stem}.md"

        # ── Timeline
        timeline_path = ROOT / "library" / "threads" / "timeline" / f"{stem}.json"
        if timeline_path.exists():
            zf.write(timeline_path, f"{folder}/timeline.json")
            manifest["contents"]["timeline"] = "timeline.json"

        # ── Related insights
        insight_files = _collect_related_insights(stem, meta)
        if insight_files:
            manifest["contents"]["insights"] = []
            for ip in insight_files:
                arcname = f"{folder}/insights/{ip.name}"
                zf.write(ip, arcname)
                manifest["contents"]["insights"].append(ip.name)

        # ── Related candidates
        candidate_files = _collect_related_candidates(stem, meta)
        if candidate_files:
            manifest["contents"]["candidates"] = []
            for cp in candidate_files:
                arcname = f"{folder}/candidates/{cp.name}"
                zf.write(cp, arcname)
                manifest["contents"]["candidates"].append(cp.name)

        # ── Related research traces
        trace_files = _collect_related_traces(stem, meta)
        if trace_files:
            manifest["contents"]["traces"] = []
            for tp in trace_files:
                arcname = f"{folder}/traces/{tp.name}"
                zf.write(tp, arcname)
                manifest["contents"]["traces"].append(tp.name)

        # ── Related artifacts
        artifact_files = _collect_related_artifacts(stem)
        if artifact_files:
            manifest["contents"]["artifacts"] = []
            for ap in artifact_files:
                arcname = f"{folder}/artifacts/{ap.name}"
                zf.write(ap, arcname)
                manifest["contents"]["artifacts"].append(ap.name)

        # ── Attached docs
        doc_files = _collect_related_docs(stem)
        if doc_files:
            manifest["contents"]["docs"] = []
            for dp in doc_files:
                arcname = f"{folder}/docs/{dp.name}"
                zf.write(dp, arcname)
                manifest["contents"]["docs"].append(dp.name)

        # ── Manifest
        zf.writestr(
            f"{folder}/manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )

    return buf.getvalue()


def _collect_related_insights(stem: str, meta: dict) -> list[Path]:
    """Find insights that reference this thread by stem, domain, or title."""
    insights_dir = ROOT / "memory" / "insights"
    if not insights_dir.exists():
        return []
    keywords = _search_keywords(stem, meta)
    return _find_matching_json_files(insights_dir, keywords, exclude_subdirs=True)


def _collect_related_candidates(stem: str, meta: dict) -> list[Path]:
    candidates_dir = ROOT / "memory" / "candidates"
    if not candidates_dir.exists():
        return []
    keywords = _search_keywords(stem, meta)
    return _find_matching_json_files(candidates_dir, keywords)


def _collect_related_traces(stem: str, meta: dict) -> list[Path]:
    """Find research traces mentioning this thread."""
    traces_dir = ROOT / "memory" / "insights"
    if not traces_dir.exists():
        return []
    results = []
    for p in traces_dir.glob("*.json"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(text)
            if data.get("trace_kind") == "research_project_memory_trace":
                if _text_matches(text, stem, meta):
                    results.append(p)
        except Exception:
            pass
    return results


def _collect_related_artifacts(stem: str) -> list[Path]:
    art_dir = ROOT / "artifacts"
    if not art_dir.exists():
        return []
    results = []
    stem_lower = stem.lower()
    for p in art_dir.glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            if stem_lower in text:
                results.append(p)
        except Exception:
            pass
    return results


def _collect_related_docs(stem: str) -> list[Path]:
    """Find docs (attached/generated) that mention the thread stem."""
    results = []
    stem_lower = stem.lower()
    for subdir in ("attached", "generated"):
        docs_dir = ROOT / "library" / "docs" / subdir
        if not docs_dir.exists():
            continue
        for p in docs_dir.iterdir():
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore").lower()
                if stem_lower in text:
                    results.append(p)
            except Exception:
                pass
    return results


def _search_keywords(stem: str, meta: dict) -> list[str]:
    """Build list of keywords to search for in related files."""
    keywords = [stem.lower()]
    title = meta.get("title", "")
    if title:
        # Add significant title words (3+ chars)
        for w in re.split(r"\W+", title.lower()):
            if len(w) >= 3 and w not in keywords:
                keywords.append(w)
    domain = meta.get("domain", "")
    if domain and domain != "—" and domain.lower() not in keywords:
        keywords.append(domain.lower())
    return keywords


def _find_matching_json_files(
    directory: Path, keywords: list[str], exclude_subdirs: bool = False,
) -> list[Path]:
    results = []
    for p in directory.glob("*.json"):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            # At least one keyword must match
            if any(kw in text for kw in keywords):
                results.append(p)
        except Exception:
            pass
    return results


def _text_matches(text: str, stem: str, meta: dict) -> bool:
    text_lower = text.lower()
    if stem.lower() in text_lower:
        return True
    title = meta.get("title", "")
    if title and title.lower() in text_lower:
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Share HTML (self-contained)
# ═══════════════════════════════════════════════════════════════════════════════

def export_share_html(stem: str) -> str:
    """Return a self-contained HTML page for sharing (no server needed).

    The HTML includes embedded CSS with a clean reading theme,
    the thread title, metadata, and the full body rendered from Markdown.
    """
    thread_path = _find_thread(stem)
    raw = thread_path.read_text(encoding="utf-8")
    meta = _parse_thread_metadata(raw, stem)
    body = _clean_body(raw)

    title = html_mod.escape(meta.get("title", stem))
    domain = html_mod.escape(meta.get("domain", ""))
    status = html_mod.escape(meta.get("status", ""))

    body_html = _markdown_to_html(body)

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="Matylda Lab v1.2">
<title>{title}</title>
<style>
:root {{
  --bg: #0f1117;
  --surf: #181b23;
  --border: #2a2d38;
  --text: #e4e4e8;
  --text2: #a0a3af;
  --accent: #6ec1e4;
  --green: #56d68c;
}}
@media (prefers-color-scheme: light) {{
  :root {{
    --bg: #f8f9fa;
    --surf: #ffffff;
    --border: #dee2e6;
    --text: #212529;
    --text2: #6c757d;
    --accent: #0d6efd;
    --green: #198754;
  }}
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
.return-bar {{
  position: sticky; top: 0; z-index: 100;
  background: var(--surf); border-bottom: 1px solid var(--border);
  padding: .5rem 1rem; display: flex; align-items: center; gap: .75rem;
  font-size: .82rem;
}}
.return-bar a {{
  color: var(--accent); text-decoration: none; font-weight: 600;
  display: flex; align-items: center; gap: .35rem;
}}
.return-bar a:hover {{ text-decoration: underline; }}
.return-bar .return-hint {{
  color: var(--text2); font-size: .75rem;
}}
@media print {{ .return-bar {{ display: none; }} }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  padding: 2rem 1rem;
  max-width: 820px;
  margin: 0 auto;
}}
.header {{
  border-bottom: 2px solid var(--accent);
  padding-bottom: 1rem;
  margin-bottom: 2rem;
}}
.header h1 {{
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: .5rem;
}}
.meta {{
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: .82rem;
  color: var(--text2);
}}
.meta-badge {{
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px 10px;
}}
.content h1 {{ font-size: 1.4rem; margin: 1.5rem 0 .75rem; color: var(--text); }}
.content h2 {{ font-size: 1.15rem; margin: 1.3rem 0 .6rem; color: var(--accent); font-weight: 700; }}
.content h3 {{ font-size: 1rem; margin: 1rem 0 .4rem; font-weight: 700; }}
.content p {{ margin: 0 0 .75rem; }}
.content ul, .content ol {{ padding-left: 1.5rem; margin: 0 0 .75rem; }}
.content li {{ margin-bottom: .3rem; }}
.content code {{
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: .88em;
}}
.content pre {{
  background: var(--surf);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
  margin: 0 0 1rem;
}}
.content pre code {{ background: none; border: none; padding: 0; }}
.content blockquote {{
  border-left: 3px solid var(--accent);
  padding-left: 1rem;
  color: var(--text2);
  margin: 0 0 .75rem;
}}
.content strong {{ color: var(--text); font-weight: 600; }}
.content hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }}
.footer {{
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: .75rem;
  color: var(--text2);
  text-align: center;
}}
</style>
</head>
<body>
<div class="return-bar">
  <a href="http://localhost:7474" title="Otwórz Matylda Lab">&#8592; Matylda Lab</a>
  <span class="return-hint">· eksport wątku</span>
</div>
<div class="header">
  <h1>{title}</h1>
  <div class="meta">
    {f'<span class="meta-badge">Domena: {domain}</span>' if domain else ''}
    {f'<span class="meta-badge">Status: {status}</span>' if status else ''}
    <span class="meta-badge">Eksport: {_now_iso()}</span>
  </div>
</div>
<div class="content">
{body_html}
</div>
<div class="footer">
  Wygenerowano przez Matylda Lab v1.2
</div>
</body>
</html>"""


def _markdown_to_html(md: str) -> str:
    """Convert basic Markdown to HTML. Handles headings, paragraphs, lists, code, blockquotes, bold, italic, links, hr."""
    lines = md.split("\n")
    out: list[str] = []
    in_pre = False
    pre_buf: list[str] = []
    in_ul = False
    in_ol = False

    def _flush_list():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_pre:
                out.append(html_mod.escape("\n".join(pre_buf)))
                out.append("</code></pre>")
                pre_buf.clear()
                in_pre = False
            else:
                _flush_list()
                lang = line.strip()[3:].strip()
                out.append(f'<pre><code class="language-{html_mod.escape(lang)}">' if lang else "<pre><code>")
                in_pre = True
            continue

        if in_pre:
            pre_buf.append(line)
            continue

        stripped = line.strip()

        # Empty line
        if not stripped:
            _flush_list()
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            _flush_list()
            out.append("<hr>")
            continue

        # Headings
        hm = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if hm:
            _flush_list()
            level = len(hm.group(1))
            text = _inline_format(hm.group(2))
            anchor = re.sub(r"[^\w\s-]", "", hm.group(2).lower()).replace(" ", "-")
            out.append(f'<h{level} id="{html_mod.escape(anchor)}">{text}</h{level}>')
            continue

        # Blockquote
        if stripped.startswith("> "):
            _flush_list()
            out.append(f"<blockquote><p>{_inline_format(stripped[2:])}</p></blockquote>")
            continue

        # Unordered list
        if re.match(r"^[-*+]\s+", stripped):
            if not in_ul:
                _flush_list()
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline_format(re.sub(r'^[-*+]\\s+', '', stripped))}</li>")
            continue

        # Ordered list
        ol_m = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if ol_m:
            if not in_ol:
                _flush_list()
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{_inline_format(ol_m.group(2))}</li>")
            continue

        # Paragraph
        _flush_list()
        out.append(f"<p>{_inline_format(stripped)}</p>")

    _flush_list()
    if in_pre:
        out.append(html_mod.escape("\n".join(pre_buf)))
        out.append("</code></pre>")

    return "\n".join(out)


def _inline_format(text: str) -> str:
    """Apply inline Markdown formatting: bold, italic, code, links."""
    t = html_mod.escape(text)
    # Code (backtick)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    # Bold **text** or __text__
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"__(.+?)__", r"<strong>\1</strong>", t)
    # Italic *text* or _text_
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", t)
    # Links [text](url)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  Legacy ZIP exports (v0.4 compat)
# ═══════════════════════════════════════════════════════════════════════════════

def export_thread_zip(stem: str) -> bytes:
    """Return ZIP bytes: thread .md + related artifacts."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in (ROOT / "library" / "threads", ROOT / "library" / "threads" / "archive"):
            p = d / f"{stem}.md"
            if p.exists():
                zf.write(p, f"{stem}/{p.name}")
                break
        tl = ROOT / "library" / "threads" / "timeline" / f"{stem}.json"
        if tl.exists():
            zf.write(tl, f"{stem}/timeline.json")
        for art in (ROOT / "artifacts").glob("*.md"):
            try:
                if stem.lower() in art.read_text(encoding="utf-8", errors="ignore").lower():
                    zf.write(art, f"{stem}/artifacts/{art.name}")
            except Exception:
                pass
    return buf.getvalue()


def export_project_zip(project_id: str) -> bytes:
    """Return ZIP bytes: project JSON + all linked threads + their artifacts."""
    buf = io.BytesIO()
    proj_file = ROOT / "library" / "projects" / f"{project_id}.json"
    if not proj_file.exists():
        raise FileNotFoundError(f"Project {project_id} not found")

    proj = json.loads(proj_file.read_text(encoding="utf-8"))
    proj_name = proj.get("name", project_id)[:30].replace(" ", "_")

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(proj_file, f"{proj_name}/project.json")
        for stem in proj.get("threads", []):
            for d in (ROOT / "library" / "threads", ROOT / "library" / "threads" / "archive"):
                p = d / f"{stem}.md"
                if p.exists():
                    zf.write(p, f"{proj_name}/threads/{p.name}")
                    break
            for art in (ROOT / "artifacts").glob("*.md"):
                try:
                    if stem.lower() in art.read_text(encoding="utf-8", errors="ignore").lower():
                        zf.write(art, f"{proj_name}/artifacts/{art.name}")
                except Exception:
                    pass
    return buf.getvalue()


def export_artifact(name: str) -> tuple[bytes, str]:
    """Return (bytes, filename). Raises FileNotFoundError if missing."""
    p = ROOT / "artifacts" / name
    if not p.exists():
        raise FileNotFoundError(f"Artifact {name} not found")
    return p.read_bytes(), p.name


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _find_thread(stem: str) -> Path:
    """Locate thread file by stem. Raises FileNotFoundError if missing."""
    for d in (ROOT / "library" / "threads", ROOT / "library" / "threads" / "archive"):
        p = d / f"{stem}.md"
        if p.exists():
            return p
    raise FileNotFoundError(f"Thread '{stem}' nie znaleziony")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
