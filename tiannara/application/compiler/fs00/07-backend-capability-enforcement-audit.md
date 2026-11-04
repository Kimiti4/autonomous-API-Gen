# FS-00 — Backend Capability Enforcement Audit (Checkpoint 3)

**Date:** 2026-11-04  
**Inspected revision:** `944ec2bfec23049134b3b72c4267bdb39e577015`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**PR:** #201 (open, draft; base `remediation/w12-executable-effect-contract`)  
**Scope:** read-only source and test-inventory audit. This checkpoint adds documentation only; no production code, schemas, registries, backend implementations, tests, or workflows were changed.

## 1. Executive result

The ProjectCompiler composition root registers 21 implementations: 12 targets in the backend/application grouping and 9 frontend targets. The 12 are not 12 equivalent backend-service compilers: the Android entry is registered as `ArtifactKind.FRONTEND_APPLICATION`; the other 11 are `BACKEND_SERVICE` targets.

The source confirms a meaningful capability-declaration enforcement gap:

1. The selector matches requirements against declarations, not implementation-level evidence.
2. Most declarations are copied directly from each backend's emitted `CapabilityManifest`; the same self-assertion therefore drives both selection and output metadata.
3. Several manifests advertise 11 capabilities, including lint, static analysis, security scanning, deployment, observability and release, although the inspected `generate()` methods principally emit application skeletons, health routes, model files, tests, Dockerfiles and README files. Source presence of a Dockerfile or test file does not prove the corresponding operation is executable or certified.
4. The ProjectCompiler's own verifier does not execute the build and test commands in backend build profiles. Python receives syntax/AST checks, Go receives static required-file/import checks, and other languages fall back to required-file presence checks.
5. For most non-Android backends, the inspected generation path does not reject service/API/event/effect semantics that its templates do not implement. Several emit only models and a health endpoint. This creates a risk of accepting an ISR/SystemModel while omitting requested behavior.
6. The Android target is deliberately narrow and has explicit refusal behavior. It must not be promoted beyond a static catalogue shell based on structural output alone.

**Disposition:** no backend is certified as a generally capable production application compiler by this source audit. FastAPI and Go have materially richer implementation/test evidence than most other targets, but their broad manifests and native build/runtime status still require independent, target-specific proof. This checkpoint does not retire any backend or authorize capability changes.

## 2. Inventory and classification

The 12 entries registered by `tiannara/application/compiler/composition.py:build_compiler_registry()` are:

| Target | Artifact kind | Declared capabilities | Source-level implementation observation |
|---|---|---|---|
| `fastapi_hexagonal` | BACKEND_SERVICE | 11 | Richest inspected service generator: domain, application, infrastructure, API, memory repositories, health and observability files. Manifest explicitly says external trace export and audit events are false. |
| `go_hexagonal` | BACKEND_SERVICE | 11 | Emits a Go service structure with domain, repository, application, memory, API and server files. Generation is centered on a primary entity; broad operational capability declarations are not independently enforced. |
| `rust_axum` | BACKEND_SERVICE | 5 | Emits Axum health application, typed model structs, Cargo manifest and tests. Inspected generator does not establish requested service/API/effect behavior beyond this narrow output. |
| `nestjs` | BACKEND_SERVICE | 5 | Emits Nest application/module, health controller, model files, test and Dockerfile. |
| `spring_boot` | BACKEND_SERVICE | 5 | Emits Spring application, health controller, model classes, test and Dockerfile. |
| `aspnet_core` | BACKEND_SERVICE | 11 | Emits project, Program, model and test files plus Dockerfile; 11-capability manifest includes operations not proven by the generator. |
| `phoenix` | BACKEND_SERVICE | 11 | Emits Mix project, web/health route and domain file, test and Dockerfile; broad operational declarations lack matching enforcement evidence. |
| `ktor` | BACKEND_SERVICE | 11 | Emits Gradle project, application/health route, model file, test and Dockerfile; broad operational declarations lack matching enforcement evidence. |
| `express` | BACKEND_SERVICE | 5 | Emits Express application, domain file, HTTP health test, package/TypeScript configuration and Dockerfile. Test source asserts live HTTP behavior, but ProjectCompiler does not run it. |
| `laravel` | BACKEND_SERVICE | 11 | Emits Composer manifest, placeholder Artisan entrypoint, health route, model file, test and Dockerfile; not evidence of a complete Laravel application. |
| `rails` | BACKEND_SERVICE | 11 | Emits Gemfile, health route/controller, model file, test and Dockerfile; not evidence of a complete Rails application. |
| `android` | FRONTEND_APPLICATION | 2 | Static Kotlin/Compose model catalogue only; explicitly refuses service/API/event semantics. Not a backend-service compiler. |

Capability counts above are the number of values in the corresponding manifest at the inspected revision. They are declarations, not certification results.

## 3. Findings

### FS00-CAP-001 — Selection trusts declarations rather than demonstrated behavior (High)

**Evidence**
- `composition.py` registers each backend together with a `BackendCapabilityDeclaration`.
- `selector.py:BackendSelector.rank/select` matches artifact kind and `required_capabilities` against declaration values.
- The backend declarations for most targets use `list(self._manifest().capabilities)`. FastAPI has a separately authored declaration but still lists its manifest capabilities.
- `BackendCapabilityDeclaration.supports()` is a metadata-membership check. It does not call a backend, inspect an implementation proof, or consult independent certification evidence.

**Impact**

A target can be selected because it declares a capability even when the selected implementation has not demonstrated the capability's behavior. Mirroring a manifest into the declaration does not provide independent corroboration.

**Required evidence**

Each capability needs a machine-checkable contract, an implementation binding, positive and negative tests, and independent execution evidence. A declaration must not become selectable merely because it appears in the backend's own manifest.

### FS00-CAP-002 — Broad operational capability declarations are not substantiated by the inspected generators (High)

**Evidence**
- ASP.NET Core, Phoenix, Ktor, Laravel and Rails each advertise 11 capabilities: BUILD, LINT, STATIC_ANALYSIS, TEST, SECURITY_SCAN, CONTAINERIZE, DEPLOY, HEALTH_CHECK, OBSERVABILITY, DOCUMENTATION and RELEASE.
- Their inspected `generate()` methods primarily emit application source/templates, tests, Dockerfiles and README files.
- The inspected generators do not establish executable lint/static-analysis/security-scan pipelines, deployment definitions or deploy actions, observability integrations, or release/packaging metadata for all those declarations.
- Go and FastAPI also advertise 11 capabilities; their implementations are more substantial, but their manifests still require per-capability evidence. FastAPI's own manifest explicitly records `external_trace_export: false` and `audit_events: false`, demonstrating that an OBSERVABILITY declaration is not proof of every observability sub-capability.

**Impact**

Consumers of capability metadata may select a backend for an operation that the generated bundle does not actually provide. A Dockerfile is not proof of container-image construction; a test file is not proof that tests pass; a health route is not proof of deployment, release or observability.

**Required evidence**

Use capability-specific acceptance tests and execution records. Remove or withhold unsupported declarations only through a separately reviewed remediation; no such change is made here.

### FS00-CAP-003 — ProjectCompiler verification does not run native build/test commands (Critical)

**Evidence**
- Backend build profiles contain fields such as `build_command`, `test_command`, `runtime_image` and `requires_build_phase`.
- `ProjectCompiler._verify()` obtains the profile, checks generated documentation, writes the in-memory `CompilationResult` into a temporary directory, then calls `make_verifier()`.
- `make_verifier()` dispatches Python to syntax/AST verification and Go to `GoBundleVerifier`; all other languages use `RequiredFilesVerifier`, which checks only that required paths exist.
- The inspected `_verify()` path does not execute `build_command` or `test_command`.

**Impact**

A successful ProjectCompiler verification result for Java, Kotlin, C#, TypeScript, PHP, Ruby or Elixir can mean only that required files exist and documentation checks pass. It is not native compilation, test, runtime, packaging or deployment evidence. Even the Python/Go checks are not equivalent to native end-to-end application certification.

**Required evidence**

A separately governed execution harness must run the exact backend build/test contract in a pinned toolchain, preserve logs and exit codes, and independently exercise generated behavior. Missing toolchains or skipped commands must remain UNKNOWN/NOT_RUN, never PASS.

### FS00-CAP-004 — Unsupported semantics are not consistently rejected before generation (High)

**Evidence**
- The Android ProjectCompiler backend checks for at least one data model and rejects services, APIs and events before constructing its file map.
- The second Android structural backend has an even broader explicit pre-emission refusal gate for services, events, security policies, API operations, effects, effect bindings, consequences, invariants, frontend routes/interactions, and typed data-model behavior.
- The inspected Rust, NestJS, Spring Boot, ASP.NET Core, Express, Ktor, Phoenix, Laravel and Rails `generate()` methods emit fixed application templates and model projections. No equivalent comprehensive semantic refusal gate was established in these methods.
- Several generators emit a health endpoint and model classes without implementing the full SystemModel service/API/effect semantics.

**Impact**

Requested behavior may be silently omitted while a syntactically plausible project shell is emitted. This violates the required UNKNOWN/unsupported fail-closed behavior and makes generated source look more complete than it is.

**Required evidence**

Before any backend emits files, compare every ISR semantic element with an explicit supported/refused/unknown semantic map. Reject unsupported or unmapped requirements before generation. Tests must assert both the refusal and that no output is emitted or published.

### FS00-CAP-005 — Current verifier is not an artifact quarantine/publication boundary (High)

**Evidence**
- `CompilationExecutor.execute()` calls `backend.generate(system_model)` before ProjectCompiler verification.
- The executor uses collect-all semantics and records failures; it does not provide a quarantine transaction.
- `ProjectCompiler._verify()` materializes the generated result in a temporary directory only after generation.
- The legacy `compile(isr, genome, output_dir)` methods in backend classes call `write_bundle()` directly to the caller-provided output directory.

**Impact**

Post-generation verification cannot establish that the backend was never invoked or that no generated content existed. The ProjectCompiler path does not show a governed quarantine-to-publication transition; direct legacy compile paths write to their requested destination.

**Required evidence**

A future design should separate planning, semantic preflight, generation into an isolated quarantine, independent build/runtime verification, and explicit authorized publication. Failed or UNKNOWN results must remain unpublished and be cleaned or retained only as controlled forensic evidence.

### FS00-CAP-006 — The two Android implementations have different authority and evidence boundaries (High)

**Implementation A:** `tiannara/application/compiler/android_backend.py`
- Registered in the ProjectCompiler composition.
- Artifact kind is FRONTEND_APPLICATION.
- Declares only BUILD and DOCUMENTATION.
- Emits a static model catalogue shell.
- Rejects service/API/event semantics.
- Existing `tests/test_android_backend.py` checks registration, generated structure, determinism and refusal behavior. These are source/unit tests, not Android SDK/Gradle/emulator evidence.

**Implementation B:** `compiler/backends/android.py`
- Registered in the separate root compiler composition as `AndroidStructuralBackend`.
- Backend identity is explicitly `BackendClass.STRUCTURAL`.
- Declares an empty executable feature set.
- Rejects unsupported plan elements before emission.
- Its own source comment states that CampaignRunner skips execution stages for STRUCTURAL backends and that its Docker runner is not Android-aware.
- It emits a Gradle project shape and documentation, but explicitly says Gradle buildability and emulator behavior are not certified.

**Impact**

The two Android targets are distinct implementations, contracts, registries and evidence paths. Neither is evidence that the other compiles or runs. Neither is currently proven to produce a working Android application with functional runtime behavior.

### FS00-CAP-007 — Test inventory is uneven and often checks generated text rather than executing the target (High)

**Evidence**
- FastAPI has a comparatively substantial backend test module, including generated Python syntax, dependency direction, deterministic output, manifest assertions and CRUD behavior tests.
- Go has tests for generated structure, manifest/profile declarations and a previous malformed struct-tag regression. This audit did not execute a Go build.
- Rust's ProjectCompiler-family tests inspect generated files and generated test source. The separate root compiler integration test runs Cargo tests against `compiler.backends.rust_axum.RustAxumBackend`, not the ProjectCompiler-family `tiannara/application/compiler/rust_axum_backend.py`.
- Express tests inspect the generated HTTP test source and runtime entrypoint layout; this audit did not execute npm build/test commands.
- NestJS, Spring Boot, ASP.NET Core and Ktor tests mainly inspect registration, generated file presence/content and build-profile declarations.
- No backend-specific test module matching `tests/test_laravel_backend.py` or `tests/test_phoenix_backend.py` exists in the inspected tree.
- The root compiler's production backend certification tests concern a separate backend family under `compiler/backends/production/`; they do not certify the 12 ProjectCompiler entries.

**Impact**

Test presence, generated test-file presence, a profile command string, and test execution are separate evidence classes. Evidence from one compiler family cannot be transferred to another implementation merely because both target the same language/framework.

**Required evidence**

Maintain per-target evidence ledgers distinguishing source assertions, generator unit tests, native build, generated application tests, runtime integration, security tests, and independent review. Each result must identify the exact backend implementation and commit.

### FS00-CAP-008 — Android is a frontend application target inside the ProjectCompiler registry (Medium)

**Evidence**

The ProjectCompiler registry contains 12 entries grouped in composition imports as backend/application targets, but Android's declaration uses `ArtifactKind.FRONTEND_APPLICATION`; the other 11 use `BACKEND_SERVICE`.

**Impact**

Registry size must not be used as a count of backend-service compilers. Capability and target inventories should classify by artifact kind and actual output contract, not filename or import grouping.

## 4. Evidence classification at this checkpoint

| Target | Source generation | Explicit unsupported-semantics refusal established | ProjectCompiler native build/runtime proof in inspected tests | Audit disposition |
|---|---|---|---|---|
| FastAPI | Yes; substantial | Not established as comprehensive | Not established by this checkpoint; tests include richer Python-level behavior | PARTIAL — strongest evidence, not universal certification |
| Go | Yes; substantial | Not established as comprehensive | Not established by this checkpoint | PARTIAL — source/profile/tests, native evidence still required |
| Rust/Axum | Yes; narrow service shell | Not established | No; root-family Cargo integration is a different implementation | NOT CERTIFIED |
| NestJS | Yes; narrow service shell | Not established | No | NOT CERTIFIED |
| Spring Boot | Yes; narrow service shell | Not established | No | NOT CERTIFIED |
| ASP.NET Core | Yes; narrow service shell | Not established | No | NOT CERTIFIED |
| Phoenix | Yes; narrow service shell | Not established | No | NOT CERTIFIED |
| Ktor | Yes; narrow service shell | Not established | No | NOT CERTIFIED |
| Express | Yes; health/API shell | Not established | No; generated HTTP test is not run by ProjectCompiler verifier | NOT CERTIFIED |
| Laravel | Yes; placeholder/health/model shell | Not established | No | NOT CERTIFIED |
| Rails | Yes; health/model shell | Not established | No | NOT CERTIFIED |
| Android ProjectCompiler | Yes; static catalogue | Yes, for services/APIs/events | No Android SDK/Gradle/emulator evidence | STRUCTURAL STATIC SHELL ONLY |
| Android root compiler | Yes; structural candidate | Yes, for listed unsupported plan elements | Campaign execution skipped for STRUCTURAL class | STRUCTURAL ONLY |

"Not established" means the inspected source/test evidence does not prove it; it is not a claim that no such implementation exists anywhere else in the repository. No test suite or native toolchain was executed during this read-only connector audit.

## 5. Cross-cutting conclusions

1. The current capability selector is declaration-driven. It does not consume independent backend certification evidence.
2. The backend's own manifest is frequently the source of its selection declaration, so declaration and emitted metadata are not independent proof.
3. The ProjectCompiler verifier's success is not equivalent to native build/test/runtime success. For most languages it is a required-file check.
4. The generator family is heterogeneous: FastAPI and Go are more developed than several template-oriented targets. Treating all 12 as equivalent is unsupported.
5. Android is deliberately static and must remain separately classified from backend services and from the other Android implementation.
6. The root Universal Compiler production backend tests, root Android structural tests and ProjectCompiler target tests belong to different execution families. Their results must not be pooled.
7. A single authoritative ISR and one governed compilation authority remain architectural goals, not properties proven by this checkpoint.

## 6. Next audit sequence

1. Build a requirement-to-emission matrix for each of the 11 backend-service targets: data models, CRUD, service operations, API routes, auth/RBAC, persistence, events, effects, invariants, errors, migrations, configuration, deployment and observability.
2. For each backend, identify every semantic element silently ignored, explicitly rejected, or implemented.
3. Inspect and map the exact test suite and execution workflow to each backend class; prevent evidence transfer across compiler families.
4. Design a common capability evidence contract: declaration -> semantic preflight -> implementation binding -> native build -> generated behavioral tests -> runtime evidence -> independent certification.
5. Trace output writing, temporary staging, artifact retention and publication in all reachable routes.
6. Keep Android A and Android B on separate evidence ledgers; define the exact SDK, Gradle, emulator/device and application-behavior requirements before either can be promoted.
7. Reconcile these findings with the canonical ISR and single compilation authority design before proposing registry convergence or backend retirement.

## 7. Change-control boundary

This checkpoint is documentation-only. It does not authorize:
- production code or test changes;
- manifest/capability changes;
- ISR schema changes;
- registry consolidation or backend retirement;
- Android implementation merging or promotion;
- FS-01 or implementation work;
- PR #201 merge or FS-00 closure.

All findings remain subject to independent review. UNKNOWN remains UNKNOWN; generated source, source-level tests, static checks, native builds and runtime behavior remain distinct evidence classes.
