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


## Parallel compiler-runtime scope constraint

The selected core/backend boundary describes the root-level `compiler/core` substrate only. It does not, by itself, resolve the parallel `constitutional_architecture/compiler` Gen-C pipeline, the `constitutional_architecture/compilers/*` per-category runtime consuming `UniversalISR`, or the separate `tiannara/application/compiler` family. Existing R1 inventory documents some of these as legacy-retirement candidates, but those dispositions are not an authorization in this FS-00 draft. The full system-wide authority, consumer graph and approved disposition of these paths remain open prerequisites to FOUNDATION_READY.


## System-wide authority and universal backend preservation — reviewer decision 2026-11-04

**Independent reviewer decision: ACCEPT the target direction of one governed compilation authority and one authoritative ISR contract.** This decision expands the architectural scope beyond the root-level `compiler/core/` seam described above. The root core/backend boundary is a candidate foundation, not by itself the system-wide authority decision.

### Universal-development requirement

ESAP's intended universal software-developer capability is a requirement to preserve. Backend retirement must not be used as a shortcut for architecture consolidation, nor may a language, framework, platform or application-family capability be silently discarded.

The architecture shall distinguish:

- **Backend implementation:** a concrete emitter/compiler integration, which may be replaced, consolidated, deprecated or retired.
- **Target capability:** the language, framework, platform, runtime or application capability ESAP intends to provide.
- **Backend family:** one or more implementations serving a target capability under the common contract.
- **Certification status:** the evidence-backed state of a particular backend version, target version and supported feature set.

Retiring an implementation does not retire its target capability if a conformant replacement or governed alternative preserves that capability. Conversely, retaining a backend in the repository does not establish that the target is supported.

### Mandatory backend disposition rules

Every discovered backend and backend-like execution path must receive an explicit, evidence-backed disposition:

1. **RETAIN** — unique or useful implementation remains, with a defined owner and conformance obligations.
2. **CONSOLIDATE** — overlapping implementations converge on one governed implementation; target capability and required semantics remain covered.
3. **REPLACE** — implementation is superseded only after the replacement meets the applicable contract and migration/rollback criteria.
4. **DEPRECATE** — existing consumers receive a documented migration path and support window; no premature capability claim is allowed.
5. **RETIRE** — implementation is removed or fenced only after consumer/reachability analysis, capability-impact analysis, migration evidence and independent approval.
6. **QUARANTINE** — unsafe, untrusted or non-conformant implementation cannot execute or publish artifacts, but its target capability remains visible as unsupported/not certified until resolved.
7. **NOT YET IMPLEMENTED** — intended target capability is retained in the capability roadmap without falsely claiming a working backend.

No backend may be retired solely because it is inconvenient, uses a different technology, is outside the proposed directory layout, or fails to conform to a contract that has not yet been approved. Unique target semantics must first be captured in the universal contract or explicitly governed as a supported extension.

### Universal backend contract

Every backend family must consume a governed, versioned compiler input contract and declare, at minimum:

- target language, framework, platform, runtime and supported version range;
- supported ISR/Compiler-IR constructs and feature-level coverage;
- semantic obligations implemented, rejected or explicitly unsupported;
- security, authorization, effect, persistence, concurrency and deployment obligations relevant to its claims;
- deterministic configuration and dependency/toolchain identity;
- output artifact types, manifests, source-to-artifact lineage and provenance;
- build, runtime, behavioral, negative, security and regression evidence;
- verifier/conformance suite version and current certification status.

Backend-specific extensions are permitted only when namespaced, versioned, typed, documented and governed. An extension must not silently override canonical ISR semantics or bypass central policy.

### Capability preservation and retirement gate

Before consolidation, replacement, deprecation or retirement, the audit must produce a **Target Capability Preservation Matrix** mapping:

`target capability → existing implementations → consumers/routes → semantic coverage → evidence → proposed disposition → replacement/gap → migration and rollback`

The matrix must cover all discovered languages, frameworks, platforms and application families—not only currently active or easy-to-test backends. It must distinguish source-present, reachable, buildable, runnable, behaviorally verified and independently certified states.

A backend may be retired only when all of the following are true:

- its consumers and dynamic/deployment reachability have been inspected;
- every target capability it uniquely provides is preserved by an accepted replacement or explicitly recorded as a deliberate, separately approved roadmap gap;
- semantic and behavioral parity is demonstrated for the supported feature set, including negative cases;
- no required user-visible capability is silently lost;
- migration, compatibility, rollback and evidence-retention plans are reviewed;
- the independent reviewer approves the specific disposition.

If these conditions are not met, the implementation remains in place but may be fenced or marked non-conformant. It must not be represented as certified.

### System-wide compilation authority

The eventual authority must own the governed lifecycle across all compiler families: request admission, canonical ISR binding, validation, transformation orchestration, backend selection/authorization, artifact quarantine/publication, verification and evidence-backed verdicts. Existing Gen-C, ProjectCompiler, UniversalCompiler API and per-category compiler paths must either become governed adapters/subsystems under this authority or be explicitly classified and fenced. A directory move or wrapper alone is not proof of convergence.

**Status:** architectural direction accepted; implementation and current compliance remain unproven. This section does not authorize backend deletion, schema changes, code modifications, FS-01, PR merge or FS-00 closure. The complete backend inventory, capability matrix, route/reachability evidence and independent review remain FS-00 exit criteria.


## Backend hardening gate — reviewer clarification 2026-11-04

Frontend compiler hardening is recorded as complete at the workstream level; backend compiler hardening remains outstanding. The universal compiler architecture must not treat these as one undifferentiated status.

Before a backend implementation can be considered hardened or certified, evidence must show: (a) governed canonical ISR admission and provenance binding; (b) centrally enforced capability declarations; (c) complete semantic preservation or explicit pre-emission refusal; (d) authorization/effect/invariant enforcement; (e) no backend invocation or deliverable artifact on invalid/unknown/unsupported input; (f) quarantined, centrally validated artifact publication; (g) native build, runtime, behavioral and negative tests; (h) applicable security evidence; and (i) independent candidate-bound verification.

The frontend/backend integration must additionally demonstrate that frontend routes and interactions map to implemented backend API operations, data contracts, authorization and effects. Separate target builds do not establish full-stack semantic coherence.

A green backend contract-test job, source presence, registry declaration or synthetic/fake toolchain test is not native build/runtime certification. The Android backend contract-test job at PR #201 head `c229dd65b25f26411bb821e29a089512c6741507` passed; its Android cloud-build job was skipped on the pull-request event. The two Android implementations remain distinct audit targets.

**Status:** backend hardening remains an open FS-00 finding. This gate does not authorize code/schema changes, FS-01, backend retirement, PR merge or FS-00 closure.


## AI capability synthesis with senior frontend/backend engineering practice — reviewer direction 2026-11-04

**Reviewer requirement:** each frontend and backend compiler must combine the complementary strengths of advanced AI-assisted reasoning and generation with the standards, judgement and disciplined execution expected of a senior specialist software engineer. This is a product-quality requirement, not a marketing label or a claim that the current compilers already possess these capabilities.

The goal is not to choose between an AI generator and a conventional senior engineer. ESAP should combine both modes into one governed engineering process:

- **AI strengths:** broad knowledge synthesis; rapid exploration of design alternatives; pattern recognition; cross-domain reasoning; adaptation to requirements; generation of implementation options; discovery of edge cases; iterative refinement; explanation and traceability.
- **Senior-engineer strengths:** sound architecture; requirements clarification; trade-off judgement; domain modelling; maintainability; simplicity; reliability; performance; security; accessibility/usability; testing strategy; debugging; operational readiness; code review; disciplined delivery.
- **Combined result:** AI breadth and iteration constrained and improved by senior-level engineering standards, with objective tests and independent verification rather than confidence, verbosity or code volume.

The AI component is an assistive reasoning/generation capability, not a new authority. It must not bypass the canonical ISR, governance, deterministic validation, backend contracts, human approval gates or independent verifier. No external LLM provider is a mandatory architectural dependency; reasoning providers/models may be replaceable and governed, and any model output remains untrusted input until validated. Where a deterministic tool or compiler can establish a fact, it takes precedence over model assertion.

### Frontend compiler — combined capability profile

Every frontend compiler must demonstrate both AI-assisted product/design reasoning and senior frontend engineering discipline, including:

1. **Product and user understanding:** clarify user goals, personas and workflows from approved requirements; identify ambiguity, missing states, conflicting needs and accessibility implications; propose alternatives with explicit trade-offs.
2. **UX and interaction design:** information architecture, navigation, task flows, interaction patterns, responsive behavior, feedback, loading/empty/error/success states, form behavior, state transitions and recovery paths.
3. **Visual and design-system quality:** coherent hierarchy, typography, spacing, layout, component composition, tokens, themes, responsive breakpoints and consistent visual language; avoid arbitrary one-off styling and design drift.
4. **Senior frontend architecture:** appropriate component boundaries, state ownership, data flow, routing, composition, reuse, separation of concerns, typed contracts, predictable side effects and maintainable project structure.
5. **Accessibility and inclusion:** semantic markup, keyboard operation, focus management, screen-reader semantics, contrast, reduced motion, scalable text and accessible validation; test against an explicit accessibility standard and real interaction cases.
6. **Performance and resilience:** bundle and rendering budgets, loading strategy, caching where appropriate, hydration/SSR correctness, graceful network failure, browser compatibility and protection against unnecessary complexity.
7. **Security and privacy:** safe output rendering, input handling, session/token boundaries, dependency hygiene, CSP-compatible patterns where applicable, no secret leakage and secure API integration.
8. **Verification and refinement:** unit/component, integration, browser end-to-end, accessibility, visual-regression where useful, responsive viewport and negative tests; diagnose failures and refine without weakening acceptance criteria.
9. **Senior-level review:** inspect generated code for correctness, consistency, readability, maintainability, unnecessary abstractions, dead code, fragile selectors, duplicated logic and hidden coupling.
10. **Product finish:** polished empty/loading/error states, useful microcopy, consistent feedback, discoverability, responsive details and coherent behavior—not merely a page that renders.

AI should broaden and accelerate design exploration; senior frontend discipline should select, simplify, implement and verify the best solution.

### Backend compiler — combined capability profile

Every backend compiler must demonstrate both AI-assisted systems reasoning and senior backend engineering discipline, including:

1. **Domain and requirements engineering:** derive explicit domain concepts, invariants, ownership, lifecycle, authorization boundaries and failure behavior; detect ambiguity and unresolved business rules before code generation.
2. **Architecture and service design:** appropriate modularity, bounded contexts where relevant, API/service boundaries, dependency direction, separation of concerns and maintainable evolution paths.
3. **Data engineering:** correct schemas, constraints, relationships, migrations, transaction boundaries, indexing, query behavior, data integrity, retention and durable persistence where required.
4. **API and integration engineering:** accurate contracts, validation, versioning, idempotency, pagination, error semantics, compatibility, rate limiting and integration behavior.
5. **Security engineering:** authentication, authorization at every relevant boundary, least privilege, tenant isolation, secret handling, injection resistance, cryptographic correctness, auditability and threat-aware defaults.
6. **Concurrency and distributed-systems reasoning:** race conditions, isolation, ordering, retries, deduplication, backpressure, timeouts, cancellation, consistency, delivery guarantees and failure recovery where applicable.
7. **Reliability and operations:** structured logs, metrics, tracing, health/readiness, graceful shutdown, configuration, resource bounds, backup/recovery, deployment and rollback considerations.
8. **Performance and scalability:** workload-aware algorithms, query plans, caching, resource usage, load characteristics and explicit performance budgets; no unsupported scalability claims.
9. **Testing and debugging:** unit, contract, integration, database, API, concurrency, security, migration, failure-injection and end-to-end tests; reproducible diagnosis and regression prevention.
10. **Senior-level review:** inspect correctness, cohesion, coupling, complexity, duplication, error handling, maintainability, dependency risk and operational consequences.
11. **Semantic completeness:** preserve ISR-defined requirements, effects, consequences, invariants, policies, events, persistence and deployment intent—or refuse the unsupported scope before backend invocation and artifact emission.

AI should accelerate analysis, compare architectural options and identify non-obvious risks; senior backend discipline should enforce correctness, security, reliability and operational fitness.

### Shared engineering workflow and quality gates

The combined frontend/backend process must follow a governed sequence:

1. **Understand:** bind work to the approved requirement set and canonical ISR; identify missing or conflicting semantics.
2. **Explore:** generate alternative architectures, designs or implementations with rationale and explicit trade-offs.
3. **Select:** choose using requirements, constraints, quality attributes, target capability and measurable budgets—not model preference.
4. **Design:** establish contracts, boundaries, state/data flows, threat model, failure modes and test oracles before emission.
5. **Implement:** generate through the selected conformant backend/compiler under central authorization and policy.
6. **Review:** run senior-engineer-style static and semantic review, including adversarial review for omissions, overengineering and unsafe assumptions.
7. **Verify:** execute target-native builds, tests, security checks, runtime/behavior checks and semantic correspondence tests.
8. **Refine:** repair failures while preserving the original acceptance criteria; any scope or requirement change must be explicit and traceable.
9. **Certify:** independent verification binds source, ISR, transformations, compiler/backend version, toolchain, artifacts and test/runtime evidence.

The AI reviewer and generator must not be the sole verifier of their own output. Use independent deterministic checks, test oracles, static analyzers, native toolchains and—where available—separate review processes. Model-generated explanations are not evidence of correctness.

### Quality scorecard and anti-patterns

Each frontend/backend target requires an explicit scorecard with measurable, target-appropriate criteria for:

- requirement and semantic coverage;
- architectural soundness and maintainability;
- correctness and behavior;
- accessibility/usability (frontend) or data/API/security correctness (backend);
- performance and resource budgets;
- reliability and failure handling;
- test depth and negative-case coverage;
- security and privacy;
- native build/runtime evidence;
- traceability and reproducibility;
- independent verification.

No single aggregate score may hide a critical failure. Hard gates—security, data integrity, semantic preservation, authorization, accessibility obligations where required, and fail-closed behavior—cannot be compensated for by high scores elsewhere.

Prohibited anti-patterns include: treating generated code volume as quality; accepting plausible UI without interaction/accessibility tests; accepting a successful compile as proof of behavior; inventing requirements to fill gaps; silently omitting ISR semantics; overengineering simple requirements; copying fashionable architecture without workload justification; trusting model assertions instead of executable evidence; weakening tests to obtain a pass; and allowing the generator to certify itself.

**Status and scope:** this records the required target capability and quality direction for both frontend and backend compiler families. It does not assert current implementation, authorize code/schema changes or FS-01, upgrade any certification, approve backend retirement, merge PR #201 or close FS-00. Concrete per-target acceptance criteria and evidence must be developed and independently reviewed before implementation is authorized.
