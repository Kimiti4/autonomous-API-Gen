# FS-00 — Compiler Inventory and Reachability Audit (Checkpoint 2)

**Date:** 2026-11-04  
**Inspected revision:** `81f8fa1be927dad19e9bc868738016233599e9e3`  
**Branch:** `remediation/esap-android-compiler-stage-a`  
**Scope:** read-only source audit recorded as documentation. No production code, schema, registry or backend implementation was changed.

## 1. Executive result

The repository contains more compiler execution surfaces than the 21 registered targets in the Tiannara ProjectCompiler composition root. The recursive Git tree at the inspected commit contains 3,473 paths (not truncated) and exposes, at minimum, these distinct compiler families:

1. Root `compiler/` Universal Compiler API/kernel with its own registry and backend composition.
2. `constitutional_architecture/compiler/` Gen-C multi-pass pipeline with its own pass registry, backend registry and selector.
3. `tiannara/application/compiler/` ProjectCompiler with a separate capability-declaration registry, planner and executor.
4. `constitutional_architecture/compilers/` per-category compiler implementations (backend, frontend, database, deployment, documentation, infrastructure, operational, runtime policy and testing).
5. `autonomous-api/app/engine/` backend compiler/registry and frontend compiler/registry surfaces.

This is a minimum source-tree inventory, not a claim that every listed module is reachable from a production entrypoint. The tree also contains production backend modules, test fixtures, experiments, benchmarks, campaign tooling and generated-project infrastructure; these must be classified separately rather than counted as production backends by filename alone.

**Conclusion:** the 21-target ProjectCompiler registry is not a repository-wide compiler inventory. A single governed compilation authority has not been demonstrated. The independent compiler families and ISR/IR contracts remain distinct.

## 2. Source-confirmed execution surfaces

### 2.1 Tiannara ProjectCompiler — registered and CLI-reachable

**Source evidence**
- `tiannara/application/compiler/composition.py:24-49` imports the concrete target implementations.
- `composition.py:81-125` registers 21 concrete implementations: 12 backend/application targets and 9 frontend targets.
- `composition.py:136-198` constructs the ProjectCompiler. With no registry supplied, the current code calls `build_compiler_registry()` (line 191), which registers all 21 implementations.
- The docstring at `composition.py:161-165` says the omitted registry defaults to “FastAPIHexagonalBackend only”. That statement conflicts with the executable implementation at lines 81-125 and 191. This is a source-confirmed documentation/code inconsistency.
- `tiannara/interfaces/cli/main.py:8,136-137` routes the `create` command through `build_project_compiler(...)` and `compile_intent(...)`; lines 167-176 similarly construct and pass the compiler to the factory flow.
- `tiannara/application/compiler/project_compiler.py:95-145` shows intent compilation, typed SystemModel extraction, requirement derivation, backend planning and executor invocation.
- `project_compiler.py:143-164` verifies outcomes after executor invocation; it is not proof that every generated output is native-buildable or runtime-correct.

**Important behavior**
- `ProjectCompiler.taskflow_semantic_gate` defaults to `False` at `project_compiler.py:83-93`. The TaskFlow semantic-resolution check is therefore opt-in in this constructor path, not a universal mandatory gate.
- `selector.py:90-118,121-142` ranks and selects based on declared artifact kinds, declared capabilities and a quality-profile number. This establishes declaration-based planning, not proof that a backend actually realizes every declared semantic.
- `executor.py:55-83` invokes each selected backend's `generate(system_model)` and uses collect-all semantics. It records backend exceptions but does not itself enforce a zero-invocation policy after a later backend failure.
- `project_compiler.py:143-164` performs verification after execution. Therefore, a failed or unavailable post-generation verifier can block the final success result, but it cannot retroactively prevent backend invocation or artifact creation.

**Finding FS00-INV-001 — registry scope/documentation mismatch (Medium):** executable default composition registers 21 targets while the factory docstring describes a FastAPI-only default. Correct the authoritative documentation and ensure callers/tests assert the intended default registry. No code change is authorized by this finding.

**Finding FS00-INV-002 — declaration is not enforcement evidence (High):** selection trusts capability declarations before execution. Independent per-target tests must prove the implementation realizes each selected capability and rejects unsupported semantics before emission. The current source establishes the planner/executor path but not complete per-target semantic enforcement.

**Finding FS00-INV-003 — post-generation verification boundary (High):** ProjectCompiler invokes the executor before its verification loop. This is not an artifact quarantine/publication boundary. A later failed verifier does not prove zero backend invocation or zero generated output. Required acceptance: unsupported/invalid inputs rejected before execution; outputs remain quarantined until independent verification.

### 2.2 Root Universal Compiler API/kernel — separate API-reachable compiler family

**Source evidence**
- `compiler/api.py:26-36` creates a new BackendRegistry, registers a ReferenceBackend and calls `register_production_backends(registry)`.
- `compiler/api.py:39-55` constructs the FastAPI app and stores the compiler on app state.
- `compiler/api.py:115-150` exposes backend discovery, request validation and `POST /v1/compiler/compile`, which directly invokes `compiler.compile(payload)`.
- `compiler/api.py:166-169` defines the module-level ASGI app (previously confirmed in source inspection).
- `compiler/composition.py:9-13` separately builds a root core registry containing PythonFastAPIBackend, RustAxumBackend and AndroidStructuralBackend. This registry is not the same object or registration path as the API registry.
- `compiler/kernel.py:53-80` validates the ISR payload before backend resolution; invalid payloads fail before backend invocation.
- `kernel.py:81-113` resolves the requested backend and then invokes its `compile(context)`.
- `kernel.py:124-150` validates the output after backend invocation and packages valid output. This post-generation validation is not pre-invocation semantic equivalence or quarantine.
- `compiler/registry.py:21-45,61-96` allows backend instances or manifests to be registered and discovers them by manifest capability metadata. Manifest registration can store a placeholder object when no backend instance is supplied; discovery metadata must not be confused with an executable backend.

**Finding FS00-INV-004 — multiple root registries (High):** the root composition registry and API production registry are separate compositions with different registration sets. Their relationship, intended consumers and certification authority need an explicit inventory and common policy. Similar class names do not establish one registry or one authority.

**Finding FS00-INV-005 — API trust boundary unproven (High):** the compile route is source-confirmed, but authentication, authorization, tenant isolation, quotas, request bounds, artifact access control and deployment exposure are not established by these files. Deployment/gateway evidence is still required; absence of middleware in this app factory alone does not prove the deployed service is publicly exposed.

**Finding FS00-INV-006 — output validation is downstream (High):** the root kernel calls the backend before output validation and packaging. ISR syntax/schema validation is pre-invocation, but the inspected path does not establish complete requirement-to-output semantic verification before generation or a quarantine-before-publication guarantee.

### 2.3 Constitutional Gen-C compiler — multi-pass execution family

**Source evidence**
- `constitutional_architecture/compiler/pipeline.py:44-62` registers eight passes: validation, normalization, optimization, capability resolution, lowering, code generation, verification and cross-target.
- `pipeline.py:66-70,73-84` constructs a separate backend registry; its default registry contains FastAPIBackend only.
- `pipeline.py:87-175` runs the pass manager and returns a compilation result.
- `intent_entrypoint.py:50-125` provides a source-aware intent-to-constitutional-ISR entrypoint; it performs intent compilation, typed SystemModel checks, projection/source binding and then invokes the source-bound compiler pipeline.
- `validation_pass.py:20-118` fails closed for incomplete requirement-graph projections, missing required source binding, source-binding verification failure/unavailability and architecture projection errors.
- `validation_pass.py:120-145` handles the architectural type-checker failure path as an ERROR and unsuccessful PassResult, rather than a FATAL diagnostic.
- `pass_manager.py:17-58` stops later passes on FATAL diagnostics; ordinary unsuccessful passes mark the run unsuccessful but do not necessarily stop later passes.
- `code_generation_pass.py:54-89` adds a FATAL source-bound gate if any selected backend lacks `source_bound_codegen_certified is True`. The default FastAPI backend has not been shown to carry that certification flag.
- `code_generation_pass.py:94-120` calls backend validation, capability binding and compile; unsupported BIR features are recorded as warnings after compile rather than being an unconditional pre-invocation rejection.

**Finding FS00-INV-007 — validation failure can continue to code generation (High):** in the inspected type-checker exception/failure path, validation returns an unsuccessful result with ERROR diagnostics. PassManager continues after non-FATAL failures. Thus a later code-generation pass may still run. This is a narrower and more precise finding than saying all Gen-C source validation is fail-open: source-binding and projection gates are FATAL and stop the pipeline; the ordinary type-checker failure branch is the remaining continuation gap.

**Finding FS00-INV-008 — unsupported features detected after compile (High):** the code-generation pass invokes backend.compile before it calls report_unsupported. Unsupported BIR features therefore are not proven to be rejected before backend invocation/artifact emission. The source-bound certification gate is a useful narrow pre-invocation guard, but does not solve general capability enforcement.

**Finding FS00-INV-009 — source-bound backend authorization currently restrictive (High):** code-generation requires an explicit backend certification flag for source-bound input. The inspected default FastAPI backend does not establish that flag as true; source-bound code generation is therefore blocked for that backend unless another explicitly certified backend is supplied. This is a refusal boundary, not proof of a usable source-bound generation path.

### 2.4 Per-category compiler family — source-present, reachability not yet established

The tree includes the following implementation families:
- `constitutional_architecture/compilers/backend/` and `backend/fastapi/`;
- `compilers/frontend/react/`;
- `compilers/database/postgres/`;
- `compilers/deployment/cicd/`;
- `compilers/documentation/markdown/`;
- `compilers/infrastructure/terraform/`;
- `compilers/operational/intelligence/`;
- `compilers/runtime_policy/`;
- `compilers/testing/pytest/`.

The associated `base.py` interfaces and concrete modules establish source presence only. The recursive-tree audit has not yet established the production call chain, composition root, runtime selectors or artifact publication path for every category. Do not count these as additional production language/framework targets until invocation and consumer evidence is found.

**Finding FS00-INV-010 — category compiler reachability UNKNOWN:** source exists, but production reachability and lifecycle ownership remain unproven. Trace consumers, factories, dynamic imports and tests before assigning status.

### 2.5 Autonomous API compiler family — separate IR and registries

**Source evidence**
- `autonomous-api/app/engine/backend_compiler.py:1-75` defines a technology-neutral BackendProjectIR compiler contract and a TemplateBackendCompiler that emits skeletal component/config/error-contract files after IR validation.
- `autonomous-api/app/engine/backends.py:58-110` defines PythonFastAPIBackend; lines 114 onward define a separate Go/net/http backend. The Go backend declares `runtime_supported = False` at line 122, an explicit signal that generated Go source must not be represented as runtime-certified.
- `autonomous-api/app/engine/frontend_registry.py:33-53` stores target metadata/compiler pairs, validates FrontendProjectIR and invokes the selected compiler. This is a separate frontend registry and IR contract.
- The current inspected source confirms compiler classes and registry mechanics; the complete production route/consumer chain for all autonomous-api backends and frontend compilers has not yet been established.

**Finding FS00-INV-011 — parallel backend/frontend IR contracts (High):** autonomous-api has its own BackendProjectIR and FrontendProjectIR contracts and registries. Their semantic relationship to the canonical root ISR and other compiler IR families must be explicitly mapped. A technology-neutral label does not make these contracts equivalent.

**Finding FS00-INV-012 — generated source vs runnable target distinction (Medium):** at least one Go backend explicitly marks runtime support false. Its output can be source-generation evidence but cannot be counted as runtime-capable or certified without separate native build/runtime evidence.

## 3. Minimum compiler-family inventory at this checkpoint

| Family | Source present | Execution route established | Main trust/selection boundary | Certification status from this audit |
|---|---|---|---|---|
| Tiannara ProjectCompiler | Yes | CLI create/factory source route | capability declaration planner + executor | Not independently certified per target |
| Root Universal Compiler API | Yes | FastAPI compile endpoint | ISR payload validation + registry lookup | API route source-confirmed; deployment/security/runtime scope UNKNOWN |
| Root core compiler composition | Yes | Composition function exists; complete user route not established here | three-backend registry | Reachability UNKNOWN |
| Constitutional Gen-C | Yes | source-bound intent entrypoint and pipeline | eight-pass manager, backend selector | Semantic fail-closed gaps remain |
| Constitutional per-category compilers | Yes | Not yet established for every category | category-specific bases/factories unknown | Reachability UNKNOWN |
| autonomous-api backend family | Yes | Not yet established for every target | BackendProjectIR compiler boundary | Reachability/certification UNKNOWN |
| autonomous-api frontend family | Yes | Registry compile method source-confirmed; production route unknown | FrontendProjectIR registry | Reachability/certification UNKNOWN |

This table deliberately separates source presence from production reachability and certification. It is not an exhaustive backend list.

## 4. Cross-family conclusions

1. The repository contains multiple independent registries, selectors, compiler kernels, pass managers and intermediate representations. They do not yet demonstrate one governed compilation authority.
2. The ProjectCompiler's 21-target registry is only one family; it cannot be treated as the complete target inventory.
3. Capability declarations and manifests are metadata until independently proven to match implementation behavior.
4. In multiple families, verification occurs after backend generation. A failed final verdict does not by itself prevent generation or quarantine artifacts.
5. Gen-C has meaningful fail-closed source-binding/projection guards, but its ordinary architecture type-checker failure path and post-compile unsupported-feature detection remain gaps.
6. The root API and root core composition construct different backend registries. Their exact intended authority and relationship need to be resolved.
7. The per-category and autonomous-api compiler families need consumer/reachability tracing before they can be classified as production execution routes.
8. Frontend hardening remains a workstream milestone; no per-target frontend certification conclusion is made here. Backend hardening remains outstanding.

## 5. Next audit work

1. Complete consumer and dynamic-reachability tracing for all per-category compilers and autonomous-api registries.
2. Inspect every registered ProjectCompiler backend's capability declaration against its actual `generate()` implementation and refusal behavior.
3. Inspect root production backend registration and distinguish executable instances from manifest-only entries.
4. Trace all artifact writers, materializers, package/publish routes and identify whether verification precedes publication and whether quarantine is real.
5. Trace both Android implementations end-to-end, including their selectors, executor invocation, refusal tests and native build/runtime evidence.
6. Reconcile compiler-family and ISR-family authority with the accepted single-authority/single-ISR architectural direction.
7. Produce the exhaustive target/consumer/reachability/capability-preservation matrix before any implementation or disposition proposal.

## 6. Change-control boundary

This checkpoint is a source audit and documentation record only. It does not authorize implementation changes, ISR schema changes, registry convergence, backend deletion/retirement, FS-01, PR merge or FS-00 closure. All findings require independent review and may be revised if further call-chain or runtime evidence changes their scope.
