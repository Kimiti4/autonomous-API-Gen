# FS-00 Checkpoint 7 — Requirement-oracle independence and semantic-preservation audit

**Audit date:** 2026-11-05  
**Audited source revision:** `99df9f35086cc8c4b58bb83e1520963fbb2734ed`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Scope:** Read-only source and test inspection. No production code, compiler behavior, tests, or certification state changed.

## 1. Purpose and decision rule

This checkpoint asks whether acceptance evidence is independently derived from authoritative requirements/ISR, rather than merely repeating assumptions embedded in the generator. It also traces whether semantic obligations survive representation, lowering, backend generation, and runtime verification.

Labels used here:

- **PRESENT** — source shows an explicit carrier or meaningful test for the stated concern.
- **PARTIAL** — some semantics or evidence exist, but important dimensions are missing or not established.
- **ABSENT** — the inspected path has no implementation/evidence for the concern.
- **UNKNOWN** — the available source/test inspection cannot establish the behavior.
- These labels describe inspected artifacts, not universal capability. A test file existing is not proof it ran on this revision.

No backend or compiler family receives certification from this audit.

## 2. Executive findings

1. **The repository has more than one semantic representation path.** The typed `SystemModel` under `tiannara/domain/models/system_model.py` and the behavioral graph/revision path under `isr/core/behavior.py` and `compiler/core/lowering.py` are not the same contract. The latter has richer typed behavioral carriers and explicit fail-closed capability checks; this must not be treated as proof that every SystemModel compiler family consumes or preserves those semantics.
2. **A genuine independent-oracle pattern exists for a narrow behavioral path.** `tests/support/effect_contract_scenario.py` is authored separately from the emitter and copied into generated Python output by `tests/integration/test_generated_backend_behavior_builds.py`. It tests authorization denial, no execution/commit on denial, pre/postconditions, replay, concurrent same-key execution, and missing idempotency keys. This is materially stronger than generator-authored smoke tests.
3. **The stronger behavioral runtime evidence is narrow.** The integration file exercises the separate `PythonFastAPIBackend` and `RustAxumBackend` family. The effect scenario is run against generated Python; Rust is tested with `cargo test` in a different test. It does not certify the 11 ProjectCompiler backend services, frontend targets, Gen-A/Gen-C, Android implementations, or all language/framework combinations.
4. **Several ProjectCompiler backend tests are tautological or health-only.** Laravel's generated test is `assertTrue(true)`; Phoenix, ASP.NET Core, and Ktor compare `/health` with itself. Rails makes a real request but only checks success. These tests do not establish business behavior or independently verify ISR requirements.
5. **The typed SystemModel is richer than many ProjectCompiler generators consume.** It carries APIs/operations, events, field enums/references, invariants, security posture, deployment, testing and operational policies. However, the inspected API operation has only name, description, command/query and idempotent fields; there are no typed request/response schemas or explicit error contract in that model. Invariants are free-text strings. Event delivery/ordering metadata is represented, but no general evidence of emitted event semantics or delivery guarantees was found in this checkpoint.
6. **Behavioral ISR lowering is intentionally loss-aware, but lowering is not implementation.** `isr_to_plan` carries typed behavior for data models, events, policies, APIs, effects, invariants, consequences and frontend interactions/routes. `required_features` and `assert_plan_supported` reject unsupported semantic obligations before compilation. Yet the Rust reference backend advertises a narrower feature set than Python and does not advertise API contracts, authorization enforcement, or executable effect execution. This is a correct restriction, not evidence of universal parity.
7. **Independent-oracle coverage remains incomplete.** Tests of model validation, projection, capability selection, and emitted source often assert that fields, method names, or generated test names exist. Those are useful unit/conformance checks but are not independent runtime oracles for every requirement. A requirement-to-oracle registry with mandatory positive and negative cases was not established across all compiler families by the inspected evidence.

## 3. Semantic carriers and preservation boundary

### 3.1 Typed SystemModel path

At the audited revision, `SystemModel` contains:

- Business capabilities with traced requirement IDs.
- Domains, services and components.
- APIs with operations (`COMMAND`/`QUERY`, idempotent flag).
- Events with producer/consumer IDs, payload model, delivery semantics and ordering.
- Data models with typed fields, enumeration values, reference targets, free-text invariants and consistency posture.
- Security posture, infrastructure/deployment, documentation/testing policies and operational policies/SLOs.

The envelope `IntermediateSoftwareRepresentation.from_system_model` checks technology coupling and stores the canonical typed payload. This establishes a typed source carrier and deterministic payload boundary, not downstream preservation.

**Gaps in this path:**

- `ApiOperation` does not define typed request/response fields, error variants, authorization binding, transaction boundary, retry contract, or effect binding.
- `DataModelSpec.invariants` are strings, not executable expression ASTs with field references and independently testable expected outcomes.
- `SecurityModel` expresses broad postures (e.g. RBAC/ABAC) but not a complete role/action/resource/condition matrix in the inspected SystemModel types.
- `EventSpec` declares delivery and ordering expectations, but a declaration alone does not establish a broker, durable outbox/inbox, deduplication, ordering enforcement, replay or dead-letter behavior.
- Operational policies declare SLOs, observability requirements, backups and incident response; their presence is not evidence of generated enforcement or verified operational behavior.

### 3.2 Behavioral ISR graph → CompilationPlan path

The separate `isr_to_plan` lowering function preserves typed behavioral payloads and relationships for services, data models, events, security policies, APIs, effects, invariants, consequences and frontend routes/interactions. It rejects ambiguous API-to-service exposure and unresolved effect/consequence links rather than silently guessing.

The semantic feature gate distinguishes preservation from execution. In particular, effect binding/policy/consequence preservation are not equated with executing side effects. Backend capability declarations are checked before generation.

This is a stronger architectural pattern for unsupported semantics, but the source audit does not establish that the typed SystemModel pipeline is normalized into this same graph/plan contract or that every compiler route uses it. The existence of two richer-but-different paths is itself an integration and authority question for a later checkpoint.

## 4. Requirement-to-oracle matrix

| Concern | Typed source carrier | Independent or runtime evidence inspected | Status |
|---|---|---|---|
| Requirement provenance | SystemModel requirements graph ID/hash; behavioral ISR revision provenance/hash | Hash/revision validation and requirement references exist; no universal mandatory oracle binding across all backends | PARTIAL |
| Typed fields and decimal shape | Field types, enum values, references; behavioral typed-field AST with precision/scale/constraints | Behavioral contract and emission tests; generated Python/Rust runtime path exists | PARTIAL |
| Business rules and expressions | Behavioral ISR expression AST, rule IDs, field refs | Projection/emission tests and Python effect scenario; not all targets | PARTIAL |
| State transitions | Typed transitions and optional guards in behavioral ISR | Guard/source-state tests exist; target-wide runtime coverage not established | PARTIAL |
| API request/response/error semantics | SystemModel API name/description/command-query/idempotent; behavioral API method/path/request/response/auth fields | Python behavioral route tests and capability checks; broad backend parity not established | PARTIAL |
| Authorization | SystemModel broad security posture; behavioral role/action/resource/condition policies | Independent Python runtime negative tests verify denied role and no mutation; Rust does not declare equivalent authorization capability | PARTIAL |
| Effects and idempotency | Behavioral effect contracts, bindings, consequence links, idempotency metadata | Independent Python runtime scenario covers allow/deny, pre/postcondition, replay, concurrency, missing key | PRESENT for that Python scenario only; PARTIAL overall |
| Persistence and atomicity | Data model consistency/invariants; effect failure/rollback declarations | Inspected generators include in-memory repositories; scenario checks in-memory ledger behavior, not durable storage or cross-process atomicity | PARTIAL |
| Events and delivery | SystemModel event producer/consumer, delivery and ordering; behavioral typed events | Source carriers and event validation/emission tests exist; no general durable delivery/order/replay runtime oracle across targets established | PARTIAL |
| Frontend routes/interactions | Behavioral frontend route/interaction carriers; SystemModel lacks a comparable first-class interaction state model | Frontend tests/build/E2E workflows exist in separate paths; not requirement-oracle parity for all targets | PARTIAL |
| Invariants | SystemModel free-text invariants; behavioral expression-based invariant nodes | Behavioral contract and emission tests; no broad independent mutation/property oracle for all backend outputs | PARTIAL |
| Failure/retry/idempotency | Behavioral effect contract; some delivery metadata | Python scenario checks pre/postcondition failures and retry; no universal failure taxonomy or cross-backend runtime evidence | PARTIAL |
| Security/data protection operations | SystemModel encryption, secrets, audit posture | Declarations and backend-specific auth tests; encryption-at-rest/in-transit, secret lifecycle and audit event behavior not independently established across targets | UNKNOWN / PARTIAL |
| SLO/operability | SLOs, observability, backup/DR, incident policy | Mostly declaration/generator artifact evidence in inspected paths; no end-to-end operational oracle per target | PARTIAL |

## 5. Generated test quality findings

### 5.1 ProjectCompiler backend service family

At the audited revision, these concrete generated tests were inspected:

| Backend | Generated test behavior | Assessment |
|---|---|---|
| Laravel | `assertTrue(true)` | Tautological; no application behavior checked |
| Phoenix | Compares literal `"/health"` with itself | Tautological; no route invocation |
| ASP.NET Core | Compares literal `"/health"` with itself | Tautological; no application behavior |
| Ktor | Compares literal `"/health"` with itself | Tautological; no application behavior |
| Rails | Requests `/health`, checks success | Real route-level smoke only |
| FastAPI hexagonal | Health/readiness plus API-key CRUD/auth checks for the first model | Useful smoke/CRUD evidence, not complete requirement oracle |
| NestJS | Controller test checks generated health payload | Health-focused; business contract coverage not shown |
| Express | Generated HTTP app tests exist | Better test shape; full ISR operation/policy coverage not established |
| Go/Rust ProjectCompiler generators | Separate backend tests and static/runtime checks exist | Uneven; not equivalent to the separate behavioral RustAxum reference path |

A generated test may be useful even when not independent. The issue is treating a test that repeats a hard-coded generator constant as evidence that the generated product satisfies an external requirement.

### 5.2 Separate behavioral reference backend family

The file `tests/integration/test_generated_backend_behavior_builds.py` writes generated projects to temporary directories, installs Python dependencies and executes pytest; it separately runs `cargo test` for generated Rust.

The strongest independent oracle is `tests/support/effect_contract_scenario.py`. It is explicitly authored outside the emitter and copied into generated Python output. Its assertions inspect externally observable effects and non-effects, not source strings:

- authorized execution commits exactly once;
- replay returns the recorded result without re-executing;
- concurrent same-key calls execute once;
- unauthorized roles are rejected without execution or commit;
- precondition failure prevents execution/commit;
- postcondition failure prevents commit and permits retry;
- missing principal/context/idempotency key is rejected.

This is a meaningful positive/negative behavioral oracle. Its limitations are equally important: it uses an in-memory ledger, is scoped to the Python generated package and a particular executable-effect contract, and does not establish durable cross-process semantics or equivalent behavior in other language backends.

### 5.3 Unit tests that are not independent product oracles

The inspected behavioral tests validate schema rejection, typed projection, feature derivation, and generated-source structure. For example, tests asserting generated source contains `evaluate_rule`, `apply_transition`, or a test function name prove expected symbols were emitted; they do not by themselves prove that arbitrary business rules work correctly at runtime.

These tests remain useful and should be retained. Their evidence class must be named accurately: schema validation, projection preservation, static emission, native build, runtime behavior, or independent acceptance oracle.

## 6. Cross-target semantic parity

The behavioral capability gate provides an explicit asymmetry:

- PythonFastAPIBackend advertises typed fields, decimal shape, expressions, business rules, state transitions, API contracts, authorization policies and executable effect execution, plus selected preservation features.
- RustAxumBackend advertises typed fields, decimal shape, expressions, business rules and state transitions, plus effect-policy/binding/consequence preservation. It does **not** advertise API contracts, authorization enforcement or executable effect execution in the inspected capability set.

The correct outcome for a Rust plan requiring unsupported features is refusal before generation, not a claim of parity and not retirement of the Rust target. Backend capability should be promoted only after the corresponding independent runtime oracles and evidence are available.

For the ProjectCompiler family, the prior Checkpoint 4 matrix already found material losses: most generators do not project arbitrary API operations; several reduce models to shells; field types/constraints/enum/reference semantics are not consistently preserved; and business invariants, security, events and persistence are not generally derived into executable behavior. Checkpoint 7 adds that their generated tests frequently do not detect those losses.

For frontend compilers, generated component/render/build/E2E tests are evidence of frontend-specific execution, but a rendered heading or interaction smoke does not independently prove requirement-to-screen completeness, authorization-sensitive navigation, loading/empty/error states, accessibility, or backend contract integration. The inspected SystemModel path lacks a first-class frontend interaction/state-transition model equivalent to the behavioral graph carriers.

## 7. Findings register

| ID | Severity | Finding | Required disposition |
|---|---|---|---|
| FS00-ORC-001 | Critical | Tautological generated tests exist in Laravel, Phoenix, ASP.NET Core and Ktor. | Replace with runtime assertions against actual generated application behavior; do not count tautologies as verification. |
| FS00-ORC-002 | Critical | SystemModel API operations lack complete typed request/response/error and authorization/effect contracts. | Define or bind a complete technology-neutral API operation contract; fail closed when required semantics are absent. |
| FS00-ORC-003 | High | Free-text invariants cannot be reliably compiled into executable predicates or independent oracles. | Use typed expression/invariant carriers with requirement IDs, field references, severity and test vectors. |
| FS00-ORC-004 | High | Broad security posture is not a role/action/resource/condition policy matrix. | Carry explicit policies and negative cases to every protected operation; reject unsupported policy forms. |
| FS00-ORC-005 | High | Event delivery/ordering declarations are not backed by general runtime guarantees. | Define publication/consumption, durability, deduplication, ordering, replay and dead-letter acceptance cases. |
| FS00-ORC-006 | High | Independent executable-effect oracle exists for a narrow Python reference path only. | Generalize the language-neutral oracle suite and require each backend to pass it before capability promotion. |
| FS00-ORC-007 | High | Backend semantic capability sets differ materially; Rust correctly refuses several API/security/effect obligations. | Preserve targets; certify capability subsets independently and refuse unsupported plans before generation. |
| FS00-ORC-008 | High | Test evidence classes are not uniformly distinguished in compiler qualification. | Separate schema/projection/static/build/runtime/independent-oracle evidence in manifests and certification decisions. |
| FS00-ORC-009 | High | Frontend behavioral acceptance is not fully requirement-derived; SystemModel lacks a complete UI interaction/state contract. | Add technology-neutral screens, states, transitions, authorization, validation, and error/loading/empty-state semantics or block qualification. |
| FS00-ORC-010 | Medium | Some source tests verify generated symbols or test-name output rather than behavior. | Keep as emission tests, but do not treat as independent runtime acceptance evidence. |
| FS00-ORC-011 | High | Multiple semantic representation paths exist; use of the richer behavioral ISR path is not established across all compiler families. | Trace authority and adapters between requirement graph, typed SystemModel, behavioral ISR, CompilationPlan and every production entry point. |

## 8. Required remediation sequence

1. **Do not retire backends.** Retain each target and its useful language/framework capability; restrict only the unproven semantic subset.
2. Define one authoritative requirement-to-oracle contract, with stable requirement IDs, semantic feature IDs, positive and negative cases, and expected externally observable outcomes.
3. Establish a typed API contract: operation ID, method/path, request/response schemas, validation, error envelope, authorization policy, idempotency, effects and atomicity.
4. Replace free-text executable invariants with bounded typed expressions and explicit invariant-to-test-vector links.
5. Establish event semantics and acceptance oracles for durability, ordering, deduplication, replay and failure handling.
6. Make generated test suites consume independent oracle packages/fixtures, not emitter-derived expected values. Keep generator snapshot tests as a separate evidence class.
7. Run the same language-neutral behavioral contract against every backend that claims the corresponding feature. Backend-specific adapters may differ; expected semantics must not.
8. Require frontend acceptance tests to be driven by requirement-linked interaction models, including positive/negative authorization, validation, navigation, loading, empty and error states.
9. Bind each evidence record to source revision, backend version/digest, ISR/plan hash, oracle version/hash, artifact manifest, native toolchain, logs and runtime result.
10. Keep UNKNOWN as UNKNOWN. Missing toolchain, skipped workflow, static-only pass, or unexecuted test must never become a behavioral PASS.

## 9. Audit boundary and conclusion

This checkpoint is documentation-only. No code or tests were changed or run, and no compiler capability or certification status was upgraded.

**Conclusion:** ESAP has the beginnings of the right model—typed behavioral semantics, loss-aware lowering, fail-closed backend capability gates, and an independently authored executable-effect oracle. That is not yet a universal requirement-to-oracle system. The current evidence is fragmented across multiple ISR/compiler families, with meaningful behavioral execution concentrated in a narrow Python/Rust reference path and several ProjectCompiler targets still carrying tautological or health-only generated tests.

**Next checkpoint:** FS-00 Checkpoint 8 — authoritative semantic contract and end-to-end requirement lineage. Trace a single requirement from source/requirement graph through every ISR representation, projection, backend selection, generated artifact, independent oracle, runtime result and evidence ledger. Identify duplicated authorities, unbound transformations, and points where requirements can disappear without a blocking diagnostic.
