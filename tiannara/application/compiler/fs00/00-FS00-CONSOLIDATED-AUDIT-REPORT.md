# FS-00 — Consolidated Compiler and Semantic-Lineage Audit Report

**Version:** 1.0 | **Date:** 2026-11-05  
**Repository:** `Kimiti4/autonomous-API-Gen`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Audited head:** `c3ef3855986713806e26a88fda2fb7f373ec277c`  
**PR:** #201, open draft, unmerged; base `remediation/w12-executable-effect-contract`  
**Boundary:** Documentation/source audit only. No production code, tests, workflows, registrations or certification records changed.

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
