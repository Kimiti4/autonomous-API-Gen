# R1_D2_COMPILER_IR_MIGRATION_MAP (R1-D.2 D2-D5)

**Status:** R1-D.2 Deliverable D2-D5. Compiler IR semantic migration map. Index: `folder/R1_D2_COMPILER_INVENTORY.md` (D2-D1), `folder/R1_D2_COMPILER_EXECUTION_GRAPH.md` (D2-D2), `folder/R1_D2_COMPILER_IR_SEMANTIC_COMPARISON.md` (D2-D3), `folder/CONTRACT_CanonicalCompilerIR.md` (D2-D4).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt.

---

## 1. Purpose

For every donor semantic in the constitutional compiler substrate, this document specifies the migration action (CANONICALIZE / MIGRATE / SPLIT / REPLACE / REJECT / DEFER) with source, destination, reason, compatibility impact, test coverage, and lineage impact.

The R1-D.2 master prompt requires: "Migrate only semantics that belong in canonical Compiler IR. Do not migrate implementation-specific semantics."

---

## 2. Migration actions

### 2.1 Classification summary

| Classification | Count | Items |
|---|---|---|
| CANONICALIZE | 1 | (current `CompilationPlan` becomes the stabilization implementation) |
| MIGRATE | 0 | (no code changes in R1-D.2; migrations are R1-D.5) |
| SPLIT | 1 | (current `CompilationPlan` → future `CanonicalCompilerIR` module + stabilization) |
| REPLACE | 0 | |
| REJECT | 4 | (BIR, Gen-C pipeline, per-category compilers, compiler_bridge) |
| DEFER | 6 | (interfaces, API contracts, frontend/backend, deployment, observability, etc.) |
| RETAIN AS DONOR | 1 | (BIRNodeType concepts as references) |

### 2.2 SPLIT-01: `CompilationPlan` → future `CanonicalCompilerIR` + stabilization

| Field | Value |
|---|---|
| Source | `compiler/core/plan.py:CompilationPlan` (stabilization) |
| Destination | future `compiler/core/canonical_ir.py:CanonicalCompilerIR` (R1-D.5) |
| Classification | **SPLIT** |
| Reason | The current `CompilationPlan` is the stabilization implementation. The canonical Compiler IR is a new module that subsumes it with 8 new fields (per D2-D4). The campaign runtime uses `CompilationPlan`; the future canonical Compiler IR is created in R1-D.5. |
| Compatibility impact | None in R1-D.2. The campaign runtime continues to use `CompilationPlan`. |
| Test coverage | The current `tests/cbc1/`, `tests/v14/`, `tests/r1d1/` (243+15+23+21) pass. New R1-D.2 tests verify the contract refinements. |
| Lineage impact | None. The `isr_id` field preserves the source ISR identity. The `plan_id` derivation is preserved. |

**Implementation:** None in R1-D.2. The SPLIT is documented; the implementation is R1-D.5.

### 2.3 REJECT-01: `BIR` (constitutional_architecture/compiler/bir/model.py:BIR)

| Field | Value |
|---|---|
| Source | `constitutional_architecture/compiler/bir/model.py:BIR` |
| Classification | **RETAIN AS DONOR** (R1-A) → **REJECT** (as runtime) |
| Reason | BIR is the semantic donor. The 9 BIRNodeType concepts are read as references; the genuinely-semantic ones are absorbed into the canonical Compiler IR contract. BIR is **not** modified to add content-hash. The canonical Compiler IR is a new module. |
| Compatibility impact | None. BIR is not in the canonical runtime. |
| Retirement | R1-D.5 (per R1-B D17 L07). |

### 2.4 REJECT-02: Gen-C pipeline (constitutional_architecture/compiler/pipeline.py:CompilerPipeline)

| Field | Value |
|---|---|
| Source | `constitutional_architecture/compiler/pipeline.py:CompilerPipeline` |
| Classification | **REJECT** (as canonical pipeline) |
| Reason | The Gen-C 8-pass pipeline is fail-open at multiple points (validation, verification, PassManager) and has semantic loss at one point (normalization). It is not in the canonical runtime. The canonical runtime uses `isr_to_plan` (single function) and `CompilerBackend.compile` (Protocol). |
| Retirement | R1-D.5 (per R1-B D17 L08, R1-E.5 for pass adaptations). |

### 2.5 REJECT-03: Per-category compilers (constitutional_architecture/compilers/*)

| Field | Value |
|---|---|
| Source | `constitutional_architecture/compilers/*` (9 per-category compilers) |
| Classification | **REJECT** (as competing runtimes) |
| Reason | Per INV-B14, no category-specific compiler becomes a new architectural authority. The per-category compilers bypass the canonical `CompilationPlan` and produce a `CompilationBundle` directly. |
| Retirement | R1-D.5 (per R1-B D17 L10). |

### 2.6 REJECT-04: Compiler bridge (constitutional_architecture/engine/compiler_bridge.py)

| Field | Value |
|---|---|
| Source | `constitutional_architecture/engine/compiler_bridge.py:13-45` |
| Classification | **REJECT** (DEAD CODE) |
| Reason | No callers. Uses non-existent API signatures. |
| Retirement | R1-D.5 (immediate removal; per R1-C C02 §11, R1-B D17 L13). |

### 2.7 DEFER-01: Interfaces

| Field | Value |
|---|---|
| Source | D07 contract: "Interfaces" |
| Classification | **DEFER** |
| Reason | The canonical IR expresses interfaces via API contracts (deferred). The current `CompilationPlan` has no interface concept. Adding interfaces is a substantial R-phase. |
| Deferred to | A future R-phase (not R1-D.5; interfaces are a backend-lowering concern). |

### 2.8 DEFER-02: API contracts

| Field | Value |
|---|---|
| Source | D07 contract: "API contracts" |
| Classification | **DEFER** |
| Reason | The current `CompilationPlan` has no API contract concept. The canonical IR expresses API contracts via interfaces (deferred). |
| Deferred to | A future R-phase. |

### 2.9 DEFER-03: Frontend / backend responsibilities

| Field | Value |
|---|---|
| Source | D07 contract: "Frontend / backend responsibilities" |
| Classification | **DEFER** |
| Reason | The canonical IR is technology-neutral. Frontend/backend is a backend-lowering concern. |
| Deferred to | A future R-phase. |

### 2.10 DEFER-04: Deployment requirements

| Field | Value |
|---|---|
| Source | D07 contract: "Deployment requirements" |
| Classification | **DEFER** |
| Reason | Deployment is a D09 ArtifactSet + D10 RuntimeObservation concern. |
| Deferred to | A future R-phase. |

### 2.11 DEFER-05: Observability requirements

| Field | Value |
|---|---|
| Source | D07 contract: "Observability requirements" |
| Classification | **DEFER** |
| Reason | Observability is a D12 concern. |
| Deferred to | A future R-phase. |

### 2.12 DEFER-06: Target requirements

| Field | Value |
|---|---|
| Source | D07 contract: "Target requirements" |
| Classification | **DEFER** |
| Reason | Target requirements are upstream of the IR; preserved via ISR lineage. |
| Deferred to | Not applicable (not needed in the canonical IR). |

### 2.13 RETAIN AS DONOR-01: BIRNodeType concepts

| Field | Value |
|---|---|
| Source | `constitutional_architecture/compiler/bir/model.py:BIRNodeType` (9 values) |
| Classification | **RETAIN AS DONOR** |
| Reason | The 9 BIRNodeType concepts (`HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST`) are read as references. The genuinely-semantic ones (e.g., `SERVICE`, `ENTITY`) are already in the canonical IR. The others (e.g., `HANDLER`, `ROUTER`, `CONFIG`, `MIDDLEWARE`) are backend-specific and do not belong in the canonical IR. |
| Compatibility impact | None. BIR is not in the canonical runtime. |
| Retirement | BIR is retired in R1-D.5; the 9 BIRNodeType concepts are evaluated and selectively absorbed into the canonical Compiler IR (R1-D.5). |

---

## 3. Code change scope for R1-D.2

**Zero code changes in R1-D.2.** All R1-D.2 work is documentation:

- D2-D1: Inventory (DONE)
- D2-D2: Execution graph (DONE)
- D2-D3: Semantic comparison (DONE)
- D2-D4: Contract refinement (DONE; this addendum)
- D2-D5: Migration map (this document)
- D2-D6: Consumer migration (next)
- D2-D7: Legacy disposition (next)
- D2-D8: Integration report (next)
- D2-D9: Test report (next)
- D2-D10: Gate report (next)

**The canonical Compiler IR module is R1-D.5 work**, not R1-D.2. The R1-D.2 master prompt's D2.6 says "Migrate only semantics that belong in canonical Compiler IR" — the migration is the contract refinement (D2-D4), not the code.

**No `compiler/core/` files are modified in R1-D.2.** No `constitutional_architecture/compiler/` files are modified. The campaign runtime is preserved.

---

## 4. Test coverage

| Test area | Test file | Tests |
|---|---|---|
| `CompilationPlan` contract | `tests/cbc1/test_plan_builder.py` (existing) | existing |
| CompilerBackend Protocol | `tests/v14/test_multi_backend.py` (existing) | existing |
| `isr_to_plan` lowering | `tests/cbc1/test_cbc1_gates.py` (existing) | existing |
| R1-D.2 contract refinements | `tests/r1d2/test_compiler_ir_contract.py` (NEW) | new |
| D2-D4 contract fields | `tests/r1d2/test_contract_refinement.py` (NEW) | new |

The R1-D.2 contract tests verify:
- The D07 contract is preserved (the original fields are documented).
- The D2-D4 refinement fields are documented.
- The current `CompilationPlan` is the stabilization implementation.
- The future canonical Compiler IR module is R1-D.5 work.

---

## 5. Compatibility impact

| Aspect | Impact |
|---|---|
| Campaign runtime (Tier A) | **None** — `CompilationPlan` is unchanged. |
| `certification/campaign/*` | **None**. |
| `certification/provenance/bundle.py:116` | **None** — SHA-256 hash is preserved. |
| B3-v2 evidence | **None** — the plan_id derivation is preserved. |
| R1-C tests | **None** — the 15 R1-C tests pass. |
| R1-D.1 tests | **None** — the 21 R1-D.1 tests pass. |
| v12 tests | **None** — the 23 v12 tests pass. |
| `isr/core/` | **None** — the canonical ISR is unchanged. |
| `constitutional_architecture/compiler/*` | **None** — the constitutional compiler is unchanged. |

---

## 6. Lineage impact

| Aspect | Impact |
|---|---|
| ISR → Compiler IR | Preserved (`isr_id` field). |
| Architecture → Compiler IR | Will be added in R1-D.5 (`source_architecture_candidate_content_hash`). |
| Compiler IR → Backend | Preserved (`CompilerBackend.compile(plan)`). |
| Backend → ArtifactSet | Preserved (R1-C C06 invariant). |
| VerificationResult | Preserved (fail-closed). |
| CertificationEvidence | Preserved (hash-chained). |

---

## 7. Implementation order

1. **R1-D.2 (this phase):** Document the contract refinements (D2-D4), the migration map (D2-D5), the consumer migration (D2-D6), the legacy disposition (D2-D7), the integration report (D2-D8), the test report (D2-D9), the gate report (D2-D10). **No code changes.**
2. **R1-D.5 (future):** Create the canonical Compiler IR module (`compiler/core/canonical_ir.py`) that implements the refined D07 contract (including the 8 new fields). The canonical Compiler IR subsumes `CompilationPlan` with a `from_plan(plan: CompilationPlan) -> CanonicalCompilerIR` migration function. The campaign runtime migrates from `CompilationPlan` to `CanonicalCompilerIR`. The per-category compilers, Gen-C pipeline, and BIR are retired.
3. **R1-D.5 (future):** Backend compatibility — the canonical backend Protocol (D08) is adapted to consume the canonical Compiler IR. The Gen-B backends (`python_fastapi.py`, `rust_axum.py`) are updated to consume the canonical IR (or a migration adapter is used).

---

## 8. Cross-references

- D2-D1: `folder/R1_D2_COMPILER_INVENTORY.md`
- D2-D2: `folder/R1_D2_COMPILER_EXECUTION_GRAPH.md`
- D2-D3: `folder/R1_D2_COMPILER_IR_SEMANTIC_COMPARISON.md`
- D2-D4: `folder/CONTRACT_CanonicalCompilerIR.md` (contract refinement)
- D2-D6: `folder/R1_D2_COMPILER_CONSUMER_MIGRATION.md` (next)

---

*End of D2-D5. The R1-D.2 migration map is complete. Zero code changes in R1-D.2. The canonical Compiler IR module is R1-D.5 work. The contract refinements (D2-D4) are the R1-D.2 deliverable. D2-D6 (consumer migration) follows.*
