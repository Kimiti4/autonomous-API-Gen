# TaskFlow Compiler Compatibility Audit

Date: 2026-10-11
Scope: static interface audit of the provider-free TaskFlow profile against the existing ESAP compiler paths.
Verdict: **BLOCKED for full-stack generation; no certification claim.**

## 1. Existing compiler paths are distinct

### Constitutional ISR pipeline
- Input: `constitutional_architecture.isr.model.isr.ISR`.
- Entry point: `constitutional_architecture.compiler.pipeline.CompilerPipeline.compile(isr, config)`.
- The lowering pass carries entity IDs and field names into BIR.
- The current `constitutional_architecture.compiler.backends.fastapi_backend.FastAPIBackend.compile` adapter constructs its backend IR with `entities: []` and `interfaces: []`, regardless of the BIR module contents. It only carries service names/operation names into that backend IR.
- Therefore a structurally valid ISR and a successful backend artifact count do not establish that domain entities, field schemas, relationships, or interfaces survived this pipeline.

### Cap-C typed SystemModel pipeline
- Input: `tiannara.domain.models.isr.IntermediateSoftwareRepresentation` carrying a typed `SystemModel` payload.
- `ProjectCompiler.compile_intent` calls `IntentCompiler.compile_full`, requires `isr.system_model()` to return a typed model, derives compilation requirements, selects declared backends, and executes `generate(system_model)`.
- The deterministic `FastAPIHexagonalBackend` accepts the typed `SystemModel` and emits a `CompilationResult`; `BundleVerifier` checks required files, Python syntax, and dependency direction. These static checks do not themselves prove TaskFlow behavior, authorization, tenancy isolation, or persistence semantics.
- The current live runner reaches this path only after invoking the provider-backed `IntentCompiler`. The provider-free acceptance analyzer and the new constitutional ISR profile are not yet adapted into this native typed SystemModel/RequirementGraph interface.

## 2. What the provider-free profile proves

- The snapshot input digests and acceptance digest are reproducible.
- Canonical capability names and 15 explicit problem obligations are mapped to typed constitutional ISR requirements and a declarative policy.
- The source line, target capability names, requirement identity, policy identity, and acceptance-criterion identity are preserved.
- All obligation evidence states remain `UNKNOWN`; the profile does not authorize generation or certification.

## 3. Remaining integration work

1. Implement a provider-free `IntentCompiler`-compatible adapter that builds a native `RequirementGraph`, derives a typed `SystemModel`, and wraps it using `IntermediateSoftwareRepresentation.from_system_model` from snapshot inputs only.
2. Preserve all source-to-node links and unknowns across that bridge; do not silently populate unspecified field schemas, relationships, idempotent operations, or API contracts.
3. Make the generation gate inspect unresolved mandatory semantics before backend selection. A native compiler interface being callable is not enough to authorize output.
4. Once semantics are resolved, compile to a bounded temporary output directory, run independent build/API/frontend/runtime/security/persistence tests, and retain traceable evidence.
5. Keep the constitutional ISR pipeline and Cap-C SystemModel pipeline separate unless a tested, lossless adapter is implemented. Do not treat similarly named ISR types as interchangeable.

## Evidence interpretation

This is a source/interface audit, not a runtime certification test. The static code path indicates a concrete data-loss risk in the older constitutional FastAPI adapter and a missing provider-free bridge into the native Cap-C pipeline. Until an end-to-end adapter and independent behavior tests exist, the TaskFlow application generation result remains **UNKNOWN/BLOCKED**.
