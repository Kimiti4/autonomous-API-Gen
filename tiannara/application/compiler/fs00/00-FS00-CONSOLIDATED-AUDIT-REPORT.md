# FS-00 — Consolidated Compiler and Semantic-Lineage Audit Report

**Version:** 1.0 | **Date:** 2026-11-05  
**Repository:** `Kimiti4/autonomous-API-Gen`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Audited head:** `5090cc837beb54977bcb9e45b472cfa4b7340669`  
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
