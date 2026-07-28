# Matylda Lab

Matylda Lab is a local research workspace for preserving, classifying, testing, and developing user threads and hypotheses.

## Current status

Status date: 2026-06-12

Matylda Lab has moved beyond the original Lite v0.1 scaffold. It is now an explicitly experimental workspace with a dashboard/server, DARKROOM review, homeostasis, task queue, Sleeping Matylda consolidation, and Focus Mode v1.2.

The operating rule is constructive first: Matylda Lab may generate, compare, and develop hypotheses, but every consequential transition remains local, explicit, and reviewable. It does not silently publish outputs or convert suggestions into decisions.

## Core metaphor

- Library stores durable thread cards.
- Desk contains only active work.
- Secretary prepares summaries, decisions, and next prompts.
- Inbox receives raw fragments.
- Prompt queue prepares work for external tools such as Codex, Claude, ChatGPT, Gustaw, or Perplexity.

## Non-goals

- no autonomous execution by default; optional background workers require `--automation`
- no backend migration
- no network/API dependency
- no heavy local LLM runtime
- no legal automation
- no automatic memory promotion
- no destructive file operations

## Checkpoint hygiene

Commit candidates:

- source code under `src/`
- tests under `tests/`
- durable docs under `docs/`, `README_LITE.md`, `INSTRUKCJA.md`
- curated thread cards under `library/threads/`
- desk state under `desk/`
- intentionally kept artifacts when they are research outputs

Do not commit by default:

- session snapshots under `data/*_session.json`
- task queue event logs
- generated diary/reflection runtime memory
- DARKROOM review logs and transient reports
- local attached/generated documents
- DARKROOM tension archives and runtime logs

Tracked runtime files that already exist in Git should be reviewed case by case before a checkpoint. Treat large log or metrics diffs as evidence unless they are explicitly needed for a reproducible test.

## First workflow

1. Add rough notes to `inbox/raw_notes.md`.
2. Convert valuable notes into thread cards under `library/threads/`.
3. Add only 3-5 active threads to `desk/ACTIVE_THREADS.md`.
4. Move non-active but valuable threads to `desk/PARKING_LOT.md`.
5. Record durable decisions in `desk/DECISION_LOG.md`.
6. Prepare external-tool prompts in `prompts/NEXT_PROMPTS.md`.
