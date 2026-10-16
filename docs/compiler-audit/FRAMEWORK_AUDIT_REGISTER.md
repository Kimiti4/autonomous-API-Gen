# Compiler Framework Audit Register

**Branch:** `hardening/candidate-bound-full-stack-gate`  
**Purpose:** Track evidence per compiler target. File emission or registry presence is not a build, runtime, security, semantic-correspondence, or certification pass.  
**Status key:** `P` = source inspected partially; `S` = source target/file identified but not deeply audited; `U` = not yet verified by evidence. All targets currently have `U` for independent verification of generated applications unless an execution record is linked below.

## Evidence dimensions

| Target | Source/config/deps | Build/install | Meaningful tests | Runtime/health | Security/auth | Semantic correspondence | Independent verification |
|---|---|---|---|---|---|---|---|
| React / TypeScript | P | P — dependency install and production build passed in CI on `dc41c92`; re-run after latest Angular fixes pending | P — server-render test passed in CI on `dc41c92` | U | U | U | U |
| Vue / TypeScript | P | P — dependency install and production build passed in CI on `dc41c92` | P — mounted-component test passed in CI on `dc41c92` | U | U | U | U |
| Angular | P | P — dependency installation passed in the 2026-10-16 matrix; production build pending after test fix | P — live TestBed/Vitest execution reached the component assertion and exposed a mismatch between the generated model title and the test expectation; generator now asserts the model-derived title, rerun pending | U | U | U | U |
| Next.js | P | P — generated-project install/build added to CI, pending | P — page render test emitted; Vitest command corrected; CI pending | U | U | U | U |
| Nuxt | P | P — generated-project install/build added to CI, pending | P — Nuxt 4 app layout and mounted component test emitted; CI pending | U | U | U | U |
| Svelte | P | P — generated-project install/build added to CI, pending | P — Svelte 5 mount API and component test emitted; CI pending | U | U | U | U |
| Phoenix LiveView | S | U | U | U | U | U | U |
| Hologram | S | U | U | U | U | U | U |
| Scenic | S | U | U | U | U | U | U |
| Python / FastAPI | P | U | U — test suite presence is not generated-app execution evidence | U | U | U | U |
| Go / net/http | P | U | U — profile exists; generated behavior still needs execution proof | U | U | U | U |
| Rust / Axum | P | P — generated project passed `cargo test` and `cargo build --release` on the CI runner toolchain; pinned Rust 1.85 Docker build added and pending | P — two router-level integration tests passed (`/health` 200/body and unknown-route 404) | P — runner-side process not yet exercised; Docker runtime health/404 probes added and pending | U | U | U |
| TypeScript / Node / Express | P | P — generated install/build/container execution added to CI, pending | P — live ephemeral-port HTTP tests for `/health` JSON and unknown-route 404 emitted; CI pending | P — container health/404 probes added, pending | U | U | U |
| TypeScript / Node / NestJS | S | U | U | U | U | U | U |
| Java / Spring Boot | S | U | U | U | U | U | U |
| C# / ASP.NET Core | S | U | U | U | U | U | U |
| Elixir / Phoenix | S | U | U | U | U | U | U |
| Kotlin / Ktor | S | U | U | U | U | U | U |
| PHP / Laravel | S | U | U | U | U | U | U |
| Ruby / Rails | S | U | U | U | U | U | U |

## Priority findings

1. **Candidate identity:** the Campaign A runner previously passed different digests to the candidate-bound full-stack and semantic verifiers. The runner now uses the canonical generated-repository hash as the candidate identity for all verification gates; source/IR provenance remains a separate evidence dimension.
2. **Prerequisites and cleanup:** the trial workspace is removed in a `finally` block. Real build execution is now skipped unless both structural and semantic conformance explicitly pass; a regression test asserts the builder is never called for a non-conformant candidate. CI validation is pending.
3. **Campaign semantic projection:** authoritative PlanArtifacts are snapshotted, but the deterministic mapping producer correctly blocks when typed source semantics do not express the required frontend, API, backend, effect, and consequence obligations. No fabricated mapping is accepted.
4. **Next.js:** the build profile had a Jest-only `--runInBand` option despite using Vitest. It now invokes `npm test`. The root layout imports `ReactNode` explicitly. React, Vue, Angular, Next.js, Nuxt, and Svelte generated-project install/test/production-build execution is now wired into CI; results are pending. Unsupported lint/static-analysis/security-scan/release claims were removed from these frontend manifests. The Angular target now emits an index file and a separate spec TypeScript configuration for the modern Angular unit-test builder.
5. **Rust/Axum:** replaced the vacuous health test with router-level `/health` status/body and unknown-route 404 checks. The generated project passed `cargo test` (2 integration tests) and `cargo build --release` in CI on the runner’s stable Rust 1.99.1 toolchain. A separate Docker build using the generated `rust:1.85-slim` stage plus live container health/404 probes has now been added; its CI result is pending. Do not mark the pinned Rust 1.85 image verified until that run passes.
6. **Capability claims:** target manifests must be compared with executable operations. A manifest or Dockerfile alone does not establish security scanning, deployment, observability, or release capability. Express now uses a real ephemeral-port HTTP test harness and no longer advertises unimplemented lint, static-analysis, security-scan, deploy, observability, or release operations.

## Certification rule

A target can be marked passed only when the exact generated candidate has evidence for dependency installation, production build, meaningful tests, runtime/health behavior, applicable security and authorization checks, source-to-IR semantic correspondence, and independent verification. Unsupported semantics must cause a structured rejection, not a partial-success status.

## CI snapshot

Latest fully completed validation head: `a62b7ff88a79e6e4dc614f8d9fe5ea1a7b3b79a6`. Compiler Certification Matrix and Compiler Source Quality passed on that head. The generated Rust project passed host-toolchain `cargo test` and `cargo build --release`; the two router-level tests passed. The actual `rust:1.85-slim` Docker build and live container probes are now in the matrix workflow but have not yet completed. The runner prerequisite gate and regression tests, six generated frontend install/test/production-build checks, Angular entrypoint/test config fixes, Express live HTTP/container checks, unsupported capability-claim removals, and a stale semantic-binding mutation test were added afterward. Current CI results for these changes are pending; the workflows have been repeatedly queued and have not yet completed on the latest branch head. CBC-1 Campaign A failed on the last fully completed head: 78/78 evidence records formed a valid hash chain, but 0/78 trials were certified because the source-bound semantic gate remained blocked. This is not a production certification pass.


## Latest execution findings (2026-10-16)

- The first live generated-frontend matrix reached the React production build after installing dependencies and passing its component test, then failed at TypeScript declaration checking. The generated project lacked Node type declarations and did not skip incompatible third-party declaration checks (Disposable, Node built-ins, Buffer, and related symbols).
- React and Vue generated projects then passed dependency installation, meaningful component tests, and production builds in the live matrix. Corrective changes also added Node typings to Svelte and Nuxt manifests; those targets have not yet been reached by the sequential matrix.
- The 2026-10-16 compiler-matrix run reached Angular after React and Vue passed, then failed because `angular.json` referenced `tsconfig.spec.json` but the generator did not emit that file. The generator now emits `tsconfig.spec.json` using its existing `_tsconfig_spec()` definition, and the regression test asserts the generated file content. This is a source-level correction only; the next live generated-project test/build run must confirm it.
- Existing cleanup tests cover workspace removal after a conformance exception, path-traversal rejection, and container destruction after a failed deployment health gate. They are in the compiler matrix's required test command, but the latest run has not completed them because the frontend execution step failed first.
- The exact candidate hash is recomputed from sorted generated file contents by semantic correspondence verification, and the runner rejects mismatched candidate hashes from either verification gate. The canonical full-stack IR verifier independently checks cross-layer coherence/effect consequences; it does not substitute for build, runtime, or security tests.
- Current Stage 1 blocker remains source-semantic completeness: the production mapping producer intentionally refuses to publish the five-layer mapping while authoritative PlanArtifacts/ISR do not explicitly encode required frontend routes, API operation contracts, enforcement policies, effects, and consequences. That blocker must be resolved by enriching authoritative source artifacts and loss-checked lowering—not by inventing a mapping.

- Most recent generated-frontend execution detail: React and Vue are now demonstrated install/test/build passes on commit `dc41c92acf4976c46e265e38dd7ad0d2eeb0f1fb`; Angular's first real execution exposed a configuration defect, which has been corrected in `556026985de057dfdb92e9438bbbc689a5a87478` and covered by a follow-up regression test. The current full matrix is pending on the later branch head.

- NestJS source audit found the generated package omitted `@nestjs/platform-express`, lacked explicit Jest TypeScript configuration, and used a tautological route-string test. The compiler now emits the runtime adapter, a `ts-jest` configuration, and a controller behavior test; unsupported lint/static-analysis/security/deploy/observability/release manifest claims were removed. Targeted generation tests were added; a real NestJS dependency install/build/runtime job is not yet in the execution matrix.
- Spring Boot source audit found a tautological `assertTrue(true)` test, duplicate `pom.xml` in required files, multi-model output that could create multiple public classes in one Java file, and a fake `mvnw` script that merely delegated to a locally installed Maven. It now emits one Java file per model, a MockMvc `/health` response test, corrected required-file declarations, and a real Maven builder stage; unsupported manifest claims were removed. These changes await CI and generated-project execution.
- A source inspection found that the Svelte/Vite generator emitted `src/main.ts` and a Vite config but no `index.html` entry document, which a normal Vite production build requires. The generator now emits the HTML entrypoint and includes it in the build profile's required files; regression tests assert the entrypoint and its module script. This is a proactive source-level correction, not yet validated by generated-project CI execution.
- The 2026-10-16 compiler-matrix run failed in Angular's generated component test with `NG0908: In this configuration Angular requires Zone.js`. The generated package already declared `zone.js`, but the test did not import it; the component test now explicitly imports `zone.js`, with a regression assertion. This remains pending live rerun.

- The latest live matrix run (2026-10-16, head `829bba43`) passed React and Vue install/test/build, and Angular's setup now progressed through dependency installation and test startup. It then exposed a test-fixture mismatch: the generated Angular component correctly rendered the model-derived title `ESAP Frontend CI Smoke`, while its test incorrectly expected the literal `Generated application` in the heading. The generator now binds the heading assertion to the actual `SystemModel.system_name` and keeps the separate body assertion for the generated-application marker; a source regression assertion covers this binding. This is a source fix, not a verified runtime pass; the next matrix run must validate it and continue to Next.js, Nuxt, and Svelte.

- Follow-up to the 2026-10-16 matrix result for head `22873578`: Angular's next test execution failed at TypeScript parsing, before component assertions. The emitted spec contained literal backslash-n sequences instead of actual line breaks because the Python source string was over-escaped. Corrected the generator to emit newline characters. This is the currently targeted defect; Angular is not certified until a fresh generated-project run passes.

- The subsequent matrix run confirmed that real newline emission was corrected, but exposed one additional generated-spec syntax defect: an extra closing brace after the test callback. Removed the extra brace and restored the complete `describe(...)` closure. This latest correction is pending fresh matrix execution; no Angular pass is claimed.
