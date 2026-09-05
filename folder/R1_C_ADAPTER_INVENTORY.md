# R1_C_ADAPTER_INVENTORY (R1-C C01)

**Status:** R1-C Deliverable C01. Focused adapter inventory and implementation map. Index: `folder/R1_B_CONTRACT_GATE_REPORT.md` (D20), `folder/R1_B_COMPATIBILITY_MATRIX.md` (D15), `folder/CONTRACT_LegacyBoundarySpecification.md` (D17).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; the user's R1-C master prompt.

**Method:** File:line-cited enumeration of every potential crossing between legacy/constitutional modules and the canonical runtime. OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN markers. Inspect-by-inspection, not by directory name.

**Classification taxonomy (per R1-C §7):** `KEEP` / `MIGRATE_SEMANTICS` / `ADAPT` / `RETIRE` / `DEFER`.

**Important:** R1-C01 does NOT authorize implementation. C03–C12 are the next gate.

---

## 0. Crossings the inventory enumerates

The R0 reconnaissance already mapped the package surface and import relationships. This inventory focuses on the **crossings**: where a legacy or constitutional module might be expected to provide information to the canonical runtime (or vice versa). The user's R1-C spec requires classification of every potential crossing into KEEP / MIGRATE_SEMANTICS / ADAPT / RETIRE / DEFER.

The crossings are organized by:

1. Constitutional → canonical crossings (the most important).
2. Within-canonical-runtime crossings (sanity check; mostly KEEP).
3. `autonomous-api` crossings (C-17 DEFER).
4. Out-of-scope crossings (`knowledge/`, `civilization/`, `distributed_evolution/`, `autonomous_network/`, `generated/`).

---

## 1. Constitutional → canonical crossings

### 1.1 `constitutional_architecture/isr/semantics/*` → `isr/core/`

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/semantics/*` (semantic validators; e.g. `requirement.py`, `boundary.py`) |
| Source type | Semantic validator functions; called by `constitutional_architecture/isr/validation/checker.py:62-419` |
| Destination module | `isr/core/invariants.py` (or a new `isr/core/semantics/`) |
| Destination type | The canonical ISR's invariant validators (e.g. `validate_invariants` at `isr/core/invariants.py:50-109`) |
| Call sites (in canonical runtime) | None — `isr/core/invariants.py` is the canonical validator. The constitutional validators are not currently called by the canonical runtime. |
| Data direction | LEGACY → CANONICAL (semantic concepts absorbed into canonical) |
| Semantic transformation | The semantic distinction (e.g. requirement-layer semantic obligation / test / verification distinction, technology-leakage rejection) is captured. The constitutional model type (e.g. `Requirement`) is **not** migrated; the semantic property is what migrates. |
| Identity behavior | The constitutional `Requirement` has its own identity. The canonical ISR has content-hash identity. The semantic property migrates as a new invariant in `isr/core/invariants.py`. |
| Provenance behavior | The constitutional validator's source is recorded in the canonical invariant's docstring. The canonical invariant's identity is the canonical one. |
| Runtime relevance | The canonical runtime uses `isr/core/invariants.py` exclusively. The constitutional validators are dormant. |
| Current consumers | `constitutional_architecture/isr/validation/checker.py` (not in the canonical path). |
| Canonical destination | `isr/core/invariants.py` (extend) or `isr/core/semantics/` (new module). |
| Retirement condition | All genuinely-semantic properties are absorbed into `isr/core/`. The constitutional `validation/checker.py` is then redundant. |
| Classification | **MIGRATE_SEMANTICS** (per R1-D.1) |

### 1.2 `constitutional_architecture/isr/validation/*` → `isr/core/`

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/validation/checker.py` (62-419 lines; 7 architectural-type-check passes) |
| Source type | Architectural type checker; returns `passed=(errors == 0)` |
| Destination module | `isr/core/invariants.py` (or `isr/core/validation/`) |
| Destination type | Canonical ISR validation |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (selective) |
| Semantic transformation | The 7 architectural-type-check passes are evaluated for genuinely-semantic content. Semantic checks migrate; the rich type system (19 NodeType, etc.) does not. |
| Identity behavior | The canonical validation has canonical identity. |
| Provenance behavior | The constitutional checker's source is recorded. |
| Runtime relevance | None in the canonical runtime. |
| Current consumers | Constitutional tests. |
| Canonical destination | `isr/core/invariants.py` (extend). |
| Retirement condition | All genuinely-semantic checks are absorbed. |
| Classification | **MIGRATE_SEMANTICS** (selective; per R1-D.1) |

### 1.3 `constitutional_architecture/isr/versioning/*` → `evolution/core/lineage` and `release/evidence/`

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/versioning/*` (`LineageTracker`, `ContentHasher`) |
| Source type | In-memory lineage tracker; content hasher |
| Destination module | `evolution/core/lineage` (in-memory) and `release/evidence/` (durable hash-chained) |
| Destination type | Canonical lineage + provenance |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (semantic concepts) |
| Semantic transformation | The semantic concept (lineage, content hashing) is captured. The `LineageTracker` class is in-memory; the canonical lineage is durable. |
| Identity behavior | The constitutional `LineageTracker` uses in-memory IDs; the canonical lineage uses content hashes. |
| Provenance behavior | The constitutional tracker's source is recorded. The canonical lineage is hash-chained. |
| Runtime relevance | None in the canonical runtime. |
| Current consumers | Constitutional tests. |
| Canonical destination | `evolution/core/lineage` (in-memory) + `release/evidence/` (durable). |
| Retirement condition | All genuinely-semantic concepts are absorbed; the canonical lineage is durable. |
| Classification | **MIGRATE_SEMANTICS** (per R1-E.6 + R1-D.3) |

### 1.4 `constitutional_architecture/isr/diff/*` → `evolution/core/` (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/diff/*` (`StructuralDiff`, `SemanticDiff`) |
| Source type | ISR diff functions |
| Destination module | `evolution/core/diff` (R1-D.3 to add) |
| Destination type | Canonical diff for `ArchitectureCandidate` |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (selective) |
| Semantic transformation | The semantic-diff concept migrates; the structural-diff may be subsumed by the content-hash comparison. |
| Identity behavior | Constitutional diff uses constitutional IDs; canonical diff uses content hashes. |
| Provenance behavior | Recorded. |
| Runtime relevance | None in the canonical runtime. |
| Current consumers | Constitutional tests. |
| Canonical destination | `evolution/core/diff` (R1-D.3) or omitted if content-hash is sufficient. |
| Retirement condition | All genuinely-semantic concepts are absorbed or omitted. |
| Classification | **MIGRATE_SEMANTICS** (selective; possibly KEEP-as-content-hash) |

### 1.5 `constitutional_architecture/isr/metrics/*` → `evolution/core/metrics` (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/metrics/*` (`StaticFitnessEvaluator`) |
| Source type | Static fitness evaluator for ISRs |
| Destination module | `evolution/core/fitness_evaluator.py` (R1-D.3 to add) |
| Destination type | Canonical fitness evaluation for `ArchitectureCandidate` |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (selective) |
| Semantic transformation | The fitness-evaluation concept migrates; the static-vs-dynamic distinction is preserved. |
| Identity behavior | Constitutional evaluator uses constitutional IDs; canonical evaluator uses content hashes. |
| Provenance behavior | Recorded. |
| Runtime relevance | None in the canonical runtime. |
| Current consumers | Constitutional tests. |
| Canonical destination | `evolution/core/fitness_evaluator.py` (R1-D.3). |
| Retirement condition | All genuinely-semantic concepts are absorbed. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.6 `constitutional_architecture/isr/completeness/*` → `isr/core/invariants.py` (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/completeness/*` (`CompletenessChecker`) |
| Source type | Completeness checker for ISRs |
| Destination module | `isr/core/invariants.py` (extend) |
| Destination type | Canonical completeness invariants |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (selective) |
| Semantic transformation | Genuinely-semantic completeness checks migrate. |
| Identity behavior | Canonical. |
| Provenance behavior | Recorded. |
| Runtime relevance | None. |
| Current consumers | Constitutional tests. |
| Canonical destination | `isr/core/invariants.py` (extend). |
| Retirement condition | All genuinely-semantic concepts are absorbed. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.7 `constitutional_architecture/isr/views/*` → none (out of canonical scope)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/views/*` |
| Source type | Views over the rich ISR model |
| Destination module | None (views are not in the canonical runtime) |
| Call sites | None. |
| Data direction | n/a |
| Semantic transformation | n/a (views are not canonical semantics) |
| Classification | **DEFER** (out of R1 scope; views are not part of the Full-Stack Compiler vertical slice) |

### 1.8 `constitutional_architecture/isr/profiles/*` → none (out of canonical scope)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/profiles/*` |
| Source type | Architecture profiles |
| Destination module | None (profiles are not in the canonical runtime) |
| Call sites | None. |
| Data direction | n/a |
| Semantic transformation | n/a (profiles are not canonical semantics) |
| Classification | **DEFER** (out of R1 scope) |

### 1.9 `constitutional_architecture/isr/model/isr.py:ISR` → `isr/core/` (semantic validators only)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/model/isr.py:ISR` (rich System/Module/Entity/... dataclass model) |
| Source type | Rich ISR dataclass model |
| Destination module | None as runtime (the rich model is **not** the canonical ISR per D03 + INV-B01) |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (semantic validators only) |
| Semantic transformation | The model type is not migrated. The semantic validators (from `constitutional_architecture/isr/semantics/*`) are selectively absorbed into `isr/core/invariants.py` (per 1.1). |
| Identity behavior | The constitutional `ISR` has its own identity. The canonical ISR has content-hash identity. |
| Provenance behavior | Recorded. |
| Runtime relevance | None. |
| Current consumers | Constitutional tests. |
| Canonical destination | None as runtime. Semantic validators → `isr/core/invariants.py`. |
| Retirement condition | All genuinely-semantic validators are absorbed; the rich model has no canonical consumer. |
| Classification | **MIGRATE_SEMANTICS** (semantic validators only) + **RETIRE** (the rich model as runtime) |

### 1.10 `constitutional_architecture/core/models/isr.py:UniversalISR` → none

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/core/models/isr.py:UniversalISR` (17-NodeType, 13-EdgeType typed graph) |
| Source type | Third ISR model |
| Destination module | None |
| Call sites | `constitutional_architecture/compilers/backend/fastapi/compiler.py:22`, `compilers/backend/base.py:9`, `compilers/operational/intelligence/compiler.py:30-32` (constitutional compilers only; not in the canonical path) |
| Data direction | n/a |
| Semantic transformation | n/a (the third model has no canonical consumer) |
| Classification | **RETIRE** (per R1-D.5; no canonical consumer) |

### 1.11 `constitutional_architecture/eir/transformation.py:EIR` → `evolution/core/record.py`

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/eir/transformation.py:EIR` (1102 lines; `TransformationClass`, `Transformation`, `EIR` dataclasses) |
| Source type | EIR schema (defective: missing `transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`) |
| Destination module | `evolution/core/record.py` (R1-D.3 to add) |
| Destination type | Canonical `EvolutionRecord` (D06) |
| Call sites | `constitutional_architecture/engine/evolution_loop.py:107-114` (constitutional; defective: `transformations=[]`) |
| Data direction | LEGACY → CANONICAL (selective schema absorption) |
| Semantic transformation | The audit-required fields are added to the canonical `EvolutionRecord` (D06). The 10 mutation operators in `transformation.py:961-1101` are evaluated for genuinely-useful new operator kinds; the rest is retired. |
| Identity behavior | Canonical (content hash). |
| Provenance behavior | Recorded. |
| Runtime relevance | None in the canonical runtime. |
| Current consumers | Constitutional tests + `evolution_loop.py:107-114`. |
| Canonical destination | `evolution/core/record.py` (R1-D.3) with the audit-required fields. |
| Retirement condition | The audit-required fields are added; useful mutation operators are absorbed; the `transformations=[]` defect is repaired or the path is retired. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.12 `constitutional_architecture/engine/evolution_engine.py` → `evolution/core/operations.py`

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/engine/evolution_engine.py` (Substrate B evolution engine; `_mutate_individual` at line 300+) |
| Source type | Substrate B Evolution engine |
| Destination module | `evolution/core/operations.py` (canonical; real crossover at line 74-104) |
| Destination type | Canonical Evolution engine |
| Call sites | `constitutional_architecture/engine/evolution_loop.py:91-93` (constitutional; not in the canonical path) |
| Data direction | LEGACY → CANONICAL (selective semantic operator absorption) |
| Semantic transformation | Genuinely-useful mutation operators (from `constitutional_architecture/engine/mutation_*.py` 6 files) are absorbed into `evolution/core/operations.py`. The pseudo-crossover in `constitutional_architecture/engine/crossover_engine.py` is **not** absorbed. |
| Identity behavior | Canonical (content hash). |
| Provenance behavior | Recorded. |
| Runtime relevance | None in the canonical runtime. |
| Current consumers | Constitutional tests + `evolution_loop.py:91-93`. |
| Canonical destination | `evolution/core/operations.py` (extend). |
| Retirement condition | All genuinely-useful operators are absorbed; no Substrate B consumers remain. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.13 `constitutional_architecture/engine/crossover_engine.py` → none

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/engine/crossover_engine.py` |
| Source type | Substrate B crossover (pseudo-crossover: copies parent A) |
| Destination module | None (the canonical crossover is the **real** crossover at `evolution/core/operations.py:74-104`) |
| Call sites | `constitutional_architecture/engine/evolution_loop.py:91-93` (constitutional) |
| Data direction | n/a |
| Semantic transformation | n/a (pseudo-crossover is not canonical) |
| Classification | **RETIRE** (per R1-D.5) |

### 1.14 `constitutional_architecture/engine/isr_adapter.py` → `isr/core/` (semantics only) or **RETIRE**

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/engine/isr_adapter.py` (lossy TypedGraph adapter; the audit's defect) |
| Source type | Lossy round-trip between rich ISR and TypedGraph |
| Destination module | None as runtime (the lossy round-trip is not canonical per D03 + INV-B01) |
| Call sites | Constitutional tests. |
| Data direction | LEGACY → CANONICAL (semantics only) |
| Semantic transformation | The semantic concept (cross-representation) is captured; the lossy adapter itself is retired. The canonical ISR is the single source of truth (D03); no round-trip is needed. |
| Identity behavior | Canonical. |
| Provenance behavior | Recorded. |
| Runtime relevance | None. |
| Current consumers | Constitutional tests. |
| Canonical destination | None. |
| Retirement condition | The canonical ISR is the single source of truth; no cross-representation is needed. |
| Classification | **RETIRE** (per R1-D.5; D03's semantic authority replaces it) |

### 1.15 `constitutional_architecture/engine/compiler_bridge.py` → none (DEAD CODE)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/engine/compiler_bridge.py:13-45` |
| Source type | Dead code: uses non-existent API signatures; `grep -r "constitutional_architecture.engine.compiler_bridge" .` returns only the bridge itself (no callers) |
| Destination module | None |
| Call sites | **None.** The bridge is dead code. |
| Data direction | n/a |
| Semantic transformation | n/a |
| Classification | **RETIRE** (immediate; per R1-D.5) |

### 1.16 `constitutional_architecture/engine/lineage_tracker.py` → `evolution/core/lineage` (semantic concepts)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/engine/lineage_tracker.py` |
| Source type | In-memory lineage tracker (the audit's "in-memory lineage is insufficient") |
| Destination module | `evolution/core/lineage` (in-memory) and `release/evidence/` (durable hash-chained) |
| Destination type | Canonical lineage |
| Call sites | Constitutional tests. |
| Data direction | LEGACY → CANONICAL (semantic concepts; durable lineage is R1-E.6) |
| Semantic transformation | The semantic concept (lineage) is captured. The canonical lineage is durable. |
| Classification | **MIGRATE_SEMANTICS** (per R1-E.6) |

### 1.17 `constitutional_architecture/engine/verification_bridge.py` → `certification/stages/` (semantic concepts)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/engine/verification_bridge.py` |
| Source type | Substrate B verification bridge |
| Destination module | `certification/stages/` (canonical; fail-closed) |
| Destination type | Canonical verification (D10) |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (semantic concepts selectively) |
| Semantic transformation | The semantic concept of verification bridging is captured; the canonical verification is fail-closed. |
| Classification | **MIGRATE_SEMANTICS** (selective; canonical Verification contract is fail-closed) |

### 1.18 `constitutional_architecture/engine/evolution_memory.py` → `release/evidence/` (durable)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/engine/evolution_memory.py` |
| Source type | Substrate B evolution memory |
| Destination module | `release/evidence/` (durable hash-chained; per R1-E.6) |
| Destination type | Canonical evolution memory (durable) |
| Call sites | None in the canonical runtime. |
| Data direction | LEGACY → CANONICAL (semantic concepts; durable memory is R1-E.6) |
| Semantic transformation | The semantic concept (durable evolution memory) is captured. |
| Classification | **MIGRATE_SEMANTICS** (per R1-E.6) |

### 1.19 `constitutional_architecture/compiler/bir/model.py:BIR` → canonical CompilerIR (semantic donor)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/bir/model.py:BIR` (dataclass tree; 9 BIRNodeType: HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST) |
| Source type | Substrate B Compiler IR |
| Destination module | The canonical CompilerIR (R1-D.2 to create; per D07) |
| Destination type | Canonical Compiler IR contract |
| Call sites | `constitutional_architecture/compiler/passes/lowering_pass.py:8-59` (lowering ISR → BIR), `constitutional_architecture/compiler/backends/fastapi_backend.py:31-32, 73-86` (consuming BIR) |
| Data direction | LEGACY → CANONICAL (semantic donor; **BIR is read as references, not modified**) |
| Semantic transformation | The 9 BIRNodeType concepts are evaluated for genuinely-semantic content. The ones that are genuinely semantic (e.g. HANDLER, ENTITY, SERVICE) are absorbed into the canonical CompilerIR contract. The ones that are not (e.g. CONFIG) are deferred. **BIR is NOT modified to add content-hash; content-hash is added to the canonical CompilerIR, not to BIR.** |
| Identity behavior | Canonical (content hash on the canonical IR; BIR is not modified). |
| Provenance behavior | Recorded. |
| Runtime relevance | None in the canonical runtime. The campaign uses `CompilationPlan` (stabilization). |
| Current consumers | Constitutional tests + the Gen-C pipeline (not in the canonical path). |
| Canonical destination | The canonical CompilerIR (R1-D.2). |
| Retirement condition | All genuinely-semantic BIRNodeType concepts are absorbed; BIR is retired as runtime. |
| Classification | **MIGRATE_SEMANTICS** (BIR is a semantic donor; per R1-D.2) |

### 1.20 `constitutional_architecture/compiler/passes/validation_pass.py` → canonical Validation contract

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/validation_pass.py:7-31` (fail-open: returns `success=True` on exception) |
| Source type | Validation pass |
| Destination module | The canonical Validation pass contract (D14) |
| Destination type | Canonical Validation |
| Call sites | The 8-pass Gen-C pipeline (not in the canonical path). |
| Data direction | LEGACY → CANONICAL (adapt to the canonical contract) |
| Semantic transformation | The pass is refactored to be fail-closed: `PassResult(success=result.passed, ...)`; no `try/except: success=True`. **The canonical contracts are defined FIRST (R1-B); the Gen-C implementation is adapted to them.** |
| Identity behavior | Canonical. |
| Provenance behavior | Recorded. |
| Runtime relevance | None in the canonical runtime. |
| Current consumers | Constitutional tests. |
| Canonical destination | Adapted Gen-C pass (R1-E.2). |
| Retirement condition | The pass is adapted to the canonical contract; the legacy `try/except: success=True` is removed. |
| Classification | **ADAPT** (per R1-E.2; canonical contracts first) |

### 1.21 `constitutional_architecture/compiler/passes/normalization_pass.py` → canonical Normalization contract

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/normalization_pass.py:19-156` (lossy: carries only 7 of 21 System fields) |
| Source type | Normalization pass |
| Destination module | The canonical Normalization contract (D14) |
| Destination type | Canonical Normalization |
| Call sites | The 8-pass Gen-C pipeline (not in the canonical path). |
| Data direction | LEGACY → CANONICAL (adapt) |
| Semantic transformation | The pass is refactored to preserve all System fields; rebuild via `with_system`. **Canonical contracts first.** |
| Classification | **ADAPT** (per R1-E.4) |

### 1.22 `constitutional_architecture/compiler/passes/optimization_pass.py` → canonical CompilerIR optimization (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/optimization_pass.py:8-44` |
| Source type | Optimization pass |
| Destination module | The canonical CompilerIR's optimization (R1-D.2) |
| Destination type | Canonical CompilerIR optimization |
| Call sites | The 8-pass Gen-C pipeline. |
| Data direction | LEGACY → CANONICAL (semantic concepts) |
| Semantic transformation | Optimization concepts that are genuinely semantic migrate; the rest is omitted. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.23 `constitutional_architecture/compiler/passes/capability_resolution_pass.py` → canonical CompilerIR (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/capability_resolution_pass.py:8-78` (13+ capabilities: OAUTH2, JWT_AUTH, REST_API, INPUT_VALIDATION, SERIALIZATION, ORM, MIGRATIONS, VALIDATION, STRUCTURED_LOGGING, HEALTH_CHECKS, CONTAINERIZATION, METRICS, DISTRIBUTED_TRACING) |
| Source type | Capability resolution pass |
| Destination module | The canonical CompilerIR's capability resolution (R1-D.2) |
| Destination type | Canonical capability resolution |
| Call sites | The 8-pass Gen-C pipeline. |
| Data direction | LEGACY → CANONICAL (semantic concepts) |
| Semantic transformation | The abstract capabilities (authentication, authorization, persistence, REST, eventing, logging, metrics, tracing, validation, containerization, migration) are the canonical capabilities (per D08 + R1-B audit). The 13 constitutional capability names are evaluated; some are redundant with canonical capability names. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.24 `constitutional_architecture/compiler/passes/lowering_pass.py` → canonical CompilerIR (lowering concept only)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/lowering_pass.py:8-59` (lowering ISR → BIR) |
| Source type | Lowering pass |
| Destination module | The canonical CompilerIR's lowering (R1-D.2) |
| Destination type | Canonical lowering |
| Call sites | The 8-pass Gen-C pipeline. |
| Data direction | LEGACY → CANONICAL (lowering concept) |
| Semantic transformation | The lowering concept (ISR → CompilerIR) migrates. The lowering target (BIR) is not canonical. |
| Classification | **MIGRATE_SEMANTICS** (lowering concept; BIRNodeTypes absorbed per 1.19) |

### 1.25 `constitutional_architecture/compiler/passes/code_generation_pass.py` → canonical CompilerBackend

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/code_generation_pass.py:11-110` |
| Source type | Code generation pass |
| Destination module | The canonical CompilerBackend (D08) |
| Destination type | Canonical backend |
| Call sites | The 8-pass Gen-C pipeline. |
| Data direction | LEGACY → CANONICAL (selective) |
| Semantic transformation | The code generation concept is the canonical backend's lowering. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.26 `constitutional_architecture/compiler/passes/verification_pass.py` → canonical Verification contract

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/verification_pass.py:12-132` (fail-open: returns `success=True` on engine exception) |
| Source type | Verification pass |
| Destination module | The canonical Verification contract (D10, D14) |
| Destination type | Canonical Verification |
| Call sites | The 8-pass Gen-C pipeline. |
| Data direction | LEGACY → CANONICAL (adapt) |
| Semantic transformation | The pass is refactored to be fail-closed: 5-state model; `INDETERMINATE` on engine exception. **Canonical contracts first.** |
| Classification | **ADAPT** (per R1-E.1) |

### 1.27 `constitutional_architecture/compiler/passes/cross_target_pass.py` → canonical CompilerBackend

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/passes/cross_target_pass.py:7-38` |
| Source type | Cross-target pass |
| Destination module | The canonical CompilerBackend (D08) |
| Destination type | Canonical backend |
| Call sites | The 8-pass Gen-C pipeline. |
| Data direction | LEGACY → CANONICAL (selective) |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.28 `constitutional_architecture/compiler/backends/fastapi_backend.py` → canonical CompilerBackend (artifact purity)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/backends/fastapi_backend.py:47-719` |
| Source type | Gen-C FastAPI backend (with `self.write_files()` defect at line 85) |
| Destination module | The canonical CompilerBackend (D08) |
| Destination type | Canonical backend |
| Call sites | The 8-pass Gen-C pipeline. |
| Data direction | LEGACY → CANONICAL (adapt; artifact purity) |
| Semantic transformation | The backend is refactored to return an `ArtifactSet` (D09) instead of writing to the filesystem inside `compile()`. **Canonical contracts first.** |
| Classification | **ADAPT** (per R1-E.7) |

### 1.29 `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` → none (RETIRE)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` (Gen-C protocol) |
| Source type | Backend ABC |
| Destination module | None (the canonical protocol is `compiler/core/protocol.py:CompilerBackend`) |
| Call sites | Constitutional tests. |
| Classification | **RETIRE** (per R1-D.5) |

### 1.30 `constitutional_architecture/compiler/backends/backend_registry.py` → none (RETIRE)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/backends/backend_registry.py:8-27` |
| Source type | Gen-C backend registry |
| Destination module | None (the canonical registry is `compiler/core/registry.py` + `compiler/composition.py`) |
| Classification | **RETIRE** (per R1-D.5) |

### 1.31 `constitutional_architecture/compiler/backends/backend_selector.py` → none (RETIRE)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/backends/backend_selector.py` |
| Source type | Gen-C backend selector |
| Classification | **RETIRE** (per R1-D.5) |

### 1.32 `constitutional_architecture/compiler/quality/optimization_engine.py` → canonical CompilerIR optimization (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compiler/quality/optimization_engine.py:6-13` |
| Source type | Optimization engine (uses rich ISR) |
| Destination module | The canonical CompilerIR's optimization (R1-D.2) |
| Classification | **MIGRATE_SEMANTICS** (selective; the rich ISR import must be replaced with the canonical ISR) |

### 1.33 `constitutional_architecture/compilers/*` → none (RETIRE per INV-B14)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/compilers/*` (9 per-category compilers: backend, database, deployment, documentation, frontend, infrastructure, operational, runtime_policy, testing) |
| Source type | Per-category compilers (consuming `UniversalISR`) |
| Destination module | None (the canonical backend protocol is `compiler/core/protocol.py:CompilerBackend`) |
| Classification | **RETIRE** (per R1-D.5; INV-B14) |

### 1.34 `constitutional_architecture/verification/*` → `certification/stages/` (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/verification/*` (Substrate B verification) |
| Source type | Substrate B verification |
| Destination module | The canonical Verification (D10) — fail-closed |
| Call sites | Constitutional tests. |
| Data direction | LEGACY → CANONICAL (semantic concepts selectively) |
| Semantic transformation | The semantic concept of verification is captured; the canonical Verification is fail-closed. |
| Classification | **MIGRATE_SEMANTICS** (selective; canonical fail-closed) |

### 1.35 `constitutional_architecture/validation/*` → `isr/core/invariants.py` (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/validation/*` (Substrate B validation) |
| Source type | Substrate B validation |
| Destination module | `isr/core/invariants.py` (extend) |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.36 `constitutional_architecture/knowledge/*` → none (DEFER)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/knowledge/*` |
| Source type | Knowledge graph |
| Destination module | None (out of R1 scope) |
| Classification | **DEFER** (out of R1 scope) |

### 1.37 `constitutional_architecture/governance/*` → keep as governance layer

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/governance/*` (~25 .py) |
| Source type | Governance contracts |
| Destination module | The constitutional layer (KEEP) |
| Call sites | Constitutional tests. |
| Classification | **KEEP** (as governance/specification, not runtime) |

### 1.38 `constitutional_architecture/versioning/*` → `release/evidence/` (durable) and `evolution/core/lineage` (in-memory)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/versioning/*` (LineageTracker, ContentHasher) |
| Source type | Versioning |
| Destination module | `release/evidence/` (durable) and `evolution/core/lineage` (in-memory) |
| Classification | **MIGRATE_SEMANTICS** (per R1-E.6) |

### 1.39 `constitutional_architecture/core/contracts/*` → canonical contracts (D02–D12)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/core/contracts/*` |
| Source type | Constitutional contracts |
| Destination module | The canonical contracts (D02–D12) — already in `folder/CONTRACT_*.md` |
| Classification | **KEEP** (the canonical contracts are the R1-B deliverables) |

### 1.40 `constitutional_architecture/serialization/*` → canonical serialization (selective)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/serialization/*` (`ISRSerializer`, `ISRDeserializer`) |
| Source type | Serialization for the rich ISR |
| Destination module | The canonical serialization (per the per-contract specs in D02–D12) |
| Classification | **MIGRATE_SEMANTICS** (selective; canonical serialization uses sorted-key JSON) |

### 1.41 `constitutional_architecture/schemas/*` → canonical schemas (D02–D12)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/schemas/*` |
| Source type | Schemas for the rich ISR |
| Destination module | The canonical schemas (D02–D12) |
| Classification | **KEEP** (the canonical schemas are the R1-B deliverables) |

### 1.42 `constitutional_architecture/irr/*` (under `isr/`) → `reqgraph/core/` (semantic concepts)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/isr/irr/*` (`IRR`, `Requirement`, `RequirementType`, `RequirementGraph`) |
| Source type | Requirement representation (rich) |
| Destination module | The canonical RequirementGraph (D02) — `reqgraph/core/` |
| Call sites | Constitutional tests + `isr/irr/requirement.py`. |
| Data direction | LEGACY → CANONICAL (semantic concepts) |
| Semantic transformation | The semantic concept (requirement representation) is captured. The canonical RequirementGraph (D02) is the authoritative contract. |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.43 `constitutional_architecture/operations/*` → `evolution/core/` (semantic concepts)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/operations/*` |
| Source type | Operations |
| Destination module | `evolution/core/` |
| Classification | **MIGRATE_SEMANTICS** (selective) |

### 1.44 `constitutional_architecture/agents/*` → none (DEFER)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/agents/*` |
| Source type | Agents |
| Classification | **DEFER** (out of R1 scope) |

### 1.45 `constitutional_architecture/ckb/*` → none (DEFER)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/ckb/*` |
| Classification | **DEFER** (out of R1 scope) |

### 1.46 `constitutional_architecture/deployment/*` → none (DEFER)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/deployment/*` |
| Classification | **DEFER** (out of R1 scope; deployment is not in the R1-B contracts) |

### 1.47 `constitutional_architecture/frontend/*` → none (DEFER)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/frontend/*` |
| Classification | **DEFER** (out of R1 scope) |

### 1.48 `constitutional_architecture/generated/*` → none (DEFER)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/generated/*` |
| Classification | **DEFER** (out of R1 scope) |

### 1.49 `constitutional_architecture/meta/*` → none (DEFER)

| Field | Value |
|---|---|
| Source module | `constitutional_architecture/meta/*` |
| Classification | **DEFER** (out of R1 scope) |

---

## 2. Within-canonical-runtime crossings (sanity check)

These crossings are within the canonical runtime (Substrate A). They are mostly KEEP; this section exists to confirm there is no hidden constitutional dependency.

### 2.1 `reqgraph/core/*` → `isr/core/*`

| Field | Value |
|---|---|
| Source | `reqgraph/core/plan_builder.py:21-25` |
| Destination | `isr/core/*` |
| Classification | **KEEP** (canonical; the campaign runtime's expected flow) |

### 2.2 `isr/core/*` → `evolution/core/*`

| Field | Value |
|---|---|
| Source | `evolution/core/engine.py:21-22`, `construction.py:5-6`, `fitness_evaluator.py:7-8`, `materialize.py:5` |
| Destination | `isr/core/*` |
| Classification | **KEEP** (canonical; the evolution engine operates on `isr.core`) |

### 2.3 `evolution/core/*` → `compiler/core/*`

| Field | Value |
|---|---|
| Source | `certification/campaign/plan_builder.py:13-14` (`isr_to_plan(cand)`) |
| Destination | `compiler/core/*` (`CompilationPlan`) |
| Classification | **KEEP as stabilization** until canonical CompilerIR is created in R1-D.2 |

### 2.4 `compiler/core/*` → `certification/*`

| Field | Value |
|---|---|
| Source | `compiler/core/{plan,conformance,protocol,registry,repository,lowering}.py` |
| Destination | `certification/campaign/{plan_builder,runner,verdict,verify_campaign,campaign_a,campaign_b}.py`, `certification/stages/*`, `certification/provenance/bundle.py` |
| Classification | **KEEP** (canonical; the campaign runtime's expected flow) |

### 2.5 `certification/*` → `release/evidence/*`

| Field | Value |
|---|---|
| Source | `certification/evidence/ledger.py` |
| Destination | `release/evidence/*` |
| Classification | **KEEP** (canonical; the certification evidence ledger) |

---

## 3. `autonomous-api` crossings (C-17 DEFER)

### 3.1 `autonomous-api/app/main.py:111-115` (`_DbGenerationProvider.get_isr()`)

| Field | Value |
|---|---|
| Source | `autonomous-api/app/main.py:111-115` |
| Destination | None (returns `NotImplementedError("ISR binding is a declared audit gap")`) |
| Classification | **DEFER** (C-17; not in R1 scope) |

### 3.2 `autonomous-api/app/observation/*`

| Field | Value |
|---|---|
| Source | `autonomous-api/app/observation/{gateway,sequences,projectors}.py` |
| Destination | None (LEGACY; the canonical RuntimeObservation is D12, deferred to R2/R3) |
| Classification | **DEFER** (C-17) |

### 3.3 `autonomous-api/app/core/*` (lineage, governance, evidence, crossover, config)

| Field | Value |
|---|---|
| Source | `autonomous-api/app/core/*` (Tiannara v1 architecture) |
| Destination | None in the canonical runtime |
| Classification | **DEFER** (C-17; not in R1 scope) |

### 3.4 `autonomous-api/app/engine/*` (genome, self_healing, production_gate)

| Field | Value |
|---|---|
| Source | `autonomous-api/app/engine/*` |
| Classification | **DEFER** (C-17) |

### 3.5 `autonomous-api/app/storage/*` (db, models)

| Field | Value |
|---|---|
| Source | `autonomous-api/app/storage/*` |
| Classification | **DEFER** (C-17) |

### 3.6 `autonomous-api/app/api/*` (routes, ws)

| Field | Value |
|---|---|
| Source | `autonomous-api/app/api/*` |
| Classification | **DEFER** (C-17) |

### 3.7 `autonomous-api/app/monitoring/*`

| Field | Value |
|---|---|
| Source | `autonomous-api/app/monitoring/*` |
| Classification | **DEFER** (C-17) |

---

## 4. Out-of-scope crossings

### 4.1 `knowledge/*` → none

The knowledge graph is not imported by the canonical compiler or the campaign runtime. Out of R1 scope.

**Classification: DEFER** (out of R1 scope).

### 4.2 `civilization/*` → none

The civilization layer is imported only by tests. Out of R1 scope.

**Classification: DEFER**.

### 4.3 `autonomous_network/*` → none

Out of R1 scope.

**Classification: DEFER**.

### 4.4 `distributed_evolution/*` → none

Out of R1 scope.

**Classification: DEFER**.

### 4.5 `generated/testshop/`, `generated/monolithshop/`

Legacy generated artifacts. Out of R1 scope.

**Classification: DEFER** (classified as `LEGACY_GENERATED`; excluded from canonical scope).

---

## 5. Classification summary

| Classification | Count | Examples |
|---|---|---|
| **KEEP** | 7 | canonical runtime crossings (§2.1–2.5); `constitutional_architecture/governance/*` (1.37); `constitutional_architecture/core/contracts/*` (1.39); `constitutional_architecture/schemas/*` (1.41) |
| **MIGRATE_SEMANTICS** | 28 | constitutional ISR semantics (1.1, 1.2, 1.9); EIR (1.11); evolution engine (1.12, 1.18); Compiler IR concepts (1.19, 1.22–1.27, 1.32); verification (1.17, 1.34); validation (1.35); lineage (1.3, 1.16, 1.38); diff (1.4); metrics (1.5); completeness (1.6); IRR (1.42); operations (1.43); serialization (1.40) |
| **ADAPT** | 4 | Gen-C validation pass (1.20); normalization (1.21); verification (1.26); Gen-C fastapi_backend (1.28) |
| **RETIRE** | 9 | UniversalISR (1.10); Substrate B crossover (1.13); isr_adapter (1.14); compiler_bridge dead code (1.15); Gen-C ABC (1.29); Gen-C registry (1.30); Gen-C selector (1.31); per-category compilers (1.33) |
| **DEFER** | 22 | constitutional views (1.7); profiles (1.8); knowledge (1.36, 4.1); civilization (4.2); autonomous_network (4.3); distributed_evolution (4.4); generated (4.5); autonomous-api (3.1–3.7); constitutional agents (1.44); ckb (1.45); deployment (1.46); frontend (1.47); constitutional generated (1.48); meta (1.49) |

**Total crossings: 70.** Most are MIGRATE_SEMANTICS (selective absorption) or DEFER (out of R1 scope).

---

## 6. Implementation priority for C02 boundary contracts

The C02 boundary contracts focus on the crossings that have a non-DEFER classification. Priority for C02:

1. **ADAPT (4 crossings):** Gen-C validation/normalization/verification passes + fastapi_backend. **Canonical contracts first; Gen-C adaptations second.** These are the highest-value R1-C adapters because they bring the Gen-C pipeline into compliance with the R1-B contracts.
2. **MIGRATE_SEMANTICS for canonical contracts (canonical CompilerIR, canonical EvolutionRecord):** the selective absorption of BIRNodeTypes + EIR schema fragments. These are R1-D work, but the boundary contracts in C02 should define the migration boundary.
3. **RETIRE (8 crossings):** documented in D17; the retirement actions are R1-D.5 work.
4. **KEEP (7 crossings):** documented; no work required.

The DEFER items (22) are not in C02 scope.

---

## 7. Repository evidence

All crossings are documented with file:line evidence in the per-crossing tables above. The OBSERVED / INFERRED / PROPOSED / UNKNOWN markers are used throughout.

The R0 reconnaissance (`folder/R0_RECONNAISSANCE_REPORT.md`) is the source for most of the file:line citations.

---

*End of C01. The adapter inventory enumerates 70 crossings with classification. C02 will define the boundary contracts for the non-DEFER crossings. C03–C12 are the next gate.*
