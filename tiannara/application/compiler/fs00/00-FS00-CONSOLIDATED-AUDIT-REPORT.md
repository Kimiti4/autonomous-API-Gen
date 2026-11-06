# FS-00 — Consolidated Compiler and Semantic-Lineage Audit Report

**Version:** 1.1 | **Date:** 2026-11-06  
**Repository:** `Kimiti4/autonomous-API-Gen`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Audited head:** `c314049acca839358a46dd8371f3c51321e401` (targeted backend evidence delta; historical checkpoint findings retain their individually listed inspected revisions)  
**PR:** #201, open draft, unmerged; base `remediation/w12-executable-effect-contract`  
**Boundary:** Documentation-only update. The targeted source/test/workflow inspection below records evidence already produced by CI; no production code, tests, workflows, registrations or certification records are changed by this report update.

---

## 1. Purpose and audit rules

This is the **single consolidated FS-00 report**, bringing Checkpoints 2–8 into one findings register. Earlier checkpoint documents remain historical records; this is the consolidated report.

- UNKNOWN is not PASS.
- Declaration, static inspection, emitted source, native build, runtime behavior and independent acceptance are separate evidence classes.
- Hash identity is not semantic equivalence or behavioral proof.
- Mocked, skipped, simulated and structural-only evidence is not native runtime PASS.
- Retain useful compiler targets. Restrict unsupported semantic subsets; harden and certify incrementally. Do not retire a backend merely because it is incomplete.
- The goal is one authoritative RequirementGraph, one ISR contract, one compiler IR and one governed compilation authority. The audit tests actual enforcement, not architectural intent.
- No capability or certification is promoted by this report.

## 2. Executive conclusion

**The repository does not yet demonstrate one complete, universally governed requirement-to-working-software pipeline.**

There are substantial foundations: typed requirements and ISR models, immutable/content-addressed revisions, requirement-reference projection, behavioral ISR-to-CompilationPlan lowering, fail-closed semantic capability gates, source-binding checks in Gen-C, independent effect-contract tests for a narrow Python path, and native execution infrastructure for selected targets.

The critical blocker is **fragmented semantic authority and incomplete end-to-end lineage**, compounded by multiple compiler registries, inconsistent backend capability, weak/circular tests, uneven native execution and incomplete evidence/publication controls.

Current assessment:
- Architecture and implementation: PARTIAL.
- One universal compiler authority: NOT ESTABLISHED.
- One mandatory RequirementGraph → ISR → compiler IR route: NOT ESTABLISHED.
- Requirement-faithful production generation across all supported languages/frameworks: NOT ESTABLISHED.
- Universal independent acceptance and cross-target semantic parity: NOT ESTABLISHED.

## 3. Checkpoint history

| Checkpoint | Inspected revision | Subject | Historical record |
|---|---|---|---|
| 2 | `81f8fa1be927dad19e9bc868738016233599e9e3` | Compiler inventory/reachability | `06-compiler-inventory-reachability-audit.md` |
| 3 | `944ec2bfec23049134b3b72c4267bdb39e577015` | Backend capability enforcement | `07-backend-capability-enforcement-audit.md` |
| 4 | `e7ce89fb61bcf11b3571fb32568a962166f665e4` | Requirement-to-emission matrix | `08-requirement-to-emission-matrix.md` |
| 5 | `68301a4654c90b555c3b0bb93806522c2156421a` | Invocation/publication | `09-invocation-reachability-publication-audit.md` |
| 6 | `bc7de4ceed007406810224f880206709d48620b9` | Verification/native execution | `10-verification-native-execution-evidence-audit.md` |
| 7 | `99df9f35086cc8c4b58bb83e1520963fbb2734ed` | Independent oracles | `11-requirement-oracle-independence-audit.md` |
| 8 | `5090cc837beb54977bcb9e45b472cfa4b7340669` | Semantic authority/lineage | Findings included below |

Historical workflow observations apply to their inspected revisions, not necessarily the current Actions state.

## 4. Compiler inventory and reachability

At least five distinct compiler families exist:

1. Tiannara ProjectCompiler — `tiannara/application/compiler/`.
2. Root Universal Compiler API/kernel — `compiler/`.
3. Constitutional Gen-C — `constitutional_architecture/compiler/`.
4. Per-category compilers — `constitutional_architecture/compilers/`.
5. Autonomous API compiler modules — `autonomous-api/app/engine/`.

They have separate registries, plans/IRs, selectors, routes and evidence. Tests/certification cannot transfer between them without verified adapters.

ProjectCompiler registers 21 implementations: 11 backend-service targets and 10 frontend/application targets; Android is a frontend application, not a backend service. Three Android paths remain distinct: ProjectCompiler Android frontend, campaign/root Android structural backend and Android cloud-build workflow.

Reachability:
- ProjectCompiler CLI `create` selects one backend, statically verifies and materializes output. `factory` adds execution, tests, bounded repair and evidence.
- Gen-A has separate HTTP discovery/validation/compile/job routes and backend registry; job state is in-memory.
- Gen-C has a multi-pass pipeline and source-binding gate, but an enabled general production route with a source-bound certified backend was not established.
- Autonomous API compiler modules exist, but a general compiler-generation route was not found in the inspected mounted router composition.
- ProjectCompiler composition documentation includes a stale FastAPI-only description inconsistent with the executable registry.

**Finding:** no single governed compilation authority is demonstrated as mandatory across all compiler families.

## 5. RequirementGraph, ISR and compiler IR authority

### 5.1 Multiple RequirementGraph models

| Model | Location | Observed contract |
|---|---|---|
| Canonical graph | `reqgraph/core/graph.py` | Frozen mapping-based graph; five requirement kinds; four edge types |
| Tiannara domain graph | `tiannara/domain/models/requirement_graph.py` | List-based graph; six edge kinds; provenance and analysis; structural validation at construction |
| Constitutional graph | `constitutional_architecture/core/models/requirements_graph.py` | Mutable graph for intent/genome architecture; separate taxonomy |

`folder/CONTRACT_RequirementGraph.md` names `reqgraph/core` as canonical. Yet `constitutional_architecture/compiler/source_binding.py` imports the Tiannara domain RequirementGraph. Their taxonomies, validation, identity and provenance are not interchangeable.

The canonical `reqgraph/adapters/isr_projection.py` projects requirement nodes into `REQUIREMENT_REF` nodes and preserves the four graph relationships. It deliberately does not create capabilities or `SATISFIES` edges, correctly avoiding the inference that a requirement reference proves realization. Universal use of this adapter is not established.

### 5.2 ISR contract drift and duplicate models

`folder/CONTRACT_CanonicalISR.md` describes `isr/core` as the sole ISR authority with 9 node kinds and 8 edge kinds. At the audited head, `isr/core/graph.py` defines **14 node kinds and 18 edge kinds**, including frontend routes/interactions, effects, invariants, consequences and requirement relationship edges.

The implementation may have evolved intentionally, but the frozen contract and current schema disagree. Reconcile through governed versioning; do not silently treat both as exact authority.

Other ISR-like representations remain:
- `tiannara/domain/models/isr.py`: legacy-compatible envelope with typed `system_model.v1` payload.
- `constitutional_architecture/isr/model/isr.py`: rich constitutional ISR consumed by Gen-C and source binding.
- `constitutional_architecture/core/models/universal_isr.py`: UniversalISR consumed by the genome-to-ISR transpiler.
- `isr/core/revision.py`: frozen, content-addressed canonical graph revision with structural and behavioral validation.

The R1-D.1 legacy disposition says the rich constitutional ISR/System model and UniversalISR are retired or on a retirement path. However, Gen-C lowering still consumes `isr.system.modules`; source binding still imports the rich constitutional ISR; and the UniversalISR transpiler remains an execution path. A documented retirement decision is not proof that runtime consumers migrated.

### 5.3 SystemModel and behavioral ISR paths

The typed `SystemModel` carries capabilities, domains, services, components, APIs, events, data models, security, infrastructure, deployment, documentation, testing and operational policies. It binds to a RequirementGraph by graph ID/hash and has deterministic canonical hashing.

Its API operations do not define a complete typed request/response/error, authorization, effect and transaction contract. Data-model invariants are free-text. Security is a posture rather than a complete operation-level role/action/resource/condition policy matrix. Event delivery/ordering and SLO declarations do not prove runtime enforcement.

The separate behavioral path is stronger:
- `ISRRevision.create` validates graph and typed behavior before hashing.
- `reqgraph/adapters/isr_projection.py` provides explicit requirement-reference projection.
- `compiler/core/lowering.py:isr_to_plan` carries behavior and relationships into typed `CompilationPlan` objects.
- `compiler/core/capabilities.py` derives required semantic features and rejects unsupported plans before generation.

It rejects ambiguous API-service bindings, unresolved effect links and consequences without explicit targets. But it is not proven to be the mandatory input to ProjectCompiler, Gen-A, Gen-C, per-category and Autonomous API compilers.

Gen-C's inspected `LoweringPass` consumes the rich constitutional ISR and lowers module/entity/service structures to BIR. It is not the same lowering function as behavioral `isr_to_plan`.

**Finding:** no proven universal chain `RequirementGraph → one ISR → one Compiler IR → every backend`.

## 6. Checkpoint 8 — source-to-ISR lineage

### Positive evidence

`constitutional_architecture/compiler/source_binding.py` is a substantive control on its own path. It recomputes source SHA-256; checks graph provenance against the source hash; rejects empty source/graph; requires graph-to-ISR requirement ID bindings; checks graph identity/hash, source metadata and relations; verifies the bound SystemModel hash; deterministically projects that model into the constitutional ISR; compares the projected system; and reports unknown, duplicate and unbound mandatory IDs as blockers.

Its own docstring correctly limits the claim: this establishes identity and requirement-ID traceability, not semantic equivalence or proof of generated behavior.

### Lineage limitations

1. **Path-specific enforcement:** source binding uses the Tiannara domain RequirementGraph and rich constitutional ISR. It is not shown as mandatory in ProjectCompiler, Gen-A, canonical behavioral lowering, per-category or Autonomous API routes.
2. **Graph authority conflict:** the source-binding graph differs from canonical `reqgraph/core` and its projection adapter.
3. **ISR authority conflict:** binding checks a rich constitutional ISR described elsewhere as retired; the newer canonical graph/behavioral plan path is separate.
4. **Reference is not realization:** canonical projection creates requirement refs and relations, not `SATISFIES` edges. A universal gate requiring every MUST requirement to be realized and independently verified was not established.
5. **Hash is not semantic proof:** hashes prove identity of hashed content, not preservation of meaning or working behavior.
6. **Different validation outcomes:** the domain RequirementGraph attaches semantic analysis findings without uniformly blocking construction; canonical reqgraph has different fail-closed rules. No common normalization gate was demonstrated.
7. **Projection completeness is path-specific:** full typed projection checks exist in Constitutional source binding, but equivalent checks are not established across every other compiler path.
8. **Evidence identity is incomplete:** plan IDs derive from ISR hash prefixes, but a universal envelope binding plan hash, backend digest, oracle digest and artifact-set digest is not established.

### End-to-end trace assessment

| Stage | Evidence observed | Assessment |
|---|---|---|
| Source snapshot | SHA-256 source binding | PRESENT on Gen-C path |
| Requirement graph | Multiple models/taxonomies | PARTIAL; authority conflict |
| Graph validation | Different validators and semantics | PARTIAL |
| Requirement → ISR refs | Canonical adapter and separate constitutional projection | PRESENT in separate paths; universal use UNKNOWN |
| Typed architecture projection | Deterministic SystemModel projection in source binding | PRESENT on that path |
| ISR identity | Frozen canonical `ISRRevision` hash | PRESENT in `isr/core` |
| ISR → CompilationPlan | `isr_to_plan` | PRESENT for behavioral path |
| ISR → Gen-C BIR | Rich ISR lowering | PRESENT; separate legacy path |
| Backend selection | Multiple registries/selectors | PARTIAL |
| Capability gate | Fail-closed semantic gate | PRESENT in behavioral reference path; cross-family UNKNOWN |
| Generated artifacts | Uneven emitter coverage | PARTIAL |
| Independent oracle | Narrow Python effect scenario | PARTIAL |
| Native build/runtime | Selected targets only | PARTIAL |
| Evidence envelope | Some hash chains, incomplete universal binding | PARTIAL |
| Publication gate | Direct materialization paths remain | NOT ESTABLISHED universally |

## 7. Backend quality and capability enforcement

The 11 ProjectCompiler backend-service generators are materially uneven. FastAPI is the richest inspected generator but uses in-memory repositories and does not fully implement all SystemModel semantics. Go emits a restricted primary-entity CRUD surface with memory storage. The ProjectCompiler Rust generator is not the separate behavioral RustAxum reference backend. Several other targets mainly emit model/health scaffolds. No evidence supports claiming all 11 generate complete requirement-faithful production applications.

ProjectCompiler selectors often match requirements against self-declared manifests; declarations are not independent proof. Behavioral reference backends have a more honest semantic gate: Python advertises a broader feature subset; Rust advertises a narrower subset and does not claim API contracts, authorization enforcement or executable effect execution. Unsupported plans should be refused, not silently weakened and not used as grounds to retire a useful target.

Frontend build/E2E infrastructure exists, but uniform requirement-linked interaction semantics and independent acceptance are not established.

## 8. Verification and native execution

Weak generated tests observed:
- Laravel generates `assertTrue(true)`.
- Phoenix compares `"/health"` with itself.
- ASP.NET Core compares the health-path literal with itself.
- Ktor compares the health-path literal with itself.
- Rails makes a real health request but only checks success.
- Other targets have health, shape or symbol-presence tests, not complete independent business oracles.

These must not count as application-behavior verification.

A stronger narrow oracle exists: `tests/support/effect_contract_scenario.py` is authored separately from the emitter and copied into generated Python output. It tests authorization allow/deny, no execution/commit on denial, pre/postconditions, replay, concurrent idempotency and missing principal/context/key. This is meaningful evidence for a narrow Python effect contract, but it uses an in-memory ledger and does not prove durable cross-process atomicity or parity across every backend.

At Checkpoint 6's audited head, Android backend contract tests passed 11 tests; Android cloud build was skipped because it required manual dispatch. Workflows targeting `main` did not validate the PR's non-main base. A historical Angular generated production build failed; no later matrix run at that audited head demonstrated a fix. Android structural tests used fake runners/fixtures; no manual cloud build bound to that audited head was found. These are historical observations, not current Actions status.

Some ledgers are hash-chained, but the inspected calibration ledger did not bind all of: source commit, backend implementation digest, ISR/plan hash, artifact manifest/per-file hashes, oracle version/hash, toolchain identity and test log hash. Adapter-specific executable-effect ledger checks remain placeholders in inspected code. Direct artifact materialization paths remain; universal quarantine, independent verification and authorized atomic promotion are not demonstrated.

## 9. Consolidated findings register

| ID | Severity | Finding | Status |
|---|---|---|---|
| FS00-001 | Critical | Multiple compiler families/registries; no mandatory common compilation authority | OPEN |
| FS00-002 | Critical | RequirementGraph authority fragmented across three models | OPEN |
| FS00-003 | Critical | ISR contract says 9/8 while implementation is 14/18 | OPEN |
| FS00-004 | Critical | Models documented retired remain consumed by executable paths | OPEN |
| FS00-005 | Critical | No proven universal RequirementGraph → ISR → Compiler IR chain | OPEN |
| FS00-006 | Critical | No universal MUST-requirement realization/verification coverage gate | OPEN |
| FS00-007 | Critical | Tautological generated tests in Laravel, Phoenix, ASP.NET Core and Ktor | OPEN |
| FS00-008 | High | Source binding is substantive but path-specific | OPEN |
| FS00-009 | High | Hash identity is not semantic preservation or behavioral correctness | OPEN |
| FS00-010 | High | SystemModel API/invariant/security carriers lack complete typed semantics | OPEN |
| FS00-011 | High | Event delivery/ordering and operational declarations lack general runtime guarantees | OPEN |
| FS00-012 | High | Backend manifests/self-declarations can be mistaken for proof | OPEN |
| FS00-013 | High | Backend semantic subsets differ; fail-closed refusal is not universal | OPEN |
| FS00-014 | High | Independent behavioral oracles cover a narrow reference path | OPEN |
| FS00-015 | High | Evidence envelope lacks universal source/backend/plan/oracle/artifact/toolchain/log binding | OPEN |
| FS00-016 | High | Universal quarantine and authorized atomic promotion not established | OPEN |
| FS00-017 | High | Frontend requirement-to-interaction acceptance is not uniform | OPEN |
| FS00-018 | Medium | Stale documentation conflicts with executable composition/consumers | OPEN |
| FS00-019 | Medium | Evidence classes are not uniformly distinguished in qualification | OPEN |

## 10. Required remediation sequence

### Gate A — settle authority
1. Freeze an authority map naming one active RequirementGraph, ISR, compiler IR and permitted versioned adapters.
2. Reconcile the canonical ISR contract with the actual 14-node/18-edge implementation through governed versioning.
3. Assign KEEP/MIGRATE/REPLACE/RETIRE/DEFER dispositions to all RequirementGraph and ISR variants, backed by executable-consumer searches and migration tests.
4. A model is not retired while an executable route still imports or consumes it.
5. Make one mandatory requirement-to-ISR projection and one mandatory ISR-to-IR lowering boundary; temporary adapters must be explicit and bounded.

### Gate B — complete lineage
6. Require stable requirement IDs, provenance, priority, acceptance criteria, verification method and approval state.
7. Every MUST requirement must map to explicit semantic obligations and realization links; unresolved, conflicting, unapproved or unbound MUST requirements block compilation.
8. Every transformation emits a deterministic mapping report: input/output IDs, preserved/normalized/deferred/rejected fields and diagnostics.
9. Bind transformations to input/output hashes, adapter digest and schema version. Add semantic correspondence checks beyond hashing.
10. Run semantic-diff/completeness checks between requirement graph, ISR, compiler IR and artifact manifest. No silent drops/defaults for required semantics.

### Gate C — independent oracles
11. Define language-neutral positive, negative, boundary, concurrency, failure/retry and security oracles linked to requirement IDs.
12. Keep expected outcomes and test vectors independent of emitter templates.
13. Replace tautological tests with real application requests and observable state/effect assertions.
14. Require frontend oracles for routes, interactions, authorization, validation, loading, empty/error states and accessibility.
15. Promote backend feature subsets only after independent oracles pass on native builds/runtimes. Preserve targets; refuse unsupported semantics before generation.

### Gate D — evidence and publication
16. Standardize immutable evidence binding source snapshot, requirement graph, ISR, compiler IR, backend version/digest, oracle version/hash, artifact manifest/per-file hashes, toolchain, commands, raw logs and runtime results.
17. Keep skipped, unavailable, mocked and structural-only evidence distinct from native PASS.
18. Route every compiler family through quarantine; verify in isolation; promote atomically only after all required gates and an authorized publication decision.
19. Ensure CI triggers validate the actual PR base/head policy.

## 11. FS-00 exit criteria

- [ ] One authoritative RequirementGraph contract; all variants dispositioned and no undocumented live consumers.
- [ ] One authoritative ISR contract reconciled with implementation and versioned extensions.
- [ ] One canonical compiler IR contract and mandatory adapters.
- [ ] End-to-end requirement ID and semantic-field lineage across every production compiler route.
- [ ] MUST requirements cannot disappear without a blocking diagnostic.
- [ ] Each backend has an explicit semantic subset and refuses unsupported plans before generation.
- [ ] Tautological tests are not counted as verification.
- [ ] Independent requirement oracles run against each claimed backend feature.
- [ ] Native build/runtime evidence exists for every promoted target.
- [ ] Evidence binds source, intermediate hashes, backend digest, oracle, artifacts, toolchain and logs.
- [ ] Every publication path enforces quarantine, verification and authorized atomic promotion.
- [ ] Frontend and backend targets meet equivalent requirement-derived acceptance standards.

## 12. Conclusion and next checkpoint

**Conclusion:** ESAP is not yet proven to be a universal software developer system capable of producing working, requirement-faithful applications across arbitrary supported languages/frameworks. Its immediate blocker is not simply the number of generators; it is the lack of one reconciled semantic authority and complete lineage through every compiler path.

**Next checkpoint — FS-00 Checkpoint 9:** Select one bounded representative requirement set and prove its full source-to-artifact lineage on one actual production compiler route: every transformation, field/ID mapping, backend decision, generated artifact, independent oracle, native execution result and evidence envelope. Then repeat for a second backend to expose adapter divergence. Do not infer universal parity from one successful path.

**Change boundary:** Documentation-only consolidation. No production code, tests, certifications or backend dispositions changed.


---

## Checkpoint 9 — end-to-end requirement lineage proof

**Audit basis:** source inspection at `1d53110fb0ff091d680e08cabd801e0df20513f6`, including TOR ingestion/projection, canonical ISR revision lowering, the Python FastAPI and Rust Axum behavioral backends, capability gates, conformance checks, traceability records, and generated-backend integration test definitions. This checkpoint is a source audit. It does not claim that the integration tests were executed during this audit.

### 9.1 Bounded representative input

The representative source is the payroll TOR fixture in `tests/support/tor_sources.py`. Its bounded requirements are:
- manage employee payroll records;
- calculate gross pay from base salary and allowances.

The fixture deliberately obtains requirement candidates through `extract_tor_text`, then supplies explicit `HumanApproval` records. Reviewer-authored ISR declarations describe an Employee data model, Payroll service, gross-pay expression, and a `PERSISTS` relationship. The projection uses a deterministic system/revision identity.

This is a useful bounded proof because the source prose is not directly treated as executable architecture. The approval record is an explicit human decision and carries the ISR declarations.

### 9.2 Source-to-ISR lineage

The inspected `reqgraph/ingestion/tor_extractor.py` and `reqgraph/adapters/tor_isr.py` establish the following controls:

1. TOR candidates preserve source reference and source line spans.
2. A RequirementGraph is created through explicit approval; the approval requires a reviewer, decision reference and acceptance criteria.
3. ISR declarations must carry non-empty `source_requirement_ids`, include the requirement approving them, and reference known candidate IDs.
4. Duplicate ISR node/edge declarations are rejected.
5. An approved requirement without an explicit ISR declaration blocks projection.
6. The projection binds the source SHA-256 and requirement graph hash, carries requirement IDs and declared ISR node/edge IDs, and creates a content-addressed ISR revision.
7. The adapter creates requirement-reference nodes and requirement relationships rather than silently turning prose into capabilities or satisfaction claims.

The source-binding mechanism is substantive within this TOR path. It must not be conflated with the separate Constitutional source-binding path audited in Checkpoint 8: they use different requirement graph models and different binding contracts.

### 9.3 ISR-to-CompilationPlan lineage

`compiler/core/lowering.py:isr_to_plan` consumes an `ISRRevision` and builds a typed `CompilationPlan`. In the inspected implementation it:
- preserves data-model, event, security, API, effect, invariant, service, frontend-route and frontend-interaction payloads as typed plan objects;
- preserves explicit `PERSISTS`, `PUBLISHES`, `CONSUMED_BY`, `SECURED_BY`, `CAUSES_EFFECT`, `CONSEQUENCE_OF`, `EXPOSES`, `ROUTES_TO`, `CONTAINS` and `INVOKES` relationships where handled by the lowering;
- requires exactly one explicit service binding for an API operation that has `EXPOSES` relationships, rejecting ambiguous service bindings;
- rejects effect edges whose source/effect target cannot be resolved;
- rejects consequences without an explicit effect or invariant target.

The plan ID is derived from the ISR content hash prefix. The projection tests assert preservation of typed fields, expression field references, service rules/transitions, security policy links, API contract fields, effect bindings, consequence payloads and invariant expressions. Determinism is tested for repeated lowering of the same revision.

This establishes a strong typed projection for the exercised node/edge types. It does not establish that every possible ISR property or edge is supported by every compiler family.

### 9.4 Backend decision and divergence

The representative `backend_plan()` contains the Employee model, Payroll service, gross-pay expression, guarded `draft → submitted` transition and persistence relationship. Both `PythonFastAPIBackend` and `RustAxumBackend` declare support for the relevant shared subset: typed fields, decimal shape, expressions, business rules and state transitions.

The backend capability declarations are not equal:
- Python FastAPI additionally declares API contracts, authorization policies, effect-policy preservation, effect-binding preservation, consequence preservation and effect execution.
- Rust Axum does not declare API contracts or authorization policies. It does declare the listed effect/consequence preservation features, but not executable effect semantics or effect execution.

The capability gate is invoked at the start of each backend's `compile()`. The tests explicitly verify that API operations are refused by Rust and that a plan requiring API contracts and authorization is rejected by Rust while Python passes those two capability checks. Both backends still reject unsupported effect semantics. The broader behavioral ISR projection test verifies that the richer payroll API/security/effect plan is refused by both backends for the remaining unsupported obligations, and that Rust reports API/auth gaps as well.

**Interpretation:** the two backends share a real but bounded behavioral subset. They are not interchangeable and do not have equivalent semantic coverage. The Rust backend's successful shared-subset compile/test must not be represented as proof of API, authorization or executable-effect parity.

### 9.5 Generated artifact and oracle path

The integration test `tests/integration/test_generated_backend_behavior_builds.py` defines native generated-application checks:
- Python: compile the TOR-derived backend plan, write generated files, install generated requirements, and run the generated pytest suite.
- Rust: compile the same TOR-derived backend plan, write generated files, and run `cargo test`.

Both backend emitters use `compiler/core/behavior_oracle.py` when generating tests for service rules and guarded transitions. That module is not imported by generated applications; it independently evaluates the bounded expression AST and emits literal expected values into generated tests. This is stronger than merely asserting that files exist, and can detect disagreement between the reference evaluator and generated runtime for the sampled inputs.

However, the generated test expectations are produced by the compiler's own test-generation path from the same CompilationPlan. The oracle is a separate evaluator, but the test suite is not wholly independent of the compiler or its interpretation of the plan. Sample contexts are generated from field types and cover selected values, not exhaustive input domains. The source acceptance criteria in the TOR fixture are not themselves transformed into a complete independent oracle suite.

A separate Python W12 integration test copies `tests/support/effect_contract_scenario.py` into the generated app. That scenario independently exercises authorization, preconditions, postconditions, replay, concurrency and no-commit-on-failure. It is a stronger independent runtime scenario, but it is built from the separate direct ISR fixture in `tests/support/execution_effect.py`; it does not prove the entire TOR → requirement graph → ISR → plan → backend path for those W12 effect semantics. No equivalent Rust W12 runtime proof is established by this test.

The backend conformance checker verifies plan-element path mapping, artifact presence, a content floor, Python syntax parsing, and equality of the semantic-obligations manifest. It does not itself execute the generated application or prove that a generated operation behaves according to its requirement.

### 9.6 Traceability and evidence-envelope boundary

`traceability_record()` records source name/hash, requirement-graph hash, requirement IDs, ISR content hash, plan ID, artifact-bundle hash, mapping-spec version, and ISR node/edge IDs. The source-bound projection tests assert that source and ISR changes affect their hashes, that reviewed behavior changes the plan and generated code, and that the backend artifact bundle hash is calculated over sorted paths and file contents.

This is meaningful content lineage, but the inspected record is not a complete immutable execution evidence envelope. It does not itself bind:
- backend implementation identity/version or implementation digest;
- compiler/test-generator/oracle source revision;
- independent acceptance-oracle identity and digest;
- native build/test run ID, environment/toolchain identity and raw logs;
- per-file artifact hashes or a publication/promotion decision.

The traceability test constructs and asserts the record; that alone does not prove that every production compilation route persists, signs, verifies and enforces it before artifact publication.

### 9.7 Execution status at this checkpoint

The source contains integration tests that would install and execute the generated Python application and run `cargo test` for the generated Rust application. This audit inspected those test definitions but did not execute them. The PR-associated workflow run list for audited commit `1d53110fb0ff091d680e08cabd801e0df20513f6` returned an Android Cloud-Build workflow run; it does not establish that the Python/Rust generated-backend integration tests ran on this commit. Therefore:
- source-level projection and test definitions: **observed**;
- generated artifact assertions and independent reference evaluator: **observed in test source**;
- Python/Rust native execution on this audited commit: **not established here**;
- cross-backend semantic parity beyond the declared shared subset: **not established**;
- universal end-to-end requirement conformance: **not established**.

### 9.8 Checkpoint 9 findings

- **FS00-020 — TOR approval is a real gate, but its scope is path-specific.** The TOR adapter requires explicit approval and reviewer-authored declarations. This does not resolve the distinct RequirementGraph/ISR authorities and consumers identified in Checkpoint 8.
- **FS00-021 — typed ISR lowering preserves a meaningful subset, not universal semantics.** The behavioral lowering preserves typed payloads and explicit relationships for supported graph constructs, with fail-closed checks for ambiguous API ownership and unresolved consequence/effect bindings.
- **FS00-022 — backend semantic parity is demonstrably incomplete.** Python FastAPI and Rust Axum share a bounded payroll behavior subset, but Rust refuses API contracts and authorization policies that Python declares support for. Do not retire Rust on this evidence; retain it, restrict unsupported plans, and harden/certify its missing capabilities.
- **FS00-023 — the reference evaluator is useful but not a complete independent acceptance oracle.** It is separate from generated runtime code and emits literal expected values, but test inputs are compiler-generated from the plan and sample-based. Requirement acceptance criteria are not yet shown to drive comprehensive independent oracles.
- **FS00-024 — native integration tests are defined, not proven executed at this audited head.** Test source alone is not execution evidence. A workflow run tied to the exact source commit, backend implementation, generated bundle and test logs is required before any runtime status upgrade.
- **FS00-025 — traceability is not yet a complete execution evidence envelope.** Current traceability fields omit backend/toolchain/oracle identities, execution run and log bindings, and explicit publication authorization.

### 9.9 Required remediation sequence

1. Keep both backends and their separate capabilities; do not infer parity or retire a target. Add no capability claims without implementation and independent evidence.
2. Bind each generated artifact bundle to source revision, requirement graph, ISR revision, plan, backend implementation digest, generator/oracle revision and toolchain identity.
3. Make exact-commit Python and Rust integration workflows mandatory for the relevant branch/PR, with raw logs and artifact hashes retained.
4. Expand independently authored requirement-derived scenarios beyond one generated sample per expression; include boundaries, invalid inputs, authorization, state transitions, failure atomicity and concurrency where required by the contract.
5. Add a backend-by-backend semantic matrix that distinguishes preserved metadata, emitted implementation, native build, runtime behavior and independent acceptance results.
6. Require a governed verification-and-publication gate that consumes the complete evidence envelope. Keep generated output quarantined until all required checks pass.
7. Repeat this lineage proof for an API/authenticated/effect-bearing requirement set. The current Rust backend should refuse that set until those capabilities are implemented and evidenced.

### 9.10 Checkpoint 9 disposition

**PARTIAL — bounded source-to-artifact lineage is demonstrated in source and test design; exact-head native execution and universal/backend parity are not demonstrated.** No compiler implementation, test, workflow, backend capability declaration, certification status or production artifact was changed in this checkpoint. FS-00 remains an audit/documentation activity.


---

## Checkpoint 10 — independent verification and cross-backend parity

**Audit basis:** read-only source/test inspection at `54aae0132804123530adb21160394788c3b29d3e`, focused on requirement acceptance criteria, behavioral expression oracle generation, Python FastAPI and Rust Axum emitters, generated-runtime integration test definitions, conformance checking, and the workflow runs attached to the exact audited commit. No tests were executed locally in this checkpoint and no runtime status is inferred from test definitions.

### 10.1 Acceptance criteria are carried, but not yet executable verification obligations

The canonical `reqgraph.core.graph.RequirementNode` carries `acceptance_criteria`. `reqgraph.adapters.isr_projection.project_requirement_graph` preserves those criteria on ISR `REQUIREMENT_REF` nodes. The TOR ingestion path also requires at least one acceptance criterion in each human approval.

However, the representative TOR fixture in `tests/support/tor_sources.py` supplies the generic criterion: `An independently authored test verifies this requirement.` The criterion is not a concrete expected outcome, input partition, observable assertion, or named oracle. The TOR-to-ISR `SourceTraceability` record binds requirement IDs and ISR IDs but does not contain acceptance-criterion identities or test/oracle bindings.

The inspected behavioral backend emitter consumes `CompilationPlan` service rules and transitions to create generated tests. It does not consume RequirementNode acceptance criteria or resolve them to independent test specifications. The criteria therefore survive as requirement metadata, but a requirement → criterion → test oracle → execution-result relation is not demonstrated on this path.

### 10.2 The generated expression oracle is differential, not fully independent

`compiler/core/behavior_oracle.py` is separate from the generated application runtime and evaluates a bounded expression AST. It supports literals, field references, boolean operators, conditional expressions, decimal arithmetic and comparisons. Python and Rust emitters use it to compute expected values, then write those values as literals into generated tests.

This has genuine value: the generated runtime is compared with a second evaluator rather than only checking that source files or method names exist. But the oracle and generated tests are part of the same compiler repository and are invoked by the emitter itself. They share the same typed plan and expression interpretation. This is **differential testing against a reference evaluator**, not an independently authored acceptance oracle derived from the requirement statement or an external test specification.

The default `sample_context` chooses one deterministic value per field type (for example, money/decimal = `100.00`, integer = `100`, boolean = `True`). It does not derive boundary partitions from field constraints, precision/scale, nullability, enumerations or business acceptance criteria. A single representative value cannot establish behavior at zero, negative values, precision limits, missing/nullable fields, invalid types, or other boundary conditions unless separate tests explicitly cover them.

### 10.3 Concrete parity gap in transition test generation

For each guarded transition, the Python emitter generates a test using the single sampled context. In the payroll fixture, the guard is `Employee.base_salary > 0`; the default money sample is `100.00`, so the generated test covers the accepted transition. The Python emitter does not generate the corresponding rejected/zero-value case in this path.

The Rust emitter also tests the accepted sample. If that sample is accepted, it additionally derives one zero-valued context and asserts that the transition is rejected. Thus the generated Python and Rust transition suites are not even identical in their positive/negative test vectors for the shared subset.

This does not show a runtime defect in either backend. It shows an oracle/test-generation coverage asymmetry and means the current generated test pattern cannot be used as evidence of symmetric transition verification. The explicit Rust negative case is still only one derived input, not a complete boundary suite.

### 10.4 Independent executable-effect scenario: strong but narrowly scoped

`tests/support/effect_contract_scenario.py` is authored outside the emitter and copied into a generated Python application by `tests/integration/test_generated_backend_behavior_builds.py`. It checks:
- authorized execution and one commit;
- replay returning the prior result without re-execution;
- concurrent same-key calls executing once;
- unauthorized role denial without execution or commit;
- missing principal/context/idempotency key rejection;
- precondition failure without execution/commit;
- postcondition failure without commit and successful retry.

These assertions inspect observable runtime behavior and are materially stronger than generated source-string assertions. The scenario remains specific to one Python effect contract and an in-memory ledger. It does not establish durable storage, cross-process concurrency, crash recovery, external side-effect atomicity, or parity with Rust and the other compiler families. It is not bound in the inspected tests to the TOR requirement IDs and acceptance criteria from Checkpoint 9.

### 10.5 Conformance checks are not acceptance verification

`compiler/core/conformance.py` checks whether plan elements map to paths, files exist and have non-hollow content, Python files parse, and the semantic-obligations manifest matches the plan's effects/bindings/consequences. This is useful structural and manifest conformance. It does not execute generated code, validate every API contract, prove the behavior of a business rule, or compare application behavior against requirement-derived expected outcomes.

The canonical `folder/CONTRACT_TestSpecification.md` and `folder/CONTRACT_VerificationResult.md` describe a stronger evidence model: verification result identity, verifier identity/version, checks performed, evidence references and five-state failure semantics. The inspected bounded behavioral emitter/conformance path does not demonstrate that every generated test run is converted into such a complete, immutable verification record and consumed by a mandatory publication gate.

### 10.6 Exact-commit execution evidence

The workflow-run lookup for exact commit `54aae0132804123530adb21160394788c3b29d3e` returned one associated run: **ESAP Android Cloud-Build Certification (Stage A)** (run `41921507863`). That run is relevant to the separate Android campaign and does not establish that `tests/integration/test_generated_backend_behavior_builds.py` ran on this commit. The existence of Python/Rust integration test definitions is therefore not upgraded to exact-head native execution evidence.

### 10.7 Checkpoint 10 findings

- **FS00-026 — acceptance criteria are not connected to executable oracle identity.** Criteria are preserved as requirement metadata, but the representative TOR criterion is generic and the behavioral emitter does not consume criteria to create or bind test specifications. Require concrete, verifiable criteria and explicit requirement/criterion/oracle/result links.
- **FS00-027 — the generated expression oracle has limited independence.** It is a separate evaluator from generated runtime code, but it is compiler-authored, plan-derived and invoked by the emitter. Classify it as differential/reference testing, not as a fully independent acceptance oracle.
- **FS00-028 — default oracle input generation is single-sample and constraint-blind.** Fixed values do not systematically cover boundaries, invalid inputs, nullability, field constraints, decimal precision/scale, or domain-specific cases.
- **FS00-029 — generated transition test coverage differs between Python and Rust.** Both test the positive sample; Rust adds a derived zero-value rejection case while Python does not. This is a test-generation parity gap, not proof of a runtime semantic defect.
- **FS00-030 — independent executable-effect verification is narrow.** The Python scenario is meaningful, but uses an in-memory ledger, one effect fixture and no demonstrated TOR acceptance-criterion binding or cross-backend equivalent.
- **FS00-031 — structural conformance and test definitions are not execution evidence.** The conformance checker is static/manifest-oriented; the exact audited commit's associated workflow run does not establish execution of the Python/Rust generated-backend integration suite.

### 10.8 Required remediation sequence

1. Introduce a technology-neutral acceptance-oracle contract that binds requirement ID, criterion ID, source/ISR/plan identities, input partitions, expected observable outcomes, oracle identity/version/digest, and evidence references.
2. Require every MUST functional requirement and every security, data-integrity, failure and operational obligation to have concrete acceptance criteria. Reject generic criteria such as “a test verifies this requirement” at the verification-planning gate.
3. Keep the compiler's reference evaluator as a differential check, but add separately authored requirement-level scenarios that do not call the compiler's evaluator to calculate their expected values.
4. Derive test vectors from constraints and domain partitions: boundaries, zero/negative, precision/scale, null/missing, invalid values, duplicates, authorization denials, retry/replay, concurrency, and failure injection as applicable.
5. Make Python and Rust generate/run the same shared-subset oracle vectors and compare externally observable outcomes. For unsupported semantics, retain fail-closed refusal; do not reduce the contract to the intersection merely to manufacture parity.
6. Bind exact source commit, compiler/backend digests, generated bundle hashes, test/oracle identities, environment/toolchain, raw logs and result state into immutable verification evidence.
7. Make the exact-head native verification matrix a required gate for the PR/branch and make publication consume only complete PASS evidence. Missing, skipped, stale or unbound evidence must remain NOT_RUN/INDETERMINATE/BLOCKED as appropriate, never PASS.

### 10.9 Checkpoint 10 disposition

**PARTIAL — differential reference tests and a strong narrow Python effect oracle exist, but general requirement-derived independent acceptance verification, boundary coverage, symmetric backend test vectors, and exact-head Python/Rust execution evidence are not established.** No source, production code, tests, workflows, backend capability declarations, certification states or generated artifacts were changed in this checkpoint. FS-00 remains read-only audit/documentation.


---

## Checkpoint 11 — verification evidence and publication authority

**Audit basis:** read-only source/test inspection at `763f16e6481820b7a8f0fcbec63086a2a2ef6e46`. Examined CBC-1 CampaignRunner and its independent process verifier, provenance bundle and evidence ledger, backend SDK certification, Constitutional VerificationEngine/VerificationPass, evidence signing, Autonomous API verification acceptance and artifact collection, production readiness, governed evolution publication, desktop release authorization, and PromotionManager. This checkpoint did not execute tests or modify production behavior.

### 11.1 The strongest integrated path: CBC-1 CampaignRunner

The CBC-1 `CampaignRunner` is the strongest inspected integration of compile, verification and real execution. For a behaviorally eligible backend it requires:
- structural and semantic conformance before build;
- an explicit real-Docker build result and image digest;
- real-Docker test, deployment, runtime probe and destruction stages;
- independent process verification of the exact candidate files, plan and candidate content hash;
- source-bound semantic correspondence against the candidate hash;
- full-stack verification over five canonical IR inputs, also candidate-bound.

Missing adapters, verifier startup errors, timeouts, malformed results, false/missing predicates, missing semantic mapping and failed candidate binding fail closed. The independent verifier runs in a separate process, reconstructs the typed plan, re-reads expected candidate files, recomputes the repository hash and invokes the backend conformance checker. The runner requires explicit Boolean `True` for its verifier predicates. `compose_verdict` requires every defined trial stage to pass before a trial can be CERTIFIED.

This is a substantive integrated certification design. Its authority is nevertheless scoped to callers that actually use this campaign runner. It does not prove that ProjectCompiler CLI, Gen-A, Gen-C, category compilers or Autonomous API publication routes all invoke it.

### 11.2 Evidence is not yet a complete, durable execution envelope

The campaign's immutable `Trial` and `StageEvidence` record stage, pass/fail, timestamps, log hash, details, execution mode, image digest, container ID, resource peak, retries and failure class. The trial also records backend name/class/version, compiler version, repository hash, requirement graph hash, genome hash, ISR revision ID, corpus hash and semantic correspondence.

The `ProvenanceBundle` records corpus, requirement graph, genome, ISR, plan, backend identity/version and application repository hashes. Its verifier recomputes the application hash and checks ISR, genome and requirement graph hashes. This is useful artifact provenance.

The following gaps remain in the inspected composition:
- The bundle's `ledger_record_hash` parameter defaults to empty, and the CampaignRunner's call to `ProvenanceBundle.emit` does not supply a ledger record hash.
- `StageEvidence.logs_hash` binds a hash of the runner's detail string; the Trial model does not itself retain raw stdout/stderr or a durable external log locator.
- The provenance bundle does not bind a source-control commit, compiler source digest, backend implementation digest, verifier/oracle digest or toolchain/container image digest as a complete immutable set.
- The bundle is written into the temporary candidate directory, and the runner removes that directory in its `finally` block after returning the Trial. The Trial carries the bundle hash, but this function does not itself persist the bundle or raw execution logs to a durable evidence store.
- The separate hash-chained `EvidenceLedger` is not automatically linked into this bundle by the inspected call.

A hash chain or artifact hash only protects the material actually included. It cannot establish provenance for omitted identities or logs.

### 11.3 Backend SDK certification is a narrower certification claim

`BackendCertificationEngine.certify` runs backend contract tests, a determinism test and compilation-output validation against a sample ISR. It stores reports and events in in-memory dictionaries/lists. The status becomes CERTIFIED when those three checks pass.

The inspected certification request/report does not bind the certification result to a source commit or backend implementation digest, and this certification engine does not run the CBC-1 real-Docker lifecycle. Therefore this status is evidence of the SDK's sample contract/determinism/output-validation suite, not proof of general production application behavior. The same word “certified” must not be treated as equivalent across the SDK and CBC-1 campaign.

### 11.4 Constitutional VerificationEngine can approve with incomplete coverage

The Constitutional VerificationEngine builds a registry of multiple verifier classes and executes those that report `can_verify(ctx)`. The pipeline may stop on timeout, skips verifiers that cannot verify the supplied context, and stops after blockers when configured. The resulting report records skipped checks and verifier results.

However, `approved_for_deployment` is currently computed as `len(blocking_failures) == 0`. A skipped check, a warning, or an error-level failure that is not classified as deployment-blocking does not by itself make that expression false. A pipeline that returns no checks can therefore have no blocking failures. The `VerificationPass` requests a maximum level of L3_SECURITY even though the model defines L4_PERFORMANCE, L5_OPERATIONAL and L6_PRODUCTION. The report records skipped counts, but the pass boundary does not require a declared set of mandatory verifiers/checks to have actually executed.

The VerificationPass does fail closed when the verifier raises or when `approved_for_deployment` is false. This is valuable, but it does not cure the completeness problem in the underlying approval predicate.

### 11.5 Evidence signing is optional and unsigned records remain admissible

The Constitutional evidence recorder uses HMAC-SHA256 when a key is configured. The signing module correctly documents that HMAC is symmetric attestation, not third-party non-repudiation.

The composition factory deliberately falls back to an unsigned recorder when no key is configured and emits a warning. More importantly, `verify_evidence_signature` returns true for records with no signature to preserve compatibility. Thus signature absence is not a hard failure in that verifier. This may be acceptable for legacy records, but a production release policy needs an explicit distinction between legacy unsigned evidence and evidence eligible for current certification/publication. An observability warning is not a cryptographic enforcement gate.

### 11.6 Autonomous API verification acceptance has a vacuous-pass edge case

`assess_verification_suite` correctly detects missing required kinds, failed results, configured timeouts and missing required output artifacts. Its current disposition enum is PASS/FAIL/INCOMPLETE.

Two fail-closed gaps are visible in the function:
- If `required_kinds=()` and `results=()`, both missing-kind and failed-result collections are empty, so the function returns PASS. There is no explicit non-empty policy/result invariant.
- The policy checks that required kinds were observed, but does not bind each result to a source revision, candidate/artifact digest, verifier version, workspace revision or immutable run identity. Output artifact collection hashes expected files, but the acceptance result does not itself establish that those files belong to the exact candidate that was approved.

The current tests cover missing required kinds, failed verification, required output collection and timeout failure. They do not cover the empty-policy/empty-result case, stale candidate evidence or source/artifact identity mismatch.

### 11.7 Publication controls are separate, not one shared authority

The repository contains stronger controls in specific publication paths:
- Autonomous API governed evolution checks for an approving governance decision authorizing the transition before calling `promote_verified_artifact`. Its tests assert that publication is not reached after governance denial and that the publisher is reached after approval.
- Desktop release assessment validates build evidence and binds authorization to the target and artifact digest; consequential signing, notarization and distribution actions require explicit authorization.
- The Constitutional VerificationPass blocks when its verifier is unavailable or reports no deployment approval.
- CBC-1 certification consumes an archived evidence chain and checks for a CERTIFIED aggregate with no missing evidence or failed gates on main.

But these controls are not composed into one universal promotion API. In particular, `PromotionConfig.require_verification` defaults to true, yet `PromotionManager.promote()` does not consult that field, accept verification evidence, check an artifact digest, or bind promotion to a verification result. Its current implementation enforces environment-jump limits and optional approval only. This is a concrete configuration/implementation mismatch; do not count this manager as a verification-enforcing publication boundary.

The older Autonomous API `ProductionReadinessGate` is also not equivalent to certification. It evaluates genome heuristics/metrics and can allow deployment with WARNING when `strict_mode=False`. It should not override evidence-based certification. Its existence illustrates why route reachability and authority resolution matter.

### 11.8 Checkpoint 11 findings

- **FS00-032 — CBC-1 is the strongest integrated verification route, but its use is not universal.** Its real-execution and independent-verification gates apply only where the route invokes CampaignRunner.
- **FS00-033 — campaign provenance is incomplete as a durable execution envelope.** The inspected bundle call omits the evidence-ledger hash; stage records retain hashes/details rather than raw logs or durable log references; source commit, toolchain, verifier/oracle and backend implementation digests are not all bound.
- **FS00-034 — SDK backend CERTIFIED is not equivalent to CBC-1 behavioral certification.** The SDK certification uses sample contract/determinism/output validation and in-memory reports; it does not prove the full native application lifecycle.
- **FS00-035 — Constitutional approval can be vacuous or incomplete.** Approval is based on absence of deployment-blocking failures, without a mandatory executed-check set; skipped verifiers and non-blocking outcomes can coexist with approval. The compiler pass caps the requested level at L3.
- **FS00-036 — evidence authenticity is optional in the Constitutional recorder.** Missing signatures are accepted by the compatibility verifier; production publication needs a policy that requires signed evidence for current certification while explicitly handling legacy records.
- **FS00-037 — Autonomous API verification acceptance permits empty-suite PASS.** Empty required kinds plus empty results return PASS. The acceptance path also lacks exact candidate/source/verifier identity binding.
- **FS00-038 — PromotionManager's require_verification setting is not enforced.** The setting defaults true but is unused in `promote()`; the manager cannot consume or validate artifact-bound verification evidence.
- **FS00-039 — publication safeguards are path-specific.** Governed evolution and desktop release have useful controls, but no single verified-artifact publication authority is proven to cover every compiler family and route.

### 11.9 Required remediation sequence

1. Establish one authoritative verification-result schema with explicit PASS, FAIL, INCOMPLETE, NOT_RUN, INDETERMINATE and BLOCKED states; prohibit empty-policy/empty-result PASS.
2. Require policy-defined mandatory checks to execute. A skipped verifier, timeout, missing verifier, warning on a mandatory check or missing artifact must block the relevant certification level unless a governed exception is recorded.
3. Bind evidence to source commit/tree, requirement graph, ISR, plan, compiler and backend implementation digests, oracle/verifier digests, exact candidate/per-file hashes, toolchain/container image, run ID, environment, raw logs and timestamps.
4. Persist raw logs and evidence envelopes durably before temporary workspaces are destroyed. Link every trial to its hash-chained ledger record and verify both the chain and signatures.
5. Make signature requirements explicit by evidence class and release level. Do not silently treat unsigned new production evidence as equivalent to authenticated evidence; define a migration policy for legacy records.
6. Make all promotion entry points call the same authoritative publication gate. Require exact artifact digest, complete current PASS evidence and the required human/governance authorization. Remove or implement unused `require_verification` controls.
7. Treat SDK sample certification, static conformance, Constitutional L3 approval, CBC-1 behavioral certification and production release authorization as distinct assurance levels with explicit non-transfer rules.
8. Audit actual production route reachability and bypass resistance in Checkpoint 12; source-level existence of a gate is not evidence that all callers are forced through it.

### 11.10 Checkpoint 11 disposition

**PARTIAL — CBC-1 demonstrates a strong integrated fail-closed verification sequence, and selected publication paths enforce governance or artifact-bound human authorization. A universal, durable, authenticated verification-to-publication authority is not established.** No production implementation, test, workflow, capability declaration, certification status or artifact was changed. FS-00 remains a read-only audit/documentation activity.


---

## 12. Checkpoint 12 — production route reachability and bypass resistance

**Inspected revision:** `c3ef3855986713806e26a88fda2fb7f373ec277c`  
**Scope:** route/entrypoint wiring, compiler invocation, verification gates, materialization and publication. This is source-level reachability evidence; no production request or deployment was executed.

### 12.1 Route and entrypoint matrix

| Compiler family / entrypoint | Selection and semantic gate | Verification at this boundary | Output/publication behavior | Reachability assessment |
|---|---|---|---|---|
| ProjectCompiler CLI `tiannara create` | `build_project_compiler` composes the typed IntentCompiler and ProjectCompiler registry; default selection is single-best. | `ProjectCompiler.compile_intent` verifies each successful `CompilationResult`; missing/failed verification prevents a successful report. | `RepositoryMaterializer` writes files and manifest, then optionally commits through local Git. CLI exposes `--force`; the ordinary CLI's preceding compile call already raises on failed verification, so this flag does not establish a general way around that compile-time refusal. | Actual CLI route, but not CBC-1-gated. |
| ProjectCompiler factory CLI | Same ProjectCompiler compilation route; then `SoftwareFactory` adds local execution, verification/repair and evidence recording. | Stronger than `create` on this route, but still a distinct factory workflow and not shown as mandatory for other entrypoints. | Materializer and factory evidence sink; force option is exposed. | Actual CLI route, not a universal authority. |
| ProjectCompiler library materializer | Callable directly with a `ProjectCompilationReport`; no route-level caller identity or governance authorization is required by its signature. | Refuses outcomes with a present failed verification report unless `force=True`; a missing report is not classified as failed by `_verification_failed`. | Writes successful bundle files **before** evaluating the failed-verification refusal; refusal can therefore leave candidate files in the destination. With `force=True`, it records `verification.forced=True` in the manifest and continues. | Explicit, caller-controlled override and non-transactional materialization boundary. |
| Root Universal Compiler API / Gen-A | Mounted FastAPI app exposes `POST /v1/compiler/compile`; handler calls `compiler.compile(payload)` directly. Kernel validates ISR, resolves the requested backend, builds a plan and runs optimization. | Validates compiler output structure. SDK `/v1/compiler/sdk/certify` is a separate endpoint; compile does not require a current SDK certification or CBC-1 trial. | `ArtifactPackager.package` writes each artifact directly under `output_root/job_id` and writes an artifact manifest. No quarantine-and-promote transaction or shared publication gate is invoked here. | Actual HTTP compile route; independent from ProjectCompiler and CBC-1. |
| Constitutional Gen-C pipeline | `compile_intent_to_constitutional_isr` projects intent, verifies source binding, then invokes `CompilerPipeline.compile_source_bound`. Pipeline requires source binding when configured or when ISR carries a graph reference. | CodeGenerationPass refuses source-bound generation unless every selected backend explicitly has `source_bound_codegen_certified is True`. VerificationPass runs later and blocks on verifier errors or lack of deployment approval. Default FastAPI backend does not establish the required source-bound certification. | The inspected pipeline returns artifacts in a CompilationResult; no universal publication transaction is composed here. | Callable orchestration and tests are present; no mounted production HTTP/CLI route was established in this checkpoint. Its source-bound path is fail-closed but presently constrained by backend certification. |
| Autonomous API evolution routes | `autonomous-api/app/main.py` mounts evolution routes under `/api/v1`, plus governance and observation routes. Evolution routes run genome evolution/evaluation; they are not a universal dispatcher for all compiler families. | Candidate evaluation may use runtime or static modes. Governed publication calls `_governance_allows_promotion` and checks an approving decision authorizing the transition when governance enforcement is enabled. | `_publish_governed_candidate` checks the evidence artifact digest and calls `promote_verified_artifact`. | A real, bounded publication path for Autonomous API evolution only; not a shared compiler route or universal publication authority. |
| CBC-1 campaign | `certification/campaign/campaign_a.py` explicitly constructs `CampaignRunner` for the fixed Python FastAPI and Rust Axum backend set and iterates the fixed corpus. Real Docker stages are enabled by the campaign entrypoint. | Runner applies structural and semantic conformance, real-Docker build, test/deploy/runtime stages, independent process verification, full-stack checks and semantic-correspondence checks; aggregate certification requires trial evidence. | Trial candidate workspace is temporary and removed in `finally`; campaign writes trial records to its evidence ledger and aggregate output. | Strong campaign entrypoint, but only when invoked; no inspected compiler route automatically invokes it before materialization/publication. |
| Constitutional PromotionManager | Callable deployment utility, separate from the Gen-C compile pipeline. | `PromotionConfig.require_verification` defaults true but `promote()` does not read it or accept verification evidence. | Records promotion history/events after environment-jump and optional approval checks; does not bind a verification result or artifact digest. | Not a verification-enforcing compiler publication gate. |

### 12.2 Confirmed route-level findings

- **FS00-040 — compiler entrypoints remain separate.** ProjectCompiler CLI, Gen-A HTTP API, Gen-C callable pipeline, Autonomous API evolution and CBC-1 campaign are independently composed. The source does not establish one mandatory compiler invocation route or one registry shared by all of them.
- **FS00-041 — CBC-1 is opt-in by orchestration, not a universal prerequisite.** The campaign entrypoint explicitly runs its fixed corpus/backend matrix. No call from the inspected ProjectCompiler materializer, Gen-A compile handler or Gen-C pipeline requires a CBC-1 trial before output or publication.
- **FS00-042 — Gen-A compile bypasses SDK/CBC certification requirements.** The mounted compile handler directly calls the UniversalCompiler kernel. SDK certification is separately callable and its state is not consulted by the compile handler; the kernel proceeds from ISR validation and backend resolution to output validation and packaging.
- **FS00-043 — Gen-A packages directly into the output tree.** ArtifactPackager writes generated files and the manifest directly into the job output directory after structural validation. No shared quarantine, immutable candidate approval or governed promotion boundary is invoked by the API route.
- **FS00-044 — ProjectCompiler materialization is not atomic and has a public override seam.** RepositoryMaterializer writes bundle files before checking failed verification. It permits `force=True` to continue after a present failed report and records the override, but does not require a distinct human/governance authorization token or bind one to the artifact digest. A failed call may leave files in the destination even when it raises.
- **FS00-045 — the CLI force flag must not be confused with a universal verification bypass.** The inspected `create` command calls `compile_intent` first, and that method raises when verification is absent or failed; thus its normal flow does not reach materialization on such a failed report. The materializer remains independently callable with a forced report, and the factory route exposes its own force option. This is a library/API bypass surface, not evidence that every CLI compile failure can be forced through.
- **FS00-046 — Gen-C source-bound gate is reachable but blocks the default backend.** The source-bound intent entrypoint reaches the pipeline, which checks backend source-bound certification before emission. Since the default FastAPI backend does not establish that certification, this is a fail-closed restriction, not evidence of a functioning source-bound production compiler. No mounted production route was found for the entrypoint.
- **FS00-047 — Autonomous API governance is local to its evolution publisher.** The approval-plus-digest gate is meaningful on `_publish_governed_candidate`, but mounted evolution routes do not establish universal compiler-family coverage. Governance enforcement is conditional on `GOVERNANCE_ENFORCEMENT_REQUIRED`; when false, `_governance_allows_promotion` returns true. The separate Constitutional PromotionManager does not enforce its `require_verification` setting.

### 12.3 Bypass and coverage conclusions

1. A gate's presence in a compiler family does not make it mandatory for other families. CBC-1, SDK certification, Gen-C verification and Autonomous API governance have distinct callers and evidence contracts.
2. Gen-A's compile route does not require SDK certification or CBC-1 and packages directly after output validation.
3. ProjectCompiler's main compile method is stricter than the materializer's standalone interface: a failed or missing verifier blocks report creation, but the materializer can be called independently and has a force override. Its write-before-refusal ordering also means refusal is not equivalent to zero output side effects.
4. Gen-C source binding and pre-generation backend certification are path-specific. The default backend currently fails the latter condition, and the entrypoint is not shown mounted as a production route.
5. Autonomous API governance protects one publication path only, and its enforcement setting controls whether an approval is required. It is not the constitutional authority for every compiler family.
6. The CBC-1 campaign is a certification program, not a route-level middleware or mandatory compilation service. No source evidence connects every compile/publish path to a current CBC-1 verdict.
7. No single publication function is shown to receive every artifact from every compiler family, verify an exact candidate digest against complete mandatory evidence, and require the appropriate governance/human authorization.

### 12.4 Required remediation sequence

1. Inventory and register every compiler entrypoint and every artifact-writing/publication function in one authoritative route registry; require each route to declare its assurance policy and evidence level.
2. Make route execution call a shared, fail-closed compilation authorization service that checks semantic capability, mandatory verification policy and exact source/candidate identity before generation and before publication.
3. Move ProjectCompiler materialization checks before all writes; use isolated candidate staging and atomic promotion. Replace boolean `force` with an explicit, signed, scoped exception decision bound to candidate digest, reason, actor, expiry and permitted assurance downgrade.
4. Require Gen-A to consult current backend certification and the required verification policy before packaging; stage output in quarantine and promote only through the shared publication gate.
5. Keep Gen-C blocked for source-bound output until a backend has independently earned source-bound semantic certification and a complete mandatory verifier set is enforced. Do not weaken the gate to make the route appear operational.
6. Make Autonomous API governance enforcement fail closed for consequential publication; bind approval to the exact artifact digest and make the required enforcement mode immutable for production.
7. Either integrate CBC-1 as a required assurance stage for the relevant release class or explicitly define which lower assurance class may publish without it. Do not imply universal certification from a campaign result for two backends.
8. Add route-level negative tests proving that every direct materializer, packager, API and deployment path rejects missing, stale, mismatched, skipped or failed evidence and cannot write/publish on refusal.

### 12.5 Checkpoint 12 disposition

**PARTIAL — source inspection confirms several useful local gates, including Gen-C's pre-generation source-bound certification check and Autonomous API's governed evolution publisher. They are not universal. Gen-A compiles and packages through a separate route without SDK/CBC certification enforcement; ProjectCompiler exposes an independently callable forced materializer with write-before-refusal behavior; and CBC-1 is not a mandatory prerequisite across compiler families. No production implementation, test, workflow, capability declaration, certification status or generated artifact was changed.**


---

## 13. Checkpoint 13 — backend and language coverage

**Inspected revision:** `130501b8aff88e750cfeb62c6ae816b982f45499`  
**Scope:** registered target inventory, language/framework diversity, capability declarations, semantic gates, backend conformance, verification profiles and available native-execution evidence. This is a source/documentation audit; no generated target was built or run during this checkpoint.

### 13.1 ProjectCompiler target inventory

The Cap-C composition root registers 21 target implementations in one in-memory `CompilerRegistry`:

| Target family | Registered IDs | Language / platform |
|---|---|---|
| Backend services (11) | `fastapi_hexagonal`, `go_hexagonal`, `rust_axum`, `nestjs`, `spring_boot`, `aspnet_core`, `phoenix`, `ktor`, `express`, `laravel`, `rails` | Python, Go, Rust, TypeScript/JavaScript, Java, C#, Elixir, Kotlin, PHP, Ruby |
| Frontend/application (10) | `android`, `react`, `vue`, `angular`, `next`, `nuxt`, `svelte`, `liveview`, `hologram`, `scenic` | Kotlin/Android plus JavaScript/TypeScript and Elixir-oriented web targets |

The registry is real wiring, not just a documentation list: `build_compiler_registry()` constructs each backend and registers its backend-supplied declaration. The compiler-matrix test asserts at least 20 declarations and checks that select-all planning can resolve each declaration's own artifact-kind/capability requirement. This proves registry/selection coverage for those declarations, not that every target compiles a representative full application, builds natively, runs, or preserves every ISR semantic.

A composition docstring is stale: `build_project_compiler()` says the omitted registry defaults to a FastAPI-only registry, but the implementation actually calls `build_compiler_registry()` and therefore supplies the 21-target registry. This is a documentation defect; the inspected code path is the authority for this checkpoint.

### 13.2 Distinct capability authorities do not add up to universal semantic coverage

Three relevant capability systems remain separate:

1. **Cap-C `BackendCapabilityDeclaration`:** used by the 21-target ProjectCompiler registry and selector. Selection matches artifact kind and broad `BundleCapability` declarations. It does not itself prove that each backend consumes and enforces the typed behavioral obligations in canonical `CompilationPlan`.
2. **Canonical behavioral `BackendCapabilities`:** `compiler/core/capabilities.py` derives semantic obligations from a `CompilationPlan` and rejects unsupported features. The current reference behavioral implementations inspected here are Python FastAPI and Rust Axum. This strong gate is not wired as a universal adapter for all 21 Cap-C targets.
3. **Gen-C backend conformance:** `tiannara/application/compilation/backend_capability_registry.py` registers seven real category backends (React, FastAPI, Postgres, Terraform, CI/CD, Pytest and Markdown) against its separate 12-semantic/14-carrier contract. It uses explicit SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED declarations and a projection adapter. This is useful evidence of honest limits for those seven implementations, but it is not the Cap-C registry or the canonical behavioral backend registry.

**Finding:** a target's presence in one registry, or its broad artifact capability declaration, must not be interpreted as certification under either of the other semantic contracts.

### 13.3 Observed Gen-C semantic coverage

The seven Gen-C declarations are deliberately sparse:

| Backend | SUPPORTED | PARTIALLY_SUPPORTED | Consequence |
|---|---|---|---|
| React | behavior transitions; business capabilities | — | Temporal, requirement/acceptance traceability, design-token and other carriers remain unsupported |
| FastAPI | behavior transitions; business capabilities | reliability/resilience; architecture boundaries; deployment rollout/rollback | Several dimensions are only structural/presence-level; deployment behavior is not fully realized |
| Postgres | data migrations | — | Migration target schema is supported; compatibility/rollback and other semantic carriers are not |
| Terraform | — | deployment rollout/rollback | Topology artifacts are emitted from structural genome inputs; rollout/health/rollback semantics are not realized |
| CI/CD | — | deployment rollout/rollback; testing anchoring; reliability/resilience | Presence-level bundle composition, not full policy/evidence semantics |
| Pytest | — | testing anchoring | Test artifacts are emitted but are not bound to acceptance-anchor evidence |
| Markdown | documentation | — | Native documentation artifacts exist, but DocumentationIntent purpose/audience/coverage references are not consumed |

The registry defaults undeclared semantic IDs to UNSUPPORTED, which is the correct fail-closed posture. Its own findings also identify genome-driven or empty-default behavior outside the semantic projection. These declarations must not be silently upgraded because the corresponding backend can emit an artifact.

### 13.4 Canonical behavioral backend coverage

The canonical semantic gate is materially stronger than broad bundle-capability selection. It derives obligations including typed fields, decimal shape, constraints, expressions, business rules, state transitions, API contracts, authorization, executable effects, effect-policy/binding preservation, consequence preservation, invariants and typed events.

The two inspected reference backends declare different subsets:

- Python FastAPI supports typed fields, decimal shape, expressions, business rules, state transitions, API contracts, authorization, effect policy/binding preservation, consequence preservation and executable-effect execution. It also performs plan-level authorization-enforceability checks.
- Rust Axum supports typed fields, decimal shape, expressions, business rules, state transitions and preservation of effect policy/bindings and consequences. It does not claim the Python backend's API-contract, authorization or executable-effect feature set.

The tests correctly assert that unsupported semantics fail before emission. They also expose an important distinction: preservation of an effect binding or consequence is not the same as executing the external effect or realizing its consequence. The test suite explicitly keeps bank-transfer semantics blocked pending durable execution binding. Rust API contracts and authorization obligations also remain blocked. The two backends therefore provide a useful, intentionally non-identical semantic baseline, not full parity.

### 13.5 Verification and native execution are uneven by language

Cap-C build profiles carry language, required files, build/test commands and optional runtime-image/build-phase information. The deterministic verifier dispatch is much narrower:

- Python: required files, Python syntax compilation and domain-to-outer-layer import direction.
- Go: required files, `go.mod` module declaration and domain import direction.
- Other languages: `RequiredFilesVerifier`, which checks required-file presence only.

Consequently, Kotlin, Rust, TypeScript/JavaScript, Java, C#, Elixir, PHP and Ruby do not receive equivalent language-aware syntax/compile checks from this deterministic verifier dispatch. Some backends supply native build/test commands, and a separate execution harness may run them when the toolchain is available; a declared command or a skipped toolchain stage is not native PASS evidence.

CBC-1 Campaign A is explicitly fixed to **39 workloads × 2 backends: Python FastAPI and Rust Axum**. Its real-Docker entrypoint records evidence for those two targets only. This is meaningful cross-backend campaign coverage, but it does not certify the remaining Cap-C languages or frontend/mobile targets. The compiler-matrix test is a registration/planning test; it is not a 21-target native build campaign.

### 13.6 Android and frontend boundary

The Cap-C Android backend is intentionally narrow. It emits a Kotlin/Jetpack Compose static model-catalogue shell, requires at least one data model, and refuses service, API and event semantics. Its declaration is limited to BUILD and DOCUMENTATION; it does not claim persistence, CRUD, authentication, synchronization or network behavior. Its build profile names a Gradle debug-APK command but no test command. The Android backend tests verify registration, emitted project structure, determinism and refusal of unsupported semantics; they do not establish an executed Gradle build, APK installation, emulator behavior or device-level acceptance.

The frontend targets likewise must be assessed per target and per assurance level. Existing compile-time refusal tests and emitted Playwright artifacts do not prove generated authorization runtime behavior or native mobile execution. The Android cloud-build workflow and the two Android compiler implementations remain distinct routes; none of this checkpoint's source inspection upgrades Stage A or Android certification.

### 13.7 Confirmed findings

- **FS00-048 — Cap-C has 21 registered target implementations, not 21 certified application compilers.** The registry covers 11 backend-service targets and 10 frontend/application targets across multiple languages and frameworks. Registry presence and selection are established; complete application behavior and native execution are not.
- **FS00-049 — Cap-C's broad bundle-capability selection is not canonical semantic certification.** The selector matches artifact kinds and declared bundle capabilities. It is not a substitute for `required_features(CompilationPlan)` or independent semantic conformance.
- **FS00-050 — canonical behavioral enforcement is currently narrow.** The inspected canonical semantic capability gate is implemented by the Python FastAPI and Rust Axum reference backends; no universal adapter applies it to all Cap-C or Gen-C backends.
- **FS00-051 — Gen-C's seven-backend conformance registry is a separate authority.** Its explicit 12-semantic/14-carrier declarations are valuable but cannot be transferred to the 21 Cap-C targets or the canonical behavioral registry without tested adapters and evidence.
- **FS00-052 — declared Gen-C semantic support remains sparse and frequently partial.** Only selected dimensions are fully supported; several deployment, reliability, testing and architecture claims are presence-level or structurally derived, and many carriers remain unsupported.
- **FS00-053 — language-aware static verification is incomplete.** The Cap-C verifier provides deeper Python and Go checks; other languages fall back to required-file presence in the deterministic verifier dispatch. Backend-supplied build commands do not prove they were executed.
- **FS00-054 — CBC-1's native campaign covers two backend languages only.** Campaign A's 78 trials are Python FastAPI and Rust Axum across 39 workloads. They do not certify the other backend, frontend, mobile or Android targets.
- **FS00-055 — Android is a real but deliberately static target.** It emits a Kotlin/Compose project shell and refuses service/API/event semantics; a Gradle command and structural tests do not establish a successful APK build or device behavior.
- **FS00-056 — the ProjectCompiler composition documentation is stale.** The `build_project_compiler` docstring says its default registry is FastAPI-only, while the current implementation calls the 21-target `build_compiler_registry()`. Correct the documentation in a later implementation change; do not alter production code during FS-00.

### 13.8 Required remediation sequence

1. Preserve all 21 target implementations. Do not retire a useful language/framework merely because its semantic coverage or native toolchain evidence is incomplete.
2. Define one technology-neutral semantic capability contract and explicit, versioned adapters from it into each target. Unknown or unconsumed mandatory semantics must block generation.
3. Reconcile Cap-C bundle capabilities, canonical behavioral features and Gen-C carrier declarations through evidence-backed mappings. No implicit capability transfer across registries.
4. Build a per-target capability matrix covering input consumption, emitted behavior, unsupported semantics, build/test commands, native toolchain availability, runtime evidence and independent acceptance.
5. Add language-aware static verification and real native build/test stages for each target. Record missing toolchains as SKIPPED/UNKNOWN, never PASS.
6. Expand CBC-1 or an equivalent independent campaign incrementally across backend languages and representative frontend/mobile targets. Preserve the current Python/Rust evidence scope and do not generalize its verdict.
7. For Android, bind the compiler to the canonical behavioral IR and implement only explicitly supported semantic subsets; retain fail-closed refusal until runtime, persistence, authorization and device behavior are genuinely implemented and independently tested.
8. Fix the stale composition docstring in a separate reviewed implementation change, not in this read-only audit checkpoint.

### 13.9 Checkpoint 13 disposition

**PARTIAL — the repository has broad and useful language/framework diversity, including 21 Cap-C target registrations, a stronger canonical semantic gate for Python/Rust, and a separate evidence-based seven-backend Gen-C conformance registry. These systems do not yet form one shared semantic capability authority. Native campaign evidence is concentrated on Python FastAPI and Rust Axum; language-aware static verification is uneven; and Android remains a deliberately static Kotlin/Compose shell. No production implementation, test, workflow, registration, capability declaration, certification state or generated artifact was changed.**


---

## 14. Checkpoint 14 — frontend, mobile, Android and cloud compilation

**Inspected revision:** `50aca3d36b299e579f718b61343b8329e21c8c9c`  
**Scope:** frontend target inventory and generation behavior, capability declarations, browser/unit/native evidence, mobile target coverage, Android source binding and cloud execution. This is a read-only source and workflow audit. No workflow was dispatched and no build, emulator or test suite was executed by this audit.

### 14.1 Frontend target inventory and declared maturity

The Cap-C composition root registers six TypeScript browser/hybrid targets (React, Vue, Angular, Next.js, Nuxt and Svelte) and three Elixir targets (Phoenix LiveView, Hologram and Scenic). The separate `FRONTEND_TARGETS` matrix records all nine and marks every one `production_ready=False`. That is an important explicit maturity signal: registration is not a production-readiness claim.

The six TypeScript targets each emit framework-specific project files and use a typed `SystemModel` obtained from the ISR. Their current generated behavior is intentionally small: an application title, a catalogue of declared data-model names and a filter interaction. They do not yet constitute general UI generation from arbitrary page, route, form, navigation, API-client, authorization or design-system requirements.

The six targets' capability manifests are deliberately limited to BUILD, TEST and DOCUMENTATION. Tests explicitly guard against claiming LINT, STATIC_ANALYSIS, SECURITY_SCAN or RELEASE. This is more honest than the broader Elixir manifests described below.

### 14.2 Browser evidence is real but narrowly scoped

The repository contains generated-browser CI workflows for React, Vue, Next.js, Nuxt and Svelte. They install dependencies, build the generated fixture, run unit tests and Playwright browser tests. React, Vue, Next and Svelte workflows also exercise a negative control that deliberately breaks the generated filter and require the browser suite to reject it; Nuxt has a corresponding negative-control step. This is meaningful execution evidence for the tested generated UI slice, not merely a test-file declaration.

The test suites and workflow comments explicitly limit the claim: they do not establish route, form, API-client or authentication parity. Their assertions concentrate on heading/model-list rendering and filter interaction, including overlapping names and empty-model cases. The independent generated-frontend certification workflow under `autonomous-api/` is another React-only route and must not be conflated with all Cap-C targets.

An Angular browser-evidence test file exists, but the inspected workflow inventory contains no matching `tiannara-angular-browser-evidence.yml` workflow. Angular has generated unit/E2E artifacts and structural tests, but the same executed browser-CI evidence path seen for the other five TypeScript targets was not established here.

### 14.3 Elixir UI targets are substantially less complete than their declarations imply

The LiveView, Hologram and Scenic targets are registered with distinct runtime-model labels, but their generated projects are minimal source shells:

- LiveView emits a tiny `mix.exs`, a minimal LiveView module and a test that checks the module can be loaded. The emitted Mix project does not declare the Phoenix/LiveView dependencies or a complete OTP/Phoenix application, endpoint and router wiring needed for a runnable production LiveView application.
- Hologram emits a Mix project, a plain Elixir page module and a title assertion. The inspected output does not demonstrate Hologram dependencies, compiler integration, client bundle generation or an operational server/client UI.
- Scenic emits a Mix project, a plain scene module and a title assertion. The inspected output does not demonstrate Scenic dependencies, a Scenic application/window/viewport or a native GUI launch.

Their capability manifests nevertheless claim BUILD, LINT, STATIC_ANALYSIS, TEST, SECURITY_SCAN, DOCUMENTATION and RELEASE. The current minimal emitted projects and tests do not substantiate all those claims. The frontend-manifest guard test checks only the six TypeScript targets, so it does not catch these three Elixir declaration discrepancies.

**Finding:** retain these three distinct targets, but treat them as structural prototypes until their dependencies, application wiring, native runtime behavior and truthful capability declarations are implemented and independently verified.

### 14.4 Frontend-to-backend integration and semantic completeness

The inspected browser evidence deliberately avoids claiming API or authentication behavior. The frontend generators do not yet show a mandatory, evidence-backed binding from generated UI actions/forms/routes to canonical backend API contracts, authorization policies, effect bindings and consequence semantics.

This leaves an integration gap between the frontend's visible behavior and the backend's governed behavior. A frontend can render and filter a list while the full application contract—read/write operations, validation, authentication, authorization, error states, persistence, offline behavior and backend effects—remains absent or unproven.

The required next architectural step is not to duplicate backend logic in each frontend framework. It is to define a shared, technology-neutral UI/application contract bound to the same authoritative ISR and canonical API/effect contracts, then require target adapters to preserve it and fail closed on unsupported interactions.

### 14.5 Mobile and Android coverage

The inspected repository tree contains an Android target but no dedicated iOS/Swift, Flutter, React Native or Expo compiler target. This is a coverage gap, not a reason to retire Android or constrain the intended universal-software scope. Cross-platform/mobile targets should be added only with explicit semantic adapters and real build/runtime evidence.

The Cap-C Android target remains the deliberately static Kotlin/Jetpack Compose catalogue shell identified in Checkpoint 13. It refuses service, API and event semantics and does not claim persistence, authentication, synchronization or network behavior.

A separate campaign-native Android backend and cloud workflow provide stronger structural assurance than that shell's source tests alone. The manual workflow:

1. checks out an exact source revision;
2. verifies source specification, serialized `ISRRevision`, and a derivation-manifest hash;
3. recompiles the ISR revision into a canonical plan and candidate;
4. recomputes candidate binding before execution;
5. runs Gradle, inspects the APK, installs it on an Android emulator and launches it; and
6. preserves candidate-bound evidence and an explicit `STRUCTURAL_CHECKS_ONLY` verdict.

The structural runner refuses mismatched revision, plan or repository hashes and never returns a campaign CERTIFIED verdict. These are good source-binding and evidence-boundary controls.

### 14.6 Android cloud workflow is not Android application certification

The Android cloud workflow is manually dispatched for a supplied candidate and source-binding set; its pull-request job runs only the backend/runner contract tests. At the inspected PR head, the `android-backend-tests` check completed successfully and the `android-cloud-build` check was skipped, consistent with its manual-dispatch condition. No cloud APK/emulator run was established by this checkpoint.

More importantly, the campaign documentation states that the current ESAP-APP-001 problem/acceptance artifacts remain `PROPOSED_AWAITING_REVIEW_AND_HASH_FREEZE`. The source-binding manifest is a pinned hash assertion, not a cryptographic reviewer signature; reviewer approval must be established separately through repository review/governance.

The documentation also states that a faithful benchmark ISR includes CRUD, validation, search, persistence and offline behavior that the current Android structural backend does not implement. The expected outcome is therefore a fail-closed refusal before APK generation until those semantics exist. Stripping requirements to obtain a successful build would invalidate the benchmark.

Even a successful Gradle/APK/install/launch sequence would prove structural execution only. It would not satisfy benchmark runtime acceptance criteria AC-002 through AC-012 or certify ESAP-APP-001.

### 14.7 Confirmed findings

- **FS00-057 — all nine registered frontend targets are explicitly not production-ready.** The target matrix marks React, Vue, Angular, Next, Nuxt, Svelte, LiveView, Hologram and Scenic as `production_ready=False`; registry membership must not be presented as production certification.
- **FS00-058 — TypeScript frontend generation is a narrow UI slice, not general application generation.** The six targets emit a model catalogue and basic filtering from typed ISR-derived models. General route, form, API, auth, authorization, design-system and full application behavior remain unproven.
- **FS00-059 — browser execution evidence covers five TypeScript targets, not all six.** React, Vue, Next, Nuxt and Svelte have generated-browser workflows; Angular has tests but no matching browser-evidence workflow in the inspected tree.
- **FS00-060 — browser evidence proves only its asserted interaction scope.** Playwright workflows exercise rendering and filtering, including negative controls and edge cases, while explicitly disclaiming route/form/API-client/auth parity.
- **FS00-061 — Elixir frontend capability manifests overstate demonstrated behavior.** LiveView, Hologram and Scenic declare build, lint, static analysis, test, security scan, documentation and release capabilities, while their generated projects are minimal shells without demonstrated complete framework/native application wiring. Existing manifest guard tests omit these targets.
- **FS00-062 — frontend/backend contract binding is not established as a mandatory shared boundary.** The inspected UI tests do not prove that UI operations preserve canonical API contracts, authorization, effect bindings and consequence semantics end-to-end.
- **FS00-063 — no dedicated iOS or cross-platform mobile compiler target was found.** The inspected repository tree contains no Swift/iOS, Flutter, React Native or Expo target. This is an open coverage requirement, not grounds for retiring other targets.
- **FS00-064 — Android cloud execution has strong structural source-binding controls.** Exact source/revision/manifest hashes and candidate recomputation are checked before Gradle/APK/emulator execution; the runner preserves a structural-only verdict.
- **FS00-065 — Android cloud structural success cannot certify ESAP-APP-001.** The benchmark source artifacts remain awaiting approval/hash freeze, the current Android backend cannot realize the benchmark's required semantics, and AC-002 through AC-012 require separate direct runtime evidence.

### 14.8 Required remediation sequence

1. Preserve all nine frontend targets and Android. Do not collapse distinct runtime models or retire incomplete language/framework routes.
2. Define the shared UI/application contract over authoritative ISR and canonical API/effect semantics. Include routes, forms, navigation, state, validation, error handling, accessibility, authorization, offline behavior and design-system constraints as explicit typed obligations.
3. Add explicit per-target support declarations and source-bound adapters. Unknown or unconsumed UI/API semantics must block generation rather than silently disappear.
4. Expand framework behavior beyond model-name catalogues. Generate representative, requirement-derived application workflows and test actual user-visible behavior.
5. Add Angular's generated-browser workflow and align all framework workflows on consistent build, unit, browser, negative-control and evidence-binding standards.
6. Correct the LiveView, Hologram and Scenic manifests to match demonstrated capabilities immediately in a separate reviewed implementation change; then implement their real framework dependencies, application wiring, native runtime and acceptance tests before capability upgrades.
7. Establish end-to-end frontend/backend tests that trace a user action through generated UI, API contract, authorization, backend effect and observable consequence. Independent oracles must derive from requirements, not copy generator output.
8. Add iOS and cross-platform mobile targets through deliberate architecture decisions, with framework-specific build/runtime environments and device-level acceptance. Do not claim universal mobile support before evidence exists.
9. Keep Android source-binding and structural cloud checks. First approve and freeze the benchmark through governance, then implement the required semantics; never weaken the source specification to make the current static backend pass.
10. Expand independent certification across all frontend and mobile targets. Separate source generation, framework build, browser/device execution, semantic acceptance, security and production readiness as distinct evidence states.

### 14.9 Checkpoint 14 disposition

**PARTIAL — five TypeScript frontend targets have meaningful generated-browser CI for a narrow catalogue/filter interaction; Angular lacks the matching workflow; the three Elixir UI targets remain structural shells whose capability manifests overstate demonstrated behavior. Frontend-to-backend semantic integration is not established as a compulsory shared contract. Android has a well-designed source-bound structural cloud execution path, but its current backend cannot realize the benchmark's full runtime semantics, and the benchmark itself remains awaiting approval/hash freeze. No dedicated iOS or cross-platform mobile compiler target was found. No production implementation, test, workflow, capability declaration or certification state was changed.**


---

## 15. Checkpoint 15 — integrated architecture and FS-00 closure assessment

**Inspected PR head:** `09713a60dffae61a35b332d510dfbe2f27cb3ebf`  
**PR state:** #201 remains open, draft and unmerged.  
**Scope:** integrate Checkpoints 1–14; re-check active authority boundaries, canonical lowering, backend composition, Android evidence, route enforcement, and the original FS-00 exit criteria. This is a read-only architecture audit apart from this report update. No production implementation, tests, workflows, capability declarations or certification states were changed.

### 15.1 Architecture synthesis — the repository contains several real compiler systems, not one compulsory compiler authority

The audit evidence supports four distinct implementation families that must not be conflated:

1. **Cap-C ProjectCompiler:** the broad 21-target registry (11 backend-service and 10 frontend/application targets) provides meaningful target discovery and selection. It does not prove that every target consumes the same typed semantic obligations or has native runtime evidence.
2. **Canonical behavioral compiler core:** `isr/core` revisions lower through `compiler/core/lowering.py:isr_to_plan` into a typed `CompilationPlan`. `compiler/core/capabilities.py` derives semantic obligations and rejects unsupported plans. The strongest demonstrated behavioral backend implementations remain Python FastAPI and Rust Axum, with intentionally different support sets. The campaign-native Android backend is explicitly structural-only.
3. **Gen-C / constitutional and category compiler paths:** these use distinct requirement/ISR representations, lowering and capability/conformance registries. Their source-binding and governance controls are valuable on their own paths, but they are not proven to be mandatory adapters for every other compiler family.
4. **Root Universal Compiler API / SDK path:** `compiler/api.py` constructs a separate registry containing a reference backend and registered production backends, then exposes `POST /v1/compiler/compile` directly to `UniversalCompiler.compile`. SDK routes are enabled alongside it, but the compile route itself does not establish that CBC-1, universal semantic certification, or every other compiler family's governance/publication gates are compulsory.

The smaller `compiler/composition.py` root separately registers Python FastAPI, Rust Axum and Android into the behavioral core registry. This is another concrete composition boundary, not the 21-target Cap-C registry. A name such as “Universal Compiler” or a target's presence in one registry must not be treated as proof that all production routes converge on one governed authority.

**Integrated conclusion:** the critical FS00-001 / FS00-005 / FS00-048–051 / FS00-066 issue remains open. The repository has multiple functioning compiler subsystems and valuable adapters, but a single mandatory end-to-end compilation authority is not established.

### 15.2 Requirement and ISR authority — canonical behavioral lineage is strong but not universal

The strongest explicit typed path remains:

`ISRRevision → isr_to_plan → CompilationPlan → semantic capability gate → backend`

The lowering carries typed behavior and explicit graph relationships, including API/service links, effect bindings and consequences. The backend capability gate derives requirements from populated plan fields and refuses unsupported semantics. This is a sound foundation and should be extended rather than replaced.

However, the repository still contains multiple RequirementGraph/ISR-like models and contract drift documented in Sections 5–6. The source-bound Constitutional path, canonical requirement-reference projection, CAP-001 EngineeringISR projection, campaign `ISRRevision`, legacy-compatible SystemModel and Gen-C rich ISR are not demonstrated as one governed versioned chain.

A fresh source check of `autonomous-api/app/engine/requirement_isr.py` also confirms that its `project_to_isr` implementation is a conservative, partial projection rather than the canonical behavioral ISR lowering. It creates entities only from explicit `entity:` tags, policies from requirement kinds, invariants from a short lexical token list, and interfaces from keyword matches. It does not itself construct the complete typed API, authorization, effect, consequence, event, frontend interaction and executable behavior graph carried by `isr/core` revisions. The integrity validator checks duplicate IDs, dangling references, technology leakage and traceability coverage; those structural checks do not prove that every requirement's meaning was represented in the projection.

- **FS00-066 — CAP-001 EngineeringISR projection is intentionally partial and lexical.** It must not be mistaken for complete semantic equivalence with the canonical behavioral ISR or used as a substitute for `ISRRevision → CompilationPlan`. Any route using it for generation needs explicit typed obligation coverage and a blocking completeness check.
- **Integrated disposition:** the authoritative model/version map, live-consumer migration, complete MUST-requirement realization mapping and semantic-diff gates remain unresolved. Hash identity and traceability are necessary but do not prove semantic preservation.

### 15.3 Backend and frontend capability — preserve diversity; certify claims individually

The 21 Cap-C registrations, seven Gen-C conformance declarations, behavioral Python/Rust implementations and Android structural backend represent useful diversity. They do not share one proven, evidence-backed capability authority.

The evidence still supports these boundaries:

- Python FastAPI has the broadest demonstrated behavioral subset among the canonical reference backends, including API contracts, authorization and executable effects, but important storage/effect durability and production acceptance boundaries remain.
- Rust Axum has a narrower semantic subset and correctly refuses unsupported API/auth/effect-execution semantics rather than inheriting Python's claims.
- Other backend targets vary from useful scaffolds to partial CRUD/service generation; required-file presence and declared build commands are not equivalent to language-native build or behavioral verification.
- Five TypeScript frontend targets have meaningful but narrow catalogue/filter browser evidence; Angular lacks the matching workflow identified in Checkpoint 14.
- LiveView, Hologram and Scenic remain minimal shells whose capability declarations exceed demonstrated runtime behavior.
- Android remains a structural static-catalogue target and refuses unsupported application semantics. Its separate native runner is a structural evidence mechanism, not a behaviorally certified Android compiler.
- No dedicated iOS/Swift, Flutter, React Native or Expo target was found in the inspected tree.

The correct strategic decision remains **preserve all target families and improve them incrementally**. Retiring incomplete targets would narrow the intended universal scope without solving the shared semantic-authority problem. Conversely, registering or selecting them must never upgrade their capability or production-readiness state.

### 15.4 Android PR-head execution evidence — backend tests passed; cloud build did not run

The GitHub Actions run associated with the inspected PR head is run **#88**, workflow `ESAP Android Cloud-Build Certification (Stage A)`, run ID `42007428668`, head SHA `09713a60dffae61a35b332d510dfbe2f27cb3ebf`.

Its two jobs have different outcomes:

| Job | Result | What it establishes |
|---|---|---|
| `android-backend-tests` | SUCCESS | The workflow installed dependencies and ran `tests/test_android_campaign_backend.py` and `tests/test_android_structural_runner.py` successfully on this PR head. |
| `android-cloud-build` | SKIPPED | No Gradle build, APK inspection, emulator install or launch occurred in this PR-triggered run; the job is conditioned on `workflow_dispatch`. |

The workflow's overall conclusion is `success` because the PR-triggered backend contract-test job passed and the manual cloud-build job was skipped. It is incorrect to report this as a successful Android cloud build.

The manual workflow retains useful controls: exact source-revision checkout, path containment, source/ISR/manifest hash checks, revision revalidation and candidate re-derivation before native execution. The benchmark instructions still explicitly require independent approval/hash freeze and state that even successful APK/emulator structural execution does not satisfy AC-002 through AC-012. The current source/acceptance artifacts remain marked `PROPOSED_AWAITING_REVIEW_AND_HASH_FREEZE`; the Android backend is expected to refuse a faithful benchmark carrying unsupported CRUD, validation, search, persistence and offline semantics.

**Evidence classification:** PR-head backend contract tests = PASS for that test scope; cloud native execution = NOT RUN in this run; Android runtime acceptance and ESAP-APP-001 certification = BLOCKED / NOT ESTABLISHED. No capability or certification status is upgraded.

### 15.5 Integrated route, verification and publication assessment

Across Checkpoints 9–12, the evidence establishes several strong components but not a compulsory system-wide chain:

- source-binding checks are substantive on selected paths, not mandatory across all production compiler entrypoints;
- the typed behavioral lowering and fail-closed backend feature gate are strong where invoked, but not shown as universal adapters for all 21 Cap-C targets, Gen-C, root API and all materializers;
- CBC-1 Campaign A's 78 trials remain bounded to 39 workloads across Python FastAPI and Rust Axum;
- independent oracles are meaningful for selected behaviors, but acceptance coverage and oracle independence are not complete for every promoted semantic feature;
- evidence records and hash chains exist, but the universal evidence envelope does not bind every source, requirement graph, ISR, plan, backend digest, oracle, artifact, toolchain and raw execution log;
- direct compilation/materialization routes and governance/publication paths remain distinct; universal quarantine, independent verification and authorized atomic promotion are not established;
- the root `/v1/compiler/compile` route is reachable independently of the SDK certification routes and is not proven to require CBC-1 before reporting success.

The control objective is not that every compiler call must run one heavyweight campaign synchronously. It is that every route must be governed by the same authoritative contract, must select an evidence-backed target capability subset, and must be unable to publish or claim a higher assurance state without the required independent evidence and authorization.

### 15.6 FS-00 exit-criteria status

| Exit criterion | Integrated status | Remaining blocker |
|---|---|---|
| One authoritative RequirementGraph | OPEN | Multiple models/taxonomies and path-specific consumers |
| One reconciled, versioned ISR contract | OPEN | Contract/schema drift and parallel ISR representations |
| One canonical compiler IR and mandatory adapters | PARTIAL | Typed `CompilationPlan` exists, but not universal across compiler families |
| Complete requirement lineage on every production route | PARTIAL | Strong bounded paths; universal route binding absent |
| MUST requirements cannot silently disappear | NOT ESTABLISHED universally | No mandatory completeness/semantic-diff gate on every route |
| Explicit per-target semantic subsets and fail-closed behavior | PARTIAL | Strong for reference backends; inconsistent coverage across target families |
| Tautological tests excluded from verification claims | OPEN | Previously identified weak/tautological generated tests remain to be replaced |
| Independent requirement oracles for every claimed feature | PARTIAL | Narrow campaigns and feature-specific scenarios |
| Native build/runtime evidence for every promoted target | NOT ESTABLISHED | Coverage limited by language/framework/toolchain; mobile/native gaps |
| Complete source-to-runtime evidence envelope | PARTIAL | Universal digest/provenance/log binding incomplete |
| Quarantine, verification and authorized atomic publication on every route | NOT ESTABLISHED | Direct and path-specific publication routes remain |
| Equivalent frontend/backend requirement-derived acceptance | NOT ESTABLISHED | UI/API/auth/effect end-to-end semantic contract and evidence incomplete |

### 15.7 Priority closure sequence

The recommended order is dependency-driven. Do not expand certification breadth before settling the shared authority and lineage contracts.

1. **Authority freeze:** publish a governed authority map for RequirementGraph, ISR, Compiler IR, schemas, registries, adapters and active production routes. Reconcile schema drift and disposition every legacy representation based on executable consumers.
2. **Mandatory lineage boundary:** require every production route to bind the exact approved source snapshot and requirement graph to one versioned ISR revision and canonical typed IR. Emit deterministic mapping/semantic-diff reports; block unresolved MUST requirements and silent drops.
3. **Capability unification without forced target retirement:** define one versioned semantic capability vocabulary and explicit per-target adapters from it. Map existing Cap-C, Gen-C and behavioral declarations; unknown or unconsumed required semantics remain unsupported.
4. **Independent acceptance:** derive language-neutral positive, negative, boundary, concurrency, failure/retry and security oracles from approved requirements. Replace tautological tests and require independent verification of each claimed semantic feature.
5. **Native target evidence:** establish a staged matrix for each backend/frontend/mobile target: static analysis, native build, unit/integration, browser/device runtime, semantic acceptance, security and operational behavior. A missing toolchain is UNKNOWN/SKIPPED, not PASS.
6. **Frontend/backend integration:** make routes, forms, navigation, state, validation, accessibility, authorization, API operations and effects part of one source-bound application contract. Verify an actual UI action through API, authorization, effect and observable consequence.
7. **Evidence and publication:** standardize immutable evidence binding source, requirements, ISR, plan, backend digest, oracle, artifacts, toolchain and raw logs. Require quarantine, independent verification and authorized atomic promotion for every publication path.
8. **Broaden coverage deliberately:** add Angular browser evidence; correct Elixir capability declarations and implement real framework wiring; extend native mobile targets (including iOS/cross-platform) when their semantic adapters and execution environments are ready; broaden CBC-1 beyond Python/Rust. Preserve all existing targets and refuse unsupported work rather than stripping requirements.

### 15.8 Checkpoint 15 disposition and FS-00 conclusion

**Checkpoint 15: COMPLETE. FS-00: NOT CLOSED — integrated disposition PARTIAL / OPEN.**

All 15 planned audit checkpoints have now been completed and consolidated. This closes the planned checkpoint sequence, not the underlying engineering exit criteria. The architecture has substantial reusable components: source-bound requirement projections on selected paths, a content-addressed behavioral ISR, typed loss-aware lowering, fail-closed semantic capability checks, two materially different behavioral reference backends, independent narrow effect oracles, browser evidence for selected frontends, and a source-bound Android structural runner.

The decisive blockers remain: no single reconciled requirement/ISR authority; no universal mandatory source-to-IR lineage; multiple registries and compiler routes without one compulsory governance boundary; uneven semantic and native evidence across targets; incomplete independent requirement acceptance; and no universal quarantine/authorized atomic publication path.

**No target is retired. No capability, readiness or certification status is upgraded. No production implementation, test, workflow or benchmark is modified. Only this consolidated audit report is updated.**


## 16. Current-head evidence freshness delta — 2026-11-06

### 16.1 Scope and source identity

This is a targeted delta against the earlier architecture/source baseline `68696e2a07595fed98a19e24ee96c3e4e0e5bfeb`, not a repetition of Checkpoints 1–15. The PR head inspected for this delta is `c314049acca839358a46dd8371f3c51321e401`.

The source comparison identified four backend implementations changed after the architecture baseline: Ktor, Laravel, Rails and Spring Boot. Their corresponding generator tests, generated-application integration tests and dedicated GitHub Actions workflows were inspected. These changes improve the executable framework scaffold/runtime contract; they do not replace the shared RequirementGraph/ISR/CompilationPlan architecture or establish a new universal compiler authority.

### 16.2 Current CI evidence

All four dedicated workflows completed successfully on the current PR head:

| Target | Workflow run | Generator contract tests | Generated-project integration test | Evidence classification |
|---|---:|---|---|---|
| Ktor | `42156712935` | 3 passed | 1 passed; Gradle test/installDist; Docker image build, container launch and live `GET /health` probe are exercised when Docker is present; this run did not skip the test | Native build and narrow health-route runtime verified |
| Laravel | `42156712786` | 3 passed | 1 passed; Composer install, `php artisan test`, `artisan about`; Docker image build, container launch and live `GET /api/health` probe are exercised when Docker is present; this run did not skip the test | Native build and narrow health-route runtime verified |
| Rails | `42156712852` | 3 passed | 1 passed; Bundler install, `rails test`, `rails about`, Docker image build | Native build/test and image build verified; container startup/live HTTP runtime not exercised |
| Spring Boot | `42156712891` | 3 passed | 1 passed; Maven test, package, Docker image build; health assertion uses Spring MockMvc | Native build/test and image build verified; container startup/live HTTP runtime not exercised |

The test code conditionally skips its Docker path when Docker is absent. The Ktor and Laravel integration tests completed as passed rather than skipped, and their Docker branches include a launched container and a live HTTP probe. Rails and Spring Boot tests only build the Docker image; they do not start that image or probe its live HTTP endpoint. Spring Boot's health assertion is an in-process MockMvc test, not an external process/runtime probe.

The Android backend-test workflow on this same PR head, run `42156712886`, passed. Its Android cloud-build job was skipped by the workflow's manual-dispatch condition. Therefore no Android Gradle/APK/emulator execution is established by this PR-triggered run.

### 16.3 Capability and semantic boundary

The four backend manifests declare only BUILD, TEST, CONTAINERIZE, HEALTH_CHECK and DOCUMENTATION. The generated output and tests support a narrow framework/application-shell conclusion, not broad backend semantic conformance:

- **Ktor:** emits typed Kotlin data classes, a Ktor application and a `/health` route. It does not emit domain CRUD, persistence, authorization or business operations.
- **Laravel:** emits a bootable Laravel 12 application and health routes. Generated Eloquent model classes are structural shells; migrations, persistence semantics, CRUD, authentication, authorization and business operations are explicitly not implemented/certified.
- **Rails:** emits a bootable Rails 8 application and `GET /health`. Generated model classes are structural shells; migrations, schema, CRUD, authentication, authorization and business operations are explicitly not implemented/certified.
- **Spring Boot:** emits a Spring Boot application, health controller and Java domain classes. The current test proves the in-process health controller contract and native Maven build/package; it does not establish generated persistence, CRUD, authentication/authorization, transactions or requirement-derived business behavior.

The integration fixtures use a minimal `SystemModel` with a problem statement and placeholder graph reference. They do not exercise a rich requirement graph, complete ISR behavioral semantics, independent requirement oracles, adversarial authorization, persistence, transactions, event delivery, failure/retry semantics or cross-target parity. Passing these workflows must not be represented as production application certification.

### 16.4 Target-matrix delta

For the four targets, the earlier matrix wording “UNKNOWN pending target-specific evidence” is now superseded only for the narrow evidence layers stated here:

| Target | Current supported evidence state | Still UNKNOWN / NOT ESTABLISHED |
|---|---|---|
| Ktor | SOURCE_PRESENT; generator contract tests PASS; NATIVE_BUILD_VERIFIED; limited health-route RUNTIME_VERIFIED | Requirement-faithful behavior, persistence, auth/security, full API semantics, operational readiness, independent certification |
| Laravel | SOURCE_PRESENT; generator contract tests PASS; NATIVE_BUILD_VERIFIED; limited health-route RUNTIME_VERIFIED | Migrations/data integrity, persistence/transactions, CRUD, auth/security, business behavior, independent certification |
| Rails | SOURCE_PRESENT; generator contract tests PASS; NATIVE_BUILD_VERIFIED; container image build PASS | Container startup/live runtime, migrations/data integrity, persistence/transactions, CRUD, auth/security, business behavior, independent certification |
| Spring Boot | SOURCE_PRESENT; generator contract tests PASS; NATIVE_BUILD_VERIFIED; in-process MockMvc health test PASS; container image build PASS | Container startup/live runtime, persistence/transactions, CRUD, auth/security, business behavior, independent certification |

These are evidence-layer updates, not capability or certification promotions. The remaining backend acceptance criteria in Section 5 of `05-target-engineering-acceptance-criteria.md` continue to apply.

### 16.5 Architecture conclusion revalidation

The targeted source review does not invalidate the existing architecture conclusions:

1. These four ProjectCompiler backends consume the legacy-compatible `IntermediateSoftwareRepresentation.system_model()` payload and generate directly from `SystemModel`. Their inspected `compile()` paths do not establish mandatory traversal through `ISRRevision → CompilationPlan`.
2. Their dedicated CI workflows are target-specific validation, not a universal route gate. No evidence here shows that every production compiler entrypoint must pass the same canonical ISR binding, semantic capability gate, independent verifier and publication authority.
3. No change in this delta reconciles the multiple RequirementGraph/ISR representations, compiler families, registries or direct materialization paths identified in the earlier checkpoints.
4. The proposed architecture boundary/ADR remains proposed; this delta does not approve it or authorize architecture migration.

A non-blocking Python SyntaxWarning about an invalid escape sequence is emitted from `rails_backend.py` during generator tests. It did not fail these workflows and should be cleaned up in a separate code-maintenance change.

### 16.6 Integrated disposition

- The four backend scaffolds now have materially stronger, current-head native build/test evidence.
- Ktor and Laravel additionally have narrow live health-route evidence in the passing CI integration tests.
- Rails and Spring Boot have image-build evidence but still lack container-start/live HTTP verification in these workflows.
- No evidence here establishes durable persistence, complete domain/API semantics, security acceptance, independent requirement-oracle coverage, full-stack coherence or production readiness.
- The architecture conclusions remain PARTIAL / OPEN. FS-00 remains NOT CLOSED. No backend is retired; no capability, readiness or certification state is upgraded.
- PR #201 remains open, draft and unmerged. The Android cloud build remains NOT RUN by the PR-triggered workflow.

**Checkpoint disposition:** targeted evidence-freshness reconciliation COMPLETE for these four changed backends. This does not close FS-00 or approve FS-01, the proposed architecture ADR, benchmark decisions R1/R5/R6/R7, or PR #201.


## 17. Semantic capability preflight and invocation-order delta — 2026-11-06

### 17.1 Scope and inspected current-head paths

This targeted continuation inspected the current PR branch's capability/conformance implementation and its call ordering, including:

- `tiannara/application/compiler/selector.py`
- `tiannara/application/compiler/composition.py`
- `tiannara/application/compiler/executor.py`
- `tiannara/application/compiler/project_compiler.py`
- `tiannara/application/compiler/verification.py`
- `tiannara/application/compilation/backend_conformance.py`
- `tiannara/application/compilation/backend_capability_registry.py`
- `tiannara/application/compilation/integrity_gate.py`
- `tiannara/application/campaign/backend_matrix.py`
- Existing R2.10.7/R2.10.8 test and design references found by repository search.

This is a source-level audit. No tests were executed in this connector inspection, and no production code or certification state was changed.

### 17.2 Finding FS00-CAP-009 — ProjectCompiler selection is declaration-only and does not enforce semantic support at invocation (High)

**Observed path**

1. `composition.py:build_compiler_registry()` registers the 11 backend-service implementations alongside the frontend targets.
2. `selector.py:BackendSelector.rank/select()` calls `BackendCapabilityDeclaration.supports()` and ranks declarations using artifact kind and the required capability names.
3. `project_compiler.py:compile_intent()` derives compilation requirements, selects a declaration, then invokes `CompilationExecutor.execute()`.
4. `executor.py:execute()` obtains the selected backend and calls `backend.generate(system_model)` directly.
5. The executor does not call a target semantic-coverage preflight, does not establish that unsupported requested ISR elements are rejected, and does not require zero backend invocation/output when support is absent.
6. `project_compiler.py:_verify()` runs after generation. Its generic verifier is structural: required-file checks, Python syntax checks and dependency-direction checks; Go has a toolchain-free structural verifier. This is not a substitute for pre-generation semantic refusal or native execution.

**Impact**

The declaration-based selector can select a backend based on advertised capability names, but this route does not prove that every requested semantic is consumed. A successful generated bundle may therefore omit requested services, API operations, event/effect behavior or policies while still reaching post-generation structural verification.

This confirms and sharpens FS00-CAP-001, FS00-CAP-004 and FS00-CAP-005: the required fail-closed boundary is not demonstrated on this production ProjectCompiler route.

**Required evidence**

For every selected backend, derive the complete required semantic set from the bound ISR/SystemModel and compare it with an implementation-bound, evidence-backed support map before calling `generate()`. Unsupported, partially supported where full support is required, or unknown semantics must produce an explicit non-success disposition. A negative test must assert that the backend invocation count remains zero and no deliverable artifact is emitted or published.

### 17.3 Finding FS00-CAP-010 — Campaign's “before compiling” unsupported decision occurs after conformance has already invoked the backend (High)

**Observed path**

The campaign matrix documentation states that an all-unsupported case is disposed before compiling. The current call order in `MatrixHarness._run_case()` is:

1. Compute `required`, `coverage` and `unsupported`.
2. Call `self._evaluator.conform(adapter, isr, target)`.
3. Record the conformance report.
4. Only then test `if required <= frozenset(unsupported)` and return `EXPLICITLY_UNSUPPORTED`.
5. Otherwise call `adapter.compile(isr, target)` for the matrix case.

The evaluator's `conform()` calls `CompilationIntegrityGate.verify()`. That gate calls `backend.compile()` three times: primary compile, determinism twin and alternate-target independence probe. The adapter's `compile()` translates the semantic projection and invokes the real backend's `compile()` or `compile_system()`.

**Impact**

The matrix's terminal disposition may correctly say `EXPLICITLY_UNSUPPORTED`, and no matrix-case artifact is subsequently recorded for that disposition, but the backend has already been invoked three times during conformance. Therefore the statement that an all-unsupported case is never compiled is not true for this execution path. The post-conformance branch prevents the later matrix compile; it does not provide pre-invocation refusal.

This is distinct from the ProjectCompiler finding above: the matrix uses the separate seven-backend conformance registry and campaign, not the 11-service ProjectCompiler registry.

**Required evidence**

Move or introduce the required-semantics/unsupported decision ahead of any conformance call that invokes the backend. If conformance of a backend itself must exercise its declared unsupported surface, keep that as a separately named conformance experiment and do not describe it as a no-invocation refusal test. Add a counting backend test proving zero calls for an all-unsupported case in the campaign path.

### 17.4 Clarification — explicit UNSUPPORTED coverage is not itself a semantic PASS

The eight-gate integrity contract intentionally distinguishes silent omission from an explicit unsupported declaration. Gate D checks whether every expressed semantic identifier appears in the coverage list; an explicit `UNSUPPORTED` entry is therefore allowed to satisfy the coverage-presence gate. This is useful for honest reporting, but it must not be interpreted as proof that the backend implements that semantic.

The separate artifact verifier and campaign disposition must continue to distinguish:
- coverage declared;
- semantic supported;
- semantic partially supported;
- semantic explicitly unsupported;
- behavior independently verified.

A report with complete coverage metadata can be internally well-formed while correctly recording that some semantics are unsupported. It must not be promoted to a successful implementation for a request requiring those semantics.

### 17.5 Cross-family boundary

The repository contains at least two distinct capability/conformance mechanisms in the inspected paths:

- **ProjectCompiler family:** 11 backend-service targets plus frontend targets; selection declarations and `SystemModel` generation through `generate()`.
- **R2.10.7 conformance family:** seven registered real compilers (React, FastAPI, Postgres, Terraform, CI/CD, Pytest, Markdown) wrapped by `BackendConformanceAdapter` and evaluated against the 14-carrier/12-capability semantic vocabulary.

Evidence from the seven-backend conformance family does not establish preflight enforcement for the 11 ProjectCompiler backend-service targets. Likewise, target-specific CI evidence for Ktor/Laravel/Rails/Spring Boot does not prove the R2.10.7 adapter/campaign path is correct. These ledgers and execution routes must remain separate until a governed convergence is demonstrated.

### 17.6 Disposition and next work

- FS00-CAP-009: SOURCE-CONFIRMED; HIGH; remediation required before this ProjectCompiler route can claim semantic fail-closed enforcement.
- FS00-CAP-010: SOURCE-CONFIRMED; HIGH; campaign documentation/call-order mismatch requires a pre-invocation refusal test and corrected ordering or narrower wording.
- Existing FS00-CAP-001 through FS00-CAP-008 remain open; this delta does not close them.
- No backend is retired. No capability, readiness or certification state is upgraded. FS-00 remains NOT CLOSED.

**Next checkpoint:** trace the per-backend semantic projection/generation code for FastAPI, Go, Rust/Axum, NestJS, ASP.NET Core and Phoenix; identify the exact ISR fields consumed versus ignored/refused; then map negative tests to each route. Preserve the separate ProjectCompiler and R2.10.7 evidence families.


## 18. ProjectCompiler backend semantic-consumption delta — 2026-11-06

### 18.1 Scope and evidence boundary

Inspected the current PR-branch implementations and composition registration for:

- `tiannara/application/compiler/composition.py`
- `fastapi_hexagonal_backend.py`
- `go_hexagonal_backend.py`
- `rust_axum_backend.py`
- `nestjs_backend.py`
- `aspnet_core_backend.py`
- `phoenix_backend.py`

This checkpoint is a source-level consumption audit. It did not execute generated applications or tests. The conclusions below describe the code paths visible in these files; they are not runtime certification findings. The separate R2.10.7 seven-backend conformance registry is not used as evidence for these six ProjectCompiler targets.

### 18.2 Registration and input boundary

`composition.py:build_compiler_registry()` registers FastAPI, Go, Rust/Axum, NestJS, ASP.NET Core and Phoenix as separate `CompilerBackend` implementations. The default ProjectCompiler selection path uses these declarations; the declarations expose broad `BundleCapability` lists, not an implementation-bound map of individual ISR semantic identifiers.

The six implementations divide into two input-handling groups:

- **FastAPI and Go:** call `isr.system_model()`; when it returns no typed model, each has a legacy conversion path.
- **Rust/Axum, NestJS, ASP.NET Core and Phoenix:** require `isr.system_model()` to return a typed `SystemModel`, otherwise raise `ValueError`.

A typed-model-presence check is a schema/input precondition only. None of the four strict typed-model guards, as inspected, checks whether all requested semantics in that model are implemented by the target.

### 18.3 Per-backend consumption map

| Backend | Consumed input visible in generator | Explicitly narrowed or omitted surface in inspected implementation | Fail-closed boundary evidenced |
|---|---|---|---|
| FastAPI | Typed model's system name, data models/fields, services, capabilities, security authentication posture, and operational observability requirements. Legacy conversion maps legacy data models, services/responsibilities, service-derived capabilities, and authentication posture into a reduced typed model. | Legacy conversion creates a single general domain and synthesizes requirement graph identity from the ISR hash; legacy field types are best-effort mapped. Generated API routes/services are model-derived, but the inspected conversion does not preserve a full requirement graph, workflow/event/effect semantics or complete authorization/business policy model. The observability map explicitly marks business audit-event generation NOT_IMPLEMENTED and external trace export absent. | Legacy fallback is permissive/best-effort; no complete required-semantic preflight before `generate()` is evidenced. |
| Go | Typed model's system name and a selected primary data entity, including its field definitions, drive generated domain, repository, service, in-memory infrastructure and HTTP handler scaffolding. | `_primary_entity()` deliberately selects one entity; the generated service is therefore not evidence that every declared entity/service/capability is realized. Legacy conversion creates data models from legacy field names but maps their types to TEXT and does not carry the full typed services/security/operational policy surface. | No unsupported-semantic rejection or complete-model coverage check is evidenced before generation. |
| Rust/Axum | Typed model's system name and data models/fields drive Rust structs and type mapping. Optional fields become `Option<T>`; unsupported field types and field-name collisions raise errors. | The emitted application router is a fixed `/health` route; generated data structs are not wired to CRUD/API operations, persistence, authorization, or business workflows in the inspected source. | Rejects missing typed model and certain invalid field/type cases; does not reject a valid model whose requested business semantics are not implemented. |
| NestJS | Typed model's system name and data models/fields drive package naming and TypeScript interfaces. | `_module(model)` emits a fixed module containing only the health controller; the model argument is not used to derive controllers/services/routes. No persistence, domain operations, authorization or workflow realization is visible in this backend file. | Rejects missing typed model; no semantic coverage/refusal gate for a valid model is evidenced. |
| ASP.NET Core | Typed model's system name and data models/fields drive project naming and C# domain classes. | `Program.cs` emits only a fixed `/health` minimal API route. The test source's health assertion compares the literal string `"/health"` with itself; it does not exercise a generated HTTP endpoint. No persistence, API/domain operation, authorization or workflow realization is visible here. | Rejects missing typed model; no semantic coverage/refusal gate for a valid model is evidenced. |
| Phoenix | Typed model's system name and data models/fields drive project naming and Elixir type declarations. | `lib/generated_web.ex` emits a fixed Plug health route. The generated domain module contains typespec-like declarations, not persistence schemas, business operations, controllers or workflow execution. The test asserts a literal path equals itself rather than exercising a running endpoint. | Rejects missing typed model; no semantic coverage/refusal gate for a valid model is evidenced. |

The FastAPI backend has a materially broader generated scaffold than the other five inspected implementations, including application services, repositories, in-memory repositories, API schemas/routes, API-key configuration, observability and generated API tests. That breadth must not be conflated with complete semantic fidelity: the legacy conversion is lossy, generated persistence is in-memory, and the observability map itself declares specific limitations.

### 18.4 Finding FS00-CAP-011 — backend declarations are broader than demonstrated per-target semantic consumption (High)

**Evidence:** the composition root registers these six implementations using capability declarations based on `BundleCapability` lists (FastAPI's declaration lists all `BundleCapability` values; the other backends derive their declarations from their manifests). The inspected backend generators consume materially different subsets of `SystemModel`: Go selects one primary entity; Rust emits model structs plus a fixed health router; NestJS emits interfaces plus a fixed health-only module; ASP.NET Core emits domain classes plus a fixed health route; Phoenix emits type declarations plus a fixed health route. These files contain no target-specific full semantic coverage map that binds every required ISR semantic to generated behavior and evidence.

**Impact:** selector eligibility can be interpreted more broadly than the generator's demonstrated semantic realization. A generated scaffold may pass structural verification while requested entities, operations, persistence, policies, workflows or effects remain unrealized. This is a per-target manifestation of FS00-CAP-009, not a separate proof that every such request has already escaped in production.

**Required evidence/remediation:** define an implementation-bound semantic support declaration for each target; derive the required semantics from the same bound ISR/SystemModel; reject unsupported, partial-when-full-is-required, and unknown requirements before backend invocation. Add negative tests per backend that assert zero generator invocation and zero artifact materialization for unsupported requests. Positive tests must bind generated behavior to requirement-specific independent oracles rather than only checking file presence or type declarations.

### 18.5 Finding FS00-CAP-012 — typed-model acceptance is not semantic validation (High)

**Evidence:** Rust/Axum, NestJS, ASP.NET Core and Phoenix raise when `isr.system_model()` is absent. Once a typed model is present, their generation paths do not perform a general semantic completeness check. Their model consumers are limited to fields/type declarations and, in some cases, project naming; their application routes/modules remain fixed health scaffolds.

**Impact:** the guard prevents a missing or legacy-only payload from silently entering these backends, but a well-formed typed model containing unsupported business/API/persistence/security semantics is still accepted by the visible generator path. This is not a fail-closed semantic boundary.

**Required evidence/remediation:** preserve strict typed-model requirements where intentional, but add semantic preflight after binding and before `generate()`. Distinguish schema validity from target capability and behavior verification in the disposition ledger.

### 18.6 Negative-test and evidence status

This checkpoint inspected the backend implementations and composition root, not the complete backend test inventory. Therefore, it does not claim that no relevant negative tests exist anywhere in the repository. It does establish that the inspected generator paths do not themselves enforce the required semantic refusal. The next test-mapping pass must locate each backend's tests and determine whether they prove all of the following independently:

1. unsupported semantic is identified from the actual bound ISR;
2. generator/backend invocation count remains zero;
3. no output directory, bundle or publication artifact is produced;
4. partial support is not treated as full support;
5. the refusal is recorded as a non-success, auditable disposition.

A test that only checks missing typed model, invalid field type, generated file presence, or health response does not prove these properties.

### 18.7 Disposition and next work

- FS00-CAP-011: SOURCE-CONFIRMED; HIGH; declaration breadth is not bound to demonstrated per-target semantic consumption.
- FS00-CAP-012: SOURCE-CONFIRMED; HIGH; typed-model presence checks do not provide semantic fail-closed enforcement.
- FastAPI is comparatively broader, but legacy conversion and in-memory persistence constrain its demonstrated fidelity.
- Go's single-primary-entity path and the four typed-only health-scaffold paths require explicit semantic limits until expanded and independently verified.
- No backend is retired. No capability, readiness or certification state is upgraded. FS-00 remains NOT CLOSED.
- This checkpoint changes documentation only; no production source, tests, workflow, registry or certification state was modified.

**Next checkpoint:** locate and map the actual generator, integration, negative, and invocation-count tests for these six targets; then reconcile each target's declared `BundleCapability` list with the exact semantics its implementation consumes. Keep remediation separate from this read-only audit unless separately authorized.


## 19. Checkpoint 20 — backend test evidence, full-stack coherence and product capability — 2026-11-06

### 19.1 Scope and family separation

This checkpoint inspected current PR-branch test and implementation sources for the six ProjectCompiler targets, then traced the separate root behavioral compiler and full-stack design boundary:

- ProjectCompiler tests: `tests/test_go_hexagonal_backend.py`, `tests/test_r24_fastapi_runtime.py`, `tests/test_nestjs_backend.py`, `tests/test_aspnet_core_backend.py`, and the corresponding target test files where present.
- Root behavioral compiler: `compiler/core/lowering.py`, `compiler/core/plan.py`, `compiler/core/capabilities.py`, `compiler/backends/python_fastapi.py`, `compiler/backends/rust_axum.py`.
- Root behavioral tests: `tests/test_behavioral_backend_emission.py`, `tests/integration/test_generated_backend_behavior_builds.py).
- Full-stack source-bound design: `autonomous-api/app/engine/source_bound_full_stack.py`.
- Full-stack architectural acceptance and sequencing: `folder/prefull.md`.

This was a source/test-contract inspection through GitHub. Tests were not executed in this checkpoint. The ProjectCompiler targets and root behavioral compiler are distinct execution families, even where their backend names overlap. Evidence must not be transferred between them.

### 19.2 ProjectCompiler test evidence: six-target interpretation

The inspected tests have uneven strength:

| Target | Test evidence found | What it does prove | What it does not prove |
|---|---|---|---|
| FastAPI | Runtime-profile/harness tests in `test_r24_fastapi_runtime.py`; portions stub subprocess execution; optional real-Docker test | Build/test command composition and harness wiring; optional generated-bundle test path | Not complete semantic parity or full-stack product acceptance; stubbed subprocess results are not real runtime evidence |
| Go | `test_go_hexagonal_backend.py` source-shape and manifest/profile assertions; optional Docker Go test | Expected emitted files, module shape, struct tags, declared build/test profile; optional native Go compilation/test when Docker exists | Most tests explicitly do not run Go; no general requirement-to-behavior or unsupported-before-invocation proof |
| Rust/Axum (ProjectCompiler) | No matching `tests/test_rust_axum_backend.py` at the guessed path; separate root behavioral Rust tests exist | Root behavioral Rust tests are evidence for the separate root compiler only | They do not certify ProjectCompiler Rust/Axum |
| NestJS | `test_nestjs_backend.py` checks registration/profile and health-controller test source shape | Registry presence, independent profile and a narrow generated health-controller assertion | No requirement-derived business API, persistence, auth, workflow, full-stack integration or semantic refusal proof |
| ASP.NET Core | Target-specific test file exists and is narrow; source review identifies health-focused scaffolding | Limited registration/profile/scaffold contract | No evidence here of requirement-faithful domain/API operations, persistence or end-to-end runtime behavior |
| Phoenix | Target-specific test file exists and is narrow; source review identifies health-focused scaffolding | Limited registration/profile/scaffold contract | No evidence here of requirement-faithful domain/API operations, persistence or end-to-end runtime behavior |

No target-specific test inspected in this checkpoint establishes the complete negative-test tuple: actual ISR-derived unsupported semantic, zero backend invocations, zero output materialization, partial-support refusal, and auditable non-success disposition. This does not assert that no such test exists anywhere; it records that the inspected test surface does not establish it.

The optional Go Docker test is materially stronger than source-only assertions when it actually runs, but a conditional test definition is not evidence that a particular CI run executed it. The FastAPI runtime test file includes mocked subprocess composition tests; those must not be counted as generated application runtime proof.

### 19.3 Separate root behavioral compiler: real foundations

The root compiler has a substantially stronger semantic contract than the ProjectCompiler backend shells:

1. `compiler/core/lowering.py:isr_to_plan()` projects typed ISR node behavior and explicit graph relations into a technology-neutral `CompilationPlan`. It preserves typed data models, events, security policies, API operations, effects, effect bindings, consequences, invariants, frontend routes and interactions. It rejects unresolved effect/consequence bindings and ambiguous API-to-service bindings.
2. `compiler/core/capabilities.py:required_features()` derives required semantic features from the plan. `assert_plan_supported()` rejects requirements outside the selected backend's declared supported feature set.
3. Root `PythonFastAPIBackend.compile()` and `RustAxumBackend.compile()` call that semantic gate before emission.
4. The Python backend declares typed fields, decimal shape, expressions, business rules, state transitions, API contracts, authorization policies, effect policy/binding preservation, consequence preservation and executable effects. Its source describes generated CRUD routes, in-memory repositories, event handlers and fail-closed API-key authorization.
5. The root Rust backend declares typed fields, decimal shape, expressions, business rules, state transitions, and preservation of effect policies/bindings/consequences. It does not declare API contracts, authorization policies or effect execution as supported; those semantics should be rejected by the feature gate when required.

This is a meaningful reference implementation and a valid route for expanding ESAP's behavioral capabilities. It is not the same as the six ProjectCompiler backend-service implementations, and it is not proof that all ESAP entry points use this gate.

### 19.4 Runtime and oracle evidence boundary

`tests/test_behavioral_backend_emission.py` builds a small payroll-shaped ISR with:
- Employee identifier, base salary and allowances;
- a gross-pay expression (base salary plus allowances);
- a guarded draft-to-submitted state transition;
- a persistence relation between the payroll service and employee model.

The tests assert the required semantic feature set, exercise capability acceptance for the two root reference backends, inspect generated Python/Rust behavior methods and generated test source, and verify that a structural-only backend rejects the behavioral plan.

`tests/integration/test_generated_backend_behavior_builds.py` goes further for separately constructed backend plans:
- generated Python application installation and its generated test suite;
- generated Python authorization-policy runtime tests;
- generated Python executable-effect contract tests, including authorization, pre/postconditions and replay behavior;
- generated Rust `cargo test`.

These are valuable native generated-application tests. However, the inspected integration tests do not show that the exact payroll fixture from `test_behavioral_backend_emission.py` is installed and run through the generated payroll application. The payroll-specific tests in that file inspect emitted method/test source; they are not, by themselves, proof that a payroll application was executed end to end.

The root Rust capability declaration also intentionally does not claim API-contract, authorization-policy or effect-execution support. It is therefore not yet a parity-equivalent substitute for the Python reference backend across all payroll requirements.

### 19.5 Full-stack coherence: architectural design versus implemented route

`folder/prefull.md` states the correct acceptance criterion: validated technology-neutral ISR → deterministic Compiler IR lowering → complete full-stack application → verification/quarantine → immutable evidence → lineage from requirement to deployed instance. It explicitly sequences FS-00, FS-01 ISR↔IR contract, FS-02 orchestration, FS-03 backend/artifact contracts and FS-04 first vertical slice. It also says implementation must not begin before the FS-00 gate and ADR approval.

The source-bound full-stack subsystem has a `LoweredFullStackIR` with frontend, API, backend, effects and consequences. Its explicit mapping lowerer rejects unknown keys, requires explicit frontend/API/backend sections and provenance, validates required sections, and avoids inferring omitted architecture. This is a useful fail-closed design boundary.

But the existence of the design document and a mapping-to-IR function does not demonstrate the full acceptance criterion. The audited report still records:
- no approved universal Compiler IR boundary/ADR;
- no single mandatory orchestration authority across compiler families;
- no demonstrated production composition of frontend, API, backend, data, auth, infrastructure and deployment artifacts from one authoritative ISR/IR;
- no verified universal requirement → graph → ISR → IR → backend artifact → deployed instance lineage;
- no full-stack independent acceptance verdict for a real generated product.

The root behavioral `CompilationPlan` carries frontend route/interaction semantics, but the two inspected reference backend classes are backend emitters. That is not evidence of a complete, coordinated frontend compiler plus backend plus persistence/auth/deployment composition route. The separate source-bound full-stack IR path must not be silently equated with the root behavioral plan or ProjectCompiler's SystemModel route.

**Full-stack coherence disposition:** ARCHITECTURALLY SPECIFIED IN PART; IMPLEMENTATION/UNIVERSAL ROUTE NOT ESTABLISHED. This is consistent with the earlier FS-00 conclusion and does not authorize starting a new parallel full-stack architecture.

### 19.6 Can ESAP create the payroll system?

**Current evidence supports a narrow payroll behavior-generation experiment, not a complete payroll product.**

Demonstrated in source/tests:
- employee typed fields and decimal precision/scale;
- gross-pay arithmetic expression;
- a guarded payroll submission state transition;
- generation of corresponding Python/Rust behavior methods;
- Python and Rust backend capability checks for that limited feature set;
- broader Python generated-application runtime tests for CRUD, authorization and executable effects on other fixtures.

Not established for a complete payroll system:
- jurisdiction-specific tax and statutory contribution rules, rates, effective dates and versioned tables;
- employee lifecycle, contracts, pay groups, pay periods and multi-company/multi-country support;
- earnings, allowances, overtime, leave, benefits, deductions, garnishments and adjustments;
- tax/social-contribution calculation, rounding, caps, exemptions and year-to-date reconciliation;
- approval workflows, segregation of duties and payroll-period locking;
- durable transactional storage, migrations, concurrency controls and audit-grade change history;
- bank/payment-provider integration, idempotent disbursement, reconciliation and failure/reversal handling;
- payslip generation, statutory filings, accounting/GL exports and reporting;
- privacy, tenant isolation, access control, retention and jurisdictional compliance;
- independent golden payroll oracles covering boundary cases and multiple jurisdictions;
- full frontend-to-API-to-backend-to-database runtime, deployment and recovery tests.

The narrow fixture uses an in-memory/persistence-shaped model and two simple behaviors. It is a useful seed for a vertical slice, not a certified payroll implementation. Prior payroll parity work also remains constrained to in-memory FastAPI and Elixir implementations; durable storage and bank-transfer semantics were not established in that work. No evidence in this checkpoint changes that status.

### 19.7 Can ESAP create novel global software products?

The compiler's intended architecture is general enough to target many domains, but universal product capability is not demonstrated by a general-purpose design or by a handful of backend scaffolds.

For each proposed global product, ESAP must be able to preserve and implement its domain semantics—not just create a UI, CRUD API and database schema. It must model:
- authoritative domain entities, constraints, workflows and invariants;
- actor identities, permissions, trust boundaries and abuse cases;
- API/event contracts, consistency and transaction semantics;
- durable storage, migration, backup and recovery;
- integration protocols and external-system failure handling;
- localization, accessibility, jurisdiction and regulatory variations where applicable;
- scale, availability, observability, cost and operational controls;
- independent acceptance oracles, adversarial tests and runtime evidence.

A universal developer system should retain broad language/framework targets while honestly restricting each target to the semantic subset it can prove. It should not promise every product merely because a backend can emit a project shell.

### 19.8 New findings and integrated priorities

**FS00-FS-013 — behavioral reference compiler and ProjectCompiler are not shown to converge on one governed full-stack route (High).**

The repository has a stronger root behavioral pipeline (`ISRRevision → CompilationPlan → capability gate → Python/Rust emitter`) alongside ProjectCompiler's typed `SystemModel` route and the separate source-bound full-stack mapping/IR subsystem. Their schemas, registries, selection paths and evidence are not shown to converge through one mandatory orchestration and publication authority.

Required evidence: one approved ISR↔IR contract; one mandatory orchestrator; explicit adapters with loss reports; shared backend semantic contracts; coordinated frontend/API/backend/data/security/infrastructure lowering; common verification/publication gates; and end-to-end lineage.

**FS00-FS-014 — payroll capability is a narrow behavioral demonstration, not a complete payroll product (High).**

The payroll fixture demonstrates typed employee money fields, one gross-pay expression and one guarded state transition. Generated source assertions exist, but the inspected payroll-specific test does not execute that exact fixture as a complete payroll application. Full payroll workflows, jurisdictional rules, durable storage, payment, reconciliation, statutory outputs and independent domain oracles remain unestablished.

Required evidence: a technology-neutral payroll ISR with versioned jurisdictional rule packs; independent golden calculation oracles; durable transactional persistence; secure approvals; payment/reconciliation adapters; generated UI/API/backend/database; and native runtime, failure/recovery and cross-target parity tests.

**FS00-FS-015 — global-product capability has no domain-independent end-to-end acceptance evidence (High).**

The inspected repository does not establish that an arbitrary complex domain can be carried from validated requirements through coherent full-stack generation to independently verified deployment. This is an evidence gap, not a reason to narrow the system's ambition or retire target languages.

Required evidence: a repeatable vertical-slice protocol and multiple materially different reference products, each with complete requirement lineage, independent domain oracles, native builds, runtime behavior, security and operational acceptance.

### 19.9 Recommended order of work

1. Finish the FS-00 audit and reconcile the multiple compiler families, semantic authorities and artifact/publication routes. Do not create another parallel full-stack implementation.
2. Resolve and approve the architecture/IR decision through the required governance process; deferred decisions remain deferred until explicitly decided.
3. Define the shared ISR↔IR and orchestration contracts, including frontend, API, backend, data, auth, effects, events, infrastructure and deployment.
4. Build one coherent vertical slice using the root behavioral reference backends, with explicit adapters rather than hidden schema conversion.
5. Use payroll as the first substantial business-domain acceptance product: start with one clearly bounded jurisdiction and payroll cycle, then expand jurisdiction coverage only with versioned rules and independent oracles.
6. Select a second, materially different global problem domain to test whether the architecture generalizes beyond payroll.
7. Expand and certify each backend family incrementally against the same semantic conformance suite. Preserve all useful targets; unsupported features must fail closed rather than be silently omitted.

### 19.10 Disposition

- Checkpoint 20 source/test mapping: COMPLETE for the inspected files; no tests were executed in this checkpoint.
- FS00-FS-013, FS00-FS-014 and FS00-FS-015: SOURCE/DOCUMENTATION-CONFIRMED; HIGH; remain open.
- Root behavioral Python/Rust compiler: meaningful reference capability; not universal ESAP certification.
- Payroll: narrow behavioral proof only; complete payroll product capability NOT ESTABLISHED.
- Full-stack coherence: design foundations exist; one governed end-to-end full-stack route NOT ESTABLISHED.
- Global software generation: intended ambition retained; domain-independent product acceptance NOT ESTABLISHED.
- No backend retired; no capability/readiness/certification state upgraded; no production code, tests, workflows, registrations or approvals changed.
- FS-00 remains NOT CLOSED. PR #201 remains a draft and unmerged.

**Next checkpoint:** audit the actual frontend/backend/data/auth/infrastructure/deployment composition and lineage routes, then reconcile the source-bound full-stack subsystem with the root behavioral compiler and ProjectCompiler. The first implementation slice should be chosen only after the architecture boundary is approved; payroll is a strong candidate for the first substantial domain acceptance product, not a reason to bypass the FS-00 gates.


## 20. Checkpoint 21 — full-stack composition, candidate verification and lineage route

**Scope:** source-trace the certification campaign's actual ISR-to-candidate route, source-bound mapping and full-stack verification; compare it with the root behavioral compiler and ProjectCompiler; inspect the boundary between verification, deployment and provenance. Documentation-only audit. No tests executed in this checkpoint.

### 20.1 Three compiler families and their actual boundaries

The source trace confirms three distinct execution families:

1. **Root behavioral compiler:** `certification/campaign/plan_builder.py` builds a requirement graph, genesis ISR, genome, materialized candidate ISR and then calls `compiler.core.lowering.isr_to_plan()`. The resulting `compiler.core.plan.CompilationPlan` carries typed data models, events, security policies, API operations, effects, bindings, consequences, invariants, frontend routes and frontend interactions. `compiler.core.capabilities` derives required features and provides fail-closed backend support assertions. The root composition registry currently registers Python/FastAPI, Rust/Axum and Android structural backends.
2. **Source-bound full-stack verification subsystem:** `autonomous-api/app/engine/source_bound_full_stack.py` snapshots Campaign A `PlanArtifacts`, deterministically produces an explicit mapping from the source ISR, lowers that mapping to `LoweredFullStackIR`, validates requirement coverage/typed bindings/semantic obligations, and checks candidate/source/mapping hashes. It is invoked by the certification campaign as a verification path around the generated repository; it is not the same IR schema as `compiler.core.plan.CompilationPlan`.
3. **ProjectCompiler:** `tiannara/application/compiler/composition.py` registers a separate family of frontend and backend implementations. `ProjectCompiler.compile_intent()` converts intent to a typed `SystemModel`, derives selection requirements, selects from its own registry, and calls `CompilationExecutor.execute()`. The executor calls `backend.generate(system_model)`. This path does not call root `isr_to_plan()`, the root semantic capability gate, or the source-bound full-stack lowering in the inspected call chain.

The registries, input models, backend interfaces, selectors and verification contracts are distinct. The campaign's root compiler and source-bound verifier are connected to each other; the inspected ProjectCompiler route is not shown to be adapted into that same orchestration or evidence contract.

### 20.2 Positive source-bound evidence

The Campaign A route is more than an unused design seam:

- `plan_builder.py:build_artifacts_from_graph()` constructs the requirement graph, genesis ISR, genome, materialized candidate ISR, and `CompilationPlan` through `isr_to_plan()`; it returns these in `PlanArtifacts`.
- `CampaignRunner.run_trial()` accepts those authoritative artifacts. When explicit semantic-correspondence inputs are absent, it builds a canonical source snapshot using `source_snapshot_from_plan_artifacts()`, then calls `produce_architecture_mapping()`.
- The mapping producer extracts explicit ISR node/edge types (including requirements, data models, services, APIs, events, policies, infrastructure targets, frontend routes/interactions, effects, invariants and consequences). It refuses to invent missing semantics and returns canonical mapping only when its declared conditions are met.
- The runner binds the produced mapping to the exact generated repository hash. The semantic-correspondence verifier recomputes the candidate digest, validates requirement coverage and typed target bindings, re-runs deterministic source-to-ISR mapping and compares the submitted mapping, then lowers and checks the full-stack IR.
- The runner only derives the five canonical IR inputs after semantic correspondence passes. The candidate-bound full-stack verifier receives and echoes the candidate hash; missing inputs, missing verifier methods, mismatches and failed findings are non-passing.
- The source-bound helper `lower_source_bound_candidate()` separately checks source hash, candidate hash, mapping hash, source refs, requirement coverage, typed bindings and explicit mapping lowering. Its readiness predicate does not itself authorize certification or claim runtime enforcement.

This is a substantive source-bound verification foundation. It should be preserved and integrated, not discarded or treated as proof that every compiler entry point uses it.

### 20.3 FS00-FS-016 — full-stack verification is recorded after deployment/runtime stages in CampaignRunner (High)

In `certification/campaign/runner.py:run_trial()`, the actual order is:

1. `backend.compile(plan)` is called before the candidate workspace and verification stages.
2. Generated files are materialized into a temporary candidate directory.
3. Backend conformance and build/test stages are evaluated.
4. The deployer may deploy the candidate; the runtime prober may exercise the deployed container; the destroyer may clean it up.
5. The runner writes the independent-verification plan, builds source-bound correspondence inputs, performs full-stack IR derivation/verification, and records the combined result as `TrialStage.VERIFY`.
6. The trial verdict is composed from the stage results.

Thus the source-bound/full-stack checks are meaningful certification gates for the final verdict, but they are not pre-build or pre-deployment authorization gates in this route. A candidate can reach deployment/runtime before the full-stack/source-correspondence verdict is known. This is especially important where the desired production policy requires semantic proof before publication or deployment.

**Required:** separate mandatory gates by lifecycle stage. At minimum: source/IR and backend semantic preflight before generation; artifact integrity and semantic verification before publication; deployment authorization before deployment; post-deployment independent runtime acceptance before production promotion. Tests must prove that failed/missing upstream gates cause zero calls to downstream side-effecting adapters.

### 20.4 FS00-FS-017 — current source-bound full-stack IR is not the complete deployment/infrastructure artifact contract (High)

The explicit `LoweredFullStackIR` currently contains frontend, API, backend, effects and consequences. The mapping's required top-level layers are those five; the canonical lowerer rejects unknown keys and requires explicit provenance. The mapping producer can inspect infrastructure-target ISR nodes, but the five-layer IR object does not expose a corresponding infrastructure/deployment/CI/CD/operations artifact contract.

Therefore, the subsystem proves a bounded five-layer coherence contract, not the entire `folder/prefull.md` acceptance surface. The inspected runner does not show the same canonical IR lowering and independent source-to-deployed-instance lineage for infrastructure configuration, deployment manifests, CI/CD, observability, secrets/configuration, runtime environment and deployed instance identity.

**Required:** extend or formally compose the canonical contract for infrastructure, packaging, deployment, runtime configuration, operational controls and deployed-instance identity. Each layer needs typed source bindings, implementation-bound capability declarations, artifact hashes and independently checked lineage. Do not infer these from an infrastructure target name or a successful Docker stage.

### 20.5 FS00-FS-018 — root campaign and ProjectCompiler do not share a mandatory orchestration/publication authority (High)

The campaign root route uses `ISRRevision → isr_to_plan() → root BackendRegistry → CompilerBackend.compile(plan) → GeneratedRepository`, followed by campaign conformance and evidence stages. ProjectCompiler uses `IntentCompiler → SystemModel → BackendCapabilityDeclaration/CompilerRegistry → CompilationExecutor.generate(system_model) → CompilationResult → BundleVerifier`.

The ProjectCompiler executor invokes generation before its bundle verification. Its verifier checks documentation, required files, selected syntax and dependency direction; it is not the root behavioral semantic gate or the candidate-bound full-stack verifier. The ProjectCompiler report is not shown to produce the campaign's source-bound requirement-to-candidate correspondence record. Conversely, the campaign's root backend registry does not include the ProjectCompiler's full frontend/backend family.

The repository therefore contains meaningful but separate compiler capabilities, not one demonstrated mandatory route that all user-facing compilation entry points must traverse. This confirms and sharpens FS00-FS-013.

**Required:** after architecture approval, designate one authoritative orchestration boundary and define one-way, loss-reporting adapters for each retained compiler family. All production routes must bind the same immutable ISR revision and canonical IR digest, run the same required-semantic derivation, enforce backend-specific support before invocation, and pass through common verification/publication/deployment authorization. No backend family should be retired merely to simplify integration.

### 20.6 Provenance and lineage: what is established versus missing

Established in the campaign route:
- `PlanArtifacts` includes plan, ISR revision, genome, requirement graph and their declared hashes.
- `ProvenanceBundle.emit()` records corpus, requirement graph, genome, ISR revision/content, plan, backend identity/version and application repository hash, and emits source snapshots plus evidence manifest.
- `ProvenanceBundle.verify_bundle()` recomputes the application repository hash and checks ISR, genome and requirement-graph hash relationships.
- Candidate-bound full-stack and semantic-correspondence checks bind verification to the generated repository content hash.

Not established by this evidence:
- a universal, immutable lineage record spanning every frontend/backend/database/auth/infrastructure/deployment artifact from one canonical IR;
- a verified mapping from the generated repository hash to a deployed artifact/image digest and a stable deployed-instance identity in the same end-to-end lineage;
- one common publication authority that rejects unverified candidates across Campaign A, ProjectCompiler and other compiler routes;
- atomic/immutable publication semantics and promotion/rollback controls for all routes.

The provenance bundle is valuable evidence, but its own module states it is a record rather than the certification authority. It must not be mistaken for a universal publication gate.

### 20.7 Test evidence and limitations

Inspected source/test contracts:
- `tests/cbc1/test_source_bound_full_stack_projection.py`: missing/incomplete mapping refusal, known-source-ref checks, digest sensitivity, snapshot construction, explicit mapping lowering and unknown-field rejection.
- `tests/certification/test_campaign_semantic_input_wiring.py` and `tests/certification/test_architecture_mapping_producer.py`: campaign source snapshot/mapping producer wiring and related mapping behavior.
- `certification/campaign/runner.py`: candidate-bound verifier invocation and stage ordering.
- `certification/campaign/plan_builder.py`: requirement graph/ISR/genome/plan production.
- `compiler/core/plan.py`, `lowering.py`, `capabilities.py`, `compiler/composition.py`: root behavioral IR, lowering, semantic feature gate and registry.
- `tiannara/application/compiler/composition.py`, `project_compiler.py`, `executor.py`, `verification.py`, `writer.py`: separate ProjectCompiler route and verification/materialization behavior.
- `certification/provenance/bundle.py`: campaign provenance and hash checks.

These files were inspected at the PR branch. Tests were not run in this checkpoint; test definitions are not represented as executed evidence. The inspection does not claim that no other publisher/deployment integration exists elsewhere in the repository; the finding is that the audited routes do not establish one shared mandatory authority or complete lineage.

### 20.8 Updated integrated disposition

- **FS00-FS-016 — verification occurs after deployment/runtime in CampaignRunner:** SOURCE-CONFIRMED; HIGH; open.
- **FS00-FS-017 — five-layer full-stack IR omits explicit infrastructure/deployment artifact contract:** SOURCE-CONFIRMED; HIGH; open.
- **FS00-FS-018 — root campaign and ProjectCompiler are separate orchestration/verification routes:** SOURCE-CONFIRMED; HIGH; open.
- Positive source-bound mapping, candidate binding and campaign provenance foundations: CONFIRMED as bounded capabilities; not universal route/certification proof.
- Root behavioral compiler: remains the strongest inspected technology-neutral semantic backend route, but not the universal orchestration authority.
- ProjectCompiler: remains a separate typed-SystemModel generator family; its backend declarations and structural bundle verifier do not substitute for source-bound semantic verification.
- Full-stack coherence: partial five-layer source-bound verification exists in Campaign A; pre-deployment gate, full infrastructure/deployment contract and universal entry-point enforcement remain NOT ESTABLISHED.
- Payroll/global product capability conclusions from Checkpoint 20 are unchanged.
- No production code, tests, workflows, backend registrations, certification states or approvals changed. No tests executed. No backend retired.
- FS-00 remains NOT CLOSED; PR #201 remains open, draft and unmerged.

**Next checkpoint:** trace every publication/deployment adapter and production entry point (including CLI/API routes and any repository publisher) to determine whether any common immutable promotion gate exists outside CampaignRunner. Then complete the route matrix: entry point → ISR/IR authority → backend registry → semantic preflight → generation → verification → publication → deployment → runtime identity/evidence. Keep this audit documentation-only until FS-00 and the architecture decision are formally approved.
