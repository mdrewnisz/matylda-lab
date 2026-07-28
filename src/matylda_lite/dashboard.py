"""Matylda Lab dashboard — interactive HTML served from local server."""

from __future__ import annotations

import re
import webbrowser
from datetime import date
from pathlib import Path

from .config import ROOT

PORT = 7474


# ── File helpers ──────────────────────────────────────────────────────────────

def read(relative: str) -> str:
    p = ROOT / relative
    return p.read_text(encoding="utf-8") if p.exists() else ""


def parse_table(text: str) -> list[dict]:
    rows: list[dict] = []
    headers: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not headers:
            headers = cells
        elif re.match(r"^[-: ]+$", cells[0]):
            continue
        else:
            rows.append(dict(zip(headers, cells)))
    return rows


def parse_checklist(text: str) -> list[dict]:
    items = []
    for line in text.splitlines():
        m = re.match(r"\s*-\s*\[(x| )\]\s*(.+)", line, re.IGNORECASE)
        if m:
            items.append({"done": m.group(1).lower() == "x", "label": m.group(2).strip()})
    return items


def extract_section(text: str, heading: str) -> str:
    pat = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    m = re.search(pat, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def strip_md_link(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def inbox_status() -> tuple[bool, int]:
    text = read("inbox/raw_notes.md")
    section = extract_section(text, "Unprocessed Notes")
    lines = [l for l in section.splitlines()
             if l.strip() and not l.strip().startswith("<!--")]
    return len(lines) == 0, len(lines)


def artifact_list() -> list[str]:
    d = ROOT / "artifacts"
    if not d.exists():
        return []
    return sorted(f.name for f in d.iterdir() if f.suffix.lower() == ".md")


# ── HTML helpers ──────────────────────────────────────────────────────────────

def badge(text: str, kind: str = "neutral") -> str:
    return f'<span class="badge badge-{kind}">{text}</span>'


def card(title: str, body: str, accent: str = "") -> str:
    bar = f'<div class="card-accent" style="background:{accent}"></div>' if accent else ""
    return f'<div class="card">{bar}<h2>{title}</h2>{body}</div>'


# ── Section renderers ─────────────────────────────────────────────────────────

def render_active_threads(rows: list[dict]) -> str:
    if not rows:
        return "<p class='empty'>Brak aktywnych wątków.</p>"
    out = []
    for r in rows:
        name = strip_md_link(r.get("Thread", ""))
        nxt  = r.get("Next action", r.get("Next Action", "—"))
        blk  = r.get("Blocker", "—")
        rev  = r.get("Review required", "—")
        rev_html = badge("review needed", "warn") if rev.lower() == "yes" else ""
        blk_html = (
            f'<div class="blocker">⚠ {blk}</div>'
            if blk not in ("—", "", "none", "None") else ""
        )
        out.append(
            f'<div class="thread-row">'
            f'<div class="thread-name">{name} {rev_html}</div>'
            f'<div class="thread-next">→ {nxt}</div>'
            f'{blk_html}</div>'
        )
    return "".join(out)


def render_parking(rows: list[dict]) -> str:
    if not rows:
        return "<p class='empty'>Parking pusty.</p>"
    out = []
    for r in rows:
        name    = strip_md_link(r.get("Thread", ""))
        reason  = r.get("Reason parked", r.get("Reason Parked", "—"))
        trigger = r.get("Return trigger", r.get("Return Trigger", "—"))
        out.append(
            f'<div class="parking-row">'
            f'<span class="parking-name">{name}</span>'
            f'<span class="parking-reason">{reason}</span>'
            f'<span class="parking-trigger">powrót gdy: {trigger}</span>'
            f'</div>'
        )
    return "".join(out)


def render_prompts(rows: list[dict], server_mode: bool = False) -> str:
    ready = [r for r in rows if r.get("Status", "").lower() == "ready"]
    done  = [r for r in rows if r.get("Status", "").lower() in ("completed", "done")]
    if not rows:
        return "<p class='empty'>Brak promptów.</p>"
    html = ""
    if ready:
        html += "<h3 class='sub'>Gotowe do uruchomienia</h3>"
        for r in ready:
            task     = r.get("Task", "—")
            target   = r.get("Target", "—")
            expected = r.get("Expected output", r.get("Expected Output", "—"))
            btn = ""
            if server_mode:
                safe = task.replace("'", "\\'").replace("`", "\\`")
                btn = f'<button class="run-btn" onclick="sendPreset(\'{safe}\')">▶ Uruchom</button>'
            html += (
                f'<div class="prompt-row ready">'
                f'<div class="prompt-header">{badge("ready","ready")} {btn}</div>'
                f'<div class="prompt-task">{task}</div>'
                f'<div class="prompt-meta">narzędzie: {target}</div>'
                f'<div class="prompt-meta">wynik: {expected}</div>'
                f'</div>'
            )
    if done:
        html += f"<h3 class='sub'>Ukończone ({len(done)})</h3>"
        for r in done:
            html += f'<div class="prompt-row done">{badge("done","done")} {r.get("Task","—")}</div>'
    return html


def render_decisions(rows: list[dict], n: int = 3) -> str:
    if not rows:
        return "<p class='empty'>Brak decyzji.</p>"
    out = []
    for r in list(reversed(rows))[:n]:
        out.append(
            f'<div class="decision-row">'
            f'<span class="decision-date">{r.get("Date","")}</span>'
            f'<div class="decision-text">{r.get("Decision","—")}</div>'
            f'<div class="decision-reason">{r.get("Reason","—")}</div>'
            f'</div>'
        )
    return "".join(out)


def render_this_week(text: str) -> str:
    focus   = extract_section(text, "Focus")
    actions = extract_section(text, "Planned Actions")
    f_lines = [l.lstrip("0123456789. ").strip() for l in focus.splitlines() if l.strip()]
    f_html  = "".join(f"<li>{l}</li>" for l in f_lines if l)
    checks  = parse_checklist(actions)
    done_c  = sum(1 for c in checks if c["done"])
    total   = len(checks)
    pct     = int(done_c / total * 100) if total else 0
    ch_html = "".join(
        f'<div class="check {"done" if c["done"] else "todo"}">'
        f'{"✓" if c["done"] else "○"} {c["label"]}</div>'
        for c in checks
    )
    prog = (
        f'<div class="progress-bar-wrap">'
        f'<div class="progress-bar-fill" style="width:{pct}%"></div></div>'
        f'<div class="progress-label">{done_c}/{total} ukończone</div>'
    ) if total else ""
    return f'<div class="week-focus"><ul>{f_html}</ul></div>{prog}<div class="checklist">{ch_html}</div>'


def render_inbox(empty: bool, count: int) -> str:
    if empty:
        return f'{badge("pusty","done")} <span>Inbox jest czysty.</span>'
    return f'{badge(f"{count} notatek","warn")} <span>Inbox zawiera nieprzetworzony materiał.</span>'


def render_artifacts(files: list[str]) -> str:
    if not files:
        return "<p class='empty'>Brak artefaktów.</p>"
    return "".join(f'<div class="artifact-item">📄 {f}</div>' for f in files)


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── UNIFIED DESIGN TOKENS ───────────────────────────────────────────────────
   Single source of truth. No duplicate variable families.
   Neo-noir: deep backgrounds, magenta/violet accent, deliberate whitespace.
────────────────────────────────────────────────────────────────────────────── */
:root {
  /* Surfaces — warm dark (Claude dark-mode family): brown-grey, not blue-black */
  --bg:     #1c1b19;
  --surf:   #262624;
  --surf2:  #302f2c;
  --surf3:  #3a3935;
  --surf4:  #46443f;

  /* Borders — warm, soft */
  --border:  #35332f;
  --border2: #46443f;
  --border3: #57544d;

  /* Text — warm cream, 4 weights */
  --text:    #f5f4ee;
  --text2:   #bcb9af;
  --text3:   #8a877d;
  --text4:   #57544d;

  /* Accent — Claude coral (primary identity colour) */
  --accent:  #d97757;
  --accent2: #c2613f;
  --accent-dim: rgba(217, 119, 87, 0.13);

  /* Semantic colours — warmed to match */
  --green:   #5fa572;
  --green2:  #3d6b4a;
  --red:     #cc6a5a;
  --yellow:  #c39a3e;
  --orange:  #c47a44;
  --blue:    #6b93c2;
  --ice:     #7ba0c2;

  /* Legacy aliases — keep JS working without changes */
  --surf1:   var(--surf);
  --surf5:   var(--surf4);
  --border1: var(--border);
  --text1:   var(--text);
  --ok:      var(--green);
  --warning: var(--yellow);
  --mono:    ui-monospace, "SF Mono", "Fira Code", monospace;
}

html, body {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  -webkit-font-smoothing: antialiased;
}

/* ── Header ──────────────────────────────────────────────────────────────────
   Calm, thin. Identity mark on left; status cluster on right.
   The accent line at bottom is the only decorative element.
────────────────────────────────────────────────────────────────────────────── */
.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 1.1rem; height: 44px;
  background: var(--surf);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
}
/* Subtle magenta underline — identity anchor */
.header::after {
  content: '';
  position: absolute; bottom: 0; left: 0;
  width: 48px; height: 2px;
  background: linear-gradient(90deg, var(--accent) 0%, transparent 100%);
}
.logo { font-size: .92rem; font-weight: 700; color: var(--text); letter-spacing: -.2px; }
.logo-sub { color: var(--text3); font-weight: 400; font-size: .78rem; margin-left: .45rem; }
.header-right { display: flex; align-items: center; gap: .9rem; font-size: .74rem; }
.date-str { color: var(--text3); font-variant-numeric: tabular-nums; }
.server-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text4); flex-shrink: 0; }
.server-dot.online { background: var(--green); box-shadow: 0 0 4px var(--green); }
.server-label { color: var(--text3); }
.epi-badge {
  background: rgba(192, 72, 72, .15); color: var(--red); font-size: .66rem; font-weight: 700;
  letter-spacing: .05em; padding: .18em .55em; border-radius: 4px;
  border: 1px solid rgba(192, 72, 72, .3);
}
.epi-badge.hidden { display: none; }

/* ── 3-column layout ─────────────────────────────────────────────────────────── */
.app-layout {
  display: grid;
  grid-template-columns: 268px 1fr 252px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── Left panel ──────────────────────────────────────────────────────────────── */
.panel-left {
  overflow-y: auto;
  border-right: 1px solid var(--border);
  background: var(--surf);
  padding: .6rem .5rem;
}

.panel-section { margin-bottom: .6rem; }

.panel-header {
  display: flex; justify-content: space-between; align-items: center;
  font-size: .64rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em;
  color: var(--text3); padding: .35rem .5rem .45rem;
  border-bottom: 1px solid var(--border); margin-bottom: .4rem;
}
.panel-header button {
  background: none; border: none; color: var(--text3); cursor: pointer;
  font-size: .88rem; line-height: 1; padding: 0 .25rem; border-radius: 5px;
}
.panel-header button:hover { color: var(--text2); background: var(--surf3); }

.panel-sub {
  font-size: .63rem; color: var(--text3); text-transform: uppercase;
  letter-spacing: .08em; padding: .5rem .5rem .28rem;
  display: flex; align-items: center; gap: .35rem;
}
.panel-sub-count {
  background: var(--surf3); border: 1px solid var(--border2);
  border-radius: 10px; font-size: .6rem; padding: .05rem .4rem;
  color: var(--text3); letter-spacing: 0; text-transform: none;
  font-weight: 600; line-height: 1.4;
}
.threads-filter-wrap {
  padding: .25rem .5rem .15rem;
}
.threads-filter-input {
  width: 100%; box-sizing: border-box;
  background: var(--surf2); border: 1px solid var(--border);
  color: var(--text2); padding: .3rem .6rem;
  border-radius: 6px; font-size: .76rem; outline: none;
}
.threads-filter-input:focus { border-color: var(--accent); }

/* ── Thread items ─────────────────────────────────────────────────────────────
   Clean rows. Status dot is the only colour signal.
   Actions appear only on hover — reduces visual noise.
────────────────────────────────────────────────────────────────────────────── */
.thread-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: .5rem .6rem; border-radius: 7px; cursor: default; margin-bottom: 1px;
  transition: background .1s;
}
.thread-item:hover { background: var(--surf3); }
.thread-item.active {
  background: var(--surf3);
  box-shadow: inset 2px 0 0 var(--accent);
}
.thread-status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.thread-status-dot.active  { background: var(--green); box-shadow: 0 0 5px rgba(58, 170, 120, .6); }
.thread-status-dot.library { background: var(--text4); }
.thread-status-dot.archived { background: var(--red); opacity: .45; }
.thread-status-dot.frozen  { background: var(--ice); box-shadow: 0 0 4px rgba(92, 159, 212, .5); }

.thread-limit-warning {
  display: flex; align-items: center; gap: 6px;
  margin: 4px 6px 2px; padding: 6px 10px;
  background: rgba(176, 144, 32, .08); border: 1px solid rgba(176, 144, 32, .25);
  border-radius: 6px; font-size: .73rem; color: #c8a040;
}
.thread-limit-warning .warn-icon { font-size: .85rem; flex-shrink: 0; }
.thread-name {
  font-size: .83rem; color: var(--text); flex: 1; margin: 0 .45rem;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; line-height: 1.3;
}
.thread-domain { font-size: .68rem; color: var(--text3); }

.icon-btn {
  background: none; border: none; color: var(--text3); cursor: pointer;
  font-size: .74rem; padding: .15rem .3rem; border-radius: 5px;
  transition: color .1s, background .1s;
}
.icon-btn:hover { color: var(--text2); background: var(--surf4); }

/* Project items */
.project-item { padding: .45rem .5rem; border-radius: 4px; margin-bottom: 3px; }
.project-item:hover { background: var(--surf3); }
.project-name { font-size: .82rem; font-weight: 600; color: var(--text); }
.project-meta { font-size: .7rem; color: var(--text3); }
.project-threads { font-size: .72rem; color: var(--text2); margin-top: .2rem; }

.new-project-form {
  background: var(--surf2); border: 1px solid var(--border);
  border-radius: 4px; padding: .5rem; margin-bottom: .5rem;
  display: flex; flex-direction: column; gap: .3rem;
}
.new-project-form.hidden { display: none; }
.new-project-form input {
  background: var(--surf3); border: 1px solid var(--border2); color: var(--text);
  padding: .3rem .5rem; border-radius: 5px; font-size: .78rem;
}
.new-project-form .form-btns { display: flex; gap: .3rem; }
.new-project-form .form-btns button {
  flex: 1; background: var(--surf3); border: 1px solid var(--border2);
  color: var(--text2); padding: .28rem; border-radius: 5px; font-size: .72rem; cursor: pointer;
}
.new-project-form .form-btns button:first-child {
  background: var(--accent); color: #fff; border-color: transparent;
}

/* ── Center panel ────────────────────────────────────────────────────────────
   The main cognitive workspace. Background slightly darker than panels.
   Chat messages: user compact, AI full-width with reading-friendly line-height.
────────────────────────────────────────────────────────────────────────────── */
.panel-center {
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--bg);
}

.chat-panel {
  display: flex; flex-direction: column; height: 100%; padding: .7rem .85rem .7rem;
}

.chat-history {
  flex: 1; overflow-y: auto; padding: .6rem 0;
  display: flex; flex-direction: column; gap: .7rem;
  scroll-behavior: smooth;
}
.chat-empty {
  color: var(--text3); font-size: .82rem; font-style: italic;
  padding: 2rem 0 0; text-align: center;
}

.msg { display: flex; flex-direction: column; max-width: 94%; }
.msg-user { align-self: flex-end; align-items: flex-end; max-width: 72%; }
.msg-ai   { align-self: flex-start; align-items: flex-start; width: 100%; max-width: 100%; }

.msg-bubble {
  padding: .7rem .95rem; border-radius: 10px; font-size: .9rem; line-height: 1.5;
  white-space: pre-wrap; word-break: break-word; max-width: 100%;
}
/* User messages: compact, muted blue — they are input, not focus */
.msg-user .msg-bubble {
  background: #172040; color: #b8ccf0;
  border: 1px solid #1e2e55;
  border-bottom-right-radius: 3px;
  font-size: .87rem;
}
/* AI messages: primary reading surface — generous, calm */
.msg-ai .msg-bubble {
  background: var(--surf2); color: var(--text);
  border: 1px solid var(--border2);
  border-bottom-left-radius: 3px;
  font-family: inherit; font-size: .9rem;
  box-shadow: 0 1px 6px rgba(0, 0, 0, .3);
}

.msg-bubble.streaming::after { content: '▌'; animation: blink .9s step-end infinite; color: var(--accent); }
@keyframes blink { 50% { opacity: 0; } }

.msg-meta {
  display: flex; gap: .4rem; align-items: center; flex-wrap: wrap;
  font-size: .67rem; color: var(--text3); margin-top: .22rem;
}
.msg-saved { color: var(--green); }

.msg-review {
  margin-top: .28rem; padding: .3rem .55rem; background: var(--surf2);
  border-left: 2px solid var(--border2); font-size: .71rem; color: var(--text3);
  border-radius: 0 3px 3px 0;
}
.msg-review.flag { border-left-color: var(--yellow); }
.msg-review.fail { border-left-color: var(--red); color: #c08888; }

.msg-approval {
  margin-top: .3rem; padding: .45rem .65rem; background: var(--surf2);
  border: 1px solid var(--border3); border-radius: 7px; font-size: .75rem;
}
.msg-approval p { margin-bottom: .3rem; color: var(--text2); }
.msg-approval .changes { font-family: var(--mono); font-size: .7rem; color: var(--text3); margin-bottom: .4rem; }

/* ── Chat input ──────────────────────────────────────────────────────────────
   Unified input card. Secondary options (save-as, fetch URL) collapsed by default.
────────────────────────────────────────────────────────────────────────────── */
.chat-input-area { display: flex; gap: .5rem; margin-top: .5rem; flex-direction: column; }

/* The textarea container — rounded card */
.input-row-wrap {
  display: flex; gap: .5rem; align-items: flex-end;
  background: var(--surf2); border: 1px solid var(--border2);
  border-radius: 10px; padding: .55rem .7rem;
  transition: border-color .15s, box-shadow .15s;
}
.input-row-wrap:focus-within {
  border-color: var(--accent2);
  box-shadow: 0 0 0 3px var(--accent-dim);
}

.chat-textarea {
  flex: 1; background: transparent; border: none;
  color: var(--text); padding: 0; border-radius: 0; font-size: .88rem;
  font-family: inherit; resize: none; outline: none; line-height: 1.6;
  min-height: 26px; max-height: 200px; overflow-y: auto;
}
.chat-textarea::placeholder { color: var(--text3); }

.chat-actions { display: flex; flex-direction: column; gap: .28rem; }

.send-btn {
  width: 38px; height: 38px; padding: 0;
  background: var(--accent2); color: #fff;
  border: none; border-radius: 8px; font-size: 1rem;
  font-weight: 700; cursor: pointer; display: flex;
  align-items: center; justify-content: center;
  transition: background .15s, transform .1s;
  flex-shrink: 0;
}
.send-btn:hover { background: var(--accent); transform: scale(1.04); }
.send-btn:disabled { background: var(--surf3); color: var(--text3); cursor: not-allowed; transform: none; }

.clear-btn2 {
  padding: .3rem .55rem; background: transparent; color: var(--text3);
  border: 1px solid var(--border); border-radius: 6px; font-size: .76rem; cursor: pointer;
  transition: color .1s;
}
.clear-btn2:hover { color: var(--text2); border-color: var(--border2); }

.save-row { display: flex; align-items: center; gap: .5rem; }
.save-label { font-size: .71rem; color: var(--text3); white-space: nowrap; }
.save-input {
  flex: 1; background: var(--surf2); border: 1px solid var(--border);
  color: var(--text2); padding: .28rem .5rem; border-radius: 7px;
  font-size: .74rem; font-family: var(--mono); outline: none;
}
.save-input:focus { border-color: var(--accent); }

.fetch-row { display: flex; gap: .45rem; }
.url-input {
  flex: 1; background: var(--surf2); border: 1px solid var(--border);
  color: var(--text2); padding: .28rem .5rem; border-radius: 7px;
  font-size: .74rem; outline: none;
}
.url-input:focus { border-color: var(--accent); }
.fetch-btn {
  background: var(--surf3); border: 1px solid var(--border2); color: var(--text2);
  padding: .28rem .6rem; border-radius: 7px; cursor: pointer; font-size: .76rem;
  transition: color .1s;
}
.fetch-btn:hover { color: var(--text); }

.spinner {
  display: none; width: 14px; height: 14px;
  border: 2px solid var(--surf3); border-top-color: var(--accent);
  border-radius: 50%; animation: spin .65s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Right panel (DARKROOM) ──────────────────────────────────────────────────
   Epistemic monitoring panel. Deliberately quieter than the center.
   Sections use <details> for progressive disclosure — most info is collapsed.
────────────────────────────────────────────────────────────────────────────── */
.panel-right {
  overflow-y: auto;
  border-left: 1px solid var(--border);
  background: var(--surf);
  padding: .6rem .6rem;
}

.dr-header {
  font-size: .64rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .12em; color: var(--text3); padding: .4rem .1rem .6rem;
  border-bottom: 1px solid var(--border); margin-bottom: .55rem;
  display: flex; align-items: center; justify-content: space-between;
}
/* Accent dot on DARKROOM header */
.dr-header::before {
  content: '●';
  color: var(--accent); font-size: .45rem; margin-right: .5rem; opacity: .7;
}

.dr-section {
  margin-bottom: .75rem; padding-bottom: .75rem;
  border-bottom: 1px solid var(--border2);
}
.dr-section:last-child { border-bottom: none; }

/* Sleeping Matylda widget */
.sm-run-btn {
  font-size: .68rem; padding: .12rem .42rem; background: var(--surf3);
  border: 1px solid var(--border2); border-radius: 4px; cursor: pointer; color: var(--text2);
  transition: color .1s;
}
.sm-run-btn:hover { color: var(--green); border-color: var(--green2); }
.sm-run-btn.running { opacity: .45; cursor: wait; }
.sm-card {
  background: var(--surf2); border-radius: 4px; padding: .42rem .52rem;
  margin-bottom: .28rem; font-size: .73rem; line-height: 1.5;
}
.sm-card-label {
  font-size: .61rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .08em; color: var(--text3); margin-bottom: .2rem;
}
.sm-list-item {
  padding: .15rem 0; border-bottom: 1px solid var(--border2); font-size: .72rem;
}
.sm-list-item:last-child { border-bottom: none; }
.sm-synthesis { color: var(--text); margin-bottom: .4rem; font-size: .75rem; line-height: 1.5; }

.dr-section-title {
  font-size: .63rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .1em; color: var(--text3); margin-bottom: .45rem;
}

/* ── Focus Mode panel ────────────────────────────────────────────────────────── */
.focus-panel { margin-top: .5rem; }
.focus-mode-row {
  display: flex; gap: .35rem; flex-wrap: wrap; margin-bottom: .5rem;
}
.focus-timer-btn {
  padding: .22rem .55rem; border-radius: 7px; border: 1px solid var(--border2);
  background: var(--surf2); color: var(--text2); font-size: .72rem; cursor: pointer;
  transition: background .1s, border-color .1s, color .1s;
}
.focus-timer-btn.active, .focus-timer-btn:hover {
  background: var(--accent-dim); border-color: var(--accent2); color: var(--accent);
}
.focus-area-check { display: flex; align-items: center; gap: .3rem; font-size: .73rem; color: var(--text2); cursor: pointer; }
.focus-area-check input[type=checkbox] { accent-color: var(--accent2); }
.focus-custom-prompt {
  width: 100%; box-sizing: border-box; background: var(--surf2); border: 1px solid var(--border2);
  border-radius: 7px; color: var(--text); font-size: .75rem; font-family: inherit;
  padding: .3rem .45rem; resize: none; outline: none; margin-bottom: .4rem; line-height: 1.4;
}
.focus-custom-prompt::placeholder { color: var(--text3); }
.focus-custom-prompt:focus { border-color: var(--accent2); }
.focus-start-btn {
  width: 100%; padding: .32rem; border-radius: 6px; border: none;
  background: var(--accent2); color: #fff; font-size: .8rem; font-weight: 700; cursor: pointer;
  transition: opacity .15s;
}
.focus-start-btn:hover { opacity: .88; }
.focus-start-btn:disabled { opacity: .45; cursor: wait; }
.focus-status-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: .3rem .45rem; background: var(--surf2); border-radius: 7px;
  margin-bottom: .35rem; font-size: .72rem;
}
.focus-countdown { font-weight: 700; color: var(--accent); font-variant-numeric: tabular-nums; }
.focus-badge {
  display: inline-block; background: var(--accent2); color: #fff;
  font-size: .65rem; font-weight: 700; border-radius: 10px;
  padding: .05rem .4rem; margin-left: .3rem; vertical-align: middle;
}
.focus-ctrl-btn {
  padding: .18rem .45rem; border-radius: 4px; border: 1px solid var(--border2);
  background: transparent; color: var(--text2); font-size: .7rem; cursor: pointer;
  transition: background .1s;
}
.focus-ctrl-btn:hover { background: var(--surf3); }
.focus-idle-note { font-size: .68rem; color: var(--text3); margin-bottom: .3rem; }

/* ── Silo Science widget ─────────────────────────────────────────────────────── */
.silo-widget {
  background: var(--surf2); border-radius: 7px; padding: .55rem .65rem;
  margin-bottom: .5rem; border: 1px solid var(--border2);
}
.silo-widget-header { display: flex; align-items: center; gap: .4rem; margin-bottom: .3rem; }
.silo-widget-name { font-weight: 700; font-size: .8rem; color: var(--text1); }
.silo-type-badge {
  font-size: .6rem; padding: .1rem .35rem; border-radius: 5px; font-weight: 700; flex-shrink: 0;
}
.silo-hashtag { font-size: .68rem; color: var(--text3); margin-left: auto; font-family: monospace; }
.silo-policy-row { font-size: .68rem; color: var(--text3); margin-bottom: .4rem; }
.silo-actions { display: flex; gap: .3rem; flex-wrap: wrap; margin-bottom: .4rem; }
.silo-btn {
  font-size: .68rem; padding: .18rem .45rem; background: var(--surf3);
  border: 1px solid var(--border2); border-radius: 5px; cursor: pointer; color: var(--text2);
}
.silo-btn:hover { background: var(--surf2); color: var(--green); }
.silo-btn-pipeline { border-color: var(--green); }
.silo-summary { font-size: .7rem; color: var(--text3); line-height: 1.4; }
.silo-skills-list { margin-top: .3rem; }
.silo-skill-item {
  display: flex; align-items: center; gap: .4rem; padding: .2rem 0;
  border-bottom: 1px solid var(--border2); font-size: .72rem;
}
.silo-skill-item:last-child { border-bottom: none; }
.silo-skill-name { flex: 1; color: var(--text1); }
.silo-skill-tag { font-size: .6rem; color: var(--text3); background: var(--surf3); padding: .05rem .25rem; border-radius: 2px; }
.silo-nb-item { padding: .18rem 0; border-bottom: 1px solid var(--border2); font-size: .72rem; cursor: pointer; }
.silo-nb-item:hover { color: var(--green); }
.silo-nb-item:last-child { border-bottom: none; }
/* ── Session panel ─────────────────────────────────────────────────────────── */
.session-panel { font-size:.72rem; }
.session-confidence { display:inline-block; height:4px; border-radius:2px; background:var(--green); margin-top:.15rem; }
.session-goal { font-size:.7rem; color:var(--text2); margin:.25rem 0 .1rem; font-style:italic; }
.session-events { font-size:.65rem; color:var(--text3); margin-top:.2rem; }
/* ── Research traces panel ─────────────────────────────────────────────────── */
.trace-item { padding:.25rem 0; border-bottom:1px solid var(--border2); }
.trace-item:last-child { border-bottom:none; }
.trace-title { font-size:.72rem; font-weight:600; color:var(--text1); }
.trace-summary { font-size:.68rem; color:var(--text3); margin:.1rem 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.trace-next { font-size:.67rem; color:var(--green); }
.trace-empty { font-size:.7rem; color:var(--text3); }
/* ── UCB1 stats panel ──────────────────────────────────────────────────────── */
.ucb1-row { display:flex; gap:.3rem; align-items:center; font-size:.68rem; margin:.15rem 0; }
.ucb1-model { width:3.5rem; font-weight:600; color:var(--text1); }
.ucb1-bar { flex:1; height:4px; border-radius:2px; background:var(--surf3); overflow:hidden; }
.ucb1-bar-fill { height:100%; border-radius:2px; background:var(--green); transition:width .4s; }
.ucb1-rate { width:2.5rem; text-align:right; color:var(--text3); }
.ucb1-empty { font-size:.7rem; color:var(--text3); }

/* Notebook editor modal */
.nb-modal-overlay { position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:1000;display:flex;align-items:center;justify-content:center; }
.nb-modal { background:var(--surf1);border:1px solid var(--border1);border-radius:8px;width:min(700px,95vw);max-height:90vh;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,.4); }
.nb-modal-header { display:flex;align-items:center;gap:.5rem;padding:.6rem .8rem;border-bottom:1px solid var(--border2); }
.nb-modal-title-input { flex:1;background:transparent;border:none;color:var(--text1);font-size:.85rem;font-weight:700;outline:none; }
.nb-modal-title-input:focus { background:var(--surf2);border-radius:5px;padding:2px 4px; }
.nb-modal-tags { font-size:.68rem;color:var(--text3);background:var(--surf2);border:1px solid var(--border2);border-radius:5px;padding:2px 6px;width:180px;outline:none; }
.nb-modal-body { flex:1;overflow:hidden;display:flex;flex-direction:column; }
.nb-modal-textarea { flex:1;background:var(--surf2);border:none;color:var(--text1);font-size:.78rem;font-family:var(--mono);padding:.7rem;resize:none;outline:none;overflow-y:auto;min-height:300px; }
.nb-modal-footer { display:flex;gap:.5rem;padding:.5rem .8rem;border-top:1px solid var(--border2);align-items:center; }
.nb-save-status { font-size:.65rem;color:var(--text3);margin-left:auto; }
.nb-btn { font-size:.72rem;padding:.25rem .65rem;border-radius:5px;border:1px solid var(--border2);cursor:pointer;background:var(--surf3);color:var(--text1); }
.nb-btn-primary { background:var(--green);border-color:var(--green);color:#000; }
.nb-btn-danger { background:transparent;border-color:#c0392b;color:#c0392b; }

/* Multi-project panel */
.proj-panel { padding:.3rem 0; }
.proj-active-name { font-size:.8rem;font-weight:700;color:var(--green);white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.proj-list { max-height:120px;overflow-y:auto;margin:.3rem 0; }
.proj-item { display:flex;align-items:center;gap:.4rem;padding:.2rem .3rem;border-radius:5px;cursor:pointer;font-size:.72rem;color:var(--text2); }
.proj-item:hover { background:var(--surf3); }
.proj-item.active { color:var(--green);font-weight:600; }
.proj-item-dot { width:6px;height:6px;border-radius:50%;background:var(--border2);flex-shrink:0; }
.proj-item.active .proj-item-dot { background:var(--green); }
.proj-actions { display:flex;gap:.3rem;margin-top:.3rem; }
.proj-stats { font-size:.65rem;color:var(--text3);margin-top:.2rem; }

/* ── Disposition bars ─────────────────────────────────────────────────────────
   Accent (violet) fill — differentiates from UCB1 (green) bars.
────────────────────────────────────────────────────────────────────────────── */
.disp-row { display: flex; align-items: center; gap: .4rem; margin-bottom: .28rem; }
.disp-label {
  font-size: .67rem; color: var(--text3); width: 7.5rem; flex-shrink: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.disp-bar-wrap { flex: 1; background: var(--surf3); border-radius: 2px; height: 3px; }
.disp-bar-fill { height: 3px; border-radius: 2px; background: var(--accent); }
.disp-value { font-size: .65rem; color: var(--text3); width: 2rem; text-align: right; font-family: var(--mono); }

/* ── Tensions ─────────────────────────────────────────────────────────────────
   Left border encodes severity. Body is muted — tensions are background signal.
────────────────────────────────────────────────────────────────────────────── */
.tension-item {
  background: var(--surf2); border-left: 2px solid var(--border2);
  border-radius: 0 4px 4px 0; padding: .35rem .5rem; margin-bottom: .28rem; font-size: .74rem;
}
.tension-item.high { border-left-color: var(--red); }
.tension-item.med  { border-left-color: var(--yellow); }
.tension-item.low  { border-left-color: var(--green); opacity: .65; }
.tension-item-header { display: flex; justify-content: space-between; align-items: center; }
.tension-type { font-size: .6rem; color: var(--text3); text-transform: uppercase; letter-spacing: .05em; }
.tension-sev  { font-size: .6rem; color: var(--text3); font-family: var(--mono); }
.tension-desc { color: var(--text2); margin-top: .12rem; line-height: 1.4; font-size: .73rem; }

.tension-archive-btn {
  font-size: .63rem; padding: .1rem .38rem; background: transparent;
  color: var(--text3); border: 1px solid var(--border2); border-radius: 5px;
  cursor: pointer; margin-left: .4rem; transition: color .1s;
}
.tension-archive-btn:hover { color: var(--text2); }

.tension-add-form { margin-top: .45rem; display: flex; flex-direction: column; gap: .28rem; }
.tension-add-form input, .tension-add-form select {
  background: var(--surf2); border: 1px solid var(--border2); color: var(--text2);
  padding: .28rem .45rem; border-radius: 4px; font-size: .73rem; outline: none;
}
.tension-add-form input:focus, .tension-add-form select:focus { border-color: var(--accent); }
.tension-add-form button {
  background: var(--surf3); border: 1px solid var(--border2);
  color: var(--text2); padding: .28rem .6rem; border-radius: 4px;
  font-size: .72rem; cursor: pointer; transition: color .1s;
}
.tension-add-form button:hover { color: var(--text); }

/* ── Metrics ──────────────────────────────────────────────────────────────────
   Simple key/value table. Numbers in monospace.
────────────────────────────────────────────────────────────────────────────── */
.metric-row {
  display: flex; justify-content: space-between; padding: .26rem 0;
  border-bottom: 1px solid var(--surf3); font-size: .74rem;
}
.metric-row:last-child { border-bottom: none; }
.metric-label { color: var(--text3); }
.metric-val { color: var(--text2); font-family: var(--mono); }
.metric-val.bad { color: var(--red); }
.metric-val.ok  { color: var(--green); }

/* ── Pending approvals ────────────────────────────────────────────────────────
   Approval cards have a violet left-edge to distinguish from tensions.
────────────────────────────────────────────────────────────────────────────── */
.approval-card {
  background: var(--surf2);
  border: 1px solid var(--border2);
  border-left: 2px solid var(--accent2);
  border-radius: 0 5px 5px 0; padding: .58rem .72rem; margin-bottom: .45rem; font-size: .75rem;
}
.approval-trigger { color: var(--text3); font-size: .69rem; margin-bottom: .28rem; }
.approval-changes { font-family: var(--mono); font-size: .69rem; color: var(--text2); margin-bottom: .42rem; }
.approval-change-row { margin-bottom: .14rem; }
.change-from { color: var(--text3); }
.change-to   { color: var(--accent); }
.approval-btns { display: flex; gap: .4rem; }
.btn-approve {
  padding: .28rem .7rem; background: rgba(58, 170, 120, .1); color: #4ac87a;
  border: 1px solid rgba(58, 170, 120, .3); border-radius: 4px; font-size: .72rem; cursor: pointer;
  transition: background .1s;
}
.btn-approve:hover { background: rgba(58, 170, 120, .2); }
.btn-reject {
  padding: .28rem .7rem; background: transparent; color: var(--red);
  border: 1px solid rgba(192, 72, 72, .3); border-radius: 4px; font-size: .72rem; cursor: pointer;
  transition: background .1s;
}
.btn-reject:hover { background: rgba(192, 72, 72, .1); }
.btn-validate {
  padding: .28rem .7rem; background: transparent; color: var(--text3);
  border: 1px solid var(--border2); border-radius: 4px; font-size: .72rem; cursor: pointer;
  transition: background .1s, color .1s;
}
.btn-validate:hover { background: var(--surf2); color: var(--accent); border-color: var(--accent2); }
.validation-result {
  margin-top: .35rem; font-size: .72rem; padding: .3rem .5rem;
  border-radius: 4px; background: var(--surf2); line-height: 1.4;
}
.dr-no-approval { font-size: .76rem; color: var(--text3); font-style: italic; }

/* ── Review log ───────────────────────────────────────────────────────────────
   Collapsed by default. Toggle reveals up to 220px scroll area.
────────────────────────────────────────────────────────────────────────────── */
.review-log-section { margin-top: .45rem; }
.review-log-toggle {
  background: none; border: none; color: var(--text3); font-size: .65rem;
  text-transform: uppercase; letter-spacing: .07em; cursor: pointer; padding: 0;
  transition: color .1s;
}
.review-log-toggle:hover { color: var(--text2); }
.review-log-list { max-height: 200px; overflow-y: auto; margin-top: .38rem; display: none; }
.review-log-list.open { display: block; }
.rl-item { padding: .28rem 0; border-bottom: 1px solid var(--surf3); font-size: .69rem; }
.rl-item:last-child { border-bottom: none; }
.rl-ts   { color: var(--text3); font-family: var(--mono); }
.rl-task { color: var(--text2); margin: .1rem 0; }

/* Alias — JS compatibility */
.review-log-item { padding: .28rem 0; border-bottom: 1px solid var(--surf3); font-size: .69rem; }
.review-log-item:last-child { border-bottom: none; }

/* ── Workspace strip ─────────────────────────────────────────────────────────
   Collapsible panel below chat. Initially collapsed — reduce default noise.
────────────────────────────────────────────────────────────────────────────── */
.workspace-strip {
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  background: var(--bg);
}
.workspace-toggle {
  background: none; border: none; color: var(--text3);
  font-size: .72rem; padding: .45rem .9rem; cursor: pointer;
  text-transform: uppercase; letter-spacing: .07em;
  transition: color .1s;
}
.workspace-toggle:hover { color: var(--text2); }

.workspace-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(265px, 1fr));
  gap: .7rem; padding: .7rem .9rem; max-height: 400px; overflow-y: auto;
}
.workspace-grid.hidden { display: none; }

/* Workspace cards */
.wcard {
  background: var(--surf); border: 1px solid var(--border); border-radius: 10px;
  padding: .85rem .95rem; position: relative; overflow: hidden;
}
.wcard-accent { position: absolute; top: 0; left: 0; width: 3px; height: 100%; }
.wcard h2 {
  font-size: .65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .09em; color: var(--text3); margin-bottom: .65rem;
}

/* ── Badges ───────────────────────────────────────────────────────────────────
   Semantic colour pairs. No decorative gradients.
────────────────────────────────────────────────────────────────────────────── */
.badge {
  display: inline-block; font-size: .61rem; font-weight: 700;
  padding: .1em .48em; border-radius: 5px; text-transform: uppercase; letter-spacing: .05em;
}
.badge-ready   { background: rgba(58, 170, 120, .14); color: #4ac87a;
                 border: 1px solid rgba(58, 170, 120, .28); }
.badge-active  { background: rgba(74, 143, 212, .14); color: #6ab0f0;
                 border: 1px solid rgba(74, 143, 212, .28); }
.badge-done    { background: var(--surf3); color: var(--text3); border: 1px solid var(--border2); }
.badge-warn    { background: rgba(176, 144, 0, .14); color: #c8a040;
                 border: 1px solid rgba(176, 144, 0, .28); }
.badge-neutral { background: var(--surf3); color: var(--text3); border: 1px solid var(--border2); }
/* Model badges — violet family for sonnet/opus, blue for haiku */
.badge-haiku   { background: rgba(74, 143, 212, .12); color: #6ab0f0; border: 1px solid rgba(74,143,212,.25); }
.badge-sonnet  { background: var(--accent-dim); color: #c090f0; border: 1px solid rgba(160,108,213,.28); }
.badge-opus    { background: rgba(192, 72, 72, .12); color: #d07878; border: 1px solid rgba(192,72,72,.28); }
.badge-pass    { background: rgba(58, 170, 120, .14); color: #4ac87a; border: 1px solid rgba(58,170,120,.28); }
.badge-flag    { background: rgba(176, 160, 0, .14); color: #b0a020; border: 1px solid rgba(176,160,0,.28); }
.badge-fail    { background: rgba(192, 72, 72, .14); color: var(--red); border: 1px solid rgba(192,72,72,.3); }

/* ── Workspace inner elements ───────────────────────────────────────────────── */
.sub {
  font-size: .72rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: .06em; color: var(--text3); margin: .6rem 0 .3rem;
}

.thread-row {
  border-left: 2px solid var(--border2); padding: .4rem .6rem; margin-bottom: .4rem;
}
.thread-row:hover { border-left-color: var(--accent); background: var(--surf3); }
.thread-next { font-size: .76rem; color: var(--text2); }
.blocker { font-size: .72rem; color: var(--orange); margin-top: .15rem; }

.parking-row {
  display: grid; grid-template-columns: 6.5rem 1fr; gap: .15rem .6rem;
  padding: .35rem 0; border-bottom: 1px solid var(--surf3); font-size: .78rem;
}
.parking-row:last-child { border-bottom: none; }
.parking-name   { font-weight: 600; color: var(--text2); font-size: .75rem; }
.parking-reason { color: var(--text2); }
.parking-trigger{ grid-column: 2; color: var(--text3); font-size: .72rem; }

.prompt-row { padding: .45rem .55rem; border-radius: 4px; margin-bottom: .4rem; font-size: .8rem; }
.prompt-row.ready { background: #0f1f14; border: 1px solid #1a4a2a; }
.prompt-row.done  { color: var(--text3); }
.prompt-header { display: flex; align-items: center; gap: .4rem; margin-bottom: .2rem; }
.prompt-task { font-weight: 600; margin-bottom: .15rem; }
.prompt-meta { font-size: .72rem; color: var(--text3); }

.run-btn {
  padding: .25rem .55rem; background: var(--green); color: #fff;
  border: none; border-radius: 5px; font-size: .72rem; cursor: pointer;
}
.run-btn:hover { background: #3aaa7a; }

.decision-row {
  display: grid; grid-template-columns: 5.5rem 1fr; gap: .08rem .6rem;
  padding: .4rem 0; border-bottom: 1px solid var(--surf3); font-size: .78rem;
}
.decision-row:last-child { border-bottom: none; }
.decision-date   { grid-row: 1 / 3; color: var(--text3); font-size: .7rem; padding-top: .1rem; }
.decision-text   { font-weight: 600; }
.decision-reason { color: var(--text2); font-size: .74rem; }

.week-focus ul { padding-left: 1rem; margin-bottom: .6rem; }
.week-focus li  { margin-bottom: .2rem; font-size: .8rem; }
.progress-bar-wrap { background: var(--surf3); border-radius: 2px; height: 4px; margin-bottom: .25rem; }
.progress-bar-fill { background: var(--green); height: 4px; border-radius: 2px; }
.progress-label    { font-size: .7rem; color: var(--text3); margin-bottom: .6rem; }
.checklist { display: flex; flex-direction: column; gap: .25rem; }
.check { font-size: .78rem; }
.check.done { color: var(--text3); text-decoration: line-through; }

.inbox-row { display: flex; align-items: center; gap: .5rem; font-size: .8rem; }
.artifact-item { font-size: .74rem; color: var(--text2); padding: .15rem 0; font-family: monospace; }
.empty { color: var(--text3); font-size: .78rem; font-style: italic; }

/* ── Thread viewer ────────────────────────────────────────────────────────────
   Reading mode. Generous line-height, slightly narrowed max-width for
   comfortable line-length. Accent left-border on blockquote.
────────────────────────────────────────────────────────────────────────────── */
.thread-view {
  display: flex; flex-direction: column; height: 100%;
}
.thread-view-header {
  display: flex; align-items: center; gap: .55rem;
  padding: .48rem .7rem; border-bottom: 1px solid var(--border);
  background: var(--surf); flex-shrink: 0;
}
.thread-view-back {
  background: none; border: 1px solid var(--border2); color: var(--text2);
  padding: .2rem .48rem; border-radius: 4px; cursor: pointer; font-size: .76rem;
  transition: color .1s, border-color .1s;
}
.thread-view-back:hover { color: var(--text); border-color: var(--border3); }
.thread-view-title {
  font-size: .84rem; font-weight: 600; color: var(--text); flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.thread-view-body {
  flex: 1; overflow-y: auto; padding: 1.1rem 1.3rem;
  font-size: .85rem; line-height: 1.72; color: var(--text);
  max-width: 760px;
}
.thread-view-body h1 { font-size: 1.08rem; margin: 0 0 .65rem; color: var(--text); font-weight: 700; }
.thread-view-body h2 {
  font-size: .86rem; font-weight: 700; margin: 1.1rem 0 .38rem;
  color: var(--text2); text-transform: uppercase; letter-spacing: .07em;
}
.thread-view-body h3 { font-size: .83rem; font-weight: 700; margin: .8rem 0 .28rem; color: var(--text); }
.thread-view-body p  { margin: 0 0 .65rem; }
.thread-view-body ul,
.thread-view-body ol { padding-left: 1.2rem; margin: 0 0 .65rem; }
.thread-view-body li { margin-bottom: .22rem; }
.thread-view-body code {
  background: var(--surf3); padding: .1rem .32rem; border-radius: 5px;
  font-family: var(--mono); font-size: .8rem; color: var(--text2);
}
.thread-view-body pre {
  background: var(--surf3); padding: .65rem .85rem; border-radius: 7px;
  overflow-x: auto; margin: 0 0 .65rem; border: 1px solid var(--border2);
}
.thread-view-body pre code { background: none; padding: 0; font-size: .78rem; }
.thread-view-body strong { color: var(--text); font-weight: 600; }
.thread-view-body hr { border: none; border-top: 1px solid var(--border); margin: .9rem 0; }
.thread-view-body blockquote {
  border-left: 2px solid var(--accent2); margin: 0 0 .65rem;
  padding-left: .8rem; color: var(--text2);
}

/* ── Active thread context bar ──────────────────────────────────────────────── */
.thread-ctx-bar {
  display: flex; align-items: center; gap: .5rem;
  padding: .35rem .75rem; background: var(--surf3);
  border-bottom: 1px solid var(--border2); flex-shrink: 0;
  font-size: .75rem;
}
.thread-ctx-label {
  color: var(--text3); text-transform: uppercase;
  font-size: .65rem; letter-spacing: .08em; font-weight: 700;
}
.thread-ctx-name {
  color: var(--green); font-weight: 600; flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.thread-ctx-clear {
  background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: .85rem; padding: 0 .2rem;
  line-height: 1;
}
.thread-ctx-clear:hover { color: var(--red); }
.thread-ctx-frozen {
  font-size: .65rem; color: #5c9fd4; background: rgba(92,159,212,.1);
  border: 1px solid rgba(92,159,212,.3); border-radius: 4px;
  padding: 1px 6px; letter-spacing: .05em; flex-shrink: 0;
}
.thread-ctx-expand {
  background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: .75rem; padding: 0 .2rem;
}
.thread-ctx-expand:hover { color: var(--text2); }
.thread-ctx-preview {
  font-size: .74rem; color: var(--text2); padding: .4rem .75rem .5rem;
  background: var(--surf3); border-bottom: 1px solid var(--border);
  white-space: pre-wrap; max-height: 8rem; overflow-y: auto;
  font-family: monospace; display: none;
}

/* ── Document library panel ─────────────────────────────────────────────────── */
.doc-item { display:flex; align-items:center; gap:.35rem; padding:.28rem .35rem; border-radius:5px; cursor:pointer; }
.doc-item:hover { background:var(--surf3); }
.doc-icon { font-size:.8rem; flex-shrink:0; width:1rem; text-align:center; }
.doc-name { font-size:.76rem; color:var(--text); flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.doc-source { font-size:.6rem; color:var(--text3); flex-shrink:0;
  background:var(--surf3); border:1px solid var(--border2); border-radius:2px;
  padding:0 .25rem; margin-left:.15rem; }
.doc-arch-btn { background:none; border:none; color:var(--text3); cursor:pointer; font-size:.75rem; padding:0 .15rem; opacity:0; }
.doc-item:hover .doc-arch-btn { opacity:1; }
.doc-arch-btn:hover { color:var(--red); }

/* Upload drop zone */
.upload-zone { border:1px dashed var(--border2); border-radius:4px; padding:.5rem; text-align:center;
  font-size:.72rem; color:var(--text3); cursor:pointer; margin:.4rem 0; transition:border-color .15s; }
.upload-zone:hover, .upload-zone.drag-over { border-color:var(--green); color:var(--green); }
.upload-zone input[type=file] { display:none; }

/* Active doc bar */
.doc-ctx-bar { background:var(--surf3); border-bottom:1px solid var(--border2); }
.doc-ctx-name { color:var(--orange,#b06000); font-weight:600; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* ── NO-GO mode ───────────────────────────────────────────────────────────────
   Active state: red glow — unmistakable epistemic mode signal.
────────────────────────────────────────────────────────────────────────────── */
.nogo-btn {
  background: transparent;
  border: 1px solid rgba(192, 72, 72, .4);
  color: rgba(192, 72, 72, .8); padding: .2rem .55rem; border-radius: 4px;
  font-size: .71rem; cursor: pointer; font-weight: 600; letter-spacing: .04em;
  transition: all .15s;
}
.nogo-btn:hover { background: rgba(192, 72, 72, .1); color: var(--red); }
.nogo-btn.active {
  background: rgba(192, 72, 72, .15); color: var(--red);
  border-color: var(--red); box-shadow: 0 0 0 2px rgba(192, 72, 72, .12);
}

/* ── Confidence topology bar ─────────────────────────────────────────────────── */
.topology-bar {
  display: flex; height: 4px; border-radius: 2px; overflow: hidden;
  margin-top: .4rem; gap: 1px;
}
.topo-stable    { background: var(--green); }
.topo-heuristic { background: #b08000; }
.topo-speculative { background: var(--orange, #b06000); }
.topo-required  { background: var(--red); }
.topology-legend {
  display: flex; gap: .6rem; flex-wrap: wrap;
  font-size: .65rem; color: var(--text3); margin-top: .25rem;
}
.topo-tag { display: flex; align-items: center; gap: .2rem; }
.topo-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }

/* ── Structural / Epistemic scores ───────────────────────────────────────────── */
.score-row {
  display: flex; gap: .4rem; align-items: center; margin-bottom: .3rem;
}
.score-label { font-size: .68rem; color: var(--text3); width: 6rem; flex-shrink: 0; }
.score-bar-wrap { flex: 1; background: var(--surf3); border-radius: 2px; height: 4px; }
.score-bar-fill { height: 4px; border-radius: 2px; }
.score-bar-structural { background: #b08000; }
.score-bar-epistemic  { background: var(--red); }
.score-value { font-size: .68rem; color: var(--text3); width: 2.2rem; text-align: right; }

/* ── Memory panel ─────────────────────────────────────────────────────────────
   Insights use accent left-border colour matched to kind.
   Content is clamped at 3 lines — hover to see archive action.
────────────────────────────────────────────────────────────────────────────── */
.insight-item {
  padding: .3rem .42rem; border-radius: 4px; margin-bottom: .22rem;
  border-left: 2px solid var(--border2); cursor: default;
  transition: background .1s;
}
.insight-item:hover { background: var(--surf3); }
.insight-topic {
  font-size: .63rem; color: var(--text3); text-transform: uppercase;
  letter-spacing: .07em; font-weight: 700; margin-bottom: .14rem;
}
.insight-content {
  font-size: .76rem; color: var(--text2); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
}
.insight-meta { font-size: .63rem; color: var(--text3); margin-top: .14rem; }
.insight-arch-btn {
  float: right; background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: .72rem; padding: 0 .15rem; opacity: 0;
  transition: color .1s;
}
.insight-item:hover .insight-arch-btn { opacity: 1; }
.insight-arch-btn:hover { color: var(--red); }

/* ── MemoryKind badge ────────────────────────────────────────────────────────── */
.kind-badge {
  display: inline-block; font-size: .58rem; font-weight: 700; letter-spacing: .05em;
  text-transform: uppercase; padding: .05rem .3rem; border-radius: 2px;
  margin-right: .3rem; opacity: .85;
  border: 1px solid currentColor;
}

/* ── Candidate score bar ─────────────────────────────────────────────────────── */
.cand-score-row {
  display: flex; align-items: center; gap: .35rem; margin-top: .2rem;
}
.cand-score-bar-wrap {
  flex: 1; height: 3px; background: var(--border2); border-radius: 2px; overflow: hidden;
}
.cand-score-bar {
  height: 100%; border-radius: 2px; transition: width .3s;
}
.cand-score-num { font-size: .6rem; color: var(--text3); min-width: 2.5rem; text-align: right; }
.cand-rec-badge {
  font-size: .58rem; font-weight: 700; padding: .05rem .25rem; border-radius: 2px;
  text-transform: uppercase; letter-spacing: .04em;
}
.cand-rec-promote   { background: rgba(80,200,120,.18); color: var(--ok); }
.cand-rec-reject    { background: rgba(255,80,80,.15); color: var(--red); }
.cand-rec-manual    { background: rgba(255,180,0,.15); color: var(--warning); }
.cand-rec-keep      { background: rgba(150,150,150,.12); color: var(--text3); }

/* ── Save insight button (after response) ─────────────────────────────────────── */
.save-insight-btn {
  background: none; border: 1px solid var(--border2); color: var(--text3);
  padding: .15rem .4rem; border-radius: 5px; font-size: .7rem; cursor: pointer;
  margin-top: .35rem;
}
.save-insight-btn:hover { border-color: var(--green); color: var(--green); }
.save-insight-btn.saved { color: var(--green); border-color: var(--green); }
.save-insight-btn.append-btn { border-color: rgba(94,140,200,.4); color: #7eb8f7; }
.save-insight-btn.append-btn:hover { border-color: #7eb8f7; background: rgba(94,140,200,.12); color: #9ecfff; }
.save-insight-btn.copy-btn { border-color: rgba(160,120,220,.35); color: #b89ee8; }
.save-insight-btn.copy-btn:hover { border-color: #b89ee8; background: rgba(160,120,220,.12); color: #cdbef8; }

/* ── Floating selection-copy button ───────────────────────────────────────── */
#sel-copy-btn {
  position: fixed; display: none; z-index: 5000;
  background: #252540; color: #c0b0f0; border: 1px solid #554488;
  border-radius: 7px; padding: 3px 9px; font-size: .72rem; cursor: pointer;
  box-shadow: 0 2px 10px rgba(0,0,0,.55); pointer-events: auto;
  transition: background .1s;
}
#sel-copy-btn:hover { background: #32325a; }

/* ── Copy thread button (next to clear) ───────────────────────────────────── */
.copy-thread-btn {
  background: none; border: 1px solid rgba(160,120,220,.3); color: #a08ec0;
  padding: .18rem .45rem; border-radius: 4px; font-size: .72rem; cursor: pointer;
}

/* ── Memory tabs ───────────────────────────────────────────────────────────── */
.mem-tab {
  flex: 1; background: none; border: 1px solid var(--border2);
  color: var(--text3); padding: .2rem .3rem; border-radius: 5px;
  font-size: .65rem; cursor: pointer; text-align: center;
}
.mem-tab.active { background: var(--surf3); color: var(--text1); border-color: var(--border3); }
.mem-tab:hover { color: var(--text2); }

/* ── Search modal ─────────────────────────────────────────────────────────────
   Command-palette style. Large input, compact results.
   Opens at 10vh from top — focal but not blocking full screen.
────────────────────────────────────────────────────────────────────────────── */
.search-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, .65);
  display: flex; align-items: flex-start; justify-content: center;
  padding-top: 10vh; z-index: 9999;
  backdrop-filter: blur(2px);
}
.search-box {
  background: var(--surf2); border: 1px solid var(--border3);
  border-radius: 10px; width: min(560px, 90vw);
  box-shadow: 0 12px 48px rgba(0, 0, 0, .7);
}
.search-input-row {
  display: flex; align-items: center; gap: .55rem;
  padding: .65rem .85rem; border-bottom: 1px solid var(--border2);
}
.search-icon { color: var(--text3); font-size: 1rem; }
.search-input {
  flex: 1; background: none; border: none; outline: none;
  color: var(--text); font-size: .95rem;
}
.search-input::placeholder { color: var(--text3); }
.search-close {
  background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: 1rem; padding: 0 .25rem;
  transition: color .1s;
}
.search-close:hover { color: var(--text); }
.search-results { max-height: 55vh; overflow-y: auto; padding: .35rem 0; }
.search-result {
  padding: .42rem .8rem; cursor: pointer; display: flex; gap: .6rem;
  align-items: flex-start; transition: background .08s;
}
.search-result:hover { background: var(--surf3); }
.search-result-type {
  font-size: .6rem; color: var(--text3); text-transform: uppercase;
  letter-spacing: .07em; flex-shrink: 0; padding-top: .15rem; width: 4.5rem;
}
.search-result-body { flex: 1; min-width: 0; }
.search-result-name { font-size: .8rem; color: var(--text); font-weight: 600; }
.search-result-snippet { font-size: .72rem; color: var(--text2); margin-top: .1rem;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.search-empty { padding: .85rem; text-align: center; color: var(--text3); font-size: .8rem; }
.search-filter-btn {
  padding: 3px 9px; border-radius: 7px; border: 1px solid var(--border2);
  background: transparent; color: var(--text3); font-size: .7rem;
  cursor: pointer; white-space: nowrap; transition: background .1s, color .1s;
}
.search-filter-btn:hover { background: var(--surf3); color: var(--text2); }
.search-filter-btn.active {
  background: var(--surf3); color: var(--text); border-color: var(--accent2);
}

/* ── Active project bar ──────────────────────────────────────────────────────── */
.proj-ctx-bar {
  display: flex; align-items: center; gap: .5rem;
  padding: .3rem .5rem; background: var(--surf3);
  border-radius: 5px; margin-bottom: .35rem; font-size: .74rem;
}
.proj-ctx-label { font-size: .62rem; color: var(--text3); text-transform: uppercase; letter-spacing: .06em; }
.proj-ctx-name { color: var(--green); font-weight: 600; flex: 1; }
.proj-ctx-clear { background: none; border: none; color: var(--text3); cursor: pointer; font-size: .78rem; }
.proj-ctx-clear:hover { color: var(--red); }

/* ── Research toolbar ────────────────────────────────────────────────────────── */
.research-toolbar {
  display: flex; gap: .35rem; flex-wrap: wrap;
  padding: .4rem .75rem; border-bottom: 1px solid var(--border2);
  background: var(--surf); flex-shrink: 0;
}
.research-btn {
  background: var(--surf3); border: 1px solid var(--border2);
  color: var(--text2); padding: .18rem .5rem; border-radius: 5px;
  font-size: .7rem; cursor: pointer; white-space: nowrap;
}
.research-btn:hover { border-color: var(--text3); color: var(--text); }

/* ── Thread multi-select (v0.6.4 improved) ───────────────────────────────── */
.thread-checkbox {
  appearance: none; width: 16px; height: 16px;
  border: 2px solid var(--border2); border-radius: 5px;
  background: var(--surf3); cursor: pointer; flex-shrink: 0;
  position: relative; transition: border-color .15s, background .15s;
  margin-right: 2px;
}
.thread-checkbox:hover {
  border-color: var(--green);
}
.thread-checkbox:checked {
  background: var(--green); border-color: var(--green);
}
.thread-checkbox:checked::after {
  content: '✓'; position: absolute; color: #000;
  font-size: .72rem; font-weight: 800; top: -1px; left: 2px;
}
.synthesize-btn {
  display: none; width: 100%; margin-top: .35rem;
  background: var(--surf3); border: 1px solid var(--green);
  color: var(--green); padding: .25rem; border-radius: 5px;
  font-size: .72rem; cursor: pointer; text-align: center;
}
.synthesize-btn:hover { background: var(--green); color: #000; }
.synth-counter {
  display: none; padding: 8px 14px; margin: 6px 12px;
  background: linear-gradient(135deg, rgba(42,154,106,.15), rgba(42,154,106,.05));
  border: 1.5px solid var(--green); border-radius: 8px;
  color: var(--green); font-size: .84rem; font-weight: 600;
  cursor: pointer; text-align: center; transition: background .15s, transform .1s;
}
.synth-counter:hover { background: var(--green); color: #000; transform: scale(1.02); }
.synth-counter .synth-count {
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--green); color: #000;
  font-weight: 800; font-size: .78rem; min-width: 22px; height: 22px;
  border-radius: 50%; margin-right: 6px;
}
.synth-counter.pulse {
  animation: synthPulse .35s ease-out;
}
@keyframes synthPulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.06); }
  100% { transform: scale(1); }
}

/* ── Research modal ──────────────────────────────────────────────────────────── */
.research-modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.75);
  display: flex; align-items: center; justify-content: center; z-index: 9998;
}
.research-modal {
  background: var(--surf); border: 1px solid var(--border2);
  border-radius: 6px; padding: 1.25rem; width: min(480px, 90vw);
  box-shadow: 0 8px 32px rgba(0,0,0,.6);
}
.research-modal h3 {
  font-size: .85rem; font-weight: 700; margin: 0 0 .75rem;
  color: var(--text); text-transform: uppercase; letter-spacing: .06em;
}
.research-modal input, .research-modal textarea {
  width: 100%; background: var(--surf3); border: 1px solid var(--border);
  color: var(--text); padding: .4rem .6rem; border-radius: 5px;
  font-size: .82rem; margin-bottom: .5rem; box-sizing: border-box;
}
.research-modal textarea { resize: vertical; min-height: 80px; }
.research-modal-btns {
  display: flex; gap: .5rem; justify-content: flex-end; margin-top: .5rem;
}
.research-modal-btns button {
  padding: .3rem .8rem; border-radius: 5px; font-size: .78rem; cursor: pointer; border: none;
}
.research-modal-cancel {
  background: var(--surf3); color: var(--text2);
}
.research-modal-submit {
  background: var(--green); color: #000; font-weight: 600;
}

/* ── Export buttons & menu ───────────────────────────────────────────────────── */
.export-btn {
  background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: .72rem; padding: 0 .15rem;
  opacity: 0; position: relative;
}
.thread-item:hover .export-btn,
.project-item:hover .export-btn { opacity: 1; }
.export-btn:hover { color: var(--text2); }
.export-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  background: var(--surf2);
  border: 1px solid var(--border2);
  border-radius: 8px;
  padding: 4px 0;
  min-width: 190px;
  box-shadow: 0 4px 16px rgba(0,0,0,.35);
  z-index: 999;
  display: none;
}
.export-menu.show { display: block; }
.export-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  font-size: .78rem;
  color: var(--text2);
  cursor: pointer;
  white-space: nowrap;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
}
.export-menu-item:hover {
  background: var(--surf3);
  color: var(--text);
}
.export-menu-sep {
  height: 1px;
  background: var(--border);
  margin: 3px 8px;
}

/* ── Disposition history chart ───────────────────────────────────────────────── */
.disp-history-chart {
  width: 100%; height: 80px; margin-top: .4rem; overflow: hidden;
}
.disp-history-chart svg {
  width: 100%; height: 100%;
}
.chart-line { fill: none; stroke-width: 1.5; }
.chart-zero { stroke: var(--border2); stroke-width: 1; stroke-dasharray: 2,2; }

/* ── Epistemic report panel ──────────────────────────────────────────────────── */
.report-section {
  margin-top: .6rem;
}
.report-date {
  font-size: .65rem; color: var(--text3); margin-bottom: .3rem;
}
.report-text {
  font-size: .74rem; color: var(--text2); line-height: 1.6;
  white-space: pre-wrap; max-height: 200px; overflow-y: auto;
  background: var(--surf3); padding: .5rem .6rem; border-radius: 5px;
  display: none;
  -webkit-user-select: text; user-select: text; cursor: text;
}
.report-copy-btn:hover { border-color: var(--text3); color: var(--text); }
.report-text.visible { display: block; }
.report-generate-btn {
  width: 100%; padding: .25rem; background: var(--surf3);
  border: 1px solid var(--border2); color: var(--text2);
  border-radius: 5px; font-size: .72rem; cursor: pointer; margin-bottom: .3rem;
}
.report-generate-btn:hover { border-color: var(--text3); color: var(--text); }
.report-generate-btn.generating { color: var(--text3); cursor: default; }

/* ── Model comparison ─────────────────────────────────────────────────────────── */
.compare-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.8);
  display: flex; align-items: center; justify-content: center; z-index: 9997;
}
.compare-modal {
  background: var(--surf); border: 1px solid var(--border2); border-radius: 6px;
  width: min(960px, 96vw); max-height: 88vh; display: flex; flex-direction: column;
  box-shadow: 0 8px 40px rgba(0,0,0,.7);
}
.compare-modal-header {
  display: flex; align-items: center; gap: .6rem;
  padding: .7rem 1rem; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.compare-modal-title { font-weight: 700; font-size: .85rem; flex: 1; }
.compare-modal-close {
  background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: 1.1rem;
}
.compare-modal-close:hover { color: var(--text); }
.compare-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 0;
  overflow-y: auto; flex: 1;
}
.compare-col {
  padding: .75rem; border-right: 1px solid var(--border);
}
.compare-col:last-child { border-right: none; }
.compare-col-title {
  font-size: .7rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .08em; color: var(--text3); margin-bottom: .4rem;
  display: flex; align-items: center; gap: .4rem;
}
.compare-verdict {
  display: inline-block; font-size: .65rem; padding: .1rem .3rem;
  border-radius: 2px; font-weight: 700;
}
.compare-verdict.pass { background: #1a3a1a; color: var(--green); }
.compare-verdict.flag { background: #3a3000; color: #c8a000; }
.compare-verdict.fail { background: #3a1a1a; color: var(--red); }
.compare-text {
  font-size: .76rem; color: var(--text2); line-height: 1.6;
  white-space: pre-wrap; max-height: 50vh; overflow-y: auto;
}
.compare-input-row {
  padding: .7rem 1rem; border-top: 1px solid var(--border);
  display: flex; gap: .5rem; flex-shrink: 0;
}
.compare-input {
  flex: 1; background: var(--surf3); border: 1px solid var(--border);
  color: var(--text); padding: .35rem .6rem; border-radius: 5px; font-size: .82rem;
}
.compare-run-btn {
  background: var(--green); color: #000; border: none;
  padding: .35rem .8rem; border-radius: 5px; font-weight: 700;
  font-size: .8rem; cursor: pointer;
}
.compare-run-btn:disabled { opacity: .4; cursor: default; }

/* Smooth scrolling — global */
* { scroll-behavior:smooth; }

/* ═══ v0.7+ Layout — tabbed application shell ═════════════════════════════
   Thin header, tab strip, body fills remainder.
   Active tab highlighted with accent bottom border — not background fill.
═══════════════════════════════════════════════════════════════════════════ */
html, body { height:100%; margin:0; overflow:hidden; }
body { display:flex; flex-direction:column; }

/* Application header — matches .header above but for the v0.7 shell */
.app-header {
  display:flex; align-items:center; gap:10px;
  padding:0 1rem; height:44px;
  border-bottom:1px solid var(--border);
  background:var(--surf); flex-shrink:0;
  position:relative;
}
.app-header::after {
  content:''; position:absolute; bottom:0; left:0;
  width:44px; height:2px;
  background:linear-gradient(90deg, var(--accent) 0%, transparent 100%);
}
.app-brand { display:flex; align-items:center; gap:8px; margin-right:6px; }
.app-logo {
  width:26px; height:26px;
  background:linear-gradient(135deg, var(--accent2) 0%, var(--accent) 100%);
  border-radius:6px; display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:.82rem; color:#fff; letter-spacing:-.5px;
}
.app-name { font-weight:700; font-size:.88rem; color:var(--text); }
.app-header-right { display:flex; align-items:center; gap:9px; margin-left:auto; font-size:.74rem; color:var(--text3); }

/* Tab strip — minimal pill style */
.tab-nav { display:flex; gap:1px; }
.tab-btn {
  padding:6px 16px; border:none; background:transparent;
  color:var(--text3); font-size:.84rem; font-weight:500;
  cursor:pointer; border-radius:6px;
  transition:background .12s, color .12s;
  white-space:nowrap; height:38px;
  position:relative;
}
.tab-btn:hover { background:var(--surf3); color:var(--text2); }
.tab-btn.active {
  background:transparent; color:var(--text); font-weight:600;
}
/* Active indicator: bottom accent line */
.tab-btn.active::after {
  content:''; position:absolute; bottom:3px; left:16px; right:16px;
  height:2px; background:var(--accent); border-radius:2px;
}

.app-shell { flex:1; overflow:hidden; display:flex; flex-direction:row; min-height:0; }
.app-body { flex:1; overflow:hidden; display:flex; flex-direction:column; min-height:0; }

/* ── Vertical ribbon (Obsidian-style) ─────────────────────────────────────────
   44px left strip replacing the horizontal tab bar.
   Active indicator: left-side accent bar via box-shadow.
────────────────────────────────────────────────────────────────────────────── */
.ribbon {
  width:44px; flex-shrink:0;
  background:var(--surf); border-right:1px solid var(--border);
  display:flex; flex-direction:column; align-items:center;
  padding:6px 0; gap:2px; overflow:visible; z-index:5;
}
.ribbon-btn {
  width:36px; height:36px;
  display:flex; align-items:center; justify-content:center;
  border:none; background:transparent; border-radius:4px;
  cursor:pointer; color:var(--text3); font-size:1.05rem;
  transition:background .12s, color .12s;
  position:relative; flex-shrink:0;
}
.ribbon-btn:hover { background:var(--surf3); color:var(--text2); }
.ribbon-btn.active {
  color:var(--accent); background:var(--accent-dim);
  box-shadow:inset 3px 0 0 var(--accent);
}
.ribbon-spacer { flex:1; }
.ribbon-sep { width:24px; height:1px; background:var(--border2); margin:4px 0; flex-shrink:0; }
.tab-page { flex:1; overflow:hidden; flex-direction:column; min-height:0; }

/* ── Matylda Lab: hypothesis lifecycle ─────────────────────────────────── */
.lab-layout { height:100%; display:flex; flex-direction:column; overflow:hidden; background:var(--bg); }
.lab-toolbar { display:grid; grid-template-columns:minmax(180px,1.25fr) minmax(220px,2fr) 110px auto; gap:8px; padding:12px 16px; border-bottom:1px solid var(--border); background:var(--surf); }
.lab-input, .lab-select { min-width:0; border:1px solid var(--border2); border-radius:6px; background:var(--surf2); color:var(--text); padding:8px 10px; font-size:.82rem; outline:none; }
.lab-input:focus, .lab-select:focus { border-color:var(--accent); }
.lab-create { border:1px solid var(--accent); border-radius:6px; background:var(--accent); color:#fff; padding:8px 13px; cursor:pointer; font-weight:700; }
.lab-create:hover { filter:brightness(1.08); }
.lab-board { flex:1; display:grid; grid-template-columns:repeat(4,minmax(210px,1fr)); overflow-x:auto; align-items:stretch; }
.lab-column { min-width:210px; padding:14px; border-right:1px solid var(--border); overflow-y:auto; }
.lab-column:last-child { border-right:none; }
.lab-column-head { display:flex; align-items:center; justify-content:space-between; padding:2px 1px 11px; margin-bottom:8px; border-bottom:1px solid var(--border2); color:var(--text3); font-size:.65rem; font-weight:700; letter-spacing:.08em; }
.lab-column-head b { color:var(--text2); font-size:.72rem; }
.lab-card { padding:10px; margin-bottom:8px; border:1px solid var(--border2); border-radius:7px; background:var(--surf); }
.lab-card-incubator { border-left:3px solid #d29b42; }
.lab-card-active { border-left:3px solid var(--green); }
.lab-card-waiting { border-left:3px solid #5c80c4; }
.lab-card-cemetery { border-left:3px solid #8a6b79; opacity:.86; }
.lab-card-top, .lab-actions { display:flex; align-items:center; justify-content:space-between; gap:5px; }
.lab-state { color:var(--text3); font-size:.62rem; text-transform:uppercase; letter-spacing:.06em; }
.lab-cost { color:var(--accent); font-size:.68rem; white-space:nowrap; }
.lab-card h3 { margin:7px 0 4px; font-size:.82rem; line-height:1.3; }
.lab-card p, .lab-reentry, .lab-parent { margin:0; color:var(--text2); font-size:.73rem; line-height:1.45; white-space:pre-wrap; }
.lab-reentry, .lab-parent { margin-top:6px; color:var(--text3); }
.lab-actions { justify-content:flex-start; flex-wrap:wrap; margin-top:9px; }
.lab-actions button { padding:4px 7px; border:1px solid var(--border2); border-radius:5px; background:var(--surf3); color:var(--text2); font-size:.69rem; cursor:pointer; }
.lab-actions button:hover { border-color:var(--accent); color:var(--text); }
.lab-actions .lab-action-muted { background:transparent; color:var(--text3); }
.lab-empty, .lab-overflow { padding:12px 3px; color:var(--text3); font-size:.73rem; }
.lab-overflow { border-top:1px dashed var(--border2); margin-top:5px; }
@media (max-width:900px) { .lab-toolbar { grid-template-columns:1fr 1fr; } .lab-board { grid-template-columns:repeat(4,250px); } }

/* Work tab layout */
.work-layout { display:flex; height:100%; overflow:hidden; }
.work-sidebar {
  width:238px; min-width:190px; border-right:1px solid var(--border);
  background:var(--surf); overflow-y:auto;
  display:flex; flex-direction:column; flex-shrink:0;
}
.sidebar-section { padding:3px 0; border-bottom:1px solid var(--border2); }
.sidebar-section:last-child { border-bottom:none; flex:1; }
.sidebar-header {
  display:flex; align-items:center; justify-content:space-between;
  padding:9px 12px 5px;
}
.sidebar-header > span {
  font-size:.63rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text3);
}
.sidebar-header-actions { display:flex; gap:2px; }

/* Override icon-btn for sidebar context (size already defined above) */
.work-main { flex:1; display:flex; flex-direction:column; overflow:hidden; background:var(--bg); }

/* ── SM Findings cards (page-sleeping) ───────────────────────────────────── */
.sm-finding-card {{
  background:var(--surf2); border:1px solid var(--border2); border-radius:10px;
  padding:9px 11px; margin-bottom:7px;
}}
.sm-finding-header {{
  display:flex; align-items:center; gap:5px; margin-bottom:4px; flex-wrap:wrap;
}}
.sm-finding-type {{
  font-size:.68rem; font-weight:600; color:var(--text3);
  background:var(--surf3); border-radius:5px; padding:1px 5px;
}}
.sm-finding-title {{
  font-size:.78rem; font-weight:600; color:var(--text); margin-bottom:3px; line-height:1.35;
}}
.sm-finding-desc {{
  font-size:.72rem; color:var(--text2); line-height:1.45; margin-bottom:7px;
}}
.sm-finding-actions {{ display:flex; gap:6px; }}
.sm-btn-approve {{
  padding:3px 10px; border-radius:7px; border:1px solid rgba(92,164,114,.5);
  background:rgba(92,164,114,.08); color:#5ca472; font-size:.73rem; cursor:pointer;
  transition:background .12s;
}}
.sm-btn-approve:hover {{ background:rgba(92,164,114,.18); }}
.sm-btn-dismiss {{
  padding:3px 10px; border-radius:7px; border:1px solid var(--border2);
  background:transparent; color:var(--text3); font-size:.73rem; cursor:pointer;
  transition:background .12s;
}}
.sm-btn-dismiss:hover {{ background:var(--surf3); color:var(--text2); }}

/* ── NO-GO sidebar panel ──────────────────────────────────────────────────── */
.nogo-sidebar-header {
  display:flex; align-items:center; justify-content:space-between;
  padding:9px 12px 5px; cursor:pointer; user-select:none;
}
.nogo-sidebar-header:hover { background:var(--surf2); }
.nogo-sidebar-header > span {
  font-size:.63rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--red); opacity:.85;
}
.nogo-sidebar-arrow { color:var(--text3); font-size:.65rem; }
.nogo-traj-list { padding:2px 6px 6px; }
.nogo-traj-item {
  display:flex; align-items:center; justify-content:space-between;
  padding:4px 8px; font-size:.73rem; border-radius:7px; margin:2px 0;
}
.nogo-traj-item.nogo-high { background:rgba(192,72,72,.12); color:var(--red); }
.nogo-traj-item.nogo-mid  { background:var(--surf2); color:var(--text2); }
.nogo-traj-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:140px; }
.nogo-traj-risk { font-weight:700; flex-shrink:0; margin-left:6px; font-size:.7rem; }
.chat-history { flex:1; overflow-y:auto; padding:18px 22px; display:flex; flex-direction:column; gap:14px; min-height:0; scroll-behavior:smooth; }

/* v0.7 input area — use the new .input-row-wrap defined above */
.chat-input-area { flex-shrink:0; border-top:1px solid var(--border); background:var(--surf); padding:12px 16px; display:flex; flex-direction:column; gap:8px; }
.input-row {
  display:flex; align-items:flex-end; gap:9px;
  background:var(--surf2); border:1px solid var(--border2);
  border-radius:12px; padding:9px 11px;
  transition:border-color .15s, box-shadow .15s;
}
.input-row:focus-within {
  border-color:var(--accent2);
  box-shadow:0 0 0 3px var(--accent-dim);
}
.attach-btn {
  cursor:pointer; font-size:1.15rem; color:var(--text3);
  background:none; border:none; padding:4px 6px;
  border-radius:6px; flex-shrink:0; line-height:1;
  display:flex; align-items:center; transition:color .15s, background .15s;
  min-height:34px;
}
.attach-btn:hover { color:var(--accent); background:var(--surf3); }
/* chat-textarea defined already */
.input-send-col { display:flex; flex-direction:row; align-items:center; gap:5px; flex-shrink:0; }

/* send-btn already redefined above — override size for v0.7 layout */
.input-send-col .send-btn { width:36px; height:36px; border-radius:9px; font-size:1rem; }

.nogo-btn {
  padding:0 9px; border-radius:7px;
  border:1px solid var(--border2); background:transparent;
  color:var(--text3); font-size:.73rem; cursor:pointer;
  height:36px; display:flex; align-items:center;
  transition:color .1s, border-color .1s, background .1s;
}
.nogo-btn.active {
  border-color:rgba(192,72,72,.5); color:var(--red);
  background:rgba(192,72,72,.08);
}
.clear-btn2 {
  padding:4px 9px; border-radius:7px; border:1px solid var(--border2);
  background:transparent; color:var(--text3); font-size:.75rem;
  cursor:pointer; min-height:26px; transition:color .1s;
}
.clear-btn2:hover { color:var(--text2); }
.input-meta-row { display:flex; gap:8px; align-items:center; }
.input-meta-label { font-size:.78rem; color:var(--text3); flex-shrink:0; }
.url-input,.save-input {
  flex:1; background:var(--surf2); border:1px solid var(--border2);
  border-radius:6px; color:var(--text2); font-size:.8rem; padding:6px 9px; outline:none;
}
.url-input:focus,.save-input:focus { border-color:var(--accent); }
.fetch-btn {
  padding:6px 11px; border-radius:6px; border:1px solid var(--border2);
  background:var(--surf3); color:var(--text2); font-size:.8rem;
  cursor:pointer; min-height:32px; transition:color .1s;
}
.fetch-btn:hover { color:var(--text); }
.synthesize-btn {
  width:calc(100% - 20px); margin:3px 10px 5px;
  padding:8px 12px; background:var(--surf2);
  border:1px solid var(--border2); border-radius:10px;
  color:var(--text2); font-size:.82rem; cursor:pointer;
  text-align:left; min-height:34px;
  transition:background .12s, color .12s;
}
.synthesize-btn:hover { background:var(--surf3); color:var(--text); }

/* ── Morning briefing card ─────────────────────────────────────────────────── */
.briefing-card {
  background:linear-gradient(135deg, #0e1830 0%, #0d1828 60%, #0a1220 100%);
  border:1px solid rgba(74, 100, 160, .35); border-radius:12px;
  padding:16px 20px; margin-bottom:4px;
}
.briefing-header { display:flex; align-items:center; gap:9px; margin-bottom:12px; }
.briefing-icon { font-size:1.3rem; }
.briefing-title { font-size:.92rem; font-weight:700; color:#8ab4f8; }
.briefing-gap { font-size:.72rem; color:#4a6a9a; margin-left:auto; }
.briefing-section { margin-bottom:12px; }
.briefing-section-label {
  font-size:.62rem; font-weight:700; text-transform:uppercase;
  letter-spacing:.1em; color:#4a6a9a; margin-bottom:5px;
}
.briefing-synthesis { font-size:.86rem; line-height:1.65; color:#b8ccf0; }
.briefing-connection {
  display:flex; align-items:flex-start; gap:7px;
  padding:6px 9px; background:rgba(20,48,100,.4);
  border-radius:10px; margin-bottom:4px; font-size:.8rem; color:#90acd8;
}
.briefing-connection-icon { flex-shrink:0; color:#5c80c4; }
.briefing-connection-threads { flex:1; }
.briefing-connection-threads strong { color:#8ab4f8; }
.briefing-connection-kws { font-size:.7rem; color:#4a6a9a; margin-top:2px; }
.briefing-dismiss {
  font-size:.73rem; color:#4a6a9a; background:none;
  border:1px solid rgba(74,100,160,.3); border-radius:7px; padding:3px 10px; cursor:pointer;
  transition:color .1s, border-color .1s;
}
.briefing-dismiss:hover { color:#8ab4f8; border-color:rgba(74,100,160,.6); }

/* ── System health ─────────────────────────────────────────────────────────── */
.sys-health-row {
  display:flex; align-items:center; justify-content:space-between;
  padding:4px 0; border-bottom:1px solid var(--border2); font-size:.73rem;
}
.sys-health-row:last-child { border-bottom:none; }
.sys-health-label { color:var(--text3); }
.sys-health-val { font-weight:700; font-family:var(--mono); }
.sys-health-val.ok { color:var(--green); }
.sys-health-val.warn { color:#c8a040; }
.sys-health-val.bad { color:var(--red); }
.sys-health-score {
  margin-top:7px; padding:5px 9px; background:var(--surf2);
  border-radius:7px; display:flex; align-items:center;
  justify-content:space-between; font-size:.72rem;
}
.sys-health-score-label { color:var(--text3); }
.sys-health-score-bar { flex:1; height:3px; background:var(--surf3); border-radius:2px; margin:0 8px; overflow:hidden; }
.sys-health-score-fill { height:100%; border-radius:2px; transition:width .4s; }

/* ── Active project context bar ────────────────────────────────────────────── */
.proj-ctx-bar {
  display:flex; align-items:center; gap:6px;
  padding:6px 12px; background:var(--surf2);
  border-bottom:1px solid var(--border2); font-size:.74rem;
}
.proj-ctx-label { color:var(--text3); font-size:.62rem; text-transform:uppercase; letter-spacing:.06em; }
.proj-ctx-name { color:var(--green); font-weight:600; flex:1; }
.proj-ctx-clear {
  background:none; border:none; color:var(--text3);
  cursor:pointer; font-size:.88rem; padding:0 2px;
  transition:color .1s;
}
.proj-ctx-clear:hover { color:var(--red); }

/* ── Library tab layout ────────────────────────────────────────────────────── */
.library-layout { display:flex; flex-direction:column; height:100%; overflow:hidden; }
.library-toolbar {
  display:flex; align-items:center; gap:9px;
  padding:9px 14px; border-bottom:1px solid var(--border);
  background:var(--surf); flex-shrink:0;
}
.lib-view-switcher {
  display:flex; gap:2px; background:var(--surf2);
  border-radius:10px; padding:2px;
}
.lib-switch-btn {
  padding:5px 15px; border:none; background:transparent;
  color:var(--text3); font-size:.82rem; border-radius:7px;
  cursor:pointer; font-weight:500; min-height:30px;
  transition:background .12s, color .12s;
}
.lib-switch-btn.active {
  background:var(--surf); color:var(--text);
  font-weight:700; box-shadow:0 1px 4px rgba(0,0,0,.3);
}
.lib-search {
  background:var(--surf2); border:1px solid var(--border2);
  border-radius:6px; color:var(--text2); font-size:.82rem;
  padding:6px 11px; outline:none; width:200px;
  transition:border-color .15s;
}
.lib-search:focus { border-color:var(--accent); }
.library-body { display:flex; flex:1; overflow:hidden; min-height:0; }
.lib-sidebar { width:230px; border-right:1px solid var(--border); overflow-y:auto; background:var(--surf); flex-shrink:0; padding:6px 0; }
.lib-main { flex:1; overflow-y:auto; padding:14px 18px; display:flex; flex-direction:column; gap:12px; }
.lib-detail { padding:13px 15px; background:var(--surf); border:1px solid var(--border2); border-radius:9px; font-size:.83rem; }
.lib-detail-empty { color:var(--text3); font-size:.82rem; padding:28px; text-align:center; }
.lib-section { background:var(--surf); border:1px solid var(--border2); border-radius:9px; padding:11px 15px; }
.lib-section-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:9px; }
.lib-section-header > span { font-size:.63rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; color:var(--text3); }
.attach-btn-lib {
  cursor:pointer; font-size:.76rem; color:var(--text3);
  background:var(--surf2); border:1px solid var(--border2);
  padding:4px 9px; border-radius:7px; min-height:28px;
  transition:color .1s, background .1s;
}
.attach-btn-lib:hover { color:var(--text); background:var(--surf3); }
/* Thread link items in library */
.thread-link-item { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid var(--border2); font-size:.8rem; }
.thread-link-item:last-child { border-bottom:none; }
.thread-link-url { flex:1; color:var(--green); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer; }
.thread-link-url:hover { text-decoration:underline; }
.thread-link-del { background:none; border:none; color:var(--text3); cursor:pointer; font-size:.85rem; padding:2px 5px; border-radius:4px; }
.thread-link-del:hover { color:#e74c3c; }
.link-add-row { display:flex; gap:6px; margin-top:8px; }
.link-add-input { flex:1; background:var(--surf2); border:1px solid var(--border2); border-radius:6px; color:var(--text2); font-size:.8rem; padding:6px 9px; outline:none; }
.link-add-input:focus { border-color:var(--green); }
.link-add-btn { padding:6px 12px; border-radius:6px; border:1px solid var(--border2); background:var(--surf3); color:var(--text1); font-size:.8rem; cursor:pointer; white-space:nowrap; }
.analytics-layout { display:flex; height:100%; overflow:hidden; }
.analytics-col {
  flex:1; overflow-y:auto; padding:14px 16px;
  display:flex; flex-direction:column; gap:11px;
  border-right:1px solid var(--border);
}
.analytics-col:last-child { border-right:none; }
.analytics-col-header {
  font-size:.63rem; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--text3);
  padding:5px 2px 10px; border-bottom:1px solid var(--border2); margin-bottom:3px;
}
.form-btn {
  padding:7px 14px; border-radius:6px; border:1px solid var(--border2);
  background:var(--surf3); color:var(--text); font-size:.83rem;
  cursor:pointer; min-height:34px; transition:background .12s;
}
.form-btn:hover { background:var(--surf4); }
.form-btn.secondary { background:transparent; color:var(--text3); }
.research-toolbar-wrap { border-bottom:1px solid var(--border2); background:var(--surf); flex-shrink:0; }
.research-toolbar-toggle {
  display:flex; align-items:center; gap:6px; padding:5px 14px;
  font-size:.63rem; font-weight:700; letter-spacing:.07em;
  text-transform:uppercase; color:var(--text3); cursor:pointer;
  user-select:none; border:none; background:none; width:100%; text-align:left;
  transition:color .1s;
}
.research-toolbar-toggle:hover { color:var(--text2); }
.research-toolbar-arrow { transition:transform .2s; display:inline-block; }
.research-toolbar-arrow.open { transform:rotate(90deg); }
.research-toolbar {
  display:flex; gap:6px; padding:5px 14px 9px; overflow-x:auto; flex-shrink:0;
}
.research-toolbar.hidden { display:none; }
.research-btn {
  padding:8px 14px; border-radius:10px; border:1px solid var(--border2);
  background:var(--surf2); color:var(--text2); font-size:.85rem;
  cursor:pointer; white-space:nowrap; min-height:36px; font-weight:500;
  transition:background .12s, color .12s, border-color .12s;
}
.research-btn:hover { background:var(--surf3); color:var(--text); border-color:var(--border3); }

/* ── v0.6 native app feel ─────────────────────────────────────────────────── */
body { -webkit-font-smoothing:antialiased; }
.left-panel, .toolbar-btn, .silo-card, .section-header { -webkit-user-select:none; user-select:none; }
button:focus:not(:focus-visible) { outline:none; }
a { cursor:default; }
a.ext-link { cursor:pointer; }
"""

# ── JavaScript ────────────────────────────────────────────────────────────────

_JS = f"""
const API = 'http://localhost:{PORT}';
let conversation = []; // {{role, content, meta?}}
let activeThread = null; // {{stem, title, content}}
let activeDoc = null;   // {{name, path_rel, content}}
let noGoMode = false;
let pendingApprovalId = null;

// ── Per-thread conversation storage ──────────────────────────────────────────
const _threadConversations = {{}}; // {{[stem]: message[]}}
let _streamAbortCtrl = null;     // AbortController for current stream
let _isStreaming = false;        // true while AI is generating
let _streamingStem = null;       // stem of the thread currently streaming
let _streamGeneration = 0;       // incremented each sendMessage — prevents stale finally from corrupting new stream

// ── localStorage persistence ──────────────────────────────────────────────────
const _CONV_PREFIX = 'ml_conv_';
const _CONV_MAX_MSGS = 40;       // max messages stored per thread
const _CONV_MAX_CONTENT = 8000;  // max chars per message content (trim long responses)

// Returns the storage key for the current context.
// '__free__' is used when no thread is active (free chat).
function _currentStem() {{
  return activeThread ? activeThread.stem : '__free__';
}}

function _persistConversation(stem, msgs) {{
  try {{
    const limited = msgs.slice(-_CONV_MAX_MSGS).map(m => ({{
      role: m.role,
      content: (m.content || '').slice(0, _CONV_MAX_CONTENT),
      meta: m.meta ? {{
        model_key: m.meta.model_key,
        saved_to:  m.meta.saved_to,
        aborted:   m.meta.aborted,
        error:     m.meta.error,
      }} : undefined,
    }}));
    localStorage.setItem(_CONV_PREFIX + stem, JSON.stringify(limited));
  }} catch(e) {{ /* storage full or unavailable */ }}
}}

function _recallConversation(stem) {{
  try {{
    const raw = localStorage.getItem(_CONV_PREFIX + stem);
    return raw ? JSON.parse(raw) : null;
  }} catch(e) {{ return null; }}
}}

function _forgetConversation(stem) {{
  try {{ localStorage.removeItem(_CONV_PREFIX + stem); }} catch(e) {{}}
}}

function _saveCurrentConversation() {{
  // Runs on every thread switch — save regardless of whether a thread is active.
  // '__free__' key covers the threadless (free chat) context.
  const stem = _currentStem();
  const msgs = conversation.map(m => {{
    if (m.meta && m.meta.streaming) {{
      return m.content
        ? {{role: m.role, content: m.content, meta: {{aborted: true}}}}
        : null; // empty placeholder — discard
    }}
    return m;
  }}).filter(Boolean);
  if (activeThread) _threadConversations[activeThread.stem] = msgs;
  _persistConversation(stem, msgs); // survive page refresh
}}
function _loadConversation(stem) {{
  // In-memory first (current session), then localStorage (previous session)
  if (_threadConversations[stem]) {{
    conversation = [..._threadConversations[stem]];
  }} else {{
    const recalled = _recallConversation(stem);
    conversation = recalled || [];
    if (recalled) _threadConversations[stem] = recalled; // restore to memory
  }}
  renderConversation();
  scrollChat();
}}
function _abortStream() {{
  if (_streamAbortCtrl) {{ _streamAbortCtrl.abort(); _streamAbortCtrl = null; }}
  _isStreaming = false;
  _streamingStem = null;
  _streamGeneration++; // invalidate the running sendMessage's finally so it won't undo our cleanup
  const btn = document.getElementById('send-btn');
  const spin = document.getElementById('spinner');
  if (btn) btn.disabled = false;
  if (spin) spin.style.display = 'none';
  if (conversation.length && conversation[conversation.length-1].meta &&
      conversation[conversation.length-1].meta.streaming) {{
    conversation.pop();
  }}
}}

// ── Tab navigation (v0.7) ────────────────────────────────────────────────────
function switchTab(name) {{
  ['work','library','lab','analytics','sleeping'].forEach(t => {{
    const p = document.getElementById('page-' + t);
    if (p) p.style.display = 'none';
    const b = document.getElementById('tab-btn-' + t);
    if (b) b.classList.remove('active');
  }});
  const page = document.getElementById('page-' + name);
  const btn  = document.getElementById('tab-btn-' + name);
  if (page) page.style.display = 'flex';
  if (btn)  btn.classList.add('active');
  if (name === 'library')   loadLibraryTab();
  if (name === 'lab')       loadLab();
  if (name === 'analytics') loadAnalyticsTab();
  if (name === 'sleeping')  loadSleepingTab();
}}


function loadLibraryTab() {{
  if (typeof loadDocs === 'function') loadDocs();
  if (typeof loadMemory === 'function') loadMemory();
  if (typeof loadAllSilos === 'function') loadAllSilos();
  if (typeof loadSessionPanel === 'function') loadSessionPanel();
  loadLibView();
}}

function loadAnalyticsTab() {{
  if (typeof loadDarkroom === 'function') loadDarkroom();
  if (typeof runSleepingMatylda !== 'function') {{}} // sm loads on demand
  if (typeof loadResearchTraces === 'function') loadResearchTraces();
  if (typeof loadUcb1Stats === 'function') loadUcb1Stats();
  if (typeof loadProjectPanel === 'function') loadProjectPanel();
}}

// ── Matylda Lab: explicit hypothesis lifecycle ───────────────────────────────
let _labOverview = null;
const _labStateLabels = {{
  seed: 'Ziarno', incubator: 'Inkubator', exploration: 'Eksploracja',
  working_model: 'Model roboczy', waiting_room: 'Poczekalnia', cemetery: 'Kostnica'
}};

async function loadLab() {{
  const board = document.getElementById('lab-board');
  if (!board) return;
  try {{
    const resp = await fetch(API + '/api/hypotheses');
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    _labOverview = data;
    renderLab(data);
  }} catch (e) {{
    board.innerHTML = '<div class="lab-empty">Nie udało się wczytać rejestru: ' + escHtml(e.message) + '</div>';
  }}
}}

function labCards(items, kind) {{
  if (!items || !items.length) return '<div class="lab-empty">Brak rekordów</div>';
  return items.map(item => {{
    const note = item.description || item.next_test || item.cemetery_reason || 'Bez notatki.';
    const parent = item.parent_id ? '<div class="lab-parent">revival z ' + escHtml(item.parent_id) + '</div>' : '';
    let actions = '';
    if (kind === 'incubator') actions = item.state === 'seed'
      ? '<button onclick="labTransition(&quot;' + item.id + '&quot;,&quot;incubator&quot;)">Do inkubatora</button>'
      : '<button onclick="labTransition(&quot;' + item.id + '&quot;,&quot;exploration&quot;)">Rozwiń</button>';
    if (kind === 'active') actions = item.state === 'exploration'
      ? '<button onclick="labTransition(&quot;' + item.id + '&quot;,&quot;working_model&quot;)">Model roboczy</button>'
      : '<button onclick="labTransition(&quot;' + item.id + '&quot;,&quot;waiting_room&quot;)">Do poczekalni</button><button class="lab-action-muted" onclick="labTransition(&quot;' + item.id + '&quot;,&quot;cemetery&quot;)">Zakończ</button>';
    if (kind === 'waiting') actions = '<button onclick="labTransition(&quot;' + item.id + '&quot;,&quot;working_model&quot;)">Wznów</button><button class="lab-action-muted" onclick="labTransition(&quot;' + item.id + '&quot;,&quot;cemetery&quot;)">Zakończ</button>';
    if (kind === 'cemetery') actions = '<button onclick="labRevive(&quot;' + item.id + '&quot;)">Wskrześ</button>';
    return '<article class="lab-card lab-card-' + kind + '">' +
      '<div class="lab-card-top"><span class="lab-state">' + escHtml(_labStateLabels[item.state] || item.state) + '</span><span class="lab-cost">' + escHtml(item.exploration_cost || '—') + '</span></div>' +
      '<h3>' + escHtml(item.title) + '</h3><p>' + escHtml(note) + '</p>' +
      (item.reentry_condition ? '<div class="lab-reentry">powrót: ' + escHtml(item.reentry_condition) + '</div>' : '') +
      parent + '<div class="lab-actions">' + actions + '</div></article>';
  }}).join('');
}}

function renderLab(data) {{
  const by = data.by_state || {{}};
  const incubator = [...(by.seed || []), ...(by.incubator || [])];
  const active = [...(by.exploration || []), ...(by.working_model || [])];
  const waiting = data.focus_waiting || [];
  const cemetery = by.cemetery || [];
  const board = document.getElementById('lab-board');
  if (!board) return;
  board.innerHTML =
    '<section class="lab-column"><div class="lab-column-head"><span>INKUBATOR</span><b>' + incubator.length + '</b></div>' + labCards(incubator, 'incubator') + '</section>' +
    '<section class="lab-column"><div class="lab-column-head"><span>EKSPLORACJA</span><b>' + active.length + '</b></div>' + labCards(active, 'active') + '</section>' +
    '<section class="lab-column"><div class="lab-column-head"><span>POCZEKALNIA</span><b>' + waiting.length + '/' + (data.focus_waiting_limit || 7) + '</b></div>' +
      labCards(waiting, 'waiting') + (data.waiting_overflow ? '<div class="lab-overflow">+' + data.waiting_overflow + ' poza limitem uwagi</div>' : '') + '</section>' +
    '<section class="lab-column"><div class="lab-column-head"><span>KOSTNICA</span><b>' + cemetery.length + '</b></div>' + labCards(cemetery, 'cemetery') + '</section>';
}}

async function createLabHypothesis() {{
  const title = document.getElementById('lab-new-title');
  const description = document.getElementById('lab-new-note');
  const cost = document.getElementById('lab-new-cost');
  if (!title || !title.value.trim()) {{ title && title.focus(); return; }}
  const resp = await fetch(API + '/api/hypotheses', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{title: title.value.trim(), fields: {{description: description.value.trim(), exploration_cost: cost.value}}}})
  }});
  const data = await resp.json();
  if (data.error) {{ alert(data.error); return; }}
  title.value = ''; description.value = ''; cost.value = '30 min';
  loadLab();
}}

async function labTransition(id, state) {{
  const fields = {{}};
  if (state === 'waiting_room') {{
    const evidence = prompt('Jaki jest obecny stan dowodów?');
    const test = evidence && prompt('Jakiego testu lub dowodu jeszcze brakuje?');
    const condition = test && prompt('Warunek powrotu do pracy:');
    const reviewDate = condition && prompt('Data przeglądu (YYYY-MM-DD):');
    if (!evidence || !test || !condition || !reviewDate) return;
    fields.current_evidence = evidence.trim();
    fields.missing_test = test.trim();
    fields.reentry_condition = condition.trim();
    fields.review_date = reviewDate.trim();
  }}
  if (state === 'cemetery') {{
    const reason = prompt('Dlaczego ten model trafia do Kostnicy?');
    const record = reason && prompt('Link lub identyfikator testu, decyzji albo przeglądu:');
    if (!reason || !record) return;
    fields.cemetery_reason = reason.trim();
    fields.cemetery_record = record.trim();
  }}
  const resp = await fetch(API + '/api/hypotheses/' + encodeURIComponent(id) + '/transition', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{state, fields}})
  }});
  const data = await resp.json();
  if (data.error) {{ alert(data.error); return; }}
  loadLab();
}}

async function labRevive(id) {{
  const resp = await fetch(API + '/api/hypotheses/' + encodeURIComponent(id) + '/revive', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{}})
  }});
  const data = await resp.json();
  if (data.error) {{ alert(data.error); return; }}
  loadLab();
}}

let _libView = 'threads';
let _libSelectedId = '';
function switchLibView(view) {{
  _libView = view;
  document.querySelectorAll('.lib-switch-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('lib-btn-' + view);
  if (btn) btn.classList.add('active');
  _libSelectedId = '';
  const detail = document.getElementById('lib-detail');
  if (detail) detail.innerHTML = '<div class="lib-detail-empty">← Wybierz wątek lub projekt</div>';
  loadLibView();
}}

function loadLibView() {{
  const el = document.getElementById('lib-list');
  if (!el) return;
  const endpoint = _libView === 'projects'
    ? API + '/api/library/projects'
    : API + '/api/library/threads';
  fetch(endpoint).then(r => r.json()).then(data => {{
    const items = _libView === 'projects' ? (data.projects || []) : (data.threads || []);
    if (!items.length) {{ el.innerHTML = '<div class="empty" style="padding:12px">Brak elementów</div>'; return; }}
    el.innerHTML = items.map(item => {{
      const name = item.title || item.name || item.stem || item.id || '—';
      const id   = item.stem || item.id || '';
      const isActive = id === _libSelectedId;
      const domain = item.domain && item.domain !== '—' ? `<span style="font-size:.65rem;color:var(--text3)">${{escHtml(item.domain)}}</span>` : '';
      const _safeName = escHtml(name).split("'").join('&#39;');
      return `<div class="thread-item${{isActive ? ' active' : ''}}" style="padding:9px 14px;cursor:pointer;border-radius:0" onclick="selectLibItem('${{escHtml(id)}}','${{_safeName}}')">
        <div style="font-size:.84rem;color:var(--text${{isActive?'1':'2'}});font-weight:${{isActive?'600':'400'}};overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{escHtml(name)}}</div>
        ${{domain}}
      </div>`;
    }}).join('');
  }}).catch(() => {{ el.innerHTML = '<div class="empty" style="padding:12px">Błąd ładowania</div>'; }});
}}

async function selectLibItem(id, name) {{
  _libSelectedId = id;
  loadLibView(); // refresh highlight
  const detail = document.getElementById('lib-detail');
  if (!detail) return;
  detail.innerHTML = `<div style="font-size:.95rem;font-weight:700;margin-bottom:4px">${{escHtml(name)}}</div>
    <div style="font-size:.72rem;color:var(--text3);margin-bottom:12px">ID: ${{escHtml(id)}}</div>
    <div style="font-size:.72rem;color:var(--text3)">ładowanie…</div>`;

  if (_libView === 'threads') {{
    // Load thread content + links in parallel
    const [contentResp, linksResp] = await Promise.all([
      fetch(API + '/api/library/threads/content?stem=' + encodeURIComponent(id)).then(r=>r.json()).catch(()=>({{}})),
      fetch(API + '/api/library/thread-links?stem=' + encodeURIComponent(id)).then(r=>r.json()).catch(()=>({{links:[]}})),
    ]);
    const content = contentResp.content || '';
    const links   = linksResp.links || [];

    detail.innerHTML = `
      <div style="font-size:.95rem;font-weight:700;margin-bottom:4px">${{escHtml(name)}}</div>
      <div style="font-size:.72rem;color:var(--text3);margin-bottom:12px">ID: ${{escHtml(id)}}</div>
      ${{content ? `<details open>
        <summary style="font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text3);cursor:pointer;margin-bottom:6px">TREŚĆ WĄTKU</summary>
        <pre style="font-size:.73rem;color:var(--text2);white-space:pre-wrap;max-height:220px;overflow-y:auto;background:var(--surf2);padding:10px 12px;border-radius:10px;margin-top:6px">${{escHtml(content.substring(0,4000))}}</pre>
      </details>` : ''}}
      <div style="margin-top:14px">
        <div style="font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text3);margin-bottom:8px">LINKI (${{links.length}})</div>
        <div id="lib-links-list">${{links.length ? links.map(l=>`
          <div class="thread-link-item">
            <span class="thread-link-url" onclick="window.open('${{escHtml(l.url)}}','_blank')" title="${{escHtml(l.url)}}">${{escHtml(l.title||l.url)}}</span>
            <span style="font-size:.65rem;color:var(--text3)">${{l.added||''}}</span>
            <button class="thread-link-del" onclick="removeThreadLink('${{escHtml(id)}}','${{escHtml(l.url)}}')" title="Usuń">✕</button>
          </div>`).join('') : '<div style="font-size:.78rem;color:var(--text3);padding:4px 0">Brak linków</div>'}}</div>
        <div class="link-add-row">
          <input id="link-add-url-${{escHtml(id)}}" class="link-add-input" placeholder="https://…" onkeydown="if(event.key==='Enter')addThreadLink('${{escHtml(id)}}')">
          <button class="link-add-btn" onclick="addThreadLink('${{escHtml(id)}}')">+ Link</button>
        </div>
      </div>`;
  }} else {{
    // Project view — show threads in project
    fetch(API + '/api/library/projects').then(r=>r.json()).then(data => {{
      const proj = (data.projects||[]).find(p=>p.id===id);
      if (!proj) {{ detail.innerHTML += '<div style="color:var(--text3);font-size:.8rem">Brak danych projektu</div>'; return; }}
      const threads = proj.threads || [];
      detail.innerHTML = `
        <div style="font-size:.95rem;font-weight:700;margin-bottom:4px">${{escHtml(proj.name||name)}}</div>
        <div style="font-size:.78rem;color:var(--text3);margin-bottom:8px">${{escHtml(proj.description||'')}}</div>
        <div style="font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text3);margin-bottom:8px">WĄTKI (${{threads.length}})</div>
        ${{threads.length ? threads.map(s=>`<div style="padding:5px 0;font-size:.82rem;border-bottom:1px solid var(--border2)">${{escHtml(s)}}</div>`).join('') : '<div style="font-size:.78rem;color:var(--text3)">Brak przypisanych wątków</div>'}}`;
    }}).catch(()=>{{}});
  }}
}}

async function addThreadLink(stem) {{
  const inp = document.getElementById('link-add-url-' + stem);
  if (!inp) return;
  const url = inp.value.trim();
  if (!url) return;
  const title = prompt('Tytuł linku (opcjonalnie):', url) || url;
  const resp = await fetch(API + '/api/library/thread-links', {{
    method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{stem, url, title}}),
  }}).catch(()=>null);
  if (resp && resp.ok) {{ inp.value=''; selectLibItem(stem, _libSelectedId===stem?stem:stem); }}
}}

async function removeThreadLink(stem, url) {{
  if (!confirm('Usunąć link?')) return;
  await fetch(API + '/api/library/thread-links', {{
    method:'DELETE', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{stem, url}}),
  }}).catch(()=>null);
  selectLibItem(stem, stem);
}}

function libSearch(q) {{
  document.querySelectorAll('#lib-list .thread-item').forEach(el => {{
    el.style.display = (!q || el.textContent.toLowerCase().includes(q.toLowerCase())) ? '' : 'none';
  }});
}}

// ── Library (threads + projects + docs) ───────────────────────────────────────
let libraryData = {{threads: [], projects: [], docs: []}};

async function loadLibrary() {{
  try {{
    const [tr, pr] = await Promise.all([
      fetch(API + '/api/library/threads').then(r => r.json()),
      fetch(API + '/api/library/projects').then(r => r.json()),
    ]);
    libraryData.threads  = tr.threads  || [];
    libraryData.projects = pr.projects || [];
    renderThreads();
    renderProjects();
  }} catch (_) {{}}
  loadDocs();
}}

function renderThreads() {{
  const el = document.getElementById('threads-list');
  if (!el) return;
  const filterVal = (document.getElementById('threads-filter-input')?.value || '').toLowerCase().trim();
  const matchFilter = t => !filterVal || t.title.toLowerCase().includes(filterVal) || (t.domain||'').toLowerCase().includes(filterVal);
  const active   = libraryData.threads.filter(t => !t.archived && t.status === 'active' && matchFilter(t));
  const frozen   = libraryData.threads.filter(t => !t.archived && t.status === 'frozen' && matchFilter(t));
  const library  = libraryData.threads.filter(t => !t.archived && t.status !== 'active' && t.status !== 'frozen' && matchFilter(t));
  const archived = libraryData.threads.filter(t => t.archived && matchFilter(t));

  let html = '';
  // v0.9: warn when active threads ≥ 5
  if (active.length >= 5) {{
    const lvl = active.length >= 7 ? 'bad' : 'warn';
    html += '<div class="thread-limit-warning">' +
      '<span class="warn-icon">⚠</span>' +
      '<span>' + active.length + ' aktywnych — zalecane max. 5 ' +
      '(<a href="#" onclick="event.preventDefault()" style="color:inherit;text-decoration:underline" title="Zamroź lub zarchiwizuj wątki, które nie potrzebują odpowiedzi AI.">?</a>)</span>' +
      '</div>';
  }}
  if (active.length) {{
    html += '<div class="panel-sub">Aktywne<span class="panel-sub-count">' + active.length + '</span></div>';
    html += active.map(t => threadItemHtml(t)).join('');
  }}
  if (frozen.length) {{
    html += '<div class="panel-sub">Zamrożone<span class="panel-sub-count">' + frozen.length + '</span></div>';
    html += frozen.map(t => threadItemHtml(t)).join('');
  }}
  if (library.length) {{
    html += '<div class="panel-sub">Biblioteka<span class="panel-sub-count">' + library.length + '</span></div>';
    html += library.map(t => threadItemHtml(t)).join('');
  }}
  if (archived.length) {{
    html += '<div class="panel-sub">Archiwum<span class="panel-sub-count">' + archived.length + '</span></div>';
    html += archived.map(t => threadItemHtml(t, true)).join('');
  }}
  el.innerHTML = html || '<div class="empty">Brak wątków</div>';
  // Re-apply active class after re-render
  if (activeThread) {{
    const activeEl = el.querySelector('.thread-item[data-stem="' + CSS.escape(activeThread.stem) + '"]');
    if (activeEl) activeEl.classList.add('active');
  }}
}}

function threadItemHtml(t, isArchived) {{
  isArchived = isArchived || false;
  const dot = isArchived ? 'archived'
    : t.status === 'active'  ? 'active'
    : t.status === 'frozen'  ? 'frozen'
    : 'library';
  const archBtn = isArchived
    ? `<button class="icon-btn" onclick="restoreThread('${{escHtml(t.filename)}}');event.stopPropagation()" title="Przywróć">↩</button>`
    : `<button class="icon-btn" onclick="archiveThread('${{escHtml(t.filename)}}');event.stopPropagation()" title="Archiwizuj">⊘</button>`;
  const exportBtn = `<button class="export-btn" onclick="toggleExportMenu('${{escHtml(t.stem)}}',this,event)" title="Eksportuj">⬇</button>`;
  // v1.0: freeze / thaw toggle (only for non-archived threads)
  const freezeBtn = !isArchived
    ? (t.status === 'frozen'
        ? `<button class="icon-btn" style="color:#5c9fd4" onclick="toggleThreadStatus('${{escHtml(t.stem)}}','frozen');event.stopPropagation()" title="Odblokuj wątek">▶</button>`
        : `<button class="icon-btn" onclick="toggleThreadStatus('${{escHtml(t.stem)}}','${{escHtml(t.status||'library')}}');event.stopPropagation()" title="Zamroź wątek">❄</button>`)
    : '';
  const checkbox = !isArchived
    ? `<input type="checkbox" class="thread-checkbox" title="Zaznacz do syntezy"
        onclick="event.stopPropagation();onThreadCheckbox(this,'${{escHtml(t.stem)}}','${{escHtml(t.title)}}')">`
    : '';
  return `<div class="thread-item" data-stem="${{escHtml(t.stem)}}" onclick="openThread('${{escHtml(t.stem)}}','${{escHtml(t.title)}}')" style="cursor:pointer">` +
    checkbox +
    `<span class="thread-status-dot ${{dot}}"></span>` +
    `<span class="thread-name" title="${{escHtml(t.title)}}">${{escHtml(t.title)}}</span>` +
    `<span class="thread-domain">${{escHtml(t.domain || '')}}</span>` +
    `<span onclick="event.stopPropagation()">${{freezeBtn}}${{archBtn}}${{exportBtn}}</span>` +
    `</div>`;
}}

async function archiveThread(filename) {{
  await fetch(API + '/api/library/threads/archive', {{method:'POST',
    headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{filename}})}});
  loadLibrary();
}}

async function restoreThread(filename) {{
  await fetch(API + '/api/library/threads/restore', {{method:'POST',
    headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{filename}})}});
  loadLibrary();
}}

function renderProjects() {{
  const el = document.getElementById('projects-list');
  if (!el) return;
  const active   = libraryData.projects.filter(p => !p.archived);
  const archived = libraryData.projects.filter(p => p.archived);

  let html = '';
  for (const p of active) html += projectItemHtml(p, false);
  if (archived.length) {{
    html += '<div class="panel-sub" style="margin-top:.4rem">Archiwum</div>';
    for (const p of archived) html += projectItemHtml(p, true);
  }}
  el.innerHTML = html || '<div class="empty">Brak projektów</div>';
}}

function projectItemHtml(p, isArchived) {{
  const threadNames = (p.threads || []).slice(0, 3).join(', ');
  const archBtn = isArchived
    ? `<button class="icon-btn" onclick="restoreProject('${{escHtml(p.id)}}')" title="Przywróć">↩</button>`
    : `<button class="icon-btn" onclick="archiveProject('${{escHtml(p.id)}}')" title="Archiwizuj">⊘</button>`;
  const activateBtn = isArchived ? '' :
    `<button class="icon-btn" onclick="activateProject('${{escHtml(p.id)}}');event.stopPropagation()" title="Aktywuj projekt">▶</button>`;
  const exportBtn = !isArchived
    ? `<button class="export-btn" onclick="exportProject('${{escHtml(p.id)}}',event)" title="Pobierz ZIP">⬇</button>`
    : '';
  return '<div class="project-item">' +
    '<div style="display:flex;justify-content:space-between;align-items:center">' +
    '<span class="project-name">' + escHtml(p.name) + '</span>' +
    '<span>' + activateBtn + archBtn + exportBtn + '</span>' +
    '</div>' +
    (p.description ? '<div class="project-meta">' + escHtml(p.description) + '</div>' : '') +
    '<div class="project-threads">' + (p.threads ? p.threads.length : 0) + ' wątków' +
    (threadNames ? ': ' + escHtml(threadNames) : '') + '</div>' +
    '</div>';
}}

function showNewProjectForm() {{
  document.getElementById('new-project-form').classList.remove('hidden');
}}
function hideNewProjectForm() {{
  document.getElementById('new-project-form').classList.add('hidden');
}}
async function createProject() {{
  const name = document.getElementById('proj-name').value.trim();
  const desc = document.getElementById('proj-desc').value.trim();
  if (!name) return;
  await fetch(API + '/api/library/projects', {{method:'POST',
    headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{name, description: desc}})}});
  document.getElementById('proj-name').value = '';
  document.getElementById('proj-desc').value = '';
  hideNewProjectForm();
  loadLibrary();
}}
async function archiveProject(id) {{
  await fetch(API + '/api/library/projects/archive', {{method:'POST',
    headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{project_id: id}})}});
  loadLibrary();
}}
async function restoreProject(id) {{
  await fetch(API + '/api/library/projects/restore', {{method:'POST',
    headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{project_id: id}})}});
  loadLibrary();
}}

// ── Workspace toggle ──────────────────────────────────────────────────────────
function toggleWorkspace() {{
  const grid = document.getElementById('workspace-grid');
  const btn  = document.querySelector('.workspace-toggle');
  const isOpen = !grid.classList.contains('hidden');
  grid.classList.toggle('hidden', isOpen);
  btn.textContent = isOpen ? '▶ Workspace' : '▼ Workspace';
}}

// ── NO-GO mode ────────────────────────────────────────────────────────────────
function toggleNoGo() {{
  noGoMode = !noGoMode;
  const btn = document.getElementById('nogo-btn');
  if (btn) {{
    btn.classList.toggle('active', noGoMode);
    btn.title = noGoMode ? 'NO-GO aktywny — kliknij aby wyłączyć' : 'Aktywuj tryb NO-GO';
  }}
  const input = document.getElementById('chat-input');
  if (input) {{
    input.placeholder = noGoMode
      ? '⊗ NO-GO: wpisz hipotezę do zniszczenia… (⌘+Enter)'
      : 'Zadanie lub odpowiedź… (⌘+Enter)';
  }}
}}

// ── NO-GO sidebar panel ───────────────────────────────────────────────────────
async function loadNoGoSidebar() {{
  try {{
    const r = await fetch(API + '/api/nogo-room/trajectories');
    if (!r.ok) return;
    const trajs = await r.json();
    const el = document.getElementById('nogo-sidebar-list');
    if (!el) return;
    if (!Array.isArray(trajs) || !trajs.length) {{
      el.innerHTML = '<div class="empty" style="padding:6px 8px;font-size:.73rem">Brak ryzykownych trajektorii</div>';
      return;
    }}
    el.innerHTML = trajs.slice(0, 6).map(t => {{
      const risk = Math.round((t.effective_risk || 0) * 100);
      const cls  = (t.effective_risk || 0) >= 0.7 ? 'nogo-high' : 'nogo-mid';
      const id   = escHtml(t.trajectory_id || '');
      const cat  = escHtml(t.category || '');
      return `<div class="nogo-traj-item ${{cls}}" title="${{cat}}">
        <span class="nogo-traj-name">${{id}}</span>
        <span class="nogo-traj-risk">${{risk}}%</span>
      </div>`;
    }}).join('');
  }} catch (_) {{}}
}}

function toggleNoGoSidebar() {{
  const body  = document.getElementById('nogo-sidebar-body');
  const arrow = document.getElementById('nogo-sidebar-arrow');
  if (!body) return;
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : 'block';
  if (arrow) arrow.textContent = open ? '▶' : '▼';
  if (!open) loadNoGoSidebar();
}}

// ── Server status ─────────────────────────────────────────────────────────────
async function checkServer() {{
  try {{
    const r = await fetch(API + '/api/status', {{signal: AbortSignal.timeout(2000)}});
    if (r.ok) {{
      document.getElementById('dot').className = 'server-dot online';
      document.getElementById('srv-label').textContent = 'online';
      try {{
        const data = await r.clone().json();
        const epiEl = document.getElementById('epi-badge');
        if (epiEl) {{
          if (data.epistemic_limit_mode && data.epistemic_limit_mode.active) {{
            epiEl.classList.remove('hidden');
          }} else {{
            epiEl.classList.add('hidden');
          }}
        }}
      }} catch (_) {{}}
    }}
  }} catch (_) {{}}
}}

// ── Chat ──────────────────────────────────────────────────────────────────────
function sendPreset(task) {{
  document.getElementById('chat-input').value = task;
  sendMessage();
}}

async function sendMessage() {{
  const input  = document.getElementById('chat-input');
  const saveAs = document.getElementById('save-input');
  const btn    = document.getElementById('send-btn');
  const spin   = document.getElementById('spinner');

  const text = input.value.trim();
  if (!text || btn.disabled) return;

  // ── Slash commands ─────────────────────────────────────────────────────────
  if (text === '/briefing') {{
    input.value = '';
    checkMorningBriefing(true);
    return;
  }}
  if (text === '/briefing clear' || text === '/briefing dismiss') {{
    input.value = '';
    dismissBriefing();
    return;
  }}

  conversation.push({{role: 'user', content: text}});
  input.value = '';
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 26) + 'px';
  localStorage.removeItem('matylda-chat-draft');
  // Persist user message immediately — so it survives a tab close before response
  _persistConversation(_currentStem(), conversation);
  renderConversation();
  scrollChat();

  btn.disabled = true;
  spin.style.display = 'inline-block';
  _isStreaming = true;
  _streamAbortCtrl = new AbortController();
  _streamingStem = activeThread ? activeThread.stem : null;
  const myStreamStem = _streamingStem; // capture — used to detect thread switches mid-stream
  const myGeneration = ++_streamGeneration; // capture — prevents stale finally from corrupting next stream

  conversation.push({{role: 'assistant', content: '', meta: {{streaming: true}}}});
  renderConversation();
  scrollChat();

  try {{
    let msgs = conversation
      .filter(m => !(m.meta && m.meta.streaming))
      .map(m => ({{role: m.role, content: m.content}}));

    // Inject active thread content as context prefix on first user message
    if (activeThread && msgs.length > 0 && msgs[0].role === 'user') {{
      const ctxPrefix = '=== WĄTEK: ' + activeThread.title + ' ===\\n' +
        activeThread.content + '\\n\\n=== ZADANIE ===\\n';
      msgs = [{{role: 'user', content: ctxPrefix + msgs[0].content}}, ...msgs.slice(1)];
    }}

    // Inject active doc content as context prefix on first user message
    if (activeDoc && msgs.length > 0 && msgs[0].role === 'user') {{
      const docPrefix = '=== DOKUMENT: ' + activeDoc.name + ' ===\\n' +
        activeDoc.content.slice(0, 20000) + '\\n\\n=== ZADANIE ===\\n';
      msgs = [{{role: 'user', content: docPrefix + msgs[0].content}}, ...msgs.slice(1)];
    }}

    const response = await fetch(API + '/api/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        messages: msgs,
        save_as: saveAs ? saveAs.value.trim() : '',
        no_go: noGoMode
      }}),
      signal: _streamAbortCtrl ? _streamAbortCtrl.signal : undefined,
    }});

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {{
      const {{done, value}} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {{stream: true}});
      const parts = buffer.split('\\n\\n');
      buffer = parts.pop();
      for (const part of parts) {{
        if (!part.startsWith('data: ')) continue;
        try {{
          const event = JSON.parse(part.slice(6));
          // Guard: ignore stale chunks from a previous thread's stream.
          // If the user switched threads, myStreamStem !== activeThread.stem.
          // True if still in the same thread context as when stream started.
          // Uses null===null parity: sending without a thread is valid (myStreamStem===null, activeThread===null).
          const _onMyThread = (activeThread ? activeThread.stem : null) === myStreamStem;

          if (event.type === 'chunk') {{
            if (!_onMyThread) continue; // stale chunk — discard
            const lastIdx = conversation.length - 1;
            if (lastIdx < 0) continue;
            conversation[lastIdx].content += event.text || '';
            const bubbles = document.querySelectorAll('.msg-ai .msg-bubble');
            if (bubbles.length > 0) {{
              const lastBubble = bubbles[bubbles.length - 1];
              lastBubble.textContent = conversation[lastIdx].content;
              if (!lastBubble.classList.contains('streaming')) {{
                lastBubble.classList.add('streaming');
              }}
            }}
            scrollChat();

          }} else if (event.type === 'done') {{
            // "done" fires RIGHT after the main stream ends — before DARKROOM review.
            // We show the result and add the save-insight button immediately.
            // Review metadata arrives separately in "review" event.
            if (!_onMyThread) {{
              // Background thread completed — save silently for when user returns.
              if (myStreamStem) {{
                const bgConv = _threadConversations[myStreamStem] || [];
                const bgLast = bgConv[bgConv.length - 1];
                // Match both streaming placeholder AND aborted partial (saved on thread switch)
                if (bgLast && bgLast.meta && (bgLast.meta.streaming || bgLast.meta.aborted)) {{
                  bgConv[bgConv.length - 1] = {{role: 'assistant', content: event.result || bgLast.content, meta: event}};
                }} else {{
                  bgConv.push({{role: 'assistant', content: event.result || '', meta: event}});
                }}
                _threadConversations[myStreamStem] = bgConv;
                _persistConversation(myStreamStem, bgConv); // persist background thread
                // If user returned to this thread while stream was finishing, update the visible chat
                if (activeThread && activeThread.stem === myStreamStem) {{
                  conversation = [...bgConv];
                  renderConversation();
                  scrollChat();
                }}
              }}
              continue;
            }}
            const lastIdx = conversation.length - 1;
            if (lastIdx >= 0) {{
              conversation[lastIdx] = {{
                role: 'assistant',
                content: event.result || conversation[lastIdx].content,
                meta: event
              }};
            }}
            // Persist immediately after done — survives tab close before next thread switch
            _persistConversation(_currentStem(), conversation);
            renderConversation();
            scrollChat();
            // Add save-insight button immediately — don't wait for review
            const aiBubbles = document.querySelectorAll('.msg-ai');
            if (aiBubbles.length > 0) {{
              addSaveInsightButton(aiBubbles[aiBubbles.length - 1], event.result || '');
            }}

          }} else if (event.type === 'review') {{
            // DARKROOM review + topology arrive after done — update metadata only.
            if (!_onMyThread) continue;
            const lastIdx = conversation.length - 1;
            if (lastIdx >= 0 && conversation[lastIdx].role === 'assistant') {{
              // Merge review/topology into existing meta without replacing content
              conversation[lastIdx].meta = Object.assign({{}}, conversation[lastIdx].meta, {{
                review:   event.review,
                topology: event.topology,
              }});
            }}
            // Re-render to show DARKROOM badge
            renderConversation();
            scrollChat();
            if (event.review && event.review.pending_approval) {{
              loadDarkroom();
            }}
            if (event.topology) {{
              const bubbles = document.querySelectorAll('.msg-ai .msg-bubble');
              if (bubbles.length > 0) {{
                renderTopology(event.topology, bubbles[bubbles.length - 1].parentElement);
              }}
            }}
            if (event.topology && event.topology.no_go_mode) {{
              if (noGoMode) {{ noGoMode = true; toggleNoGo(); }}
            }}

          }} else if (event.type === 'error') {{
            if (!_onMyThread) continue; // stale error — discard
            const lastIdx = conversation.length - 1;
            if (lastIdx >= 0) {{
              // Preserve any streamed content — don't overwrite if text already arrived
              const existing = conversation[lastIdx].content || '';
              conversation[lastIdx] = {{
                role: 'assistant',
                content: existing || event.error || 'Błąd odpowiedzi modelu.',
                meta: {{error: true, errorDetail: event.error || ''}}
              }};
            }}
            renderConversation();
            scrollChat();
          }}
        }} catch(e) {{}}
      }}
    }}
  }} catch (e) {{
    if (e.name === 'AbortError') {{
      // Stream was intentionally aborted (user switched thread) — no error shown
    }} else {{
      const lastIdx = conversation.length - 1;
      if (conversation[lastIdx] && conversation[lastIdx].meta && conversation[lastIdx].meta.streaming) {{
        conversation[lastIdx] = {{role: 'assistant', content: 'Błąd połączenia: ' + e.message, meta: {{error: true}}}};
      }} else {{
        conversation.push({{role: 'assistant', content: 'Błąd połączenia: ' + e.message, meta: {{error: true}}}});
      }}
      renderConversation();
      scrollChat();
    }}
  }} finally {{
    // Only clean up shared streaming state if this is still the active stream.
    // If the user switched threads and a NEW sendMessage() already started,
    // _streamGeneration > myGeneration — don't touch the new stream's state.
    if (_streamGeneration === myGeneration) {{
      _isStreaming = false;
      _streamAbortCtrl = null;
      _streamingStem = null;
      btn.disabled = false;
      spin.style.display = 'none';
      input.focus();
    }}
  }}
}}

function clearChat() {{
  if (_isStreaming) _abortStream();
  conversation = [];
  if (activeThread) {{
    delete _threadConversations[activeThread.stem];
    _forgetConversation(activeThread.stem); // clear from localStorage too
  }}
  renderConversation();
}}

function renderConversation() {{
  const history = document.getElementById('chat-history');
  const empty   = document.getElementById('chat-empty');

  if (conversation.length === 0) {{
    if (empty) empty.style.display = 'block';
    history.querySelectorAll('.msg').forEach(e => e.remove());
    return;
  }}
  if (empty) empty.style.display = 'none';
  history.querySelectorAll('.msg').forEach(e => e.remove());

  for (const msg of conversation) {{
    const el = buildMsgEl(msg);
    history.appendChild(el);
  }}
}}

// ── Copy utilities ─────────────────────────────────────────────────────────────
async function copyText(text, btnEl) {{
  const orig = btnEl ? btnEl.textContent : '';
  try {{
    await navigator.clipboard.writeText(text);
  }} catch(e) {{
    // Fallback for contexts without clipboard API
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy'); }} catch(e2) {{}}
    document.body.removeChild(ta);
  }}
  if (btnEl) {{
    btnEl.textContent = '✓ Skopiowano';
    btnEl.classList.add('saved');
    setTimeout(() => {{ btnEl.textContent = orig; btnEl.classList.remove('saved'); }}, 1600);
  }}
}}

function copyThread() {{
  const parts = [];
  for (const msg of conversation) {{
    if (msg.meta && msg.meta.streaming) continue;
    const role = msg.role === 'user' ? '**Ty:**' : '**Matylda:**';
    parts.push(role + '\\n\\n' + (msg.content || '').trim());
  }}
  const text = parts.join('\\n\\n---\\n\\n');
  const btn = document.getElementById('copy-thread-btn');
  copyText(text, btn);
}}

function buildMsgEl(msg) {{
  const div = document.createElement('div');
  div.className = 'msg msg-' + (msg.role === 'assistant' ? 'ai' : msg.role);

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if (msg.meta && msg.meta.streaming) {{
    bubble.classList.add('streaming');
    bubble.textContent = msg.content;
  }} else if (msg.role === 'assistant') {{
    bubble.innerHTML = renderMarkdown(msg.content || '');
  }} else {{
    bubble.textContent = msg.content;
  }}
  div.appendChild(bubble);

  if (msg.role === 'assistant' && msg.meta && !msg.meta.error && !msg.meta.streaming) {{
    const meta = msg.meta;
    const metaEl = document.createElement('div');
    metaEl.className = 'msg-meta';
    const parts = [];
    if (meta.model_key) parts.push('<span class="badge badge-' + meta.model_key + '">' + meta.model_key + '</span>');
    if (meta.reasoning) parts.push('<span>' + escHtml(meta.reasoning) + '</span>');
    if (meta.saved_to)  parts.push('<span class="msg-saved">💾 ' + escHtml(meta.saved_to) + '</span>');
    if (meta.fetched_urls && meta.fetched_urls.length) parts.push('<span>🌐 ' + meta.fetched_urls.length + ' URL</span>');
    metaEl.innerHTML = parts.join(' · ');
    div.appendChild(metaEl);

    if (meta.review) {{
      const rv = meta.review;
      const rvEl = document.createElement('div');
      rvEl.className = 'msg-review ' + (rv.verdict || 'pass');
      let rvHtml = '<strong>DARKROOM: ' + (rv.verdict || 'pass').toUpperCase() + '</strong>';
      if (rv.reviews) {{
        for (const r of rv.reviews) {{
          if (r.issues && r.issues.length) {{
            rvHtml += '<br><span style="color:var(--text3)">' + r.reviewer + ':</span> ' + escHtml(r.issues.join('; '));
          }}
        }}
      }}
      rvEl.innerHTML = rvHtml;
      div.appendChild(rvEl);

      if (rv.pending_approval) {{
        const pa = rv.pending_approval;
        const paEl = document.createElement('div');
        paEl.className = 'msg-approval';
        let changesHtml = '';
        for (const [k, v] of Object.entries(pa.proposed_changes || {{}})) {{
          changesHtml += k + ': ' + v.from + ' → ' + v.to + '\\n';
        }}
        paEl.innerHTML =
          '<p>⚡ DARKROOM proponuje zmianę disposition:</p>' +
          '<div class="changes">' + escHtml(changesHtml) + '</div>' +
          '<div class="approval-btns">' +
          `<button class="btn-approve" onclick="approveFromChat(this,'${{pa.id}}')">Zatwierdź</button>` +
          `<button class="btn-reject" onclick="rejectFromChat(this,'${{pa.id}}')">Odrzuć</button>` +
          '</div>';
        div.appendChild(paEl);
      }}
    }}

    // ── Copy response button (always present on completed AI messages) ──────
    const copyWrap = document.createElement('div');
    copyWrap.style.cssText = 'display:flex;gap:6px;margin-top:4px';
    const btnCopy = document.createElement('button');
    btnCopy.className = 'save-insight-btn copy-btn';
    btnCopy.textContent = '📋 Kopiuj';
    btnCopy.title = 'Kopiuj odpowiedź (Markdown)';
    btnCopy.onclick = () => copyText(msg.content || '', btnCopy);
    copyWrap.appendChild(btnCopy);
    div.appendChild(copyWrap);
  }}

  // Copy button also for completed aborted messages (partial content preserved)
  if (msg.role === 'assistant' && msg.meta && msg.meta.aborted && msg.content) {{
    const copyWrap = document.createElement('div');
    copyWrap.style.cssText = 'display:flex;gap:6px;margin-top:4px';
    const btnCopy = document.createElement('button');
    btnCopy.className = 'save-insight-btn copy-btn';
    btnCopy.textContent = '📋 Kopiuj (częściowa)';
    btnCopy.title = 'Kopiuj tę część odpowiedzi';
    btnCopy.onclick = () => copyText(msg.content || '', btnCopy);
    copyWrap.appendChild(btnCopy);
    div.appendChild(copyWrap);
  }}

  return div;
}}

function scrollChat() {{
  const h = document.getElementById('chat-history');
  h.scrollTop = h.scrollHeight;
}}

// ── Fetch URL ─────────────────────────────────────────────────────────────────
async function fetchUrl() {{
  const urlInput = document.getElementById('url-input');
  const url = urlInput.value.trim();
  if (!url) {{ urlInput.focus(); return; }}

  try {{
    const resp = await fetch(API + '/api/fetch', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{url}})
    }});
    const data = await resp.json();
    if (data.error) {{
      conversation.push({{role: 'assistant', content: '[FETCH ERROR] ' + data.error, meta: {{error: true}}}});
    }} else {{
      const preview = data.content.substring(0, 600) + (data.content.length > 600 ? '\\n[…]' : '');
      conversation.push({{role: 'assistant', content: preview, meta: {{model_key: 'fetch', reasoning: url}}}});
      urlInput.value = '';
    }}
    renderConversation();
    scrollChat();
  }} catch (e) {{
    conversation.push({{role: 'assistant', content: 'Błąd fetch: ' + e.message, meta: {{error: true}}}});
    renderConversation();
  }}
}}

// ── v0.7: Reader mode ────────────────────────────────────────────────────────
async function fetchReaderMode() {{
  const urlInput = document.getElementById('url-input');
  const url = urlInput.value.trim();
  if (!url) {{ urlInput.focus(); return; }}

  conversation.push({{role: 'user', content: '📖 Reader: ' + url}});
  conversation.push({{role: 'assistant', content: '⏳ Pobieram artykuł…', meta: {{streaming: true}}}});
  renderConversation(); scrollChat();

  try {{
    const resp = await fetch(API + '/api/fetch/reader', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{url}})
    }});
    const data = await resp.json();
    const lastIdx = conversation.length - 1;

    if (data.ok) {{
      const header = [
        data.title ? '# ' + data.title : '',
        [data.author, data.date].filter(Boolean).join(' · '),
        data.description ? '> ' + data.description : '',
        '---',
        data.word_count ? data.word_count + ' słów' : '',
        ''
      ].filter(s => s !== undefined).join('\\n');

      conversation[lastIdx] = {{
        role: 'assistant',
        content: header + '\\n' + (data.content || ''),
        meta: {{model_key: 'reader', reasoning: url}}
      }};
      urlInput.value = '';
    }} else {{
      conversation[lastIdx] = {{
        role: 'assistant',
        content: '✕ ' + (data.error || 'Błąd reader mode'),
        meta: {{error: true}}
      }};
    }}
  }} catch (e) {{
    const lastIdx = conversation.length - 1;
    conversation[lastIdx] = {{
      role: 'assistant',
      content: '✕ Błąd: ' + e.message,
      meta: {{error: true}}
    }};
  }}
  renderConversation(); scrollChat();
}}

// ── Confidence topology ───────────────────────────────────────────────────────
function renderTopology(topology, containerEl) {{
  if (!topology || topology.error || topology.no_go_mode) return;
  const stable = (topology.stable || []).length;
  const heuristic = (topology.heuristic || []).length;
  const speculative = (topology.speculative || []).length;
  const required = (topology.data_required || []).length;
  const total = stable + heuristic + speculative + required || 1;

  const topoDiv = document.createElement('div');
  topoDiv.className = 'msg-topology';

  const bar = document.createElement('div');
  bar.className = 'topology-bar';
  const parts = [
    [stable,      'topo-stable',      'stabilne'],
    [heuristic,   'topo-heuristic',   'heurystyczne'],
    [speculative, 'topo-speculative', 'spekulatywne'],
    [required,    'topo-required',    'wymaga danych'],
  ];
  let legendHtml = '<div class="topology-legend">';
  for (const [count, cls, label] of parts) {{
    if (count > 0) {{
      const seg = document.createElement('div');
      seg.className = cls;
      seg.style.flex = String(count);
      bar.appendChild(seg);
      const dotColor = cls === 'topo-stable' ? 'var(--green)'
        : cls === 'topo-heuristic' ? '#b08000'
        : cls === 'topo-speculative' ? 'var(--orange,#b06000)'
        : 'var(--red)';
      legendHtml += `<span class="topo-tag"><span class="topo-dot" style="background:${{dotColor}}"></span>${{count}} ${{label}}</span>`;
    }}
  }}
  legendHtml += '</div>';
  topoDiv.appendChild(bar);
  topoDiv.insertAdjacentHTML('beforeend', legendHtml);
  containerEl.appendChild(topoDiv);
}}

// ── DARKROOM ──────────────────────────────────────────────────────────────────
async function loadDarkroom() {{
  try {{
    const resp = await fetch(API + '/api/darkroom');
    if (!resp.ok) return;
    const data = await resp.json();
    renderDarkroom(data);
  }} catch (_) {{}}
}}

function renderDarkroom(data) {{
  renderDisposition(data.disposition || {{}});
  renderTensions(data.active_tensions || []);
  const metricsWithScores = Object.assign({{}}, data.metrics || {{}}, {{
    structural_score: data.structural_score,
    epistemic_score:  data.epistemic_score,
  }});
  renderMetrics(metricsWithScores, data.last_review);
  renderApprovals(data.pending_approvals || []);
  renderDispositionHistoryChart(data.disposition_history || []);
}}

function renderDisposition(profile) {{
  const el = document.getElementById('dr-disposition');
  if (!el) return;
  const keys = [
    ['skepticism_level',          'Sceptycyzm'],
    ['uncertainty_tolerance',     'Tol. niepewności'],
    ['falsification_preference',  'Falsyfikacja'],
    ['narrative_risk_sensitivity','Drift sensitivity'],
    ['review_strictness',         'Surowość review'],
    ['simplicity_preference',     'Prostota'],
  ];
  el.innerHTML = keys.map(([k, label]) => {{
    const v = profile[k] ?? 0.5;
    const pct = Math.round(v * 100);
    return '<div class="disp-row">' +
      '<span class="disp-label">' + label + '</span>' +
      '<div class="disp-bar-wrap"><div class="disp-bar-fill" style="width:' + pct + '%"></div></div>' +
      '<span class="disp-value">' + v.toFixed(2) + '</span>' +
      '</div>';
  }}).join('');
}}

function renderTensions(tensions) {{
  const el = document.getElementById('dr-tensions');
  if (!el) return;
  const titleEl = document.getElementById('dr-tensions-title');
  if (titleEl) titleEl.textContent = 'TENSIONS (' + tensions.length + ')';
  if (!tensions.length) {{
    el.innerHTML = '<div style="color:var(--text3);font-size:.75rem;font-style:italic">brak aktywnych napięć</div>';
    return;
  }}
  el.innerHTML = tensions
    .sort((a, b) => b.severity - a.severity)
    .slice(0, 5)
    .map(t => {{
      const cls = t.severity >= 0.6 ? 'high' : t.severity >= 0.35 ? 'med' : 'low';
      const tid = escHtml(t.id || '');
      return '<div class="tension-item ' + cls + '">' +
        '<div class="tension-item-header">' +
        '<span class="tension-type">' + escHtml(t.type) + '</span>' +
        '<span class="tension-sev">' + t.severity.toFixed(2) +
        (tid ? `<button class="tension-archive-btn" onclick="archiveTension('${{tid}}')">⊘</button>` : '') +
        '</span>' +
        '</div>' +
        '<div class="tension-desc">' + escHtml(t.description.substring(0, 80)) + '</div>' +
        '</div>';
    }}).join('');
}}

async function archiveTension(id) {{
  await fetch(API + '/api/darkroom/tension/archive', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{tension_id: id, note: ''}})
  }});
  loadDarkroom();
}}

async function triageTensions() {{
  try {{
    const r = await fetch(API + '/api/darkroom/tension/triage', {{method: 'POST'}}).then(r => r.json());
    if (r.error) {{ alert('Błąd: ' + r.error); return; }}
    const parts = [];
    if (r.deduped) parts.push(r.deduped + ' duplikatów');
    if (r.test_archived) parts.push(r.test_archived + ' testowych');
    if (r.aged_archived) parts.push(r.aged_archived + ' przeterminowanych (>30 dni)');
    alert(parts.length
      ? 'Zarchiwizowano: ' + parts.join(', ') + '. Aktywnych: ' + r.active_remaining + ' (krytyczne zostają).'
      : 'Nic do zarchiwizowania — wszystkie napięcia świeże lub krytyczne. Aktywnych: ' + r.active_remaining + '.');
    loadDarkroom();
  }} catch(e) {{ alert('Błąd: ' + e.message); }}
}}

async function addTension() {{
  const desc = document.getElementById('tension-desc');
  const sev  = document.getElementById('tension-sev');
  const type = document.getElementById('tension-type');
  if (!desc || !sev || !type) return;
  const description = desc.value.trim();
  if (!description) {{ desc.focus(); return; }}
  try {{
    await fetch(API + '/api/darkroom/tension/create', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        description,
        severity: parseFloat(sev.value) || 0.5,
        type: type.value
      }})
    }});
    desc.value = '';
    loadDarkroom();
  }} catch (e) {{
    console.error('addTension error:', e);
  }}
}}

function renderMetrics(m, lastReview) {{
  const el = document.getElementById('dr-metrics');
  if (!el) return;
  const failRate = (m.failure_rate || 0);
  const frClass  = failRate > 0.3 ? 'bad' : 'ok';
  const repPat   = m.repeated_patterns !== undefined ? m.repeated_patterns : '—';
  let html =
    '<div class="metric-row"><span class="metric-label">Total reviews</span><span class="metric-val">' + (m.total_reviews||0) + '</span></div>' +
    '<div class="metric-row"><span class="metric-label">Pass / Flag / Fail</span><span class="metric-val">' + (m.total_passes||0) + ' / ' + (m.total_flags||0) + ' / ' + (m.total_failures||0) + '</span></div>' +
    '<div class="metric-row"><span class="metric-label">Failure rate</span><span class="metric-val ' + frClass + '">' + (failRate*100).toFixed(1) + '%</span></div>' +
    '<div class="metric-row"><span class="metric-label">Repeated patterns</span><span class="metric-val">' + repPat + '</span></div>';
  if (lastReview) {{
    const s = lastReview.summary || {{}};
    html += '<div class="metric-row"><span class="metric-label">Last verdict</span>' +
      '<span class="metric-val"><span class="badge badge-' + (s.verdict||'pass') + '">' + (s.verdict||'pass') + '</span></span></div>';
  }}
  // Structural / Epistemic scores from darkroom_status or last review
  const structScore = typeof m.structural_score === 'number' ? m.structural_score
    : (lastReview && lastReview.summary && typeof lastReview.summary.structural_score === 'number' ? lastReview.summary.structural_score : 0);
  const epistScore  = typeof m.epistemic_score  === 'number' ? m.epistemic_score
    : (lastReview && lastReview.summary && typeof lastReview.summary.epistemic_score  === 'number' ? lastReview.summary.epistemic_score  : 0);
  html +=
    '<div class="score-row" style="margin-top:.4rem">' +
      '<span class="score-label">Structural</span>' +
      '<div class="score-bar-wrap"><div class="score-bar-fill score-bar-structural" style="width:' + Math.round(structScore*100) + '%"></div></div>' +
      '<span class="score-value">' + structScore.toFixed(2) + '</span>' +
    '</div>' +
    '<div class="score-row">' +
      '<span class="score-label">Epistemic</span>' +
      '<div class="score-bar-wrap"><div class="score-bar-fill score-bar-epistemic" style="width:' + Math.round(epistScore*100) + '%"></div></div>' +
      '<span class="score-value">' + epistScore.toFixed(2) + '</span>' +
    '</div>';
  el.innerHTML = html;
}}

function renderApprovals(approvals) {{
  const el = document.getElementById('dr-approvals');
  if (!el) return;
  if (!approvals.length) {{
    el.innerHTML = '<p class="dr-no-approval">brak oczekujących zatwierdzeń</p>';
    return;
  }}
  el.innerHTML = approvals.map(a => {{
    let changesHtml = '';
    for (const [k, v] of Object.entries(a.proposed_changes || {{}})) {{
      changesHtml += '<div class="approval-change-row">' + k + ': <span class="change-from">' +
        v.from + '</span> → <span class="change-to">' + v.to + '</span></div>';
    }}
    return '<div class="approval-card">' +
      '<div class="approval-trigger">trigger: ' + escHtml(a.trigger) + '</div>' +
      '<div class="approval-trigger" style="margin-bottom:.35rem">zadanie: ' + escHtml(a.task_preview||'') + '</div>' +
      '<div class="approval-changes">' + changesHtml + '</div>' +
      '<div class="approval-btns">' +
      `<button class="btn-approve" onclick="approveDR(this,'${{a.id}}')">Zatwierdź</button>` +
      `<button class="btn-reject"  onclick="rejectDR(this,'${{a.id}}')">Odrzuć</button>` +
      `<button class="btn-validate" onclick="validateFinding(this,'${{escHtml(a.task_preview||'')}}')">Zwaliduj</button>` +
      '</div>' +
      '<div class="validation-result" id="val-${{a.id}}" style="display:none"></div>' +
      '</div>';
  }}).join('');
}}

async function approveFromChat(btn, id) {{ await _sendApproval(btn, id, true); }}
async function rejectFromChat(btn, id)  {{ await _sendApproval(btn, id, false); }}
async function approveDR(btn, id)       {{ await _sendApproval(btn, id, true); }}
async function rejectDR(btn, id)        {{ await _sendApproval(btn, id, false); }}

async function _sendApproval(btn, id, approve) {{
  const endpoint = approve ? '/api/darkroom/approve' : '/api/darkroom/reject';
  const container = btn ? btn.closest('.approval-btns, .msg-approval') : null;
  if (btn) {{ btn.disabled = true; btn.textContent = '…'; }}
  try {{
    const resp = await fetch(API + endpoint, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{approval_id: id}})
    }});
    const data = await resp.json();
    if (data.error) {{
      if (btn) {{ btn.disabled = false; btn.textContent = approve ? 'Zatwierdź' : 'Odrzuć'; }}
      const errEl = btn ? btn.closest('.msg-approval, .approval-card') : null;
      if (errEl) {{
        const e = document.createElement('div');
        e.style.cssText = 'color:var(--red);font-size:.75rem;margin-top:.3rem';
        e.textContent = '⚠ ' + data.error;
        errEl.appendChild(e);
        setTimeout(() => e.remove(), 4000);
      }}
    }} else {{
      if (container) {{
        const ok = document.createElement('div');
        ok.style.cssText = 'color:var(--green);font-size:.8rem;padding:.3rem 0';
        ok.textContent = approve ? '✓ Zatwierdzono' : '✗ Odrzucono';
        container.replaceWith(ok);
      }}
      loadDarkroom();
    }}
  }} catch (e) {{
    if (btn) {{ btn.disabled = false; btn.textContent = approve ? 'Zatwierdź' : 'Odrzuć'; }}
    console.error('Approval error:', e);
  }}
}}

// ── External validation ───────────────────────────────────────────────────────
async function validateFinding(btn, claim) {{
  if (!claim) return;
  const card   = btn ? btn.closest('.approval-card') : null;
  const resEl  = card ? card.querySelector('.validation-result') : null;
  if (btn) {{ btn.disabled = true; btn.textContent = '…'; }}
  if (resEl) {{ resEl.style.display = 'block'; resEl.textContent = 'Walidacja opus…'; }}
  try {{
    const resp = await fetch(API + '/api/darkroom/validate', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{claim: claim, sources: []}})
    }});
    const data = await resp.json();
    if (btn) {{ btn.disabled = false; btn.textContent = 'Zwaliduj'; }}
    if (!resEl) return;
    if (data.error) {{
      resEl.textContent = '⚠ ' + data.error;
      resEl.style.color = 'var(--red)';
      return;
    }}
    const v = data.validation || {{}};
    const icons = {{supported:'✓', partial:'△', unsupported:'✗'}};
    const colors = {{supported:'var(--green)', partial:'var(--accent)', unsupported:'var(--red)'}};
    const verd = v.verdict || 'unsupported';
    resEl.style.color = colors[verd] || 'var(--text2)';
    resEl.innerHTML = `${{icons[verd]||'?'}} ${{verd}} (conf: ${{(v.confidence||0).toFixed(2)}}) — ${{escHtml(v.notes||'')}}`;
  }} catch (e) {{
    if (btn) {{ btn.disabled = false; btn.textContent = 'Zwaliduj'; }}
    if (resEl) {{ resEl.textContent = '⚠ błąd połączenia'; resEl.style.color = 'var(--red)'; }}
  }}
}}

// ── Review log ────────────────────────────────────────────────────────────────
function toggleReviewLog() {{
  const list = document.getElementById('review-log-list');
  if (!list) return;
  if (list.classList.contains('open')) {{
    list.classList.remove('open');
    return;
  }}
  list.classList.add('open');
  loadReviewLog();
}}

async function loadReviewLog() {{
  const list = document.getElementById('review-log-list');
  if (!list) return;
  list.innerHTML = '<div style="color:var(--text3);font-size:.75rem">ładowanie…</div>';
  try {{
    const resp = await fetch(API + '/api/darkroom/reviews');
    if (!resp.ok) {{ list.innerHTML = '<div style="color:var(--text3);font-size:.75rem">Brak danych.</div>'; return; }}
    const data = await resp.json();
    const reviews = (data.reviews || data || []).slice(0, 10);
    if (!reviews.length) {{ list.innerHTML = '<div style="color:var(--text3);font-size:.75rem;font-style:italic">brak historii</div>'; return; }}
    list.innerHTML = reviews.map(r => {{
      const verdict = r.verdict || (r.summary && r.summary.verdict) || 'pass';
      const ts = r.timestamp ? r.timestamp.substring(0, 19).replace('T', ' ') : '—';
      const task = r.task_preview || '';
      const model = r.model_used || '';
      const maxSev = r.max_severity !== undefined ? r.max_severity.toFixed(2) : '—';
      return '<div class="rl-item">' +
        '<div class="rl-ts">' + escHtml(ts) + (model ? ' · ' + escHtml(model) : '') + '</div>' +
        (task ? '<div class="rl-task">' + escHtml(task.substring(0, 60)) + '</div>' : '') +
        '<div style="margin-top:.15rem">' +
        '<span class="badge badge-' + verdict + '">' + verdict + '</span>' +
        '<span style="color:var(--text3);font-size:.7rem;margin-left:.4rem">max sev: ' + maxSev + '</span>' +
        '</div></div>';
    }}).join('');
  }} catch (e) {{
    list.innerHTML = '<div style="color:var(--text3);font-size:.75rem">Błąd: ' + escHtml(e.message) + '</div>';
  }}
}}

// ── Thread → chat context ──────────────────────────────────────────────────────
async function openThread(stem, title) {{
  // If already on this thread, just focus input — don't abort ongoing stream
  if (activeThread && activeThread.stem === stem) {{
    const ta = document.getElementById('chat-input');
    if (ta) ta.focus();
    return;
  }}

  // Save current thread's conversation before switching
  _saveCurrentConversation();

  // Detach any in-progress stream instead of aborting it.
  // Aborting kills the HTTP request — the response is lost.
  // Detaching just disconnects the UI: the fetch continues in the background,
  // the done-handler will save the full result to _threadConversations[myStreamStem].
  if (_isStreaming) {{
    _streamGeneration++;      // prevent this stream's finally from touching the new UI state
    _isStreaming = false;
    _streamAbortCtrl = null;  // lose the abort handle — fetch keeps running, we just don't track it
    const _db = document.getElementById('send-btn');
    const _ds = document.getElementById('spinner');
    if (_db) _db.disabled = false;
    if (_ds) _ds.style.display = 'none';
  }}

  // ── CRITICAL: update activeThread IMMEDIATELY (before any await) ─────────
  // Without this, there's an async gap where activeThread.stem = old thread,
  // causing the early-return guard above to misfire and sendMessage() to
  // inject the wrong thread's context.
  const _metaEarly = (libraryData && libraryData.threads || []).find(t => t.stem === stem);
  activeThread = {{
    stem,
    title: title || stem,
    content: '',          // filled after fetch; empty is safe for now
    status: (_metaEarly && _metaEarly.status) || 'library',
  }};

  // Load conversation for new thread immediately
  _loadConversation(stem);

  // Sidebar highlight
  document.querySelectorAll('.thread-item').forEach(el => el.classList.remove('active'));
  const activeEl = document.querySelector('.thread-item[data-stem="' + CSS.escape(stem) + '"]');
  if (activeEl) activeEl.classList.add('active');

  // Show loading state in ctx bar
  const bar = document.getElementById('thread-ctx-bar');
  if (bar) {{
    bar.innerHTML = '<span class="thread-ctx-label">Kontekst</span>' +
      '<span class="thread-ctx-name">⏳ ' + escHtml(title || stem) + '</span>';
    bar.style.display = 'flex';
  }}

  try {{
    const resp = await fetch(API + '/api/library/threads/content?stem=' + encodeURIComponent(stem));
    const data = await resp.json();
    if (data.error) {{ console.error('Thread load error:', data.error); return; }}

    // Guard: user may have switched to yet another thread during the fetch
    if (activeThread.stem !== stem) return;

    const meta = (libraryData && libraryData.threads || []).find(t => t.stem === stem);
    activeThread = {{
      stem,
      title: title || stem,
      content: data.content || '',
      status: (meta && meta.status) || 'library',
    }};
    renderThreadCtxBar();

    const ta = document.getElementById('chat-input');
    if (ta) ta.focus();
  }} catch (e) {{
    console.error('openThread error:', e);
  }}
}}

function renderThreadCtxBar() {{
  const bar = document.getElementById('thread-ctx-bar');
  const preview = document.getElementById('thread-ctx-preview');
  if (!bar) return;
  if (!activeThread) {{
    bar.style.display = 'none';
    if (preview) preview.style.display = 'none';
    return;
  }}
  bar.style.display = 'flex';
  const frozenBadge = activeThread.status === 'frozen'
    ? '<span class="thread-ctx-frozen">❄ zamrożony</span>'
    : '';
  bar.innerHTML =
    '<span class="thread-ctx-label">Kontekst</span>' +
    `<span class="thread-ctx-name">${{escHtml(activeThread.title)}}</span>` +
    frozenBadge +
    `<button class="thread-ctx-expand" onclick="toggleThreadPreview()" title="Podgląd">⊞</button>` +
    `<button class="thread-ctx-clear" onclick="clearActiveThread()" title="Usuń kontekst">✕</button>`;
  if (preview) {{
    preview.textContent = activeThread.content.slice(0, 800) + (activeThread.content.length > 800 ? '…' : '');
  }}
}}

function toggleThreadPreview() {{
  const preview = document.getElementById('thread-ctx-preview');
  if (!preview) return;
  preview.style.display = preview.style.display === 'none' ? 'block' : 'none';
}}

function clearActiveThread() {{
  activeThread = null;
  renderThreadCtxBar();
  const preview = document.getElementById('thread-ctx-preview');
  if (preview) preview.style.display = 'none';
}}

// Legacy — thread-view panel no longer used but keep for compatibility
function closeThreadView() {{
  const viewer = document.getElementById('thread-view');
  const chatEl = document.getElementById('chat-panel');
  if (viewer) viewer.style.display = 'none';
  if (chatEl) chatEl.style.display = 'flex';
}}

function renderMarkdown(md) {{
  // Simple markdown → HTML, line-by-line to avoid regex escaping issues
  const lines = md.split('\\n');
  const out = [];
  let inPre = false, preBuf = [], inUl = false;

  function flushUl() {{
    if (inUl) {{ out.push('</ul>'); inUl = false; }}
  }}

  for (let i = 0; i < lines.length; i++) {{
    const raw = lines[i];

    // code block fence
    if (raw.startsWith('```')) {{
      if (!inPre) {{ flushUl(); inPre = true; preBuf = []; }}
      else {{ out.push('<pre><code>' + escHtml(preBuf.join('\\n')) + '</code></pre>'); inPre = false; }}
      continue;
    }}
    if (inPre) {{ preBuf.push(raw); continue; }}

    const line = escHtml(raw);

    // headings
    if (line.startsWith('### ')) {{ flushUl(); out.push('<h3>' + line.slice(4) + '</h3>'); continue; }}
    if (line.startsWith('## '))  {{ flushUl(); out.push('<h2>' + line.slice(3) + '</h2>'); continue; }}
    if (line.startsWith('# '))   {{ flushUl(); out.push('<h1>' + line.slice(2) + '</h1>'); continue; }}

    // hr
    if (/^---+$/.test(line)) {{ flushUl(); out.push('<hr>'); continue; }}

    // list item
    if (line.startsWith('- ')) {{
      if (!inUl) {{ out.push('<ul>'); inUl = true; }}
      out.push('<li>' + inlineFormat(line.slice(2)) + '</li>');
      continue;
    }}

    // blank line
    if (!line.trim()) {{ flushUl(); out.push(''); continue; }}

    // paragraph / plain line
    flushUl();
    out.push('<p>' + inlineFormat(line) + '</p>');
  }}
  flushUl();
  return out.join('\\n');
}}

function inlineFormat(s) {{
  s = s.replace(/[*][*](.+?)[*][*]/g, '<strong>$1</strong>');
  s = s.replace(/[*](.+?)[*]/g,       '<em>$1</em>');
  s = s.replace(/`([^`]+)`/g,         '<code>$1</code>');
  return s;
}}

// ── Document library ─────────────────────────────────────────────────────────
async function loadDocs() {{
  try {{
    const resp = await fetch(API + '/api/library/docs');
    if (!resp.ok) return;
    const data = await resp.json();
    libraryData.docs = data.docs || [];
    renderDocs();
  }} catch (_) {{}}
}}

function renderDocs() {{
  const el = document.getElementById('docs-list');
  if (!el) return;
  const docs = libraryData.docs || [];
  if (!docs.length) {{
    el.innerHTML = '<div class="empty">Brak dokumentów</div>';
    return;
  }}
  const attached  = docs.filter(d => d.source === 'attached'  && !d.archived);
  const generated = docs.filter(d => d.source === 'generated' && !d.archived);
  const artifacts = docs.filter(d => d.source === 'artifact');

  let html = '';
  if (attached.length) {{
    html += '<div class="panel-sub">Załączone</div>';
    html += attached.map(d => docItemHtml(d)).join('');
  }}
  if (generated.length) {{
    html += '<div class="panel-sub">Wygenerowane</div>';
    html += generated.map(d => docItemHtml(d)).join('');
  }}
  if (artifacts.length) {{
    html += '<div class="panel-sub">Artefakty</div>';
    html += artifacts.map(d => docItemHtml(d)).join('');
  }}
  el.innerHTML = html || '<div class="empty">Brak dokumentów</div>';

  // Attach events via delegation
  el.querySelectorAll('.doc-item').forEach(function(item) {{
    const pathRel = item.getAttribute('data-path-rel');
    const name = item.getAttribute('data-name');
    item.addEventListener('click', function() {{ openDoc(pathRel, name); }});
    const archBtn = item.querySelector('.doc-arch-btn');
    if (archBtn) {{
      archBtn.addEventListener('click', function(e) {{
        e.stopPropagation();
        archiveDoc(pathRel);
      }});
    }}
  }});
}}

function docItemHtml(d) {{
  const icon = d.source === 'attached' ? '📎' : d.source === 'generated' ? '✍' : '📄';
  const pathAttr = escHtml(d.path_rel);
  const nameAttr = escHtml(d.name);
  return '<div class="doc-item" data-path-rel="' + pathAttr + '" data-name="' + nameAttr + '">' +
    '<span class="doc-icon">' + icon + '</span>' +
    '<span class="doc-name" title="' + nameAttr + '">' + nameAttr + '</span>' +
    '<span class="doc-source">' + escHtml(d.source) + '</span>' +
    '<button class="doc-arch-btn" title="Archiwizuj">⊘</button>' +
    '</div>';
}}

async function openDoc(path_rel, name) {{
  try {{
    const resp = await fetch(API + '/api/library/docs/content?path_rel=' + encodeURIComponent(path_rel));
    const data = await resp.json();
    if (data.error) {{ console.error('openDoc error:', data.error); return; }}
    activeDoc = {{name: name, path_rel: path_rel, content: data.content || ''}};
    renderDocCtxBar();
    const ta = document.getElementById('chat-input');
    if (ta) ta.focus();
  }} catch (e) {{
    console.error('openDoc error:', e);
  }}
}}

function renderDocCtxBar() {{
  const bar = document.getElementById('doc-ctx-bar');
  const preview = document.getElementById('doc-ctx-preview');
  if (!bar) return;
  if (!activeDoc) {{
    bar.style.display = 'none';
    if (preview) preview.style.display = 'none';
    return;
  }}
  bar.style.display = 'flex';
  bar.innerHTML =
    '<span class="thread-ctx-label">Dok.</span>' +
    '<span class="doc-ctx-name">' + escHtml(activeDoc.name) + '</span>' +
    '<button class="thread-ctx-expand" onclick="toggleDocPreview()" title="Podgląd">⊞</button>' +
    '<button class="thread-ctx-clear" onclick="clearActiveDoc()" title="Usuń kontekst">✕</button>';
  if (preview) {{
    preview.textContent = activeDoc.content.slice(0, 800) + (activeDoc.content.length > 800 ? '…' : '');
  }}
}}

function toggleDocPreview() {{
  const preview = document.getElementById('doc-ctx-preview');
  if (!preview) return;
  preview.style.display = preview.style.display === 'none' ? 'block' : 'none';
}}

function clearActiveDoc() {{
  activeDoc = null;
  renderDocCtxBar();
  const preview = document.getElementById('doc-ctx-preview');
  if (preview) preview.style.display = 'none';
}}

async function archiveDoc(path_rel) {{
  try {{
    await fetch(API + '/api/library/docs/archive', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{path_rel: path_rel}})
    }});
    loadDocs();
  }} catch (e) {{
    console.error('archiveDoc error:', e);
  }}
}}

function handleFileSelect(input) {{
  const file = input.files && input.files[0];
  if (!file) return;

  const zone = document.getElementById('upload-zone');
  const origHTML = zone ? zone.innerHTML : '';
  if (zone) zone.innerHTML = '<span style="color:var(--text3)">⏳ ' + escHtml(file.name) + '…</span>';

  const reader = new FileReader();
  reader.onload = async function(e) {{
    try {{
      // Convert ArrayBuffer → base64 in chunks (avoids stack overflow for large files)
      const uint8 = new Uint8Array(e.target.result);
      const CHUNK = 8192;
      let binary = '';
      for (let i = 0; i < uint8.length; i += CHUNK) {{
        binary += String.fromCharCode.apply(null, uint8.subarray(i, i + CHUNK));
      }}
      const b64 = btoa(binary);

      const resp = await fetch(API + '/api/library/docs/upload', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{filename: file.name, content_b64: b64, mime: file.type}})
      }});
      const data = await resp.json();

      if (data.ok && data.doc) {{
        if (zone) zone.innerHTML = '<span style="color:var(--ok)">✓ ' + escHtml(file.name) + '</span>';
        setTimeout(() => {{ if (zone) zone.innerHTML = origHTML; }}, 2000);
        loadDocs();
        openDoc(data.doc.path_rel, data.doc.name);
      }} else {{
        const msg = data.error || 'Błąd uploadu';
        if (zone) zone.innerHTML = '<span style="color:var(--red)">✕ ' + escHtml(msg) + '</span>';
        setTimeout(() => {{ if (zone) zone.innerHTML = origHTML; }}, 3000);
      }}
    }} catch (err) {{
      console.error('upload error:', err);
      if (zone) zone.innerHTML = '<span style="color:var(--red)">✕ Błąd połączenia</span>';
      setTimeout(() => {{ if (zone) zone.innerHTML = origHTML; }}, 3000);
    }} finally {{
      input.value = '';
    }}
  }};
  reader.onerror = function() {{
    if (zone) zone.innerHTML = '<span style="color:var(--red)">✕ Nie można odczytać pliku</span>';
    setTimeout(() => {{ if (zone) zone.innerHTML = origHTML; }}, 3000);
    input.value = '';
  }};
  reader.readAsArrayBuffer(file);
}}

function setupDragDrop() {{
  const zone = document.getElementById('upload-zone');
  if (!zone) return;
  // prevent label's default (opening file dialog) during drag
  zone.addEventListener('dragenter', function(e) {{ e.preventDefault(); }});
  zone.addEventListener('dragover',  function(e) {{
    e.preventDefault();
    zone.classList.add('drag-over');
  }});
  zone.addEventListener('dragleave', function(e) {{
    if (!zone.contains(e.relatedTarget)) zone.classList.remove('drag-over');
  }});
  zone.addEventListener('drop', function(e) {{
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (!file) return;
    // inject file into actual input so handleFileSelect works consistently
    const input = document.getElementById('file-upload-input');
    if (!input) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    handleFileSelect(input);
  }});
}}

// ── v0.6.2: Drag-and-drop on chat area → auto-thread ─────────────────────────
function setupChatDragDrop() {{
  const chatArea = document.querySelector('.chat-input-area');
  if (!chatArea) return;
  chatArea.addEventListener('dragenter', function(e) {{ e.preventDefault(); }});
  chatArea.addEventListener('dragover', function(e) {{
    e.preventDefault();
    chatArea.style.borderColor = 'var(--green)';
    chatArea.style.background = 'rgba(42,154,106,.06)';
  }});
  chatArea.addEventListener('dragleave', function(e) {{
    if (!chatArea.contains(e.relatedTarget)) {{
      chatArea.style.borderColor = '';
      chatArea.style.background = '';
    }}
  }});
  chatArea.addEventListener('drop', function(e) {{
    e.preventDefault();
    chatArea.style.borderColor = '';
    chatArea.style.background = '';
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (!file) return;
    const isDoc = /[.](pdf|docx?|txt|md|rtf|png|jpe?g|tiff?|heic|webp)$/i.test(file.name);
    if (isDoc) {{
      const choice = confirm(
        `Upuszczono: ${{file.name}}\n\nOK = Utwórz nowy wątek z tego pliku\nAnuluj = Załącz jako dokument`
      );
      if (choice) {{
        uploadFileToThread(file);
        return;
      }}
    }}
    // Fallback: regular upload
    const input = document.getElementById('file-upload-input');
    if (input) {{
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      handleFileSelect(input);
    }}
  }});
}}

// ── MemoryKind helpers ────────────────────────────────────────────────────────
const KIND_LABELS = {{
  user_preference: 'Preferencja', project_fact: 'Fakt',
  procedural_lesson: 'Lekcja', failure_pattern: 'Błąd',
  style_rule: 'Styl', domain_constraint: 'Ograniczenie', temporary_context: 'Tymczasowe'
}};
const KIND_COLORS = {{
  user_preference: 'var(--blue)', project_fact: 'var(--ok)',
  procedural_lesson: '#9c6ef8', failure_pattern: 'var(--red)',
  style_rule: 'var(--warning)', domain_constraint: 'var(--text2)', temporary_context: 'var(--text3)'
}};
function kindBadge(kind) {{
  if (!kind) return '';
  const label = KIND_LABELS[kind] || kind;
  const color = KIND_COLORS[kind] || 'var(--text3)';
  return `<span class="kind-badge" style="color:${{color}};border-color:${{color}}">${{escHtml(label)}}</span>`;
}}

// ── Memory ────────────────────────────────────────────────────────────────────
async function loadMemory() {{
  try {{
    const resp = await fetch(API + '/api/memory');
    const data = await resp.json();
    renderMemory(data.insights || []);
  }} catch (_) {{}}
}}

function renderMemory(insights) {{
  const el = document.getElementById('memory-list');
  if (!el) return;
  const active = insights.filter(i => !i.archived);
  if (!active.length) {{
    el.innerHTML = '<div class="empty">Brak zapamiętanych ustaleń</div>';
    return;
  }}
  el.innerHTML = active.map(i => `
    <div class="insight-item">
      <button class="insight-arch-btn" onclick="archiveInsight('${{escHtml(i.id)}}');event.stopPropagation()" title="Archiwizuj">⊘</button>
      <div style="display:flex;align-items:center;flex-wrap:wrap;gap:.2rem;margin-bottom:.1rem">
        ${{kindBadge(i.kind)}}
        ${{i.topic ? '<span class="insight-topic" style="margin-bottom:0">' + escHtml(i.topic) + '</span>' : ''}}
      </div>
      <div class="insight-content">${{escHtml(i.content)}}</div>
      <div class="insight-meta">${{i.created}}${{i.linked_thread ? ' · ' + escHtml(i.linked_thread) : ''}}${{i.auto_score != null ? ' · score ' + i.auto_score : ''}}</div>
    </div>`).join('');
}}

async function saveInsight(content, topic) {{
  try {{
    await fetch(API + '/api/memory/save', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{content, topic: topic || ''}})
    }});
    loadMemory();
  }} catch (_) {{}}
}}

async function archiveInsight(id) {{
  await fetch(API + '/api/memory/archive', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{insight_id: id}})
  }});
  loadMemory();
}}

// ── Memory candidates ────────────────────────────────────────────────────
function switchMemTab(tab) {{
  const isInsights = tab === 'insights';
  document.getElementById('memory-list').style.display    = isInsights ? '' : 'none';
  document.getElementById('candidates-list').style.display = isInsights ? 'none' : '';
  document.getElementById('tab-insights').classList.toggle('active', isInsights);
  document.getElementById('tab-candidates').classList.toggle('active', !isInsights);
  if (!isInsights) loadCandidates();
}}

async function loadCandidates() {{
  try {{
    const resp = await fetch(API + '/api/memory/candidates');
    const data = await resp.json();
    renderCandidates(data.candidates || []);
  }} catch (_) {{}}
}}

function _recBadge(rec) {{
  if (!rec) return '';
  const map = {{
    promote: ['cand-rec-promote', '↑ Promuj'],
    reject: ['cand-rec-reject', '✕ Odrzuć'],
    manual_review: ['cand-rec-manual', '⚠ Review'],
    keep_candidate: ['cand-rec-keep', '… Trzymaj']
  }};
  const [cls, label] = map[rec] || ['cand-rec-keep', rec];
  return `<span class="cand-rec-badge ${{cls}}">${{label}}</span>`;
}}

function _scoreBar(score) {{
  if (score == null) return '';
  const pct = Math.max(0, Math.min(100, Math.round(score * 111)));  // ~0.90 max → 100%
  const color = score >= 0.70 ? 'var(--ok)' : score < 0.30 ? 'var(--red)' : 'var(--warning)';
  return `<div class="cand-score-row">
    <div class="cand-score-bar-wrap"><div class="cand-score-bar" style="width:${{pct}}%;background:${{color}}"></div></div>
    <span class="cand-score-num">${{(score*100).toFixed(0)}}%</span>
  </div>`;
}}

function renderCandidates(candidates) {{
  const el = document.getElementById('candidates-list');
  if (!el) return;
  if (!candidates.length) {{
    el.innerHTML = '<div class="empty">Brak kandydatów</div>';
    return;
  }}
  el.innerHTML = candidates.map(c => `
    <div class="insight-item candidate-item" style="border-left:2px solid var(--warning)">
      <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px;flex-wrap:wrap">
        <button class="insight-arch-btn" style="color:var(--ok);opacity:1"
          onclick="promoteCandidate('${{escHtml(c.id)}}');event.stopPropagation()" title="Zatwierdź → memory">✓</button>
        <button class="insight-arch-btn" style="opacity:1"
          onclick="discardCandidate('${{escHtml(c.id)}}');event.stopPropagation()" title="Odrzuć">✕</button>
        ${{kindBadge(c.kind)}}
        ${{_recBadge(c._recommendation)}}
      </div>
      ${{c.topic ? '<div class="insight-topic">' + escHtml(c.topic) + '</div>' : ''}}
      <div class="insight-content">${{escHtml(c.content)}}</div>
      ${{_scoreBar(c._score)}}
      ${{c.note ? '<div class="insight-meta" style="font-style:italic">' + escHtml(c.note) + '</div>' : ''}}
      <div class="insight-meta">${{c.created}}${{c.linked_thread ? ' · ' + escHtml(c.linked_thread) : ''}}</div>
    </div>`).join('');
}}

async function saveCandidate(content, topic, note, linkedThread) {{
  try {{
    const resp = await fetch(API + '/api/memory/candidates/save', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{content, topic: topic||'', note: note||'', linked_thread: linkedThread||''}})
    }});
    const data = await resp.json();
    return data.ok ? data.candidate : null;
  }} catch (_) {{ return null; }}
}}

async function promoteCandidate(id) {{
  await fetch(API + '/api/memory/candidates/promote', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{candidate_id: id}})
  }});
  loadCandidates();
  loadMemory();
}}

async function discardCandidate(id) {{
  await fetch(API + '/api/memory/candidates/discard', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{candidate_id: id}})
  }});
  loadCandidates();
}}

function addSaveInsightButton(msgEl, content) {{
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;gap:6px;margin-top:6px';

  // Kandydat (staging)
  const btnCand = document.createElement('button');
  btnCand.className = 'save-insight-btn';
  btnCand.textContent = '📋 Kandydat';
  btnCand.title = 'Dodaj do staging area — wymaga zatwierdzenia';
  btnCand.onclick = async () => {{
    const topic = prompt('Temat (opcjonalnie):') || '';
    const note  = prompt('Notatka / powód (opcjonalnie):') || '';
    const c = await saveCandidate(content, topic, note, activeThread ? activeThread.stem : '');
    if (c) {{ btnCand.textContent = '✓ W kandydatach'; btnCand.classList.add('saved'); btnCand.disabled = true; }}
  }};

  // Bezpośredni zapis (durable)
  const btnDur = document.createElement('button');
  btnDur.className = 'save-insight-btn';
  btnDur.textContent = '💾 Zapamiętaj';
  btnDur.title = 'Zapisz od razu jako durable memory';
  btnDur.onclick = async () => {{
    const topic = prompt('Temat (opcjonalnie):') || '';
    await saveInsight(content, topic);
    btnDur.textContent = '✓ Zapisano';
    btnDur.classList.add('saved');
    btnDur.disabled = true;
    btnCand.disabled = true;
  }};

  // v1.0: append to active thread
  if (activeThread) {{
    const btnAppend = document.createElement('button');
    btnAppend.className = 'save-insight-btn append-btn';
    btnAppend.textContent = '📎 Do wątku';
    btnAppend.title = 'Dołącz do wątku: ' + activeThread.title;
    btnAppend.onclick = async () => {{
      const sectionTitle = prompt('Tytuł sekcji:', 'Wynik AI') || 'Wynik AI';
      const ok = await appendToThread(activeThread.stem, sectionTitle, content);
      if (ok) {{
        btnAppend.textContent = '✓ Dołączono';
        btnAppend.classList.add('saved');
        btnAppend.disabled = true;
      }} else {{
        btnAppend.textContent = '✕ Błąd';
      }}
    }};
    wrap.appendChild(btnAppend);
  }}

  wrap.appendChild(btnCand);
  wrap.appendChild(btnDur);
  msgEl.appendChild(wrap);
}}

// ── v1.0 — Thread append + status ─────────────────────────────────────────────

async function appendToThread(stem, sectionTitle, content) {{
  try {{
    const resp = await fetch(
      API + '/api/library/threads/' + encodeURIComponent(stem) + '/append',
      {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{section_title: sectionTitle, content}}),
      }}
    );
    const data = await resp.json();
    if (data.ok) {{
      // Refresh local thread content so subsequent appends stack correctly
      if (activeThread && activeThread.stem === stem) {{
        const tr = await fetch(
          API + '/api/library/threads/content?stem=' + encodeURIComponent(stem)
        ).then(r => r.json()).catch(() => null);
        if (tr && tr.content) activeThread.content = tr.content;
      }}
      loadLibrary();
      return true;
    }}
    return false;
  }} catch(e) {{
    console.error('appendToThread:', e);
    return false;
  }}
}}

async function toggleThreadStatus(stem, currentStatus) {{
  const newStatus = currentStatus === 'frozen' ? 'active' : 'frozen';
  try {{
    const resp = await fetch(
      API + '/api/library/threads/' + encodeURIComponent(stem) + '/set-status',
      {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{status: newStatus}}),
      }}
    );
    const data = await resp.json();
    if (data.ok) {{
      // Update local activeThread status if it matches
      if (activeThread && activeThread.stem === stem) {{
        activeThread.status = newStatus;
        renderThreadCtxBar();
      }}
      loadLibrary();
    }}
  }} catch(e) {{
    console.error('toggleThreadStatus:', e);
  }}
}}

// ── Search ────────────────────────────────────────────────────────────────────
let searchTimeout = null;
let _searchFilter = ''; // v0.7: source filter

function setSearchFilter(btn, filter) {{
  _searchFilter = filter;
  document.querySelectorAll('.search-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  // Re-run search with new filter
  const inp = document.getElementById('search-input');
  if (inp && inp.value.trim()) onSearchInput(inp.value);
}}

function openSearch() {{
  const overlay = document.getElementById('search-overlay');
  if (overlay) {{ overlay.style.display = 'flex'; }}
  setTimeout(() => {{
    const inp = document.getElementById('search-input');
    if (inp) inp.focus();
  }}, 50);
}}

function closeSearch() {{
  const overlay = document.getElementById('search-overlay');
  if (overlay) overlay.style.display = 'none';
}}

function onSearchKey(e) {{
  if (e.key === 'Escape') closeSearch();
}}

function onSearchInput(q) {{
  clearTimeout(searchTimeout);
  if (!q.trim()) {{
    document.getElementById('search-results').innerHTML = '<div class="search-empty">Wpisz frazę…</div>';
    return;
  }}
  searchTimeout = setTimeout(() => runSearch(q), 250);
}}

let _searchResults = [];

async function runSearch(q) {{
  const el = document.getElementById('search-results');
  if (!el) return;
  el.innerHTML = '<div class=”search-empty”>Szukam…</div>';
  try {{
    const filterParam = _searchFilter ? '&source=' + encodeURIComponent(_searchFilter) : '';
    const resp = await fetch(API + '/api/search?q=' + encodeURIComponent(q) + filterParam);
    const data = await resp.json();
    const results = data.results || [];
    _searchResults = results;
    if (!results.length) {{
      el.innerHTML = '<div class=”search-empty”>Brak wyników dla „' + escHtml(q) + '”</div>';
      return;
    }}
    const sourceIcons = {{thread:'📝', doc:'📎', artifact:'📄', insight:'💡', candidate:'📋', notebook_silo_1:'🔬', notebook_silo_2:'⚖️'}};
    const sourceLabels = {{thread:'wątek', doc:'dokument', artifact:'artefakt', insight:'pamięć', candidate:'kandydat', notebook_silo_1:'notebook', notebook_silo_2:'notebook'}};
    el.innerHTML = results.map(function(r, idx) {{
      const icon = sourceIcons[r.type] || '📄';
      const label = sourceLabels[r.type] || r.type.replace('_',' ');
      const score = r.score ? '<span style=”font-size:.6rem;color:var(--text3);margin-left:auto;font-family:monospace”>' + r.score.toFixed(1) + '</span>' : '';
      const domain = r.domain ? '<span style=”font-size:.6rem;color:var(--text3);margin-left:.3rem;background:var(--surf3);padding:0 .25rem;border-radius:2px”>' + escHtml(r.domain) + '</span>' : '';
      const title = r.title || r.name || '—';
      return '<div class=”search-result” data-idx=”' + idx + '” onclick=”openSearchResult(' + idx + ')”>' +
        '<span class=”search-result-type”>' + icon + ' ' + escHtml(label) + '</span>' +
        '<div class=”search-result-body”>' +
          '<div class=”search-result-name”>' + escHtml(title) + domain + score + '</div>' +
          '<div class=”search-result-snippet”>' + escHtml(r.snippet || '') + '</div>' +
        '</div>' +
      '</div>';
    }}).join('');
  }} catch (_) {{
    el.innerHTML = '<div class=”search-empty”>Błąd wyszukiwania</div>';
  }}
}}

function openSearchResult(idx) {{
  const r = _searchResults[idx];
  if (!r) return;
  closeSearch();
  if (r.type === 'thread') {{
    openThread(r.path_rel.replace('library/threads/','').replace('.md',''), r.name);
  }} else if (r.type.startsWith('doc') || r.type === 'artifact') {{
    openDoc(r.path_rel, r.name);
  }} else if (r.type === 'insight') {{
    document.getElementById('memory-list') && document.getElementById('memory-list').scrollIntoView({{behavior:'smooth'}});
  }}
}}

// ── Active project ─────────────────────────────────────────────────────────────
let activeProjectData = null;

async function loadActiveProject() {{
  try {{
    const resp = await fetch(API + '/api/library/projects/active');
    const data = await resp.json();
    activeProjectData = data.project || null;
    renderProjCtxBar();
  }} catch (_) {{}}
}}

function renderProjCtxBar() {{
  const bar = document.getElementById('proj-ctx-bar');
  const nameEl = document.getElementById('proj-ctx-name');
  if (!bar) return;
  if (!activeProjectData) {{ bar.style.display = 'none'; return; }}
  bar.style.display = 'flex';
  if (nameEl) nameEl.textContent = activeProjectData.name || activeProjectData.project_id;
}}

async function activateProject(projectId) {{
  try {{
    const resp = await fetch(API + '/api/library/projects/activate', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{project_id: projectId}})
    }});
    const data = await resp.json();
    if (data.ok) {{ activeProjectData = data.project; renderProjCtxBar(); }}
  }} catch (_) {{}}
}}

async function deactivateProject() {{
  await fetch(API + '/api/library/projects/deactivate', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{}}),
  }});
  activeProjectData = null;
  renderProjCtxBar();
}}

// ── Research tools ─────────────────────────────────────────────────────────────
let _researchTool = null;
let _selectedThreads = []; // list of {{stem, title, content}}

function openLitMap() {{
  _researchTool = 'literature_map';
  document.getElementById('research-modal-title').textContent = '\U0001F4DA Mapa literatury';
  document.getElementById('research-modal-label').textContent = 'Temat / obszar literatury';
  document.getElementById('research-modal-input').placeholder = 'np. "skalarne pola w kosmologii przedbounce"';
  document.getElementById('research-modal-input').value = '';
  document.getElementById('research-modal-overlay').style.display = 'flex';
  setTimeout(() => document.getElementById('research-modal-input').focus(), 50);
}}

function openStressTest() {{
  _researchTool = 'stress_test';
  document.getElementById('research-modal-title').textContent = '⊗ Stress-test hipotezy';
  document.getElementById('research-modal-label').textContent = 'Hipoteza do analizy';
  document.getElementById('research-modal-input').placeholder = 'Sformułuj hipotezę precyzyjnie…';
  document.getElementById('research-modal-input').value = '';
  document.getElementById('research-modal-overlay').style.display = 'flex';
  setTimeout(() => document.getElementById('research-modal-input').focus(), 50);
}}

function openSynthesis() {{
  if (_selectedThreads.length < 2) {{
    alert('Zaznacz co najmniej 2 wątki (checkboxy przy wątkach).');
    return;
  }}
  _researchTool = 'synthesis';
  const names = _selectedThreads.map(t => t.title).join(', ');
  document.getElementById('research-modal-title').textContent = '⇄ Synteza cross-thread';
  document.getElementById('research-modal-label').textContent = 'Zaznaczone wątki: ' + names;
  document.getElementById('research-modal-input').placeholder = 'Opcjonalna wskazówka dla syntezy (lub zostaw puste)';
  document.getElementById('research-modal-input').value = '';
  document.getElementById('research-modal-overlay').style.display = 'flex';
  setTimeout(() => document.getElementById('research-modal-input').focus(), 50);
}}

function closeResearchModal() {{
  document.getElementById('research-modal-overlay').style.display = 'none';
}}

async function submitResearchModal() {{
  const input = document.getElementById('research-modal-input').value.trim();
  closeResearchModal();

  const endpoints = {{
    literature_map: '/api/research/literature-map',
    stress_test:    '/api/research/stress-test',
    synthesis:      '/api/research/synthesize',
  }};
  const endpoint = endpoints[_researchTool];
  if (!endpoint) return;

  let bodyData = {{}};
  if (_researchTool === 'literature_map') bodyData = {{subject: input}};
  else if (_researchTool === 'stress_test') bodyData = {{hypothesis: input}};
  else if (_researchTool === 'synthesis') {{
    bodyData = {{
      subject: input || _selectedThreads.map(t => t.title).join(' + '),
      threads: _selectedThreads.map(t => ({{title: t.title, content: t.content}}))
    }};
  }}

  // Show user message in chat
  const label = {{
    literature_map: '\U0001F4DA Mapa literatury: ' + input,
    stress_test:    '⊗ Stress-test: ' + input,
    synthesis:      '⇄ Synteza: ' + _selectedThreads.map(t => t.title).join(', '),
  }}[_researchTool] || input;

  conversation.push({{role: 'user', content: label}});
  renderConversation(); scrollChat();

  // Stream response — uses the same streaming infrastructure as sendMessage()
  const btn = document.getElementById('send-btn');
  const spin = document.getElementById('spinner');
  btn.disabled = true; spin.style.display = 'inline-block';
  _isStreaming = true;
  _streamAbortCtrl = new AbortController();
  _streamingStem = activeThread ? activeThread.stem : null;
  const myStreamStem = _streamingStem;
  const myGeneration = ++_streamGeneration;

  conversation.push({{role: 'assistant', content: '', meta: {{streaming: true}}}});
  renderConversation(); scrollChat();

  try {{
    const response = await fetch(API + endpoint, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(bodyData),
      signal: _streamAbortCtrl ? _streamAbortCtrl.signal : undefined,
    }});
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {{
      const {{done, value}} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {{stream: true}});
      const parts = buffer.split('\\n\\n');
      buffer = parts.pop();
      for (const part of parts) {{
        if (!part.startsWith('data: ')) continue;
        try {{
          const event = JSON.parse(part.slice(6));
          const _onMyThread = (activeThread ? activeThread.stem : null) === myStreamStem;
          if (event.type === 'chunk') {{
            if (!_onMyThread) continue;
            const lastIdx = conversation.length - 1;
            if (lastIdx < 0) continue;
            conversation[lastIdx].content += event.text || '';
            const bubbles = document.querySelectorAll('.msg-ai .msg-bubble');
            if (bubbles.length > 0) {{
              bubbles[bubbles.length-1].textContent = conversation[lastIdx].content;
              bubbles[bubbles.length-1].classList.add('streaming');
            }}
            scrollChat();
          }} else if (event.type === 'done') {{
            if (!_onMyThread) {{
              if (myStreamStem) {{
                const bgConv = _threadConversations[myStreamStem] || [];
                bgConv.push({{role: 'assistant', content: event.result || '', meta: event}});
                _threadConversations[myStreamStem] = bgConv;
                _persistConversation(myStreamStem, bgConv);
              }}
              continue;
            }}
            const lastIdx = conversation.length - 1;
            if (lastIdx >= 0) {{
              conversation[lastIdx] = {{
                role: 'assistant', content: event.result || conversation[lastIdx].content,
                meta: {{model_key: event.model_key, saved_to: event.saved_to}}
              }};
            }}
            _persistConversation(_currentStem(), conversation);
            renderConversation();
            const aiBubbles = document.querySelectorAll('.msg-ai');
            if (aiBubbles.length > 0) addSaveInsightButton(aiBubbles[aiBubbles.length-1], event.result || '');
            if (_researchTool === 'synthesis') {{ _selectedThreads = []; updateSynthesizeBtn(); }}
            scrollChat();
          }} else if (event.type === 'review') {{
            if (!_onMyThread) continue;
            const lastIdx = conversation.length - 1;
            if (lastIdx >= 0 && conversation[lastIdx].role === 'assistant') {{
              conversation[lastIdx].meta = Object.assign({{}}, conversation[lastIdx].meta, {{
                review: event.review, topology: event.topology,
              }});
            }}
            renderConversation();
            loadDarkroom();
            if (event.topology) {{
              const bubbles = document.querySelectorAll('.msg-ai .msg-bubble');
              if (bubbles.length > 0) renderTopology(event.topology, bubbles[bubbles.length-1].parentElement);
            }}
            scrollChat();
          }} else if (event.type === 'error') {{
            if (!_onMyThread) continue;
            const lastIdx = conversation.length - 1;
            if (lastIdx >= 0) {{
              const existing = conversation[lastIdx].content || '';
              conversation[lastIdx] = {{
                role: 'assistant',
                content: existing || event.error || 'Błąd odpowiedzi modelu.',
                meta: {{error: true}}
              }};
            }}
            renderConversation(); scrollChat();
          }}
        }} catch (_) {{}}
      }}
    }}
  }} catch (e) {{
    if (e.name !== 'AbortError') {{
      const lastIdx = conversation.length - 1;
      if (lastIdx >= 0) conversation[lastIdx] = {{role:'assistant', content:'Błąd: ' + e.message}};
      renderConversation();
    }}
  }} finally {{
    if (_streamGeneration === myGeneration) {{
      _isStreaming = false;
      _streamAbortCtrl = null;
      _streamingStem = null;
      btn.disabled = false;
      spin.style.display = 'none';
    }}
  }}
}}

// ── Thread multi-select for synthesis ─────────────────────────────────────────
async function onThreadCheckbox(checkbox, stem, title) {{
  if (checkbox.checked) {{
    // Fetch content for synthesis
    try {{
      const resp = await fetch(API + '/api/library/threads/content?stem=' + encodeURIComponent(stem));
      const data = await resp.json();
      _selectedThreads.push({{stem, title, content: data.content || ''}});
    }} catch (_) {{
      _selectedThreads.push({{stem, title, content: ''}});
    }}
  }} else {{
    _selectedThreads = _selectedThreads.filter(t => t.stem !== stem);
  }}
  updateSynthesizeBtn();
}}

function updateSynthesizeBtn() {{
  const n = _selectedThreads.length;
  // Old button (hidden, kept for compat)
  const btn = document.getElementById('synthesize-btn');
  if (btn) {{
    btn.style.display = n >= 2 ? 'block' : 'none';
    btn.textContent = '⇄ Syntezuj ' + n + ' wątki';
  }}
  // v0.6.4: prominent counter
  const counter = document.getElementById('synth-counter');
  const countNum = document.getElementById('synth-count-num');
  if (counter) {{
    counter.style.display = n >= 1 ? 'block' : 'none';
    if (countNum) countNum.textContent = n;
    // Pulse animation on change
    counter.classList.remove('pulse');
    void counter.offsetWidth; // force reflow
    if (n >= 1) counter.classList.add('pulse');
    // Change text based on count
    if (n < 2) {{
      counter.innerHTML = '<span class="synth-count" id="synth-count-num">' + n + '</span> Zaznacz min. 2 wątki do syntezy';
      counter.style.opacity = '0.6';
      counter.style.cursor = 'default';
    }} else {{
      counter.innerHTML = '<span class="synth-count" id="synth-count-num">' + n + '</span> ⇄ Syntezuj ' + n + ' zaznaczonych';
      counter.style.opacity = '1';
      counter.style.cursor = 'pointer';
    }}
  }}
}}

// ── Export (v0.8 — export menu) ───────────────────────────────────────────────
let _activeExportMenu = null;

function toggleExportMenu(stem, btnEl, event) {{
  if (event) event.stopPropagation();
  closeExportMenu();

  const menu = document.createElement('div');
  menu.className = 'export-menu show';
  menu.innerHTML =
    `<button class="export-menu-item" onclick="exportPolishedMd('${{stem}}')">📝 Polished Markdown</button>` +
    `<button class="export-menu-item" onclick="exportResearchBundle('${{stem}}')">📦 Research Bundle (ZIP)</button>` +
    `<button class="export-menu-item" onclick="exportShareHtml('${{stem}}')">🌐 Share HTML</button>` +
    `<button class="export-menu-item" onclick="previewShareHtml('${{stem}}')">👁 Podgląd HTML</button>` +
    `<div class="export-menu-sep"></div>` +
    `<button class="export-menu-item" onclick="exportThread('${{stem}}')">⬇ Prosty ZIP</button>`;
  btnEl.appendChild(menu);
  _activeExportMenu = menu;

  // Close on outside click
  setTimeout(function() {{
    document.addEventListener('click', _closeExportMenuHandler, {{once: true}});
  }}, 10);
}}

function _closeExportMenuHandler() {{ closeExportMenu(); }}

function closeExportMenu() {{
  if (_activeExportMenu) {{
    _activeExportMenu.remove();
    _activeExportMenu = null;
  }}
}}

function exportPolishedMd(stem) {{
  closeExportMenu();
  window.location.href = API + '/api/export/polished-md?stem=' + encodeURIComponent(stem);
}}

function exportResearchBundle(stem) {{
  closeExportMenu();
  window.location.href = API + '/api/export/research-bundle?stem=' + encodeURIComponent(stem);
}}

function exportShareHtml(stem) {{
  closeExportMenu();
  window.location.href = API + '/api/export/share-html?stem=' + encodeURIComponent(stem);
}}

function previewShareHtml(stem) {{
  closeExportMenu();
  window.open(API + '/api/export/share-html/preview?stem=' + encodeURIComponent(stem), '_blank');
}}

async function exportThread(stem, event) {{
  if (event) event.stopPropagation();
  closeExportMenu();
  window.location.href = API + '/api/export/thread?stem=' + encodeURIComponent(stem);
}}

async function exportProject(projectId, event) {{
  if (event) event.stopPropagation();
  window.location.href = API + '/api/export/project?project_id=' + encodeURIComponent(projectId);
}}

async function exportArtifact(name, event) {{
  if (event) event.stopPropagation();
  window.location.href = API + '/api/export/artifact?name=' + encodeURIComponent(name);
}}

// ── Disposition history chart ──────────────────────────────────────────────────
function renderDispositionHistoryChart(history) {{
  const el = document.getElementById('disp-history-chart');
  if (!el) return;
  if (!history || history.length < 2) {{
    el.innerHTML = '<div class="empty" style="font-size:.7rem;padding:.5rem 0">Brak historii zmian</div>';
    return;
  }}

  const keys = ['skepticism_level','falsification_preference','review_strictness','uncertainty_tolerance'];
  const colors = ['#4a9a4a','#4a7aaa','#c8a000','#8a4a8a'];
  const W = 220, H = 72, PAD = 4;

  const allValues = history.flatMap(function(s) {{
    return keys.map(function(k) {{ return s.values && s.values[k] != null ? s.values[k] : null; }}).filter(function(v) {{ return v !== null; }});
  }});
  const minV = Math.min.apply(null, allValues.concat([0]));
  const maxV = Math.max.apply(null, allValues.concat([1]));
  const xStep = (W - PAD*2) / Math.max(history.length - 1, 1);

  function toX(i) {{ return PAD + i * xStep; }}
  function toY(v) {{ return PAD + (H - PAD*2) * (1 - (v - minV) / (maxV - minV)); }}

  var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">';
  var zeroY = toY(0.5).toFixed(1);
  svg += '<line x1="' + PAD + '" y1="' + zeroY + '" x2="' + (W-PAD) + '" y2="' + zeroY + '" class="chart-zero"/>';

  keys.forEach(function(k, ki) {{
    var pts = history.map(function(s, i) {{
      var val = (s.values && s.values[k] != null) ? s.values[k] : 0.5;
      return [toX(i), toY(val)];
    }});
    var d = pts.map(function(p, i) {{
      return (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ',' + p[1].toFixed(1);
    }}).join(' ');
    svg += '<path d="' + d + '" class="chart-line" stroke="' + colors[ki] + '" opacity="0.8"/>';
    var lp = pts[pts.length - 1];
    svg += '<circle cx="' + lp[0].toFixed(1) + '" cy="' + lp[1].toFixed(1) + '" r="2" fill="' + colors[ki] + '"/>';
  }});

  svg += '</svg>';
  el.innerHTML = svg;
}}

// ── Epistemic report ───────────────────────────────────────────────────────────
var _reportVisible = false;

async function loadLatestReport() {{
  try {{
    const resp = await fetch(API + '/api/darkroom/epistemic-report');
    const data = await resp.json();
    renderReport(data.report);
  }} catch (_) {{}}
}}

function renderReport(report) {{
  const dateEl   = document.getElementById('report-date');
  const textEl   = document.getElementById('report-text');
  const toggleEl = document.getElementById('report-toggle-btn');
  if (!report) {{
    if (dateEl) dateEl.textContent = 'Brak raportu — wygeneruj pierwszy';
    return;
  }}
  if (dateEl) dateEl.textContent = report.date || '';
  if (textEl) textEl.textContent = report.analysis || '';
  if (toggleEl) {{ toggleEl.style.display = 'block'; toggleEl.textContent = '▼ Pokaż raport'; }}
}}

function toggleReport() {{
  const textEl   = document.getElementById('report-text');
  const toggleEl = document.getElementById('report-toggle-btn');
  if (!textEl) return;
  _reportVisible = !_reportVisible;
  textEl.classList.toggle('visible', _reportVisible);
  if (toggleEl) toggleEl.textContent = _reportVisible ? '▲ Ukryj raport' : '▼ Pokaż raport';
}}

function copyReport() {{
  const dateEl = document.getElementById('report-date');
  const textEl = document.getElementById('report-text');
  const body   = textEl ? (textEl.textContent || '').trim() : '';
  if (!body) {{ return; }}
  const date = dateEl ? (dateEl.textContent || '').trim() : '';
  const out  = (date ? '# Raport epistemiczny — ' + date + '\\n\\n' : '') + body;
  copyText(out, document.getElementById('report-copy-btn'));
}}

async function generateReport() {{
  const btn = document.getElementById('report-generate-btn');
  if (!btn) return;
  btn.textContent = '⏳ Generowanie…';
  btn.classList.add('generating');
  btn.disabled = true;
  try {{
    const resp = await fetch(API + '/api/darkroom/generate-report', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{}}),
    }});
    const data = await resp.json();
    if (data.report) {{
      renderReport(data.report);
      _reportVisible = true;
      const textEl = document.getElementById('report-text');
      if (textEl) textEl.classList.add('visible');
      const toggleEl = document.getElementById('report-toggle-btn');
      if (toggleEl) toggleEl.textContent = '▲ Ukryj raport';
    }}
  }} catch (_) {{}} finally {{
    btn.textContent = '⟳ Generuj raport';
    btn.classList.remove('generating');
    btn.disabled = false;
  }}
}}

// ── Model comparison ───────────────────────────────────────────────────────────
function openCompare() {{
  document.getElementById('compare-overlay').style.display = 'flex';
  setTimeout(function() {{
    const inp = document.getElementById('compare-input');
    if (inp) inp.focus();
  }}, 50);
}}

function closeCompare() {{
  document.getElementById('compare-overlay').style.display = 'none';
}}

async function runCompare() {{
  const input = document.getElementById('compare-input');
  const btn   = document.getElementById('compare-run-btn');
  const task  = (input && input.value || '').trim();
  if (!task) return;

  btn.disabled = true;
  btn.textContent = '⏳ Porównuję…';
  ['haiku','sonnet','opus'].forEach(function(m) {{
    const el = document.getElementById('cmp-' + m);
    if (el) el.textContent = '⏳ Ładowanie…';
    const col = el && el.closest('.compare-col');
    const title = col && col.querySelector('.compare-col-title');
    if (title) title.innerHTML = m.charAt(0).toUpperCase() + m.slice(1);
  }});

  try {{
    const resp = await fetch(API + '/api/research/compare-models', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{task: task}})
    }});
    const data = await resp.json();
    const cmp = data.comparison || {{}};

    ['haiku','sonnet','opus'].forEach(function(m) {{
      const r = cmp[m] || {{}};
      const el = document.getElementById('cmp-' + m);
      const col = el && el.closest('.compare-col');
      const title = col && col.querySelector('.compare-col-title');

      if (r.error) {{
        if (el) el.textContent = '⚠ ' + r.error;
        return;
      }}
      const verdictCls = r.verdict === 'pass' ? 'pass' : r.verdict === 'flag' ? 'flag' : 'fail';
      if (title) title.innerHTML =
        (m.charAt(0).toUpperCase() + m.slice(1)) + ' ' +
        '<span class="compare-verdict ' + verdictCls + '">' + (r.verdict || '?').toUpperCase() + '</span>' +
        (r.severity != null ? ' <span style="font-size:.62rem;color:var(--text3)">' + r.severity.toFixed(2) + '</span>' : '');
      if (el) el.textContent = r.result || '';

      if (r.topology && !r.topology.error && col) {{
        renderTopology(r.topology, col);
      }}
    }});
  }} catch (e) {{
    ['haiku','sonnet','opus'].forEach(function(m) {{
      const el = document.getElementById('cmp-' + m);
      if (el) el.textContent = 'Błąd: ' + e.message;
    }});
  }} finally {{
    btn.disabled = false;
    btn.textContent = '▶ Porównaj';
  }}
}}

// ── Utils ─────────────────────────────────────────────────────────────────────
function escHtml(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ── Silo Science ──────────────────────────────────────────────────────────────
async function loadSiloScience() {{
  try {{
    const [infoResp, skillsResp, nbResp] = await Promise.all([
      fetch(API + '/api/silos/silo_1/info').then(r => r.json()).catch(() => null),
      fetch(API + '/api/silos/silo_1/skills').then(r => r.json()).catch(() => ({{skills:[]}})),
      fetch(API + '/api/silos/silo_1/notebooks').then(r => r.json()).catch(() => ({{notebooks:[]}})),
    ]);
    const container = document.getElementById('silos-widgets-container');
    if (!container) return;

    if (!infoResp) {{
      container.innerHTML = '<div style="color:var(--text3);font-size:.72rem">Silo Science niedostępny</div>';
      return;
    }}

    const name    = infoResp.name || 'Science';
    const hashtag = infoResp.hashtag || '#science';
    const stype   = infoResp.type || 'open';
    const badge   = stype === 'open' ? 'OPEN' : 'CLOSED';
    const bc      = stype === 'open' ? '#2a9d8f' : '#e76f51';
    const skills  = skillsResp.skills || [];
    const nbs     = nbResp.notebooks || [];

    let skillsHtml = skills.length
      ? skills.map(s => `<div class="silo-skill-item"><span class="silo-skill-name">${{escHtml(s.name)}}</span><button class="silo-skill-tag" onclick="runSiloSkill('${{s.id}}')">▶</button></div>`).join('')
      : '<div style="font-size:.7rem;color:var(--text3)">Brak skills</div>';
    let nbHtml = nbs.length
      ? nbs.slice(-3).map(n => `<div class="silo-nb-item" onclick="openScienceNotebook('${{n.id}}')">${{escHtml(n.title)}}</div>`).join('')
      : '<div style="font-size:.7rem;color:var(--text3)">Brak notebooków</div>';

    container.innerHTML = `
      <div class="silo-widget">
        <div class="silo-widget-header">
          <span class="silo-widget-name">🔬 ${{escHtml(name)}}</span>
          <span class="silo-type-badge" style="background:${{bc}}22;color:${{bc}}">${{badge}}</span>
          <span class="silo-hashtag">${{escHtml(hashtag)}}</span>
        </div>
        <div class="silo-policy-row">Ext LLM ✓ &nbsp;·&nbsp; SM ✓ &nbsp;·&nbsp; DARKROOM ✓</div>
        <div class="silo-actions">
          <button class="silo-btn" onclick="changeSiloHashtag()">✏ Label</button>
          <button class="silo-btn" onclick="newScienceNotebook()">📓 Notebook</button>
          <button class="silo-btn" onclick="runSiloSM()">🌙 SM</button>
        </div>
        <div style="font-size:.68rem;font-weight:700;color:var(--text3);text-transform:uppercase;margin:.3rem 0 .2rem">Skills (${{skills.length}})</div>
        <div class="silo-skills-list">${{skillsHtml}}</div>
        <div style="font-size:.68rem;font-weight:700;color:var(--text3);text-transform:uppercase;margin:.4rem 0 .2rem">Notebooki</div>
        <div>${{nbHtml}}</div>
      </div>`;
  }} catch(e) {{
    const container = document.getElementById('silos-widgets-container');
    if (container) container.innerHTML = `<div style="font-size:.72rem;color:var(--text3)">Błąd: ${{e.message}}</div>`;
  }}
}}

async function runSiloSkill(skillId) {{
  const inputs = {{}};
  try {{
    const resp = await fetch(API + '/api/silos/silo_1/skills/' + skillId);
    const skill = await resp.json();
    const title = skill.name || skillId;
    const userInputStr = prompt(`Uruchamiam skill: ${{title}}\n\nPodaj dane wejściowe (JSON lub tekst):`);
    if (!userInputStr) return;
    let inp;
    try {{ inp = JSON.parse(userInputStr); }} catch {{ inp = {{text: userInputStr}}; }}

    const runResp = await fetch(API + '/api/silos/silo_1/skills/run', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{skill_id: skillId, inputs: inp}}),
    }});
    const result = await runResp.json();
    if (result.error) {{ alert('Błąd skill: ' + result.error); return; }}
    // Wyświetl wynik w chacie
    const chatEl = document.getElementById('chat-history');
    if (chatEl) {{
      const div = document.createElement('div');
      div.className = 'message assistant';
      div.innerHTML = `<strong>🔬 Skill: ${{escHtml(title)}}</strong><br><pre style="white-space:pre-wrap;font-size:.75rem">${{escHtml(JSON.stringify(result.result, null, 2))}}</pre>`
        + (result.sm_reflection ? `<div style="margin-top:.5rem;padding:.4rem;background:var(--surf2);border-radius:5px;font-size:.73rem"><strong>🌙 SM:</strong> ${{escHtml(result.sm_reflection)}}</div>` : '');
      chatEl.appendChild(div);
      chatEl.scrollTop = chatEl.scrollHeight;
    }}
  }} catch(e) {{
    alert('Błąd: ' + e.message);
  }}
}}

async function newScienceNotebook() {{
  await newNotebookModal('silo_1');
}}

async function openScienceNotebook(nbId) {{
  await openNotebookModal('silo_1', nbId);
}}

async function runSiloSM() {{
  const summary = document.querySelector('.silo-summary');
  if (summary) summary.textContent = 'SM synthesis w toku…';
  try {{
    const resp = await fetch(API + '/api/silos/silo_1/sleeping/run', {{method: 'POST'}});
    const data = await resp.json();
    if (summary) summary.textContent = data.day_synthesis
      ? data.day_synthesis.substring(0, 120) + '…'
      : 'Brak syntezy';
    // Pokaż w globalnym SM widget
    if (data.day_synthesis) renderSleepingResult(data);
  }} catch(e) {{
    if (summary) summary.textContent = 'Błąd SM: ' + e.message;
  }}
}}

async function changeSiloHashtag() {{
  const tag = prompt('Nowy hashtag/label silosu (np. #research, #fizyka):');
  if (!tag) return;
  try {{
    await fetch(API + '/api/silos/silo_1/hashtag', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{hashtag: tag}}),
    }});
    loadSiloScience();
  }} catch(e) {{
    alert('Błąd: ' + e.message);
  }}
}}

// ── Sleeping Matylda ──────────────────────────────────────────────────────────
async function loadSleepingStatus() {{
  try {{
    const [status, last] = await Promise.all([
      fetch(API + '/api/sleeping/status').then(r => r.json()),
      fetch(API + '/api/sleeping/last').then(r => r.json()),
    ]);
    const statusEl = document.getElementById('sm-status');
    if (statusEl) {{
      const ts = last.timestamp ? new Date(last.timestamp).toLocaleString('pl-PL', {{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}}) : null;
      statusEl.textContent = last.available
        ? `Ostatnia synteza: ${{ts}}`
        : 'Brak syntezy — kliknij ▶ aby uruchomić';
    }}
    if (last.available && last.result) renderSleepingResult(last.result);
  }} catch(e) {{
    const statusEl = document.getElementById('sm-status');
    if (statusEl) statusEl.textContent = 'Sleeping Matylda niedostępna';
  }}
}}

function renderSleepingResult(r) {{
  const el = document.getElementById('sm-result');
  if (!el) return;
  let html = '';

  if (r.day_synthesis) {{
    html += `<div class="sm-card"><div class="sm-card-label">Synteza</div><div class="sm-synthesis">${{escHtml(r.day_synthesis)}}</div></div>`;
  }}

  function renderList(label, items) {{
    if (!items || !items.length) return '';
    let s = `<div class="sm-card"><div class="sm-card-label">${{label}} (${{items.length}})</div>`;
    items.forEach(item => {{ s += `<div class="sm-list-item">${{escHtml(item)}}</div>`; }});
    s += '</div>';
    return s;
  }}

  html += renderList('Otwarte wątki', r.open_threads);
  html += renderList('Proponowane kroki', r.proposed_next_steps);
  html += renderList('Pytania', r.next_questions);
  html += renderList('Napięcia', r.tensions_or_conflicts);
  if (r.warnings && r.warnings.length) {{
    html += renderList('Ostrzeżenia', r.warnings);
  }}
  el.innerHTML = html;
}}

async function runSleepingMatylda() {{
  const btn = document.querySelector('.sm-run-btn');
  const statusEl = document.getElementById('sm-status');
  const resultEl = document.getElementById('sm-result');
  if (btn) btn.classList.add('running');
  if (statusEl) statusEl.textContent = 'Uruchamianie syntezy…';
  if (resultEl) resultEl.innerHTML = '';
  try {{
    const resp = await fetch(API + '/api/sleeping/run', {{method: 'POST'}});
    const data = await resp.json();
    if (data.error) {{
      if (statusEl) statusEl.textContent = 'Błąd: ' + data.error;
    }} else {{
      if (statusEl) statusEl.textContent = 'Synteza gotowa ✓';
      renderSleepingResult(data);
    }}
  }} catch(e) {{
    if (statusEl) statusEl.textContent = 'Błąd połączenia: ' + e.message;
  }} finally {{
    if (btn) btn.classList.remove('running');
  }}
}}

// ── Focus Mode ────────────────────────────────────────────────────────────────
let _focusPollInterval = null;
let _selectedFocusMode = 'timebox';
let _selectedFocusDuration = 900;

function focusSelectTimer(btn) {{
  document.querySelectorAll('.focus-timer-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  _selectedFocusMode = btn.dataset.mode;
  _selectedFocusDuration = parseInt(btn.dataset.val, 10);
  const customRow = document.getElementById('focus-custom-time-row');
  if (customRow) customRow.style.display = btn.dataset.val === 'custom' ? 'block' : 'none';
}}

function _getSelectedAreas() {{
  return ['questions','tensions','steps','no_go']
    .filter(v => {{ const el = document.getElementById('fa-' + (v === 'no_go' ? 'nogo' : v)); return el && el.checked; }});
}}

async function startFocusMode() {{
  const areas = _getSelectedAreas();
  if (!areas.length) {{ alert('Wybierz co najmniej jeden obszar.'); return; }}
  const btn = document.getElementById('focus-start-btn');
  if (btn) {{ btn.disabled = true; btn.textContent = '…'; }}
  const customPrompt = (document.getElementById('focus-custom-prompt') || {{}}).value || '';
  const autoTag = !!(document.getElementById('fa-tag-low-risk') || {{}}).checked;
  const customMin = parseInt((document.getElementById('focus-custom-minutes') || {{}}).value || '0', 10);
  const duration = (customMin > 0 && _selectedFocusMode === 'timebox') ? customMin * 60 : _selectedFocusDuration;
  try {{
    const resp = await fetch(API + '/api/sleeping-matylda/focus-start', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        focus_areas: areas,
        mode: _selectedFocusMode,
        duration_seconds: duration,
        idle_threshold: _selectedFocusDuration,
        custom_prompt: customPrompt,
        auto_tag_low_risk: autoTag,
      }})
    }});
    const data = await resp.json();
    if (data.error) {{
      if (btn) {{ btn.disabled = false; btn.textContent = '▶ START Focus Mode'; }}
      alert('Błąd: ' + data.error);
    }} else {{
      _showFocusActive(data.session || {{}});
      _startFocusPoll();
    }}
  }} catch(e) {{
    if (btn) {{ btn.disabled = false; btn.textContent = '▶ START Focus Mode'; }}
    alert('Błąd połączenia: ' + e.message);
  }}
}}

function _showFocusActive(session) {{
  document.getElementById('focus-panel-config').style.display = 'none';
  document.getElementById('focus-panel-done').style.display = 'none';
  document.getElementById('focus-panel-active').style.display = 'block';
  const areasEl = document.getElementById('focus-areas-active');
  if (areasEl && session.focus_areas) {{
    const labels = {{'questions':'❓ pytania','tensions':'⚡ napięcia','steps':'📋 kroki','no_go':'⊗ NO-GO'}};
    areasEl.textContent = (session.focus_areas || []).map(a => labels[a] || a).join(' · ');
  }}
  const idleNote = document.getElementById('focus-idle-note');
  if (idleNote) {{
    if (session.mode === 'until_idle') {{
      idleNote.style.display = 'block';
      idleNote.textContent = `Tryb: do wyczerpania (próg: ${{session.idle_threshold}} pustych cykli)`;
    }} else {{
      idleNote.style.display = 'none';
    }}
  }}
}}

function _startFocusPoll() {{
  if (_focusPollInterval) clearInterval(_focusPollInterval);
  _focusPollInterval = setInterval(_pollFocusStatus, 10000);
  _pollFocusStatus();
}}

async function _pollFocusStatus() {{
  try {{
    const data = await fetch(API + '/api/sleeping-matylda/focus-status').then(r => r.json());
    if (!data.active) {{
      clearInterval(_focusPollInterval);
      _focusPollInterval = null;
      if (data.status === 'completed' || data.status === 'cancelled') {{
        _showFocusDone(data);
      }}
      return;
    }}
    // Update countdown
    const cdEl = document.getElementById('focus-countdown');
    if (cdEl) {{
      if (data.mode === 'timebox') {{
        const rem = Math.max(0, data.remaining_seconds || 0);
        const m = Math.floor(rem / 60), s = rem % 60;
        cdEl.textContent = `${{m}}:${{String(s).padStart(2,'0')}}`;
      }} else {{
        const empty = data.consecutive_empty_cycles || 0;
        const thresh = data.idle_threshold || 3;
        cdEl.textContent = `${{empty}}/${{thresh}} pustych`;
      }}
    }}
    // Update badge
    const badge = document.getElementById('focus-findings-badge');
    if (badge) badge.textContent = data.findings_generated || 0;
    // Update status label
    const lbl = document.getElementById('focus-status-label');
    if (lbl) {{
      lbl.textContent = data.status === 'paused' ? '⏸ zapauzowana' : `cykl ${{data.cycles_completed || 0}}`;
      lbl.style.color = data.status === 'paused' ? 'var(--accent)' : 'var(--text2)';
    }}
    // Update pause btn
    const pauseBtn = document.getElementById('focus-pause-btn');
    if (pauseBtn) pauseBtn.textContent = data.status === 'paused' ? '▶ Wznów' : '⏸ Pauzuj';
  }} catch(_) {{}}
}}

async function toggleFocusPause() {{
  try {{
    const status = await fetch(API + '/api/sleeping-matylda/focus-status').then(r => r.json());
    const endpoint = status.status === 'paused'
      ? '/api/sleeping-matylda/focus-resume'
      : '/api/sleeping-matylda/focus-pause';
    await fetch(API + endpoint, {{method: 'POST'}});
    _pollFocusStatus();
  }} catch(_) {{}}
}}

async function stopFocusMode() {{
  if (!confirm('Zatrzymać sesję Focus Mode?')) return;
  try {{
    const data = await fetch(API + '/api/sleeping-matylda/focus-stop', {{method: 'POST'}}).then(r => r.json());
    clearInterval(_focusPollInterval);
    _focusPollInterval = null;
    _showFocusDone(data);
  }} catch(_) {{}}
}}

function _showFocusDone(data) {{
  document.getElementById('focus-panel-active').style.display = 'none';
  document.getElementById('focus-panel-config').style.display = 'none';
  document.getElementById('focus-panel-done').style.display = 'block';
  const sumEl = document.getElementById('focus-done-summary');
  if (sumEl) {{
    sumEl.textContent = (
      `${{data.cycles_completed || 0}} cykli · `
      + `${{data.findings_generated || 0}} findings · `
      + `status: ${{data.status || '—'}}`
    );
  }}
  // Refresh SM findings list to show new focus findings
  if (typeof loadSleepingStatus === 'function') loadSleepingStatus();
}}

function resetFocusPanel() {{
  document.getElementById('focus-panel-done').style.display = 'none';
  document.getElementById('focus-panel-active').style.display = 'none';
  document.getElementById('focus-panel-config').style.display = 'block';
  const startBtn = document.getElementById('focus-start-btn');
  if (startBtn) {{ startBtn.disabled = false; startBtn.textContent = '▶ START Focus Mode'; }}
}}

async function initFocusPanel() {{
  const status = await fetch(API + '/api/sleeping-matylda/focus-status').then(r => r.json()).catch(() => ({{active: false}}));
  if (status.active) {{
    _showFocusActive(status);
    _startFocusPoll();
  }}
}}

// ── Sleeping Matylda tab (page-sleeping) ─────────────────────────────────────

let _selectedFocusMode2 = 'timebox';
let _selectedFocusDuration2 = 900;
let _focusPollInterval2 = null;

function focusSelectTimer2(btn) {{
  document.querySelectorAll('#focus-timer-btns-2 .focus-timer-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  _selectedFocusMode2 = btn.dataset.mode;
  _selectedFocusDuration2 = parseInt(btn.dataset.val, 10);
  const customRow = document.getElementById('focus-custom-time-row-2');
  if (customRow) customRow.style.display = btn.dataset.val === 'custom' ? 'block' : 'none';
}}

function _getSelectedAreas2() {{
  return ['questions','tensions','steps','no_go']
    .filter(v => {{ const el = document.getElementById('fa2-' + (v === 'no_go' ? 'nogo' : v)); return el && el.checked; }});
}}

async function startFocusMode2() {{
  const areas = _getSelectedAreas2();
  if (!areas.length) {{ alert('Wybierz co najmniej jeden obszar.'); return; }}
  const btn = document.getElementById('focus-start-btn-2');
  if (btn) {{ btn.disabled = true; btn.textContent = '…'; }}
  const customPrompt = (document.getElementById('focus-custom-prompt-2') || {{}}).value || '';
  const autoTag = !!(document.getElementById('fa2-tag-low-risk') || {{}}).checked;
  const customMin = parseInt((document.getElementById('focus-custom-minutes-2') || {{}}).value || '0', 10);
  const duration = (customMin > 0 && _selectedFocusMode2 === 'timebox') ? customMin * 60 : _selectedFocusDuration2;
  try {{
    const resp = await fetch(API + '/api/sleeping-matylda/focus-start', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        focus_areas: areas,
        mode: _selectedFocusMode2,
        duration_seconds: duration,
        idle_threshold: _selectedFocusDuration2,
        custom_prompt: customPrompt,
        auto_tag_low_risk: autoTag,
      }})
    }});
    const data = await resp.json();
    if (data.error) {{
      if (btn) {{ btn.disabled = false; btn.textContent = '▶ START Focus Mode'; }}
      alert('Błąd: ' + data.error);
    }} else {{
      _showFocusActive2(data.session || {{}});
      _startFocusPoll2();
    }}
  }} catch(e) {{
    if (btn) {{ btn.disabled = false; btn.textContent = '▶ START Focus Mode'; }}
    alert('Błąd połączenia: ' + e.message);
  }}
}}

function _showFocusActive2(session) {{
  document.getElementById('focus-panel-config-2').style.display = 'none';
  document.getElementById('focus-panel-done-2').style.display = 'none';
  document.getElementById('focus-panel-active-2').style.display = 'block';
  const areasEl = document.getElementById('focus-areas-active-2');
  if (areasEl && session.focus_areas) {{
    const labels = {{'questions':'❓ pytania','tensions':'⚡ napięcia','steps':'📋 kroki','no_go':'⊗ NO-GO'}};
    areasEl.textContent = (session.focus_areas || []).map(a => labels[a] || a).join(' · ');
  }}
  const idleNote = document.getElementById('focus-idle-note-2');
  if (idleNote) {{
    if (session.mode === 'until_idle') {{
      idleNote.style.display = 'block';
      idleNote.textContent = `Tryb: do wyczerpania (próg: ${{session.idle_threshold}} pustych cykli)`;
    }} else {{
      idleNote.style.display = 'none';
    }}
  }}
}}

function _startFocusPoll2() {{
  if (_focusPollInterval2) clearInterval(_focusPollInterval2);
  _focusPollInterval2 = setInterval(_pollFocusStatus2, 10000);
  _pollFocusStatus2();
}}

async function _pollFocusStatus2() {{
  try {{
    const data = await fetch(API + '/api/sleeping-matylda/focus-status').then(r => r.json());
    if (!data.active) {{
      clearInterval(_focusPollInterval2);
      _focusPollInterval2 = null;
      if (data.status === 'completed' || data.status === 'cancelled') {{
        _showFocusDone2(data);
      }}
      return;
    }}
    const cdEl = document.getElementById('focus-countdown-2');
    if (cdEl) {{
      if (data.mode === 'timebox') {{
        const rem = Math.max(0, data.remaining_seconds || 0);
        const m = Math.floor(rem / 60), s = rem % 60;
        cdEl.textContent = `${{m}}:${{String(s).padStart(2,'0')}}`;
      }} else {{
        cdEl.textContent = `${{data.consecutive_empty_cycles || 0}}/${{data.idle_threshold || 3}} pustych`;
      }}
    }}
    const badge = document.getElementById('focus-findings-badge-2');
    if (badge) badge.textContent = data.findings_generated || 0;
    const lbl = document.getElementById('focus-status-label-2');
    if (lbl) {{
      lbl.textContent = data.status === 'paused' ? '⏸ zapauzowana' : `cykl ${{data.cycles_completed || 0}}`;
      lbl.style.color = data.status === 'paused' ? 'var(--accent)' : 'var(--text2)';
    }}
    const pauseBtn = document.getElementById('focus-pause-btn-2');
    if (pauseBtn) pauseBtn.textContent = data.status === 'paused' ? '▶ Wznów' : '⏸ Pauzuj';
  }} catch(_) {{}}
}}

async function toggleFocusPause2() {{
  try {{
    const status = await fetch(API + '/api/sleeping-matylda/focus-status').then(r => r.json());
    const endpoint = status.status === 'paused'
      ? '/api/sleeping-matylda/focus-resume'
      : '/api/sleeping-matylda/focus-pause';
    await fetch(API + endpoint, {{method: 'POST'}});
    _pollFocusStatus2();
  }} catch(_) {{}}
}}

async function stopFocusMode2() {{
  if (!confirm('Zatrzymać sesję Focus Mode?')) return;
  try {{
    const data = await fetch(API + '/api/sleeping-matylda/focus-stop', {{method: 'POST'}}).then(r => r.json());
    clearInterval(_focusPollInterval2);
    _focusPollInterval2 = null;
    _showFocusDone2(data);
  }} catch(_) {{}}
}}

function _showFocusDone2(data) {{
  document.getElementById('focus-panel-active-2').style.display = 'none';
  document.getElementById('focus-panel-config-2').style.display = 'none';
  document.getElementById('focus-panel-done-2').style.display = 'block';
  const sumEl = document.getElementById('focus-done-summary-2');
  if (sumEl) {{
    sumEl.textContent = `${{data.cycles_completed || 0}} cykli · ${{data.findings_generated || 0}} findings · status: ${{data.status || '—'}}`;
  }}
  loadSleepingStatus();
}}

function resetFocusPanel2() {{
  document.getElementById('focus-panel-done-2').style.display = 'none';
  document.getElementById('focus-panel-active-2').style.display = 'none';
  document.getElementById('focus-panel-config-2').style.display = 'block';
  const startBtn = document.getElementById('focus-start-btn-2');
  if (startBtn) {{ startBtn.disabled = false; startBtn.textContent = '▶ START Focus Mode'; }}
}}

async function initFocusPanel2() {{
  const status = await fetch(API + '/api/sleeping-matylda/focus-status').then(r => r.json()).catch(() => ({{active: false}}));
  if (status.active) {{
    _showFocusActive2(status);
    _startFocusPoll2();
  }}
}}

async function loadSleepingTab() {{
  // Load SM status
  try {{
    const status = await fetch(API + '/api/sleeping/status').then(r => r.json());
    const focusStatus = await fetch(API + '/api/sleeping-matylda/focus-status').then(r => r.json()).catch(() => ({{}}));
    const statusEl = document.getElementById('sm-status-2');
    if (statusEl) {{
      let txt = status.running ? '⟳ cykl w toku' : '— bezczynna';
      if (focusStatus.cycles_completed) {{
        txt += ` · ostatnia sesja: ${{focusStatus.cycles_completed}} cykli, ${{focusStatus.findings_generated}} findings`;
      }}
      statusEl.textContent = txt;
    }}
  }} catch(_) {{}}

  // Init focus panel state
  initFocusPanel2();

  // Load SM findings and health in parallel
  await Promise.all([
    loadSmFindings(),
    loadResearchTraces().catch(() => {{}}),
    loadSystemHealth().catch(() => {{}}),
  ]);

  // Mirror traces & health into sleeping tab containers
  const pairs = [['traces-list','sm-traces-list'],['sys-health-content','sm-health-content']];
  pairs.forEach(([src,dst]) => {{
    const s = document.getElementById(src), d = document.getElementById(dst);
    if (s && d) d.innerHTML = s.innerHTML;
  }});
}}

async function loadSmFindings() {{
  const el = document.getElementById('sm-approvals-list');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text3);font-size:.75rem">ładowanie…</div>';
  try {{
    // Auto-triage first (scores + archives Q4)
    const triage = await fetch(API + '/api/sleeping-matylda/triage', {{method:'POST'}}).then(r=>r.json()).catch(()=>({{}}));
    const autoArchived = triage.auto_archived || 0;

    const data = await fetch(API + '/api/sleeping-matylda/findings?state=pending').then(r => r.json());
    const findings = data.findings || [];

    if (!findings.length) {{
      const archMsg = autoArchived > 0
        ? `<div style="color:var(--text3);font-size:.72rem;margin-bottom:6px">🗄 ${{autoArchived}} auto-zarchiwizowanych (Q4 — nieważne i niepilne)</div>` : '';
      el.innerHTML = archMsg + '<div style="color:var(--text3);font-size:.75rem">Brak oczekujących findings.</div>';
      return;
    }}

    const typeLabels = {{
      question_focus:'❓ pytanie', stale_question:'❓ stare pyt.',
      tension_analysis:'⚡ napięcie', step_proposal:'📋 krok',
      nogo_recheck:'⊗ NO-GO', graph_orphan:'🔗 orphan',
      reflection_candidate:'💭 refleksja',
    }};
    const areaColors = {{questions:'#5c80c4',tensions:'#c47a5c',steps:'#5ca472',no_go:'#c45c5c'}};
    const quadrantMeta = {{
      1: {{label:'Q1 — Ważne & Pilne', color:'#c45c5c', badge:'🔴 Q1'}},
      2: {{label:'Q2 — Ważne, niepilne', color:'#c49a5c', badge:'🟠 Q2'}},
      3: {{label:'Q3 — Pilne, mniej ważne', color:'#c4c05c', badge:'🟡 Q3'}},
    }};

    // Group by quadrant; unscored fall into Q2 fallback
    const byQ = {{1:[], 2:[], 3:[]}};
    findings.forEach(f => {{
      const q = f.eisenhower_quadrant || 2;
      if (byQ[q]) byQ[q].push(f);
    }});
    // Sort each group by confidence desc
    [1,2,3].forEach(q => byQ[q].sort((a,b) => (b.confidence||0)-(a.confidence||0)));

    function renderCard(f) {{
      const lbl = typeLabels[f.type] || '📌';
      const qm  = quadrantMeta[f.eisenhower_quadrant] || quadrantMeta[2];
      const areaColor = areaColors[f.focus_area] || 'var(--text3)';
      const provenance = [
        f.focus_area ? `<span style="color:${{areaColor}};font-size:.65rem">[${{f.focus_area}}]</span>` : '',
        f.source_thread ? `<span style="font-size:.65rem;color:var(--text3)">${{escHtml(f.source_thread)}}</span>` : '',
      ].filter(Boolean).join(' ');
      const repeatBadge = (f.repeat_count > 1)
        ? `<span style="font-size:.65rem;font-weight:700;color:#9b7edb;background:rgba(155,126,219,.12);border-radius:5px;padding:1px 5px" title="Pytanie pojawiło się ${{f.repeat_count}} razy">×${{f.repeat_count}}</span>`
        : '';
      const impUrgLine = (f.eisenhower_importance != null)
        ? `<span style="font-size:.63rem;color:var(--text3);margin-left:4px">ważność ${{f.eisenhower_importance?.toFixed(2)}} · pilność ${{f.eisenhower_urgency?.toFixed(2)}}</span>`
        : '';
      return `<div class="sm-finding-card" id="smf-${{f.finding_id}}">
        <div class="sm-finding-header">
          <span class="sm-finding-type">${{lbl}}</span>
          <span style="font-size:.65rem;color:${{qm.color}};font-weight:600">${{qm.badge}}</span>
          ${{repeatBadge}}
          ${{provenance}}
          <span style="margin-left:auto;font-size:.68rem;color:var(--text3)">${{(f.confidence||0).toFixed(2)}}</span>
        </div>
        <div class="sm-finding-title">${{escHtml(f.title||'')}}</div>
        <div class="sm-finding-desc">${{escHtml((f.description||'').slice(0,140))}}${{impUrgLine}}</div>
        <div class="sm-finding-actions">
          <button class="sm-btn-approve" onclick="smApprove('${{f.finding_id}}')">✓ Zatwierdź</button>
          <button class="sm-btn-dismiss" onclick="smDismiss('${{f.finding_id}}')">✕ Odrzuć</button>
        </div>
      </div>`;
    }}

    let html = '';
    const autoDeduped = triage.deduped || 0;
    if (autoArchived > 0 || autoDeduped > 0) {{
      const parts = [];
      if (autoDeduped > 0) parts.push(`${{autoDeduped}} duplikatów scalonych`);
      if (autoArchived > 0) parts.push(`${{autoArchived}} nieistotnych (Q4)`);
      html += `<div style="color:var(--text3);font-size:.72rem;margin-bottom:8px;padding:5px 8px;background:var(--surf3);border-radius:7px">🗄 Zarchiwizowano: ${{parts.join(', ')}}</div>`;
    }}
    [1,2,3].forEach(q => {{
      if (!byQ[q].length) return;
      const qm = quadrantMeta[q];
      html += `<div style="margin-bottom:4px;margin-top:${{q===1?'0':'10px'}}">
        <div style="font-size:.68rem;font-weight:700;color:${{qm.color}};margin-bottom:5px;letter-spacing:.03em;text-transform:uppercase">${{qm.label}} (${{byQ[q].length}})</div>
        ${{byQ[q].map(renderCard).join('')}}
      </div>`;
    }});

    el.innerHTML = html || '<div style="color:var(--text3);font-size:.75rem">Brak oczekujących findings.</div>';
  }} catch(e) {{
    el.innerHTML = `<div style="color:var(--red);font-size:.75rem">Błąd: ${{escHtml(e.message)}}</div>`;
  }}
}}

async function smApprove(id) {{
  const card = document.getElementById('smf-' + id);
  if (card) card.style.opacity = '0.5';
  try {{
    const r = await fetch(API + `/api/sleeping-matylda/findings/${{id}}/approve`, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:'{{}}'}}).then(r=>r.json());
    if (r.error) {{ alert('Błąd: ' + r.error); if(card) card.style.opacity='1'; return; }}
    if (card) card.remove();
  }} catch(e) {{ alert('Błąd: ' + e.message); if(card) card.style.opacity='1'; }}
}}

async function smDismiss(id) {{
  const card = document.getElementById('smf-' + id);
  if (card) card.style.opacity = '0.5';
  try {{
    const r = await fetch(API + `/api/sleeping-matylda/findings/${{id}}/dismiss`, {{method:'POST',headers:{{'Content-Type':'application/json'}},body:'{{}}'}}).then(r=>r.json());
    if (r.error) {{ alert('Błąd: ' + r.error); if(card) card.style.opacity='1'; return; }}
    if (card) card.remove();
  }} catch(e) {{ alert('Błąd: ' + e.message); if(card) card.style.opacity='1'; }}
}}

// ── v0.9 — System Health (DARKROOM panel) ─────────────────────────────────────

async function loadSystemHealth() {{
  const el = document.getElementById('sys-health-content');
  if (!el) return;
  try {{
    const data = await fetch(API + '/api/health/system').then(r => r.json());
    renderSystemHealth(data, el);
  }} catch(e) {{
    if (el) el.innerHTML = '<div style="color:var(--text3);font-size:.72rem">Błąd: ' + escHtml(e.message) + '</div>';
  }}
}}

function renderSystemHealth(d, el) {{
  function cls(val, warn, bad) {{
    if (val >= bad)  return 'bad';
    if (val >= warn) return 'warn';
    return 'ok';
  }}
  const atCls  = cls(d.active_threads, 5, 8);
  // Red/amber = actionable problem, not "a number got big". Accumulating
  // memory (insights/artifacts) is the system working — keep it neutral.
  const rows = [
    ['Aktywne wątki', d.active_threads + ' / ' + d.active_thread_limit, atCls],
    ['Zamrożone wątki', d.frozen_threads, 'ok'],
    ['Insighty (pamięć)', d.insight_count, cls(d.insight_count, 400, 800)],
    ['Kandydaci', d.candidate_count, cls(d.candidate_count, 50, 120)],
    ['Artefakty', d.artifact_count, 'ok'],
  ].map(([label, val, c]) =>
    '<div class="sys-health-row">' +
      '<span class="sys-health-label">' + label + '</span>' +
      '<span class="sys-health-val ' + c + '">' + val + '</span>' +
    '</div>'
  ).join('');

  const score = d.complexity_score || 0;
  const scoreMax = 40;
  const scorePct = Math.min(100, Math.round(score / scoreMax * 100));
  const scoreColor = scorePct < 60 ? 'var(--green)' : scorePct < 85 ? 'var(--yellow)' : 'var(--red)';
  const scoreHtml = '<div class="sys-health-score">' +
    '<span class="sys-health-score-label">Złożoność</span>' +
    '<div class="sys-health-score-bar">' +
      '<div class="sys-health-score-fill" style="width:' + scorePct + '%;background:' + scoreColor + '"></div>' +
    '</div>' +
    '<span style="font-size:.72rem;font-family:monospace;color:' + scoreColor + '">' + score + '</span>' +
  '</div>';

  el.innerHTML = rows + scoreHtml;
}}

// ── v0.9 — Morning Briefing ───────────────────────────────────────────────────

async function checkMorningBriefing(force) {{
  try {{
    const url = API + '/api/briefing' + (force ? '?force=true' : '');
    const data = await fetch(url).then(r => r.json()).catch(() => null);
    if (!data || !data.show) return;
    renderBriefingCard(data);
  }} catch (_) {{}}
}}

async function markSession() {{
  try {{
    await fetch(API + '/api/briefing/mark-session', {{method: 'POST'}});
  }} catch (_) {{}}
}}

function renderBriefingCard(data) {{
  const history = document.getElementById('chat-history');
  if (!history) return;

  // Remove existing briefing card if any
  const existing = history.querySelector('.briefing-card');
  if (existing) existing.remove();

  const gapH = data.gap_hours || 0;
  const gapLabel = gapH < 24
    ? Math.round(gapH) + ' godz. temu'
    : Math.round(gapH / 24) + ' dni temu';

  // Build synthesis section
  let synthHtml = '';
  if (data.synthesis && data.synthesis.result) {{
    const r = data.synthesis.result;
    const parts = [];
    if (r.day_synthesis) parts.push('<p>' + escHtml(r.day_synthesis) + '</p>');
    if (r.open_threads && r.open_threads.length) {{
      parts.push('<p><strong style="color:#7eb8f7">Otwarte wątki:</strong> ' +
        r.open_threads.map(t => escHtml(t)).join(' · ') + '</p>');
    }}
    if (r.next_questions && r.next_questions.length) {{
      parts.push('<p><strong style="color:#7eb8f7">Pytania:</strong> ' +
        r.next_questions.slice(0, 2).map(q => escHtml(q)).join(' · ') + '</p>');
    }}
    if (parts.length) {{
      synthHtml = '<div class="briefing-section">' +
        '<div class="briefing-section-label">Synteza Sleeping Matylda</div>' +
        '<div class="briefing-synthesis">' + parts.join('') + '</div>' +
        '</div>';
    }}
  }}

  // Build connections section
  let connHtml = '';
  if (data.connections && data.connections.length) {{
    const items = data.connections.map(c =>
      '<div class="briefing-connection">' +
        '<span class="briefing-connection-icon">🔗</span>' +
        '<div class="briefing-connection-threads">' +
          '<strong>' + escHtml(c.thread_a.title) + '</strong>' +
          ' ↔ <strong>' + escHtml(c.thread_b.title) + '</strong>' +
          '<div class="briefing-connection-kws">' +
            escHtml(c.shared_keywords.join(', ')) +
          '</div>' +
        '</div>' +
      '</div>'
    ).join('');
    connHtml = '<div class="briefing-section">' +
      '<div class="briefing-section-label">Powiązania między wątkami</div>' +
      items +
      '</div>';
  }}

  const card = document.createElement('div');
  card.className = 'briefing-card';
  card.innerHTML =
    '<div class="briefing-header">' +
      '<span class="briefing-icon">🌅</span>' +
      '<span class="briefing-title">Poranne podsumowanie</span>' +
      '<span class="briefing-gap">' + gapLabel + '</span>' +
    '</div>' +
    synthHtml +
    connHtml +
    '<div style="display:flex;justify-content:flex-end;margin-top:6px">' +
      '<button class="briefing-dismiss" onclick="dismissBriefing()">Zamknij</button>' +
    '</div>';

  // Insert before the first chat-empty div or prepend
  const empty = history.querySelector('.chat-empty');
  if (empty) {{
    history.insertBefore(card, empty);
  }} else {{
    history.insertBefore(card, history.firstChild);
  }}
}}

function dismissBriefing() {{
  const card = document.querySelector('.briefing-card');
  if (card) card.remove();
}}

// ── Init ──────────────────────────────────────────────────────────────────────
async function loadSessionPanel() {{
  const el = document.getElementById('session-panel-content');
  if (!el) return;
  try {{
    const r = await fetch(API + '/api/perception/context?project_id=lite&event_limit=20').then(r => r.json()).catch(() => null);
    if (!r || !r.available) {{
      el.innerHTML = '<div style="color:var(--text3);font-size:.72rem">Brak danych sesji — uruchom kilka zadań.</div>';
      return;
    }}
    const ctx = r.context;
    const conf = Math.round((ctx.confidence || 0) * 100);
    const confW = Math.max(4, conf);
    el.innerHTML = `
      <div class="session-panel">
        <div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.2rem">
          <span style="font-size:.65rem;color:var(--text3)">Projekt:</span>
          <span style="font-size:.7rem;font-weight:600;color:var(--text1)">${{escHtml(ctx.project_id || '—')}}</span>
          <span style="font-size:.65rem;color:var(--text3);margin-left:auto">conf ${{conf}}%</span>
        </div>
        <div class="session-confidence" style="width:${{confW}}%"></div>
        ${{ctx.inferred_goal ? `<div class="session-goal">${{escHtml(ctx.inferred_goal.slice(0,100))}}</div>` : ''}}
        ${{ctx.summary ? `<div class="session-events">${{escHtml(ctx.summary.slice(0,160))}}</div>` : ''}}
      </div>`;
  }} catch(e) {{
    el.innerHTML = `<div style="color:var(--text3);font-size:.7rem">Błąd sesji: ${{e.message}}</div>`;
  }}
}}

async function loadResearchTraces() {{
  const el = document.getElementById('traces-list');
  if (!el) return;
  try {{
    const pid = _activeProjectId ? `&project_id=${{encodeURIComponent(_activeProjectId)}}` : '';
    const r = await fetch(API + `/api/research/pipeline/list?limit=20${{pid}}`).then(r => r.json()).catch(() => null);
    if (!r || !r.results || !r.results.length) {{
      el.innerHTML = '<div class="trace-empty">Brak wyników pipeline.</div>';
      return;
    }}
    // Collapse identical traces (same title+summary) into one row with ×N badge
    const seen = new Map();
    for (const t of r.results) {{
      const key = (t.title || '') + '|' + (t.summary || '');
      if (seen.has(key)) seen.get(key).count++;
      else seen.set(key, {{ t, count: 1 }});
    }}
    el.innerHTML = Array.from(seen.values()).slice(0, 8).map(({{t, count}}) => `
      <div class="trace-item">
        <div class="trace-title">${{escHtml((t.title || '—').slice(0,50))}}${{count > 1 ? ` <span style="color:var(--text3);font-weight:600">×${{count}}</span>` : ''}}</div>
        <div class="trace-summary">${{escHtml((t.summary || '').slice(0,80))}}</div>
        ${{t.recommended_next_step ? `<div class="trace-next">→ ${{escHtml(t.recommended_next_step.slice(0,60))}}</div>` : ''}}
      </div>`).join('');
  }} catch(e) {{
    el.innerHTML = `<div class="trace-empty">Błąd: ${{e.message}}</div>`;
  }}
}}

async function loadStaleTraces() {{
  const el = document.getElementById('stale-traces-list');
  if (!el) return;
  try {{
    const r = await fetch(API + '/api/research/traces/stale?days=7').then(r => r.json()).catch(() => null);
    if (!r) {{ el.innerHTML = '<div class="trace-empty">Błąd ładowania.</div>'; return; }}
    if (!r.stale || !r.stale.length) {{
      el.innerHTML = `<div class="trace-empty" style="color:var(--green)">Brak przeterminowanych trace’ów ✓</div>`;
      return;
    }}
    el.innerHTML = r.stale.map(t => `
      <div class="trace-item" style="border-left:2px solid var(--red);padding-left:6px">
        <div class="trace-title">${{escHtml((t.title||'—').slice(0,50))}} <span style="color:var(--red);font-size:.68rem">(${{t.days_open}}d)</span></div>
        <div class="trace-summary" style="color:var(--text3)">${{escHtml((t.summary||'').slice(0,70))}}</div>
        <button class="btn-validate" style="margin-top:.25rem" onclick="promoteTrace('${{escHtml(t.id||'')}}','published',this)">Opublikuj</button>
      </div>`).join('');
  }} catch(e) {{
    el.innerHTML = `<div class="trace-empty">Błąd: ${{e.message}}</div>`;
  }}
}}

async function promoteTrace(traceId, newStatus, btn) {{
  if (!traceId) return;
  if (btn) {{ btn.disabled = true; btn.textContent = '…'; }}
  try {{
    const resp = await fetch(API + '/api/research/traces/promote', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{trace_id: traceId, new_status: newStatus}})
    }});
    const data = await resp.json();
    if (btn) {{ btn.disabled = false; btn.textContent = 'Opublikuj'; }}
    if (data.error) {{
      const card = btn ? btn.closest('.trace-item') : null;
      if (card) {{
        const e = document.createElement('div');
        e.style.cssText = 'color:var(--red);font-size:.7rem;margin-top:.2rem';
        e.textContent = '⚠ ' + data.error;
        card.appendChild(e);
        setTimeout(() => e.remove(), 5000);
      }}
    }} else {{
      loadStaleTraces();
    }}
  }} catch(e) {{
    if (btn) {{ btn.disabled = false; btn.textContent = 'Opublikuj'; }}
  }}
}}

async function loadUcb1Stats() {{
  const el = document.getElementById('ucb1-stats');
  if (!el) return;
  try {{
    const r = await fetch(API + '/api/models/performance').then(r => r.json()).catch(() => null);
    if (!r || !r.summary || !Object.keys(r.summary).length) {{
      el.innerHTML = '<div class="ucb1-empty">Brak danych — uruchom zadania przez Secretary.</div>';
      return;
    }}
    // Aggregate across task types
    const totals = {{}};
    for (const [tt, models] of Object.entries(r.summary)) {{
      for (const [m, s] of Object.entries(models)) {{
        if (!totals[m]) totals[m] = {{calls:0, successes_sum:0}};
        totals[m].calls += s.calls || 0;
        totals[m].successes_sum += (s.success_rate || 0) * (s.calls || 0);
      }}
    }}
    const rows = ['haiku','sonnet','opus'].map(m => {{
      const d = totals[m] || {{calls:0, successes_sum:0}};
      const rate = d.calls > 0 ? d.successes_sum / d.calls : 0;
      const pct = Math.round(rate * 100);
      return `<div class="ucb1-row">
        <span class="ucb1-model">${{m}}</span>
        <div class="ucb1-bar"><div class="ucb1-bar-fill" style="width:${{pct}}%"></div></div>
        <span class="ucb1-rate">${{pct}}% (${{d.calls}})</span>
      </div>`;
    }}).join('');
    el.innerHTML = rows;
  }} catch(e) {{
    el.innerHTML = `<div class="ucb1-empty">Błąd: ${{e.message}}</div>`;
  }}
}}

async function loadAllSilos() {{
  try {{
    const silosResp = await fetch(API + '/api/silos').then(r => r.json()).catch(() => ({{silos:[]}}));
    const container = document.getElementById('silos-widgets-container');
    if (!container) return;
    const enabled = (silosResp.silos || []).filter(s => s.enabled);
    if (!enabled.length) {{
      container.innerHTML = '<div style="color:var(--text3);font-size:.72rem">Brak aktywnych silosów.</div>';
      return;
    }}
    const widgets = await Promise.all(enabled.map(async s => {{
      const [infoR, skillsR, nbR] = await Promise.all([
        fetch(API + '/api/silos/' + s.id + '/info').then(r=>r.json()).catch(()=>null),
        fetch(API + '/api/silos/' + s.id + '/skills').then(r=>r.json()).catch(()=>({{skills:[]}})),
        fetch(API + '/api/silos/' + s.id + '/notebooks').then(r=>r.json()).catch(()=>({{notebooks:[]}})),
      ]);
      if (!infoR) return '';
      const stype = infoR.type || 'open';
      const bc = stype === 'open' ? '#2a9d8f' : '#e76f51';
      const badge = stype === 'open' ? 'OPEN' : 'CLOSED';
      const iconByHashtag = {{'#science':'🔬','#legal':'⚖️','#code':'💻','#graphics':'🎨'}};
      const icon = iconByHashtag[infoR.hashtag] || (stype === 'open' ? '🔬' : '⚖️');
      const skills = skillsR.skills || [];
      const nbs = nbR.notebooks || [];
      const skillsHtml = skills.length
        ? skills.slice(0,5).map(sk => `<div class="silo-skill-item"><span class="silo-skill-name">${{escHtml(sk.name)}}</span><button class="silo-skill-tag" onclick="runSiloSkillGeneric('${{s.id}}','${{sk.id}}')">▶</button></div>`).join('')
        : '<div style="font-size:.7rem;color:var(--text3)">Brak skills</div>';
      const nbHtml = nbs.length
        ? nbs.slice(-3).map(n => `<div class="silo-nb-item" onclick="openNotebookModal('${{escHtml(s.id)}}','${{escHtml(n.id)}}')">${{escHtml(n.title)}}</div>`).join('')
        : '<div style="font-size:.7rem;color:var(--text3)">Brak notebooków</div>';
      const policyRow = [
        infoR.llm_policy?.anonymize ? 'Anon ✓' : 'Anon ✗',
        'DARKROOM ✓',
        infoR.llm_policy?.sleeping_matylda ? 'SM ✓' : 'SM ✗',
      ].join(' &nbsp;·&nbsp; ');
      return `<div class="silo-widget">
        <div class="silo-widget-header">
          <span class="silo-widget-name">${{icon}} ${{escHtml(infoR.name)}}</span>
          <span class="silo-type-badge" style="background:${{bc}}22;color:${{bc}}">${{badge}}</span>
          <span class="silo-hashtag">${{escHtml(infoR.hashtag || '')}}</span>
        </div>
        <div class="silo-policy-row">${{policyRow}}</div>
        <div style="font-size:.68rem;font-weight:700;color:var(--text3);text-transform:uppercase;margin:.3rem 0 .2rem">Skills (${{skills.length}})</div>
        <div class="silo-skills-list">${{skillsHtml}}</div>
        <div style="font-size:.68rem;font-weight:700;color:var(--text3);text-transform:uppercase;margin:.4rem 0 .2rem">Notebooki (${{nbs.length}}) <button class="nb-btn" style="font-size:.6rem;padding:.1rem .35rem;margin-left:.3rem" onclick="newNotebookModal('${{escHtml(s.id)}}')">+ Nowy</button></div>
        <div>${{nbHtml}}</div>
      </div>`;
    }}));
    container.innerHTML = widgets.join('');
  }} catch(e) {{
    const c = document.getElementById('silos-widgets-container');
    if (c) c.innerHTML = `<div style="color:var(--text3);font-size:.72rem">Błąd: ${{e.message}}</div>`;
  }}
}}

async function runSiloSkillGeneric(siloId, skillId) {{
  try {{
    const resp = await fetch(API + '/api/silos/' + siloId + '/skills/' + skillId);
    const skill = await resp.json();
    const title = skill.name || skillId;
    const userInputStr = prompt(`Skill: ${{title}}\n\nDane wejściowe (JSON lub tekst):`);
    if (!userInputStr) return;
    let inp;
    try {{ inp = JSON.parse(userInputStr); }} catch {{ inp = {{text: userInputStr}}; }}
    const runResp = await fetch(API + '/api/silos/' + siloId + '/skills/run', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{skill_id: skillId, inputs: inp}}),
    }});
    const result = await runResp.json();
    if (result.error) {{ alert('Błąd skill: ' + result.error); return; }}
    const chatEl = document.getElementById('chat-history');
    if (chatEl) {{
      const div = document.createElement('div');
      div.className = 'message assistant';
      const icon = siloId === 'silo_2' ? '⚖️' : '🔬';
      div.innerHTML = `<strong>${{icon}} Skill: ${{escHtml(title)}}</strong>`
        + (result.anonymization ? `<div style="font-size:.68rem;color:var(--text3);margin:.2rem 0">🔏 ${{escHtml(result.anonymization.summary)}}</div>` : '')
        + `<pre style="white-space:pre-wrap;font-size:.75rem">${{escHtml(JSON.stringify(result.result, null, 2))}}</pre>`
        + (result.sm_reflection ? `<div style="margin-top:.5rem;padding:.4rem;background:var(--surf2);border-radius:5px;font-size:.73rem"><strong>🌙 SM:</strong> ${{escHtml(result.sm_reflection)}}</div>` : '');
      chatEl.appendChild(div);
      chatEl.scrollTop = chatEl.scrollHeight;
    }}
  }} catch(e) {{
    alert('Błąd: ' + e.message);
  }}
}}

document.addEventListener('DOMContentLoaded', () => {{
  loadProjectPanel();
  checkServer();
  loadDarkroom();
  loadLibrary();
  loadDocs();
  loadMemory();
  loadActiveProject();
  loadLatestReport();
  loadSleepingStatus();
  loadAllSilos();
  loadSessionPanel();
  loadResearchTraces();
  loadStaleTraces();
  loadUcb1Stats();
  initFocusPanel();
  setupDragDrop();
  setupChatDragDrop();
  // v0.9: morning briefing + session tracking + system health
  markSession();
  // Restore toolbar preference (default: collapsed)
  try {{
    const tbOpen = localStorage.getItem('matylda-toolbar-open');
    const tb = document.getElementById('research-toolbar');
    const arrow = document.getElementById('research-toolbar-arrow');
    if (tb && tbOpen === '1') {{
      tb.classList.remove('hidden');
      if (arrow) arrow.classList.add('open');
    }}
  }} catch(e) {{}}
  setTimeout(() => checkMorningBriefing(false), 1200);
  loadSystemHealth();
  setInterval(loadSystemHealth, 180000);
  setInterval(loadProjectPanel, 120000);
  setInterval(loadDarkroom, 15000);
  setInterval(checkServer, 30000);
  setInterval(loadLibrary, 60000);
  setInterval(loadSleepingStatus, 120000);
  setInterval(loadAllSilos, 300000);
  setInterval(loadSessionPanel, 60000);
  setInterval(loadResearchTraces, 120000);
  setInterval(loadStaleTraces, 120000);
  setInterval(loadUcb1Stats, 300000);

  // Restore free-chat conversation from previous session
  (function() {{
    const recalled = _recallConversation('__free__');
    if (recalled && recalled.length) {{
      conversation = recalled;
      renderConversation();
      scrollChat();
    }}
  }})();

  const ta = document.getElementById('chat-input');
  if (ta) {{
    // v1.0: restore draft from localStorage
    const draft = localStorage.getItem('matylda-chat-draft');
    if (draft) ta.value = draft;
    const autoResize = () => {{
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
    }};
    ta.addEventListener('input', () => {{
      localStorage.setItem('matylda-chat-draft', ta.value);
      autoResize();
    }});
    ta.addEventListener('keydown', e => {{
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) sendMessage();
    }});
  }}

  document.addEventListener('keydown', e => {{
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {{
      e.preventDefault();
      openSearch();
    }}
    // Escape: close topmost open overlay
    if (e.key === 'Escape') {{
      const rm = document.getElementById('research-modal-overlay');
      if (rm && rm.style.display !== 'none') {{ closeResearchModal(); return; }}
      const so = document.getElementById('search-overlay');
      if (so && so.style.display !== 'none') {{ closeSearch(); return; }}
      const co = document.getElementById('compare-overlay');
      if (co && co.style.display !== 'none') {{ closeCompare(); return; }}
      const nb = document.getElementById('nb-modal-overlay');
      if (nb && nb.style.display !== 'none') {{ closeNbModal(); return; }}
    }}
  }});
}});

// ── Notebook editor modal (v0.4e) ────────────────────────────────────────────

let _nbModalState = {{ siloId: null, nbId: null, autoSaveTimer: null }};

async function openNotebookModal(siloId, nbId) {{
  _nbModalState.siloId = siloId;
  _nbModalState.nbId = nbId;
  const url = `${{API}}/api/silos/${{siloId}}/notebooks/${{nbId}}`;
  const resp = await fetch(url).catch(() => null);
  if (!resp || !resp.ok) {{ alert('Nie można otworzyć notebooka.'); return; }}
  const nb = await resp.json();

  document.getElementById('nb-modal-title').value = nb.title || '';
  document.getElementById('nb-modal-tags').value = (nb.tags || []).join(', ');
  document.getElementById('nb-modal-textarea').value = nb.body || nb.content || '';
  document.getElementById('nb-modal-silo-badge').textContent = siloId === 'silo_2' ? '⚖️ Legal' : '🔬 Science';
  document.getElementById('nb-save-status').textContent = '';
  document.getElementById('nb-modal-overlay').style.display = 'flex';

  // Auto-save every 30s
  if (_nbModalState.autoSaveTimer) clearInterval(_nbModalState.autoSaveTimer);
  _nbModalState.autoSaveTimer = setInterval(() => saveNbModal(true), 30000);
}}

async function saveNbModal(auto = false) {{
  const {{ siloId, nbId }} = _nbModalState;
  if (!siloId || !nbId) return;
  const title = document.getElementById('nb-modal-title').value.trim();
  const tagsRaw = document.getElementById('nb-modal-tags').value;
  const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
  const body = document.getElementById('nb-modal-textarea').value;
  const statusEl = document.getElementById('nb-save-status');
  statusEl.textContent = auto ? '⏳ auto-zapis…' : '⏳ zapis…';

  const resp = await fetch(`${{API}}/api/silos/${{siloId}}/notebooks/${{nbId}}`, {{
    method: 'PUT',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ title, tags, body }}),
  }}).catch(() => null);

  if (resp && resp.ok) {{
    statusEl.textContent = auto ? `✓ auto ${{new Date().toLocaleTimeString('pl-PL', {{hour:'2-digit',minute:'2-digit'}})}}` : '✓ zapisano';
    setTimeout(() => {{ if(!auto) statusEl.textContent = ''; }}, 3000);
  }} else {{
    statusEl.textContent = '✗ błąd zapisu';
  }}
}}

async function deleteNbModal() {{
  const {{ siloId, nbId }} = _nbModalState;
  if (!siloId || !nbId) return;
  if (!confirm('Usunąć ten notebook? Tej operacji nie można cofnąć.')) return;
  const resp = await fetch(`${{API}}/api/silos/${{siloId}}/notebooks/${{nbId}}`, {{ method: 'DELETE' }}).catch(() => null);
  if (resp && resp.ok) {{
    closeNbModal();
    loadAllSilos();
  }} else {{
    alert('Błąd usuwania notebooka.');
  }}
}}

function closeNbModal() {{
  if (_nbModalState.autoSaveTimer) {{ clearInterval(_nbModalState.autoSaveTimer); _nbModalState.autoSaveTimer = null; }}
  document.getElementById('nb-modal-overlay').style.display = 'none';
  _nbModalState = {{ siloId: null, nbId: null, autoSaveTimer: null }};
}}

async function newNotebookModal(siloId) {{
  const title = prompt(`Tytuł nowego notebooka (${{siloId === 'silo_2' ? 'Legal' : 'Science'}}):`);
  if (!title) return;
  const resp = await fetch(`${{API}}/api/silos/${{siloId}}/notebooks/create`, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ title, project_id: _activeProjectId || 'lite' }}),
  }}).catch(() => null);
  if (!resp || !resp.ok) {{ alert('Błąd tworzenia notebooka.'); return; }}
  const nb = await resp.json();
  await openNotebookModal(siloId, nb.id);
  loadAllSilos();
}}

// ── Multi-project (v0.5) ─────────────────────────────────────────────────────

let _activeProjectId = '';
let _activeProjectName = '';

async function loadProjectPanel() {{
  const [projsResp, activeResp] = await Promise.all([
    fetch(API + '/api/library/projects').then(r => r.json()).catch(() => ({{projects:[]}})),
    fetch(API + '/api/library/projects/active').then(r => r.json()).catch(() => ({{project:null}})),
  ]);

  const projects = projsResp.projects || [];
  const active   = activeResp.project;
  _activeProjectId   = active ? (active.project_id || active.id || '') : '';
  _activeProjectName = active ? (active.name || _activeProjectId) : '';

  // Active name
  const nameEl = document.getElementById('proj-active-name');
  if (nameEl) nameEl.textContent = _activeProjectName || '— brak projektu —';

  // Stats
  if (_activeProjectId) {{
    fetch(API + `/api/library/projects/${{_activeProjectId}}/summary`)
      .then(r => r.json()).then(s => {{
        const statsEl = document.getElementById('proj-active-stats');
        if (statsEl) statsEl.textContent = `${{s.trace_count || 0}} traces · ${{s.notebook_count || 0}} notebooków`;
      }}).catch(() => {{}});
  }} else {{
    const statsEl = document.getElementById('proj-active-stats');
    if (statsEl) statsEl.textContent = '';
  }}

  // Project list
  const listEl = document.getElementById('proj-list');
  if (listEl) {{
    if (!projects.length) {{
      listEl.innerHTML = '<div style="font-size:.68rem;color:var(--text3)">Brak projektów</div>';
    }} else {{
      listEl.innerHTML = projects.slice(0, 10).map(p => `
        <div class="proj-item${{p.id === _activeProjectId ? ' active' : ''}}" onclick="switchProject('${{escHtml(p.id)}}','${{escHtml(p.name)}}')">
          <span class="proj-item-dot"></span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{escHtml(p.name)}}</span>
        </div>
      `).join('');
    }}
  }}
}}

async function switchProject(projectId, projectName) {{
  const resp = await fetch(API + '/api/library/projects/activate', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{project_id: projectId}}),
  }}).catch(() => null);
  if (!resp || !resp.ok) {{ alert('Nie można aktywować projektu.'); return; }}
  _activeProjectId   = projectId;
  _activeProjectName = projectName;
  await loadProjectPanel();
  // Reload project-specific data
  loadResearchTraces();
  loadAllSilos();
}}

async function deactivateProject() {{
  await fetch(API + '/api/library/projects/deactivate', {{method:'POST'}}).catch(() => {{}});
  _activeProjectId = '';
  _activeProjectName = '';
  await loadProjectPanel();
  loadResearchTraces();
  loadAllSilos();
}}

async function newProject() {{
  const name = prompt('Nazwa nowego projektu:');
  if (!name || !name.trim()) return;
  const desc = prompt('Opis (opcjonalnie):') || '';
  const resp = await fetch(API + '/api/library/projects', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{name: name.trim(), description: desc}}),
  }}).catch(() => null);
  if (!resp || !resp.ok) {{ alert('Błąd tworzenia projektu.'); return; }}
  const data = await resp.json();
  const proj = data.project || {{}};
  if (proj.id) {{
    await switchProject(proj.id, proj.name || name);
  }} else {{
    await loadProjectPanel();
  }}
}}

// ── v0.6.2: Upload file → auto-create thread ────────────────────────────────
async function uploadFileToThread(file, opts) {{
  opts = opts || {{}};
  const zone = document.getElementById('upload-zone');
  const origHTML = zone ? zone.innerHTML : '';

  // Status indicator in chat
  conversation.push({{role: 'user', content: '📎 Tworzę wątek z: ' + file.name}});
  conversation.push({{role: 'assistant', content: '⏳ Ekstrakcja tekstu i tworzenie wątku…', meta: {{streaming: true}}}});
  renderConversation(); scrollChat();

  const reader = new FileReader();
  reader.onload = async function(e) {{
    try {{
      const uint8 = new Uint8Array(e.target.result);
      const CHUNK = 8192;
      let binary = '';
      for (let i = 0; i < uint8.length; i += CHUNK) {{
        binary += String.fromCharCode.apply(null, uint8.subarray(i, i + CHUNK));
      }}
      const b64 = btoa(binary);

      const resp = await fetch(API + '/api/library/docs/upload-to-thread', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          filename: file.name,
          content_b64: b64,
          title: opts.title || '',
          domain: opts.domain || '',
        }})
      }});
      const data = await resp.json();

      const lastIdx = conversation.length - 1;
      if (data.ok) {{
        conversation[lastIdx] = {{
          role: 'assistant',
          content: `✓ Wątek "${{data.thread_title}}" utworzony z ${{file.name}}.\nID: ${{data.thread_stem}}`,
          meta: {{}}
        }};
        // Refresh thread list
        loadLibrary();
        // Open the new thread
        setTimeout(() => openThread(data.thread_stem, data.thread_title), 500);
      }} else {{
        conversation[lastIdx] = {{
          role: 'assistant',
          content: '✕ ' + (data.error || 'Błąd tworzenia wątku'),
          meta: {{error: true}}
        }};
      }}
    }} catch (err) {{
      const lastIdx = conversation.length - 1;
      conversation[lastIdx] = {{
        role: 'assistant',
        content: '✕ Błąd połączenia: ' + err.message,
        meta: {{error: true}}
      }};
    }}
    renderConversation(); scrollChat();
  }};
  reader.onerror = function() {{
    const lastIdx = conversation.length - 1;
    conversation[lastIdx] = {{
      role: 'assistant',
      content: '✕ Nie można odczytać pliku',
      meta: {{error: true}}
    }};
    renderConversation(); scrollChat();
  }};
  reader.readAsArrayBuffer(file);
}}

// File attach: show menu with two options
function showFileMenu(input) {{
  const file = input.files && input.files[0];
  if (!file) return;

  // If it's a PDF or large text → offer thread creation
  const isPdf = file.name.toLowerCase().endsWith('.pdf');
  const isDoc = /[.](pdf|docx?|txt|md|rtf)$/i.test(file.name);

  if (isDoc) {{
    const choice = confirm(
      `Plik: ${{file.name}}\n\n` +
      `OK = Utwórz nowy wątek z tego pliku\n` +
      `Anuluj = Załącz jako dokument (bez wątku)`
    );
    if (choice) {{
      uploadFileToThread(file);
      input.value = '';
      return;
    }}
  }}
  // Default: attach as doc
  handleFileSelect(input);
}}

// ── v0.6.3: Keyboard shortcuts ──────────────────────────────────────────────
// Ctrl+S handler for notebook modal
document.addEventListener('keydown', e => {{
  if ((e.ctrlKey || e.metaKey) && e.key === 's' && _nbModalState.nbId) {{
    e.preventDefault();
    saveNbModal();
  }}

  // Cmd+1..5 — tab switching
  if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey) {{
    if (e.key === '1') {{ e.preventDefault(); switchTab('work'); }}
    if (e.key === '2') {{ e.preventDefault(); switchTab('library'); }}
    if (e.key === '3') {{ e.preventDefault(); switchTab('lab'); }}
    if (e.key === '4') {{ e.preventDefault(); switchTab('analytics'); }}
    if (e.key === '5') {{ e.preventDefault(); switchTab('sleeping'); }}
  }}

  // Cmd+N — new thread (create from prompt)
  if ((e.metaKey || e.ctrlKey) && e.key === 'n' && !e.shiftKey) {{
    // Only if no modal is open
    if (_nbModalState.nbId) return;
    if (document.getElementById('research-modal-overlay').style.display !== 'none') return;
    e.preventDefault();
    const title = prompt('Nazwa nowego wątku:');
    if (!title || !title.trim()) return;
    createNewThread(title.trim());
  }}

  // Cmd+Shift+S — launch synthesis of selected threads
  if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'S') {{
    e.preventDefault();
    openSynthesis();
  }}

  // Ctrl+Shift+D — toggle debug panel
  if (e.ctrlKey && e.shiftKey && e.key === 'D') {{
    e.preventDefault();
    toggleDebug();
  }}
}});

// Quick prompt → create thread
function promptNewThread() {{
  const title = prompt('Nazwa nowego wątku:');
  if (!title || !title.trim()) return;
  createNewThread(title.trim());
}}

// Research toolbar collapse/expand
function toggleResearchToolbar() {{
  const tb = document.getElementById('research-toolbar');
  const arrow = document.getElementById('research-toolbar-arrow');
  if (!tb) return;
  const isHidden = tb.classList.toggle('hidden');
  if (arrow) arrow.classList.toggle('open', !isHidden);
  try {{ localStorage.setItem('matylda-toolbar-open', isHidden ? '0' : '1'); }} catch(e) {{}}
}}

// Create a new empty thread
async function createNewThread(title) {{
  const stem = title.toLowerCase().replace(/[^a-z0-9ąćęłńóśźż]+/gi, '_').replace(/_+/g, '_').substring(0, 60);
  const content = `# ${{title}}\n\n## Metadata\n- Domain: —\n- Value: —\n- Status: active\n- Last updated: ${{new Date().toISOString().slice(0,10)}}\n\n---\n\n## Notatki\n\n`;
  try {{
    const resp = await fetch(API + '/api/library/threads/create', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{title, stem, content}})
    }});
    const data = await resp.json();
    if (data.ok || data.stem) {{
      loadLibrary();
      setTimeout(() => openThread(data.stem || stem, title), 300);
    }} else if (data.error) {{
      alert('Błąd: ' + data.error);
    }}
  }} catch (err) {{
    alert('Błąd: ' + err.message);
  }}
}}

// ── Floating selection-copy button ────────────────────────────────────────────
(function () {{
  const btn = document.createElement('button');
  btn.id = 'sel-copy-btn';
  btn.textContent = '📋 Kopiuj zaznaczenie';
  document.body.appendChild(btn);

  function hide() {{ btn.style.display = 'none'; }}

  document.addEventListener('mouseup', ev => {{
    if (ev.target === btn) return; // don't hide on button click
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) {{ hide(); return; }}
    const text = sel.toString().trim();
    if (!text) {{ hide(); return; }}
    // Only show inside chat-history
    const chatEl = document.getElementById('chat-history');
    if (!chatEl) {{ hide(); return; }}
    const range = sel.getRangeAt(0);
    if (!chatEl.contains(range.commonAncestorContainer)) {{ hide(); return; }}
    // Position above selection
    const rect = range.getBoundingClientRect();
    const x = Math.min(Math.max(rect.left, 8), window.innerWidth - 180);
    const y = rect.top + window.scrollY - 34;
    btn.style.left = x + 'px';
    btn.style.top  = y + 'px';
    btn.style.display = 'block';
    btn.onclick = () => {{
      copyText(text, null);
      btn.textContent = '✓ Skopiowano';
      setTimeout(() => {{ hide(); btn.textContent = '📋 Kopiuj zaznaczenie'; }}, 1200);
    }};
  }});

  document.addEventListener('mousedown', ev => {{
    if (ev.target !== btn) hide();
  }});
  document.addEventListener('keydown', ev => {{
    if (ev.key === 'Escape') hide();
  }});
}})();

// ── Debug panel ───────────────────────────────────────────────────────────────
const _debugLog = [];
const _DEBUG_MAX = 60;

function _debugPush(type, msg, detail) {{
  _debugLog.push({{
    t: new Date().toISOString().slice(11, 23),
    type,
    msg: String(msg).slice(0, 400),
    detail: detail ? String(detail).slice(0, 600) : undefined,
  }});
  if (_debugLog.length > _DEBUG_MAX) _debugLog.shift();
  const panel = document.getElementById('debug-panel');
  if (panel && panel.style.display !== 'none') _renderDebugPanel();
}}

// Capture all errors before they vanish into the void
(function() {{
  const _origErr = console.error.bind(console);
  console.error = function(...args) {{
    _origErr(...args);
    _debugPush('error', args.map(a => (a instanceof Error) ? a.message : (typeof a === 'object' ? JSON.stringify(a) : String(a))).join(' '));
  }};
  const _origWarn = console.warn.bind(console);
  console.warn = function(...args) {{
    _origWarn(...args);
    _debugPush('warn', args.map(a => String(a)).join(' '));
  }};
  window.addEventListener('error', ev => {{
    _debugPush('uncaught', ev.message, ev.filename + ':' + ev.lineno + (ev.error ? '\\n' + ev.error.stack : ''));
  }});
  window.addEventListener('unhandledrejection', ev => {{
    _debugPush('promise', String(ev.reason), ev.reason && ev.reason.stack);
  }});
}})();

function _dbState() {{
  return {{
    activeThread: activeThread ? activeThread.stem : null,
    isStreaming: _isStreaming,
    streamingStem: _streamingStem,
    generation: _streamGeneration,
    convLen: conversation.length,
    cachedThreads: Object.keys(_threadConversations),
    localStorage: (() => {{ try {{ const ks = Object.keys(localStorage).filter(k => k.startsWith('ml_conv_')); return ks.length + ' wątków'; }} catch(e) {{ return 'N/A'; }} }})(),
  }};
}}

function _renderDebugPanel() {{
  const panel = document.getElementById('debug-panel');
  if (!panel) return;
  const state = _dbState();
  const stateHtml = '<pre style="font-size:.68rem;color:#9ee;margin:0 0 .5rem;white-space:pre-wrap;word-break:break-all">' +
    JSON.stringify(state, null, 2) + '</pre>';
  const entries = _debugLog.slice().reverse();
  const logHtml = entries.length === 0
    ? '<div style="color:#555;font-size:.7rem;padding:.4rem">Brak błędów ✓</div>'
    : entries.map(e => {{
        const col = e.type === 'error' ? '#f88' : e.type === 'uncaught' ? '#fa8' : e.type === 'promise' ? '#f8f' : '#8cf';
        return '<div style="border-bottom:1px solid #2a2a3e;padding:.25rem 0">' +
          '<span style="color:' + col + ';font-size:.65rem;font-weight:700">[' + e.t + '] ' + e.type + '</span> ' +
          '<span style="font-size:.7rem;color:#ddd">' + escHtml(e.msg) + '</span>' +
          (e.detail ? '<div style="font-size:.63rem;color:#888;white-space:pre-wrap;margin-top:.1rem">' + escHtml(e.detail.slice(0,300)) + '</div>' : '') +
          '</div>';
      }}).join('');
  panel.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">' +
    '<b style="font-size:.8rem;color:#9ee">🐛 Debug — Matylda Lab</b>' +
    '<div>' +
    '<button onclick="_debugLog.splice(0);_renderDebugPanel()" style="font-size:.65rem;background:#2a2a3e;color:#888;border:1px solid #444;border-radius:5px;padding:2px 6px;cursor:pointer;margin-right:4px">Wyczyść</button>' +
    '<button onclick="toggleDebug()" style="background:none;border:none;color:#888;cursor:pointer;font-size:.95rem;line-height:1">✕</button>' +
    '</div></div>' +
    stateHtml +
    '<div style="font-size:.68rem;color:#666;margin:.25rem 0 .3rem">Zdarzenia (najnowsze pierwsze):</div>' +
    '<div style="max-height:220px;overflow-y:auto;font-family:monospace">' + logHtml + '</div>';
}}

function toggleDebug() {{
  let panel = document.getElementById('debug-panel');
  if (!panel) {{
    panel = document.createElement('div');
    panel.id = 'debug-panel';
    panel.style.cssText = [
      'position:fixed', 'bottom:64px', 'right:16px', 'width:420px',
      'max-height:460px', 'overflow:hidden', 'background:#12121e',
      'border:1px solid #3a3a5e', 'border-radius:8px', 'padding:.75rem',
      'z-index:9999', 'box-shadow:0 4px 24px rgba(0,0,0,.7)',
      'font-family:monospace', 'display:none',
    ].join(';');
    document.body.appendChild(panel);
  }}
  const nowVisible = panel.style.display === 'none';
  panel.style.display = nowVisible ? 'block' : 'none';
  if (nowVisible) _renderDebugPanel();
}}
"""


# ── Main builder ──────────────────────────────────────────────────────────────

def build(server_mode: bool = False) -> str:
    active_rows   = parse_table(read("desk/ACTIVE_THREADS.md"))
    parking_rows  = parse_table(read("desk/PARKING_LOT.md"))
    decision_rows = parse_table(read("desk/DECISION_LOG.md"))
    prompt_rows   = parse_table(read("prompts/NEXT_PROMPTS.md"))
    week_text     = read("desk/THIS_WEEK.md")
    inbox_empty, inbox_count = inbox_status()
    artifacts     = artifact_list()
    today         = date.today().strftime("%Y-%m-%d")

    # Workspace grid (cards inside the collapsible strip)
    active_html   = render_active_threads(active_rows)
    parking_html  = render_parking(parking_rows)
    prompts_html  = render_prompts(prompt_rows, server_mode=server_mode)
    decisions_html= render_decisions(decision_rows, n=3)
    week_html     = render_this_week(week_text)
    inbox_html    = render_inbox(inbox_empty, inbox_count)
    artifacts_html= render_artifacts(artifacts)

    workspace_grid = f"""
      <div class="wcard">
        <div class="wcard-accent" style="background:#4a8fd4"></div>
        <h2>Active Desk</h2>
        {active_html}
      </div>
      <div class="wcard">
        <div class="wcard-accent" style="background:#2a9a6a"></div>
        <h2>This Week</h2>
        {week_html}
      </div>
      <div class="wcard">
        <div class="wcard-accent" style="background:#b08000"></div>
        <h2>Prompt Queue</h2>
        {prompts_html}
      </div>
      <div class="wcard">
        <div class="wcard-accent" style="background:#444"></div>
        <h2>Parking Lot</h2>
        {parking_html}
      </div>
      <div class="wcard">
        <div class="wcard-accent" style="background:#555"></div>
        <h2>Ostatnie decyzje</h2>
        {decisions_html}
      </div>
      <div class="wcard">
        <h2>Inbox</h2>
        <div class="inbox-row">{inbox_html}</div>
        <h2 style="margin-top:.6rem">Artifacts</h2>
        {artifacts_html}
      </div>"""

    js_block = f"<script>{_JS}</script>" if server_mode else ""

    if not server_mode:
        # Static snapshot — no interactive elements, minimal layout
        return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <title>Matylda Lab · Dashboard</title>
  <style>{_CSS}
  html, body {{ overflow: auto; height: auto; }}
  .app-layout {{ display: block; }}
  .panel-left, .panel-right {{ display: none; }}
  .panel-center {{ display: none; }}
  .workspace-grid {{ display: grid !important; max-height: none; }}
  .workspace-strip .workspace-toggle {{ display: none; }}
  </style>
</head>
<body>
  <header class="header">
    <div class="logo">Matylda Lab <span class="logo-sub">+ DARKROOM</span></div>
    <div class="header-right">
      <span class="date-str">{today}</span>
    </div>
  </header>
  <div class="workspace-strip">
    <div id="workspace-grid" class="workspace-grid">
      {workspace_grid}
    </div>
  </div>
</body>
</html>"""

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <title>Matylda Lab · Dashboard</title>
  <style>{_CSS}</style>
</head>
<body>

  <header class="app-header">
    <div class="app-brand">
      <span class="app-logo">M</span>
      <span class="app-name">Matylda Lab</span>
    </div>
    <div class="app-header-right">
      <span id="epi-badge" class="epi-badge hidden">⚡ EPI</span>
      <span class="date-str">{today}</span>
      <span class="server-dot" id="dot"></span>
      <span class="server-label" id="srv-label">online</span>
    </div>
  </header>

  <div class="app-shell">
  <nav class="ribbon" aria-label="Nawigacja">
    <button class="ribbon-btn active" id="tab-btn-work"
      onclick="switchTab('work')" title="Praca (⌘1)">💬</button>
    <button class="ribbon-btn" id="tab-btn-library"
      onclick="switchTab('library')" title="Biblioteka (⌘2)">📚</button>
    <button class="ribbon-btn" id="tab-btn-analytics"
      onclick="switchTab('analytics')" title="Analityka (⌘3)">⚗</button>
    <button class="ribbon-btn" id="tab-btn-sleeping"
      onclick="switchTab('sleeping')" title="Sleeping Matylda (⌘4)">🌙</button>
    <div class="ribbon-spacer"></div>
    <div class="ribbon-sep"></div>
    <button class="ribbon-btn" onclick="openSearch()" title="Szukaj (⌘K)">🔍</button>
    <button class="ribbon-btn" id="debug-btn" onclick="toggleDebug()" title="Debug (Ctrl+Shift+D)" style="opacity:.45;font-size:.7rem">🐛</button>
  </nav>

  <div class="app-body">

    <!-- TAB 1: PRACA -->
    <div id="page-work" class="tab-page" style="display:flex">
      <div class="work-layout">
        <aside class="work-sidebar">
          <div id="proj-ctx-bar" style="display:none" class="proj-ctx-bar">
            <span class="proj-ctx-label">Projekt:</span>
            <span id="proj-ctx-name" class="proj-ctx-name"></span>
            <button class="proj-ctx-clear" onclick="deactivateProject()" title="Wyłącz">✕</button>
          </div>
          <div class="sidebar-section">
            <div class="sidebar-header">
              <span>WĄTKI</span>
              <div class="sidebar-header-actions">
                <button class="icon-btn" onclick="openSearch()" title="Szukaj wątków">🔍</button>
                <button class="icon-btn" onclick="promptNewThread()" title="Nowy wątek">+</button>
                <button class="icon-btn" onclick="openSynthesis()" title="Synteza">⇌</button>
                <button class="icon-btn" onclick="loadLibrary()" title="Odśwież">↻</button>
              </div>
            </div>
            <div class="threads-filter-wrap">
              <input id="threads-filter-input" class="threads-filter-input"
                type="text" placeholder="Filtruj wątki…"
                oninput="renderThreads()" autocomplete="off">
            </div>
            <div id="synth-counter" class="synth-counter" onclick="openSynthesis()" style="display:none">
              <span class="synth-count" id="synth-count-num">0</span> Syntezuj zaznaczone
            </div>
            <button id="synthesize-btn" class="synthesize-btn" onclick="openSynthesis()" style="display:none">⇌ Syntezuj zaznaczone wątki</button>
            <div id="threads-list"><div class="empty">ładowanie…</div></div>
          </div>
          <div class="sidebar-section">
            <div class="sidebar-header">
              <span>PROJEKTY</span>
              <button class="icon-btn" onclick="showNewProjectForm()">+</button>
            </div>
            <div id="new-project-form" class="new-project-form hidden">
              <input id="proj-name" placeholder="Nazwa projektu">
              <input id="proj-desc" placeholder="Opis (opcjonalnie)">
              <div class="form-btns">
                <button class="form-btn" onclick="createProject()">Utwórz</button>
                <button class="form-btn secondary" onclick="hideNewProjectForm()">Anuluj</button>
              </div>
            </div>
            <div id="projects-list"><div class="empty">ładowanie…</div></div>
          </div>
          <div class="sidebar-section" id="nogo-sidebar-section">
            <div class="nogo-sidebar-header" onclick="toggleNoGoSidebar()" title="NO-GO Risk Registry">
              <span>⊗ NO-GO Ryzyko</span>
              <span id="nogo-sidebar-arrow" class="nogo-sidebar-arrow">▶</span>
            </div>
            <div id="nogo-sidebar-body" style="display:none">
              <div class="nogo-traj-list" id="nogo-sidebar-list">
                <div class="empty">ładowanie…</div>
              </div>
            </div>
          </div>
        </aside>

        <main class="work-main">
          <div class="research-toolbar-wrap">
            <button class="research-toolbar-toggle" onclick="toggleResearchToolbar()" title="Narzędzia badawcze">
              <span id="research-toolbar-arrow" class="research-toolbar-arrow">▶</span>
              Narzędzia
            </button>
            <div class="research-toolbar hidden" id="research-toolbar">
              <button class="research-btn" onclick="openLitMap()">📖 Mapa literatury</button>
              <button class="research-btn" onclick="openStressTest()">⊗ Stress-test</button>
              <button class="research-btn" onclick="openSynthesis()">⇌ Synteza</button>
              <button class="research-btn" onclick="window.print()">⎙ PDF</button>
              <button class="research-btn" onclick="openCompare()">⚖ Porównaj modele</button>
            </div>
          </div>
          <div id="thread-ctx-bar" class="thread-ctx-bar" style="display:none"></div>
          <div id="thread-ctx-preview" class="thread-ctx-preview"></div>
          <div id="doc-ctx-bar" class="thread-ctx-bar doc-ctx-bar" style="display:none"></div>
          <div id="doc-ctx-preview" class="thread-ctx-preview" style="display:none"></div>
          <div id="thread-view" class="thread-view" style="display:none">
            <div class="thread-view-header">
              <button class="thread-view-back" onclick="closeThreadView()">← Czat</button>
              <span class="thread-view-title" id="thread-view-title"></span>
            </div>
            <div class="thread-view-body" id="thread-view-body"></div>
          </div>
          <div class="chat-history" id="chat-history">
            <div class="chat-empty" id="chat-empty">Wpisz zadanie…</div>
          </div>
          <div class="chat-input-area">
            <div class="input-row">
              <label class="attach-btn" for="file-upload-input" title="Załącz dokument lub obraz — skany użyją lokalnego OCR">📎
                <input type="file" id="file-upload-input" accept=".md,.txt,.json,.pdf,.docx,.png,.jpg,.jpeg,.tif,.tiff,.heic,.webp"
                  onchange="showFileMenu(this)" style="display:none">
              </label>
              <textarea id="chat-input" class="chat-textarea" rows="1"
                placeholder="Zadanie lub odpowiedź… (⌘+Enter · /briefing)"></textarea>
              <div class="input-send-col">
                <button id="send-btn" class="send-btn" onclick="sendMessage()">▶</button>
                <button id="nogo-btn" class="nogo-btn" onclick="toggleNoGo()" title="NO-GO">⊗</button>
                <span id="spinner" class="spinner"></span>
              </div>
            </div>
            <div class="input-meta-row">
              <button class="clear-btn2" onclick="clearChat()" title="Nowa rozmowa">✕ wyczyść</button>
              <button id="copy-thread-btn" class="copy-thread-btn" onclick="copyThread()" title="Kopiuj całą rozmowę jako Markdown">📄 kopiuj</button>
              <div style="flex:1"></div>
              <span class="input-meta-label">🌐</span>
              <input id="url-input" class="url-input" type="text" placeholder="pobierz URL…">
              <button class="fetch-btn" onclick="fetchUrl()" title="Pobierz surowy tekst">↓</button>
              <button class="fetch-btn" onclick="fetchReaderMode()" title="Reader mode — wyciągnij artykuł">📖</button>
              <span class="input-meta-label">💾</span>
              <input id="save-input" class="save-input" type="text" placeholder="zapisz jako…">
            </div>
          </div>
        </main>
      </div>
    </div>

    <!-- TAB 2: BIBLIOTEKA -->
    <div id="page-library" class="tab-page" style="display:none">
      <div class="library-layout">
        <div class="library-toolbar">
          <div class="lib-view-switcher">
            <button class="lib-switch-btn active" id="lib-btn-threads" onclick="switchLibView('threads')">Wątki</button>
            <button class="lib-switch-btn" id="lib-btn-projects" onclick="switchLibView('projects')">Projekty</button>
          </div>
          <button class="icon-btn" onclick="loadLibraryTab()" title="Odśwież">↻</button>
          <div style="flex:1"></div>
          <input id="lib-search-input" class="lib-search" placeholder="Szukaj…" oninput="libSearch(this.value)">
        </div>
        <div class="library-body">
          <aside class="lib-sidebar">
            <div id="lib-list"><div class="empty">ładowanie…</div></div>
          </aside>
          <main class="lib-main">
            <div id="lib-detail" class="lib-detail">
              <div class="lib-detail-empty">← Wybierz wątek lub projekt</div>
            </div>
            <div class="lib-section">
              <div class="lib-section-header">
                <span>DOKUMENTY</span>
                <label class="attach-btn-lib" for="file-upload-lib">+ Dodaj plik
                  <input type="file" id="file-upload-lib" accept=".md,.txt,.json,.pdf,.png,.jpg,.jpeg,.tif,.tiff,.heic,.webp"
                    onchange="handleFileSelect(this)" style="display:none">
                </label>
              </div>
              <div id="docs-list"><div class="empty">Brak dokumentów</div></div>
            </div>
            <div class="lib-section">
              <div class="lib-section-header">
                <span>PAMIĘĆ</span>
                <button class="icon-btn" onclick="loadMemory()">↻</button>
              </div>
              <div style="display:flex;gap:6px;margin-bottom:8px">
                <button class="mem-tab active" id="tab-insights" onclick="switchMemTab('insights')">Zatwierdzone</button>
                <button class="mem-tab" id="tab-candidates" onclick="switchMemTab('candidates')">Kandydaci</button>
              </div>
              <div id="memory-list"><div class="empty">ładowanie…</div></div>
              <div id="candidates-list" style="display:none"><div class="empty">ładowanie…</div></div>
            </div>
            <div class="lib-section">
              <div class="lib-section-header">
                <span>SILOSY</span>
                <button class="icon-btn" onclick="loadAllSilos()">↻</button>
              </div>
              <div id="silos-widgets-container">
                <div style="color:var(--text3);font-size:.75rem">ładowanie…</div>
              </div>
            </div>
            <div class="lib-section">
              <div class="lib-section-header"><span>SESJA</span></div>
              <div id="session-panel-content" class="session-panel">
                <div style="color:var(--text3);font-size:.75rem">ładowanie…</div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>

    <!-- TAB 3: ANALITYKA -->
    <div id="page-analytics" class="tab-page" style="display:none">
      <div class="analytics-layout">
        <div class="analytics-col">
          <div class="analytics-col-header">DARKROOM</div>
          <div class="dr-section">
            <div class="dr-section-title">DISPOSITION</div>
            <div id="dr-disposition"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
          <div class="dr-section">
            <div class="dr-section-title">HISTORIA DISPOSITION</div>
            <div class="disp-history-chart" id="disp-history-chart">
              <div class="empty" style="font-size:.7rem;padding:.5rem 0">Brak historii</div>
            </div>
          </div>
          <div class="dr-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span id="dr-tensions-title">TENSIONS (0)</span>
              <button class="icon-btn" onclick="triageTensions()" title="Scal duplikaty, usuń testowe i przeterminowane (>30 dni, sev<0.6). Krytyczne (≥0.6) zostają." style="font-size:.66rem;padding:1px 7px;border:1px solid var(--border2);border-radius:5px;color:var(--text3);background:none;cursor:pointer">⚖ triage</button>
            </div>
            <div id="dr-tensions"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
            <div class="tension-add-form">
              <input id="tension-desc" placeholder="Opis napięcia…">
              <div style="display:flex;gap:.3rem">
                <select id="tension-type">
                  <option value="conceptual_conflict">conceptual_conflict</option>
                  <option value="unresolved_critique">unresolved_critique</option>
                  <option value="drift_signature">drift_signature</option>
                  <option value="hallucination_pattern">hallucination_pattern</option>
                  <option value="boundary_violation">boundary_violation</option>
                  <option value="contradiction">contradiction</option>
                </select>
                <input id="tension-sev" type="number" min="0.1" max="1.0" step="0.1" value="0.5" style="width:4rem">
              </div>
              <button class="form-btn" onclick="addTension()">+ Dodaj napięcie</button>
            </div>
          </div>
          <div class="dr-section">
            <div class="dr-section-title">PENDING APPROVALS</div>
            <div id="dr-approvals"><p class="dr-no-approval">ładowanie…</p></div>
          </div>
          <div class="dr-section">
            <div class="dr-section-title">METRICS</div>
            <div id="dr-metrics"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
            <div class="review-log-section">
              <button class="review-log-toggle" onclick="toggleReviewLog()">Historia recenzji ▾</button>
              <div id="review-log-list" class="review-log-list"></div>
            </div>
          </div>
        </div>
        <div class="analytics-col">
          <div class="analytics-col-header">ANALITYKA</div>
          <div class="dr-section" id="dr-report-section">
            <div class="dr-section-title">RAPORT EPISTEMICZNY</div>
            <button class="report-generate-btn" id="report-generate-btn" onclick="generateReport()">⟳ Generuj raport</button>
            <div class="report-date" id="report-date"></div>
            <div class="report-text" id="report-text"></div>
            <div style="display:flex;gap:.3rem;margin-top:.2rem">
              <button style="flex:1;padding:.3rem;background:none;border:none;color:var(--text3);font-size:.7rem;cursor:pointer" onclick="toggleReport()" id="report-toggle-btn">▾ Pokaż raport</button>
              <button class="report-copy-btn" style="padding:.3rem .6rem;background:none;border:1px solid var(--border2);border-radius:5px;color:var(--text3);font-size:.7rem;cursor:pointer" onclick="copyReport()" id="report-copy-btn" title="Kopiuj raport">📄 Kopiuj</button>
            </div>
          </div>
          <div class="dr-section" id="sm-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>SLEEPING MATYLDA</span>
              <button class="icon-btn" onclick="runSleepingMatylda()" title="Uruchom syntezę">▶</button>
            </div>
            <div id="sm-status" style="font-size:.72rem;color:var(--text3);margin-bottom:.4rem">ładowanie…</div>
            <div id="sm-result"></div>
          </div>

          <div class="dr-section" id="focus-mode-section">
            <div class="dr-section-title">🎯 FOCUS MODE</div>
            <div id="focus-panel-config" class="focus-panel">
              <div style="font-size:.68rem;color:var(--text3);margin-bottom:.4rem">Nad czym pracować:</div>
              <div class="focus-mode-row" style="flex-direction:column;gap:.25rem;margin-bottom:.5rem">
                <label class="focus-area-check"><input type="checkbox" id="fa-questions" value="questions" checked> ❓ pytania otwarte</label>
                <label class="focus-area-check"><input type="checkbox" id="fa-tensions"  value="tensions"> ⚡ napięcia DARKROOM</label>
                <label class="focus-area-check"><input type="checkbox" id="fa-steps"     value="steps"> 📋 kroki badawcze</label>
                <label class="focus-area-check"><input type="checkbox" id="fa-nogo"      value="no_go"> ⊗ weryfikacja NO-GO</label>
              </div>
              <div style="font-size:.68rem;color:var(--text3);margin-bottom:.3rem">Czas / tryb:</div>
              <div class="focus-mode-row" id="focus-timer-btns">
                <button class="focus-timer-btn active" data-mode="timebox" data-val="900"   onclick="focusSelectTimer(this)">15 min</button>
                <button class="focus-timer-btn"        data-mode="timebox" data-val="1800"  onclick="focusSelectTimer(this)">30 min</button>
                <button class="focus-timer-btn"        data-mode="timebox" data-val="3600"  onclick="focusSelectTimer(this)">1h</button>
                <button class="focus-timer-btn"        data-mode="until_idle" data-val="3" onclick="focusSelectTimer(this)">do wyczerpania</button>
              </div>
              <div id="focus-custom-time-row" style="display:none;margin-bottom:.35rem">
                <input id="focus-custom-minutes" type="number" min="1" max="480" placeholder="minuty"
                  style="width:70px;background:var(--surf2);border:1px solid var(--border2);border-radius:4px;color:var(--text);padding:.2rem .35rem;font-size:.75rem">
              </div>
              <textarea id="focus-custom-prompt" class="focus-custom-prompt" rows="2"
                placeholder="Opcjonalnie: na czym dokładnie się skupić? (np. wątek X, napięcie Y…)"></textarea>
              <div style="display:flex;gap:.3rem;align-items:center;margin-bottom:.45rem">
                <label class="focus-area-check"><input type="checkbox" id="fa-tag-low-risk"> oznaczaj niskie ryzyko</label>
              </div>
              <button class="focus-start-btn" id="focus-start-btn" onclick="startFocusMode()">▶ START Focus Mode</button>
            </div>
            <div id="focus-panel-active" style="display:none">
              <div class="focus-status-bar">
                <span>
                  <span id="focus-status-label" style="color:var(--text2)">uruchomiona</span>
                  <span class="focus-badge" id="focus-findings-badge">0</span>
                </span>
                <span class="focus-countdown" id="focus-countdown">—</span>
              </div>
              <div class="focus-idle-note" id="focus-idle-note" style="display:none"></div>
              <div class="focus-mode-row" style="margin-bottom:.35rem">
                <button class="focus-ctrl-btn" id="focus-pause-btn" onclick="toggleFocusPause()">⏸ Pauzuj</button>
                <button class="focus-ctrl-btn" onclick="stopFocusMode()" style="color:var(--red)">■ Stop</button>
              </div>
              <div id="focus-areas-active" style="font-size:.68rem;color:var(--text3)"></div>
            </div>
            <div id="focus-panel-done" style="display:none">
              <div style="font-size:.73rem;color:var(--green);margin-bottom:.3rem">✓ Sesja zakończona</div>
              <div id="focus-done-summary" style="font-size:.71rem;color:var(--text2);margin-bottom:.4rem"></div>
              <button class="focus-start-btn" onclick="resetFocusPanel()" style="background:var(--surf3);color:var(--text2)">Nowa sesja</button>
            </div>
          </div>

          <div class="dr-section" id="traces-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>RESEARCH TRACES</span>
              <button class="icon-btn" onclick="loadResearchTraces()">↻</button>
            </div>
            <div id="traces-list"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
          <div class="dr-section" id="stale-traces-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>⚠ STALE TRACES</span>
              <button class="icon-btn" onclick="loadStaleTraces()" title="Odśwież">↻</button>
            </div>
            <div id="stale-traces-list"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
          <div class="dr-section" id="ucb1-section">
            <div class="dr-section-title">MODEL UCB1</div>
            <div id="ucb1-stats"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
          <div class="dr-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>SYSTEM HEALTH</span>
              <button class="icon-btn" onclick="loadSystemHealth()" title="Odśwież">↻</button>
            </div>
            <div id="sys-health-content"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
          <div class="dr-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>PROJEKTY (multi)</span>
              <button class="icon-btn" onclick="loadProjectPanel()">↻</button>
            </div>
            <div class="proj-active-name" id="proj-active-name">— brak projektu —</div>
            <div class="proj-stats" id="proj-active-stats"></div>
            <div class="proj-list" id="proj-list"></div>
            <div class="proj-actions">
              <button class="form-btn" onclick="newProject()">+ Nowy projekt</button>
              <button class="form-btn secondary" onclick="deactivateProject()">Odłącz</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: SLEEPING MATYLDA -->
    <div id="page-sleeping" class="tab-page" style="display:none">
      <div class="analytics-layout">
        <div class="analytics-col">
          <div class="analytics-col-header">🌙 SLEEPING MATYLDA</div>
          <div class="dr-section" id="sm-section-2">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>STATUS</span>
              <button class="icon-btn" onclick="runSleepingMatylda()" title="Uruchom cykl">▶</button>
            </div>
            <div id="sm-status-2" style="font-size:.72rem;color:var(--text3);margin-bottom:.4rem">ładowanie…</div>
            <div id="sm-result-2"></div>
          </div>
          <div class="dr-section" id="focus-mode-section-2">
            <div class="dr-section-title">🎯 FOCUS MODE</div>
            <div id="focus-panel-config-2" class="focus-panel">
              <div style="font-size:.68rem;color:var(--text3);margin-bottom:.4rem">Nad czym pracować:</div>
              <div class="focus-mode-row" style="flex-direction:column;gap:.25rem;margin-bottom:.5rem">
                <label class="focus-area-check"><input type="checkbox" id="fa2-questions" value="questions" checked> ❓ pytania otwarte</label>
                <label class="focus-area-check"><input type="checkbox" id="fa2-tensions"  value="tensions"> ⚡ napięcia DARKROOM</label>
                <label class="focus-area-check"><input type="checkbox" id="fa2-steps"     value="steps"> 📋 kroki badawcze</label>
                <label class="focus-area-check"><input type="checkbox" id="fa2-nogo"      value="no_go"> ⊗ weryfikacja NO-GO</label>
              </div>
              <div style="font-size:.68rem;color:var(--text3);margin-bottom:.3rem">Czas / tryb:</div>
              <div class="focus-mode-row" id="focus-timer-btns-2">
                <button class="focus-timer-btn active" data-mode="timebox" data-val="900"   onclick="focusSelectTimer2(this)">15 min</button>
                <button class="focus-timer-btn"        data-mode="timebox" data-val="1800"  onclick="focusSelectTimer2(this)">30 min</button>
                <button class="focus-timer-btn"        data-mode="timebox" data-val="3600"  onclick="focusSelectTimer2(this)">1h</button>
                <button class="focus-timer-btn"        data-mode="until_idle" data-val="3" onclick="focusSelectTimer2(this)">do wyczerpania</button>
              </div>
              <div id="focus-custom-time-row-2" style="display:none;margin-bottom:.35rem">
                <input id="focus-custom-minutes-2" type="number" min="1" max="480" placeholder="minuty"
                  style="width:70px;background:var(--surf2);border:1px solid var(--border2);border-radius:4px;color:var(--text);padding:.2rem .35rem;font-size:.75rem">
              </div>
              <textarea id="focus-custom-prompt-2" class="focus-custom-prompt" rows="2"
                placeholder="Opcjonalnie: na czym dokładnie się skupić?"></textarea>
              <div style="display:flex;gap:.3rem;align-items:center;margin-bottom:.45rem">
                <label class="focus-area-check"><input type="checkbox" id="fa2-tag-low-risk"> oznaczaj niskie ryzyko</label>
              </div>
              <button class="focus-start-btn" id="focus-start-btn-2" onclick="startFocusMode2()">▶ START Focus Mode</button>
            </div>
            <div id="focus-panel-active-2" style="display:none">
              <div class="focus-status-bar">
                <span>
                  <span id="focus-status-label-2" style="color:var(--text2)">uruchomiona</span>
                  <span class="focus-badge" id="focus-findings-badge-2">0</span>
                </span>
                <span class="focus-countdown" id="focus-countdown-2">—</span>
              </div>
              <div class="focus-idle-note" id="focus-idle-note-2" style="display:none"></div>
              <div class="focus-mode-row" style="margin-bottom:.35rem">
                <button class="focus-ctrl-btn" id="focus-pause-btn-2" onclick="toggleFocusPause2()">⏸ Pauzuj</button>
                <button class="focus-ctrl-btn" onclick="stopFocusMode2()" style="color:var(--red)">■ Stop</button>
              </div>
              <div id="focus-areas-active-2" style="font-size:.68rem;color:var(--text3)"></div>
            </div>
            <div id="focus-panel-done-2" style="display:none">
              <div style="font-size:.73rem;color:var(--green);margin-bottom:.3rem">✓ Sesja zakończona</div>
              <div id="focus-done-summary-2" style="font-size:.71rem;color:var(--text2);margin-bottom:.4rem"></div>
              <button class="focus-start-btn" onclick="resetFocusPanel2()" style="background:var(--surf3);color:var(--text2)">Nowa sesja</button>
            </div>
          </div>
        </div>
        <div class="analytics-col">
          <div class="analytics-col-header">FINDINGS &amp; STAN</div>
          <div class="dr-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>FINDINGS DO ZATWIERDZENIA</span>
              <button class="icon-btn" onclick="loadSmFindings()">↻</button>
            </div>
            <div id="sm-approvals-list"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
          <div class="dr-section" id="sm-traces-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>RESEARCH TRACES</span>
              <button class="icon-btn" onclick="loadResearchTraces()">↻</button>
            </div>
            <div id="sm-traces-list"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
          <div class="dr-section">
            <div class="dr-section-title" style="display:flex;align-items:center;justify-content:space-between">
              <span>SYSTEM HEALTH</span>
              <button class="icon-btn" onclick="loadSystemHealth()">↻</button>
            </div>
            <div id="sm-health-content"><div style="color:var(--text3);font-size:.75rem">ładowanie…</div></div>
          </div>
        </div>
      </div>
    </div>

  </div><!-- /app-body -->
  </div><!-- /app-shell -->

  <!-- Research modal -->
  <div id="research-modal-overlay" class="research-modal-overlay" style="display:none" onclick="if(event.target===this)closeResearchModal()">
    <div class="research-modal">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:.6rem">
        <h3 id="research-modal-title">Narzędzie badawcze</h3>
        <button onclick="closeResearchModal()" style="background:none;border:none;color:var(--text3);font-size:1.1rem;cursor:pointer;padding:2px 6px;border-radius:4px" title="Zamknij">&#x2715;</button>
      </div>
      <label id="research-modal-label" style="font-size:.75rem;color:var(--text3);display:block;margin-bottom:.25rem">Temat</label>
      <textarea id="research-modal-input" rows="3" placeholder="Wpisz&#8230;"></textarea>
      <div class="research-modal-btns">
        <button class="research-modal-cancel" onclick="closeResearchModal()">Anuluj</button>
        <button class="research-modal-submit" onclick="submitResearchModal()">&#9658; Uruchom</button>
      </div>
    </div>
  </div>

  <!-- Model comparison modal -->
  <div id="compare-overlay" class="compare-overlay" style="display:none">
    <div class="compare-modal">
      <div class="compare-modal-header">
        <span class="compare-modal-title">&#9878; Porównanie modeli</span>
        <button class="compare-modal-close" onclick="closeCompare()">&#x2715;</button>
      </div>
      <div class="compare-grid" id="compare-grid">
        <div class="compare-col"><div class="compare-col-title">Haiku</div><div class="compare-text" id="cmp-haiku">—</div></div>
        <div class="compare-col"><div class="compare-col-title">Sonnet</div><div class="compare-text" id="cmp-sonnet">—</div></div>
        <div class="compare-col"><div class="compare-col-title">Opus</div><div class="compare-text" id="cmp-opus">—</div></div>
      </div>
      <div class="compare-input-row">
        <input id="compare-input" class="compare-input" placeholder="Zadanie do porównania…"
          onkeydown="if(event.key==='Enter')runCompare()">
        <button id="compare-run-btn" class="compare-run-btn" onclick="runCompare()">&#9654; Porównaj</button>
      </div>
    </div>
  </div>

  <!-- Search modal (v0.7: FTS5 + source filters) -->
  <div id="search-overlay" class="search-overlay" style="display:none" onclick="if(event.target===this)closeSearch()">
    <div class="search-box">
      <div class="search-input-row">
        <span class="search-icon">⌕</span>
        <input id="search-input" class="search-input" placeholder="BM25 search — wątki, dokumenty, artefakty, pamięć… (⌘K)"
          oninput="onSearchInput(this.value)" onkeydown="onSearchKey(event)">
        <button class="search-close" onclick="closeSearch()">✕</button>
      </div>
      <div style="display:flex;gap:4px;padding:6px 12px;border-bottom:1px solid var(--border);flex-wrap:wrap">
        <button class="search-filter-btn active" data-filter="" onclick="setSearchFilter(this,'')">Wszystko</button>
        <button class="search-filter-btn" data-filter="thread" onclick="setSearchFilter(this,'thread')">📝 Wątki</button>
        <button class="search-filter-btn" data-filter="doc" onclick="setSearchFilter(this,'doc')">📎 Dokumenty</button>
        <button class="search-filter-btn" data-filter="insight" onclick="setSearchFilter(this,'insight')">💡 Pamięć</button>
        <button class="search-filter-btn" data-filter="artifact" onclick="setSearchFilter(this,'artifact')">📄 Artefakty</button>
      </div>
      <div id="search-results" class="search-results">
        <div class="search-empty">Wpisz frazę…</div>
      </div>
    </div>
  </div>

  <!-- Notebook editor modal (v0.4e) -->
  <div id="nb-modal-overlay" class="nb-modal-overlay" style="display:none" onclick="if(event.target===this)closeNbModal()">
    <div class="nb-modal">
      <div class="nb-modal-header">
        <span style="font-size:.75rem;color:var(--text3);white-space:nowrap" id="nb-modal-silo-badge">📓</span>
        <input id="nb-modal-title" class="nb-modal-title-input" placeholder="Tytuł notebooka…" />
        <input id="nb-modal-tags" class="nb-modal-tags" placeholder="tagi, oddzielone, przecinkiem" />
        <button class="nb-btn" onclick="closeNbModal()">✕</button>
      </div>
      <div class="nb-modal-body">
        <textarea id="nb-modal-textarea" class="nb-modal-textarea" placeholder="Treść notebooka (Markdown)…"></textarea>
      </div>
      <div class="nb-modal-footer">
        <button class="nb-btn nb-btn-primary" onclick="saveNbModal()">💾 Zapisz</button>
        <button class="nb-btn nb-btn-danger" onclick="deleteNbModal()">🗑 Usuń</button>
        <span class="nb-save-status" id="nb-save-status"></span>
      </div>
    </div>
  </div>

  {js_block}
</body>
</html>"""


# ── Entry point (legacy — użyj run.py) ───────────────────────────────────────

def main():
    """Legacy entry point — deleguje do run.py / server.start()."""
    from .server import start  # noqa: PLC0415
    start(port=PORT, open_browser=True)


if __name__ == "__main__":
    main()
