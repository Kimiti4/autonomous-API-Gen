# FS-00 Deliverable 3 — ISR / Evolution Audit

**Status:** REVIEW DRAFT — no schema change authorized  
**Source commit:** `68696e2a07595fed98a19e24ee96c3e4e0e5bfeb`  
**Companion:** Deliverables 1, 2 and 4 in this directory.

## 1. Verdict against the Full-Stack Compiler acceptance criterion

**Current ISR supports a meaningful subset of full-stack architecture semantics, but it does not yet demonstrate complete, lossless, independently verifiable full-stack compilation.** Keep ISR schema frozen during FS-00. This is an audit finding, not permission to add primitives.

The acceptance criterion requires deterministic lowering from validated technology-neutral ISR through Compiler IR into one complete full-stack application, followed by verification, immutable evidence and requirement-to-deployed-artifact lineage.

## 2. Current semantic surface

At the inspected source commit, `isr/core/graph.py` declares 14 node kinds:

`DOMAIN`, `CAPABILITY`, `SERVICE`, `API`, `DATA_MODEL`, `EVENT`, `SECURITY_POLICY`, `INFRASTRUCTURE_TARGET`, `REQUIREMENT_REF`, `FRONTEND_ROUTE`, `FRONTEND_INTERACTION`, `EFFECT`, `INVARIANT`, `CONSEQUENCE`.

It declares 18 edge kinds:

`SATISFIES`, `IMPLEMENTED_BY`, `EXPOSES`, `PERSISTS`, `PUBLISHES`, `CONSUMED_BY`, `DEPENDS_ON`, `SECURED_BY`, `CONTAINS`, `ROUTES_TO`, `INVOKES`, `CAUSES_EFFECT`, `REQUIRES_INVARIANT`, `CONSEQUENCE_OF`, `REQUIREMENT_DEPENDS_ON`, `REQUIREMENT_CONFLICTS_WITH`, `REQUIREMENT_REFINES`, `REQUIREMENT_OWNED_BY`.

Typed behavior payloads exist for service, API, data model, event, security, effect, frontend route, frontend interaction, invariant and consequence semantics. `ISRRevision` binds graph identity/provenance/content hash and validation surfaces.

This is a stronger source model than the older R1 inventory's nine-node description; the historical report must not be treated as current without reconciliation.

## 3. Lowering coverage and preservation risks

The inspected `compiler/core/lowering.py` constructs carriers for data models, events, security policies, APIs, effects, invariants, consequences, effect bindings, services, frontend interactions and routes. It preserves typed behavior payloads for these supported carriers and rejects some ambiguous bindings, including API operations with multiple explicit service bindings and consequences without explicit targets.

However:

- `DOMAIN`, `CAPABILITY`, `INFRASTRUCTURE_TARGET` and `REQUIREMENT_REF` do not become dedicated first-class `CompilationPlan` carriers in the inspected lowerer.
- Requirement relationships (`REQUIREMENT_DEPENDS_ON`, `REQUIREMENT_CONFLICTS_WITH`, `REQUIREMENT_REFINES`, `REQUIREMENT_OWNED_BY`) do not appear as first-class plan relations in the inspected model.
- General `CONTAINS` ownership semantics are not uniformly represented; the lowerer uses it to collect interactions owned by frontend routes.
- The plan carrier for `FrontendInteraction` resolves its target API only when exactly one `INVOKES` target exists; the inspected code does not reject all non-singleton cases, which warrants a loss/ambiguity test.
- The lowering docstring describes a loss-aware projection, but the presence of typed carriers alone does not prove semantic equivalence. Every unsupported or unrepresented construct needs an explicit reject, policy-gated omission or a proven lossless representation.
- Determinism must be tested across mapping order, canonical serialization, seed/backend policy and artifact packaging; the source snapshot alone does not establish byte-identical full-stack output.

## 4. Android benchmark implications

The Android backend is `STRUCTURAL`, has an empty certified feature set, and enforces a static-shell-only check. It rejects service/API/event/security/effect/effect-binding/consequence/invariant/frontend route and interaction constructs, and typed data-model behavior. Consequently it cannot implement the complete ESAP-APP-001 behavior.

The benchmark requires an actual native app, candidate-bound runtime UI tests, before/after durable-state assertions, process relaunch, offline emulator execution, negative-case coverage, source-to-plan lineage, independent semantic verification and reproducible CI. No end-to-end APK/emulator evidence was established in this audit session. Unit tests using fake subprocesses or synthetic APK ZIPs are not runtime evidence.

Benchmark-specific missing semantics requiring explicit contracts before implementation include:
- case-insensitive local search behavior and oracle;
- durable local-store guarantees and observable state;
- process death/relaunch lifecycle;
- offline behavior;
- UI state/interaction semantics and accessibility selectors;
- acceptance oracles and independent semantic verifier binding.

These are benchmark requirements, not a recommendation to add ISR primitives during FS-00. First determine whether existing typed contracts can express them; otherwise FS-01 must define and govern any schema evolution after this gate.

## 5. Evolution boundary

The evolution engine can construct candidate genomes and decision spaces, but the existence of candidate/mutation/fitness modules does not prove that a candidate preserves the ISR contract, that an evolved design is compilable, or that a proposed self-modification is authorized.

Required safeguards:
- evolution proposes candidates; it does not authorize its own protected schema/compiler changes;
- candidates must bind to parent ISR/genome hashes and explicit mutation operators;
- unknown semantics or missing verification evidence are not accepted as valid fitness improvements;
- certification consumes security obligations and evidence; it must not invent ISR security requirements post hoc;
- a generated artifact's fitness cannot substitute for correctness, security or constitutional approval;
- mutation and rollback must be replayable and auditable.

## 6. Lineage and evidence findings

The target lineage is `requirement_id → requirement_graph_node → isr_node → compiler_ir_node → backend_artifact → deployed_instance`.

Current source provides identity/hash structures and campaign provenance/verifier surfaces, but this audit has not established a complete authoritative, immutable chain spanning every step through a deployed Android instance. `autonomous-api/app/main.py`'s `_DbGenerationProvider.get_isr()` raises `NotImplementedError`, an explicit ISR observation gap. This is not enough to conclude all lineage is absent; it is enough to prevent claiming the observation surface is complete.

Unknown/corrupt/missing evidence must not yield PASS. The backend must reject unsupported semantics; the orchestration/certification boundary must quarantine partial output and retain source, plan, repository, verifier and runtime hashes.

## 7. Findings register

| ID | Finding | Severity | Required disposition |
|---|---|---|---|
| ISR-A01 | Historical R1 node inventory is stale relative to current 14-node/18-edge source | High | Reconcile all older inventory assertions against pinned current source |
| ISR-A02 | Several ISR node kinds and requirement relationships lack first-class plan representation | Critical | FS-01 contract must define complete coverage or explicit fail-closed behavior |
| ISR-A03 | `CONTAINS` is not represented as general ownership in the plan | High | Specify ownership mapping and test preservation |
| ISR-A04 | Frontend interaction target ambiguity may not fail closed for non-singleton targets | High | Add negative test and contract requirement in a later authorized implementation phase |
| ISR-A05 | CompilationPlan is transitional/stabilization IR, not proven canonical full-stack IR | Critical | Resolve in Compiler Architecture ADR and FS-01 |
| ISR-A06 | Android backend is structural-only and refuses benchmark behavior | Critical | Build behaviorally capable backend only after FS-00/FS-01 authorization |
| ISR-A07 | No candidate-bound end-to-end Android runtime evidence established | Critical | Obtain real SDK/Gradle/emulator or approved cloud runner evidence; never simulate |
| ISR-A08 | Complete requirement-to-deployed-instance lineage not demonstrated | Critical | Define evidence contract, verify every edge and expose lineage query |
| ISR-A09 | Observation API ISR binding raises NotImplementedError | High | Assign owner and reconcile with authoritative ISR store |
| ISR-A10 | Evolution fitness/candidate existence does not prove governance or semantic preservation | High | Bind proposals to constitutional authorization and independent verification |

## 8. Required follow-on contract topics

- FS-01: ISR and Compiler IR schema IDs/versions, canonical forms, hashes, node/edge coverage, behavior contracts, unknown-kind policy and migration/versioning.
- FS-02: orchestrator inputs/outputs, deterministic backend selection, composition, partial failure/quarantine, evidence integrity and retry/idempotency.
- FS-03: backend family input obligations, artifact manifest, build/runtime/negative tests, independent semantic verification and evidence schema.
- Certification: verifier identity, anti-vacuity, unknown-state handling, source/candidate binding and immutable verdict record.
- Evolution: proposal versus approval authority, parent-child lineage, rollback and reproducible candidate evaluation.

## 9. FS-00 status

**ISR/Evolution Audit: PARTIAL; acceptance criterion not demonstrated.** Do not change ISR schema or add backend semantics in this phase. Reconcile these findings with Deliverables 1, 2 and 4 and submit for independent review.


## 8. Phase 31 / B3-v2 closeout reconciliation

The Phase 31 closeout ADR records B3-v2 as **NOT_CERTIFIED**: 443 trials completed against a planned 936 before the 12-hour runtime budget expired. This is a campaign verdict, not proof that all Phase 31 implementation is invalid; equally, passing Tier A / certification tests does not upgrade the B3-v2 campaign verdict. The closeout states the ledger chain is intact and distinguishes Phase 31 implementation completeness from B3 campaign certification.

**Effect on FS-00:** the B3-v2 verdict is an input to this ISR/Evolution audit, not the FS-00 output. It does not authorize schema changes or imply evolutionary/compiler capability is certified. The evidence supports keeping the ISR schema frozen during FS-00 and treating candidate/evolution-to-ISR transformations as requiring explicit lineage and verification. Any future claim that relies on B3 certification must remain blocked until a separately authorized campaign achieves its acceptance target and produces verified evidence.

**Evidence reference:** `folder/PHASE31_CLOSEOUT_ADR.md`, sections 2–3 (443 completed; NOT_CERTIFIED; runtime budget exhausted) and the ledger/chain integrity record. No new campaign was run in this audit.


## 9. ISR model-family and compiler-runtime authority reconciliation

The earlier count of three ISR model families was incomplete. The pinned source tree contains **at least five distinct ISR model definitions/envelopes**. They are not interchangeable, and their existence does not imply equal production status.

1. **Root typed ISR — `isr/core`:** `ISRGraph` + frozen, content-addressed `ISRRevision`; 14 node kinds and 18 edge kinds in the inspected source. Root lowering, campaign planning, genesis, evolution and stores/adapters consume it.
2. **Constitutional rich ISR — `constitutional_architecture/isr/model/isr.py:ISR`:** immutable dataclass over `System` and rich module/entity/service/workflow/policy/interface/event structures; separate serialization, deserialization, versioning and Gen-C pipeline. Existing R1-D1 records classify the model/runtime RETIRE, while source imports remain in compiler, engine, verification, snapshot and evolution-related modules.
3. **Graph `UniversalISR` — `constitutional_architecture/core/models/isr.py`:** Pydantic graph with `ISRNode.semantic_attributes`, typed edge list, intent/genome hashes and a distinct 17-node/13-edge vocabulary in the R1 inventory. It feeds a separate `ArchitectureGenome + UniversalISR → CompilationBundle` per-category compiler/orchestrator contract and Tiannara projection/conformance adapters. Existing R1 records classify it RETIRE / legacy.
4. **Second `UniversalISR` — `constitutional_architecture/core/models/universal_isr.py`:** a separate class with the same exported class name but a different eight-node, dependency-list model and no typed edge list. It is exported from `constitutional_architecture/core/__init__.py` and used by `core/governance.py` plus tests. The earlier disposition table did not identify this second definition separately.
5. **Tiannara ISR envelope — `tiannara/domain/models/isr.py:IntermediateSoftwareRepresentation`:** Pydantic envelope retaining a legacy flat payload and supporting a `system_model.v1` typed payload nested as `SystemModel`. The Tiannara intent compiler creates this envelope; `ProjectCompiler` reads `system_model()`, plans backend generation from the typed model and receives `CompilationResult`. The Tiannara CLI imports the project compiler composition root. This envelope is not assigned a clear disposition in the R1 ISR authority/disposition documents inspected.

`SystemModel` is the typed payload inside the fifth envelope, not counted as a sixth outer ISR. Its schema, canonicalization and semantic correspondence to the root ISR remain unproven.

### 9.1 Existing authority decision versus implementation evidence

The R1 authority map and canonical ISR contract establish a prior decision that `isr/core` is the single canonical ISR authority. R1-D1 classifies the rich constitutional ISR and graph `UniversalISR` as RETIRE, and R1-D follow-up records describe the category compilers as legacy/test-only. This is a governance decision and must be respected unless explicitly superseded by an authorized decision.

The current source nevertheless contains additional or still-reachable surfaces:
- the second `UniversalISR` class in `core/models/universal_isr.py`, not separately classified in the disposition table;
- the Tiannara `IntermediateSoftwareRepresentation` / `SystemModel` envelope used by the separate ProjectCompiler/CLI path;
- a `tiannara/application/compilation` projection/conformance adapter that constructs the legacy graph `UniversalISR` for backend conformance;
- rich-ISR Gen-C pipeline, source-binding entrypoint, engine bridge and serializer/versioning code, despite the retirement classification;
- a standalone root `compiler/api.py` / `compiler/kernel.py` path accepting a dictionary ISR envelope with a minimal pre-compilation validator, separate from `ISRRevision → CompilationPlan`.

These findings do not prove that every legacy surface is a production default. They do prove that a documentation-only retirement classification is not, by itself, a complete runtime-reachability, compatibility or deletion proof. The audit must distinguish production entrypoints, explicitly invoked compatibility adapters, test-only references, historical modules and unreachable code using import-walk, CLI/API wiring, packaging, deployment configuration and clean-environment execution evidence.

### 9.2 Root ISR-to-CompilerPlan coverage is still incomplete

The inspected root lowerer constructs carriers for 10 of the 14 declared node kinds. It does not provide first-class plan carriers for `DOMAIN`, `CAPABILITY`, `INFRASTRUCTURE_TARGET` or `REQUIREMENT_REF`. It consumes 10 of 18 edge kinds, but does not preserve requirement dependency/conflict/refinement/ownership edges, `SATISFIES`, `IMPLEMENTED_BY`, `DEPENDS_ON` or `REQUIRES_INVARIANT` as first-class plan relations. General `CONTAINS` ownership is reduced to the frontend-route/interaction case.

The lowerer also does not fail closed for every ambiguous or missing binding:
- `INVOKES` produces a target only when exactly one target is an API; zero, multiple or service targets leave `target_api_operation=None`.
- API service ownership is rejected when multiple distinct `EXPOSES` sources exist, but missing ownership may remain `service_id=None`.
- Invariants are carried as a collection, but the `REQUIRES_INVARIANT` edge is not mapped into a source-bound invariant binding.

The presence of typed behavior carriers and fail-closed checks for some bindings does not establish total semantic preservation. These uncovered constructs remain blockers for claiming the current `CompilationPlan` is a complete canonical Compiler IR.

### 9.3 Compiler paths requiring one governed disposition

At least five compilation surfaces must be reconciled:

1. Root campaign path: `ISRRevision → isr_to_plan → CompilationPlan → compiler.core backend → GeneratedRepository → certification`.
2. Standalone root UniversalCompiler API: raw dictionary ISR → minimal validator → separate backend registry/kernel → packaged output.
3. Constitutional Gen-C: rich constitutional ISR → BIR → Gen-C backend/pipeline and source-binding entrypoint.
4. Per-category compiler/orchestrator: graph `UniversalISR` + `ArchitectureGenome` → category compilers → `CompilationBundle` / `SystemDeploymentBundle`.
5. Tiannara ProjectCompiler: `IntermediateSoftwareRepresentation` → `SystemModel` → capability-derived plan → backend `generate()` → `CompilationResult` → verification/materialization.

The `tiannara/application/compilation` backend-conformance path additionally adapts a semantic projection into the legacy `UniversalISR` input shape. Its relationship to the Tiannara ProjectCompiler and root canonical compiler must be established rather than assumed.

### 9.4 Required resolution before FS-00 can close

- Reaffirm or amend the existing canonical authority decision through the authorized governance process; this audit does not make that decision.
- Add the two distinct `UniversalISR` definitions and the Tiannara `IntermediateSoftwareRepresentation` envelope to the authoritative inventory and migration register.
- Trace each model's producers, consumers, serializers/deserializers, persistence, hashes, schema migrations, API/CLI entrypoints, tests, packaging and deployment reachability.
- Determine whether `SystemModel` is a one-way projection, an independent semantic authority or a transitional typed payload; prove correspondence to canonical ISR before it can authorize compilation.
- Reconcile the per-category conformance adapter with the retirement decision; specify whether it is an approved, bounded legacy bridge, test-only harness or prohibited path.
- Prove all RETIRE classifications are actually fenced from canonical production entrypoints, while preserving any explicitly authorized compatibility adapter with versioned semantics and rollback.
- For every conversion, test semantic preservation for security policy, requirements, effects, invariants, consequences, deployment intents, provenance and evolution metadata. Unknown or unrepresentable semantics must block conversion.

**System-wide ISR/compiler authority: GOVERNANCE DIRECTION EXISTS (`isr/core` canonical), BUT IMPLEMENTATION/MIGRATION RECONCILIATION IS INCOMPLETE.** Architectural Evidence, Contract Completeness and Boundary Integrity remain PARTIAL. No schema changes, model consolidation, deletion, adapter rewrite or legacy retirement are authorized by this audit.


## 10. PR-head source verification — 2026-11-03

This section supplements the earlier pinned-baseline inventory. It is based on direct reads from PR-head commit `058810c9a2027d009dd9f0f0f6291da30bbc0417` and its complete recursive Git tree (3,472 blobs; tree response reported `truncated=false`). It does not claim an exhaustive dynamic import/reachability proof. The source paths below are confirmed present at this PR head.

### 10.1 Five outer ISR/model envelopes remain distinct

The current source confirms five outer model families, not merely three:

| Family | Definition | Mutability / identity evidence | Direct compiler or system consumers confirmed |
|---|---|---|---|
| Canonical typed graph | `isr/core/revision.py:18-63`, `isr/core/graph.py` | Frozen Pydantic revision; create() invokes invariant + behavioral validation and computes content hash | `compiler/core/lowering.py` → `CompilationPlan`; campaign/evolution paths |
| Rich constitutional ISR | `constitutional_architecture/isr/model/isr.py:55-100`, `model/system.py` | Frozen dataclasses; semantic hash projects `system` | `constitutional_architecture/compiler/intent_entrypoint.py` and 8-pass Gen-C pipeline; serializer/deserializer and snapshot/versioning |
| Graph UniversalISR A | `constitutional_architecture/core/models/isr.py:9-104` | Pydantic graph; mutable node/edge collections and add_node/add_edge mutation methods; no frozen config/content-hash factory in this model | `constitutional_architecture/core/contracts/compiler.py` and `constitutional_architecture/compilers/backend/base.py`, consuming UniversalISR + ArchitectureGenome and returning CompilationBundle |
| Graph UniversalISR B | `constitutional_architecture/core/models/universal_isr.py:9-36` | Separate same-named class; eight node types, attributes and dependency lists; mutable Pydantic model and add_node mutation | Exported from core package and used by governance/tests; exact production compilation reachability remains to be proven |
| Tiannara envelope | `tiannara/domain/models/isr.py:53-125` | Mutable Pydantic envelope; dual legacy / `system_model.v1` payload; typed content is serialization-excluded by default and explicitly reinserted into typed hash; lineage excluded from hash | Intent compiler creates typed envelope; `ProjectCompiler.compile_intent` extracts SystemModel and invokes capability-selected backend generation |

Important distinction: the fifth envelope's `SystemModel` is not an instance of root `isr.core.ISRRevision`. It is a separate typed payload. The rich constitutional ISR is also not the root canonical graph revision. Therefore the existence of a canonical-authority decision in R1 documents does not demonstrate that every current compiler entrypoint actually crosses that canonical boundary.

### 10.2 Active-looking entrypoints demonstrate multiple direct routes

1. **Root typed compiler:** `ISRRevision → compiler.core.lowering.isr_to_plan → CompilationPlan → CompilerBackend → GeneratedRepository`. The protocol is in `compiler/core/protocol.py`; composition registers Python FastAPI, Rust Axum and Android structural backends (`compiler/composition.py`). This route is the clearest implementation of the canonical root ISR decision.
2. **Constitutional intent entrypoint:** `IntentCompiler.compile_full → IntermediateSoftwareRepresentation.system_model() → project_intent_to_constitutional_isr → rich constitutional ISR → CompilerPipeline`. The entrypoint performs source/graph/SystemModel binding and refuses projection blockers. This is meaningful fail-closed protection, but it compiles a rich constitutional ISR directly; no conversion into root `ISRRevision` is present in this entrypoint.
3. **Tiannara ProjectCompiler:** `IntermediateSoftwareRepresentation → SystemModel → derive_compilation_requirements → capability plan → backend.generate(SystemModel) → CompilationResult`. This is a distinct execution path from root `CompilationPlan` and from Gen-C.
4. **Universal Compiler HTTP API:** `compiler/api.py` exposes `/v1/compiler/validate` and `/v1/compiler/compile`; it constructs `UniversalCompiler` over a `CompilationRequest` ISR payload and its own backend registry/kernel/optimization/packaging. It is not the `ISRRevision → CompilationPlan` protocol.
5. **Per-category compiler contract:** `UniversalISR + ArchitectureGenome + context → CompilationBundle`, with category-specific compiler classes and a separate deployment bundle. Its graph model is distinct from both root `ISRRevision` and the second `UniversalISR`.
6. **Evolution graph adapter:** `constitutional_architecture/engine/isr_adapter.py` converts rich constitutional ISR to/from `TypedGraph`. This is an evolution representation bridge, not evidence of conversion to root canonical ISR.

The prior five-path list is therefore not the full active-entrypoint picture: the Universal Compiler HTTP API and the rich-ISR evolution graph adapter must be included in the boundary/reachability register.

### 10.3 Concrete semantic and assurance differences

- **Immutability is not uniform.** Root `ISRRevision` and rich constitutional ISR are frozen at their top-level model declarations. Both graph `UniversalISR` models and the Tiannara Pydantic envelope expose mutable state; the UniversalISR A model has mutating add_node/add_edge methods. Hash/provenance semantics cannot be assumed equivalent.
- **Hash scopes differ.** Root identity hashes schema version + graph; rich constitutional `semantic_content_hash` hashes the system projection; Tiannara typed-v1 envelope hashes the envelope plus typed content but excludes lineage. UniversalISR A carries intent/genome hash strings but has no demonstrated canonical content-hash contract in its model definition; UniversalISR B has metadata/version but no demonstrated content-hash contract.
- **Validation differs.** Root `ISRRevision.create` calls graph invariants and behavioral validation. Rich ISR exposes a family of semantic validators; the Gen-C validation pass now fails closed for missing/incomplete source binding, projection errors and validator exceptions. UniversalISR A's model-level add_edge checks endpoint existence but does not establish full typed edge compatibility or semantic validation. UniversalISR B's add_node checks duplicate IDs but no complete graph validation is present in the inspected model.
- **Rich projection is intentionally partial.** `project_intent_to_constitutional_isr` preserves requirement nodes/relations and maps selected SystemModel sections, but explicitly blocks unsupported API/policy contracts, unknown references, unprojected extensions, missing deployment/testing/documentation posture and other incomplete source declarations. This is good fail-closed behavior, but it is not proof of equivalence to root ISR.
- **Gen-C BIR is visibly lossy relative to the rich ISR.** `LoweringPass.execute` iterates modules, entities, services and service operations; the shown BIR lowering carries entity field names and operation types, but does not encode the complete rich ISR semantic surface (for example API contracts, event guarantees, policy posture, requirement graph metadata, provenance and deployment intents). It must not be described as a complete full-stack lowering without a total mapping/reject contract.
- **Backend failure semantics differ.** Root protocol separates backend class, test spec, conformance and generated repository. Gen-C has a distinct backend interface and artifact/diagnostic result. Tiannara executor uses collect-all semantics and treats a backend's successful `generate()` return as an outcome success before independent bundle verification. UniversalCompiler has its own request validator, optimizer, output validator and packager. These verdicts are not interchangeable.

### 10.4 Updated blockers and disposition

| ID | Finding | Severity | Required evidence / disposition |
|---|---|---|---|
| ISR-A11 | Canonical root ISR authority is not enforced by every compiler entrypoint; rich ISR, SystemModel and raw request routes compile through distinct interfaces | Critical | Trace each entrypoint from CLI/API/deployment composition to runtime invocation; decide which routes are canonical, bounded adapters, test-only or retired |
| ISR-A12 | Two different classes named `UniversalISR` have materially different schema and mutability semantics | High | Inventory imports/exports and all call sites; resolve naming collision through governed disposition, not blind rename |
| ISR-A13 | Tiannara typed SystemModel envelope is not proven semantically equivalent to root ISRRevision | Critical | Define field/edge coverage, identity/hash, provenance and unknown-field behavior; build semantic-preservation evidence before it can be an authority or compiler source |
| ISR-A14 | Rich constitutional ISR → BIR lowering does not visibly preserve the complete rich semantic model | Critical | Produce complete node/field/relationship mapping and fail-closed rejection matrix; verify each BIR pass and backend consumer |
| ISR-A15 | Universal Compiler HTTP API accepts a separate ISR payload contract and packages artifacts outside the canonical root pipeline | High | Establish API exposure/deployment status and ensure authorization/source binding/evidence gates are equivalent or explicitly quarantine the route |
| ISR-A16 | Model immutability, hashing, validation and provenance contracts are inconsistent across families | Critical | Compare canonical serialization/hash, mutation controls, schema versioning, provenance and validator failure semantics with executable tests |

**PR-head audit conclusion:** the root canonical ISR decision exists as documented governance direction, but multiple distinct compiler entrypoints still accept non-canonical ISR/model inputs. This is now a demonstrated boundary-enforcement gap, not merely an unresolved inventory question. FS-00 remains **NOT READY**. Do not change schemas, add adapters, delete legacy paths, mark any runtime retired, or begin FS-01 on the strength of this audit alone. The next audit work is exhaustive consumer/reachability tracing (including CLI, API deployment, persistence and test-only classification), semantic mapping tables for each bridge, and a governance disposition for each reachable non-canonical entrypoint.
