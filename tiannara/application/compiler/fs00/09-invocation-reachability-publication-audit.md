# FS-00 Checkpoint 5 — Invocation, Reachability and Artifact-Publication Audit

**Audit class:** read-only source audit  
**Audited revision:** `68301a4654c90b555c3b0bb93806522c2156421a`  
**Parent audit:** `08-requirement-to-emission-matrix.md`  
**Scope:** compiler entrypoints, composition roots, registries, selectors, generation calls, verification, materialization, publication and failure paths.  
**Change boundary:** documentation only. No compiler, backend, registry, route, workflow, test, schema or generated artifact was changed.

## 1. Executive result

The repository contains multiple separately reachable compiler execution paths. It does **not** yet expose one end-to-end governed compilation authority shared by every compiler family.

The most concrete intent-to-bundle route is the Tiannara ProjectCompiler CLI:

`tiannara create` → `build_project_compiler()` → IntentCompiler → typed SystemModel → requirements → backend selection → `CompilationExecutor.execute()` → backend `generate()` → temporary static verification → `RepositoryMaterializer.materialize()` → optional local Git commit.

A second CLI route, `tiannara factory`, composes the same ProjectCompiler and materializer with an execution environment, test verification, bounded repair and evidence recording.

Separately, the root Universal Compiler API exposes HTTP endpoints for backend discovery, validation, compilation and job retrieval. Its kernel calls a selected backend's `compile()`, validates the returned artifact set and writes artifacts plus a manifest under its configured output root.

The Constitutional Gen-C intent entrypoint is a distinct source-bound route. Its code-generation pass deliberately refuses source-bound generation when selected backends lack explicit source-bound semantic certification. The default Gen-C backend registry currently contains only FastAPI, and the inspected backend does not establish that certification flag. This is a pre-emission block, not a successful compilation.

The campaign-native Android structural backend is another separate implementation and registry family. It must not be conflated with either ProjectCompiler's Android backend or the root Universal Compiler API's production backend registry.

The audit therefore classifies **registration, selection, invocation, static verification, native build/runtime verification and publication as separate states**. No state is inferred from an earlier state.

## 2. Reachability and authority map

| Family / route | Composition and entrypoint | Reachability established at this revision | Publication behavior |
|---|---|---|---|
| Tiannara ProjectCompiler | `tiannara/application/compiler/composition.py`; CLI `tiannara/interfaces/cli/main.py` | CLI `create` and `factory` call `build_project_compiler()`; tests also instantiate it | ProjectCompiler verifies in a temporary directory; RepositoryMaterializer writes bundle files and provenance manifest to caller-supplied output root; optional Git commit |
| ProjectCompiler calibration | CLI `calibrate`; `BackendCalibrationHarness` and `build_calibration_registry()` | Separate explicit calibration command; select-all corpus path | Calibration harness owns its own per-backend output/evidence path; not the same as `create` selection |
| Root Universal Compiler API (Gen-A) | `compiler/api.py` creates FastAPI app and `UniversalCompiler` | HTTP `POST /v1/compiler/compile`, backend list/discovery, validation and job retrieval are defined; module creates `app = create_app()` | Kernel calls backend, validates output, then ArtifactPackager writes files and manifest under job output directory |
| Root campaign-native backend family | `compiler/composition.py`, `compiler/core/*` | Separate registry builder registers Python FastAPI, Rust Axum and Android structural implementations; this is not the registry constructed by `compiler/api.py` | Backend returns a `GeneratedRepository`; campaign execution/publication is a distinct path and requires its own audit |
| Constitutional Gen-C | `constitutional_architecture/compiler/intent_entrypoint.py`, `CompilerPipeline` | Intent entrypoint is callable and exercised by tests; no production HTTP or CLI wiring was found in the inspected composition roots | Pipeline returns in-memory artifacts; inspected pipeline does not itself establish an authorized repository publication transaction |
| Autonomous API backend compiler family | `autonomous-api/app/engine/backend_compiler.py`, FastAPI/Express compiler modules | Compiler functions and tests exist; inspected `autonomous-api/app/main.py` mounts evolution, observation, governance and operator routers, not a compiler route | Backend compiler returns artifact objects; no route-level materializer for these compiler functions was found in the inspected app composition |

**Interpretation:** these are multiple executable seams, not one shared runtime authority. The presence of a FastAPI app object or a registry builder proves that a route can be instantiated or a backend can be registered; it does not prove that the service is deployed, externally reachable, authorized for production use, or certified.

## 3. ProjectCompiler invocation trace

### 3.1 Actual CLI caller

The CLI declares `create`, `factory`, `calibrate`, `generate-corpus`, `run-calibration` and `verify-ledger`.

- `create` constructs the ProjectCompiler using `build_project_compiler(args.provider, transcript_path=args.transcript)`, calls `compile_intent()`, then passes the report to RepositoryMaterializer.
- `factory` constructs the same ProjectCompiler and materializer, then calls SoftwareFactory. SoftwareFactory materializes, executes verification through LocalExecutionEnvironment, optionally performs bounded repair, re-verifies, computes fitness and writes evidence through the configured evidence sink.
- `calibrate` builds a distinct calibration registry and runs a SystemModel corpus through BackendCalibrationHarness. This is not evidence that the regular `create` command uses the same selection policy, corpus or runtime verification path.
- Recorded provider mode requires a transcript. The CLI does not inject a custom live provider; the composition root explicitly rejects `provider_mode="live"` when no provider adapter is supplied.

### 3.2 Registry construction and selection

`build_compiler_registry()` registers the ProjectCompiler backend implementations, including the 11 backend-service implementations and the ProjectCompiler Android frontend-application implementation, plus frontend targets. This registry is independent from the root Universal Compiler API registry and the campaign-native registry.

The composition function's docstring says that the default registry is “FastAPIHexagonalBackend only”; the executable code contradicts that description: when no registry is injected it calls `build_compiler_registry()`, which registers the full ProjectCompiler registry. The docstring must not be used as evidence of the actual default registration set.

The regular CLI path leaves `plan_all=False`. The ProjectCompiler therefore uses `plan_compilation()` (single-best selection) rather than `plan_compilation_across_backends()`. The all-backend path is explicitly a calibration seam. Consequently, “registered in the default registry” does not mean “selected and invoked for each project”.

### 3.3 Generation, verification and report

`CompilationExecutor.execute()` iterates the planned backends and invokes each selected backend's `generate(system_model)`. It collects outcomes and continues after individual exceptions.

ProjectCompiler then calls `_verify()` for each outcome. Verification is performed only when the returned object is the expected `CompilationResult` shape. Other return shapes become UNKNOWN and block the ProjectCompiler report; they are not silently accepted.

For a `CompilationResult`, the flow:
1. obtains the backend's build profile;
2. validates generated README/documentation claims against capabilities and paths;
3. writes the result into a temporary directory;
4. runs the selected BundleVerifier against required files and static language/structure checks;
5. discards the temporary directory when the context exits.

This is not a native build or application runtime test. The BundleVerifier documentation explicitly leaves behavioral verification to tests and the execution environment.

### 3.4 Publication and factory route

RepositoryMaterializer writes successful CompilationResult bundles to the supplied output directory and creates `provenance/manifest.json`. If a source-control backend is supplied, it initializes the repository, stages files and commits them. If Git is unavailable, it still writes the artifact tree and manifest without a VCS commit.

Materialization is not an atomic promotion transaction: files are written directly into the destination tree before the provenance manifest and optional Git operations. The inspected implementation does not stage the complete bundle in a quarantine directory and atomically promote it after all checks. A write or later operation failure can therefore leave a partial destination tree. The materializer's verification refusal is valuable, but it is not equivalent to transactional publication.

The `factory` path adds a distinct runtime verification stage after materialization. It uses LocalExecutionEnvironment, a bounded repair provider and a durable JSONL evidence sink. That route is stronger than the `create` route for build/test evidence, but it still does not prove that all target frameworks, deployment environments or production integrations have been exercised.

## 4. Root Universal Compiler API invocation and publication

`compiler/api.py` builds a BackendRegistry with ReferenceBackend plus the production backend registrations: OpenAPI, PostgreSQL schema, FastAPI foundation, Docker deployment and GitHub Actions CI/CD.

The API exposes:
- `GET /v1/compiler/backends`
- `POST /v1/compiler/backends/discover`
- `POST /v1/compiler/validate`
- `POST /v1/compiler/compile`
- `GET /v1/compiler/jobs/{job_id}`

The compile endpoint calls `UniversalCompiler.compile()`. The kernel validates the ISR payload, resolves the explicitly requested backend and version, builds a plan, runs the optimization pipeline, invokes that backend's `compile(context)`, validates the returned CompilationOutput and calls ArtifactPackager.

ArtifactPackager writes each artifact directly below `output_root/job_id`, computes per-file SHA-256 values and writes `artifact-manifest.json`. The kernel stores the resulting job record in an in-memory dictionary.

Important boundaries:
- The API request chooses one explicit backend ID/version. It does not route the request through the ProjectCompiler's SystemModel-derived multi-backend selector.
- Backend capability discovery is manifest matching, not proof of semantic completeness or independent certification.
- Packaging writes directly to the destination. The inspected path does not first write to a separate quarantine root and atomically promote a fully verified package.
- The job registry is in memory in this kernel implementation; durable job recovery is not established by this source path.
- The API's backend registry is not the same as `compiler/composition.py`'s Python/Rust/Android campaign registry. In particular, the presence of AndroidStructuralBackend in the latter does not make it available through `/v1/compiler/compile`.

## 5. Constitutional Gen-C invocation boundary

`compile_intent_to_constitutional_isr()` composes IntentCompiler, typed SystemModel projection, source binding verification and CompilerPipeline.compile_source_bound().

The pipeline's default backend registry registers only the Gen-C FastAPI backend. The CodeGenerationPass checks every selected backend for `source_bound_codegen_certified is True` whenever source binding is required. If any selected backend lacks that explicit certification, it emits a fatal diagnostic and returns before invoking backend compilation. The inspected FastAPI backend does not demonstrate the required certification declaration.

This is a deliberate fail-closed boundary and must be preserved until backend semantic certification exists. A successful intent projection or complete source binding is not backend semantic certification. The intent entrypoint's “compiled” state is not native build/runtime certification either.

No production CLI or HTTP route invoking this Gen-C intent entrypoint was found in the inspected composition roots; its direct call was located in its test path. Treat it as a separately callable/tested pipeline, not as the live ProjectCompiler route.

## 6. Autonomous API backend compiler reachability

The Autonomous API contains separate backend compiler modules, including a generic TemplateBackendCompiler, FastAPI compiler and Express compiler. The generic compiler validates BackendProjectIR and returns GeneratedArtifact objects; it does not write a repository or run a native build.

The inspected Autonomous API FastAPI composition root mounts the evolution, observation, operator-authentication, governance and maintenance-outbox routers. No compiler-generation route was found in that router composition. The generic backend compiler call sites located by source search were tests, not the production API router.

Therefore, these backend compiler classes are **implemented/testable components**, not demonstrated user-facing application-generation endpoints at this revision. Their outputs must not be counted as production app creation merely because unit tests call them.

## 7. Android implementation separation

| Android path | Registry / invocation boundary | Output / evidence boundary |
|---|---|---|
| ProjectCompiler Android backend | Registered by `tiannara/application/compiler/composition.py`; selected only when the ProjectCompiler planner chooses it | Emits the static model catalogue shell; refuses service/API/event semantics; ProjectCompiler static verification is not an Android SDK/Gradle/device build |
| Campaign-native AndroidStructuralBackend | Registered by `compiler/composition.py` in the separate campaign registry; not registered by `compiler/api.py`'s default production registry | Emits a structural Android repository and has a Gradle build TestSpec, but the implementation comments state campaign execution skips build stages for STRUCTURAL backends; no native Android runtime certification follows from registration |
| Android cloud-build workflow | Separate GitHub Actions workflow and Stage A evidence boundary | A workflow definition is not a successful build. Stage A remains subject to its explicit governance/effect/authorization gates; no status is upgraded by this source audit |

These paths must retain distinct IDs, source revisions, artifacts, build logs, emulator/device evidence and certification records. No Android evidence is transferred between them.

## 8. Reachability classification

| Capability / stage | ProjectCompiler CLI | Root Universal Compiler API | Gen-C intent entrypoint | Autonomous API compiler modules |
|---|---|---|---|---|
| Backend registration | Yes | Yes | Yes (default FastAPI) | Compiler objects exist; no unified API registry observed |
| User-facing entrypoint in source | CLI create/factory | FastAPI compile endpoint | No production route located | No compiler route located |
| Backend invocation | Selected `generate()` | Explicit backend `compile()` | Blocked for source-bound compile unless certification flag is true | Tests invoke compiler methods |
| Static verification | Yes, temporary bundle checks | ISR/output validation; packager follows | Compiler verification pass when codegen reaches it | IR validation only in generic template compiler |
| Native build/runtime | Factory path adds environment tests; create path does not | Not established by kernel | Not established by pipeline alone | Not established by compiler function |
| Artifact publication | Direct output-root materialization | Direct job output-root packaging | In-memory pipeline artifacts; no authorized repository promotion shown | Returned artifact objects; no route materializer shown |
| Atomic quarantine/promotion | Not established | Not established | Not established | Not established |

## 9. Findings

### FS00-IRP-001 — Multiple compiler execution authorities remain
**Severity:** Critical architectural coherence gap  
ProjectCompiler, Gen-A Universal Compiler API, Gen-C CompilerPipeline, campaign-native compiler registry and Autonomous API compiler modules expose separate composition, registry, planning, invocation and publication behavior. They do not currently share one enforced compilation authority and one end-to-end lifecycle contract.

### FS00-IRP-002 — ProjectCompiler is CLI-reachable, not a demonstrated service API
**Severity:** High  
The concrete ProjectCompiler production caller located is the CLI's create/factory path. Tests also instantiate it. No ProjectCompiler HTTP route was found in the inspected service compositions. This limits claims of a unified hosted application-generation service.

### FS00-IRP-003 — ProjectCompiler default registry documentation is stale
**Severity:** Medium  
The composition docstring says FastAPI-only, but executable default construction registers the full ProjectCompiler registry. The code is authoritative; documentation needs correction to prevent mistaken assumptions about selection and backend coverage.

### FS00-IRP-004 — Default project creation selects one backend, not all suitable backends
**Severity:** High  
The regular CLI path leaves `plan_all=False`; only calibration selects all satisfying backends. Multi-backend registration does not mean every backend is invoked for an ordinary project.

### FS00-IRP-005 — Static verification and runtime verification are different routes
**Severity:** High  
ProjectCompiler's built-in verifier checks documentation, required files, syntax/structure and dependency direction. Factory separately executes runtime verification. The CLI create route does not itself execute the generated application or its test suite.

### FS00-IRP-006 — ProjectCompiler publication is not atomic
**Severity:** Critical publication-integrity gap  
RepositoryMaterializer writes directly into the target output root before the final manifest and optional VCS operations. No quarantine-to-approved atomic promotion was observed. A failed write/commit may leave partial output.

### FS00-IRP-007 — Gen-C source-bound code generation is correctly fail-closed but not yet enabled
**Severity:** High capability gap, protective control  
The Gen-C code-generation pass refuses source-bound compilation when the selected backend lacks explicit source-bound semantic certification. The default FastAPI backend does not establish that certification in the inspected source. Preserve the refusal; do not downgrade it to a warning.

### FS00-IRP-008 — Gen-A API and campaign registry are disconnected
**Severity:** High coherence gap  
The root Universal Compiler API registers ReferenceBackend and five production artifact backends. The separate campaign composition registers Python FastAPI, Rust Axum and Android structural backends. Android campaign registration therefore does not make Android selectable through the Gen-A API.

### FS00-IRP-009 — Autonomous API compiler modules are not a demonstrated production route
**Severity:** Medium  
The generic/FastAPI/Express compiler components are exercised by tests, but no compiler route was found in the inspected Autonomous API router composition. Their existence is not proof of production user-facing compilation.

### FS00-IRP-010 — Android execution evidence is fragmented by implementation
**Severity:** Critical evidence-integrity risk  
The ProjectCompiler Android backend, campaign-native AndroidStructuralBackend and cloud-build workflow are separate implementations and evidence channels. They must not share certification or be represented as one Android compiler.

### FS00-IRP-011 — Gen-A package writes lack an atomic promotion boundary
**Severity:** High  
ArtifactPackager writes individual artifacts directly into the job output directory and writes the manifest afterward. The inspected kernel/packager path does not stage, verify and atomically promote the completed artifact set. Partial output after an interrupted package is therefore possible.

## 10. Required remediation direction (not implemented in FS-00)

1. Define one governed compilation lifecycle contract: source/ISR binding → requirement preservation → capability evidence resolution → backend selection → isolated generation → independent verification → native build/runtime tests → quarantine → authorized atomic publication → immutable provenance.
2. Keep compiler implementations and language/framework targets. Do not retire backends to conceal incomplete capability. Restrict only unproven capabilities and require explicit unsupported-semantics refusal.
3. Make every registry a named adapter or plugin source under the single authority; prevent an alternate API/CLI/campaign path from bypassing the authority.
4. Reconcile ProjectCompiler composition docstring with actual registration behavior.
5. Make backend selection explainable and explicit: selected backend(s), reason, rejected alternatives, capability evidence and unsupported requirements. Preserve the select-all calibration path as calibration, not production routing.
6. Make runtime verification a required promotion stage for application targets. Static source checks must never be reported as a successful application build.
7. Introduce isolated staging and atomic promotion. Failed generation, verification, native build, provenance signing or publication must leave no partially promoted candidate.
8. Keep the Gen-C source-bound gate closed until a backend has independently reviewed semantic-preservation evidence.
9. Give Android implementations distinct backend identifiers, benchmark bindings and evidence manifests.
10. Add an invocation matrix test proving which route can reach each backend and which authority blocks unauthorized direct generation/publication.

## 11. Evidence limits and non-claims

- This checkpoint is source inspection at the audited revision. It did not run the CLI, HTTP server, compiler backends, native toolchains, generated application tests, Docker, Gradle, emulator or device.
- Source-level route definitions establish that handlers are implemented in the repository; they do not prove deployment or external reachability.
- GitHub code-search results were used only as a call-site discovery aid. Findings above are anchored to files fetched at the audited branch revision.
- No backend certification, universal language coverage, production readiness, Android build success or runtime success is claimed.
- No production code was changed and no test status was modified.

## 12. Files inspected

- `tiannara/application/compiler/composition.py`
- `tiannara/application/compiler/executor.py`
- `tiannara/application/compiler/project_compiler.py`
- `tiannara/application/compiler/writer.py`
- `tiannara/application/compiler/verification.py`
- `tiannara/interfaces/cli/main.py`
- `tiannara/application/materializer/materializer.py`
- `tiannara/application/factory/factory.py`
- `compiler/api.py`
- `compiler/kernel.py`
- `compiler/packaging.py`
- `compiler/sdk/routes.py`
- `compiler/backends/production/register.py`
- `compiler/composition.py`
- `compiler/backends/android.py`
- `constitutional_architecture/compiler/intent_entrypoint.py`
- `constitutional_architecture/compiler/pipeline.py`
- `constitutional_architecture/compiler/passes/code_generation_pass.py`
- `constitutional_architecture/compiler/passes/verification_pass.py`
- `constitutional_architecture/compiler/backends/fastapi_backend.py`
- `autonomous-api/app/main.py`
- `autonomous-api/app/api/routes.py`
- `autonomous-api/app/engine/backend_compiler.py`

## 13. Next checkpoint

**Checkpoint 6 — verification and native-execution evidence audit.**

Trace each compiler family from generated candidate to actual build/test/runtime evidence. Inventory the tests and CI workflows by backend, distinguish unit/static checks from native compilation and deployed behavior, identify skipped/conditional stages and missing toolchains, and verify whether evidence is bound to the exact source revision, ISR/requirements, backend version and artifact hashes. Keep both Android implementations separate. FS-00 remains open.
