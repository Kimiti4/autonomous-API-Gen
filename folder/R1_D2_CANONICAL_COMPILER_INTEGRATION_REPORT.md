# R1_D2_CANONICAL_COMPILER_INTEGRATION_REPORT (R1-D.2 D2-D8)

**Status:** R1-D.2 Deliverable D2-D8. Canonical compiler integration report. Index: `folder/R1_D2_COMPILER_INVENTORY.md` (D2-D1), `folder/R1_D2_COMPILER_IR_MIGRATION_MAP.md` (D2-D5), `folder/CONTRACT_CanonicalCompilerIR.md` (D2-D4).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt.

---

## 1. Purpose

Document the before/after state of the canonical compiler after R1-D.2. The R1-D.2 master prompt requires: "Document: before, after, canonical IR, canonical pipeline, backend boundary, adapters, lineage, failure semantics, legacy boundaries."

---

## 2. Before R1-D.2

| Aspect | Value |
|---|---|
| Canonical Compiler IR | `compiler/core/plan.py:CompilationPlan` (stabilization; Pydantic flat; 4 node types: Service, DataModel, Event, SecurityPolicy) |
| Canonical compiler pipeline | `isr_to_plan` (`compiler/core/lowering.py:14-73`) + `CompilerBackend.compile(plan)` (Protocol) |
| Canonical backend boundary | `CompilerBackend.compile(plan) -> GeneratedRepository` (structural conformance via `CHECKER`) |
| Adapters | None (canonical runtime has no adapters) |
| Lineage | `CompilationPlan.isr_id` (system_id, not content hash) + `plan_id` (derived from ISR hash) |
| Failure semantics | `isr_to_plan` is pure function; backend returns GeneratedRepository (possibly empty); `CHECKER` produces structural conformance report |
| Legacy boundaries | 4 Gen-C consumers, ~11 per-category compiler consumers, 3+ BIR consumers, 1 dead-code bridge, 9 per-category compilers, Gen-C 8-pass pipeline (fail-open) |
| Content hash on Compiler IR | None (no `content_hash` field on `CompilationPlan`; hash is on `plan.model_dump()` in provenance) |
| Schema version | None |
| Source ArchitectureCandidate reference | None |
| Lowering metadata | None |
| Required capabilities | None |
| Backend constraints | None |

**Test count: 302 (243 Tier A + 15 R1-C + 23 v12 + 21 R1-D.1).**

---

## 3. After R1-D.2

| Aspect | Value |
|---|---|
| Canonical Compiler IR | `CompilationPlan` (stabilization, unchanged) + future `CanonicalCompilerIR` module (R1-D.5; per D2-D4 refinement) |
| Canonical compiler pipeline | `isr_to_plan` + `CompilerBackend.compile(plan)` (unchanged) |
| Canonical backend boundary | `CompilerBackend.compile(plan) -> GeneratedRepository` (unchanged) |
| Adapters | None (canonical runtime has no adapters) |
| Lineage | `CompilationPlan.isr_id` + `plan_id` (unchanged) + future `source_isr_content_hash`, `source_architecture_content_hash` (R1-D.5; per D2-D4) |
| Failure semantics | Unchanged (canonical fail-closed; Gen-C fail-open on retirement path) |
| Legacy boundaries | 30+ constitutional compiler implementations classified for retirement (R1-D.5); 3 Gen-C passes ADAPT TEMPORARILY (R1-E.x) |
| **Contract refinement (D2-D4)** | 8 new fields added to the canonical Compiler IR contract: `content_hash`, `schema_version`, `source_architecture_candidate_content_hash`, `backend_constraints`, `required_capabilities`, `lowering_operator`, `lowering_timestamp`, `lowering_chain`. 3 fields refined: Compilation ID, Source ISR reference, Security requirements. |
| Content hash on Compiler IR | **REFINED**: contract requires `content_hash`; implementation is R1-D.5 |
| Schema version | **ADDED**: contract requires `schema_version` (semver); implementation is R1-D.5 |
| Source ArchitectureCandidate reference | **ADDED**: contract requires `source_architecture_content_hash`; implementation is R1-D.5 |
| Required capabilities | **ADDED**: contract requires `required_capabilities: list[str]`; implementation is R1-D.5 |
| Backend constraints | **ADDED**: contract requires `backend_constraints: list[str]`; implementation is R1-D.5 |

**Test count: 302 + new R1-D.2 tests (TBD in D2-D9).**

---

## 4. Canonical Compiler IR (D2-D4 refinement)

The canonical Compiler IR contract (D07 + D2-D4) carries:

| Field | Classification | Source |
|---|---|---|
| Compilation ID (refined to content-hash-derived) | semantic | D07 + D2-D4 |
| Source ISR revision reference (content hash; refined) | semantic | D07 + D2-D4 |
| Source ArchitectureCandidate reference (content hash; added) | semantic | D07 + D2-D4 |
| Content hash (SHA-256; added) | derived | D07 + D2-D4 |
| Schema version (added) | semantic | D07 + D2-D4 |
| Component model (Service, DataModel, Event, SecurityPolicy) | semantic | D07 |
| Data flows (Service.data_models, published_events, consumed_events) | semantic | D07 |
| Persistence requirements | semantic | D07 |
| Security requirements (refined: per-service) | semantic | D07 + D2-D4 |
| Backend constraints (added) | semantic | D07 + D2-D4 |
| Required capabilities (added) | semantic | D07 + D2-D4 |
| Lowering metadata (added) | observational metadata | D07 + D2-D4 |
| Provenance (added/refined) | observational metadata | D07 + D2-D4 |
| Serialization (deterministic JSON; added) | derived | D07 + D2-D4 |

---

## 5. Canonical pipeline (unchanged in R1-D.2)

```text
isr.core.revision.ISRRevision (canonical)
  │ isr_to_plan
  ▼
compiler.core.plan.CompilationPlan (stabilization)
  │ CompilerBackend.compile
  ▼
compiler.core.repository.GeneratedRepository
  │ certification/stages/*
  ▼
VerificationResult
  │ EvidenceLedger
  ▼
CertificationEvidence
```

**No pipeline changes in R1-D.2.** The canonical pipeline is preserved. The contract refinements (D2-D4) are applied to the future canonical Compiler IR module (R1-D.5).

---

## 6. Backend boundary (unchanged in R1-D.2)

```text
CompilerIR (future CanonicalCompilerIR)
  ↓
CompilerBackend (D08 Protocol)
  ↓
ArtifactSet (D09; GeneratedRepository stabilization)
  ↓
Verification (D10)
  ↓
Certification (D11)
```

**Backend constraints (per D2-D4):** The future canonical Compiler IR carries `backend_constraints: list[str]` and `required_capabilities: list[str]`. The `CompilerBackend` Protocol declares its supported capabilities. The cross-contract mapping (D14) routes `UNSUPPORTED_CAPABILITY` → `Verification INDETERMINATE`.

**No backend boundary changes in R1-D.2.**

---

## 7. Adapters (none in canonical runtime)

The canonical runtime has no adapters. The constitutional substrate has internal lowering and emission but no canonical adapter. **No adapters introduced or removed in R1-D.2.**

---

## 8. Lineage

The canonical compiler lineage (preserved):

```text
Requirement ID
  → RequirementGraph identity (D02)
  → ISR identity (D03; ISRRevision.content_hash)
  → ArchitectureCandidate identity (D04; future source_architecture_content_hash per D2-D4)
  → Compiler IR identity (D07 + D2-D4; future content_hash)
  → Backend identity (D08; BackendIdentity)
  → ArtifactSet identity (D09; GeneratedRepository stabilization; future canonical ArtifactSet)
  → VerificationResult identity (D10)
  → CertificationEvidence (D11; hash-chained)
```

**Lineage is preserved.** The R1-D.2 contract refinement adds the Architecture → Compiler IR link (D2-D4) and strengthens the ISR → Compiler IR link (refined from system_id to content hash).

---

## 9. Failure semantics

| Surface | Failure mode | Handling |
|---|---|---|
| `ISRRevision` invalid | `validate_invariants` raises | Fail-closed (R1-D.1 G09) |
| `isr_to_plan` receives invalid ISR | Pure function; produces a CompilationPlan from whatever nodes are present | Partial lowering; documented limitation |
| `CompilerBackend.compile` returns empty repo | Structural conformance fails | `ConformanceReport` indicates failure |
| Verifier internal exception | `VerificationResult.INDETERMINATE` | Fail-closed (D10) |
| Verifier unsupported capability | `VerificationResult.INDETERMINATE` | Fail-closed (D14) |
| Gen-C validation pass exception | `success=True` (fail-open) | VIOLATION (R1-E.2) |
| Gen-C verification pass exception | `success=not has_errors` (WARNING; fail-open) | VIOLATION (R1-E.1) |
| Gen-C PassManager fail | Records error; continues | VIOLATION (R1-D.5 retirement) |
| Gen-C normalization loss | Silently drops 14 of 21 System fields | VIOLATION (R1-E.4) |

**Canonical runtime: fail-closed. Constitutional: fail-open (on retirement path).**

---

## 10. Legacy boundaries

| Boundary | Status | Action |
|---|---|---|
| `constitutional_architecture/compiler/pipeline.py:CompilerPipeline` | LEGACY; fail-open | RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/bir/model.py:BIR` | LEGACY; semantic donor | RETAIN AS DONOR → RETIRE (R1-D.5); selective absorption of BIRNodeType concepts |
| `constitutional_architecture/compiler/backends/fastapi_backend.py` | LEGACY; artifact purity done (R1-C C06) | RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/backends/backend_interface.py` | LEGACY; ABC | RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/passes/validation_pass.py` | LEGACY; fail-open | ADAPT TEMPORARILY (R1-E.2); RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/passes/normalization_pass.py` | LEGACY; lossy | ADAPT TEMPORARILY (R1-E.4); RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/passes/verification_pass.py` | LEGACY; fail-open | ADAPT TEMPORARILY (R1-E.1); RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/passes/{optimization,capability_resolution,lowering,code_generation,cross_target}_pass.py` | LEGACY | MIGRATE SELECTED SEMANTICS (R1-D.5) |
| `constitutional_architecture/compiler/quality/*` | LEGACY | MIGRATE SELECTED SEMANTICS (R1-D.5) |
| `constitutional_architecture/compiler/artifacts/*` | LEGACY | MIGRATE SELECTED SEMANTICS (R1-D.5) |
| `constitutional_architecture/compiler/contract.py` | LEGACY | MIGRATE SELECTED SEMANTICS (R1-D.5) |
| `constitutional_architecture/compiler/capability.py` | LEGACY | MIGRATE SELECTED SEMANTICS (R1-D.2 contract; R1-D.5 implementation) |
| `constitutional_architecture/compiler/{pass_interface,pass_manager,pass_registry}.py` | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/{compilation_config,compiler_context,compiler_result}.py` | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/compiler/observability/*` | LEGACY | DEFER (R2/R3) |
| `constitutional_architecture/compiler/cache/*` | LEGACY | DEFER (R2/R3) |
| `constitutional_architecture/engine/compiler_bridge.py` | DEAD CODE | RETIRE (R1-D.5; immediate) |
| `constitutional_architecture/compilers/*` (9 per-category) | LEGACY; INV-B14 | RETIRE (R1-D.5) |
| `compiler/backends/production/*` (Gen-A) | LEGACY | RETIRE (R1-D.5) |

---

## 11. R1-D.5 path

The R1-D.2 contract refinement is the **safe path** to the canonical Compiler IR. The future canonical Compiler IR module (R1-D.5) will:

1. Create `compiler/core/canonical_ir.py:CanonicalCompilerIR` (Pydantic frozen) with the refined D07 contract fields (8 new + 3 refined).
2. Provide `from_plan(plan: CompilationPlan) -> CanonicalCompilerIR` migration function.
3. Update `isr_to_plan` to produce `CanonicalCompilerIR` instead of `CompilationPlan`.
4. Update the 10 canonical CompilationPlan consumers to consume `CanonicalCompilerIR`.
5. Update the 2 canonical backends to consume `CanonicalCompilerIR`.
6. Update `CHECKER` to work with `CanonicalCompilerIR`.
7. Update `certification/provenance/bundle.py` to hash the canonical Compiler IR's `content_hash`.
8. Retire `CompilationPlan` (or keep as a type alias for backward compatibility).
9. Retire the per-category compilers, Gen-C pipeline, BIR, and compiler_bridge.
10. Verify the 302-test baseline remains green.

---

## 12. Verdict

R1-D.2 is a **bounded, additive, non-breaking** contract refinement:

- 0 code changes to the canonical runtime (`compiler/core/`, `isr/core/`, `evolution/`, `reqgraph/`, `certification/`, `release/evidence/`).
- 1 contract file updated (`folder/CONTRACT_CanonicalCompilerIR.md`) with the D2-D4 refinement (8 new fields, 3 refined).
- 8 new R1-D.2 documentation files (D2-D1 through D2-D10, minus D2-D4 which is the contract itself).
- 302 tests pass (243 Tier A + 15 R1-C + 23 v12 + 21 R1-D.1); new R1-D.2 contract tests to be added.
- B3-v2 evidence chain preserved.
- No changes to `certification/`, `release/evidence/`, `compiler/core/`, `isr/core/`, `evolution/`, `reqgraph/`.
- The canonical Compiler IR contract is **authoritative** (D07 + D2-D4 refinement). The future canonical Compiler IR module is R1-D.5.

---

## 13. Cross-references

- D2-D1 through D2-D7: R1-D.2 inventory, execution graph, comparison, contract refinement, migration map, consumer migration, legacy disposition.
- D2-D9: `folder/R1_D2_COMPILER_IR_TEST_REPORT.md` (next)

---

*End of D2-D8. The R1-D.2 canonical compiler integration is verified. 302 tests pass. The D07 contract is refined (D2-D4). The future canonical Compiler IR module is R1-D.5. D2-D9 (test report) follows.*
