# Compiler Framework Audit Register

**Branch:** `hardening/candidate-bound-full-stack-gate`  
**Purpose:** Track evidence per compiler target. File emission or registry presence is not a build, runtime, security, semantic-correspondence, or certification pass.  
**Status key:** `P` = source inspected partially; `S` = source target/file identified but not deeply audited; `U` = not yet verified by evidence. All targets currently have `U` for independent verification of generated applications unless an execution record is linked below.

## Evidence dimensions

| Target | Source/config/deps | Build/install | Meaningful tests | Runtime/health | Security/auth | Semantic correspondence | Independent verification |
|---|---|---|---|---|---|---|---|
| React / TypeScript | P | P — generated-project install/build added to CI, pending | P — server-render test emitted; title encoded as data; CI pending | U | U | U | U |
| Vue / TypeScript | P | P — generated-project install/build added to CI, pending | P — mounted component test and Vite Vue plugin emitted; CI pending | U | U | U | U |
| Angular | P | P — generated-project install/build added to CI, pending | P — Vitest/TestBed test emitted; CI pending | U | U | U | U |
| Next.js | P | P — generated-project install/build added to CI, pending | P — page render test emitted; Vitest command corrected; CI pending | U | U | U | U |
| Nuxt | P | P — generated-project install/build added to CI, pending | P — Nuxt 4 app layout and mounted component test emitted; CI pending | U | U | U | U |
| Svelte | P | P — generated-project install/build added to CI, pending | P — Svelte 5 mount API and component test emitted; CI pending | U | U | U | U |
| Phoenix LiveView | S | U | U | U | U | U | U |
| Hologram | S | U | U | U | U | U | U |
| Scenic | S | U | U | U | U | U | U |
| Python / FastAPI | P | U | U — test suite presence is not generated-app execution evidence | U | U | U | U |
| Go / net/http | P | U | U — profile exists; generated behavior still needs execution proof | U | U | U | U |
| Rust / Axum | P | P — generated project passed `cargo test` and `cargo build --release` on the CI runner toolchain; pinned Rust 1.85 Docker build added and pending | P — two router-level integration tests passed (`/health` 200/body and unknown-route 404) | P — runner-side process not yet exercised; Docker runtime health/404 probes added and pending | U | U | U |
| TypeScript / Node / Express | P | U | P — current health test only checks a string; real HTTP behavior required | U | U | U | U |
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
4. **Next.js:** the build profile had a Jest-only `--runInBand` option despite using Vitest. It now invokes `npm test`. The root layout now imports `ReactNode` explicitly.
5. **Rust/Axum:** replaced the vacuous health test with router-level `/health` status/body and unknown-route 404 checks. The generated project passed `cargo test` (2 integration tests) and `cargo build --release` in CI on the runner’s stable Rust 1.99.1 toolchain. A separate Docker build using the generated `rust:1.85-slim` stage plus live container health/404 probes has now been added; its CI result is pending. Do not mark the pinned Rust 1.85 image verified until that run passes.
6. **Capability claims:** target manifests must be compared with executable operations. A manifest or Dockerfile alone does not establish security scanning, deployment, observability, or release capability.

## Certification rule

A target can be marked passed only when the exact generated candidate has evidence for dependency installation, production build, meaningful tests, runtime/health behavior, applicable security and authorization checks, source-to-IR semantic correspondence, and independent verification. Unsupported semantics must cause a structured rejection, not a partial-success status.

## CI snapshot

Latest fully completed validation head: `a62b7ff88a79e6e4dc614f8d9fe5ea1a7b3b79a6`. Compiler Certification Matrix and Compiler Source Quality passed on that head. The generated Rust project passed host-toolchain `cargo test` and `cargo build --release`; the two router-level tests passed. The actual `rust:1.85-slim` Docker build and live container probes are now in the matrix workflow but have not yet completed. The runner prerequisite gate and regression tests, six generated frontend install/test/production-build checks, Angular entrypoint/test config fixes, and removal of unsupported frontend manifest claims were added afterward. Current branch head `886061cdb26366c6e5a5974ddfdd0fba0be1baa0` has CI queued. CBC-1 Campaign A failed on the last fully completed head: 78/78 evidence records formed a valid hash chain, but 0/78 trials were certified because the source-bound semantic gate remained blocked. This is not a production certification pass.
