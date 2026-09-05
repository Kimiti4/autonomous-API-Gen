# R1_B_COMPATIBILITY_MATRIX (R1-B D15)

**Status:** R1-B Deliverable D15. The compatibility matrix mapping each canonical contract to its current A implementation and constitutional B implementation, with KEEP / MIGRATE / ADAPT TEMPORARILY / RETIRE / DEFER actions.

**Authority:** R1-A canonical substrate decision (`folder/CANONICAL_SUBSTRATE_DECISION.md`), R1-B D01 (registry), D02–D12 (per-contract specs).

---

## 1. Purpose

The compatibility matrix is the gate between R1-B (contract-only) and R1-C (adapters + migration). For each canonical contract, it identifies the current A implementation, the constitutional B implementation(s), and the action to take — KEEP, MIGRATE, ADAPT TEMPORARILY, RETIRE, or DEFER — with rationale.

## 2. Action taxonomy

| Action | Meaning |
|---|---|
| `KEEP` | The A implementation is the canonical contract; no change. |
| `MIGRATE` | B's semantic properties are extracted and absorbed into A; B is retired. |
| `ADAPT TEMPORARILY` | B is wrapped in a `LEGACY → CANONICAL` adapter during the migration window; B is retired when the adapter is no longer needed. |
| `RETIRE` | B has no value; it is removed (after the canonical replacement is verified). |
| `DEFER` | B is out of R1 scope; it is addressed in R2/R3 or a later phase. |

## 3. The matrix

### C01 RequirementGraph

| Field | Value |
|---|---|
| Canonical contract | `RequirementGraph` (D02) |
| Current A | `reqgraph/core/graph.py:25-44` — 4 edge types (DEPENDS_ON, CONFLICTS_WITH, REFINES, OWNED_BY) |
| Constitutional B | None observed in the canonical execution path. The audit's reference to 8 edge types is not in any code path. |
| Action | **KEEP** |
| Rationale | The A implementation is the canonical contract. No migration is required. |
| Migration destination | n/a (canonical from inception) |
| Status | KEEP — frozen at `reqgraph/core/graph.py:25-44` |

### C02 ISR

| Field | Value |
|---|---|
| Canonical contract | `ISR` (D03) |
| Current A | `isr/core/{graph,identity,invariants,revision}.py` — 9 NodeType, 8 EdgeType, frozen Pydantic, SHA-256 content hash, 25 forbidden terms |
| Constitutional B (1) | `constitutional_architecture/isr/model/isr.py:ISR` — rich System/Module/Entity/... dataclass model |
| Constitutional B (2) | `constitutional_architecture/core/models/isr.py:UniversalISR` — 17-NodeType, 13-EdgeType typed graph |
| Action (A) | **KEEP** |
| Action (B1) | **MIGRATE** (selective) — semantic validators from `constitutional_architecture/isr/semantics/*` are absorbed into `isr/core/invariants.py` (or `isr/core/semantics/`) in R1-D.1; the rich dataclass model is retired as runtime. |
| Action (B2) | **RETIRE** — `UniversalISR` is not used by the canonical execution path; it is removed (after the canonical replacement is verified). |
| Rationale | The canonical ISR is `isr/core/`. The constitutional ISR provides semantic validators that are genuinely semantic (and useful); the rich dataclass model duplicates the canonical ISR's role. |
| Migration destination | B1 → selective migration to `isr/core/` (R1-D.1); B2 → retired as runtime (R1-D.5) |
| Status | KEEP A; MIGRATE B1 selectively; RETIRE B2 |

### C03 ArchitectureCandidate

| Field | Value |
|---|---|
| Canonical contract | `ArchitectureCandidate` (D04) |
| Current A | `evolution/core/genome.py` — Genome with chromosomes+genes (de facto ArchitectureCandidate today) |
| Constitutional B | `constitutional_architecture/engine/individual.py` + `evolution_engine.py` |
| Action (A) | **KEEP + formalize** — the Genome is the de facto implementation; the contract (D04) freezes the API and a typed `ArchitectureCandidate` module is created in R1-D.3. |
| Action (B) | **MIGRATE** (selective) — semantic operators from the Substrate B evolution engine are absorbed into `evolution/core/operations.py` in R1-D.3; the Substrate B engine is retired. |
| Rationale | The canonical evolution is `evolution/core/`. The Substrate B engine has semantic properties (mutation operators, crossover semantics) that are genuinely useful; the rest is retired. |
| Migration destination | B → selective migration to `evolution/core/` (R1-D.3) |
| Status | KEEP A (formalize in R1-D.3); MIGRATE B selectively |

### C04 EvolutionOperation

| Field | Value |
|---|---|
| Canonical contract | `EvolutionOperation` (D05) |
| Current A | `evolution/core/operations.py:74-104` — real crossover verified; mutation, crossover, recombination, selection, evaluation all present |
| Constitutional B | `constitutional_architecture/engine/mutation_*.py` (6 files), `crossover_engine.py` |
| Action (A) | **KEEP** — the real crossover is the canonical crossover. |
| Action (B) | **MIGRATE** (selective) — only the genuinely-new operator kinds are absorbed into `evolution/core/operations.py`; the rest is retired. |
| Rationale | The Substrate B crossover is pseudo-crossover (copies parent A); the canonical crossover is real. Substrate B's mutation operators may have useful new kinds; if so, they are absorbed selectively. |
| Migration destination | B → selective migration to `evolution/core/operations.py` (R1-D.3) |
| Status | KEEP A; MIGRATE B selectively |

### C05 EvolutionRecord / EIR

| Field | Value |
|---|---|
| Canonical contract | `EvolutionRecord / EIR` (D06) |
| Current A | `evolution/core/lineage` (in-memory) |
| Constitutional B | `constitutional_architecture/eir/transformation.py:EIR` (defective: `evolution_loop.py:110 transformations=[]`) |
| Action (A) | **KEEP + create** — the canonical `EvolutionRecord` is created in R1-D.3 as `evolution/core/record.py` with the required fields (audit-required: transformation_id, source_isr, target_isr, operator, etc.). |
| Action (B) | **MIGRATE** (selective) — useful schema fields from B's `transformation.py:Transformation` are absorbed into the canonical `EvolutionRecord`; the B path is retired. The `transformations=[]` defect is repaired or the path is retired. |
| Rationale | The canonical evolution record is a new module (R1-D.3) that absorbs the audit-required fields. The B path has useful schema fragments but is defective. |
| Migration destination | B → selective migration to `evolution/core/record.py` (R1-D.3) |
| Status | CREATE A (R1-D.3); MIGRATE B selectively |

### C06 CompilerIR

| Field | Value |
|---|---|
| Canonical contract | `CompilerIR` (D07) |
| Current A (stabilization) | `compiler/core/plan.py:CompilationPlan` — Pydantic flat (Service, DataModel, Event, SecurityPolicy). Used by `certification/`. |
| Constitutional B | `constitutional_architecture/compiler/bir/model.py:BIR` — 9 BIRNodeType (HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST). **BIR is a semantic donor.** |
| Action (A) | **KEEP as stabilization** — CompilationPlan is the stabilization implementation; the canonical CompilerIR is a new module (R1-D.2) that supersedes it. **Content-hash is added to the canonical CompilerIR, NOT to BIR.** |
| Action (B) | **MIGRATE** (selective) — the 9 BIRNodeTypes are read as references; genuinely-semantic ones are absorbed into the canonical CompilerIR contract where appropriate. BIR is **not** modified to add content-hash. |
| Rationale | The canonical CompilerIR is a new module (R1-D.2). BIR is a semantic donor, not the implementation. The stabilization `CompilationPlan` is preserved during the migration window. |
| Migration destination | B → selective migration to the canonical CompilerIR (R1-D.2); BIR retired as runtime (R1-D.5) |
| Status | KEEP A as stabilization; CREATE canonical CompilerIR (R1-D.2); MIGRATE B selectively |

### C07 CompilerBackend

| Field | Value |
|---|---|
| Canonical contract | `CompilerBackend` (D08) |
| Current A | `compiler/core/protocol.py:CompilerBackend` (Protocol) |
| Constitutional B (1) | `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` (Gen-C) |
| Constitutional B (2) | `compiler/sdk/base.py:CompilerBackendBase` (Gen-A) |
| Constitutional B (3) | `constitutional_architecture/compilers/backend/base.py:BackendCompiler` (per-category, 9 sub-categories) |
| Action (A) | **KEEP** — the canonical protocol retains the Gen-B shape with the D08 additions. |
| Action (B1) | **RETIRE** — Gen-C ABC is not used by the canonical execution path. |
| Action (B2) | **RETIRE** — Gen-A `CompilerBackendBase` is not used by the canonical execution path. |
| Action (B3) | **RETIRE** — per-category compilers are retired (INV-B14: no category-specific compiler becomes a new architectural authority). |
| Rationale | The canonical protocol is the Gen-B Protocol. The constitutional backends are not used by the campaign runtime; they are retired. |
| Migration destination | B1, B2, B3 → retired as runtime (R1-D.5) |
| Status | KEEP A; RETIRE B1, B2, B3 |

### C08 ArtifactSet

| Field | Value |
|---|---|
| Canonical contract | `ArtifactSet` (D09) |
| Current A (stabilization) | `compiler/core/repository.py:GeneratedRepository` (used by `certification/`). Gen-B backends emit via `build_repository(files_dict)` (pure emission). |
| Constitutional B (1) | `constitutional_architecture/compiler/backends/fastapi_backend.py:72-86` — calls `self.write_files()` inside `compile()` (the Gen-C artifact-purity defect) |
| Constitutional B (2) | `CompilationOutput` (Gen-A `compiler/models.py`) |
| Action (A) | **KEEP as stabilization + create canonical** — the canonical `ArtifactSet` module is created in R1-D.5 to formalize the contract. |
| Action (B1) | **ADAPT TEMPORARILY** — the `self.write_files()` defect is corrected in R1-E.7 (return `ArtifactSet`; packager writes). If correction is not feasible, the backend is retired. |
| Action (B2) | **RETIRE** — Gen-A `CompilationOutput` is not used by the canonical execution path. |
| Rationale | The canonical ArtifactSet is a new module. The Gen-C backend has a defect that must be corrected (or the backend is retired). The Gen-A `CompilationOutput` is not in the runtime path. |
| Migration destination | B1 → corrected or retired (R1-E.7); B2 → retired as runtime (R1-D.5) |
| Status | KEEP A as stabilization; CREATE canonical ArtifactSet (R1-D.5); ADAPT B1 (R1-E.7) or RETIRE; RETIRE B2 |

### C09 VerificationResult

| Field | Value |
|---|---|
| Canonical contract | `VerificationResult` (D10) |
| Current A (stabilization) | `certification/stages/{stub_stages,docker_stages,independent_verify}.py` (fail-closed in the campaign runtime; R0 verified) |
| Constitutional B | `constitutional_architecture/compiler/passes/verification_pass.py:12-132` (fail-open) |
| Action (A) | **KEEP as stabilization + create canonical** — the canonical Verifier interface is defined in D10 and implemented in R1-E.1. |
| Action (B) | **ADAPT TEMPORARILY** — the fail-open pass is adapted to the canonical contract in R1-E.1 (fail-closed). If adaptation is not feasible, the path is retired. |
| Rationale | The canonical verification contract is fail-closed. The Substrate B verification pass is fail-open; it must be adapted to the canonical contract (or retired). INV-B10: verification cannot fail open. |
| Migration destination | B → adapted to the canonical contract (R1-E.1) or retired |
| Status | KEEP A as stabilization; CREATE canonical Verifier (R1-E.1); ADAPT B (R1-E.1) or RETIRE |

### C10 CertificationEvidence

| Field | Value |
|---|---|
| Canonical contract | `CertificationEvidence` (D11) |
| Current A | `certification/evidence/ledger.py:EvidenceLedger` (JSONL, hash-chained, SHA-256). B3-v2 ledger (443 records, chain intact) preserved unchanged. |
| Constitutional B | None observed at this layer |
| Action | **KEEP** |
| Rationale | The certification evidence ledger is canonical from inception. The B3-v2 evidence chain is preserved unchanged (INV-B13). |
| Migration destination | n/a (canonical from inception) |
| Status | KEEP — frozen at `certification/evidence/ledger.py` |

### C11 RuntimeObservation

| Field | Value |
|---|---|
| Canonical contract | `RuntimeObservation` (D12) |
| Current A | None in the canonical runtime |
| Constitutional B | `autonomous-api/app/observation/{gateway,sequences,projectors}.py` (LEGACY). `autonomous-api/app/main.py:111-115` `_DbGenerationProvider.get_isr() → NotImplementedError("ISR binding is a declared audit gap")` is the audit-flagged observation-ISR binding gap. |
| Action (A) | **CREATE in R2/R3** — the contract (D12) is defined in R1-B; the implementation is out of R1 scope. |
| Action (B) | **DEFER** — C-17 deferred to R2/R3 platform integration phase. |
| Rationale | The contract surface is defined; the implementation is out of R1 scope. The legacy `autonomous-api/` observation subsystem is C-17 deferred. |
| Migration destination | B → deferred to R2/R3 |
| Status | CREATE A (R2/R3); DEFER B (C-17) |

## 4. Cross-cutting actions

### 4.1 Compiler bridge

| Field | Value |
|---|---|
| Canonical contract | n/a (no canonical compiler bridge contract in D02–D12) |
| Current | `constitutional_architecture/engine/compiler_bridge.py:13-45` — dead code, broken API |
| Action | **RETIRE** (delete) — no callers; the bridge is removed in R1-D.5. |
| Rationale | The bridge is dead code with no callers. It uses non-existent API signatures. |

### 4.2 R1-A deferred items

| Item | Status | Deferred to |
|---|---|---|
| C-17 (`autonomous-api/` observation lineage) | DEFERRED — classified as legacy application/runtime; must not introduce an ISR source of truth | R2/R3 platform integration phase |
| C-18 (`pyproject.toml` topology) | DEFERRED — first stabilize architecture; then clean packaging | post-R1 packaging cleanup |

## 5. Migration action summary

| Action | Contracts | Migration step |
|---|---|---|
| KEEP | C01, C07-A, C10 | n/a (canonical from inception) |
| KEEP + formalize/create | C03-A, C05-A, C06-A, C08-A, C09-A | R1-D.3, R1-D.2, R1-D.5, R1-E.1 |
| MIGRATE (selective) | C02-B1, C03-B, C04-B, C05-B, C06-B | R1-D.1, R1-D.3, R1-D.2 |
| ADAPT TEMPORARILY | C08-B1, C09-B | R1-E.7, R1-E.1 |
| RETIRE | C02-B2, C07-B1, C07-B2, C07-B3, C08-B2, compiler bridge | R1-D.5 |
| DEFER | C11-A (create in R2/R3), C11-B (C-17) | R2/R3 platform integration |

## 6. Cross-references

- D01: registry (per-contract summary).
- D02–D12: per-contract specifications.
- D16: invariants.
- D17: legacy boundary specification.
- D19: migration constraints.
- D20: R1-B gate report (the gate evaluates this matrix).

---

*End of D15. The compatibility matrix is the gate between R1-B and R1-C. It identifies, for each canonical contract, what to keep, what to migrate, what to adapt, what to retire, and what to defer — with rationale.*
