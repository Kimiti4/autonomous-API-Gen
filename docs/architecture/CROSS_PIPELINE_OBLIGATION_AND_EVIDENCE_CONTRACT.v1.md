# Cross-Pipeline Obligation and Evidence Contract v1

Status: **INITIAL CONTRACT MODEL IMPLEMENTED — adapters and runtime evidence integration remain incomplete; not certified**

Branch: `review/taskflow-group-1-kimityr-clean`  
Related: [Coherence suite plan](COHERENCE_SUITE_AND_CROSS_COMPILER_ENGINEERING_PLAN.v1.md), [Phase 0 inventory](COHERENCE_SUITE_PHASE_0_SOURCE_INVENTORY.v1.md)

## Decision

Do not create a third independent capability/conformance framework, and do not silently merge the two existing compiler pipelines. Establish one versioned, compiler-neutral obligation/evidence contract and build explicit adapters at each pipeline boundary. Keep each pipeline's existing execution APIs until an evidence-backed migration proves behavioral equivalence.

The contract is an extension to semantic capability selection, not a replacement for artifact capability declarations.

## Source-backed motivation

1. `tiannara/domain/models/backend_declaration.py` describes artifact-kind and `BundleCapability` matching. `supports()` answers whether a declaration lists an artifact kind and the required generic capabilities. It does not identify domain obligations, enforcement sites, or acceptance evidence.
2. `tiannara/application/compiler/executor.py` invokes `generate(system_model)` and stores its result opaquely. A successful return is execution success, not semantic conformance.
3. `tiannara/application/compiler/verification.py` checks required-file presence, Python syntax, and selected dependency direction. Its module documentation explicitly leaves behavioral verification to tests.
4. `tiannara/application/compilation/consumption_contract.py` already provides a semantic projection boundary and explicit `SUPPORTED` / `PARTIALLY_SUPPORTED` / `UNSUPPORTED` coverage.
5. `tiannara/application/compilation/integrity_gate.py` defines eight gates for read-only behavior, determinism, provenance, semantic coverage, backend independence, round-trip identity, constitutional preservation, and evidence binding.
6. `tiannara/application/compilation/backend_capability_registry.py` contains source-verified declarations for its seven legacy realization backends. Its scope is not the same as the newer 20-implementation registry in `application/compiler/composition.py`.
7. `tests/test_r29_31_2_backend_matrix.py` explicitly distinguishes `VERIFIED_COMPILATION` from `SUCCESSFUL_COMPILATION` and `EXPLICITLY_UNSUPPORTED`; `tests/test_r29_31_5_certification.py` preserves bounds/assumptions in certification artifacts. These concepts should be retained, not reinterpreted as broad product certification.

## Canonical contract

The shared contract should be versioned, immutable once evaluated, canonicalizable, and content-hashed. It must be framework-neutral and must not include backend IDs or technology choices in the source semantic obligation itself.

Each obligation requires:

- `obligation_id`: stable identifier within a versioned vocabulary;
- `contract_version`: explicit schema/semantics version;
- `source_graph_id` and `source_graph_hash`: exact ISR/requirement source identity;
- `canonical_obligation_hash`: hash of normalized obligation content;
- `domain`: universal or named domain (authorization, booking, ledger, etc.);
- `statement`: precise, testable invariant, not an unbounded natural-language note;
- `applicability`: required / optional / not-applicable with a reason for the latter;
- `required_strength`: required guarantee and allowed failure semantics;
- `enforcement_points`: one or more typed loci (identity boundary, repository, transaction, event handler, scheduler, repair controller, etc.);
- `consumer_binding`: backend/runtime adapter identifier and version, held outside the technology-neutral source obligation;
- `acceptance_scenarios`: stable scenario IDs, expected outcomes, adversarial inputs, and required observables;
- `evidence_refs`: immutable references to build/runtime/test evidence and hashes;
- `disposition`: `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE`;
- `limitations`: explicit bounds, assumptions, skipped dimensions, and unsupported behavior.

A backend may not upgrade `UNKNOWN` to `PASS` from declaration alone, a generated file existing, compilation success, a mocked call, or an unexecuted test. `NOT_APPLICABLE` must be justified against the source obligation and reviewed policy; it is not a generic escape hatch.

## Separate capability and conformance layers

1. **Artifact capability** — can this compiler produce a backend service, frontend, migration, deployment, infrastructure or documentation artifact with the declared generic build/test surfaces?
2. **Semantic coverage** — which ISR obligations does the adapter claim to consume, with explicit support strength and degradation?
3. **Enforcement proof** — which generated/runtime code paths actually enforce the obligation?
4. **Acceptance evidence** — which executable scenarios challenge that enforcement, and what outcomes were observed?
5. **Campaign/certification** — are all required obligations and applicable scenarios covered for the exact source hash, target, backend version, environment and build?

These layers must not be collapsed into one boolean.

## Integration architecture

- **Canonical source:** retain the technology-neutral ISR/requirement graph as the authority.
- **Contract projection:** add a deterministic adapter that projects source semantics into the shared obligation model. Projection must be complete for all declared source semantics or explicitly record unsupported/unresolved obligations.
- **New compiler pipeline adapter:** extend planning metadata so each planned artifact can reference the obligation set it must consume. Keep `BackendCapabilityDeclaration` for artifact-level selection.
- **Legacy conformance adapter:** map existing `BackendSemanticModel`, coverage declarations, eight integrity gates and ledger references into the shared report without weakening any existing gate.
- **Runtime evidence adapter:** collect real build/test/runtime outcomes and artifact hashes; keep static verification distinct from behavior verification.
- **Evidence assembler:** verify that each PASS has a source-bound obligation, consumer binding, executable scenario result, and integrity-checked evidence chain. Missing or stale bindings become UNKNOWN/BLOCKED.
- **Benchmark runner:** run common universal scenarios plus each domain pack against every applicable backend. A backend that cannot meet a required guarantee is marked unsupported/blocked, not coerced into the same implementation.

Do not move legacy code into the new compiler namespace merely to reduce duplication. First demonstrate compatible schemas, equivalent semantics, and tests for both adapters.

## Universal guarantees vs domain contracts

### Universal contract candidates

- source/ISR identity and content-hash binding;
- no silent dropping of declared semantics;
- deterministic planning/provenance for identical inputs and policy;
- secret-safe error and audit output;
- fail-closed authentication configuration where authentication is required;
- consistent denial/not-found behavior where disclosure could leak cross-scope resources;
- idempotent retry outcomes where the source contract requires idempotency;
- evidence integrity, replayability and explicit UNKNOWN states;
- no claim of verified behavior without an executed acceptance scenario.

These are candidates for a shared contract only where the ISR explicitly requires them. Do not impose a domain policy where it was not specified.

### Domain-specific contracts

- TaskFlow: actor identity, workspace membership, role/action matrix, scope-filtered reads/writes, role changes, membership revocation and deletion safeguards.
- Booking: atomic availability claim, overlap rejection, timezone/recurrence policy, retry idempotency.
- Commerce: inventory reservation, order state transitions, event consistency and duplicate delivery.
- Wallet/Ledger: balanced immutable postings, atomicity, idempotency, reconciliation and replay.
- Telemetry/Fleet: ingestion identity, ordering/window semantics, duplicate handling, late events and retention.
- Collaboration: concurrent updates, ordering, reconnection, conflict resolution and version semantics.
- Legacy repair: baseline reproduction, minimal repair, regression detection and patch provenance.
- Incident repair: detection, diagnosis, bounded repair, rollback and post-repair verification.
- Multi-stack equivalence: same source-obligation hash and equivalent scenario outcomes despite different artifact hashes.
- Enterprise capstone: all applicable guarantees, operational evidence, threat cases and recovery paths linked in one verifiable chain.

Domain contracts must be explicit and versioned; they are not to be guessed from example applications.

## Required state machine

A proposed minimum disposition flow:

`UNMAPPED -> MAPPED -> CONSUMER_BOUND -> SCENARIOS_DEFINED -> EVIDENCE_COLLECTED -> VERIFIED`

Failure branches remain explicit:

- missing/ambiguous source semantics -> `BLOCKED_UNRESOLVED`;
- no backend consumer -> `BLOCKED_NO_CONSUMER`;
- declared unsupported -> `UNSUPPORTED`;
- scenario failure -> `FAIL`;
- no executed or unverifiable evidence -> `UNKNOWN`;
- applicability exemption -> `NOT_APPLICABLE` only with reason and review evidence.

The contract must prohibit transitions based solely on a declaration or on a downstream summary boolean.

## Implementation sequence and acceptance gates

1. **Schema and invariant tests:** strict schema/version, canonicalization, source hash binding, duplicate-ID rejection, no missing dispositions, no implicit PASS.
2. **Legacy adapter:** map existing eight-gate reports and explicit support declarations into shared evidence; prove each original gate remains mandatory and results are unchanged.
3. **New-pipeline adapter:** attach obligation references to plan/outcome; generation can continue only when the relevant gates permit it, otherwise it is blocked.
4. **Evidence assembler:** independently recompute canonical hashes, verify evidence references and required scenario completeness, reject stale source hashes and mismatched backend versions.
5. **Cross-pipeline parity:** same source obligation fixture fed through both adapters must preserve obligation IDs/content and must not improve a disposition without new evidence.
6. **Benchmark packs:** start with universal negative tests and TaskFlow authorization gate, then B02–B08 domain packs, B09 differential semantics, and B10 capstone.
7. **Migration decision:** only consider consolidating shared internals after adapter parity and backward-compatibility tests pass.

## Acceptance criteria

- No existing integrity gate is weakened or bypassed.
- The same obligation source hash is preserved across compiler adapters.
- Artifact capability is not used as a proxy for business-semantic enforcement.
- Every required obligation has an identified consumer and at least one executable acceptance scenario.
- An absent consumer, absent test result, stale evidence, or unverifiable evidence cannot produce PASS.
- Cross-stack tests compare normalized semantic outcomes, not generated file equality.
- Required unsupported semantics prevent certification; explicitly unsupported cases remain visible in the report.
- All reports bind source, contract version, backend/adapter version, scenario IDs, environment/build identity, and evidence hashes.
- The first end-to-end run yields a bounded verdict; no aggregate score can hide a failed required invariant.

## Current status

- Initial Pydantic contract model: `tiannara/domain/models/compiler_obligation.py`.
- Initial adversarial/unit coverage: `tests/test_compiler_obligation.py`.
- The model validates source hash shape, deterministic obligation hashing, strict fields, explicit NOT_APPLICABLE reasons, and PASS requirements for consumer binding, enforcement points, and passing scenario evidence.
- The model is not yet integrated into either compiler pipeline; a PASS record constructed by application code is not itself trusted evidence. The future evidence assembler must verify the referenced artifacts and executed test results independently.
- CI has been triggered by the commits; results are pending at time of update. No local test run is claimed.
- No benchmark is certified by this document.
- TaskFlow authorization remains blocked until policy decisions, lossless semantic projection, runtime consumer integration, trusted executable evidence, and independent evidence verification are complete.
