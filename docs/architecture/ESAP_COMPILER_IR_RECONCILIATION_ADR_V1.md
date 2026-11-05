# Canonical CompilerIR Reconciliation ADR — FS-00 Remediation A3

**ADR ID:** ESAP-ADR-FS00-003  
**Status:** APPROVED BY USER — IMPLEMENTATION IN PROGRESS  
**Target contract:** D07 + D2–D4 refinement in `folder/CONTRACT_CanonicalCompilerIR.md`  
**Current implementation:** `compiler/core/plan.py:CompilationPlan` and `compiler/core/lowering.py:isr_to_plan`  
**Related:** ESAP Authority Reconciliation; FS-00 Checkpoints 9–15  
**Change boundary:** design only; no runtime or certification changes.

---

## 1. Decision required

D07 already states that `CompilationPlan` is a stabilization implementation and is not the final canonical CompilerIR. The D2–D4 refinement explicitly identifies missing identity, provenance, schema and backend-constraint fields, and schedules a future canonical module.

The current `CompilationPlan` is valuable and should be preserved. It is frozen, typed and carries important behavioral contracts, including APIs, effects, effect bindings, consequences, invariants and frontend routes/interactions. But it is not a complete canonical CompilerIR and must not be promoted by renaming alone.

**Proposed decision:** implement one canonical, versioned `CompilerIR` as the authoritative technology-neutral representation between `ISRRevision` and backend lowering. Retain `CompilationPlan` as a transitional backend execution plan / lowering adapter until each backend consumes the canonical CompilerIR directly or through a versioned, loss-aware adapter.

This preserves the current behavioral work while separating the system's authoritative semantic compilation record from a backend-facing projection.

## 2. Observed gaps in CompilationPlan and isr_to_plan

### 2.1 Identity and lineage

| D07 / refinement requirement | Current `CompilationPlan` | Assessment |
|---|---|---|
| Compilation ID | `plan_id` | Present but generated as `plan:{first 16 chars of ISR hash}`; not a full canonical IR content identity |
| Own content hash | Absent | Missing |
| Schema version | Absent | Missing |
| Source ISR revision content hash | `isr_id` is populated with `revision.system_id`; `plan_id` embeds only a 16-character hash prefix | Missing as explicit, full source reference |
| Source ArchitectureCandidate content hash | Absent | Missing |
| Lowering operator/timestamp/chain | Absent | Missing |
| Provenance | Absent | Missing |
| Deterministic canonical serialization | No canonical serialization method on the plan | Missing |

The full ISR hash can be recovered only indirectly from the derivation of `plan_id`; that is not an explicit typed reference and is not a substitute for a full digest.

### 2.2 Semantic coverage and silent projection gaps

The current `isr_to_plan` implementation creates plan carriers for services, data models, events, security policies, APIs, effects, invariants, consequences, frontend routes and frontend interactions. It does not carry all ISR semantic surfaces.

Observed examples:
- `REQUIREMENT_REF` nodes and source requirement metadata are not represented in `CompilationPlan`.
- `SATISFIES` and the requirement relationship edges are not represented in the plan, so requirement realization and requirement-to-requirement lineage are not preserved there.
- `DOMAIN`, `CAPABILITY` and `INFRASTRUCTURE_TARGET` nodes are not represented as plan fields.
- `IMPLEMENTED_BY` and general `DEPENDS_ON` relationships are not represented as first-class plan relationships.
- D07 target requirements, backend constraints and required capability declarations are absent.
- Data-flow, deployment and observability requirements are not first-class plan fields.
- Frontend interactions with anything other than exactly one target API receive `target_api_operation=None`; missing route API IDs are filtered from the emitted list. Those conditions are not uniformly raised as blocking projection errors.
- An API with no explicit `EXPOSES` service binding receives `service_id=None`; only multiple distinct service bindings are rejected.

These are not claims that every such case is valid or invalid in all contexts. They identify where the current plan does not preserve the full ISR surface or does not make the loss an explicit blocker.

### 2.3 Current strength to retain

The current plan/lowering path does preserve valuable typed semantics:
- API behavior and explicit service binding when present;
- security-policy bindings;
- typed data-model, service, event and effect behavior;
- source-bound `CAUSES_EFFECT` relationships;
- explicit consequences and their effect/invariant targets;
- frontend route and interaction payloads for the supported cases;
- explicit rejection of selected ambiguous API ownership, unresolved effect/consequence links and unbound consequences.

The new canonical IR should absorb and generalize this work, not replace it with weaker string labels or a smaller DTO.

## 3. Proposed architecture

```text
ISRRevision
   |
   | canonical, versioned, loss-aware lowering
   v
Canonical CompilerIR (D07, versioned and content-addressed)
   |
   | target-specific capability negotiation
   v
Backend Lowering Adapter
   |
   | explicit supported-subset check + loss report
   v
CompilationPlan (transitional execution plan, where needed)
   |
   v
CompilerBackend → quarantined ArtifactSet
```

Rules:
1. Canonical CompilerIR is the authoritative compiler input for all compiler families after migration.
2. `CompilationPlan` remains a downstream execution plan, not a second authority.
3. An adapter may project a supported subset only when every omitted field/relationship is explicitly classified as not required for the selected target. If a required semantic is omitted, compilation blocks.
4. Backend capability declarations are checked against the canonical CompilerIR obligations before adapter projection.
5. No compiler route may construct a parallel CompilerIR from a different RequirementGraph/ISR model without an approved source adapter.
6. The compiler must retain an immutable mapping report from ISR IDs/edges/requirements to CompilerIR IDs/fields and then to backend-plan/artifact IDs.

## 4. Proposed canonical CompilerIR contract

The canonical CompilerIR should include the D07 refined identity/provenance surface and the complete typed semantic payload needed by the current ISR. The exact Pydantic/serialization shape is implementation work; this table defines required semantic groups.

| Group | Required content |
|---|---|
| Identity | compilation ID, schema version, canonical content hash |
| Source lineage | full source ISR revision ID and content hash; optional ArchitectureCandidate hash only where the route has no candidate, with explicit reason/state |
| Requirement obligations | source requirement IDs, priority, acceptance criteria, review/approval state, preserved requirement relationships and explicit realization links |
| Architecture | domains, capabilities, services, components/responsibilities and explicit dependencies |
| Interfaces | typed API operations, request/response/error contracts, explicit service ownership and security bindings |
| Data | typed models, constraints, persistence requirements and data-flow relationships |
| Events | typed event schemas, producers/consumers, delivery/ordering obligations where declared |
| Security | policies, principals/roles, actions, resources, conditions, operation/service bindings and required enforcement points |
| Behavior | rules, expressions, invariants, state transitions, effects, effect bindings and observable consequences |
| Frontend | routes, interactions, route-to-API and interaction-to-operation bindings, authorization and validation obligations |
| Deployment/operations | technology-neutral infrastructure targets, availability/performance/reliability/observability and operational constraints |
| Backend negotiation | required semantic capabilities, compatible backend constraints, unsupported/unknown semantic list |
| Lowering provenance | adapter ID/version, source and output hashes, lowering chain, toolchain/implementation digest, timestamp |
| Loss and diagnostics | preserved/normalized/deferred/rejected IDs and fields; unresolved/ambiguous references; blocking diagnostics |
| Serialization | deterministic canonical serialization and a separately specified revision/evidence envelope |

A nullable ArchitectureCandidate reference must not be mistaken for an unbound reference. The IR must distinguish `NOT_APPLICABLE` (a route legitimately does not use an ArchitectureCandidate) from `MISSING` (a required reference was not supplied).

## 5. Migration strategy

### Stage A3.1 — contract and schema

- Add a canonical CompilerIR contract module under `compiler/core` only after D07 is reconciled with this proposal.
- Version the schema; define canonical serialization, content hash and provenance envelope.
- Include every current ISR semantic kind or explicitly reject it before producing an IR.
- Require source requirement references and explicit realization status; never infer satisfaction from a requirement reference.

### Stage A3.2 — canonical lowering

- Implement `isr_revision_to_compiler_ir` as the single canonical ISR-to-CompilerIR lowering boundary.
- Preserve node and edge IDs, source requirement IDs, typed payloads and relationship direction.
- Produce a deterministic mapping/loss report.
- Block on any unknown node/edge type, unsupported required payload, ambiguous binding, missing MUST requirement or unclassified semantic loss.
- Add property-based and adversarial tests for permutation invariance, round-trip preservation and deliberate omission.

### Stage A3.3 — transitional backend adapters

- Implement `compiler_ir_to_plan` as a compatibility adapter for existing Python FastAPI and Rust Axum reference backends.
- Keep the current backend-specific semantic capability gates; adapt them to canonical CompilerIR feature IDs.
- Reject a CompilerIR when the selected backend cannot implement its required subset.
- Keep Android's structural-only boundary explicit; it must refuse behavioral application plans rather than stripping obligations.
- Migrate the other target families incrementally after their own capability and native evidence gates are ready.

### Stage A3.4 — route convergence

- Migrate Campaign A, ProjectCompiler, root Universal Compiler API, Gen-C and other production-reachable compiler paths to the canonical CompilerIR.
- Until each route is migrated and bypass-tested, mark its canonical lineage status as UNKNOWN / NOT ESTABLISHED.
- Do not retire the old route or backend solely because it has not yet been migrated.

## 6. Required tests and evidence

1. Every ISR node and edge kind is either preserved into a typed CompilerIR field or produces a blocking diagnostic.
2. Every MUST requirement ID is present in the CompilerIR requirement-obligation set.
3. Every `SATISFIES` edge remains an explicit claim with its source/target IDs and verification state; it is not silently dropped.
4. Every API has the required explicit service binding when the contract requires one; zero, multiple and dangling bindings have distinct tests.
5. Every frontend interaction has exactly the required target binding; zero/multiple targets cannot silently become `None`.
6. Effects, invariants, consequences and their relationships survive round-trip serialization.
7. Content hashes are stable under insertion-order permutations and change when semantic content changes.
8. Source ISR hash, ArchitectureCandidate reference state, lowering implementation digest and mapping report are bound to the CompilerIR identity/evidence envelope.
9. The compatibility adapter either preserves all selected backend obligations or refuses before artifact emission.
10. Tests prove that direct compilation routes cannot bypass canonical lowering or the capability gate.

## 7. Proposed decision for reviewer

**Recommend approval of the following direction:**
1. D07 remains the canonical CompilerIR contract authority, updated by a new ADR to include the behavioral and frontend semantics now carried by `CompilationPlan`.
2. Implement a distinct canonical CompilerIR model with full lineage, content identity, typed obligations and deterministic loss reporting.
3. Retain `CompilationPlan` as a transitional backend execution-plan projection; do not rename it or claim it is canonical as-is.
4. Require every compiler family to consume the canonical CompilerIR directly or through a versioned, fail-closed adapter.
5. Keep all existing backend/frontend/mobile targets; unsupported required semantics block generation rather than triggering retirement or silent weakening.

**Approval record:** user approved the four FS-00 remediation steps on 2026-11-05. The implementation branch introduces the canonical CompilerIR and retains CompilationPlan as a transitional execution-plan projection.

**Change boundary:** documentation only. No tests were run because no executable code changed.
