# Compiler Framework Audit Register

**Branch:** `hardening/candidate-bound-full-stack-gate`  
**Purpose:** Track evidence per compiler target. File emission or registry presence is not a build, runtime, security, semantic-correspondence, or certification pass.  
**Status key:** `P` = source inspected partially; `S` = source target/file identified but not deeply audited; `U` = not yet verified by evidence. All targets currently have `U` for independent verification of generated applications unless an execution record is linked below.

## Evidence dimensions

| Target | Source/config/deps | Build/install | Meaningful tests | Runtime/health | Security/auth | Semantic correspondence | Independent verification |
|---|---|---|---|---|---|---|---|
| React / TypeScript | P | U | P — render test emitted; latest CI pending | U | U | U | U |
| Vue / TypeScript | P | U | P — mounted component test emitted; latest CI pending | U | U | U | U |
| Angular | S | U | U | U | U | U | U |
| Next.js | P | U | P — render test emitted; build-profile command corrected, latest CI pending | U | U | U | U |
| Nuxt | P | U | P — mounted component test emitted; latest CI pending | U | U | U | U |
| Svelte | P | U | P — component test emitted; latest CI pending | U | U | U | U |
| Phoenix LiveView | S | U | U | U | U | U | U |
| Hologram | S | U | U | U | U | U | U |
| Scenic | S | U | U | U | U | U | U |
| Python / FastAPI | P | U | U — test suite presence is not generated-app execution evidence | U | U | U | U |
| Go / net/http | P | U | U — profile exists; generated behavior still needs execution proof | U | U | U | U |
| Rust / Axum | P | U | U — generated health test was found to be vacuous; replacement and real Cargo execution remain required | U | U | U | U |
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
2. **Workspace cleanup:** the trial workspace is now removed in a `finally` block on normal returns and exceptions after workspace creation. Regression coverage and CI validation are still pending.
3. **Campaign semantic projection:** authoritative PlanArtifacts are snapshotted, but the deterministic mapping producer correctly blocks when typed source semantics do not express the required frontend, API, backend, effect, and consequence obligations. No fabricated mapping is accepted.
4. **Next.js:** the build profile had a Jest-only `--runInBand` option despite using Vitest. It now invokes `npm test`. The root layout now imports `ReactNode` explicitly.
5. **Rust/Axum:** the generated test in `tiannara/application/compiler/rust_axum_backend.py` was a vacuous string equality assertion. The toolchain change to Rust 1.85 has a source-level regression assertion, but **an actual generated-project `cargo test` / release build has not yet been evidenced**. Do not mark the Rust target build-verified.
6. **Capability claims:** target manifests must be compared with executable operations. A manifest or Dockerfile alone does not establish security scanning, deployment, observability, or release capability.

## Certification rule

A target can be marked passed only when the exact generated candidate has evidence for dependency installation, production build, meaningful tests, runtime/health behavior, applicable security and authorization checks, source-to-IR semantic correspondence, and independent verification. Unsupported semantics must cause a structured rejection, not a partial-success status.

## CI snapshot

Latest known PR branch head at register creation: `a70ca62f767ac8b603a461d2be81dfc42c14af91`. Workflows for that head were queued or in progress when checked. Earlier compiler-matrix and source-quality runs passed on prior heads; those results do not validate the latest runner/frontend edits.
