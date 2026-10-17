# TaskFlow live-path compatibility audit — 2026-10-10

## Scope

Audit the current `main` compiler/provider interfaces before connecting immutable trial snapshots. This is a compatibility audit, not a TaskFlow certification.

## Confirmed interfaces

- `IntentCompiler` accepts the `LanguageModelProvider` port and returns a typed `IntermediateSoftwareRepresentation`, requirement graph, bounded repair count, and model-call records.
- `ProjectCompiler.compile_intent` performs typed ISR synthesis, derives compilation requirements, selects registered backends, invokes `generate(SystemModel)`, and verifies returned compilation results.
- `CompilerRegistry` and `CompilationExecutor` use the current `BackendCapabilityDeclaration` / `CompilationResult` contracts.
- The live provider seam is intentionally not configured by `build_project_compiler(provider_mode="live")`; it raises `CompositionError` unless a provider is explicitly injected.
- The previous trial runner's `inputs` / per-input pinned hash / output-directory schema is not used. The canonical contract's `generator_inputs` and `forbidden_inputs` are authoritative and the new runner consumes verified snapshot copies.

## Blockers before end-to-end TaskFlow generation can pass

1. A concrete live provider endpoint/model must be configured. Without it, the runner records `BLOCKED` and does not use replay.
2. Current requirement derivation emits backend service, frontend, database migration, infrastructure, deployment, and documentation requirements. The default compiler registry does not currently demonstrate complete backend declarations for every required artifact kind; selection must fail closed when one is unsupported.
3. A successful `CompilationResult` is not by itself a full-stack application. The acceptance contract requires authentication, workspace tenancy, RBAC, projects/tasks, comments/activity, search/filter, dashboard, audit trail, operational observability, negative security tests, build, deployment smoke test, runtime observation, and requirement traceability.
4. The runner must not infer frontend/API/runtime PASS from static file generation. Those are separate evidence gates and must remain `UNKNOWN` until executed against the generated artifact.

## Changes in this integration branch

- Added an opt-in OpenAI-compatible implementation of the existing `LanguageModelProvider` port. It requires explicit endpoint/model configuration and returns `LIVE` provenance only after a successful schema-validated response; network/provider errors raise `LanguageModelError`.
- Added a bounded snapshot-consuming TaskFlow trial runner. It loads the contract and input files from the verified evidence snapshot, records provider-call provenance, emits ISR/requirement-graph artifacts when available, and records compiler capability gaps as `BLOCKED`.
- Added a manual GitHub Actions workflow that uses repository secrets `TIANNARA_LLM_BASE_URL`, `TIANNARA_LLM_MODEL`, and optional `TIANNARA_LLM_API_KEY`. It uploads the evidence artifact even when the attempt is blocked or fails.
- Added mock-based provider contract tests. These tests verify port compatibility and failure behavior; they are not live-model evidence.

## Verdict

- Provider interface compatibility: **PASS (contract-level; mock-tested)**
- Live endpoint availability in this repository's CI environment: **UNKNOWN until the manual workflow is run with configured secrets**
- Full-stack TaskFlow generation capability coverage: **BLOCKED pending missing artifact-kind coverage and end-to-end runtime gates**
- ReadingShelf generalization: **NOT STARTED; gated on TaskFlow evidence boundaries**
