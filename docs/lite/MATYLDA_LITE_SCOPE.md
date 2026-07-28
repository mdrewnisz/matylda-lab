# Matylda Lite Scope v0.1

## Purpose

Matylda Lite is a lightweight organizational system for preserving,
classifying, reviewing, and activating user threads.

Its job is not to replace Matylda Full. Its job is to prevent valuable context
from being lost, scattered, or repeatedly rediscovered from scratch.

Matylda Lite should help the user:

- keep durable records of important threads
- separate active work from parked work
- extract decisions, constraints, and open questions
- prepare the next useful prompt or review packet
- preserve continuity without introducing hidden automation

## Non-Goals

Matylda Lite v0.1 does not aim to be:

- a full backend migration
- a workflow engine
- a live agent runtime
- an autonomous operator
- a heavy local LLM platform
- a legal or high-stakes automation layer
- a self-modifying system
- a silent memory or truth engine

More explicitly, Lite must not:

- run autonomous execution
- depend on heavy local LLM reasoning by default
- recreate `backend/core-v1`
- maintain a live agent loop
- perform legal-domain automation
- promote memory automatically
- edit files without clear user supervision
- expand its own scope through self-directed behavior
- create hidden scheduling, daemons, or watchers
- silently convert working notes into canonical truth

## Core Metaphor

Matylda Lite = Library + Desk + Secretary.

### Library

The Library stores durable thread cards.

This is where important threads, projects, imported notes, and preserved context
live after they are worth keeping. The Library is not for everything. It is for
materials that should remain available, classifiable, and reviewable over time.

The Library should answer:

- what this thread is
- why it matters
- what sources belong to it
- what status it has
- whether it is active, working, canonical, or archived

### Desk

The Desk contains only active work.

This is the working surface for what is currently under review, in progress, or
waiting for an immediate decision. The Desk should stay small on purpose. If
everything stays on the Desk, then nothing is truly active.

The Desk should answer:

- what is active right now
- what is blocked
- what is parked
- what needs review this week
- what decisions are currently shaping the work

### Secretary

The Secretary summarizes, classifies, extracts decisions, and prepares next
prompts.

The Secretary is not an autonomous agent. It is a bounded helper role. Its job
is to turn scattered material into clearer working structure.

The Secretary should help with:

- thread summaries
- classification into desk vs library
- extraction of decisions and constraints
- identification of open threads and next questions
- preparation of the next prompt packet

## Core Directories

The initial structure for Matylda Lite v0.1 should be:

```text
matylda-lite/
  docs/lite/
  inbox/
  library/
    THREAD_INDEX.md
    threads/
  desk/
    ACTIVE_THREADS.md
    PARKING_LOT.md
    THIS_WEEK.md
    DECISION_LOG.md
  prompts/
    NEXT_PROMPTS.md
  artifacts/
  src/matylda_lite/
```

### Directory Roles

#### `docs/lite/`

Lite scope, policies, conventions, and extraction notes.

#### `inbox/`

Raw incoming material not yet classified.

Examples:

- copied thread exports
- notes to review later
- imported prompts
- temporary captures

#### `library/`

Durable preserved context.

This should contain:

- `THREAD_INDEX.md` as the top-level map of durable threads
- `threads/` as per-thread cards, notes, and structured records

#### `desk/`

Active working surface only.

This should contain:

- `ACTIVE_THREADS.md`
  - what is currently active
- `PARKING_LOT.md`
  - what is valuable but intentionally not active
- `THIS_WEEK.md`
  - the short operating focus for the week
- `DECISION_LOG.md`
  - important active decisions and clarifications

#### `prompts/`

Prompt-preparation surface.

This should start with:

- `NEXT_PROMPTS.md`
  - the next prompts worth preparing or sending

#### `artifacts/`

Reviewable outputs produced by Lite workflows.

Examples:

- summaries
- extracted thread cards
- review packets
- prompt packets

These should remain explicit artifacts, not hidden state.

#### `src/matylda_lite/`

Small local implementation code for Lite utilities.

This should stay narrow and support the file-based workflow rather than trying
to recreate Full.

## Core Objects

### Thread Card

The Thread Card is the main durable unit in the Library.

Fields:

- `title`: short human-readable name for the thread
- `domain`: broad category such as research, writing, product, admin, or personal
- `status`: current state such as active, parked, archived, working, or canonical
- `value`: why this thread matters or how valuable it is to preserve
- `risk`: main caution, uncertainty, or failure mode
- `source`: where the thread came from
- `current state`: concise summary of where the thread stands now
- `next artifact`: the next useful output to produce
- `next action`: the next concrete step to take
- `review required`: whether human review is required before acting on it
- `last updated`: last meaningful update date

### Desk Item

The Desk Item is the working form of a thread while it is active.

Fields:

- `thread`: reference to the related Thread Card
- `reason active`: why this thread is on the Desk now
- `current blocker`: what is currently preventing progress
- `next action`: the next concrete step
- `deadline, if any`: optional deadline or review date

### Memory Candidate

The Memory Candidate is a weak, reviewable memory record, not established truth.

Fields:

- `claim`: the possible durable memory to preserve
- `source`: where that claim came from
- `stability`: how likely it is to remain true over time
- `usefulness`: how valuable it is for future continuity
- `sensitivity`: how risky or delicate it is to preserve
- `review status`: whether it is pending review, reviewed, rejected, or approved
- `promotion decision`: whether it stays candidate, is promoted, or is rejected

### Decision Log Entry

The Decision Log Entry records meaningful choices and prevents rediscovery loops.

Fields:

- `date`: when the decision was made
- `decision`: the decision itself
- `reason`: why it was made
- `alternatives rejected`: what was considered and not chosen
- `source`: what note, thread, or artifact grounded the decision
- `review required`: whether further review is required before treating it as settled

### Prompt Queue Item

The Prompt Queue Item is the unit used to prepare the next useful external or
internal prompt.

Fields:

- `target`: `Codex` / `Claude` / `ChatGPT` / `Gustaw` / `Perplexity`
- `task`: what the prompt is asking for
- `context`: the minimum context required
- `constraints`: limits, cautions, and rules for the prompt
- `expected output`: what form of result is wanted
- `status`: queued, prepared, sent, done, blocked, or archived

## v0.1 Features

Include only:

1. Capture raw notes into `inbox/`.
2. Convert raw notes into Thread Cards.
3. Maintain an active Desk with a maximum of 3-5 active threads.
4. Maintain a Parking Lot for valuable but inactive work.
5. Maintain a Decision Log.
6. Maintain a Prompt Queue.
7. Run a weekly Desk review.
8. Support manual-only memory promotion.

## v0.1 Safety Rules

- human approval before changing source files
- no automatic promotion to memory
- no autonomous background tasks
- no legal advice automation
- no destructive operations
- all generated artifacts must be reviewable

## v0.1 Operating Rule

Matylda Lite v0.1 should be useful even if it is only:

- folders
- markdown files
- small deterministic helpers
- explicit review artifacts

If a proposed feature requires a backend, a live loop, heavy model orchestration,
or unsupervised execution, it is outside the intended scope of Lite v0.1.
