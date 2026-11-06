# FS-00 Checkpoint 6 — Verification and Native-Execution Evidence Audit

**Audit class:** read-only source + GitHub Actions evidence audit  
**Audited branch head:** `bc7de4ceed007406810224f880206709d48620b9`  
**PR:** #201, head `bc7de4c`, base `remediation/w12-executable-effect-contract`  
**Scope:** generated-candidate tests, static checks, native build/test/runtime stages, CI triggers, execution logs, evidence binding and certification boundaries.  
**Change boundary:** documentation only. No production code, tests, workflows, schemas, backend declarations or evidence records were changed.

## 1. Executive result

The repository contains meaningful native-execution and behavioral-test infrastructure, but coverage is uneven across compiler families and targets. Several tests exercise real generated applications; several other tests only inspect generated text, manifests, declarations or mocked command results. Those categories must not be conflated.

The most important current-run fact is:

- The latest Actions run associated with audited head `bc7de4ceed007406810224f880206709d48620b9` is run **41913400154**.
- Its `android-backend-tests` job passed; the job log records **11 passed in 0.40s**.
- Its `android-cloud-build` job was **skipped**, because that job runs only for `workflow_dispatch`; the pull-request event executes the backend contract job only.
- No Compiler Certification Matrix run is attached to this audited head. The matrix workflow is configured for pull requests targeting `main`, while PR #201 targets `remediation/w12-executable-effect-contract`. The current head therefore has no current-run evidence from that matrix.
- An earlier Compiler Certification Matrix run on branch commit `6b5f3e5dcc8e1d22cbe1ab184f734ec486f701f5` failed during the generated Angular production build. The failure included unresolved `@angular/forms`, TypeScript `never` assignment errors and Angular imports diagnostics. No later matrix run for the audited head was found to establish a corrected result.

The current evidence supports **partial target-specific engineering progress**, not universal compiler certification, not all-language runtime support, and not Android benchmark certification.

## 2. Evidence vocabulary

| Evidence class | What it establishes | What it does not establish |
|---|---|---|
| Unit / source-shape test | Specific functions, emitted files, declarations, refusals or deterministic output match assertions | That generated code compiles or runs |
| Static bundle verification | Required files, syntax/structure, import direction or documentation constraints pass | Correct behavior or a successful native toolchain build |
| Native build | Compiler/toolchain accepted generated source and produced build output | Correct application semantics or runtime behavior |
| Generated unit / integration tests | Executed tests against the generated candidate | Production deployment, external integration or full requirement coverage |
| Container / HTTP smoke | Candidate starts in a container and selected HTTP behavior is observed | Full product correctness, security or production operations |
| Emulator/device execution | Candidate installs and launches in a controlled Android environment | Complete Android product behavior or benchmark acceptance |
| Independent semantic certification | Independently reviewed requirement-to-behavior preservation with bound evidence | Must not be inferred from any of the above alone |

## 3. Latest audited-head GitHub Actions evidence

### 3.1 Run 41913400154

Workflow: **ESAP Android Cloud-Build Certification (Stage A)**  
Event: pull request  
Reported head SHA: `bc7de4ceed007406810224f880206709d48620b9`  
Conclusion: workflow run `success`.

Jobs:

| Job | Result | Evidence |
|---|---|---|
| `android-backend-tests` | **success** | Installs Python dependencies and runs `tests/test_android_campaign_backend.py` plus `tests/test_android_structural_runner.py`; log summary: 11 passed in 0.40s |
| `android-cloud-build` | **skipped** | Workflow condition requires `github.event_name == 'workflow_dispatch'`; it does not run for this PR event |

The checkout log uses GitHub's PR merge ref `dffb42de922b6418b7d33006a3852abd161a7fa6`, which merges audited head `bc7de4c` into base `719580d4...`. The Actions run's reported `head_sha` remains `bc7de4c`. This is normal PR merge-ref testing, but the exact merge commit and head commit are distinct identifiers.

**Interpretation:** the 11 tests establish contract and runner behavior. They do not establish a real Gradle build or emulator execution on this run.

### 3.2 Trigger coverage gap

The `compiler-certification-matrix.yml` workflow uses `pull_request.branches: [main]`. PR #201's base is `remediation/w12-executable-effect-contract`, so this workflow is not triggered by the current PR target. It also has path filters. Its substantial generated frontend, Express and Rust execution steps are therefore not represented in the latest run for this audit head.

The `compiler-source-quality.yml` workflow also targets pull requests to `main`; it is not evidence for this current PR head.

The Autonomous API `ci-cd.yml` workflow targets pushes to `main`/`develop` and pull requests to `main`; it is likewise not evidence from the current PR head.

A workflow definition is an execution plan, not an execution result. Only an actual run bound to a commit, with successful job steps and inspectable logs, can establish CI evidence.

## 4. Compiler-family and target evidence inventory

### 4.1 Tiannara ProjectCompiler backend-service targets

The ProjectCompiler registry has backend-specific tests for FastAPI Hexagonal, Go Hexagonal, Rust Axum, NestJS, Spring Boot, ASP.NET Core, Express, Ktor, Phoenix, Laravel and Rails.

Evidence levels differ:

- **FastAPI Hexagonal:** backend tests inspect generated layout, manifests, source syntax and behavior. Runtime-focused tests and calibration infrastructure exist. The test suite includes real generated FastAPI app execution in some paths, but that must be distinguished from ordinary unit tests and from the latest PR run.
- **Go Hexagonal:** backend tests inspect emitted Go structure and profile commands. The profile declares `go build ./...` and `go test ./...`; a declaration or unit assertion of those commands is not evidence that Go ran on the audited head. The compiler matrix workflow has a Go toolchain setup in some test paths, but no run is attached to this head.
- **Rust Axum:** backend tests inspect generated Cargo project structure and health-test source. The compiler matrix workflow contains real `cargo test`, release build, Docker image build and HTTP health/404 smoke steps for a generated Rust target. These are meaningful planned execution checks, but no matrix run exists for the audited head.
- **Express:** the compiler matrix workflow generates an Express candidate, installs dependencies, runs tests/build, builds a Docker image, starts a container, checks `/health` and verifies unknown-route 404. No matrix run exists for the audited head.
- **NestJS, Spring Boot, ASP.NET Core, Ktor, Phoenix, Laravel and Rails:** target-specific backend tests exist, but the inspected compiler matrix workflow does not establish the same broad native build/container/runtime path for every one of these targets. Static source generation or unit-test success must not be promoted to native runtime certification.

### 4.2 ProjectCompiler calibration harness

The Phase-31 BackendCalibrationHarness has a useful fail-closed model:

1. derive requirements from each SystemModel;
2. select all suitable registered backend-service targets;
3. generate each candidate into a backend-specific output directory;
4. run backend-specific static verification;
5. run the backend's test command when a runtime image/container or local toolchain is available;
6. record PASS only when static verification and runtime execution both pass;
7. record missing toolchain or runtime errors as skips, and skips fail the calibration gate.

The gate semantics explicitly say that a skipped runtime is unverified and cannot count as passed.

However, `tests/test_phase31_calibration.py` deliberately monkeypatches tool discovery so Go and Git are absent. It asserts static verification passes while the overall calibration success rate remains zero and the runtime is skipped. This is a strong test of honest failure semantics, **not** evidence of Go runtime success.

The calibration evidence object records project ID, ISR hash, genome ID, backend name, compilation/test result, fitness, verdict and error. The inspected record construction does not itself bind:
- repository source commit SHA;
- backend implementation/version digest;
- generated artifact manifest hash or per-file hashes;
- test-log/output hash;
- toolchain/container image digest.

The JSONL ledger is hash-chained, which protects ledger ordering/integrity, but hash chaining alone does not supply the missing provenance fields.

### 4.3 Root campaign-native Python and Rust targets

`tests/integration/test_generated_backend_behavior_builds.py` creates generated Python FastAPI and Rust Axum repositories and executes real dependency installation and tests. The Python scenarios include authorization, non-mutation on denial, executable effect contracts, replay/idempotency and concurrency. Rust uses `cargo test`.

These are materially stronger than source-shape assertions. They are still bounded test fixtures and not proof of arbitrary ISR coverage or production deployment. The test file's existence does not establish that it ran on the current PR head; no matching current-head workflow result was found in the latest run inventory.

### 4.4 Root Universal Compiler API (Gen-A)

`tests/test_compiler_runtime.py` uses FastAPI TestClient to exercise `POST /v1/compiler/compile` with the ReferenceBackend, checks invalid ISR rejection and verifies artifact files plus manifest are written.

This proves the API/kernel/packager path works for the reference backend in its test fixture. It does not prove all production backends are behaviorally equivalent or that generated production apps pass native runtime tests. The ReferenceBackend test is not a proxy for every registered production backend.

### 4.5 Constitutional Gen-C

The source-bound integration workflow runs tests for intent compilation, projection, source binding, entrypoint and backend-certification refusal. The dedicated certification-gate tests verify an uncertified backend is blocked before `compile()`, emits no artifacts, and cannot bypass the gate through legacy configuration, source graph presence or explicit binding.

This is valuable governance evidence. It verifies a refusal boundary; it is not evidence that Gen-C has an enabled, independently certified source-bound backend that successfully builds and runs an application. The current default backend must remain blocked unless its source-bound semantic certification is independently established.

### 4.6 Autonomous API compiler family

The Autonomous API `ci-cd.yml` defines:
- unit test matrix across Python 3.11, 3.12 and 3.13;
- Go backend-neutral/evolution tests with Go 1.27;
- a generated Go runtime test;
- Docker image build/smoke on main;
- a containerized circuit-breaker runtime test.

These workflows target main/develop and pull requests to main. They do not establish current PR #201 head evidence. They also exercise the Autonomous API application/evolution compiler family, not the ProjectCompiler's 11 backend-service targets or the Gen-A API registry. Evidence must remain family-specific.

### 4.7 Frontend targets

The compiler certification matrix workflow defines generated frontend execution for React, Vue, Angular, Next, Nuxt and Svelte: generate candidate, install dependencies, run generated tests and production build.

The separate generated React frontend certification workflow goes further: build, unit tests, Playwright Chromium E2E, record evidence from build/unit/E2E logs, certify and upload the evidence JSON plus logs.

The workflow definitions provide a credible testing design. They do not prove a passing result for every target at the audited head. The earlier Angular failure below is a concrete counterexample to treating generation or unit tests as build success.

## 5. Android evidence — keep implementations separate

### 5.1 ProjectCompiler Android backend

`tests/test_android_backend.py` checks registration, declared BUILD/DOCUMENTATION capabilities, deterministic output, expected Android project files and refusal of service/API/event semantics. This is static generation/contract evidence. It does not invoke Gradle, inspect an APK or launch an emulator.

### 5.2 Campaign-native AndroidStructuralBackend

`tests/test_android_campaign_backend.py` checks protocol identity, structural classification, deterministic candidate output, conformance, refusal of unsupported semantics and ISR-to-plan-to-candidate hashes.

`tests/test_android_structural_runner.py` checks the runner's stage ordering, hash binding, failure behavior and mandatory source/plan hashes. Its successful tests inject a fake command runner and synthesize a ZIP/APK fixture. These tests prove runner logic and fail-closed handling; they do not execute the Android SDK or emulator.

The runner's verdict is deliberately `STRUCTURAL_CHECKS_ONLY`. It does not upgrade the backend from STRUCTURAL to BEHAVIORAL/PRODUCTION.

### 5.3 Android cloud workflow

The manual `workflow_dispatch` path is significantly stronger. It:
- checks out the exact requested source revision;
- validates the benchmark specification, serialized ISR revision and approved derivation manifest;
- verifies source-spec, ISR-file and derivation-manifest SHA-256 values plus ISR content hash;
- configures Java 17, Android API 35/build-tools 35.0.0, Gradle 8.9 and an x86_64 emulator;
- recompiles the campaign-native candidate from the ISR revision;
- checks revision, plan and repository hashes;
- executes Gradle build, APK inspection, emulator install and launch;
- records APK hash and per-stage evidence;
- uploads the candidate and evidence.

The workflow explicitly preserves the verdict `STRUCTURAL_CHECKS_ONLY` and states that ESAP-APP-001 remains BLOCKED unless independent semantic and runtime acceptance gates are separately satisfied.

This is the correct evidence boundary. But on the latest audited-head PR run, the manual cloud-build job was skipped. No successful manual-dispatch run bound to the audited head was found in the inspected run inventory. Therefore this checkpoint does **not** claim an actual APK or emulator result for `bc7de4c`.

The workflow is for the campaign-native Android implementation. It does not certify the separate ProjectCompiler Android backend.

## 6. Historical negative CI evidence — Angular

The branch's earlier Compiler Certification Matrix run **41492567772**, associated with commit `6b5f3e5dcc8e1d22cbe1ab184f734ec486f701f5` on 2026-11-02, failed in the step “Generate, install, test, and production-build frontend targets”.

The generated Angular production build reported:
- could not resolve `@angular/forms`;
- TypeScript `TS2307` missing module/type declarations;
- multiple `TS2322` errors assigning strings to `never`;
- Angular `NG1010` imports-array diagnostics;
- `TS2339` `toLowerCase` unavailable on `never`.

The earlier run's compiler matrix resolution passed before the frontend build failed. This demonstrates why selection/registry tests cannot stand in for a native frontend build.

This is historical evidence, not a claim that the audited head necessarily has the same defect. But no later matrix run for the audited head was found to demonstrate that Angular now builds. The issue remains **UNVERIFIED at the current head**, not PASS and not necessarily still FAIL.

## 7. Source-revision and artifact binding assessment

| Evidence source | ISR / requirement binding | Source commit binding | Backend version binding | Artifact hash binding | Test/log hash binding |
|---|---|---|---|---|---|
| ProjectCompiler calibration ledger | ISR content hash present | Not present in inspected evidence constructor | Backend ID present; implementation version digest not present | Not present in inspected evidence constructor | TestRun object may carry result; explicit output/log hash not present in record constructor |
| ProjectCompiler materialization manifest | ISR hash and generated file inventory are present in report/materialization flow | Source commit is not established as a required manifest field by the inspected path | Backend ID/capability metadata; immutable implementation digest not established | File list/provenance exists; per-file content hashes are not established as a universal required contract in this path | Not established |
| Gen-A artifact manifest | Input/job/backend metadata and per-artifact SHA-256 are written by packager | Source commit not shown as a required compile-request binding | Backend ID/version is requested; immutable backend implementation digest not established | Yes, per artifact | Build/test log binding not established in kernel/packager |
| Gen-C source-bound gate | Source graph and binding checks exist | Exact source revision may be present in source-binding inputs, but complete generated artifact provenance not established | Certification flag is checked; backend implementation digest not established | No complete published artifact evidence for default source-bound path | Not established |
| Android manual cloud workflow | Yes: source spec, ISR revision, derivation manifest, ISR content hash | Yes: exact source revision checkout | Backend source revision is pinned by checkout; separate signed backend identity digest not shown | Yes: repository candidate hash and APK SHA-256 | Stage outputs hashed; evidence JSON uploaded; logs are not all separately represented as a signed log bundle in the shown workflow |
| Generated React frontend workflow | Generated candidate is rebuilt and evidence is recorded from exact candidate | Workflow checkout commit is implicit in run; explicit commit field in evidence format needs verification | Compiler source revision is implicit in checkout; explicit compiler implementation digest needs verification | Certification script hashes generated source/candidate according to its own contract; per-file manifest semantics require separate audit | Build/unit/E2E logs are inputs to evidence recording and uploaded |

**Conclusion:** evidence binding is strongest in the Android manual campaign and newer frontend certification workflows, but no repository-wide provenance schema enforces the same fields for every backend family. A hash-chained ledger is not a substitute for source revision, backend identity/version, artifact hashes and execution-log hashes.

## 8. Findings

### FS00-VER-001 — Current audited head has no broad compiler-matrix execution evidence
**Severity:** High  
The latest run associated with `bc7de4c` ran Android backend contract tests only. The Compiler Certification Matrix is not triggered for PR #201's non-main base branch. Broad generated frontend, Express and Rust execution steps are not evidenced for this head.

### FS00-VER-002 — Android contract test success is not Android cloud-build success
**Severity:** Critical evidence classification  
11 campaign backend/runner tests passed, but the cloud build job was skipped. The successful workflow conclusion must not be reported as a successful APK build or emulator launch.

### FS00-VER-003 — ProjectCompiler backend coverage is uneven
**Severity:** High  
Backend-specific tests exist for all 11 service backends, but many primarily assert output structure, declarations or refusal behavior. Strong native execution is concentrated in selected targets/workflows; equivalent runtime evidence is not demonstrated for every registered backend.

### FS00-VER-004 — Calibration harness correctly fails closed when runtime toolchains are absent
**Severity:** Positive control  
The harness refuses to count static-only verification as success and records missing toolchains as skipped/unverified. Its hermetic tests intentionally produce zero certification passes when Go is absent. Preserve this rule.

### FS00-VER-005 — Historical Angular native build failure remains unresolved at current head
**Severity:** High  
The earlier matrix run failed the Angular production build. The current head has no later compiler-matrix run establishing a fix. Status is UNKNOWN at `bc7de4c`, not PASS.

### FS00-VER-006 — Test coverage does not uniformly prove requirement semantics
**Severity:** Critical capability gap  
Generated health endpoints, API smoke tests, structural shell checks and generic test templates do not prove that arbitrary ISR operations, security policies, invariants, events, data persistence and business workflows are preserved. Tests need independent requirement-derived oracles, not only generator-derived expectations.

### FS00-VER-007 — Evidence provenance is not uniform across compiler families
**Severity:** Critical governance gap  
The calibration ledger records ISR hash and backend ID but does not establish source commit, immutable backend implementation digest, generated artifact hash and test-log hash as required evidence fields. Gen-A, Gen-C, Android and frontend paths each use different evidence shapes.

### FS00-VER-008 — Android structural runner is intentionally not behavioral certification
**Severity:** Positive control / boundary  
The runner records source/plan/repository/APK hashes and executes Gradle/APK/emulator stages when actually invoked, but its verdict remains STRUCTURAL_CHECKS_ONLY. Preserve the class boundary.

### FS00-VER-009 — Workflow triggers do not guarantee audit-branch coverage
**Severity:** High CI architecture gap  
Several broad workflows target `main` only. PRs targeting integration/remediation branches can bypass them even when relevant compiler code is present in the PR history. Critical compiler verification should be required by explicit reusable workflows or branch-independent required checks, not accidental path/target matching.

### FS00-VER-010 — Passing API kernel tests use the reference backend
**Severity:** Medium  
The Gen-A runtime API tests demonstrate API/packaging behavior with ReferenceBackend. They do not establish equivalent behavior for each production backend registered by the API composition root.

## 9. Required remediation direction (not implemented in FS-00)

1. Establish a branch-independent compiler certification workflow callable by every PR target branch and pinned to the exact PR merge/head SHA.
2. Add per-backend execution tiers to the certification matrix: generation, static verification, native build, generated unit tests, independent behavioral tests, container execution, HTTP contract tests and deployment/emulator checks where applicable.
3. Do not require every backend to support the same toolchain locally. Use pinned, reproducible toolchain containers or runners, and record honest skips as UNKNOWN/FAIL for certification.
4. Repair and rerun the Angular generated production build; retain the historical failure in the evidence ledger and require a new exact-head successful run before upgrading status.
5. Expand native build/runtime coverage for NestJS, Spring Boot, ASP.NET Core, Ktor, Phoenix, Laravel and Rails. Do not infer it from FastAPI, Go, Rust or Express results.
6. Add independent requirement-to-oracle suites for API operations, authorization, effects, pre/postconditions, idempotency, events, persistence, invariants and failure/recovery behavior.
7. Standardize an immutable evidence envelope requiring source commit SHA, source/ISR content hash, approved derivation manifest hash, backend ID and implementation digest, toolchain/container digest, candidate manifest/per-file hashes, test commands, exit codes, log hashes, verdict and signer identity.
8. Keep Android ProjectCompiler and campaign-native Android evidence separate. Trigger manual Android cloud execution explicitly when a candidate is ready; a skipped job remains UNKNOWN.
9. Keep Gen-C's source-bound backend gate closed until a backend passes independent semantic certification and bound native/runtime evidence.
10. Make the promotion gate consume only evidence bound to the exact candidate and requirements. Do not let a green workflow aggregate override a skipped critical job or a structural-only verdict.

## 10. Evidence inspected

### Current revision source files
- `.github/workflows/compiler-certification-matrix.yml`
- `.github/workflows/compiler-source-quality.yml`
- `.github/workflows/android-cloud-build-certification.yml`
- `.github/workflows/generated-frontend-certification.yml`
- `.github/workflows/source-binding-integration-focused.yml`
- `.github/workflows/ci-cd.yml`
- `tests/certification/test_compiler_matrix_certification.py`
- `tests/certification/test_compiler_source_quality.py`
- `tests/integration/test_generated_backend_behavior_builds.py`
- `tests/test_android_backend.py`
- `tests/test_android_campaign_backend.py`
- `tests/test_android_structural_runner.py`
- `tests/test_source_bound_backend_certification_gate.py`
- `tests/test_phase31_calibration.py`
- `tests/test_r24_fastapi_runtime.py`
- `tests/test_rust_axum_typed_backend.py`
- `tests/test_compiler_runtime.py`
- `tiannara/application/harness/calibration/harness.py`
- `certification/campaign/android_structural_runner.py`
- `compiler/core/protocol.py`

### GitHub Actions records
- Current-head run: [41913400154](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/41913400154)
- Current-head Android backend job: [126866585718](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/41913400154/job/126866585718)
- Current-head Android cloud-build job (skipped): [126866588323](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/41913400154/job/126866588323)
- Historical Angular compiler-matrix failure: [41492567772](https://github.com/Kimiti4/autonomous-API-Gen/actions/runs/41492567772)

## 11. Non-claims and audit limits

- This checkpoint inspected source, workflow definitions and GitHub Actions run metadata/logs. It did not rerun repository tests or toolchains.
- Only the exact current-head run and the cited historical matrix failure are treated as executed evidence.
- Workflow definitions, tests in source, test mocks and command declarations are not treated as actual successful native execution.
- No claim is made that all backends build, all generated applications work, Android is certified, or universal semantic preservation is achieved.
- No production code or tests were changed.

## 12. Next checkpoint

**Checkpoint 7 — requirement-oracle independence and semantic-preservation audit.**

Trace whether generated tests and acceptance oracles are independently derived from the authoritative requirements/ISR or merely mirror generator templates. Audit API operations, authorization, effects, invariants, events, persistence, failure/retry/idempotency and frontend interactions across backend targets. Identify vacuous tests, circular test oracles, missing negative cases and semantics lost between ISR → plan/IR → generated code → runtime assertions. Preserve the rule that UNKNOWN is not PASS. FS-00 remains open.
