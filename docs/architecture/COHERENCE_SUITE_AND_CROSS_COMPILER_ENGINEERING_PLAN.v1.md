# ESAP Coherence Suite and Cross-Compiler Engineering Plan — v1

Status: **PROPOSED ENGINEERING BASELINE — not a certification claim**

Scope: the ESAP compiler and runtime as a whole, across all ten benchmark families. TaskFlow is one benchmark and must not become the architecture's organising assumption.

## Objective

Establish a measurable coherence suite that tests whether ESAP can derive, compile, run, observe, repair, and verify systems from a shared Intermediate Software Representation (ISR), without duplicating foundational fixes per application or silently weakening guarantees between compiler backends.

**Core rule:** implement an invariant once at its correct shared layer; express its requirements in typed, versioned contracts; require each applicable backend to implement that contract; and run the same backend-neutral acceptance scenarios against every supported implementation. Stack-specific adapters are permitted. Stack-specific reinterpretations or unverified substitutes are not.

This document defines a plan. It does not assert that any benchmark, backend, runtime path, or certification gate already passes.

## Ten benchmark families

| ID | Benchmark | Primary proof obligations | Required adversarial evidence |
|---|---|---|---|
| B01 | TaskFlow — full-stack SaaS / tenancy / RBAC | Identity and membership binding; tenant-scoped reads/writes; explicit role/action policy; safe membership changes; auditability | Cross-tenant read/write/list attempts; role escalation; stale membership/session; foreign assignee; deletion without authority |
| B02 | Booking system — concurrency, scheduling, idempotency | Time/availability invariants; conflict-safe concurrent booking; stable idempotent command outcomes; timezone and boundary rules | Simultaneous competing bookings; duplicate requests; retry after lost acknowledgement; timezone/DST boundaries; cancellation/reschedule races |
| B03 | Commerce — inventory, orders, workflows/events | Stock reservation and release; order state machine; transactional/outbox or equivalent event consistency; replay safety | Concurrent last-item purchases; failed payment/fulfilment; duplicate event delivery; out-of-order events; compensation/retry |
| B04 | Wallet/Ledger — transaction integrity and reconciliation | Immutable balanced journal entries; atomic posting; idempotent transaction commands; deterministic reconciliation; no silent mutation | Concurrent debits; duplicate transfer; partial failure; replay; unbalanced entry; reconciliation mismatch and recovery |
| B05 | Telemetry/Fleet — event ingestion and operational data | Schema/version validation; bounded ingestion; deduplication/order semantics; event-time vs processing-time clarity; retention/query integrity | Burst/backpressure; malformed/unknown schema; duplicates and late events; partition/restart; bounded resource use |
| B06 | Real-time collaboration — streaming/concurrency | Ordered or explicitly versioned updates; conflict handling; reconnect/resume; backpressure; access control on subscriptions | Simultaneous edits; reconnect and replay; slow consumer; duplicate/out-of-order messages; revoked access |
| B07 | Legacy repair benchmark — reverse engineering and maintenance | Baseline reproduction; intended-behavior reconstruction; minimal justified patch; regression preservation; uncertainty reporting | Seeded defects; misleading comments/specs; missing dependencies; regression suite; reject unsupported repair claims |
| B08 | Production incident benchmark — detect → diagnose → repair → verify | Evidence-backed detection; causal hypothesis; bounded reversible repair; post-repair verification; audit trail and rollback | Fault injection; misleading alerts; incomplete telemetry; failed repair; recurrence; rollback and independent verification |
| B09 | Multi-stack equivalence — same ISR across stacks | Same normalized semantics and policy outcomes across each supported backend; documented capability differences; no hidden semantic downgrade | Identical acceptance vectors on each backend; differential outputs; error/denial equivalence; deterministic rebuild; capability mismatch |
| B10 | Enterprise capstone — complete end-to-end proof | Requirements provenance through ISR, compile, build, runtime, operations, repair, and certification evidence | Cross-cutting failure injection; identity and data isolation; retries; event recovery; audit reconstruction; reproducible build and evidence bundle |

## Shared architecture layers

### L0 — Source-of-truth requirements and ISR
- Keep technology choices and provider-specific assumptions out of domain requirements.
- Represent business invariants, trust boundaries, actor/resource relationships, state transitions, consistency requirements, idempotency, event semantics, and explicit non-functional bounds as typed/versioned ISR contracts.
- Preserve source graph identity/hash and provenance for every derived obligation.
- Missing, ambiguous, contradictory, or unresolved semantics remain explicit; no guessed defaults.

### L1 — Canonical domain contracts and policy semantics
- Define reusable contracts for identity/authorization, tenant scope, audit events, idempotency keys, concurrency preconditions, state machines, transactional effects, event envelopes, retries/deadlines, observability, and evidence provenance.
- Separate universal invariants from domain-specific policies. A shared contract must not flatten different semantics into a vague generic flag.
- Validate contracts before backend planning. Reject unsupported requirements or declare them bounded/unsupported; never silently omit them.

### L2 — Compiler-neutral capability and obligation model
- Every required invariant becomes a typed obligation with source provenance, version, required strength, and acceptance IDs.
- Each backend declares which obligations it can implement and how they are consumed. A capability label alone is not proof of enforcement.
- Require a backend enforcement manifest linking each obligation to generated artifacts, runtime enforcement points, and tests/evidence.
- If an obligation has no valid consumer, compilation fails closed before generation or produces an explicitly non-deployable diagnostic bundle; it must not claim certification.

### L3 — Backend adapters and generated runtime
- Backends translate canonical contracts into their stack's mechanisms, retaining the same observable policy outcomes.
- Shared semantic checks remain outside backend-specific templates wherever feasible; backend adapters implement the required enforcement hooks.
- Do not solve a shared authorization, idempotency, or evidence bug by patching only one benchmark's generated application.
- Stack-specific differences are explicit, capability-checked, and tested against common acceptance vectors.

### L4 — Runtime primitives and operational controls
- Provide reusable mechanisms/adapters for identity context, membership/policy lookup, scoped repositories, transaction boundaries, idempotency records, concurrency controls, event publication/deduplication, retries, cancellation, audit, health/readiness, telemetry, and bounded execution.
- Avoid claiming a primitive is production-ready until persistence, failure, restart, concurrency, and security boundaries are tested for its declared use.
- Runtime configuration must fail closed where security is required; secrets must not be logged; unsafe retries must not duplicate effects.

### L5 — Coherence test harness and evidence
- Maintain one benchmark-neutral scenario format and assertion vocabulary, with domain-specific scenario packs.
- Run the same applicable scenarios against every backend and supported runtime mode.
- Record results as PASS, FAIL, UNKNOWN, or NOT_APPLICABLE with reason. Unknown is never pass; simulated evidence cannot satisfy a live/runtime gate.
- Bind evidence to source commit, ISR graph/hash, compiler/backend version, generated bundle hash, runtime/configuration, test command, result, and timestamps.
- Certification is derived from verified evidence and explicit gates, not from demo appearance, generated files, or a successful HTTP response alone.

## Shared fixes vs domain-specific implementations

**Fix once, verify everywhere**
- Typed ISR contract validation and provenance.
- Capability/obligation accounting and fail-closed unsupported-feature handling.
- Authorization context interfaces and policy-decision contracts.
- Stable error/denial semantics and non-disclosure rules.
- Idempotency contract and retry classification.
- Audit/evidence envelope, hashes, and evidence-state semantics.
- Deterministic compilation, reproducible manifests, test harness, and certification rules.
- Secret-safe logging, configuration validation, bounded execution defaults, and common failure taxonomy.

**Implement per domain, under shared contracts**
- Booking slot/conflict algorithms.
- Commerce inventory reservation, order state machine, and compensation policy.
- Ledger journal rules and reconciliation.
- Telemetry event-time, schema evolution, and ingestion semantics.
- Collaboration merge/version model and subscription semantics.
- Legacy repair strategies and incident diagnosis/repair plans.
- Each backend's stack-specific transaction, queue, database, streaming, and deployment adapters.

A “shared fix” is complete only when common contract tests pass and every applicable backend has either passing evidence or an explicit blocked/unsupported status. Do not copy code between backends as a substitute for semantic equivalence.

## Required evidence model

Each benchmark scenario must specify:
1. **Given:** versioned ISR and source provenance, declared capabilities, initial state and trust boundary.
2. **When:** a reproducible command or fault injection, including concurrency/retry conditions.
3. **Then:** externally observable invariants and expected denial/error/state outcomes.
4. **Evidence:** test output, runtime/build provenance, relevant logs/traces/audit entries, and hashes.
5. **Classification:** PASS / FAIL / UNKNOWN / NOT_APPLICABLE plus limitations.
6. **Backend matrix:** result per backend/runtime configuration; no inference from one stack to another.

Minimum cross-cutting gates:
- ISR contract validation and traceability.
- Compiler capability/obligation completeness.
- Generated source syntax/build and runtime startup.
- Positive and adversarial acceptance tests.
- Restart, retry, duplicate delivery, and failure recovery where relevant.
- Security/authorization and isolation where relevant.
- Reproducible evidence bundle and independent verification.
- Differential equivalence across backends.
- No unresolved critical obligation for a claimed certified deployment.

## Phased implementation sequence

### Phase 0 — Inventory and baseline
- Inventory current ISR models, semantic resolvers, compiler requirement derivation, backend declarations, all compiler backends, runtime primitives, certification workflows, benchmark artifacts, and existing evidence.
- Map current tests and implementation to the ten benchmark families and L0–L5.
- Identify duplicate mechanisms, backend-specific patches, placeholder/theatrical paths, unconsumed obligations, and claims without runtime evidence.
- Preserve existing behavior; this phase is an audit, not a mass refactor.

**Exit:** versioned coverage matrix with implemented / partial / placeholder / unknown / absent status and source/test references.

### Phase 1 — Canonical contracts and evidence spine
- Define typed, versioned obligation and enforcement-manifest schemas.
- Connect source graph provenance through semantic resolution, compiler plan, generated bundle, runtime tests, and evidence bundle.
- Enforce fail-closed handling for missing, unsupported, contradictory, or unconsumed required obligations.
- Define common scenario schema and result classifications.

**Exit:** contract mutation/omission tests; deterministic manifests; every required obligation traceable end-to-end or compilation blocked.

### Phase 2 — Shared runtime/security primitives
- Define interfaces and test doubles for principal context, policy decision, resource scope, idempotency, concurrency/transaction boundaries, event envelopes, audit, and failure/retry behavior.
- Integrate only where underlying persistence and semantics are specified; do not invent open TaskFlow policy details.
- Add shared adversarial contract tests independent of application templates.

**Exit:** shared contracts pass their unit/contract tests; no generated backend claims support without implementing the required hooks.

### Phase 3 — Backend conformance
- For each supported backend, implement the contract adapters and enforcement manifest.
- Run common scenario packs against generated applications, not only helper functions or mocks.
- Test capability mismatch, fail-closed generation, generated source, startup, runtime behavior, and recovery.
- Record backend-specific gaps without lowering the canonical requirement.

**Exit:** per-backend conformance matrix backed by actual execution evidence.

### Phase 4 — Benchmark packs B01–B08
- Build and validate each benchmark against canonical contracts.
- Use each to expose missing shared abstractions; promote a fix into a shared layer only when its generality is justified and it has regression coverage across existing packs.
- Keep domain-specific invariants explicit and independently testable.

**Exit:** all benchmark-specific acceptance criteria either pass or have named blockers and honest UNKNOWN/FAIL classifications.

### Phase 5 — Multi-stack equivalence (B09)
- Compile the same canonical ISR into each declared supported stack.
- Normalize outputs only for irrelevant representation differences; never normalize away policy or business-semantic differences.
- Compare success, denial, state transition, idempotency, error classification, and evidence trace.
- Verify unsupported features cause explicit blocking rather than silent downgrade.

**Exit:** differential test report for every supported backend pair and scenario.

### Phase 6 — Enterprise capstone (B10)
- Execute an end-to-end system through requirements, ISR, compilation, generated build, runtime, injected incident, repair, verification, and evidence review.
- Include adversarial security, concurrency, retry, restart, and evidence-integrity cases as applicable.
- Have the certification gate consume the evidence bundle and independently verify hashes, provenance, results, and limitations.

**Exit:** reproducible end-to-end proof with no unresolved critical obligations; otherwise report exact failures and retain blocked status.

## Initial work order

1. Complete Phase 0 inventory before broad implementation. Avoid another TaskFlow-only patch cycle.
2. Create a canonical matrix mapping every existing compiler/backend and existing test suite to L0–L5 and B01–B10.
3. Audit current requirement derivation and backend declarations for unconsumed ISR extensions and unsupported obligations.
4. Design the obligation/enforcement manifest from actual existing types and tests, minimizing duplicate abstractions.
5. Add the neutral scenario harness and evidence binding before expanding benchmark generation.
6. Keep TaskFlow generation blocked until its actual runtime consumer is proven; this is one instance of the global rule, not a special architecture.
7. Do not mark this plan, any benchmark, or any backend certified merely because this document or a scaffold exists.

## Change-control rule

Before introducing a shared abstraction, identify at least two concrete consumers or one clearly universal contract, the current duplication/failure it addresses, and regression tests. Before changing a contract, run all affected benchmark and backend scenarios. If the test cannot run, record UNKNOWN and preserve the gate.

## Current known limitation

The inspected FastAPI hexagonal backend currently generates API-key authentication and entity-ID-based in-memory repositories; it does not provide actor/workspace identity, workspace-scoped repository operations, or role enforcement. Pure authorization primitives exist but are not runtime-integrated. The missing-API-key configuration branch has been hardened, but no TaskFlow authorization certification follows from that change. This plan does not claim otherwise.
