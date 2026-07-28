"""Fetch web content and return clean readable text. Zero external dependencies."""

from __future__ import annotations
import html
import re
import urllib.error
import urllib.request

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "pl,en-US;q=0.9,en;q=0.8",
}

# Tags whose content is stripped entirely (scripts, styles, nav, etc.)
_DROP_TAGS = re.compile(
    r"<(script|style|nav|footer|header|aside|noscript|iframe|svg|form)"
    r"(\s[^>]*)?>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def fetch_url(url: str, max_chars: int = 15_000) -> str:
    """Fetch *url* and return clean text (max *max_chars* characters)."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text" not in content_type and "json" not in content_type:
                return f"[POMINIĘTO: {url} — typ treści: {content_type}]"
            raw = resp.read(500_000).decode("utf-8", errors="replace")
        text = _clean(raw)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[… treść skrócona …]"
        return f"[ŹRÓDŁO: {url}]\n\n{text}"
    except urllib.error.HTTPError as e:
        return f"[BŁĄD HTTP {e.code}: {url}]"
    except urllib.error.URLError as e:
        return f"[BŁĄD SIECI: {url} — {e.reason}]"
    except Exception as e:  # noqa: BLE001
        return f"[BŁĄD: {url} — {e}]"


def _clean(raw: str) -> str:
    # Drop noisy tag blocks
    raw = _DROP_TAGS.sub(" ", raw)
    # Strip remaining tags
    text = _HTML_TAG.sub(" ", raw)
    # Decode HTML entities
    text = html.unescape(text)
    # Normalise whitespace per line
    lines = [_WHITESPACE.sub(" ", ln).strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    # Collapse excess blank lines
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


# ── v0.7: Reader mode ───────────────────────────────────────────────────────

# Patterns to identify the main content area
_ARTICLE_TAGS = re.compile(
    r"<(article|main|div\s+[^>]*(?:class|id)=\"[^\"]*(?:content|article|post|entry|main|body)[^\"]*\")"
    r"[^>]*>(.*?)</(?:article|main|div)>",
    re.DOTALL | re.IGNORECASE,
)

_TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_H1_TAG = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL | re.IGNORECASE)
_META_DESC = re.compile(
    r'<meta\s+[^>]*(?:name="description"|property="og:description")\s+content="([^"]*)"',
    re.IGNORECASE,
)
_META_AUTHOR = re.compile(
    r'<meta\s+[^>]*(?:name="author")\s+content="([^"]*)"',
    re.IGNORECASE,
)
_TIME_TAG = re.compile(
    r"<time[^>]*datetime=\"([^\"]+)\"[^>]*>",
    re.IGNORECASE,
)

_PARAGRAPH_TAGS = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)


def _extract_article_html(raw_html: str) -> str:
    """Try to extract the main article/content from HTML."""
    # Try <article> or <main> or content-div first
    m = _ARTICLE_TAGS.search(raw_html)
    if m:
        return m.group(2)

    # Fallback: extract all <p> tags and pick the longest cluster
    paragraphs = _PARAGRAPH_TAGS.findall(raw_html)
    if paragraphs:
        # Filter out very short paragraphs (likely nav/footer)
        long_paragraphs = [p for p in paragraphs if len(p) > 50]
        if long_paragraphs:
            return "\n\n".join(long_paragraphs)

    return ""


def _extract_metadata(raw_html: str) -> dict:
    """Extract metadata (title, description, author, date) from HTML."""
    meta: dict[str, str] = {}

    m = _TITLE_TAG.search(raw_html)
    if m:
        meta["title"] = html.unescape(_HTML_TAG.sub("", m.group(1))).strip()

    m = _H1_TAG.search(raw_html)
    if m:
        h1 = html.unescape(_HTML_TAG.sub("", m.group(1))).strip()
        if h1:
            meta["title"] = h1  # H1 overrides <title> if present

    m = _META_DESC.search(raw_html)
    if m:
        meta["description"] = html.unescape(m.group(1)).strip()

    m = _META_AUTHOR.search(raw_html)
    if m:
        meta["author"] = html.unescape(m.group(1)).strip()

    m = _TIME_TAG.search(raw_html)
    if m:
        meta["date"] = m.group(1)

    return meta


def fetch_reader(url: str, max_chars: int = 25_000) -> dict:
    """v0.7 Reader mode: fetch URL and return structured content.

    Returns:
        {
            "url": str,
            "title": str,
            "author": str | None,
            "date": str | None,
            "description": str | None,
            "content": str,       # Clean text of main article
            "word_count": int,
            "ok": bool,
            "error": str | None,
        }
    """
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=20) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text" not in content_type and "json" not in content_type:
                return {"url": url, "ok": False, "error": f"Nieobsługiwany typ: {content_type}",
                        "title": "", "content": "", "word_count": 0}
            raw_html = resp.read(1_000_000).decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return {"url": url, "ok": False, "error": str(e),
                "title": "", "content": "", "word_count": 0}

    metadata = _extract_metadata(raw_html)

    # Try to get article content
    article_html = _extract_article_html(raw_html)
    if article_html:
        content = _clean(article_html)
    else:
        # Fallback: clean entire page
        content = _clean(raw_html)

    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[… treść skrócona …]"

    return {
        "url": url,
        "ok": True,
        "error": None,
        "title": metadata.get("title", ""),
        "author": metadata.get("author"),
        "date": metadata.get("date"),
        "description": metadata.get("description"),
        "content": content,
        "word_count": len(content.split()),
    }
