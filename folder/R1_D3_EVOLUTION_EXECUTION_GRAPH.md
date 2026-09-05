# R1_D3_EVOLUTION_EXECUTION_GRAPH (R1-D.3 D3-02)

**Status:** R1-D.3 Deliverable D3-02. Evolution execution graph. Index: `folder/R1_D3_EVOLUTION_INVENTORY.md` (D3-01), `folder/CONTRACT_EvolutionOperation.md` (D05 R1-B), `folder/R1_D2_COMPILER_EXECUTION_GRAPH.md` (D2-D2).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; R1-D.2 D2-D1–D2-D10; the R1-D.3 master prompt.

**Method:** File:line-cited trace of the actual runtime data flow. OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN markers.

---

## 1. Purpose

Construct the actual evolution execution graph. Trace:

```text
entrypoint
→ candidate
→ operation
→ mutation/crossover
→ constraints
→ evaluation
→ selection
→ lineage
→ provenance
→ verification
```

Mark every edge as: STATIC / TESTED / RUNTIME / UNKNOWN.

---

## 2. Canonical evolution execution graph

### 2.1 The actual flow (file:line cited)

```text
isr.core.revision.ISRRevision (canonical)
  │
  │ (candidate construction)
  │ evolution/core/construction.py: build candidate from ISRRevision
  ▼
evolution.core.genome.Genome (Architecture Candidate)
  │
  │ (EvolutionOperation)
  │ evolution/core/operations.py: mutation / crossover / recombination / selection / evaluation
  ▼
New Genome (Architecture Candidate)
  │
  │ (lineage)
  │ evolution/core/construction.py: lineage tracking
  │ evolution/history.py: history
  ▼
Lineage (in-memory)
  │
  │ (selection)
  │ evolution/core/operations.py: selection
  │ evolution/core/selection.py: selection
  │ evolution/pareto.py: Pareto selection
  ▼
Selected Genome
```

### 2.2 Edge-by-edge analysis

#### Edge 1: `ISRRevision` → `Genome` (Architecture Candidate)

| Field | Value |
|---|---|
| Producer | `evolution/core/construction.py` (candidate construction) |
| Consumer | Evolution engine (`evolution/core/engine.py`) |
| Data type | `ISRRevision` (canonical) → `Genome` (Architecture Candidate) |
| Adapter | None (direct function call) |
| Serialization | `Genome` has no content hash (in-memory; durable lineage is R1-E.6) |
| Validation | `Genome` validates structure (per `evolution/core/genome.py`) |
| Failure behavior | Fail-closed at candidate construction |
| Provenance | `Genome` references `ISRRevision.content_hash` |
| Edge status | **TESTED** (via `tests/test_genome_validator.py` and Tier A) |

**Observation:** The canonical evolution consumes the canonical ISR's content-hash identity. The Genome is the de facto Architecture Candidate (per R1-B D04).

#### Edge 2: `Genome` → `EvolutionOperation` (mutation / crossover)

| Field | Value |
|---|---|
| Producer | `evolution/core/operations.py:mutate`, `crossover`, `recombination` |
| Consumer | Evolution engine loop |
| Data type | `Genome` → `Genome` (new) |
| Adapter | None |
| Serialization | None (in-memory operation) |
| Validation | Operations validate inputs; real crossover is at `operations.py:74-104` (RNG-pick per gene with 50/50) |
| Failure behavior | Operations can fail (e.g., invalid mutation); the engine handles failures |
| Provenance | Operations should record parent IDs; lineage is via `evolution/core/construction.py` |
| Edge status | **TESTED** (via `tests/test_evolution_*.py` and `tests/test_recombination_*.py`) |

**Observation:** The real crossover at `evolution/core/operations.py:74-104` is canonical. The constitutional `crossover_engine.py` is pseudo-crossover (copies parent A) — a known defect on the retirement path (R1-D.5).

#### Edge 3: `Genome` → `Genome` (selection)

| Field | Value |
|---|---|
| Producer | `evolution/core/operations.py:selection` (from population of Genomes) |
| Consumer | Evolution engine loop |
| Data type | `list[Genome]` → `Genome` (selected) |
| Adapter | None |
| Serialization | None (in-memory) |
| Validation | Selection criteria; Pareto optimization via `evolution/pareto.py` |
| Failure behavior | Selection can fail; the engine handles failures |
| Provenance | Selection records which candidates were selected |
| Edge status | **TESTED** |

#### Edge 4: `Genome` → `EvolutionRecord` (lineage)

| Field | Value |
|---|---|
| Producer | `evolution/core/construction.py` (lineage tracking) |
| Consumer | `evolution/history.py` (history) |
| Data type | `Genome` → lineage record (in-memory; durable is R1-E.6) |
| Adapter | None |
| Serialization | None (in-memory) |
| Validation | Lineage validates parent-child relationships |
| Failure behavior | Missing parent → lineage failure |
| Provenance | Lineage carries parent IDs, child IDs, operation IDs |
| Edge status | **TESTED** (via `tests/test_evolution_*.py`; durable is R1-E.6) |

**Observation:** The canonical lineage is in-memory. Durable lineage (hash-chained, persisted to `release/evidence/`) is R1-E.6 work. The canonical EvolutionRecord contract (R1-B D06) requires the audit fields (`transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`); these are documented in R1-B D06 but not yet enforced in the canonical lineage.

---

## 3. Constitutional evolution execution graph (Gen-C)

### 3.1 The actual flow (file:line cited)

```text
constitutional_architecture.isr.model.isr.ISR (rich)
  │
  │ (individual construction)
  │ constitutional_architecture/engine/individual.py
  ▼
Individual (genome)
  │
  │ (EvolutionEngine)
  │ constitutional_architecture/engine/evolution_engine.py
  │ EvolutionLoop.evolve()
  ▼
EvolutionLoop iteration:
  1. mutation_engine.mutate() (or crossover_engine.crossover())
  2. individual.apply_mutation()
  3. validate constraints
  4. evaluate fitness
  5. select
  6. record in lineage_tracker
  │
  │ (EIR construction)
  │ constitutional_architecture/engine/evolution_loop.py:107-114
  │ eir_from_transformations(...)
  ▼
EIR (constitutional_architecture.isr.eir.model.EIR)
  ⚠ transformations=[] defect at line 110 (per R0)
  │
  │ (evolution_memory)
  │ constitutional_architecture/engine/evolution_memory.py
  ▼
Evolution memory (in-memory)
```

### 3.2 Edge-by-edge analysis

#### Edge 1: `ISR` (rich) → `Individual` (genome)

| Field | Value |
|---|---|
| Producer | `constitutional_architecture/engine/individual.py` |
| Consumer | `EvolutionEngine` |
| Data type | `constitutional_architecture.isr.model.isr.ISR` → `Individual` |
| Adapter | None |
| Serialization | None (in-memory) |
| Validation | Individual validates structure |
| Failure behavior | Fail-closed at individual construction |
| Provenance | Individual references the rich ISR identity |
| Edge status | **STATIC** (constitutional; not in canonical runtime) |

#### Edge 2: `Individual` → `EIR` (via EvolutionLoop)

| Field | Value |
|---|---|
| Producer | `constitutional_architecture/engine/evolution_loop.py:107-114` |
| Consumer | Constitutional evolution engine |
| Data type | `Individual` → `EIR` (constitutional) |
| Adapter | None |
| Serialization | `EIR` is a frozen dataclass with no content hash |
| Validation | None (no invariants) |
| Failure behavior | **DEFECT**: `transformations=[]` despite mutations being performed. The constitutional EIR does NOT capture the actual mutations. This violates the R1-B D06 contract. |
| Provenance | `EIR` has `source_isr_hash` and `target_isr_hash` (from R1-B D06) but the `transformations` list is empty. |
| Edge status | **STATIC** with **P0 DEFECT** |

**Observation:** The `transformations=[]` defect is a **P0 architectural correctness issue** (per R1-B D06 INV-B04 and the R1-D.3 prompt §22 "What success looks like"). The R1-D.3 fix is to populate `transformations` from the actual mutations performed by the engine. This is a **bounded, minimal** fix: populate the list, do not rewrite the engine.

#### Edge 3: `Individual` → mutation / crossover operators

| Field | Value |
|---|---|
| Producer | `constitutional_architecture/engine/mutation_engine.py`, `mutation_operators.py`, `crossover_engine.py` |
| Consumer | `EvolutionLoop` |
| Data type | `Individual` → `Individual` (new) |
| Adapter | None |
| Serialization | None (in-memory) |
| Validation | Constraint validation (per `mutation_validator.py`) |
| Failure behavior | Fail-closed at constraint violation |
| Provenance | Mutation operators record the change; but the EIR does NOT capture it (defect) |
| Edge status | **STATIC** (constitutional) |

#### Edge 4: `Individual` → lineage_tracker

| Field | Value |
|---|---|
| Producer | `constitutional_architecture/engine/lineage_tracker.py` |
| Consumer | Constitutional evolution engine |
| Data type | `Individual` → lineage record (in-memory) |
| Adapter | None |
| Serialization | None (in-memory) |
| Validation | Lineage validates parent-child relationships |
| Failure behavior | Missing parent → lineage failure |
| Provenance | Lineage carries parent IDs, child IDs |
| Edge status | **STATIC** (constitutional; in-memory only) |

---

## 4. R1-C findings (F-C10-01, F-C10-02)

### 4.1 F-C10-01: `evolution/mutation.py:15`

| Field | Value |
|---|---|
| Source | `evolution/mutation.py:15` |
| Import | `from constitutional_architecture.governance.governance_design_fitness import (baseline_governance_design,)` |
| Direction | CANONICAL → CONSTITUTIONAL (reverse of the R1-C adapter direction) |
| Status | **LEGACY BYPASS** |
| Severity | **P1** |
| R1-D.3 action | **FIX**: migrate `baseline_governance_design` to the canonical evolution (or remove the dependency if the function is not core). |

### 4.2 F-C10-02: `evolution/governance_fitness_evaluator.py`

| Field | Value |
|---|---|
| Source | `evolution/governance_fitness_evaluator.py:7,28,35,39,42` |
| Imports | `from constitutional_architecture.governance.governance_design_fitness import (GovernanceDesignFitness, design_objectives)`, `from constitutional_architecture.governance.governance_fitness import (ALL_OBJECTIVES)`, `from constitutional_architecture.governance.schemas import GovernanceDesignISR` |
| Direction | CANONICAL → CONSTITUTIONAL |
| Status | **LEGACY BYPASS** |
| Severity | **P1** |
| R1-D.3 action | **FIX**: migrate the governance fitness evaluation to the canonical evolution. The semantic content (6 governance dimensions, design fitness, etc.) is absorbed into the canonical governance fitness module. |

---

## 5. Edge status summary

| Edge | Status | Notes |
|---|---|---|
| Canonical ISRRevision → Genome | **TESTED** | Tier A tests |
| Canonical Genome → EvolutionOperation (mutation) | **TESTED** | Tier A + v12 + v14 |
| Canonical Genome → EvolutionOperation (crossover) | **TESTED** | Real crossover at `operations.py:74-104` |
| Canonical Genome → selection | **TESTED** | Tier A + v12 |
| Canonical Genome → lineage (in-memory) | **TESTED** | Durable lineage is R1-E.6 |
| Constitutional ISR (rich) → Individual | **STATIC** | Constitutional; not in canonical runtime |
| Constitutional Individual → EIR | **STATIC with P0 DEFECT** | `transformations=[]` defect at `evolution_loop.py:107-114` |
| Constitutional Individual → mutation/crossover | **STATIC** | Constitutional |
| Constitutional Individual → lineage (in-memory) | **STATIC** | Constitutional |
| F-C10-01: canonical mutation → constitutional governance | **BYPASS** | R1-D.3 fix |
| F-C10-02: canonical governance_fitness → constitutional governance | **BYPASS** | R1-D.3 fix |

---

## 6. Architecture Candidate relationship

The R1-D.3 prompt §10 requires explicit determination of:

| Concept | Role | Canonical | Constitutional |
|---|---|---|---|
| `ArchitectureCandidate` | State / object being evolved | `evolution/core/genome.py:Genome` | `constitutional_architecture/engine/individual.py:Individual` |
| `EvolutionOperation` | Transformation applied | `evolution/core/operations.py` | `constitutional_architecture/engine/evolution_engine.py:EvolutionEngine` |
| `EvolutionRecord` | Immutable historical account | `evolution/core/construction.py` (lineage) + `evolution/history.py` | `constitutional_architecture/isr/eir/model.py:EIR` (defective: `transformations=[]`) |
| `Evaluation` | Evidence about quality | `evolution/core/fitness.py` + `evolution/core/fitness_evaluator.py` | `constitutional_architecture/engine/fitness.py` |
| `Selection` | Decision over candidates | `evolution/core/operations.py:selection` + `evolution/core/selection.py` | `constitutional_architecture/engine/population_manager.py` |

**Observation:** The canonical and constitutional substrates maintain the same conceptual separation. The constitutional EIR collapses `EvolutionOperation` and `EvolutionRecord` (the `transformations=[]` defect). The R1-D.3 fix restores the separation.

---

## 7. Cross-references

- D3-01: `folder/R1_D3_EVOLUTION_INVENTORY.md`
- D2-D2: `folder/R1_D2_COMPILER_EXECUTION_GRAPH.md` (D2-D2 execution graph)
- D05 (R1-B): `folder/CONTRACT_EvolutionOperation.md`
- D06 (R1-B): `folder/CONTRACT_EvolutionRecord_EIR.md`
- D04 (R1-B): `folder/CONTRACT_ArchitectureCandidate.md`
- D3-03: `folder/R1_D3_EVOLUTION_SEMANTIC_COMPARISON.md` (next)

---

*End of D3-02. The R1-D.3 execution graph is complete. 1 P0 defect (constitutional EIR `transformations=[]`) and 2 P1 bypasses (F-C10-01, F-C10-02) identified. D3-03 (semantic comparison) follows.*
