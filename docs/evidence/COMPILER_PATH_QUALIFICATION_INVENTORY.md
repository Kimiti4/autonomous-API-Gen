# Compiler-Path Qualification Inventory for Application A/B Trials

Status: **INVENTORY / NOT QUALIFIED FOR LIVE TASKFLOW GENERATION**

This inventory separates full compilation pipelines from backend target compilers. Different output languages or backend IDs are useful cross-target tests, but do not by themselves satisfy the requirement to compare two different compilers. A backend pair is only a valid compiler comparison when the experiment explicitly studies lowering targets; it is not evidence that two end-to-end application compilers were compared.

## Candidate paths found in the repository

| Candidate | Role | Distinctness assessment | TaskFlow A/B readiness |
|---|---|---|---|
| Cap-C ProjectCompiler (`tiannara.application.compiler.project_compiler.ProjectCompiler`) | Intent compilation, typed SystemModel extraction, requirement derivation, backend planning/execution, and bundle verification | End-to-end compiler pipeline | **Not qualified**: current TaskFlow semantic gate still blocks before a proven semantic projection and downstream consumption |
| `constitutional_architecture.compiler.pipeline.CompilerPipeline` | Eight-pass ISR-to-artifact pipeline: validation, normalization, optimization, capability resolution, lowering, code generation, verification, cross-target checks | Materially different full pipeline architecture | **Not qualified**: it uses a separate `constitutional_architecture.isr.model.isr.ISR` contract and its default backend registry currently registers a FastAPI backend; a canonical-input adapter and semantic-equivalence proof are needed |
| Cap-C backend registry (`fastapi_hexagonal`, `go_hexagonal`) | Two backend implementations consuming the Cap-C pipeline's authority | Distinct target lowerings, same upstream compiler pipeline | Useful as a **separate cross-target experiment**, not a substitute for two different end-to-end compilers |
| `autonomous-api.app.engine.fastapi_compiler.FastAPIBackendCompiler` | Backend lowering from `BackendProjectIR` to a simple FastAPI artifact set | Backend compiler only; generated route handlers return operation labels, not TaskFlow domain behavior | **Not qualified** for application-level correctness |
| `autonomous-api.app.engine.layered_fastapi_compiler.LayeredFastAPICompiler` | Extends the FastAPI compiler and adds layers | Not materially independent: subclass delegates to `FastAPIBackendCompiler`; repository methods explicitly raise `NotImplementedError` | **Reject** as compiler B for a fair application comparison |
| `autonomous-api.app.engine.domain_aware_compiler.compile_domain_aware` | Converts a synthesized proposal into a `FullStackGenome` after compatibility checks | Domain-plan/genome transformation, not a complete application artifact compiler | **Not qualified** as a full compiler without a demonstrated downstream artifact path |

## Recommended candidate pair (conditional)

Use these as the first pair to qualify, not as already-approved trial paths:

- **Compiler A:** Cap-C `ProjectCompiler`.
- **Compiler B:** `constitutional_architecture.compiler.pipeline.CompilerPipeline`.

They are the strongest materially different full-pipeline candidates identified in this repository inventory. However, they currently have different input representations and their TaskFlow semantic coverage has not been shown equivalent. Do not run the comparative generation until all gates below pass.

### Qualification gates

1. **Input parity:** define a deterministic adapter from the same frozen TaskFlow specification, acceptance criteria, and trusted semantic decisions into each compiler's input representation. Hash all shared source inputs.
2. **Parity preflight:** `experiments/compiler-benchmarks/taskflow_input_parity.py` checks a proposed declaration for canonical source hashes, all 15 mandatory field states, matching semantic-value digests, distinct compiler/implementation IDs, and declared downstream consumer bindings. A declaration-only match is explicitly not qualification; source hashes, reviewer trust, and real consumer use still require independent verification.
3. **Semantic parity:** prove that the two inputs encode the same required behaviors, security constraints, negative cases, lifecycle semantics, and persistence invariants. Any unsupported field blocks both runs rather than being silently dropped.
3. **No authority leakage:** neither path may read the golden reference implementation, the other compiler's output, or the other compiler's test/runtime evidence as generation input.
4. **Independent invocation:** run each compiler separately in a clean workspace and record compiler source revision, configuration, dependency state, and invocation command.
5. **Artifact separation:** isolate generated files, caches, databases, secrets, runtime processes, and evidence by compiler and iteration.
6. **Independent evaluation:** run the same versioned acceptance suite and security/negative-case tests against both untouched outputs.
7. **Runtime evidence:** distinguish static validation, unit tests, integration tests, live runtime tests, and production-like recovery tests. No evidence type implies a stronger one.
8. **Failure preservation:** do not patch or repair one compiler's output silently. If bounded repair is later allowed, use the same budget and log every intervention; report raw and repaired outcomes separately.
9. **Qualification report:** assign each gate PASS/FAIL/UNKNOWN/BLOCKED and record exact evidence references. The pair is qualified only when all required gates are PASS.

## Separate cross-target experiment

The existing `experiments/taskflow-native/MULTI_BACKEND_TRIAL.json` specifies Python/FastAPI and Go/`net/http` targets sharing one generated ISR. Keep that experiment conceptually separate:

- **End-to-end compiler A/B:** compare different compilation pipelines.
- **Cross-target lowering:** compare different backend targets from the same canonical intermediate representation.

Both are valuable, but answer different questions and need separate reports. Do not count Python and Go outputs from one pipeline as two different end-to-end compilers.

## Current disposition

- Parity preflight: **implemented; focused CI passed for its current tested commit; declarations alone cannot qualify the pair**.
- End-to-end compiler pair: **BLOCKED / NOT QUALIFIED**.
- TaskFlow A/B generation: **NOT RUN**.
- Cross-target Python/Go backend trial: existing contract found; execution and certification status must be established from its own evidence.
- ReadingShelf: remain deferred until TaskFlow's semantic and evidence gates are sound.