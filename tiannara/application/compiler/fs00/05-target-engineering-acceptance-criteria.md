# FS-00 — Target-Specific Engineering Acceptance Criteria and Evidence Map

**Status:** proposed acceptance baseline; design/audit artifact only  
**Date:** 2026-11-04  
**Repository scope:** `Kimiti4/autonomous-API-Gen`  
**Authority:** subordinate to the approved constitutional/governance authority and canonical ISR; this document creates no implementation or certification authority.

## 1. Purpose and interpretation

This document converts the accepted requirement—combine AI reasoning/generation strengths with senior frontend/backend engineering discipline—into observable acceptance criteria. It also maps those criteria to the governed compilation lifecycle and the evidence required for independent certification.

These are requirements, not claims that any current target satisfies them. A registry entry, source file, generated code sample, mocked toolchain, synthetic artifact, model explanation or passing unit test alone cannot establish target conformance.

Use the following evidence states distinctly:

- **SOURCE_PRESENT:** implementation exists in the inspected revision.
- **REACHABLE:** an identified production route can invoke it.
- **CONTRACT_CONFORMANT:** it accepts the governed canonical input and enforces declared capabilities.
- **NATIVE_BUILD_VERIFIED:** generated output builds with the target's real toolchain.
- **RUNTIME_VERIFIED:** output starts and executes in the declared runtime/deployment environment.
- **BEHAVIOR_VERIFIED:** positive, negative and failure-path behavior matches the bound requirements and oracles.
- **SECURITY_VERIFIED:** applicable threat, authorization, data-protection and abuse cases pass independent checks.
- **INDEPENDENTLY_CERTIFIED:** a verifier other than the generator binds all evidence to exact inputs, transformations, toolchain, source and artifact digests.

A state may not be inferred from a preceding state. UNKNOWN remains UNKNOWN; skipped, mocked, synthetic, unavailable or unexecuted checks are not PASS.

## 2. Governed lifecycle and stage ownership

Every target must be assessed through the same lifecycle. Target-specific adapters may differ; authority, evidence and fail-closed semantics may not.

| Stage | Required responsibility | Minimum evidence |
|---|---|---|
| 0. Admission and identity | Authenticate/authorize caller, establish tenant and request identity, enforce quotas and resource limits | Negative authorization tests, tenant-isolation tests, request-bound audit record |
| 1. Canonical ISR binding | Resolve exact approved ISR revision, schema, provenance, requirement set and integrity digest | Recomputed integrity/invariants at trust boundary; stale/tampered hash rejection; provenance binding |
| 2. Semantic analysis | Identify required entities, operations, data, effects, consequences, invariants, policies, events, UI flows and deployment intent | Requirement-to-ISR trace matrix; ambiguity/conflict diagnostics; oracle coverage |
| 3. Capability decision | Check requested semantics against the selected target's enforced capabilities before invocation | Capability matrix plus tests proving unsupported requests cause zero backend calls and zero artifacts |
| 4. Architecture/design | Produce explicit architecture, threat/failure model, quality budgets and trade-offs | Traceable design decisions; no invented requirement; reviewable risk register |
| 5. Transformation | Execute versioned, source/target-bound transformations preserving semantics | Transformation manifest, input/output digests, mapping coverage, loss/unsupported diagnostics |
| 6. Generation | Invoke only authorized backend; isolate generated output in quarantine | Invocation audit, deterministic/reproducible metadata, quarantine path and artifact digest |
| 7. Static and specialist review | Apply language/framework checks and senior-engineer quality rules | Static-analysis reports, dependency/license checks, maintainability and architecture checks |
| 8. Native build | Build using real pinned target toolchain, not a fake runner or synthetic output | Toolchain identity, reproducible command/log, exit status, build artifact digest |
| 9. Runtime and behavior | Execute in representative runtime; test real interfaces, data, effects and failure behavior | Runtime logs, contract/E2E tests, state/effect observations and failure-injection evidence |
| 10. Security and quality | Verify applicable security, privacy, accessibility, performance and reliability gates | Independent reports and measured budgets; mandatory gates cannot be averaged away |
| 11. Independent verdict | Reconcile all evidence against exact requirement/ISR/source/toolchain/artifact identities | Signed or integrity-bound evidence manifest and explicit PASS/FAIL/UNKNOWN verdict |
| 12. Publication | Release only independently accepted artifacts; preserve rollback and provenance | Publication authorization, immutable artifact digest, release record and rollback evidence |

**Fail-closed invariant:** if admission, ISR integrity, semantic analysis, capability authorization, transformation integrity or mandatory validation fails or is unavailable, no backend may be invoked and no deliverable artifact may be emitted or published. Quarantined diagnostic output, if any, must be explicitly non-deliverable and separately controlled. Final failure after code emission is not an adequate substitute for pre-invocation rejection.

## 3. Shared AI + senior-engineering acceptance criteria

### 3.1 AI reasoning/generation contribution

For each target, demonstrate that the reasoning/generation layer can:

1. Interpret approved requirements and ask for resolution of ambiguity rather than inventing semantics.
2. Explore materially different implementation/design options and explain trade-offs against constraints.
3. Identify edge cases, misuse cases, failure modes and cross-layer inconsistencies.
4. Propose implementation and tests tied to requirement identifiers.
5. Iterate on verifier feedback without weakening requirements, policies or test oracles.
6. Preserve traceability from each generated element to requirement, ISR element and transformation.
7. Operate under governed model selection, versioning, data handling and replaceability; no external LLM provider is mandatory.

Evidence: versioned reasoning/design records, requirement-linked proposals, edge-case/test proposals, model/config provenance where used, and reproducible traces. Narrative claims alone do not pass.

### 3.2 Senior frontend engineering acceptance

Every frontend target must demonstrate:

- Product intent and user journeys mapped to information architecture, routes, screens and states.
- Coherent design tokens/components and consistent visual hierarchy; responsive behavior across declared viewport classes.
- Complete interaction/state model: loading, empty, success, validation, error, offline/retry and permission-denied states where applicable.
- Keyboard operation, semantic structure, accessible names/labels, focus management, contrast and assistive-technology checks against the applicable accessibility standard.
- Client-side validation as usability only; authoritative validation and authorization remain server-side.
- Secure handling of identity, session, untrusted content, navigation and browser storage; no secret leakage.
- Performance budgets for initial load, interaction latency, bundle/resource size and rendering stability.
- Browser/device compatibility matrix and graceful degradation.
- Component, interaction, accessibility, visual-regression and end-to-end tests.
- Maintainable component boundaries, typed contracts, error handling, dependency hygiene and documented deviations.

**Hard frontend gates:** no inaccessible critical user journey; no dead or fabricated interaction; no authorization bypass; no route/interaction omitted from the approved contract; no critical security failure.

### 3.3 Senior backend engineering acceptance

Every backend target must demonstrate:

- Domain model and invariants traceable to approved requirements; explicit aggregate/entity/value boundaries where relevant.
- API/interface contracts with schemas, versioning, validation, error semantics, idempotency and compatibility rules.
- Correct persistence, transactions, constraints, migrations, consistency and recovery; in-memory behavior must not be represented as durable storage.
- Authentication, authorization, tenant isolation, least privilege, secret management, input validation and auditability.
- Correct concurrency, retries, timeout/cancellation, duplicate delivery, ordering and race handling where applicable.
- Explicit effects and consequences: database writes, events, external calls, payments/transfers, notifications and irreversible operations.
- Reliability and operability: health/readiness, structured logs, metrics/traces, graceful shutdown, resource bounds, backup/recovery and rollback.
- Performance budgets and workload-appropriate query/resource behavior.
- Unit, contract, integration, database, migration, concurrency, security, failure-injection and end-to-end tests.
- Maintainable module boundaries, dependency governance, error handling and operational documentation.

**Hard backend gates:** no lost or duplicated consequential effect outside its contract; no unauthorized access or cross-tenant leakage; no weakened invariant/data-integrity rule; no silent semantic omission; no critical security/reliability failure.

### 3.4 Full-stack coherence acceptance

For every full-stack target combination, demonstrate a traceable chain:

`user journey → frontend route/interaction → typed API operation → identity/authorization → domain operation → data/effect → observable result/error`

Tests must exercise this chain against the actual generated frontend and backend, not only mocks. Verify successful, invalid, unauthorized, forbidden, conflict, unavailable, timeout, retry and partial-failure paths where relevant. A frontend's completion cannot compensate for missing backend behavior, and a backend's correctness cannot compensate for inaccessible or broken user journeys.

### 3.5 Independent review and non-compensable gates

The generator cannot be the sole reviewer or certifier. Independent verification must include deterministic contract checks, static analysis, native toolchains, runtime tests, security checks and human specialist review for material architecture/product decisions. A composite score may help rank non-critical quality, but cannot offset a failed hard gate. Any waiver must be explicit, authorized by the proper governance authority, scoped, time-bounded and visible in the verdict; a model cannot issue a waiver.

## 4. Target-family acceptance matrix

The current architecture map records 12 registered backend/application targets and 9 registered frontend targets. This is a preliminary registry-derived list, not proof of exhaustive repository discovery or conformance.

### 4.1 Backend/application targets

| Registered target | Target-specific evidence required in addition to shared gates | Current certification conclusion |
|---|---|---|
| Python / FastAPI | Real ASGI startup; OpenAPI/API contract; persistence and transaction tests for declared data semantics; auth/tenant tests; async/concurrency tests; dependency and container checks | Not established by registration or in-memory payroll contract tests |
| Go | Native pinned Go build/test; HTTP/router contract; context cancellation, concurrency/race and data-store tests; executable runtime probes | UNKNOWN pending target-specific evidence |
| Rust / Axum | Native pinned Rust build/test; Axum route/middleware contract; ownership/concurrency/error behavior; persistence/security/runtime probes | Prior host-toolchain checks are historical and do not certify current head |
| NestJS | Native Node/TypeScript build; module/DI/guard/interceptor behavior; API contract; persistence/transaction and async failure tests | UNKNOWN pending target-specific evidence |
| Spring Boot | Native JDK/Gradle or Maven build; dependency injection/security filters; transaction and persistence tests; executable application/health/API probes | UNKNOWN pending target-specific evidence |
| ASP.NET Core | Native .NET build/test/publish; middleware/DI/auth policies; EF or declared persistence semantics; runtime/API probes | Historical smoke evidence is not full target certification |
| Phoenix | Native Elixir/Mix build/test; Plug/Phoenix route and supervision behavior; Ecto persistence/transaction tests where declared; release/runtime probes | UNKNOWN pending target-specific evidence |
| Kotlin / Ktor | Native Kotlin/Gradle build/test; coroutine cancellation/concurrency; routing/auth/content negotiation; persistence and runtime probes | UNKNOWN pending target-specific evidence |
| Android — Tiannara ProjectCompiler `AndroidBackend` | Real Gradle/Android plugin build; generated Compose project build; emulator/device install and launch; UI/state/accessibility tests; declared backend/API semantics must be rejected unless actually implemented | Source currently describes a static model-catalogue shell; no native runtime certification established |
| Express | Native Node build/test; middleware ordering, routing, validation, auth, async error propagation; persistence and live HTTP probes | Historical checks on an earlier snapshot are not current-head certification |
| Laravel | Native PHP/Composer build/test; route/middleware/policy behavior; migrations/transactions/queues; HTTP/runtime probes | UNKNOWN pending target-specific evidence |
| Rails | Native Ruby/Bundler/Rails build/test; routes/controllers/auth callbacks; ActiveRecord transactions/jobs; HTTP/runtime probes | Historical Ruby smoke is not full target certification |

**Android separation rule:** the root campaign `AndroidStructuralBackend` is a separate implementation and requires its own matrix row, invocation trace and evidence. Its structural classification and empty supported-feature set mean it must refuse semantics outside its explicit scope. It must not be merged conceptually with the Tiannara ProjectCompiler Android backend. Android contract tests, fake command runners and synthetic APK fixtures are not Gradle/emulator/native runtime evidence.

### 4.2 Frontend targets

Frontend hardening is recorded as a completed workstream, but each target still needs current-head evidence against the shared frontend and full-stack gates.

| Registered target | Target-specific evidence required | Current certification conclusion |
|---|---|---|
| React | Native package build; component/state/router tests; accessibility and browser E2E; real API integration | Workstream milestone does not establish per-target certification |
| Vue | Native package build; component/reactivity/router tests; accessibility and browser E2E; real API integration | UNKNOWN pending current-head target evidence |
| Angular | Native CLI build; DI/forms/router/state tests; accessibility and browser E2E; real API integration | UNKNOWN pending current-head target evidence |
| Next.js | Production build; server/client boundary and route tests; hydration, caching and auth behavior; browser E2E | UNKNOWN pending current-head target evidence |
| Nuxt | Production build; SSR/CSR/hydration, routing and server middleware tests; browser E2E | UNKNOWN pending current-head target evidence |
| Svelte | Native build; component/reactivity/state tests; accessibility and browser E2E | UNKNOWN pending current-head target evidence |
| Phoenix LiveView | Native Mix build; LiveView lifecycle/event/state tests; authorization and real backend integration | UNKNOWN pending current-head target evidence |
| Hologram | Native framework build; server/client serialization, navigation and interaction tests; runtime integration | UNKNOWN pending current-head target evidence |
| Scenic | Native build; scene/event/input/state behavior; target display/runtime integration and accessibility-equivalent interaction checks | UNKNOWN pending current-head target evidence |

The frontend list is not necessarily exhaustive: inspect root compiler backends, Gen-C, Universal Compiler API, per-category compilers and dynamically loaded/deployment targets before closing the inventory.

## 5. Required evidence package per target

Each target must have a versioned evidence package containing at minimum:

1. Target identity: language, framework, supported versions, platform, backend implementation and exact source commit.
2. Reachability: production entrypoint, selector/registry path, invocation call chain and runtime configuration.
3. Capability declaration and enforcement: feature-level positive and negative cases, including zero-invocation/zero-artifact refusal tests.
4. Canonical ISR binding: revision/schema/provenance/hash and integrity verification results.
5. Semantic mapping: requirement-to-ISR-to-target construct-to-test-oracle matrix, including explicit unsupported/loss diagnostics.
6. Transformation manifest: transformer identity/version, source/target contract versions, input/output digests and preservation result.
7. Architecture and threat/failure model with quality budgets and approved deviations.
8. Native toolchain identity, reproducible build logs and artifact digest.
9. Runtime deployment/test environment and observed startup/health/interface behavior.
10. Positive, negative, boundary, concurrency, failure-injection and end-to-end test results.
11. Security, privacy, accessibility (where applicable), performance and reliability reports.
12. Independent verifier identity/version, verdict, unresolved findings and evidence-manifest integrity.
13. Publication/quarantine decision, provenance, rollback and retention record.

Evidence must be bound to exact source, canonical ISR, transformations, toolchain and generated artifact. Re-running a test against a different commit or artifact does not silently update an earlier verdict.

## 6. Acceptance decision rules

A target is **not ready for certification** if any of the following is true:

- its actual invocation route or consumer is unknown;
- its declared capabilities are not enforced before backend invocation;
- any required ISR semantic is dropped, weakened, guessed or left ambiguous;
- canonical ISR integrity/provenance is not revalidated at the trust boundary;
- failed validation can still invoke a backend or emit deliverable artifacts;
- native build or runtime evidence is missing for a claimed runnable target;
- behavior is only mocked/synthetic where real integration is required;
- security, data integrity, authorization, accessibility obligations or other hard gates fail;
- evidence cannot be reproduced or is not bound to exact source/input/artifact;
- the generator is also the sole certifier.

Verdicts are **PASS**, **FAIL** or **UNKNOWN**. PASS requires every mandatory gate and evidence item for the declared scope. FAIL records a demonstrated violation. UNKNOWN records absent, skipped, stale, ambiguous or insufficient evidence. Do not convert UNKNOWN to PASS through aggregate scoring or optimistic narrative.

## 7. FS-00 work remaining

1. Complete repository-wide discovery of every compiler/backend/frontend implementation, including dynamic imports, plugins, deployment entrypoints and test-only implementations.
2. Trace each target from user/API/CLI entrypoint through selector, capability gate, transformation, backend invocation and artifact publication.
3. Complete the capability-preservation and semantic-loss matrix for every target and every distinct compiler family.
4. Verify the actual frontend hardening evidence and distinguish workstream completion from per-target certification.
5. Audit backend hardening against the criteria above; prioritize authorization, canonical ISR binding, semantic preservation, effects/invariants, pre-invocation refusal and artifact quarantine.
6. Audit both Android implementations separately, including real native cloud/local build and emulator/device execution requirements.
7. Map the independent verifier and evidence-manifest mechanism to every lifecycle stage.
8. Reconcile all findings into the FS-00 review package with exact source references, commit identities, unresolved questions and proposed sequencing.

## 8. Authority and change control

This document is an FS-00 acceptance-design artifact only. It does not:

- certify any target or declare frontend/backend implementation complete;
- authorize production code, schema, registry, contract or migration changes;
- authorize backend consolidation, deprecation, retirement or deletion;
- authorize FS-01 or any implementation stage;
- approve or merge PR #201;
- close FS-00 or replace independent review.

The independent reviewer must explicitly review and approve FS-00 before any separately scoped implementation authorization is considered.
