# What to Drop or Defer from Matylda Full

## Summary

Matylda Lite must remain narrow because its value is not "doing everything
Matylda Full does on a smaller machine." Its value is preserving, organizing,
classifying, and reactivating valuable threads without turning that layer into a
runtime platform.

Lite must remain non-autonomous because the user's stated need is continuity,
auditability, and safe activation of context, not independent execution. The
moment Lite inherits backend state engines, routing layers, research execution
lanes, or self-expanding helper logic, it stops being a desk and becomes a
partial reimplementation of Full.

The governing rule for v0.1 is:

- keep the file-based organizational spine
- drop the service platform
- defer only the parts that can later be added without changing Lite's
  review-first character

## Drop from Lite v0.1

### Core v1 Backend

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/backend/core-v1/*`
- Why not in Lite:
  - this is a backend-first state engine with PostgreSQL, Prisma, Docker,
    guarded writes, and auditable session lifecycle machinery
  - Lite is supposed to be local, simple, and mostly markdown/file-based
- Risk if included:
  - Lite turns into a backend migration project
  - setup and maintenance burden explode immediately
  - the user gets platform complexity instead of a usable desk layer
- Future condition for reconsideration:
  - only if Lite's file-based layer proves insufficient and there is a clear,
    reviewed need for durable structured state beyond local files

### Backend-Coupled Workbenches

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/project_workbench.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/session_workbench.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/decisions_constraints.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/memory_review.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/core_v1_client.py`
- Why not in Lite:
  - these modules mostly exist to talk to the backend and assemble backend state
  - Lite should be able to function without any API or database
- Risk if included:
  - hidden dependence on Full's runtime path
  - pressure to make Full operational just to use Lite
  - loss of portability and audit simplicity
- Future condition for reconsideration:
  - if Lite later gets a strictly optional read-only adapter layer over an
    external source, not as its primary storage model

### Execution Routing And Task Budget Layer

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/execution/*`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/EXECUTION_BUDGET_POLICY.md`
- Why not in Lite:
  - executor kinds, routing decisions, task budgets, and handoff targets belong
    to a workflow engine
  - Lite is not supposed to choose or manage execution
- Risk if included:
  - Lite drifts toward autonomous or semi-autonomous orchestration
  - design effort shifts from organization to runtime control
- Future condition for reconsideration:
  - only if Lite later needs a tiny, explicit review contract for manual packet
    generation, not executor routing

### Research Runtime Lanes

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/research/*`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/paper_red_team.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/claim_support_map.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/revision_plan.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/submission_package.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/playbooks/research/*`
- Why not in Lite:
  - these are domain-specific execution surfaces for bounded research work
  - Lite should preserve and prepare context, not run specialized workflows
- Risk if included:
  - domain creep
  - heavier model/runtime expectations
  - confusing Lite's purpose as an organizational layer
- Future condition for reconsideration:
  - only if one small review-only packet format is extracted later without
    bringing over the underlying research runtime

### Knowledge Base Runtime

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/knowledge_base/*`
- Why not in Lite:
  - this is a larger structured runtime seam for compiled working knowledge and
    answer-pack assembly
  - Lite can start with curated folders, statuses, and reviewable notes
- Risk if included:
  - premature abstraction
  - a second-system effect before the basic library conventions are stable
- Future condition for reconsideration:
  - if the file-based library grows large enough that a minimal indexing or
    linting layer is clearly justified

### Model Routing, Benchmarking, And Shadow Evaluation

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/governance/model_router.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/governance/model_advisor.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/governance/shadow_evaluator.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/MODEL_*`
- Why not in Lite:
  - Lite does not need multi-model optimization, benchmark packets, or routing
    heuristics to organize threads and prompts
- Risk if included:
  - unnecessary compute and telemetry complexity
  - implicit pressure toward automated model selection
  - platform concerns overshadowing user-facing utility
- Future condition for reconsideration:
  - no earlier than a stage where Lite already has a stable manual workflow and
    optional model use needs comparison

### Dashboard, CLI, And Operator Console Surfaces

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/interface/*`
- Why not in Lite:
  - these surfaces summarize backend-backed runtime state and operator flows
  - Lite should first prove its information model in files, not in UI shells
- Risk if included:
  - frontend work starts before the underlying conventions are solid
  - interface polish masks unresolved data-model decisions
- Future condition for reconsideration:
  - after the file-based desk and library model are stable and worth rendering

### Cognition / Major / Legacy Advisory Layers

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/cognition/*`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/major/*`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/MAJOR_*`
- Why not in Lite:
  - these layers belong to a broader advisory or experimental architecture
  - Lite needs explicitness and auditability more than advisory sophistication
- Risk if included:
  - unclear authority
  - conceptual sprawl
  - time spent preserving legacy semantics instead of building a narrow tool
- Future condition for reconsideration:
  - only if a very small, review-only advisory pattern proves repeatedly useful
    in the file-based Lite workflow

### Self Evolution / Mutation Review Lane

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/self/evolution/*`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/governance/SELF_MUTATION_ADOPTION_POLICY.md`
- Why not in Lite:
  - even in bounded form, this is about mutation evidence, rollback, and
    self-change review
  - Lite's mission is preserving and activating context, not reasoning about
    changing itself
- Risk if included:
  - self-expansion pressure
  - confusion between reflective review and self-modification
- Future condition for reconsideration:
  - only if Lite later needs explicit review packets for template changes, and
    even then without any auto-apply path

### Legal Runtime Scaffolding

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/legal/*`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/playbooks/legal/*`
- Why not in Lite:
  - the Full repo itself treats Legal as conservative scaffolding only
  - Lite should stay away from high-stakes domain automation entirely
- Risk if included:
  - false impression of legal capability
  - safety and trust problems from overstated scope
- Future condition for reconsideration:
  - none for Lite as currently defined

## Defer to Later

### Handoff Packet Format

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/HANDOFF_FORMAT_NOTE.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/execution/handoff.py`
- Why not now:
  - the idea of explicit handoff is good, but the current Full shape is tied to
    workflow and execution vocabulary
- Risk if included now:
  - Lite inherits orchestration semantics before it needs them
- Future condition for reconsideration:
  - when Lite needs a small markdown-first review packet between desk review and
    prompt prep

### Memory Evidence Views

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/layer.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/memory/README.md`
- Why not now:
  - the continuity and bootstrap views are useful, but the current
    implementation is broader and partially coupled to other subsystems
- Risk if included now:
  - too much read-model complexity before Lite's raw file conventions exist
- Future condition for reconsideration:
  - after candidate memory, project packs, and library statuses are stable

### Project Registry

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/docs/architecture/PROJECT_REGISTRY_CONTRACT_V0_1.md`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/data/projects/registry.json`
- Why not now:
  - Lite likely needs an index, but not a large proto-OS registry contract
- Risk if included now:
  - over-design at the very top of the stack
- Future condition for reconsideration:
  - when there are enough projects/threads that a small index file becomes
    necessary

### Optional Local Model Helper Layer

- Source path:
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/local_runtime_adapter.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/integrations/local_ollama.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/secretary_v0.py`
  - `2026-04-18-czy-mog-cie-podpi-pod-m/Matylda-review/src/matylda/os/sleeping_matylda_v0.py`
- Why not now:
  - Lite should remain useful even with zero local inference runtime
- Risk if included now:
  - the product starts depending on heavy local reasoning before the manual
    workflow is proven
- Future condition for reconsideration:
  - after the Secretary and Sleeping Matylda packet formats are already useful
    in manual mode

## Explicit Non-Goals

Lite must not do the following:

- no autonomous execution
- no heavy local LLM reasoning
- no full backend migration
- no live agent loop
- no legal-domain automation
- no automatic memory promotion
- no unsupervised file edits
- no self-expansion

More concretely, Lite must also avoid:

- no hidden scheduling, daemons, or watchers
- no automatic write-back into canonical files
- no silent authority changes from working note to canonical reference
- no model-routing or benchmark-governance platform
- no backend-first session lifecycle
- no research workflow engine disguised as organization tooling
- no self-modification or self-directed repo maintenance

## Narrowness Rule

If a proposed Lite feature requires any of the following, it should be dropped
or postponed by default:

- a running backend or database
- executor routing or workflow dispatch
- premium or heavy local model dependence
- unsupervised writes
- cross-domain authority claims
- background loops
- silent promotion into memory or truth
