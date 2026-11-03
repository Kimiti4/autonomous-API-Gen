# FS-00 Deliverable 4 — Compiler Architecture ADR

**ADR ID:** FS-00-ADR-001  
**Status:** PROPOSED — requires independent human approval  
**Decision scope:** Compiler IR boundary for the Full-Stack Compiler  
**Source commit:** `68696e2a07595fed98a19e24ee96c3e4e0e5bfeb`  
**Companion:** Deliverables 1–3 in this directory.

## Context

The governing criterion in `folder/prefull.md` §2 requires a validated technology-neutral ISR to lower deterministically through Compiler IR into a complete full-stack application, then pass verification with immutable provenance and end-to-end lineage.

The current tree contains a concrete seam: `compiler/core/lowering.py` converts `ISRRevision` into `CompilationPlan`; `compiler/core/protocol.py` defines a backend protocol; `compiler/core/registry.py` and `compiler/composition.py` compose backends; target emitters live under `compiler/backends/`.

The current `CompilationPlan` is explicitly a stabilization IR. It contains typed carriers but does not yet demonstrate complete representation of all ISR node/edge semantics or a full-stack orchestration contract. Therefore the seam exists structurally, but the canonical IR contract is not complete.

## Decision proposed

**Choose Option 2: between `compiler/core/` and `compiler/backends/`.**

The canonical Compiler IR should be a versioned, technology-neutral semantic contract owned by compiler core. Backend-family implementations consume that contract and declare the semantic obligations they implement, artifacts they emit, verification surfaces and evidence they produce. The ISR remains the constitutional source of truth; the Compiler IR is a deterministic derived representation, not an independent source of requirements. Evolution may propose architecture candidates but does not become the compiler IR by implication.

This is a proposed architectural decision only. It does not authorize code changes, ISR schema evolution, Android behavior implementation, or FS-01.

## Alternatives considered

### Option 1 — Between intent and compiler; ISR directly to target artifacts

**Rejected.** It couples source semantics to target emitters, weakens backend polymorphism and encourages repeated target-specific lowering. It makes it harder to demonstrate one shared semantic contract and consistent lineage across backend families.

### Option 2 — Between compiler core and backends

**Selected.** It matches the existing source seam, centralizes technology-neutral plan semantics and capability gates, and permits independently testable backend-family contracts. It requires explicit canonical IR schema/version/canonicalization and lossless lowering rules; these are deliberate FS-01 work, not reasons to bypass the seam.

### Option 3 — Between evolution and compiler; Architecture Candidate/genome as IR

**Rejected.** An evolution candidate expresses a proposed architecture/search state and fitness/mutation metadata; a compiler IR expresses executable semantic obligations and backend-consumable structure. Treating them as interchangeable conflates candidate generation, approval and compilation. An explicit deterministic transformation may connect them, but the genome is not the canonical Compiler IR without a separate contract decision.

### Option 4 — After compiler and before verification

**Rejected.** An IR introduced only after compilation is too late to serve as the common contract consumed by backend families. It would make verification observe already target-specific artifacts rather than validating generation against a stable semantic representation.

## Boundary location and integrity

- **ISR side:** `isr/core/graph.py`, `isr/core/revision.py`, typed behavior and validation modules.
- **Lowering adapter:** `compiler/core/lowering.py`.
- **Current stabilization IR:** `compiler/core/plan.py`.
- **Protocol/registry side:** `compiler/core/protocol.py`, `compiler/core/registry.py`, `compiler/composition.py`.
- **Backend side:** `compiler/backends/`, including the structural Android backend.
- **Certification side:** `certification/campaign/runner.py`, verifier/conformance/evidence modules; these consume bound candidates and results and must not invent source semantics.

The seam is located in existing code. Boundary integrity is **partial** because not every import crossing the boundary in the full repository has been enumerated, and the Android module's `compile_isr_revision()` helper imports/accepts `ISRRevision` from inside a backend module. That helper is a coupling finding; any relocation must be planned and tested only after this ADR is approved.

## Required contracts after approval

1. **FS-01 — ISR ↔ Compiler IR:** node/edge coverage, behavior payloads, schema ID/version, deterministic mapping, canonical serialization/hash, provenance binding, unknown semantic handling, explicit rejection/omission policy and migration strategy.
2. **FS-02 — orchestration:** input validation, backend selection policy, full-stack composition, deterministic seed/config, stage outputs, partial failure/quarantine, retry/idempotency, publication rules and lineage.
3. **FS-03 — backend/artifact contracts:** per-family IR obligations, declared capability manifest, emitted artifact manifest, build/runtime/negative tests, independent verification and evidence surfaces.
4. **Certification/evidence:** source/plan/repository/candidate/runtime hashes, verifier identity, chain validation, immutable verdict and unknown/corruption behavior.
5. **Deployment/runtime:** deployed-instance identity, environment binding, health/lifecycle/rollback and post-deploy observations.

## Failure and security analysis

| Failure/threat | Required boundary behavior | Verification/evidence |
|---|---|---|
| Backend compile failure | stop composition, quarantine partial output; do not publish | fault injection, stage status, artifact manifest and raw logs |
| Corrupt/missing evidence or broken lineage | never convert to PASS; quarantine and escalate | tamper tests, chain verifier, source/plan/artifact hashes |
| Unknown ISR node/edge/behavior | reject or explicitly policy-escalate; no silent dropping | unknown-kind negative tests and mapping report |
| Unauthorized ISR/backend submission or publication | deny by default; authorization separate from compiler success | principal/action/policy-version audit record |
| Malicious/untrusted backend plugin | isolate execution, constrain filesystem/network/secrets, verify artifact manifest | sandbox tests, capability declaration and execution logs |
| Secret leakage in generated artifacts/evidence | redact or omit secret values; retain safe references | secret scanning and redaction tests |
| Evolution attempts protected schema/compiler mutation | proposal is not approval; require authorized human/governance decision | immutable approval record, parent hash and rollback plan |

The existing governance registry, escalation policy and ledger verification are evidence inputs; their presence does not by itself prove all these controls are wired into the proposed boundary.

## Migration safety

No file moves or code refactors are authorized by this proposed ADR. A staged migration plan for later approval is:

1. Freeze and inventory current APIs, imports, schema hashes and tests.
2. Define FS-01 contract and compatibility fixtures before implementation.
3. Add explicit coverage/mapping tests while keeping existing entry points.
4. Introduce an orchestration-owned ISR-to-IR adapter; move backend convenience helpers only when compatibility tests pass.
5. Migrate one backend family at a time; fail closed on undeclared semantics.
6. Run unit, determinism, contract, security, build, runtime and negative tests at each stage.
7. Compare evidence/lineage before and after; no verdict upgrade from synthetic tests.
8. Retain the prior commit/artifact and a documented revert path until acceptance is demonstrated.

Likely candidate files for a later migration include `compiler/core/lowering.py`, `compiler/core/plan.py`, `compiler/core/protocol.py`, `compiler/core/registry.py`, `compiler/composition.py`, and backend helpers that import ISR types. This is a preliminary list, not an exhaustive import graph or authorization to move files.

## Consequences

- Compiler IR becomes a first-class, versioned boundary owned by compiler core.
- Backend families must declare and prove which semantic obligations they implement.
- Unsupported semantics remain explicit blockers; no backend may silently omit them.
- Evolution candidate/genome, ISR, Compiler IR, generated repository, deployed instance and evidence chain remain distinct linked objects.
- Android behavioral expansion is blocked until the FS-00 decision is approved and FS-01/03 contracts are approved.
- The current `CompilationPlan` may be evolved into or adapted to the canonical IR only under a later approved contract; its current existence is not proof that the contract is complete.

## Gate assessment

| Evidence class | Assessment | Rationale |
|---|---|---|
| Architectural evidence | PARTIAL | inventory paths complete, semantic module classification and full dependency graph not yet complete |
| Contract completeness | PARTIAL | required FS-01/02/03 contracts named with input/output/failure/verification/evidence surfaces; details remain future phases |
| Boundary integrity | PARTIAL | seam is real; all crossings not yet exhaustively enumerated; Android helper is a known leak |
| Failure/security analysis | PARTIAL | threat/failure cases enumerated; enforcement wiring requires later evidence |
| Migration safety | PARTIAL | staged approach and rollback are outlined; exact import graph and intermediate test matrix not yet complete |
| Governance approval | PENDING | independent human approval required |

**FS-00 result: FOUNDATION_NOT_READY.** This document is a review draft and does not authorize FS-01 or any code/schema changes.


## Migration and verification matrix (planning only; no code migration authorized)

**Status:** REVIEW DRAFT. This matrix does not approve FS-01, an ISR schema change, or implementation. The proposed ADR must be approved first.

### Migration principles

- Keep ISR, canonical compiler IR, generated repository, runtime instance and evidence as distinct bound objects.
- Do not expand Android semantics or mutate ISR schema during FS-00.
- Migrate one backend family at a time; unknown semantics and missing evidence remain non-passing.
- Mocked toolchains, synthetic APKs and simulated runtime observations cannot satisfy native build/runtime acceptance.
- Every stage has explicit stop conditions and a rollback point.

| Stage | Scope / precondition | Required verification | Stop / rollback condition |
|---|---|---|---|
| M0 — Freeze baseline | After FS-00 approval to begin implementation; pin source, schema, fixtures, backend manifests and workflow definitions. | Clean-checkout baseline suite, hashes and exact commands/results. | Unexplained drift or unavailable baseline input. |
| M1 — Contract fixtures | FS-01 defines mapping and unknown-semantics policy. | Every ISR node/edge/payload; malformed and unknown kinds; dangling references; deterministic canonical serialization; semantic-correspondence checks. | Any source semantic unaccounted for, silently dropped or ambiguous. |
| M2 — Canonical IR adapter | M1 fixtures approved; compatibility plan reviewed. | Versioned IR schema, deterministic mapping, source-to-IR trace, compatibility and negative tests. | Missing lineage, unstable hashes or unapproved behavior change. |
| M3 — Core/backend boundary | M2 accepted; migration patch approved. | Static import-boundary checks, registry conformance, backend capability manifests, unsupported-feature refusal and isolation tests. | Core imports backend; unsupported semantics accepted; compatibility regression. |
| M4 — Orchestration seam | Canonical IR/backend contracts approved. | Full-stack composition, deterministic selection, retry/idempotency, partial-failure quarantine and lineage tests. | Partial artifacts published or source binding lost. |
| M5 — Independent evidence | Stable enough to bind source, ISR, IR, backend/version, candidate, artifacts and runtime results. | Tamper tests, fresh-process verifier, anti-vacuity tests, UNKNOWN remains non-pass, secret redaction and verdict regression tests. | Broken chain or verifier result trusted without independently checked predicates. |
| M6 — One behavioral vertical slice | FS-00 approved; FS-01/FS-03 contracts approved; real Android SDK/Gradle/emulator available. | Real APK build/install/launch; real UI interactions; behavior oracles; durable-state checks across process relaunch; offline and negative cases; source-to-runtime lineage. | Any required criterion missing, mocked, unbound or unverified. |
| M7 — Backend-family rollout | M6 accepted and rollout plan reviewed. | Per-family feature matrix, native build/run, security and contract tests, negative cases, independent conformance and version matrix. | Capability claimed without evidence or regression on shared semantic fixtures. |
| M8 — Continuous certification | Stable per-family acceptance criteria. | Reproducible CI, dependency-update tests, evidence retention, deprecation status and rollback drills. | Unsupported combination shown as supported or stale certification presented as current. |

### Minimum ISR-to-IR test matrix

| Construct | Positive coverage | Negative coverage | Evidence |
|---|---|---|---|
| Every declared node kind | Documented IR mapping or explicit policy-gated non-executable annotation. | Unknown kind, missing payload, invalid behavior. | Node coverage and source/IR hashes. |
| Every declared edge kind | First-class relation or documented verified equivalent. | Dangling endpoint, unsupported/conflicting relation, order variation. | Edge coverage and correspondence assertions. |
| Requirement dependency/conflict/refinement/ownership | Retained in IR and traceability graph. | Unresolved conflict, missing target, ambiguous ownership. | Requirement-to-IR links and resolution record. |
| Behavior payloads | Validated deterministic canonical form. | Missing/extra/invalid fields, unknown operator, type mismatch. | Validation report and payload hash. |
| Effects/invariants/consequences | Binding and evaluation obligations remain explicit. | Unbound effect, ambiguous target, violated invariant, unsupported consequence. | Binding map, oracle definitions and negative results. |
| Frontend routes/interactions | Route, action, target and expected state transition represented. | Missing or ambiguous target/selector; invalid navigation. | Interaction trace and independent state assertions. |
| Security policies | Required links preserved and checked against backend capability. | Missing/weaker policy or unauthorized action. | Policy-version binding and authorization negative tests. |
| Determinism/lineage | Pinned inputs/config yield equivalent canonical IR and stable declared outputs. | Input-order change, source hash mismatch, modified manifest, stale backend. | Repeated-run hashes and mismatch diagnostics. |

### ESAP-APP-001 acceptance evidence

A successful Gradle task or APK file is necessary but insufficient. Bind the exact source revision, approved specification/ISR derivation, candidate hash, APK hash, emulator/device identity, install/launch results, real UI interaction traces, durable-state assertions across process relaunch, offline behavior, negative cases and independent semantic-verifier output. Synthetic/mocked observations must be labelled and excluded from certification.

### Rollback and compatibility

- Keep each stage reviewable and separately revertible.
- Preserve prior entry points during migration only when the approved plan explicitly permits it; compare semantic outputs, not file counts.
- On divergence, stop and retain both reports; do not automatically prefer the new path.
- Keep the last known-good commit and evidence bundle until independent acceptance.
- Revert a failed stage as a unit; never weaken acceptance criteria to make it pass.
- Schema/version migration requires separate approval and migration/rollback fixtures.

**Migration Safety remains PARTIAL.** This is a planned matrix, not test execution evidence. The full import graph, consumer inventory and actual rollback identifiers remain outstanding.
