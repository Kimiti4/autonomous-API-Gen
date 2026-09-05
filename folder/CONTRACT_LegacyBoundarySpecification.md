# CONTRACT_LegacyBoundarySpecification (R1-B D17)

**Contract:** `Legacy Boundary Specification`
**Status:** R1-B Deliverable D17. Authoritative specification of the temporary R1-C boundary. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Authority:** R1-B D15 (compatibility matrix) and D16 (invariants).

**Invariants this contract satisfies:** INV-B15 (legacy adapters are one-way: `LEGACY → CANONICAL`).

---

## 1. Purpose

The legacy boundary specification defines the **temporary R1-C boundary** between canonical and legacy implementations. Every surviving legacy subsystem has an explicit classification, owner, purpose, input, output, canonical destination, adapter direction, and retirement condition. This allows temporary coexistence **without creating a second source of truth**.

## 2. Boundary rules

The boundary between canonical and legacy is enforced by the following rules:

- A legacy implementation is **explicitly classified** as `LEGACY` at the module level.
- A legacy implementation has an **owner** — the migration step that retires it.
- A legacy implementation has a **canonical destination** — the canonical contract it will be replaced by.
- A legacy implementation has a **retirement condition** — the criterion for retiring it.
- A legacy implementation is reached by an adapter that is **one-way**: `LEGACY → CANONICAL`. **Never** `CANONICAL ↔ LEGACY` (INV-B15).
- A legacy implementation that does not satisfy these rules is forbidden.

## 3. Legacy components

The following components are classified as LEGACY per the D15 compatibility matrix. Each is given a temporary existence contract.

### L01. `constitutional_architecture/isr/model/isr.py:ISR`

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.1 (selective migration of semantic validators) and R1-D.5 (deprecation of the rich dataclass model) |
| Purpose | The rich System/Module/Entity/Service/... dataclass model. Provides semantic validators. |
| Input | An ISR-like object (System, Module, Entity, etc.) |
| Output | Semantic validation results; rich ISRs |
| Canonical destination | `isr/core/` (D03) — selective absorption of semantic validators; the rich dataclass model is retired as runtime |
| Adapter direction | `LEGACY → CANONICAL` — semantic validators are wrapped in adapters that expose canonical ISR invariants |
| Retirement condition | All genuinely-semantic validators are absorbed into `isr/core/invariants.py` (or `isr/core/semantics/`); the rich dataclass model has no canonical consumers |

### L02. `constitutional_architecture/core/models/isr.py:UniversalISR`

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.5 (deprecation) |
| Purpose | A 17-NodeType, 13-EdgeType typed graph. Not used by the canonical execution path. |
| Input | A UniversalISR object |
| Output | Typed graph views |
| Canonical destination | None (no canonical consumers). **Retired.** |
| Adapter direction | n/a (no adapter needed) |
| Retirement condition | No canonical consumer. Removed in R1-D.5. |

### L03. `constitutional_architecture/engine/evolution_engine.py` (and `individual.py`)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.3 (selective migration of semantic operators) and R1-D.5 (deprecation) |
| Purpose | The Substrate B evolution engine. Provides mutation, crossover, and other operators. |
| Input | An ArchitectureCandidate (Substrate B variant) |
| Output | New ArchitectureCandidate (Substrate B variant) |
| Canonical destination | `evolution/core/` (D04, D05, D06) — selective absorption of semantic operators |
| Adapter direction | `LEGACY → CANONICAL` — operators are wrapped to expose canonical EvolutionOperation semantics |
| Retirement condition | All genuinely-useful operators are absorbed into `evolution/core/operations.py`; the Substrate B engine has no canonical consumers |

### L04. `constitutional_architecture/engine/mutation_*.py` (6 files)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.3 (selective migration) and R1-D.5 (deprecation) |
| Purpose | Substrate B mutation operators. May have new operator kinds not in `evolution/core/operations.py`. |
| Input | A candidate |
| Output | A mutated candidate |
| Canonical destination | `evolution/core/operations.py` (D05) — selective absorption of new operator kinds |
| Adapter direction | `LEGACY → CANONICAL` |
| Retirement condition | All genuinely-new operator kinds are absorbed; no Substrate B consumers remain |

### L05. `constitutional_architecture/engine/crossover_engine.py`

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.5 (deprecation) |
| Purpose | Substrate B crossover. **Pseudo-crossover** (copies parent A) — not a real crossover. |
| Input | Two parent candidates |
| Output | A child candidate (in practice, a copy of parent A) |
| Canonical destination | None. The canonical crossover is the **real** crossover at `evolution/core/operations.py:74-104` (D05). |
| Adapter direction | n/a (no adapter needed; the Substrate B path is defective) |
| Retirement condition | The Substrate B crossover is **not** canonical. It is removed in R1-D.5. |

### L06. `constitutional_architecture/eir/transformation.py:EIR`

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.3 (selective migration of useful schema fields) and R1-D.5 (deprecation) |
| Purpose | The Substrate B EIR. Defective: `evolution_loop.py:110 transformations=[]`. Provides useful schema fragments. |
| Input | An evolution operation |
| Output | An EIR record (often empty) |
| Canonical destination | `evolution/core/record.py` (D06) — selective absorption of useful schema fields |
| Adapter direction | `LEGACY → CANONICAL` — schema fields are migrated to the canonical EvolutionRecord |
| Retirement condition | Useful schema fields are absorbed; the `transformations=[]` defect is repaired or the path is retired; no Substrate B consumers remain |

### L07. `constitutional_architecture/compiler/bir/model.py:BIR`

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.2 (selective absorption of BIRNodeTypes into canonical CompilerIR) and R1-D.5 (deprecation) |
| Purpose | The Substrate B Compiler IR. Provides 9 BIRNodeType concepts (HANDLER, ENTITY, SERVICE, REPOSITORY, ROUTER, CONFIG, MIDDLEWARE, EVENT_HANDLER, TEST). **BIR is a semantic donor, not a competing IR.** |
| Input | A rich ISR (D03-B1) |
| Output | A BIR instance |
| Canonical destination | The canonical CompilerIR (D07) — selective absorption of BIRNodeType concepts |
| Adapter direction | `LEGACY → CANONICAL` — BIR concepts are read as references and absorbed into the canonical contract |
| Retirement condition | All genuinely-semantic BIRNodeType concepts are absorbed; BIR is **not** modified to add content-hash (content-hash is added to the canonical CompilerIR, not to BIR); no Substrate B consumers remain |

### L08. `constitutional_architecture/compiler/backends/backend_interface.py:CompilerBackend(ABC)` (Gen-C)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.5 (deprecation) |
| Purpose | The Substrate B backend protocol (ABC). Not used by the canonical execution path. |
| Input | A BIR instance |
| Output | A backend-specific artifact |
| Canonical destination | `compiler/core/protocol.py:CompilerBackend` (D08) — the canonical protocol |
| Adapter direction | n/a (no canonical consumer) |
| Retirement condition | No canonical consumer. Removed in R1-D.5. |

### L09. `compiler/sdk/base.py:CompilerBackendBase` (Gen-A)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.5 (deprecation) |
| Purpose | The Gen-A backend base. Not used by the canonical execution path. |
| Input | A `CompilationContext` (Gen-A) |
| Output | A `CompilationOutput` (Gen-A) |
| Canonical destination | `compiler/core/protocol.py:CompilerBackend` (D08) |
| Adapter direction | n/a (no canonical consumer) |
| Retirement condition | No canonical consumer. Removed in R1-D.5. |

### L10. `constitutional_architecture/compilers/*` (per-category, 9 sub-categories)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.5 (deprecation) |
| Purpose | Per-category compilers (backend, database, deployment, documentation, frontend, infrastructure, operational, runtime_policy, testing). **INV-B14**: no category-specific compiler becomes a new architectural authority. |
| Input | A `UniversalISR` (L02) |
| Output | A `CompilationBundle` (per-category) |
| Canonical destination | `compiler/core/protocol.py:CompilerBackend` (D08) — the canonical backend protocol |
| Adapter direction | n/a (no canonical consumer) |
| Retirement condition | No canonical consumer. Removed in R1-D.5. |

### L11. `constitutional_architecture/compiler/backends/fastapi_backend.py` (Gen-C, with `self.write_files()` defect)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-E.7 (correct the artifact-purity defect or retire) |
| Purpose | The Gen-C FastAPI backend. Has a defect: `self.write_files()` is called inside `compile()` (lines 72-86), violating the canonical artifact-purity invariant (INV-B09). |
| Input | A BIR instance |
| Output | Files written directly to the filesystem (the defect) |
| Canonical destination | A canonical backend implementing `CompilerBackend` (D08) and producing an `ArtifactSet` (D09) via `build_repository`-style pure emission |
| Adapter direction | `LEGACY → CANONICAL` — the backend is refactored to return an `ArtifactSet` and the packager writes |
| Retirement condition | The defect is corrected (the backend returns an `ArtifactSet` instead of writing to the filesystem). If correction is not feasible, the backend is retired. |

### L12. `constitutional_architecture/compiler/passes/verification_pass.py` (Gen-C, fail-open)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-E.1 (adapt to the canonical Verification contract) |
| Purpose | The Substrate B verification pass. Defective: returns `success=True` on engine exception (fail-open). |
| Input | A compiler context |
| Output | A pass result |
| Canonical destination | The canonical Verifier (D10) — implemented under R1-E.1 |
| Adapter direction | `LEGACY → CANONICAL` — the pass is refactored to use the canonical Verifier and the 5-state model |
| Retirement condition | The pass is adapted to the canonical contract (fail-closed). If adaptation is not feasible, the pass is retired. |

### L13. `constitutional_architecture/engine/compiler_bridge.py` (dead code)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | R1-D.5 (deprecation) |
| Purpose | The compiler bridge. **Dead code** — no callers; uses non-existent API signatures. |
| Input | A `TypedGraph` |
| Output | A compilation result (never produced) |
| Canonical destination | None. There is no canonical compiler bridge. |
| Adapter direction | n/a |
| Retirement condition | **Immediate removal** in R1-D.5 (no canonical consumer; no useful semantics). |

### L14. `autonomous-api/app/observation/*` and `_DbGenerationProvider` (C-17 deferred)

| Field | Value |
|---|---|
| `LEGACY` | yes |
| Owner | **R2/R3 platform integration** (C-17 deferred) |
| Purpose | The Substrate B runtime observation subsystem. The `_DbGenerationProvider.get_isr() → NotImplementedError("ISR binding is a declared audit gap")` is the audit-flagged gap. |
| Input | Runtime data |
| Output | Observations (currently not bound to canonical ISR) |
| Canonical destination | The canonical RuntimeObservation (D12) — implementation deferred |
| Adapter direction | TBD in R2/R3 |
| Retirement condition | TBD in R2/R3 |

## 4. Adapters (R1-C)

R1-C may introduce temporary `LEGACY → CANONICAL` adapters for the legacy components above. Each adapter must:

- Have an explicit owner (the migration step that retires the adapter).
- Have an explicit retirement condition.
- Be one-way: `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY` (INV-B15).
- Be marked `LEGACY ADAPTER` at the module level.
- Not be silently extended or evolved; changes require an ADR.

A bidirectional adapter is forbidden.

## 5. Cross-references

- D15: compatibility matrix (the action taxonomy: KEEP, MIGRATE, ADAPT TEMPORARILY, RETIRE, DEFER).
- D16: invariants (INV-B15).
- D19: migration constraints (May / May not for R1-C/R1-D).
- D20: R1-B gate report (the gate evaluates the legacy boundary).

---

*End of D17. The legacy boundary specification enumerates every surviving legacy subsystem with its classification, owner, purpose, input, output, canonical destination, adapter direction, and retirement condition. This allows temporary coexistence without creating a second source of truth.*
