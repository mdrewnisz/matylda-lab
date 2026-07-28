# Matylda Lab Charter

## Direction

Matylda Lab is a local workspace for positive, disciplined creativity. Its
default is to help a user generate, combine, clarify, and test possibilities.
DARKROOM is a proportional review instrument, not the voice of the whole
system.

The former Lite v0.1 documents remain historical records of the original
file-based organizer. They are not the current product boundary.

## Hypothesis Lifecycle

```text
seed -> incubator -> exploration -> working model -> waiting room -> cemetery
                                      |                |               |
                                      +---- evidence --+---- revival ---+
```

- **Seed**: a prompt, intuition, or connection. It is welcome without a demand
  for immediate proof.
- **Incubator**: an observation, strange analogy, or question that may matter
  but has not yet earned exploration time. It records the spark without
  prematurely turning it into a project.
- **Exploration**: Matylda develops variants, counterexamples, questions, and
  possible tests. Critique is specific and does not close the search.
- **Working model**: an explicit explanatory candidate with a stated scope,
  assumptions, and next test. It can guide current work, but is not treated as
  settled fact or necessarily as a claim about the world.
- **Waiting room**: a hypothesis is interesting but lacks evidence, a test, or
  present relevance. It is preserved with a re-entry condition and does not
  occupy active attention.
- **Cemetery**: a hypothesis is retired after a failed decisive test, an
  explicit user decision, or repeated non-productivity. It remains searchable
  with its reason for retirement and can be revived only by new evidence or a
  changed premise.

## Product Rules

1. Default chat is constructive. It names uncertainty when useful, but does
   not append global historical criticism to every answer.
2. DARKROOM receives the current task and may inject at most three relevant
   tensions. Global tension history remains visible in the audit UI.
3. Entry into the waiting room is a user-visible, reversible state transition.
   Required fields: hypothesis, current evidence, missing test, expected
   exploration cost, re-entry condition, and review date.
4. Entry into the cemetery requires an explicit reason and a link to the test,
   decision, or repeated-review record. It is never an automatic deletion.
5. Revival creates a new working pass linked to the retired record; it does not
   rewrite history.
6. Focus Mode surfaces at most seven waiting-room items. The full waiting room
   remains searchable, but does not become a second active desk.
7. Expected exploration cost is categorical: `5 min`, `30 min`, `half day`,
   `2 days`, `experiment`, or `new capability`. Matylda should prefer the
   smallest informative next step, not the grandest possible investigation.
8. A new lifecycle state requires a repeated practical problem that cannot be
   represented by an existing state plus metadata. Otherwise use a field, tag,
   or transition condition instead of growing the state machine.

## Implementation Plan

### Phase 1: De-escalate review

- Scope DARKROOM prompt injection and epistemic limitation mode to the current
  task.
- Cap injected tensions at three and keep the global registry audit-only.
- Add a visible distinction between constructive chat and explicit NO-GO review.

### Phase 2: Add hypothesis records

- Add a local `data/hypotheses.json` registry with stable IDs and the six
  lifecycle states. It is intentionally ignored by Git: it is working research
  state, not a published conclusion.
- Record explanatory candidate, scope, assumptions, next test, and expected
  exploration cost without demanding that every record be a factual claim.
- Provide create, move, inspect, and revive operations through the local API.
- Keep state transitions explicit and logged; no autonomous promotion or burial.

### Phase 3: Waiting room

- Add a waiting-room view sorted by review date and re-entry condition.
- Surface at most seven due hypotheses in briefing and Focus Mode.
- Permit a user to reactivate a hypothesis directly from its record.

### Phase 4: Cemetery and learning

- Add a cemetery view with retirement reason, decisive evidence, and links to
  successor hypotheses.
- Let DARKROOM suggest a transition, but require user confirmation.
- Use cemetery records as bounded negative evidence for similar work, never as
  a blanket ban on exploration.

## Acceptance Checks

For each phase, verify:

1. A constructive prompt can receive a useful answer without epistemic-limit
   boilerplate when it has no relevant tension.
2. A related, high-severity tension still activates a proportionate warning.
3. A hypothesis can move to waiting room and cemetery without losing its source
   or its path back to active work.
4. Focus Mode never surfaces more than seven waiting-room records at once.
5. The system can rank equivalent next tests by lower expected exploration cost.
6. No lifecycle transition silently changes a user decision or deletes content.
7. A proposed new state must cite the observed recurring problem it solves.
