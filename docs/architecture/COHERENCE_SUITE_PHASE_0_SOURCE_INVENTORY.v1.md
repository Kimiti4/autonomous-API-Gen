# Coherence Suite Phase 0 — Source Inventory v1

Status: **INITIAL SOURCE-BACKED INVENTORY — incomplete; not certification**

Branch at audit: `review/taskflow-group-1-kimityr-clean`  
Plan baseline: [Coherence Suite and Cross-Compiler Engineering Plan v1](COHERENCE_SUITE_AND_CROSS_COMPILER_ENGINEERING_PLAN.v1.md)

## Audit boundary

This is a source inspection of the typed ISR, capability declaration/selection/execution path, the FastAPI hexagonal backend, and the existing TaskFlow semantic gate/trace. It is not a complete repository-wide filesystem walk and does not claim every benchmark file or runtime primitive has been found. Repository code-search queries did not return indexed matches in this pass; therefore, a missing row below means **not established by the inspected source**, not proof that no implementation exists anywhere.

No tests were executed as part of this document. No generated application was built or started. No benchmark is certified by this audit.

## Initial architecture findings

### A. Typed ISR exists, but not every operational guarantee is a first-class typed contract

Source: [system_model.py](../../tiannara/domain/models/system_model.py)

The typed `SystemModel` includes capabilities, domains, services, components, APIs, events, data models, security posture, infrastructure/deployment policies, documentation/testing policies, and operational policies. It includes event delivery and ordering enums, consistency posture, API operation semantics/idempotency, and data-model invariant strings.

Limit: several important semantics remain broad enums, booleans, free-text invariants, or extensions. Their presence in the model does not establish a precise, versioned executable obligation, an enforcement point, or acceptance evidence. For example, `SecurityModel.authorization` can express RBAC, but the field alone does not encode a full actor/resource/action matrix or prove tenant-scoped persistence.

### B. Backend capabilities are selection metadata, not semantic enforcement proofs

Sources:
- [backend_declaration.py](../../tiannara/domain/models/backend_declaration.py)
- [capability_manifest.py](../../tiannara/domain/models/capability_manifest.py)
- [selector.py](../../tiannara/application/compiler/selector.py)

`BackendCapabilityDeclaration.supports()` checks artifact kind and a list of declared `BundleCapability` values. The selector chooses a matching declaration, ranking by quality and backend ID. The artifact manifest likewise lists capabilities.

Limit: these mechanisms do not currently express which typed domain obligations a backend consumes, which generated/runtime enforcement points implement them, or which scenario IDs prove them. A declaration such as `TEST`, `HEALTH_CHECK`, or `DEPLOY` is not proof that business invariants, security rules, concurrency semantics, or recovery guarantees hold.

### C. Compilation planning and execution have a clean seam, but semantic conformance is not enforced there

Sources:
- [derivation.py](../../tiannara/application/compiler/derivation.py)
- [registry.py](../../tiannara/application/compiler/registry.py)
- [executor.py](../../tiannara/application/compiler/executor.py)
- [project_compiler.py](../../tiannara/application/compiler/project_compiler.py)

The compiler derives artifact requirements from the typed ISR, selects declared backends, invokes `generate(system_model)`, then attempts bundle verification. The normal planner selects one backend per requirement; the opt-in cross-backend planner selects every satisfying backend.

Limit: the derivation rules currently express artifact kinds and generic capabilities, not benchmark-specific semantic obligations. The executor stores generated output opaquely. The project compiler treats a non-`CompilationResult` as UNKNOWN and blocks verification, which is appropriately conservative, but the reviewed path does not yet bind each required semantic obligation to a backend consumer and runtime acceptance scenario.

Inventory note: `derivation.py`'s module docstring says v1 covers backend services only, while the current implementation calls frontend, database, infrastructure, deployment, and documentation derivation functions. This comment/code mismatch should be reconciled so maintainers and audits do not rely on stale scope documentation.

### D. Current inspected FastAPI backend is explicitly limited in its own generated documentation

Source: [fastapi_hexagonal_backend.py](../../tiannara/application/compiler/fastapi_hexagonal_backend.py)

The backend describes itself as deterministic and model-free, generating a hexagonal API service, API-key authentication, JSON logging, settings, tests, container/deployment files, CI and docs. Its generated README explicitly says persistence is in-memory at this stage and authentication is API-key gating; richer persistence and identity mechanisms are described as future backend work.

Limit: API-key gating is not authenticated actor identity, workspace membership, scoped repository access, or role-based authorization. In-memory repository adapters do not establish durable transactional behavior, concurrent conflict safety, restart recovery, or ledger-grade integrity. These are explicit scope limits, not acceptable substitutes for stronger ISR requirements.

### E. TaskFlow semantic authorization is fail-closed at the compilation boundary

Sources:
- [intent/compiler.py](../../tiannara/application/intent/compiler.py)
- [authorization_semantic_obligations.py](../../tiannara/domain/models/authorization_semantic_obligations.py)
- [project_compiler.py](../../tiannara/application/compiler/project_compiler.py)
- [semantic consumer trace](../evidence/taskflow_review/SEMANTIC_CONSUMER_TRACE.v1.json)
- [authorization reconciliation](../evidence/taskflow_review/AUTHORIZATION_CONTRACT_RECONCILIATION.v1.md)

The intent compiler can require a semantic resolution record, validate a projection, and construct a graph-bound authorization obligation object. The project compiler deliberately raises and blocks generation when the TaskFlow gate is enabled, because no registered backend/runtime consumer currently proves enforcement. The consumer trace marks all 15 tracked semantic paths BLOCKED, with no typed destinations, consumer sources, causal mutation tests, or runtime acceptance IDs recorded.

The reconciliation document also records four unresolved authorization policy decisions and lack of cryptographic/trusted attestation. The obligation model retains and hashes two opaque mappings; the reconciliation warns that this alone does not validate a lossless role/policy projection.

Status: **BLOCKED** is the correct current classification for TaskFlow authorization; do not promote the trace to PASS based on helper tests, typed payload construction, API-key configuration hardening, or workflow success alone.

## Initial coverage matrix

Legend:
- **PARTIAL** — a relevant model/mechanism exists, but enforcement or evidence is not established.
- **BLOCKED** — a known gate explicitly prevents a claimed operational outcome.
- **UNKNOWN** — this pass did not inspect sufficient implementation/tests to classify.
- **NOT ESTABLISHED** — no end-to-end benchmark pack and evidence chain were located in the inspected sources; not a claim of repository-wide absence.

| Benchmark | ISR / shared model | Runtime or backend enforcement established by this audit | End-to-end benchmark evidence | Initial status |
|---|---|---|---|---|
| B01 TaskFlow tenancy/RBAC | Partial: generic security posture plus separate semantic ledger/obligations | No: TaskFlow gate explicitly blocks without a registered consumer | Trace has 15 BLOCKED semantic paths; acceptance IDs empty | **BLOCKED** |
| B02 Booking/concurrency | Partial: generic data/API/event fields can represent some requirements | Not established | No benchmark pack inspected | **UNKNOWN** |
| B03 Commerce/inventory/workflows | Partial: generic data/events/state can represent some requirements | Not established | No benchmark pack inspected | **UNKNOWN** |
| B04 Wallet/Ledger integrity | Partial: generic models and consistency posture only | Not established; no ledger-specific invariant implementation inspected | No benchmark pack inspected | **UNKNOWN** |
| B05 Telemetry/Fleet | Partial: event delivery/ordering and operational policy fields exist | Not established | No benchmark pack inspected | **UNKNOWN** |
| B06 Real-time collaboration | Partial: streaming interaction/event enums exist | Not established; reconnect/version/merge enforcement not established | No benchmark pack inspected | **UNKNOWN** |
| B07 Legacy repair | Not established by the inspected ISR/compiler path | Not established | No benchmark pack inspected | **UNKNOWN** |
| B08 Production incident repair | Partial: operational policy and observability vocabulary exist | No evidence here of a complete detect→diagnose→repair→verify runtime loop | No benchmark pack inspected | **UNKNOWN** |
| B09 Multi-stack equivalence | Partial: cross-backend planner can select all backends satisfying generic artifact capabilities | No semantic differential acceptance contract established by inspected selector/planner | No equivalence evidence inspected | **PARTIAL** |
| B10 Enterprise capstone | Partial: provenance-aware compiler pipeline and bundle verifier seam exist | End-to-end chain through production runtime, repair and independent evidence not established | No complete capstone evidence inspected | **UNKNOWN** |

## Cross-cutting gap register

| ID | Gap | Evidence from inspected source | Required follow-up |
|---|---|---|---|
| G0-01 | Capability declarations do not prove obligation enforcement | Capability lists and `supports()` match artifact kind/capability only | Add typed obligation requirements, backend consumer manifest, and runtime scenario links |
| G0-02 | ISR semantics may be under-specified for executable guarantees | Security posture enums; free-text invariants; extensions | Identify which invariants require typed contracts versus explicit unresolved/unsupported states |
| G0-03 | Derivation documentation is stale relative to implementation | `derivation.py` docstring says backend-only while additional artifact derivations are called | Correct the docstring and add a derivation coverage test |
| G0-04 | Default FastAPI backend has bounded identity/persistence semantics | Generated docs state API-key auth and in-memory persistence | Declare unsupported stronger guarantees; implement adapters only against canonical contracts |
| G0-05 | TaskFlow authorization policy projection is not losslessly reconciled | Reconciliation identifies shape mismatch and four unresolved decisions | Finish typed projection and mutation/omission/weakening tests; keep generation blocked |
| G0-06 | Cross-backend selection is not yet cross-backend semantic equivalence | Opt-in planner runs all backends satisfying generic capabilities | Add normalized scenario vectors and per-backend evidence matrix |
| G0-07 | End-to-end evidence provenance is incomplete at the semantic-consumer layer | TaskFlow trace entries have no consumer/test/runtime acceptance refs | Bind requirement graph → obligation → plan/backend → generated bundle → runtime test → evidence hash |

## Recommended implementation order after Phase 0

1. Complete a reliable repository inventory of backend registrations, every backend declaration, runtime primitives, existing benchmark fixtures, tests, and certification workflows.
2. Add a compiler-neutral typed obligation/enforcement-manifest contract; do not overload generic capability labels.
3. Link each obligation to its source graph/hash, version, enforcement point, and acceptance scenario IDs. Missing consumer or missing evidence remains blocking.
4. Build shared, backend-neutral scenario contracts for universal guarantees (traceability, denial/error semantics, idempotency outcomes, evidence integrity, secret-safe logging) and domain-specific contracts for booking, commerce, ledger, telemetry, collaboration, repair and incident response.
5. Run the same scenarios against each applicable generated backend/runtime; report PASS/FAIL/UNKNOWN/NOT_APPLICABLE with immutable provenance.
6. Keep all unsupported guarantees explicit. Do not expand TaskFlow or any other live generation path until its applicable gates are satisfied.

## Audit integrity

- Source files inspected on the branch listed above.
- This document records source-level observations, not test results.
- Tests: **NOT RUN** during this inventory.
- Generated applications: **NOT BUILT OR STARTED** during this inventory.
- Benchmark certification: **NONE CLAIMED**.


## Expanded repository inventory: backend registrations and existing tests

A subsequent directory-level inspection found 34 modules under `tiannara/application/compiler/` and 20 implementations registered by `build_compiler_registry()`: FastAPI, Go, Rust Axum, NestJS, Spring Boot, ASP.NET Core, Phoenix, Ktor, Express, Laravel, Rails, plus React, Vue, Angular, Next, Nuxt, Svelte, LiveView, Hologram, and Scenic frontends. This establishes implementation breadth, not equal capability or semantic equivalence across all those implementations.

Relevant existing tests include:
- `tests/test_cap_c_derivation.py`
- `tests/test_cap_c_backend_selection.py`
- `tests/test_taskflow_multi_backend_compiler.py`
- `tests/test_taskflow_semantic_contract.py`
- `tests/test_project_compiler_semantic_gate.py`
- `tests/test_r29_10_7_backend_conformance.py` and its expansion
- `tests/test_r29_31_2_backend_matrix.py`
- `tests/test_r29_31_5_certification.py`

These suites must be read and mapped to the benchmark obligations before reusing them as evidence. Their existence alone is not evidence that they passed on this branch or that they exercise live generated applications.

A concrete mismatch was found between the active derivation implementation and `tests/test_cap_c_derivation.py`: the test previously asserted that service-bearing systems produced only a backend-service requirement and that a named system without services produced no requirements. The implementation also derives frontend, infrastructure, deployment, and documentation requirements for the former, and a documentation requirement for the latter. The test was updated to reflect the current rule set and to check that a backend which only satisfies backend-service cannot satisfy the complete artifact plan. This source edit is awaiting CI; it has not been executed locally in this audit.

## Follow-up reconciliation — 2026-10-14

The repository-level reconciliation is consolidated in [Universal Developer System Reconciliation and Gap Analysis](../evidence/UNIVERSAL_DEVELOPER_RECONCILIATION_AND_GAP_ANALYSIS_2026-10-14.md). It expands this initial bounded inventory into the ten-domain disposition and shared P0/P1/P2 dependency order.

New shared toolchain declaration:
- `tiannara/domain/models/capability_manifest.py` now defines `ToolchainCapabilityManifest`, `ToolOperation`, and `SemanticSupportLevel`.
- `BackendCapabilityDeclaration` accepts the optional manifest to preserve compatibility while adapters migrate.
- Missing semantic entries are UNKNOWN, not supported. The declaration remains a claim; resolved executable identity and conformance evidence are still required.
- Focused manifest tests were added in `tests/test_toolchain_capability_manifest.py`; their status must be taken from CI for the latest commit, not inferred from their presence.

Important reconciliation finding: `source_projection.py`, `obligation_projection.py`, and `source_bound_certification.py` overlap. They must be reconciled into one authoritative contract and integrated into the live compiler before TaskFlow or any other application is authorized for certified generation. Do not grow a third independent projection/certification path.
