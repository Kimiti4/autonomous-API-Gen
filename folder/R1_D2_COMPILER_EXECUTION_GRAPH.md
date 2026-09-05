# R1_D2_COMPILER_EXECUTION_GRAPH (R1-D.2 D2-D2)

**Status:** R1-D.2 Deliverable D2-D2. Compiler execution graph. Index: `folder/R1_D2_COMPILER_INVENTORY.md` (D2-D1), `folder/R1_D1_CANONICAL_INTEGRATION_REPORT.md` (D7 R1-D.1), `folder/R1_C_CANONICAL_INTEGRATION_REPORT.md` (C9 R1-C).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; the R1-D.2 master prompt.

**Method:** File:line-cited trace of the actual runtime data flow. OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN markers.

---

## 1. Purpose

Construct the actual compiler execution graph. Trace:

```text
ISR
 ↓
Architecture Model
 ↓
Compiler IR
 ↓
Compiler Pipeline
 ↓
Backend
 ↓
ArtifactSet
 ↓
Verification
```

For every edge identify: producer, consumer, data type, adapter, serialization, validation, failure behavior, provenance. Explicitly identify bypasses.

---

## 2. Canonical execution graph (the runtime that matters)

### 2.1 The actual flow (file:line cited)

```text
isr.core.revision.ISRRevision
  │
  │ [certification/campaign/plan_builder.py:13-14, 142-144]
  │   isr_to_plan(revision) → CompilationPlan
  ▼
compiler.core.plan.CompilationPlan
  │
  │ [compiler.core.protocol.CompilerBackend.compile(plan)]
  │   PythonFastAPIBackend, RustAxumBackend
  ▼
compiler.core.repository.GeneratedRepository
  │
  │ [certification/stages/{stub_stages, docker_stages, independent_verify}.py]
  │   verify_repository(repo)
  ▼
Verification result (PASS/FAIL/INDETERMINATE/NOT_RUN/BLOCKED)
  │
  │ [certification/evidence/ledger.py:EvidenceLedger]
  │   SHA-256 hash-chained evidence record
  ▼
certification/evidence/cbc1-b-B3-ledger.jsonl (B3-v2)
```

### 2.2 Edge-by-edge analysis

#### Edge 1: `ISRRevision` → `CompilationPlan`

| Field | Value |
|---|---|
| Producer | `compiler/core/lowering.py:14-73` (`isr_to_plan`) |
| Consumer | `certification/campaign/plan_builder.py:13-14, 142-144` (canonical runtime) |
| Data type | `ISRRevision` (canonical) → `CompilationPlan` (Pydantic frozen) |
| Adapter | None (direct function call) |
| Serialization | `plan.model_dump()` (used in `certification/provenance/bundle.py:116` for SHA-256 hash) |
| Validation | `validate_invariants` is called in `ISRRevision.create()` (`isr/core/revision.py:50-52`); `isr_to_plan` itself has no validation |
| Failure behavior | If `ISRRevision` is invalid, `validate_invariants` raises `ISRInvariantViolation` (fail-closed at ISR construction). `isr_to_plan` is a pure function; it does not raise. |
| Provenance | `ISRRevision.content_hash` is the identity; `CompilationPlan.plan_id = "plan:" + revision.content_hash[:16]` |

**Observation:** The lowering is **partial** — only 4 of 9 NodeType and 4 of 8 EdgeType are consumed (per R1-D.2 D2-D1 §1.4). The other 5 NodeType (`DOMAIN`, `CAPABILITY`, `API`, `INFRASTRUCTURE_TARGET`, `REQUIREMENT_REF`) and 4 EdgeType (`SATISFIES`, `IMPLEMENTED_BY`, `EXPOSES`, `DEPENDS_ON`) are **not represented** in the plan.

**Classification:** This is a **stabilization** mapping. The canonical Compiler IR contract (R1-B D07) requires the future canonical Compiler IR to preserve the full ISR semantics. The current `CompilationPlan` is a **partial** representation.

#### Edge 2: `CompilationPlan` → `GeneratedRepository`

| Field | Value |
|---|---|
| Producer | `CompilerBackend.compile(plan)` (`compiler/core/protocol.py:64`) |
| Consumer | `PythonFastAPIBackend`, `RustAxumBackend` (canonical) |
| Data type | `CompilationPlan` → `GeneratedRepository` (the canonical ArtifactSet equivalent) |
| Adapter | None (direct Protocol call) |
| Serialization | `GeneratedRepository` is an in-memory representation; `build_repository(files_dict)` (canonical pure emission) |
| Validation | `CHECKER.check(plan, element_paths(plan), repo)` (`compiler/core/conformance.py:32-50`) — **structural-only** conformance |
| Failure behavior | If the backend cannot lower, it returns `GeneratedRepository` (possibly empty). The conformance check produces a `ConformanceReport`. If `plan_element_ids` are not in the repo, the report indicates structural failure. |
| Provenance | `plan.model_dump()` is SHA-256 hashed in `certification/provenance/bundle.py:116`. `GeneratedRepository` does not have its own content hash (it is the canonical ArtifactSet equivalent). |

**Observation:** The conformance check is **structural-only** (per R1-A; the R1-D.2 master prompt requires behavioral conformance in a future R-phase). The `CHECKER` checks that `plan_element_ids` are mapped to paths and that the paths exist in the repo.

#### Edge 3: `GeneratedRepository` → `VerificationResult`

| Field | Value |
|---|---|
| Producer | `certification/stages/{stub_stages, docker_stages, independent_verify}.py` |
| Consumer | `certification/evidence/ledger.py:EvidenceLedger` |
| Data type | `GeneratedRepository` → `VerificationResult` (5-state model) |
| Adapter | None (direct call) |
| Serialization | `VerificationResult` is a Pydantic model with `result ∈ {PASS, FAIL, INDETERMINATE, NOT_RUN, BLOCKED}` |
| Validation | The verifier is fail-closed (per R1-C C09 and D10) |
| Failure behavior | `INDETERMINATE` on internal exception; `FAIL` on check failure; `PASS` only on success |
| Provenance | `VerificationResult` carries the subject identity, verifier identity/version, evidence references |

**Observation:** The canonical verifier is **fail-closed** (per R1-C C09, R1-D.1 G09). The 5-state model is mandatory. The `INDETERMINATE` state is reserved for internal exceptions and downstream `UNSUPPORTED_CAPABILITY`.

#### Edge 4: `VerificationResult` → `CertificationEvidence`

| Field | Value |
|---|---|
| Producer | `certification/evidence/ledger.py:EvidenceLedger` |
| Consumer | Auditors, governance registry, downstream campaigns |
| Data type | `VerificationResult` → `CertificationEvidence` (hash-chained JSONL) |
| Adapter | None (direct serialization) |
| Serialization | Deterministic JSON; hash-chained (each record's hash includes the previous record's hash) |
| Validation | A `CertificationEvidence` record cannot be created without a corresponding `VerificationResult`. The certification state is derived from the verification state (D14). |
| Failure behavior | If the verification result is `INDETERMINATE` or `FAIL`, the certification state is `INDETERMINATE` or `NOT_CERTIFIED` (not `CERTIFIED`). INV-B11. |
| Provenance | The evidence chain preserves the full lineage: Requirement → RequirementGraph → ISR → ArchitectureCandidate → CompilerIR → Backend → ArtifactSet → VerificationResult → CertificationEvidence. |

**Observation:** The evidence chain is **immutable** (INV-B13). The B3-v2 evidence chain is preserved unchanged.

---

## 3. Constitutional execution graph (Gen-C)

### 3.1 The actual flow (file:line cited)

```text
constitutional_architecture.isr.model.isr.ISR (rich System/Module/Entity)
  │
  │ [constitutional_architecture/compiler/pipeline.py:86]
  │   CompilerPipeline.compile(isr, config)
  ▼
8-pass pipeline:
  1. ValidationPass (fail-open; constitutional_architecture/compiler/passes/validation_pass.py:7-31)
  2. NormalizationPass (lossy; constitutional_architecture/compiler/passes/normalization_pass.py:19-156)
  3. OptimizationPass (constitutional_architecture/compiler/passes/optimization_pass.py:8-44)
  4. CapabilityResolutionPass (constitutional_architecture/compiler/passes/capability_resolution_pass.py:8-78)
  5. LoweringPass (ISR → BIR; constitutional_architecture/compiler/passes/lowering_pass.py:8-59)
  6. CodeGenerationPass (constitutional_architecture/compiler/passes/code_generation_pass.py:11-110)
  7. VerificationPass (fail-open; constitutional_architecture/compiler/passes/verification_pass.py:12-132)
  8. CrossTargetPass (constitutional_architecture/compiler/passes/cross_target_pass.py:7-38)
  │
  ▼
BIR (constitutional_architecture/compiler/bir/model.py)
  │
  │ [constitutional_architecture/compiler/backends/fastapi_backend.py:73-86]
  │   FastAPIBackend.compile(bir, bindings)
  ▼
BackendResult (artifacts: list[Artifact], diagnostics: list)
  │
  │ (filesystem write REMOVED in R1-C C06; was self.write_files())
  ▼
ArtifactSet (in-memory)
```

### 3.2 Edge-by-edge analysis

#### Edge 1: `ISR` (rich) → `PassContext`

| Field | Value |
|---|---|
| Producer | `constitutional_architecture/compiler/pipeline.py:86-144` (`CompilerPipeline.compile`) |
| Consumer | `ValidationPass` (first pass) |
| Data type | `constitutional_architecture.isr.model.isr.ISR` → `constitutional_architecture.compiler.compiler_context.CompilerContext` |
| Adapter | None (direct call) |
| Serialization | `compiler_context.py` carries the ISR and the diagnostic collector |
| Validation | The ValidationPass is **fail-open** (line 21-30: returns `success=True` on exception) |
| Failure behavior | **Fail-open.** An internal exception in the validator produces `success=True` with diagnostic `COMP-VAL-003`. This is the audit's documented defect. |
| Provenance | The `PassContext` carries the ISR identity |

**Observation:** The Gen-C pipeline takes the **rich** `ISR` (System/Module/Entity model), not the canonical `ISRRevision`. This is a **mismatch** with the canonical runtime. The canonical runtime does not use the Gen-C pipeline.

#### Edge 2: `Pass` → `Pass` (within the 8-pass pipeline)

| Field | Value |
|---|---|
| Producer | `Pass` ABC (`constitutional_architecture/compiler/pass_interface.py`) |
| Consumer | Next pass (via `PassRegistry.resolved_order`) |
| Data type | `PassResult` (`success: bool`, `metrics: dict`, `description: str`) |
| Adapter | None |
| Serialization | In-memory |
| Validation | The PassManager `execute_all` records failures but **continues** (`constitutional_architecture/compiler/pass_manager.py:11-43`) |
| Failure behavior | **Continue-on-failure.** A failed pass produces a diagnostic error but the next pass still runs. The pipeline's overall success is `all_pass_succeeded and not has_errors`. |
| Provenance | The `PassResult.metrics` may carry provenance |

**Observation:** The Gen-C PassManager is **fail-open** (continue-on-failure). This is a documented audit defect. The canonical runtime does not use the PassManager.

#### Edge 3: `BIR` → `ArtifactSet`

| Field | Value |
|---|---|
| Producer | `constitutional_architecture/compiler/backends/fastapi_backend.py:73-86` |
| Consumer | (none in the canonical runtime) |
| Data type | `BIR` → `BackendResult(artifacts: list[Artifact], diagnostics: list)` |
| Adapter | None |
| Serialization | `Artifact` carries `path`, `content`, `artifact_type`, `backend` |
| Validation | `validate(bir) -> list[Diagnostic]` (returns `[]` — no-op) |
| Failure behavior | After R1-C C06, `compile()` does NOT call `self.write_files()`. The backend returns an `ArtifactSet` (in `BackendResult.artifacts`). The `write_files()` method is preserved as a packager utility. |
| Provenance | `Artifact.backend = "fastapi"`. The `Artifact` carries path and content. |

**Observation:** The Gen-C backend's `validate(bir) -> list[Diagnostic]` is a **no-op** (returns `[]`). This means the backend does not validate its input. The canonical `CompilerBackend` Protocol requires `compile(plan)` (not `validate`); the validation is done by `CHECKER.check(plan, ...)` in the canonical conformance layer.

---

## 4. Bypasses

### 4.1 Bypass 1: Direct ISR → backend (Gen-C)

```text
constitutional_architecture.isr.model.isr.ISR
  │
  │ (lowering pass)
  ▼
BIR
  │
  │ (FastAPIBackend.compile)
  ▼
BackendResult
```

This is a **constitutional-internal** path. It does not bypass the canonical Compiler IR because the Gen-C pipeline IS the constitutional Compiler IR (which is being retired).

**Assessment:** No architectural violation in the canonical runtime. The Gen-C path is on the retirement path (R1-D.5).

### 4.2 Bypass 2: Category compilers (per-category compilers)

```text
UniversalISR
  │
  │ (per-category compiler: backend, database, deployment, etc.)
  ▼
CompilationBundle
```

This is a **parallel** compiler runtime. The per-category compilers bypass the canonical `CompilationPlan` and produce a `CompilationBundle` directly. Per R1-A and INV-B14, per-category compilers do **not** become a new architectural authority. They are LEGACY and on the retirement path.

**Assessment:** Architectural violation in the constitutional substrate; canonical runtime is unaffected.

### 4.3 Bypass 3: Constitutional compiler bridge

```text
constitutional_architecture.isr.model.isr.ISR
  │
  │ (constitutional_architecture/engine/compiler_bridge.py:13-45)
  │   compile_evolved_isr(...)
  ▼
CompilationResult (never produced; dead code)
```

This is **dead code**. No callers. The bridge is being removed in R1-D.5.

**Assessment:** No current bypass. Classified for retirement.

---

## 5. Data flow summary

### 5.1 Canonical runtime data flow

```text
isr.core.revision.ISRRevision (canonical)
  │ (isr_to_plan)
  ▼
compiler.core.plan.CompilationPlan (stabilization)
  │ (CompilerBackend.compile)
  ▼
compiler.core.repository.GeneratedRepository
  │ (certification/stages/*)
  ▼
VerificationResult (5-state model)
  │ (EvidenceLedger)
  ▼
CertificationEvidence (hash-chained JSONL)
```

**Identity preservation:** Each step has a content-hash or versioned identity:
- `ISRRevision.content_hash` (SHA-256)
- `CompilationPlan.plan_id` (derived from ISR hash)
- `GeneratedRepository` (no content hash; structural conformance only)
- `VerificationResult` (UUIDv5 over subject + verifier + timestamp)
- `CertificationEvidence` (UUIDv5 over subject + verifier + result + timestamp + campaign ID; hash-chained)

### 5.2 Constitutional data flow (Gen-C)

```text
constitutional_architecture.isr.model.isr.ISR (rich)
  │ (8-pass pipeline; fail-open at validation and verification)
  ▼
BIR (no content hash; no provenance)
  │ (FastAPIBackend.compile; after R1-C C06: no filesystem write)
  ▼
BackendResult(artifacts: list[Artifact])
```

**Identity preservation:** The Gen-C path has **no deterministic identity** for the IR. `BIR` is a frozen dataclass with no hash. The `semantic_content_hash` is computed via `constitutional_architecture/isr/semantics/projection.py` (per R0 §5.3). The `Artifact` carries path and content but no content hash.

**Assessment:** The Gen-C path has **weaker identity preservation** than the canonical runtime. This is a known finding (R0).

---

## 6. Adapter analysis

| Boundary | Adapter | Direction | Notes |
|---|---|---|---|
| `ISRRevision` → `CompilationPlan` | None (direct function call) | canonical → canonical | The `isr_to_plan` function is the canonical lowering. No adapter. |
| `CompilationPlan` → `GeneratedRepository` | None (Protocol call) | canonical → canonical | The `CompilerBackend.compile` Protocol. No adapter. |
| `ISR` (rich) → `BIR` | Gen-C `LoweringPass` | constitutional → constitutional | The Gen-C lowering. On retirement path. |
| `BIR` → `ArtifactSet` | Gen-C `FastAPIBackend.compile` | constitutional → constitutional | After R1-C C06: no filesystem write. |
| `UniversalISR` → `CompilationBundle` | Per-category compilers | constitutional → constitutional | Parallel runtime. On retirement path. |
| `UniversalISR` → `ISRRevision` (if it exists) | None observed | n/a | No adapter found. |

**Observation:** The canonical runtime has **no adapters** — the flow is direct function calls within the canonical substrate. The constitutional runtime has internal lowering and emission but no canonical adapter.

---

## 7. Validation analysis

| Boundary | Validation | Fail-closed? |
|---|---|---|
| `ISRRevision` construction | `validate_invariants` (`isr/core/revision.py:50-52`) | **YES** (fail-closed; raises `ISRInvariantViolation`) |
| `CompilationPlan` construction | None (Pydantic frozen; no invariants) | **N/A** (no validation) |
| `isr_to_plan` | None (pure function) | **N/A** |
| `CompilerBackend.compile` | `CHECKER.check(plan, ...)` (`compiler/core/conformance.py:32-50`) — structural-only | **PARTIAL** (structural; behavioral in R1-E.8) |
| `constitutional_architecture.compiler.passes.validation_pass.py:7-31` | `try: ... except: success=True` | **NO (fail-open)** |
| `constitutional_architecture.compiler.passes.verification_pass.py:12-132` | `try: ... except: success=not has_errors` (WARNING) | **NO (fail-open)** |
| `constitutional_architecture.compiler.passes.normalization_pass.py:19-156` | Carries only 7 of 21 System fields | **NO (semantic loss)** |
| `PassManager.execute_all` | Records failure but continues | **NO (continue-on-failure)** |

**Observation:** The canonical runtime is fail-closed. The Gen-C pipeline is fail-open at three points (validation, verification, PassManager) and has semantic loss at one point (normalization). These are the documented audit findings (R0, R1-A).

---

## 8. Provenance analysis

| Surface | Provenance | Hash |
|---|---|---|
| `ISRRevision.content_hash` | `Provenance` (canonical; R1-D.1) | SHA-256 |
| `CompilationPlan.plan_id` | derived from `ISRRevision.content_hash[:16]` | None on plan itself |
| `GeneratedRepository` | None | None |
| `VerificationResult` | subject + verifier + timestamp | UUIDv5 |
| `CertificationEvidence` | subject + verifier + result + timestamp + campaign ID | UUIDv5 + SHA-256 hash chain |
| `BIR` | None | None (frozen dataclass; no hash) |
| `Artifact` | `path`, `content`, `artifact_type`, `backend` | None on artifact itself |

**Observation:** The canonical runtime preserves provenance end-to-end (ISR hash → plan id → verification → evidence). The Gen-C path has **no provenance** for the IR (BIR) or the artifacts. This is a known finding.

---

## 9. Failure behavior analysis

| Boundary | Failure mode | Handling |
|---|---|---|
| `ISRRevision` invalid | `validate_invariants` raises | Fail-closed (exception propagates) |
| `isr_to_plan` receives invalid ISR | Pure function; produces a `CompilationPlan` from whatever nodes are present | **Potential loss**: the partial lowering silently ignores 5 NodeType and 4 EdgeType |
| `CompilerBackend.compile` returns empty repo | Structural conformance fails | `ConformanceReport` indicates failure |
| Verifier internal exception | `VerificationResult.INDETERMINATE` (canonical) | Fail-closed (D10) |
| Verifier unsupported capability | `VerificationResult.INDETERMINATE` (D14) | Fail-closed |
| Gen-C validation pass exception | `success=True` (fail-open) | **VIOLATION** (audit finding) |
| Gen-C verification pass exception | `success=not has_errors` (WARNING; fail-open) | **VIOLATION** (audit finding) |
| Gen-C PassManager fail | Records error; continues | **VIOLATION** (continue-on-failure) |
| Gen-C normalization loss | Silently drops 14 of 21 System fields | **VIOLATION** (semantic loss) |

---

## 10. Architectural bypasses

| Bypass | Severity | Disposition |
|---|---|---|
| Gen-C pipeline (8-pass; fail-open) | P0 (in the constitutional substrate) | RETIRE (R1-D.5) |
| Per-category compilers (9; bypass CompilationPlan) | P0 (INV-B14) | RETIRE (R1-D.5) |
| compiler_bridge (dead code) | P3 (no callers) | RETIRE (R1-D.5; immediate) |

**No architectural bypasses in the canonical runtime.** The canonical runtime is a single, coherent flow from ISRRevision to CertificationEvidence.

---

## 11. Cross-references

- D2-D1: `folder/R1_D2_COMPILER_INVENTORY.md`
- D2-D3: `folder/R1_D2_COMPILER_IR_SEMANTIC_COMPARISON.md` (next)
- D07 (R1-B): `folder/CONTRACT_CanonicalCompilerIR.md`

---

*End of D2-D2. The R1-D.2 execution graph is complete. The canonical runtime is a single, coherent flow (ISRRevision → CompilationPlan → GeneratedRepository → VerificationResult → CertificationEvidence). The Gen-C path has 3 fail-open defects and 1 semantic-loss defect (documented audit findings). No architectural bypasses in the canonical runtime. D2-D3 (semantic comparison) follows.*
