# Matylda Lite Memory Policy v0.1

## Purpose

This policy prevents Matylda Lite from confusing raw notes, thread cards,
decisions, and durable memory.

Matylda Lite is a local organizational system, not an automatic remembering
machine. Without a strict memory policy, the system will start treating every
captured thought as durable context, every repeated phrase as identity, and
every saved note as truth. This document exists to stop that drift.

## Core Principle

Matylda Lite does not remember automatically.
It records candidates, evidence, and decisions for human review.

## Memory Is Not One Thing

Matylda Lite distinguishes the following:

### 1. Raw notes

Raw notes are temporary captures.

They may contain useful fragments, but they are not durable memory, not
authority, and not stable context.

### 2. Thread cards

Thread cards are durable project or topic records.

They are structured addresses for important work. They preserve context and
state, but they are not automatically memory claims.

### 3. Active desk items

Active desk items are current working memory.

They show what matters now, not what should be trusted indefinitely.

### 4. Parked threads

Parked threads are preserved but inactive context.

They remain valuable, but they are not currently driving action.

### 5. Decision log entries

Decision log entries are explicit settled choices.

They carry more authority than raw notes and usually more than thread summaries,
because they record an intentional decision with reasons and rejected
alternatives.

### 6. Source-of-truth documents

Source-of-truth documents are the current governing references for a topic,
project, or operating rule.

They outrank casual notes and prompt context.

### 7. Memory candidates

Memory candidates are proposed durable claims, preferences, constraints,
project facts, or recurring patterns that may be useful later but have not yet
been promoted.

### 8. Durable memory

Durable memory is reviewed, promoted context that is considered stable enough to
reuse.

Even durable memory should remain reviewable, revisable, and subordinate to
newer explicit decisions and source-of-truth material.

## Storage Locations

Memory-like objects map to the current Lite files like this:

- raw notes: `inbox/raw_notes.md`
- thread cards: `library/threads/`
- thread index: `library/THREAD_INDEX.md`
- active working memory: `desk/ACTIVE_THREADS.md`
- parked memory: `desk/PARKING_LOT.md`
- decisions: `desk/DECISION_LOG.md`
- prompt context: `prompts/NEXT_PROMPTS.md`
- candidate memory template: `templates/MEMORY_CANDIDATE_TEMPLATE.md`
- future candidate memory location: `library/memory_candidates/`

`library/memory_candidates/` is proposed for later use only.
It should not be created automatically as part of this policy.

## Memory Candidate

A memory candidate is:

A proposed durable claim, preference, constraint, project fact, or recurring
pattern that may be useful in future work but has not yet been promoted.

Fields:

- claim
- source
- evidence
- stability
- usefulness
- sensitivity
- risk
- review status
- promotion decision
- last reviewed

## Candidate Statuses

Memory candidates may use these statuses:

- `proposed`
- `needs-evidence`
- `accepted`
- `rejected`
- `superseded`
- `expired`

## Stability Levels

Use these stability levels:

- `temporary`
  - likely useful only for the current phase or conversation
- `project-bound`
  - valid within one project or thread, but not beyond it
- `durable`
  - stable enough to be useful over time across repeated work
- `identity-level`
  - persistent enough to shape how the system treats the user's enduring
    preferences or operating posture

`identity-level` memory should be rare.
It should require especially careful human review.

## Usefulness Levels

Use these usefulness levels:

- `low`
- `medium`
- `high`
- `strategic`

## Sensitivity Levels

Use these sensitivity levels:

- `public`
- `internal`
- `personal`
- `sensitive`

Sensitive material requires explicit human review before any durable use.

## Promotion Rules

A candidate may be promoted only if:

- it is useful beyond the current conversation
- it has stable or project-bound relevance
- it has a clear source
- it is not merely a raw thought
- it does not overstate uncertainty
- it has been manually reviewed

A candidate must not be promoted if:

- it is speculative
- it is emotional noise
- it is outdated
- it is contradicted by a newer decision
- it is sensitive and not explicitly approved
- it is only interesting but not useful

## Demotion and Revision

Memory is not permanent by default.

Memory can be:

- revised
- superseded
- expired
- archived
- contradicted by newer source-of-truth material

No memory claim is irreversible.

## Source-of-Truth Discipline

Use this precedence order:

1. Explicit user decision in `desk/DECISION_LOG.md`
2. Current source-of-truth document
3. Current thread card
4. Usage/memory policy docs
5. Prompt queue context
6. Parking lot note
7. Raw inbox note

Raw notes never override decisions.

If a raw note conflicts with a decision or a reviewed source-of-truth document,
the raw note loses.

## Examples

### Good memory candidate

Claim: Matylda Lite v0.1 is file-based and non-autonomous.

Reason: explicit design decision.

Likely status: `accepted`.

### Bad memory candidate

Claim: Every interesting AI news item should become a Lite thread.

Reason: would create thread sprawl.

Likely status: `rejected`.

### Project-bound memory

Claim: Active desk should contain only 3-5 threads.

Reason: usage protocol and decision log.

Likely status: `accepted`.

### Durable operating memory

Claim: Matylda Full is treated as a quarry, not a runnable target.

Reason: repeated explicit architectural decision.

Likely status: `accepted`.

### Needs-evidence candidate

Claim: Paper X attractor-switch framing is the best unifying FTAR endpoint map.

Reason: promising, but still speculative and not yet sufficiently grounded.

Likely status: `needs-evidence`.

### Rejected noise candidate

Claim: A frustrating day means the whole current thread set should be abandoned.

Reason: emotional state is not the same thing as durable project truth.

Likely status: `rejected`.

### Superseded memory

Claim: Dom nr 2 should stay active on the desk this week.

Reason: if a later weekly review parks it, the older claim becomes superseded.

Likely status: `superseded`.

### Sensitive/personal memory

Claims about private preferences, personal identity, health, finances, or
highly sensitive household matters require explicit user approval before
becoming durable.

Likely status without approval: `proposed` or `rejected`, not `accepted`.

## Review Procedure

Manual review procedure:

1. Collect candidates.
2. Check source.
3. Check stability.
4. Check usefulness.
5. Check sensitivity.
6. Decide: accept, reject, revise, or defer.
7. Record decision.

## Monthly Memory Review

Checklist:

- remove expired candidates
- identify superseded claims
- check whether active decisions still hold
- archive stale project facts
- promote only reviewed candidates

## Non-Autonomy Rules

- no automatic memory promotion
- no hidden memory writes
- no background memory review
- no autonomous identity changes
- no silent source-of-truth rewrites
- no treating generated text as truth without review

## First Candidate Memory Set

Suggested initial candidates, without creating files yet:

1. Matylda Lite v0.1 is file-based and non-autonomous.
2. Matylda Full is treated as a quarry, not a runnable target.
3. Active desk is limited to 3-5 threads.
4. Memory promotion is manual-only.
5. Raw notes are not durable memory.
6. Thread cards are durable project records, not automatically memory.
7. Decisions override raw notes.
8. Parking is preservation, not failure.

## Done Criteria

The policy is done when it:

- distinguishes raw notes, thread cards, decisions, and memory
- defines candidate memory
- defines promotion and rejection rules
- defines source-of-truth precedence
- defines sensitivity review
- reinforces non-autonomy
