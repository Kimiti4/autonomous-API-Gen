# R1_D2_COMPILER_LEGACY_DISPOSITION (R1-D.2 D2-D7)

**Status:** R1-D.2 Deliverable D2-D7. Compiler legacy disposition. Index: `folder/R1_D2_COMPILER_INVENTORY.md` (D2-D1), `folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md` (D2-D5), `folder/CONTRACT_CanonicalCompilerIR.md` (D2-D4).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt.

---

## 1. Purpose

Explicitly classify every compiler implementation per the R1-D.2 master prompt's taxonomy: MIGRATE SELECTED SEMANTICS / REPLACE / RETAIN AS DONOR / RETAIN AS SPECIFICATION / RETIRE / DEFER. No unexplained duplicate Compiler IR remains.

---

## 2. Disposition table

| Item | Source | Disposition | Reason | Migration step |
|---|---|---|---|---|
| `compiler/core/plan.py:CompilationPlan` | Canonical stabilization | **SPLIT** (RETAIN + future MIGRATE) | The current `CompilationPlan` is the stabilization implementation. The future canonical Compiler IR module subsumes it (R1-D.5). Per D2-D5 SPLIT-01. | R1-D.5 (future canonical Compiler IR module) |
| `compiler/core/protocol.py:CompilerBackend` | Canonical backend protocol | **KEEP** | The canonical Protocol is the authoritative backend contract. | (none) |
| `compiler/core/lowering.py:isr_to_plan` | Canonical lowering | **KEEP** | The canonical ISR → CompilationPlan lowering. | (none) |
| `compiler/core/conformance.py:CHECKER` | Canonical structural conformance | **KEEP** (ADAPT in R1-E.8 for behavioral) | Structural conformance is canonical. Behavioral conformance is R1-E.8. | R1-E.8 |
| `compiler/core/repository.py:GeneratedRepository` | Canonical ArtifactSet equivalent | **KEEP** (refine in R1-D.5 to canonical ArtifactSet) | The canonical ArtifactSet module is R1-D.5. | R1-D.5 |
| `compiler/composition.py:build_backend_registry` | Canonical registry | **KEEP** | The canonical backend registry. | (none) |
| `compiler/backends/python_fastapi.py:PythonFastAPIBackend` | Canonical backend | **KEEP** | The Python/FastAPI canonical backend. | (none) |
| `compiler/backends/rust_axum.py:RustAxumBackend` | Canonical backend | **KEEP** | The Rust/Axum canonical backend. | (none) |
| `compiler/backends/reference_backend.py:ReferenceBackend` | Canonical reference | **KEEP** | The reference backend. | (none) |
| `compiler/backends/production/*` (Gen-A) | Canonical Gen-A | **RETIRE** (R1-D.5) | Gen-A backends are not in the canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/bir/model.py:BIR` | Constitutional semantic donor | **RETAIN AS DONOR** → **RETIRE** (R1-D.5) | BIR is a semantic donor. The 9 BIRNodeType concepts are evaluated and selectively absorbed into the canonical Compiler IR (R1-D.5). BIR is **not** modified. | R1-D.5 (retirement); R1-D.5 (selective absorption) |
| `constitutional_architecture/compiler/pipeline.py:CompilerPipeline` | Constitutional Gen-C pipeline | **RETIRE** (R1-D.5) | Fail-open at validation, verification, PassManager. Semantic loss at normalization. Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/passes/validation_pass.py` | Constitutional validation | **ADAPT TEMPORARILY** (R1-E.2) → **RETIRE** (R1-D.5) | Fail-open. Canonical contracts first (R1-E.2); adapt to fail-closed. Retire when canonical validation is the authoritative contract. | R1-E.2, R1-D.5 |
| `constitutional_architecture/compiler/passes/normalization_pass.py` | Constitutional normalization | **ADAPT TEMPORARILY** (R1-E.4) → **RETIRE** (R1-D.5) | Lossy (7 of 21 System fields). Canonical contracts first (R1-E.4). | R1-E.4, R1-D.5 |
| `constitutional_architecture/compiler/passes/verification_pass.py` | Constitutional verification | **ADAPT TEMPORARILY** (R1-E.1) → **RETIRE** (R1-D.5) | Fail-open. Canonical contracts first (R1-E.1). | R1-E.1, R1-D.5 |
| `constitutional_architecture/compiler/passes/optimization_pass.py` | Constitutional optimization | **MIGRATE SELECTED SEMANTICS** (R1-D.2) | Optimization concepts migrate to canonical Compiler IR (R1-D.5). | R1-D.5 |
| `constitutional_architecture/compiler/passes/capability_resolution_pass.py` | Constitutional capability resolution | **MIGRATE SELECTED SEMANTICS** (R1-D.2) | 13+ capabilities (OAUTH2, JWT_AUTH, etc.). The abstract capabilities (authentication, authorization, etc.) are absorbed into the canonical Compiler IR's `required_capabilities` field (D2-D4). | R1-D.5 |
| `constitutional_architecture/compiler/passes/lowering_pass.py` | Constitutional lowering | **MIGRATE SELECTED SEMANTICS** (R1-D.2) | Lowering concept migrates; BIRNodeType concepts absorbed. | R1-D.5 |
| `constitutional_architecture/compiler/passes/code_generation_pass.py` | Constitutional code generation | **MIGRATE SELECTED SEMANTICS** (R1-D.2) | Code generation is the backend's responsibility; concepts migrate to canonical backend. | R1-D.5 |
| `constitutional_architecture/compiler/passes/cross_target_pass.py` | Constitutional cross-target | **MIGRATE SELECTED SEMANTICS** (R1-D.2) | Cross-target is a backend concern. | R1-D.5 |
| `constitutional_architecture/compiler/backends/fastapi_backend.py` | Constitutional Gen-C FastAPI backend | **ADAPT** (R1-C C06 done) → **RETIRE** (R1-D.5) | Artifact purity done in R1-C. Retire when canonical backend is the authoritative contract. | R1-D.5 |
| `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` | Constitutional Gen-C ABC | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/backends/backend_registry.py` | Constitutional Gen-C registry | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/backends/backend_selector.py` | Constitutional Gen-C selector | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/quality/*` | Constitutional quality | **MIGRATE SELECTED SEMANTICS** (R1-D.5) | Optimization concepts migrate. | R1-D.5 |
| `constitutional_architecture/compiler/observability/*` | Constitutional observability | **DEFER** (out of R1 scope) | Observability is a D12 concern. | R2/R3 |
| `constitutional_architecture/compiler/cache/*` | Constitutional cache | **DEFER** (out of R1 scope) | Caching is not in the R1 scope. | R2/R3 |
| `constitutional_architecture/compiler/artifacts/*` | Constitutional artifacts | **MIGRATE SELECTED SEMANTICS** (R1-D.5) | Artifact concepts (ArtifactType, Diagnostic) are absorbed into the canonical ArtifactSet. | R1-D.5 |
| `constitutional_architecture/compiler/contract.py` | Constitutional contracts | **MIGRATE SELECTED SEMANTICS** (R1-D.5) | Contract concepts. | R1-D.5 |
| `constitutional_architecture/compiler/capability.py` | Constitutional capability | **MIGRATE SELECTED SEMANTICS** (R1-D.2) | Capability resolution. | R1-D.5 |
| `constitutional_architecture/compiler/pass_interface.py` | Constitutional pass interface | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/pass_manager.py` | Constitutional pass manager | **RETIRE** (R1-D.5) | Continue-on-failure. Not in canonical. | R1-D.5 |
| `constitutional_architecture/compiler/pass_registry.py` | Constitutional pass registry | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/compilation_config.py` | Constitutional config | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/compiler_context.py` | Constitutional context | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/compiler/compiler_result.py` | Constitutional result | **RETIRE** (R1-D.5) | Not in canonical runtime. | R1-D.5 |
| `constitutional_architecture/engine/compiler_bridge.py` | Constitutional bridge (DEAD CODE) | **RETIRE** (R1-D.5; immediate) | No callers. Dead code. | R1-D.5 |
| `constitutional_architecture/compilers/backend/*` | Per-category backend compiler | **RETIRE** (R1-D.5) | INV-B14. Not in canonical. | R1-D.5 |
| `constitutional_architecture/compilers/database/*` | Per-category database compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |
| `constitutional_architecture/compilers/deployment/*` | Per-category deployment compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |
| `constitutional_architecture/compilers/documentation/*` | Per-category documentation compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |
| `constitutional_architecture/compilers/frontend/*` | Per-category frontend compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |
| `constitutional_architecture/compilers/infrastructure/*` | Per-category infrastructure compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |
| `constitutional_architecture/compilers/operational/*` | Per-category operational compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |
| `constitutional_architecture/compilers/runtime_policy/*` | Per-category runtime policy compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |
| `constitutional_architecture/compilers/testing/*` | Per-category testing compiler | **RETIRE** (R1-D.5) | INV-B14. | R1-D.5 |

---

## 3. Disposition summary

| Disposition | Count |
|---|---|
| KEEP (canonical) | 8 (CompilerBackend, isr_to_plan, CHECKER, build_backend_registry, 2 canonical backends, reference backend, Repository) |
| SPLIT (CompilationPlan → future CanonicalCompilerIR) | 1 |
| RETAIN AS DONOR (BIRNodeType concepts) | 1 (BIR; absorbed into R1-D.5) |
| MIGRATE SELECTED SEMANTICS (R1-D.5) | 9 (Gen-C passes, quality, artifacts, contract, capability) |
| ADAPT TEMPORARILY (R1-E.x) | 3 (validation, normalization, verification passes) |
| RETIRE (R1-D.5) | 30+ (Gen-C pipeline, backends, per-category compilers, compiler_bridge, Gen-A backends, constitutional graph) |
| DEFER (out of R1 scope) | 2 (observability, cache) |

---

## 4. No unexplained duplicate Compiler IR

After R1-D.2:

- The canonical Compiler IR is the future `CanonicalCompilerIR` module (R1-D.5). The current `CompilationPlan` is the stabilization implementation.
- No new Compiler IR types introduced.
- No constitutional types promoted to canonical.
- The constitutional Compiler IR implementations are explicitly classified: KEEP / SPLIT / RETAIN AS DONOR / MIGRATE SELECTED SEMANTICS / ADAPT TEMPORARILY / RETIRE / DEFER.
- 3 Gen-C passes (validation, normalization, verification) are ADAPT TEMPORARILY (R1-E.1, R1-E.2, R1-E.4) with the canonical contracts first discipline.
- 9 per-category compilers are RETIRE (INV-B14).

There is **no unexplained duplicate Compiler IR**. The constitutional substrate is on a clear retirement path (R1-D.5) with explicit ownership and destination for each component.

---

## 5. Cross-references

- D2-D1: `folder/R1_D2_COMPILER_INVENTORY.md`
- D2-D5: `folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md`
- D2-D6: `folder/R1_D2_COMPILER_CONSUMER_MIGRATION.md`
- D2-D8: `folder/R1_D2_CANONICAL_COMPILER_INTEGRATION_REPORT.md` (next)

---

*End of D2-D7. The R1-D.2 compiler legacy disposition is complete. 8 KEEP, 1 SPLIT, 1 RETAIN AS DONOR, 9 MIGRATE SELECTED SEMANTICS, 3 ADAPT TEMPORARILY, 30+ RETIRE, 2 DEFER. No unexplained duplicate Compiler IR. D2-D8 (integration report) follows.*
