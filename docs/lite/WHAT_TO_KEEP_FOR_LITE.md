# What to Keep for Matylda Lite

## Summary

The strongest Lite candidates are not the heavy runtime layers. They are the
repository's explicit discipline around project context, source-of-truth
classification, review-first memory, manual bounded helper roles, and
artifact-first handoff.

The most reusable Full assets for Lite are:

- the project document pack and its templates
- source-of-truth and library classification rules
- candidate-memory and promotion governance
- no-autonomy / no-hidden-scheduling / review-required policies
- bounded Secretary and Sleeping Matylda role concepts

The least reusable assets are backend-coupled workbenches, research execution
lanes, model-routing logic, and dashboard/operator runtime surfaces.

## Keep as Core

### Project Document Pack Standard

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/PROJECT_DOCUMENT_PACK_STANDARD.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/templates/projects/*`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/projects/MATYLDA/*`
- Type: doc / template / concept
- Why it matters for Lite:
  - Lite's main problem is preserving project and thread context without drift.
    The project-pack standard already defines a disciplined, markdown-first
    structure for that.
- Proposed Lite role:
  - become the default Lite project/thread desk pack:
    `PROJECT_CONTEXT.md`, `CURRENT_STATUS.md`, `NEXT_STEPS.md`,
    `DECISIONS_LOG.md`, `SOURCES_OF_TRUTH.md`, plus a renamed `AGENTS.md`
    variant if needed
- Adaptation required:
  - simplify from "workspace pack for proto-OS" to "local desk pack for active
    threads and projects"
  - likely rename `AGENTS.md` to something less agentic such as
    `OPERATING_RULES.md` or `ROLE_RULES.md`
- Risk:
  - medium risk of carrying too much Full terminology if copied verbatim
- Priority: P0

### Source-Of-Truth Discipline

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/SOURCE_OF_TRUTH_MAP.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/projects/MATYLDA/SOURCES_OF_TRUTH.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/projects/ftar/SOURCES_OF_TRUTH.md`
- Type: doc / policy / concept
- Why it matters for Lite:
  - Lite is meant to preserve valuable threads without losing the "which file
    wins?" question. This is one of the clearest mature ideas in Full.
- Proposed Lite role:
  - make source hierarchy explicit per project, thread, or document library
- Adaptation required:
  - replace repo-architecture language with thread/document/library language
  - support "canonical", "working", and "archive" at the note/library level
- Risk:
  - low
- Priority: P0

### Artifact Status And Review Posture

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/ARTIFACT_STATUS_POLICY.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/MEMORY_PROMOTION_POLICY.md`
- Type: policy
- Why it matters for Lite:
  - Lite needs auditable states for notes, prompts, summaries, and candidate
    memories. Full already distinguishes `working`, `canonical`, and
    `archival`, and blocks silent promotion.
- Proposed Lite role:
  - define lifecycle labels for notes, prompts, thread summaries, and memory
    candidates
- Adaptation required:
  - remove backend/runtime wording
  - keep the rules:
    nothing becomes canonical automatically, and review stays visible
- Risk:
  - low
- Priority: P0

### Candidate Memory Contract

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/MEMORY_LAYER_V0_1.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/contracts.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/scoring.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/promotion.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/tests/memory/test_candidate_memory_contract.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/tests/memory/test_memory_promotion.py`
- Type: doc / module / test
- Why it matters for Lite:
  - this is one of the cleanest deterministic and dependency-light code paths
    in Full. It maps directly onto "candidate memory" and "review before
    promotion".
- Proposed Lite role:
  - become the first memory subsystem in Lite:
    file-backed candidate memory items, deterministic scoring, explicit review
    queue
- Adaptation required:
  - store candidates in markdown or JSON files instead of backend-backed flows
  - narrow kinds toward user preference, project fact, procedural lesson,
    domain constraint, and temporary context
- Risk:
  - low
- Priority: P0

### Local Library Classification Pattern

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/projects/ftar/documents/README.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/projects/ftar/documents/LOCAL_LIBRARY_STATUS.md`
- Type: doc / concept
- Why it matters for Lite:
  - Lite is explicitly a library and desk. The FTAR local library pattern shows
    how imported material can be curated into "local canonical" versus
    "working library only" without pretending everything is truth.
- Proposed Lite role:
  - document-library policy for saved threads, prompt packs, reports, and
    imported files
- Adaptation required:
  - generalize from FTAR research papers to arbitrary thread/document archives
- Risk:
  - low
- Priority: P0

### Secretary v0

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/LOCAL_LIGHTWEIGHT_RUNTIME_V0.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/secretary_v0.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/projects/MATYLDA/AGENTS.md`
- Type: concept / module / role
- Why it matters for Lite:
  - the user's stated target includes "secretary", desk review, and prompt
    preparation. Secretary v0 is already framed as bounded, local-first,
    summary-oriented, and non-authoritative.
- Proposed Lite role:
  - a manual assistant that helps turn notes into:
    summary, state update, decisions noted, open items, and suggested log entry
- Adaptation required:
  - remove dependence on local LLM runtime as a default assumption
  - preserve the input/output contract, but allow fully manual use first
- Risk:
  - medium because current implementation assumes a local backend adapter
- Priority: P0

### Sleeping Matylda v0

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/LOCAL_LIGHTWEIGHT_RUNTIME_V0.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/SELF_DEVELOPMENT_DOMAIN.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/sleeping_matylda_v0.py`
- Type: concept / module / policy
- Why it matters for Lite:
  - the user's use case is overloaded thread continuity. The "bounded
    reflective standby" idea is a good match if it stays proposal-only.
- Proposed Lite role:
  - optional reflective note builder:
    open threads, tensions, next questions, possible next steps
- Adaptation required:
  - keep it explicitly manual and non-autonomous
  - treat it as a prompting or review mode, not a background role
- Risk:
  - medium because the name and history can invite autonomy drift if not framed
    carefully
- Priority: P1

### No-Autonomy / Manual Review Boundary Set

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/DOMAIN_AUTONOMY_POLICY.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/PERMISSIONS_AND_SANDBOX_POSTURE.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/SELF_DEVELOPMENT_DOMAIN.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/ARCHITECTURE_STATUS.md`
- Type: governance / architecture / policy
- Why it matters for Lite:
  - these documents encode the exact safety posture the user asked for:
    no hidden scheduling, no autonomous execution, visible review gates, and
    bounded local operation.
- Proposed Lite role:
  - Lite constitutional rules
- Adaptation required:
  - compress into a short Lite operating charter
  - remove domain complexity that only exists for Full
- Risk:
  - low
- Priority: P0

## Keep as Inspiration

### Handoff Artifact Format

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/HANDOFF_FORMAT_NOTE.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/execution/handoff.py`
- Type: doc / module / concept
- Why it matters for Lite:
  - explicit handoff is valuable for passing a thread, review packet, or prompt
    bundle between human review steps.
- Proposed Lite role:
  - file-based transfer packet between "desk review" and "prompt prep"
- Adaptation required:
  - remove execution-layer terminology and target-role assumptions
  - simplify into a markdown-first packet
- Risk:
  - medium because current form is tied to workflow/execution vocabulary
- Priority: P1

### Memory Evidence Views

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/layer.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/README.md`
- Type: module / concept
- Why it matters for Lite:
  - bootstrap, session continuity, and project continuity are very relevant to
    thread preservation.
- Proposed Lite role:
  - future read-model over file-backed notes and memory candidates
- Adaptation required:
  - decouple from research continuity imports and backend evidence rows
- Risk:
  - medium because current implementation is broader and partially coupled
- Priority: P1

### Project Registry Contract

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/PROJECT_REGISTRY_CONTRACT_V0_1.md`
- Type: doc / concept
- Why it matters for Lite:
  - a registry can become the top-level index for projects and threads.
- Proposed Lite role:
  - simple `projects/index.yaml` or `threads/index.yaml`
- Adaptation required:
  - drastically simplify fields and remove proto-OS assumptions
- Risk:
  - medium because the current contract is larger than Lite needs
- Priority: P1

## Candidate Future Modules

### Secretary Input/Output Schema

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/secretary_v0.py`
- Type: module / concept
- Why it matters for Lite:
  - even without local inference, the schema is useful for prompt assembly and
    structured desk review.
- Proposed Lite role:
  - stable secretary packet format
- Adaptation required:
  - split pure schema from runtime invocation
- Risk:
  - low
- Priority: P2

### Sleeping Matylda Review Schema

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/sleeping_matylda_v0.py`
- Type: module / concept
- Why it matters for Lite:
  - can support "open thread review" and "next questions" generation later.
- Proposed Lite role:
  - reflective review packet format
- Adaptation required:
  - keep proposal-only and manual-only
- Risk:
  - medium
- Priority: P2

### Project Workbench Summary Shape

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/project_workbench.py`
- Type: module / concept
- Why it matters for Lite:
  - useful as a future read-only dashboard shape for counts and review queues.
- Proposed Lite role:
  - static summary view over files
- Adaptation required:
  - replace all backend calls with filesystem scans
- Risk:
  - high because current implementation is backend-dependent
- Priority: P2

## Immediate Extraction Candidates

- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/templates/projects/CURRENT_STATUS.md`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/templates/projects/SOURCES_OF_TRUTH.md`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/templates/projects/DECISIONS_LOG.md`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/ARTIFACT_STATUS_POLICY.md`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/MEMORY_PROMOTION_POLICY.md`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/MEMORY_LAYER_V0_1.md`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/contracts.py`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/scoring.py`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/promotion.py`
- `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/projects/ftar/documents/LOCAL_LIBRARY_STATUS.md`
