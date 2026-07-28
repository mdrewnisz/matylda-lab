# Matylda Lite Usage Protocol v0.1

## Purpose

This protocol turns Matylda Lite from a folder structure into a repeatable
operating loop.

Without a usage rhythm, the Library becomes storage, the Desk becomes clutter,
and the Prompt Queue becomes a list of intentions. This document defines how
the user should use Matylda Lite day to day and week to week so the system
stays small, explicit, and useful.

## Core Rule

If a thought is raw, it goes to Inbox.
If it has durable value, it becomes a Thread Card.
If it needs action now, it goes to Desk.
If it is valuable but not now, it goes to Parking Lot.
If a decision is made, it goes to Decision Log.
If outside help is needed, it goes to Prompt Queue.

## Daily Capture

Purpose:
Capture without organizing too early.

User action:
Add fragments, links, conversation excerpts, ideas, and reminders to
`inbox/raw_notes.md`.

Rules:

- do not classify everything immediately
- do not promote raw notes to memory
- raw notes are temporary
- raw notes should be reviewed later

## Triage

Purpose:
Turn raw notes into one of four outcomes.

Frequency:
As needed, preferably every few days.

Outcomes:

1. discard
2. append to existing thread card
3. create new thread card
4. create prompt queue item

Decision questions:

- Is this durable?
- Is this useful within 1-3 months?
- Does it belong to an existing thread?
- Does it require action now?
- Is it only brokat?

## Thread Card Creation

Purpose:
Create durable addresses for valuable threads.

Location:
`library/threads/`

Template:
`templates/THREAD_CARD_TEMPLATE.md`

Rules:

- every thread card must have a next artifact or next action
- every thread card must have status and value
- speculative threads must say so explicitly
- no thread card is automatically active

## Desk Management

Purpose:
Keep active work limited.

Location:
`desk/ACTIVE_THREADS.md`

Rules:

- keep only 3-5 active threads
- if everything is active, nothing is active
- every active thread needs a next action
- move threads to parking when they lose urgency
- do not add a thread to desk just because it is interesting

## Parking Lot

Purpose:
Preserve valuable threads without working on them now.

Location:
`desk/PARKING_LOT.md`

Rules:

- parking is not failure
- every parked thread should have a return trigger
- parked threads should not appear in weekly focus unless reactivated

## Decision Log

Purpose:
Prevent re-litigating settled decisions.

Location:
`desk/DECISION_LOG.md`

Rules:

- record architectural, scope, and priority decisions
- include reason and rejected alternatives
- decisions can be revised, but not silently overwritten

## Prompt Queue

Purpose:
Prepare clean tasks for external tools.

Location:
`prompts/NEXT_PROMPTS.md`

Targets may include:

- Codex
- Claude
- ChatGPT
- Gustaw
- Perplexity

Rules:

- every prompt queue item needs context, constraints, and expected output
- prompt queue items should be executable without re-explaining the entire project
- hostile review tasks should be marked clearly

## Weekly Desk Review

Purpose:
Reset focus and prevent thread sprawl.

Frequency:
Once per week.

Location:
`desk/THIS_WEEK.md`

Checklist:

- Review active threads.
- Keep, park, or archive each active thread.
- Review parking lot for possible reactivation.
- Review decision log for new decisions.
- Review prompt queue.
- Select up to 3 weekly priorities.
- Define next concrete actions.

Add this weekly review template:

```md
# Weekly Desk Review — YYYY-MM-DD
## Keep Active
## Move to Parking
## Reactivate from Parking
## New Decisions
## Prompt Queue Updates
## This Week Focus
1.
2.
3.
## Notes
```

## Monthly Library Review

Purpose:
Prevent the library from becoming a graveyard.

Frequency:
Monthly.

Checklist:

- identify dead threads
- merge duplicates
- archive stale threads
- promote useful patterns into docs
- review source-of-truth conflicts

## Status Changes

Valid transitions:

- inbox -> thread card
- thread card -> active
- active -> parked
- parked -> active
- parked -> archived
- thread card -> archived
- prompt queue item -> completed
- decision -> revised decision

## Safety and Non-Autonomy Rules

- Matylda Lite does not act on its own
- no file changes without user/Codex action
- no automatic memory promotion
- no legal automation
- no hidden background work
- no destructive edits
- everything must be inspectable as text

## First Operating Cycle

1. Review current active threads.
2. Draft `MATYLDA_LITE_MEMORY_POLICY.md`.
3. Draft `SCALAR_PUMP_NO_GO_NOTE.md` skeleton.
4. Keep Dom nr 2 parked unless a practical deadline appears.
5. Update `desk/THIS_WEEK.md`.

## Done Criteria

The protocol is done when:

- it explains daily capture
- it explains triage
- it explains weekly review
- it defines desk limits
- it defines parking
- it defines prompt queue use
- it reinforces non-autonomy
