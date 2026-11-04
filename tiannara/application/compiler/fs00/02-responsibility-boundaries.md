# FS-00 Deliverable 2 — Responsibility Boundaries

**Status:** REVIEW DRAFT — not an FS-00 pass or authorization for FS-01  
**Source commit:** `68696e2a07595fed98a19e24ee96c3e4e0e5bfeb`  
**Companion:** `tiannara/application/compiler/fs00/01-existing-architecture-map.md`

## 1. Boundary principle

Each architectural concern must have exactly one accountable owner. Multiple modules may participate, but only one is the authority for the concern's contract. When current code has no defensible owner, record a gap; do not infer ownership from folder names alone.

## 2. Concern-to-owner matrix

| Concern | Proposed authoritative owner | Inputs → outputs | Failure / unknown behavior required | Verification | Evidence |
|---|---|---|---|---|---|
| Constitutional rules and authorization to change architecture | `constitutional_architecture/` governance surfaces; exact authority registry must be confirmed | approved rules/decisions → policy decisions | deny or escalate when authority/signature/state is unknown | governance invariant and unauthorized-transition tests | decision ID, approver, policy version |
| ISR schema and semantic source of truth | `isr/core/` plus its canonical constitutional contract | graph + identity/provenance → validated ISRRevision | reject invalid/unknown semantics, dangling references and invalid hash | schema, graph, invariant, hash checks | schema ID/version, canonical hash, validation report |
| Requirement intelligence and requirement graph | `tiannara/application/intent/`, `tiannara/application/cap_a_*`, and `reqgraph/` where present | user intent + constraints → requirement graph | ambiguity/conflict must be represented or escalated, not silently guessed | requirement coverage/conflict/oracle tests | input reference, graph hash, resolution log |
| Evolution candidate construction and selection | `evolution/` and `tiannara/application/evolution/` | validated ISR/decision space → candidate/genome/fitness/lineage | reject invalid candidates; never self-authorize protected mutations | invariants, mutation bounds, selection reproducibility | parent/candidate hashes, operators, fitness evidence |
| ISR → Compiler IR lowering | `compiler/core/lowering.py` | validated ISRRevision → CompilationPlan | fail closed for semantic loss, ambiguity or unknown nodes | deterministic mapping and semantic correspondence checks | source hash, IR hash, mapping report |
| Canonical Compiler IR contract | **No fully demonstrated owner yet**; current stabilization carrier is `compiler/core/plan.py` | ISR-derived semantic graph → backend-neutral IR | unrepresentable semantics block lowering | schema completeness, canonicalization and coverage checks | IR schema/version/hash |
| Backend protocol and registry | `compiler/core/protocol.py`, `compiler/core/registry.py` | IR + selected backend → generated repository | capability mismatch rejects before emission | protocol conformance and capability-gate tests | backend identity/version and capability manifest |
| Backend-family emission | `compiler/backends/<family>/` | backend-neutral IR → target artifacts | unsupported semantic obligations refuse generation | native build + behavior + negative-case suite | source/plan/repository hashes, build logs |
| Full-stack orchestration | **Gap / not demonstrated as one canonical orchestrator**; campaign runner is certification execution, not automatically compiler orchestration | ISR + backend policy → coherent multi-family candidate | partial composition quarantined; no artifact publication on failed stage | full-stack vertical slice and fault injection | orchestration trace and artifact manifest |
| Verification and semantic conformance | `compiler/core/conformance.py`, `certification/stages/`, and independent verifier surfaces; exact precedence needs reconciliation | candidate + bound inputs → conformance/verification result | UNKNOWN is not PASS; corrupted/missing evidence blocks | independent semantic, build, runtime, security and negative tests | raw results, verifier identity, input/output hashes |
| Certification verdict and governance registry | `certification/governance/` and campaign/decision modules | evidence bundle → verdict and governed record | conflicting or regressed verdict blocks certification | registry regression, anti-vacuity and verdict-policy tests | verdict, phase/attempt ID, evidence refs |
| Evidence, provenance and lineage | `certification/evidence/`, `certification/provenance/`, and `tiannara/application/provenance/` | requirement→ISR→IR→artifact→deployment refs → verifiable chain | missing link/corrupt hash quarantines; secrets redacted | chain verification and lineage completeness | append-only event/manifest/hash chain |
| Execution and deployment infrastructure | `tiannara/infrastructure/`, deployment/runtime-specific backend modules | verified artifact + target → deployed instance/observations | fail/rollback must be explicit; no false deployment success | isolated execution, health checks, rollback and runtime smoke | environment, run ID, deployment ID, logs |
| Learning and knowledge retention | `learning/`, `knowledge/`, `tiannara/application/learning/` | verified observations/evidence → bounded knowledge updates | unverified observations cannot become authoritative facts | provenance validation and regression/replay | evidence source, confidence/status, update record |
| Generated applications and fixtures | `generated/`, `autonomous-api/`, and other explicit generated targets | generated repository/artifacts → runtime instance | never treat fixtures or templates as proof of compiler correctness | candidate-bound build/runtime tests | source lineage, artifact hashes, deployment evidence |
| Observability and operational API | `autonomous-api/app/` and related surfaces | runtime/campaign state → API/events/metrics | unavailable ISR or incomplete lineage must be explicit | endpoint contract, auth, sequence/lineage tests | correlation IDs, event hashes, errors |
| Plugin/backend extension boundary | `compiler/core/protocol.py` + registry | backend implementation → declared identity/capability/test spec | unknown capability defaults to unsupported | plugin conformance, isolation and malicious-plugin tests | signed/versioned backend manifest |

## 3. Concrete boundary crossings and findings

1. **ISR to plan:** `compiler/core/lowering.py` imports ISR node/edge types and behavior validators. This is expected direction for lowering, but the coverage of all ISR semantics must be explicit. The lowerer must not silently discard requirement relationships or semantic kinds it does not map.
2. **Plan to backend:** `compiler/backends/android.py` imports `isr.core.revision.ISRRevision` in addition to the plan and protocol. Its `compile()` consumes a plan, but its public helper `compile_isr_revision()` couples the backend module back to ISR. This is a boundary leak to evaluate and likely move to orchestration/adaptor code after the ADR is approved.
3. **Campaign to compiler and evolution:** `certification/campaign/plan_builder.py` imports the compiler lowerer, evolution constructors, requirement graph and ISR identity. This combines campaign workload construction with multiple pipeline stages. Clarify whether this is a benchmark harness or the canonical production orchestration surface; do not assume it is both.
4. **Campaign runner to application API:** `certification/campaign/runner.py` imports `app.engine.source_bound_full_stack` and verifier surfaces. This makes the execution boundary sensitive to Python path/bootstrap and package coupling; document it and test from a clean environment.
5. **Observation API to ISR:** `autonomous-api/app/main.py` defines `_DbGenerationProvider.get_isr()` as `NotImplementedError`. The API's ISR observation contract is therefore incomplete at this implementation point.
6. **Legacy/reference app versus compiler output:** `autonomous-api/` is a large source subtree, not automatically proof that the compiler can generate or certify it. Maintain explicit generated/reference-source labels and candidate-bound provenance.
7. **Certification authority:** Certification can consume and verify evidence but must not author ISR security obligations. Existing comments in `isr/core/graph.py` explicitly place security policy in ISR and certification as consumer; preserve this boundary.

## 4. Required contract inventory for FS-01/02/03

| Contract | Owner to ratify | Minimum inputs/outputs | Failure behavior | Verification/evidence |
|---|---|---|---|---|
| ISR ↔ Compiler IR (FS-01) | ISR owner + compiler architecture owner | schema IDs/versions, node/edge coverage, canonical forms and hashes | unknown semantic node or unbound relation blocks | mapping completeness, determinism, hashes and coverage report |
| Compiler orchestration (FS-02) | compiler orchestration owner (currently gap) | ISR, backend policy, seed/config → coherent artifact manifest and lineage | failed backend/partial family output quarantined | orchestration integration tests, fault injection, evidence trace |
| Backend/artifact contracts (FS-03) | one owner per backend family, common protocol owner | IR obligations → declared artifacts/tests/evidence | unsupported obligation refuses | native build, behavioral tests, independent verifier |
| Certification/evidence contract | certification governance owner | bound candidate, verifier results → verdict/evidence record | UNKNOWN/corrupt/incomplete chain cannot pass | ledger verification, anti-vacuity and regression tests |
| Deployment/runtime contract | deployment/infrastructure owner | verified artifact and environment → deployment/runtime observations | rollback and unhealthy deployment are non-success | health/lifecycle/rollback tests and deployment evidence |

## 5. Unresolved ownership questions

- Is `CompilationPlan` only a transitional projection, or the first canonical Compiler IR version? Existing contract language indicates stabilization status, so this draft treats canonical IR ownership as unresolved.
- Which module owns full-stack orchestration, distinct from campaign execution and benchmark harnessing?
- Which ledger is authoritative for immutable requirement-to-deployed-artifact lineage across the full compiler path?
- Which deployment surface owns the actual deployed-instance identity and post-deploy observation?
- Which contract is authoritative for unknown ISR primitives and evolution proposals that require new schema semantics?

## 6. Status

**Boundary Integrity: PARTIAL.** Several concrete seams exist, but cross-boundary dependency enumeration is not exhaustive for all modules in the nine roots. Ownership is proposed where source evidence is strong and explicitly marked unresolved where it is not.


## 7. Dependency-crossing register (source inspection supplement)

**Completeness:** BOUNDED / PARTIAL. This register records concrete crossings confirmed by source inspection; it is not a complete static dependency graph. Dynamic imports, indirect dependencies, test-only edges, packaging configuration and imports outside the inspected files may be missing.

| ID | From → to | Observed relationship | Assessment / required disposition |
|---|---|---|---|
| DEP-01 | `compiler/core/lowering.py` → `isr/core/{behavior,graph,revision}.py` | Lowerer consumes ISRRevision, graph enums and behavior validation. | Expected adapter direction; FS-01 must define coverage for every node, edge and payload and fail closed for unknown semantics. |
| DEP-02 | `compiler/backends/android.py` → `isr/core/revision.py` and `compiler/core/lowering.py` | Android backend imports ISRRevision and lowering helpers; a source-bound helper is exposed from the backend module. | Boundary leak; after ADR approval, consider moving source binding/lowering to orchestration/adapter layer with compatibility tests. |
| DEP-03 | `compiler/backends/_naming.py` → `compiler/core/plan.py` | Backend helper consumes shared plan carrier. | Acceptable only while plan remains target-neutral. |
| DEP-04 | `compiler/backends/react_frontend.py` → `compiler/core/{capabilities,plan,repository}.py` | Frontend backend consumes shared plan/capability/repository contracts. | Expected direction; require versioned capability and conformance tests. |
| DEP-05 | `compiler/composition.py` → `compiler/core/registry.py` and concrete backend implementations | Composition root wires registry and emitters. | Appropriate if registry/core do not import concrete emitters; verify by static scan. |
| DEP-06 | `certification/campaign/plan_builder.py` → compiler lowering, evolution, genesis, ISR and requirement graph | Campaign builder constructs workload artifacts across multiple domains. | Mixed responsibility; distinguish campaign construction from production orchestration. |
| DEP-07 | `certification/campaign/runner.py` → `app.engine.source_bound_full_stack` | Runner imports application-engine verifier via package bootstrap. | Packaging/path coupling; test clean-checkout execution and consider a stable verifier protocol. |
| DEP-08 | `compiler/core/{protocol,conformance,capabilities,authorization,behavior_oracle}.py` → `compiler/core/plan.py` | Shared contracts and validators operate on CompilationPlan. | Stabilization carrier coupling; canonical IR contract/version is not yet demonstrated complete. |
| DEP-09 | `certification/campaign/verdict.py` → `compiler/core/protocol.py` | Campaign verdict logic imports backend protocol definitions. | Potential ownership inversion; keep certification authority independent of backend protocol constants. |
| DEP-10 | `autonomous-api/app/main.py` → app-local ISR observation provider | `_DbGenerationProvider.get_isr()` raises `NotImplementedError`. | Concrete incomplete observation contract; authoritative ISR store and API contract remain to be assigned. |

### Required completion of the dependency audit

1. Pin exact source commit and tool versions.
2. Run a repository-wide static import/dependency scan over production code, tests, scripts and packaging configuration; include dynamic imports and path manipulation.
3. Classify edges as allowed, conditional, legacy, test-only or violation; identify owner and evidence for each exception.
4. Validate results with targeted searches and clean-environment tests.
5. Reconcile all crossings against the chosen boundary and update this matrix before FS-00 closure.

**Boundary Integrity remains PARTIAL.** These ten confirmed crossings are not evidence that every crossing has been found.


### 8.1 ISR model-family and envelope reconciliation — live source review

The earlier three-family count was incomplete. Inspection of the pinned source tree identifies **at least five distinct ISR model definitions/envelopes**. This is a source-surface count, not a claim that all five are active production authorities:

| ID | Definition | Shape / known consumers | Existing disposition evidence |
|---|---|---|---|
| ISR-F01 | `isr/core/{graph,revision}.py:ISRRevision` | Frozen Pydantic revision over typed `ISRGraph`; consumed by root lowering, campaign planning, genesis, evolution and ISR stores/adapters. | `folder/POST_R1_D_AUTHORITY_MAP.md` names `isr/core` canonical. |
| ISR-F02 | `constitutional_architecture/isr/model/isr.py:ISR` | Immutable dataclass over `System`/modules/entities/services/workflows/policies/interfaces/events; has separate serializer, deserializer, snapshot/versioning and Gen-C pipeline. | R1-D1 disposition marks model/runtime RETIRE; semantic validators selectively migrated/deferred. |
| ISR-F03 | `constitutional_architecture/core/models/isr.py:UniversalISR` | Pydantic graph with `ISRNode.semantic_attributes`, edge list, intent/genome hashes and a 17-node/13-edge vocabulary in the associated R1 inventory. Consumed by `core/pipeline/isr_transpiler.py`, `core/orchestrator/*`, `core/registry/*`, `compilers/*`, and projection/conformance adapters. | R1-D1 disposition marks RETIRE; later boundary documents call category compilers legacy/test-only. |
| ISR-F04 | `constitutional_architecture/core/models/universal_isr.py:UniversalISR` | A second class with the same exported class name, but a different, smaller model: eight node kinds, node-level `dependencies`, no typed edge list, version and metadata. Exported by `constitutional_architecture/core/__init__.py`; imported by `core/governance.py` and a test. | Not separately identified in the prior ISR disposition table; exact intended relationship to ISR-F03 is unresolved. |
| ISR-F05 | `tiannara/domain/models/isr.py:IntermediateSoftwareRepresentation` | Separate Pydantic ISR envelope with a legacy flat shape and an additive `system_model.v1` payload; typed architectural content is nested as `SystemModel`. Produced by the Tiannara intent synthesis path and consumed by `ProjectCompiler`, which calls `isr.system_model()` then backend `generate(system_model)`. | Not assigned an explicit row/disposition in the R1 authority map or ISR legacy-disposition table inspected. |

`SystemModel` is the typed payload within ISR-F05, not counted as a sixth outer ISR envelope. Its semantics and canonical hash still require comparison with ISR-F01; it must not be assumed equivalent because both are described as technology-neutral.

### 8.2 Compiler/runtime paths and active-surface distinction

The source tree contains at least five distinct compilation execution surfaces:

1. **Root campaign/compiler path:** `ISRRevision → isr_to_plan → compiler.core.CompilationPlan → compiler.core.CompilerBackend → GeneratedRepository → certification stages`.
2. **Standalone root UniversalCompiler API:** `compiler/api.py` and `compiler/kernel.py` accept a raw dictionary ISR payload, apply a minimal field validator, resolve a separate backend registry and package output. This is a separate contract from `ISRRevision → CompilationPlan`; its actual deployment/use must be proven independently.
3. **Constitutional Gen-C pipeline:** rich constitutional `ISR → CompilerContext → eight-pass pipeline → BIR → backend/artifacts`; `intent_entrypoint.py` also exposes source projection/binding into this pipeline. Tests and engine bridge imports remain in the tree despite the R1 retirement classification.
4. **Per-category compiler/orchestrator path:** `UniversalISR` (ISR-F03) + `ArchitectureGenome` → category compiler contracts → `CompilationBundle` / `SystemDeploymentBundle`. R1 records classify this as legacy/retirement-path; the current source still contains the compiler implementations and consumers.
5. **Tiannara application compiler path:** `IntermediateSoftwareRepresentation` → typed `SystemModel` → requirement derivation/backend selection → `generate(system_model)` → `CompilationResult` → verifier/materializer. The CLI imports `build_project_compiler`; this path is not the root `ISRRevision`/root `CompilationPlan` pipeline.

A related adapter/conformance surface under `tiannara/application/compilation/` constructs ISR-F03 `UniversalISR` values from `BackendSemanticModel` projections to exercise older category backends. That is an explicit bridge to a legacy input contract, but the authority and lifecycle of this bridge are not reconciled in the R1 authority map.

**Important distinction:** static imports, CLI wiring, API construction, tests and historical architecture documents prove that code paths exist; they do not by themselves prove which path is deployed as the production default. A runtime-entrypoint and deployment-configuration audit is still required. Conversely, labeling a path LEGACY or RETIRE in a document does not prove all imports, adapters, test dependencies or public entry points have been removed or safely fenced.

### 8.3 Root ISR-to-plan mapping evidence

The current `isr/core/graph.py` declares 14 node kinds and 18 edge kinds. Direct inspection of `compiler/core/lowering.py` shows dedicated carriers for 10 node kinds; `DOMAIN`, `CAPABILITY`, `INFRASTRUCTURE_TARGET` and `REQUIREMENT_REF` have no dedicated plan carrier in this lowerer. The lowerer handles 10 edge kinds in some form, but not all semantics are preserved: requirement relation edges, `SATISFIES`, `IMPLEMENTED_BY`, `DEPENDS_ON` and `REQUIRES_INVARIANT` are not represented as first-class plan relations. `CONTAINS` is used for route-to-interaction ownership, not preserved as a general ownership relation.

Two ambiguity gaps are directly visible in the lowerer:
- A frontend interaction gets a target API only when exactly one `INVOKES` target resolves in the API index; zero, multiple or service targets result in `target_api_operation=None` rather than an explicit rejection.
- An API may retain `service_id=None` when no `EXPOSES` binding exists; the code rejects multiple distinct service bindings, but does not reject the missing binding at this lowering point.

The `REQUIRES_INVARIANT` edge is declared in the ISR taxonomy but is not consumed in the current edge loop; invariants are carried as a list without a corresponding source-to-invariant binding carrier. These are source-inspection findings, not executed test results.

### 8.4 Authority and migration contradiction to reconcile

R1 documents establish a prior governance direction: `isr/core` is canonical; the rich constitutional ISR and both `UniversalISR` models are classified for retirement; per-category compilers are described as legacy/test-only. That direction is important evidence and must not be silently overridden.

However, the current source also contains:
- a separate `UniversalISR` definition in `core/models/universal_isr.py` not separately listed in the legacy disposition table;
- `IntermediateSoftwareRepresentation` / `SystemModel` used by the Tiannara application compiler path;
- source-level imports and adapter/conformance code that still consume the legacy model families;
- a source/compiler path inventory that distinguishes several compiler entrypoints, not just the root campaign compiler.

Therefore the prior authority decision does not yet constitute a complete migration/retirement proof for every extant ISR-shaped contract. FS-00 must reconcile these exact surfaces, record which are retained as compatibility adapters versus retired, and prove their runtime reachability is either intentionally governed or fenced. No model consolidation, deletion, adapter rewrite or schema change is authorized by this audit addendum.

**Boundary Integrity remains PARTIAL. System-wide producer/consumer and deployment reachability inventory remains INCOMPLETE.**


## 8. PR-head boundary verification — 2026-11-03

The following direct source paths were confirmed at PR-head commit `78283fff71ba616832269cea1b862a08481f48b6`. These are observed crossings, not approved ownership assignments.

| Source boundary | Observed input → output | Boundary issue / required control |
|---|---|---|
| Intent extraction → constitutional compilation | `IntermediateSoftwareRepresentation.system_model()` → `project_intent_to_constitutional_isr` → rich constitutional `ISR` → Gen-C `CompilerPipeline` | Source/graph/SystemModel binding is checked, but this path does not first convert to root `ISRRevision`; reconcile with the canonical ISR authority decision |
| Intent extraction → Tiannara ProjectCompiler | `IntermediateSoftwareRepresentation` → typed `SystemModel` → capability plan → `backend.generate(SystemModel)` | Separate plan, backend protocol, result and verification boundary; semantic equivalence to root ISR and Gen-C is not established |
| Root ISR → root compiler | `ISRRevision` → `CompilationPlan` → `CompilerBackend` → `GeneratedRepository` | Canonical path candidate; still requires total semantic coverage and per-backend conformance evidence |
| Raw compiler HTTP API → UniversalCompiler | `CompilationRequest.isr` payload → independent validation/kernel/optimization/backend/package path | Separate externally reachable API surface; deployment exposure, source binding, authorization and evidence parity need verification |
| Graph UniversalISR → category compilers | `UniversalISR + ArchitectureGenome + context` → `CompilationBundle` | Legacy disposition is documented, but actual call reachability and fencing need proof |
| Rich ISR → evolution graph | rich `ISR` ↔ `TypedGraph` via `engine/isr_adapter.py` | Adapter is for evolution representation; no canonical root-ISR bridge is demonstrated |

### 8.1 Cross-cutting ownership gaps

- **ISR authority enforcement:** documentation identifies `isr/core` as canonical, but at least three compiler-facing paths consume other model envelopes directly. Governance ownership and runtime enforcement are therefore different states and must be tracked separately.
- **Model identity and immutability:** frozen root/rich models coexist with mutable UniversalISR models and a mutable typed Tiannara envelope. No common versioned conversion contract or hash-equivalence proof was established.
- **Compiler verdict authority:** root backend conformance, Gen-C pass diagnostics, Tiannara bundle verification and UniversalCompiler output validation are separate evidence producers. A shared certification authority and normalized failure semantics have not been demonstrated.
- **Partial projection boundary:** the SystemModel-to-rich-ISR projection does reject known unsupported/incomplete source declarations. That is a useful fail-closed boundary, but it must not be mistaken for a proof that the rich ISR is equivalent to canonical root ISR or that BIR preserves the rich ISR semantics.
- **Runtime status classification:** a path appearing in a package, registry or API factory is evidence of source-level availability, not proof it is deployed or invoked in production. Production, compatibility, test-only and dead-code classifications remain OPEN until import-walk, CLI/API/deployment configuration and clean-environment execution evidence are gathered.

**Boundary disposition:** no ownership changes, model consolidation, adapter creation, route retirement or deletion is authorized by this audit. FS-00 remains NOT READY pending the full reachability and semantic-preservation register plus independent governance review.


## 9. Accepted target authority boundary and backend capability preservation — 2026-11-04

**Independent reviewer decision: ACCEPT.** The target architecture is one governed compilation authority and one authoritative canonical ISR contract. This is an accepted direction, not a claim that current code already conforms.

### Responsibility allocation required by the target architecture

- **Canonical ISR authority:** owns the authoritative, versioned software intent/requirements semantics, integrity rules and provenance binding. Alternate ISR-shaped models may exist only as governed projections, compatibility forms or explicitly approved extensions; they must not independently redefine source intent.
- **Compilation authority:** owns admission, canonical-source binding, validation, transformation orchestration, backend authorization/selection, artifact quarantine/publication, verification coordination and evidence-backed final outcomes.
- **Transformation/adapter:** owns deterministic, versioned and inspectable mappings between canonical ISR, compiler IR, intermediate/backend models and artifacts. It may not silently discard or reinterpret semantics.
- **Backend family:** owns target-specific emission/build integration and declares its target/version/feature coverage, semantic obligations, unsupported constructs, toolchain identity, artifacts and conformance evidence. It does not own canonical requirements or bypass central governance.
- **Independent verifier/certifier:** evaluates bound evidence and issues a verdict independently of the backend's own success claims. Backend output alone is not certification.

### Universal capability is preserved independently of implementation count

A backend is an implementation, not the target capability itself. ESAP's universal language/framework/platform ambition remains a governing requirement. Multiple specialized backends are expected and permitted under the common contract. A single implementation need not emit every target.

No backend may be consolidated, replaced, deprecated, retired or deleted merely to simplify the architecture. Each disposition requires the Target Capability Preservation Matrix, consumer and dynamic/deployment reachability evidence, semantic/behavioral parity evidence, migration/rollback plan and independent approval. Where no verified implementation exists, retain the target in the capability roadmap and mark it NOT YET IMPLEMENTED / NOT CERTIFIED. Do not equate code presence with support or unsupported status with an intentional permanent removal.

### Prohibited authority patterns

- backend-local validation that overrides or weakens canonical governance;
- backend-specific ISR contracts treated as independent sources of truth;
- a wrapper that delegates to parallel compilers without central policy, lineage and verdict enforcement;
- silent lossy projection, semantic defaulting or unsupported-feature omission;
- artifact publication after failed, incomplete or indeterminate validation;
- retirement that removes a unique language/framework/platform capability without an accepted replacement or separately approved roadmap decision.

**Status:** target responsibility allocation accepted; current ownership, route convergence, backend conformance and capability preservation remain unproven. No code/schema changes, backend retirement or FS-01 work is authorized by this section. FS-00 remains NOT READY until the complete route/consumer inventory, capability matrix, semantic-preservation evidence and independent review are complete.


## Frontend/backend hardening responsibility split — 2026-11-04

The reviewer has clarified that frontend compiler hardening is complete as a workstream, while backend compiler hardening remains outstanding. This does not grant frontends exemption from per-target evidence or imply that they are independently certified. It does establish a separate remaining backend-hardening obligation.

**Frontend responsibility:** maintain the hardened frontend contract and per-target evidence; preserve route, component, interaction, state-transition and API-integration semantics; reject unsupported interactions; prove generated-project build and meaningful tests; keep runtime, security and independent semantic verification as separate evidence dimensions.

**Backend responsibility (outstanding):** every backend implementation must be brought under the same governed input, capability enforcement, semantic preservation, authorization, effect, artifact quarantine, build/runtime, security and independent-verification obligations. A backend declaration or registry registration is not enforcement. Unsupported semantics must be rejected before backend invocation and must not produce deliverable artifacts.

**Cross-stack responsibility:** full-stack composition must prove that frontend routes/interactions bind to real backend API operations, data contracts, authorization and effects. A hardened frontend paired with a backend that omits or weakens those obligations is not a conformant application.

The two Android implementations are separate audit entries: the Tiannara ProjectCompiler `AndroidBackend` and root campaign `AndroidStructuralBackend`. Their common target platform does not make them one implementation or prove convergence.

**Status:** backend hardening remains open. This is an FS-00 responsibility clarification only; no code/schema change, FS-01 work, backend retirement, merge or certification upgrade is authorized.
