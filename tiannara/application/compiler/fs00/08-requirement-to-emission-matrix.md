# FS-00 — Requirement-to-Emission Matrix (Checkpoint 4)

**Date:** 2026-11-05  
**Inspected revision:** `e7ce89fb61bcf11b3571fb32568a962166f665e4`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Scope:** read-only source inspection of the canonical `SystemModel` and all 11 ProjectCompiler backend-service generators. The ProjectCompiler Android frontend target and separate root Android structural backend remain separate audit subjects. No production code, tests, schemas, registries, workflows or capability declarations were modified.

## 1. Executive result

The canonical typed ISR `SystemModel` has 14 top-level semantic sections: identity/problem, requirements reference, business capabilities, domains, services, components, APIs, events, data models, security, infrastructure, deployment, documentation, testing, operational policies and extensions.

The 11 ProjectCompiler backend-service generators do not consume that contract uniformly:

- FastAPI is the only inspected backend with broad generated service structure: models, repositories, application services, memory repositories, API routes, API schemas, authentication-related dependencies, observability, health/readiness, tests, CI and container files. This is materially more complete than the other targets, but not proof of complete ISR preservation.
- Go emits a service skeleton around exactly one selected data model: the first model in the list, or a synthetic Item when none exists. It does not iterate the full model collection for service behavior.
- Rust/Axum, NestJS, Spring Boot, ASP.NET Core, Express, Ktor, Phoenix, Laravel and Rails predominantly project data-model shapes and emit fixed health-oriented application templates. Their inspected generators do not derive business operations/routes from the ISR API and service declarations.
- Security, persistence, event delivery, deployment strategy, invariants, testing policy and operational policies are not generally enforced by these generators. Some targets emit infrastructure files or health endpoints; these are not semantic implementations of the corresponding ISR requirements.

**Conclusion:** the inspected backend family is not yet a demonstrated universal ISR-to-application compiler. No target receives a universal semantic-preservation certification from this checkpoint. The evidence does not justify retiring any target; it justifies restricting claims and requiring fail-closed semantic preflight before further capability promotion.

## 2. Status vocabulary

- **E — Emitted:** source generator visibly consumes the relevant ISR section and emits corresponding output. This does not imply correct behavior or successful build.
- **P — Partial/projection:** some shape or subset is emitted, but the full semantics are not represented.
- **F — Fixed template:** output exists, but it is fixed rather than derived from the relevant ISR section.
- **N — Not observed:** no consumption/emission was found in the inspected generation path. This is not proof that no other path exists.
- **R — Refused:** explicit pre-generation refusal is present for the relevant semantic input.
- **U — Unknown:** the source path inspected does not support a reliable conclusion.

A generated file, README claim, manifest entry, or test-source string is not runtime evidence. This matrix records source-level mapping only.

## 3. Canonical ISR dimensions

The source of truth inspected is `tiannara/domain/models/system_model.py`. Its top-level sections include capabilities, domains, services, components, APIs, events, data models, security, infrastructure, deployment, documentation, testing, operational policies and extensions.

The important semantic subcontracts include:

- Data fields: type, requiredness, description, enum values, reference target.
- Data model: owning service, invariants and consistency posture.
- Services: domain, responsibilities, exposed capability IDs and communication styles.
- API: provider/consumer services, interaction style, operation name/description, command/query semantics and idempotency.
- Events: producer/consumers, payload model, delivery guarantee and ordering.
- Security: authentication, authorization, classification, encryption in transit/at rest, audit logging and secrets management.
- Infrastructure: topology, statefulness, scaling unit and availability.
- Deployment: rollout, environments, scaling policy and zero-downtime requirement.
- Testing: required levels, coverage posture, performance and security testing.
- Operations: SLOs, logging, metrics, tracing, health/readiness, audit events, backup, disaster recovery and incident response.

## 4. Backend-by-backend requirement-to-emission matrix

| Backend | Data models / fields | Services / components | APIs / operations | Events | Security | Persistence | Deployment / operations | Tests |
|---|---|---|---|---|---|---|---|---|
| FastAPI | P — maps typed model fields and emits model/schema files | P — emits service/repository layers; legacy conversion maps service names/responsibilities, but full component semantics are not proven | P — emits CRUD-style routes from data models; not a demonstrated projection of each ApiSpec operation and its command/query/idempotency semantics | N — no event delivery implementation established | P — authentication posture influences generated dependencies; full authorization, classification, encryption, secrets and audit requirements not all implemented; manifest explicitly records audit events false and external trace export false | P — memory repositories are generated; durable adapter is not established by this generator | P — Docker/compose/CI, health/readiness and local metrics/logging/tracing context emitted; ISR rollout, multi-zone/region and SLO enforcement not established | P — generated API tests and runtime profile; required testing policy/coverage not comprehensively derived |
| Go | P — only first data model is selected; fallback Item if none | P — generic application service/repository layers for the selected entity; not all ISR service/component definitions | P — generated CRUD-oriented handlers for selected entity, not all declared ApiSpec operations | N | N — security policy not mapped in inspected generator | P — in-memory repository only in generated source | P — Docker/compose/CI and health-oriented service; ISR deployment and operations policy not implemented as such | P — generated API tests and Go build/test profile; policy-level coverage/security/performance requirements not mapped |
| Rust/Axum | P — iterates data models and maps fields to Rust types; enum/reference constraints and invariants not shown as enforced | N — no ISR service/component implementation established | F — fixed health route; no generated ISR API operations | N | N | N — no repository/persistence implementation established | P — Dockerfile and build profile; no ISR deployment/rollout/operations mapping | F — generated health test; no tests derived from ISR testing policy |
| NestJS | P — iterates data models and emits model types | F/N — module and health controller templates; no service/component semantics derived | F — fixed health endpoint; no ApiSpec operation projection established | N | N | N | P — Dockerfile/build profile; no ISR deployment policy mapping | F — generated test template; no testing policy projection established |
| Spring Boot | P — emits classes and mapped field types | F/N — fixed application and health controller | F — fixed health endpoint; no ApiSpec operation projection established | N | N | N | P — Dockerfile/build profile; no ISR rollout/availability mapping | F — health endpoint test; not ISR testing policy |
| ASP.NET Core | P — emits model properties with mapped field types | F/N — fixed minimal application; no ISR service/component implementation established | F — fixed health endpoint | N | N | N | P — Dockerfile includes test/publish commands; no ISR deployment strategy or environment policy mapping | F — generated test asserts a constant path equality, not generated application behavior or ISR policy |
| Express | P — emits TypeScript interfaces; field values are typed as unknown rather than mapped to the ISR's concrete abstract field types | F/N — fixed Express app; no ISR service/component behavior | F — fixed health endpoint; no ApiSpec operations | N | N | N | P — Dockerfile includes build/test commands; no ISR deployment strategy or operations policy mapping | P — generated HTTP test exercises health and 404 behavior, but no ISR-derived business behavior |
| Ktor | P — emits data classes and partial field type mappings; enum values/reference constraints/invariants not established | F/N — fixed application module and health route | F — fixed health route | N | N | N | P — Dockerfile/build profile; no ISR deployment policy mapping | F — generated test compares the literal "/health" with itself; it does not start or exercise the application |
| Phoenix | P — emits domain type projections; unknown field types fall back to term() | F/N — fixed Plug.Router health endpoint and domain type module | F — fixed health endpoint; no ApiSpec operation projection | N | N | N | P — Dockerfile/build profile; no ISR deployment/operations mapping | F — generated test compares the literal "/health" with itself |
| Laravel | P — emits Eloquent model class shells; does not map the full field schema into migrations/constraints | F/N — placeholder artisan entrypoint and fixed health route | F — fixed health route; no ApiSpec operation projection | N | N | N — model inheritance alone does not establish migrations, schema or database configuration | P — Dockerfile is present; no ISR deployment policy mapping | F — generated test asserts true, not application behavior |
| Rails | P — emits ActiveRecord model class shells; no schema/migration mapping established | F/N — fixed health controller/route | F — fixed health route; no ApiSpec operation projection | N | N | N — ActiveRecord model class alone does not establish migrations or configured durable persistence | P — Dockerfile/build profile; no ISR deployment policy mapping | P/F — health integration test source exists, but it is not derived from the ISR testing policy and is not run by ProjectCompiler's verifier |

This matrix is deliberately conservative. A cell marked N or F means the inspected generator did not demonstrate the corresponding ISR-driven behavior; it does not mean the target framework is incapable of implementing it.

## 5. Cross-backend semantic gaps

### FS00-EMIT-001 — Multi-entity completeness is not preserved consistently (High)

Go's `_primary_entity()` explicitly selects `system_model.data_models[0]`, and its generation methods receive that one selected entity. Other declared data models are not wired through the generated application. Rust, NestJS, Spring Boot, ASP.NET Core and several others iterate models for class generation, but model projection alone does not establish repository/API/service wiring for every model.

**Required behavior:** either compile every in-scope model and its relationships, or refuse the request before emission with a list of unsupported model semantics.

### FS00-EMIT-002 — Data field constraints are lost in several projections (High)

The canonical field contract includes enumeration values and reference target model IDs, in addition to type and requiredness.

Observed examples:
- Express emits every property as `unknown`, losing concrete type semantics.
- Ktor maps field types through a fallback to `Any`, rather than refusing unknown types; enum values/reference constraints are not projected.
- Phoenix maps unknown types to `term()`; this broad fallback can conceal an unsupported type mapping.
- Laravel emits model shells without schema/migration constraints.
- Rails emits model shells without schema/migration constraints.
- Several class generators map primitive types but do not establish enum validation, reference integrity or field-level invariants.

**Required behavior:** use explicit total type mappings, preserve optionality and enum/reference constraints, and fail closed on unmapped or unsupported constraints.

### FS00-EMIT-003 — API semantics are replaced by fixed health routes (Critical)

The canonical API contract includes provider/consumer relationships, interaction style, operations, command/query semantics and idempotency. Most generators emit only a fixed health endpoint. FastAPI and Go generate CRUD-oriented routes from model structure, but this does not prove faithful projection of every ApiSpec operation or its semantics.

**Required behavior:** operation-by-operation traceability from ISR operation ID to generated route/handler, authorization policy, request/response schema and behavioral test. Unmapped operations must block generation.

### FS00-EMIT-004 — Service/component semantics are not generally compiled (Critical)

Service responsibilities, exposed capability IDs, communication styles and component kinds are architectural requirements. Fixed health applications and model-only classes do not implement those semantics. FastAPI and Go provide generic service-layer files but still require traceability from each declared service/component to generated behavior.

**Required behavior:** explicit service/component mapping and proof that dependencies and responsibilities are represented. No silent omission.

### FS00-EMIT-005 — Event delivery guarantees have no demonstrated implementation (Critical)

EventSpec carries producer/consumer identity, payload model, delivery semantics and ordering. No event broker/transport, delivery guarantee or ordering implementation was established in these generators.

**Required behavior:** event semantics must be supported by an explicitly selected event-capable backend/adapter with executable delivery and ordering tests, or refused before generation. A generic message type or event file would not be sufficient.

### FS00-EMIT-006 — Security posture is not comprehensively enforced (Critical)

SystemModel security includes authentication, authorization, classification, encryption in transit/at rest, audit logging and secrets management. FastAPI has a partial authentication implementation, but its manifest records audit events false and external trace export false. The other inspected service generators do not establish a complete mapping of these security requirements.

**Required behavior:** security preflight must bind every required posture to generated code/configuration and negative behavioral tests. Unsupported security requirements must block generation. A generic security capability declaration is not sufficient.

### FS00-EMIT-007 — Persistence semantics are incomplete (Critical)

FastAPI emits memory repositories; Go emits an in-memory repository. Several other generators emit model classes only. No broad durable database adapter, migration, transaction, consistency or recovery contract was established across this family.

**Required behavior:** persistence engine, schema/migration, transaction semantics, consistency and backup/recovery must be explicit backend capabilities with runtime evidence. In-memory storage must never be presented as durable persistence.

### FS00-EMIT-008 — Deployment and operations fields are not translated into governed deployment plans (High)

Dockerfiles, compose files, CI files and health endpoints are useful artifacts, but do not implement the ISR's topology, availability, scaling unit, rollout strategy, environment policy, zero-downtime requirement, backup, disaster recovery, incident response or SLOs.

**Required behavior:** distinguish packaging from deployment. Map each operational requirement to an enforceable artifact or external execution contract; otherwise refuse or mark the requirement unsupported.

### FS00-EMIT-009 — Testing policy is not compiled into a complete evidence plan (High)

The ISR can require unit, integration, end-to-end, property-based, performance, security and mutation testing, as well as enforced coverage. Several generated tests are constant self-comparisons or unconditional assertions. The ProjectCompiler verifier does not execute most native build/test profile commands.

**Required behavior:** generate test obligations from the testing policy, prove that each obligation is executed, and preserve results. A generated test file or test command is not a test pass.

### FS00-EMIT-010 — Extensions are not safely accounted for (High)

The canonical SystemModel allows unknown concerns in `extensions` for schema evolution. No inspected backend generator demonstrates a general extension-consumption contract or an explicit rejection of unknown extension semantics.

**Required behavior:** unknown extension keys that can affect behavior must be classified and either handled by a versioned extension contract or rejected. They must not be silently dropped.

## 6. Target-specific evidence notes

### FastAPI

The source emits a substantial service architecture and consumes more SystemModel information than other targets. It derives model, repository, schema and CRUD-style route files; generated authentication behavior is influenced by the model's authentication posture. It also emits structured logging, metrics and trace-context middleware.

However:
- the generator's CRUD route structure is not a complete mapping of arbitrary ApiSpec operations;
- memory repositories are not durable persistence;
- the manifest explicitly says business audit-event generation is not implemented and external trace export is false;
- no complete event-delivery, infrastructure-topology, deployment-rollout, SLO, backup or disaster-recovery mapping is established;
- the existence of build/test profile commands does not mean ProjectCompiler executes them.

Disposition: **PARTIAL — most developed ProjectCompiler service target; not universally ISR-preserving or fully certified.**

### Go

The source emits a coherent hexagonal service skeleton and profile commands for `go build` and `go test`. However, `_primary_entity()` selects only the first data model, or fabricates an Item fallback when none exists. The generated handlers/repositories/services are built around that one entity. The fallback can produce an apparently coherent application even when the ISR contains no actual data model.

Disposition: **PARTIAL — meaningful typed service generator, but multi-entity and broader ISR semantic preservation are unproven.**

### Rust/Axum

The source iterates data models for Rust structs and has explicit errors for unsupported field types and field-name collisions. This is useful fail-closed behavior at the field projection layer. The generated service application itself is a fixed health route; data models are not connected to generated CRUD operations, repositories or declared services/APIs.

Disposition: **PARTIAL STRUCTURAL SERVICE SHELL — typed model projection, not business application compilation.**

### NestJS, Spring Boot, ASP.NET Core, Express, Ktor and Phoenix

These targets emit framework-specific application skeletons and model projections. The observed route behavior is fixed health behavior, not a mapping of arbitrary ISR operations. Their generated tests vary significantly in quality; Ktor and Phoenix use literal self-comparisons for the health path. ASP.NET's generated test similarly asserts a constant equality. These tests do not validate application behavior.

Disposition: **PARTIAL FRAMEWORK SCAFFOLDS — target-specific native build and runtime evidence still required.**

### Laravel and Rails

Both emit framework-oriented model classes and health routes. Laravel's `artisan` file is explicitly a placeholder, its health test asserts true, and its Dockerfile runs `php -v` rather than installing dependencies or running tests. Rails emits model class shells without demonstrated migrations/schema generation. Its health integration test source is more meaningful, but it remains unexecuted by the ProjectCompiler verifier.

Disposition: **SCAFFOLD / INCOMPLETE APPLICATION GENERATION — not production application compiler evidence.**

## 7. Android separation

Android is not included in the 11 backend-service matrix because the ProjectCompiler Android target is declared as `FRONTEND_APPLICATION`, not `BACKEND_SERVICE`.

- ProjectCompiler Android implementation: static Kotlin/Compose model catalogue, requires at least one data model, explicitly refuses service/API/event semantics.
- Root Universal Compiler Android implementation: separate structural backend and separate registry, with an empty executable feature set and explicit unsupported-plan refusal.

Neither Android implementation is certified by this matrix. Neither result may be used as evidence for the other. Both require separate SDK/Gradle build, installation, emulator/device launch and functional UI behavior evidence.

## 8. Required universal compiler contract

Before backend generation, the governed compilation authority should construct a semantic obligation ledger for the exact ISR hash:

1. Enumerate every requirement and semantic element, preserving stable source IDs.
2. Bind each obligation to exactly one backend implementation or an approved external adapter.
3. Classify it as SUPPORTED, UNSUPPORTED or UNKNOWN with evidence references.
4. Refuse generation if any MUST obligation is UNSUPPORTED or UNKNOWN.
5. Permit explicit, user-approved scope reduction only when the resulting ISR is revised and re-hashed; never silently omit a requirement.
6. Generate into an isolated quarantine location only after semantic preflight passes.
7. Run native build, generated behavioral tests, security tests and runtime acceptance tests.
8. Independently compare observed behavior against the ISR obligations.
9. Publish only after all required gates pass and the authorized release decision is recorded.

This contract must not let a backend self-certify its own capabilities. A backend's manifest is a declaration; its certification evidence must be independent and bound to the exact implementation revision and ISR content hash.

## 9. Next checkpoint

**Checkpoint 5 — invocation, reachability and artifact-publication trace.**

For each of the 11 backend-service targets, and separately for both Android implementations:

- trace the CLI/API entrypoint through planning, selection and execution;
- identify all direct `generate()`, `compile()` and legacy writer call sites;
- identify which registry is used by each production route;
- determine whether a target is selectable, selected, invoked, verified, executed or published;
- trace output directories, temporary staging, cleanup and failure paths;
- identify any bypass around semantic preflight, verification or authorization;
- bind every claim to the exact backend family and commit.

## 10. Change-control boundary

This checkpoint is documentation-only. It does not authorize:
- backend implementation or test modifications;
- capability manifest changes or capability upgrades;
- registry consolidation or backend retirement;
- ISR schema changes;
- Android implementation merging or promotion;
- artifact publication or deployment;
- FS-01 implementation work;
- PR #201 merge or FS-00 closure.

No native build, runtime, security, emulator or device test was executed in this checkpoint. Findings are source-derived and must not be represented as test passes. UNKNOWN remains UNKNOWN.
