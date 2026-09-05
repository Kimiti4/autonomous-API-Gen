# R1_D3_EVOLUTION_SEMANTIC_COMPARISON (R1-D.3 D3-03)

**Status:** R1-D.3 Deliverable D3-03. Evolution semantic comparison. Index: `folder/R1_D3_EVOLUTION_INVENTORY.md` (D3-01), `folder/R1_D3_EVOLUTION_EXECUTION_GRAPH.md` (D3-02), `folder/CONTRACT_EvolutionOperation.md` (D05 R1-B), `folder/CONTRACT_EvolutionRecord_EIR.md` (D06 R1-B), `folder/CONTRACT_ArchitectureCandidate.md` (D04 R1-B).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; R1-D.2 D2-D1–D2-D10; the R1-D.3 master prompt.

**Method:** Field-by-field and concept-by-concept comparison. Each row is OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN.

---

## 1. Purpose

Compare the evolution models:
- Canonical evolution (`evolution/core/`, `evolution/`) — the canonical substrate.
- Constitutional evolution (Gen-C) (`constitutional_architecture/engine/`) — the constitutional substrate.
- Constitutional EIR (`constitutional_architecture/isr/eir/`) — the constitutional semantic donor.

Compare fields and semantics for: candidate, operation, mutation, crossover, evaluation, selection, lineage, constraints, provenance, determinism, failure, verification.

---

## 2. Architecture Candidate comparison

| Field | Canonical (`evolution/core/genome.py:Genome`) | Constitutional (`constitutional_architecture/engine/individual.py:Individual`) | R1-B D04 contract | Action | Reason |
|---|---|---|---|---|---|
| Identity | `genome_id` (string) | `individual_id` (string) | **content-derived** (R1-B D04) | **MIGRATE** | Canonical Genome has `genome_id`; D04 requires content-derived. The future canonical ArchitectureCandidate module uses content hash. |
| Architecture | references `ISRRevision.content_hash` (per `evolution/core/materialize.py`) | references `constitutional_architecture.isr.model.isr.ISR` | **semantic; references ISR identity** | **RETAIN CANONICAL** | The canonical Genome references the canonical ISR. |
| Version | (none; identity is the version) | `generation` (integer) | **semantic; evolution versioning** | **MIGRATE** | D04 requires semantic versioning; the future canonical uses content hash. |
| State | (none; Genome is immutable per operation) | (mutable; mutations modify Individual) | **semantic; immutable per operation** | **MIGRATE** | D04 requires immutability per operation. The future canonical uses `with_architecture(new_arch)`. |
| Parent | `parent_genome_id` (string; per `evolution/core/construction.py`) | `parent_id` (string) | **semantic; lineage** | **RETAIN CANONICAL** | |
| Lineage | `evolution/core/construction.py` (in-memory) | `constitutional_architecture/engine/lineage_tracker.py` (in-memory) | **semantic; reconstructable** | **MIGRATE SELECTED** | Durable lineage is R1-E.6. In-memory lineage is canonical. |
| Evaluation | `fitness_evaluation` (per `evolution/core/fitness.py`) | (fitness is external) | **semantic; evidence** | **RETAIN CANONICAL** | |
| Constraints | (in `evolution/governance.py`) | (in `constitutional_architecture/governance/`) | **semantic; constraint** | **MIGRATE SELECTED** | The governance fitness is R1-D.3 work (F-C10-02). |
| Provenance | (none; metadata only) | (none; metadata only) | **semantic; immutable** | **DEFER** | R1-E.6 (durable provenance). |

**Summary:** 3 MIGRATE (identity, version, state), 1 MIGRATE SELECTED (lineage durability), 2 RETAIN CANONICAL, 1 DEFER (provenance durability).

---

## 3. EvolutionOperation comparison

| Field | Canonical (`evolution/core/operations.py`) | Constitutional (`constitutional_architecture/engine/evolution_engine.py`) | R1-B D05 contract | Action | Reason |
|---|---|---|---|---|---|
| Operation identity | (none; operation is a function call) | (none) | **semantic; required** | **MIGRATE** | D05 requires operation identity. The future canonical uses UUIDv5 over operator type + parameters + timestamp. |
| Operation type | `mutation`, `crossover`, `recombination`, `selection`, `evaluation` | (operator type is implicit in the engine) | **semantic; required** | **RETAIN CANONICAL** | The canonical taxonomy is in `evolution/core/operations.py`. |
| Parent architecture | (passed as argument) | (passed as argument) | **semantic; required** | **RETAIN CANONICAL** | |
| Target architecture | (returned by operation) | (returned by engine) | **semantic; required** | **RETAIN CANONICAL** | |
| Operator | (function name) | (operator class) | **semantic; required** | **RETAIN CANONICAL** | |
| Parameters | (function arguments) | (operator arguments) | **semantic; required** | **RETAIN CANONICAL** | |
| Constraints | (in operator implementation) | (in `mutation_validator.py`) | **semantic; required** | **MIGRATE SELECTED** | Constitutional constraint validation is R1-D.5. |
| Preconditions | (in operator implementation) | (implicit) | **semantic; required** | **MIGRATE** | D05 requires explicit preconditions. |
| Postconditions | (in operator implementation) | (implicit) | **semantic; required** | **MIGRATE** | D05 requires explicit postconditions. |
| Randomness | (RNG per operation; e.g., crossover) | (RNG per operation) | **semantic; deterministic or stochastic** | **RETAIN CANONICAL** | The canonical evolution uses RNG with seed. |
| Seed | (RNG seed; per operation) | (RNG seed) | **semantic; reproducibility** | **RETAIN CANONICAL** | |
| Environment | (none) | (none) | **observational metadata** | **MIGRATE** | D05 requires environment metadata. |
| Actor/origin | (none) | (none) | **observational metadata** | **MIGRATE** | D05 requires actor/origin. |
| Timestamp | (system clock) | (system clock) | **observational metadata** | **RETAIN CANONICAL** | |
| Provenance | (none) | (none) | **observational metadata** | **MIGRATE** | D05 requires provenance. |
| Verification relationship | (none) | (none) | **semantic; cross-contract** | **MIGRATE** | D05 requires verification relationship. |

**Summary:** 6 MIGRATE (identity, preconditions, postconditions, environment, actor/origin, provenance, verification relationship), 1 MIGRATE SELECTED (constraints), 6 RETAIN CANONICAL.

---

## 4. Mutation comparison

| Field | Canonical (`evolution/core/operations.py:mutation`) | Constitutional (10 EIR operators in `constitutional_architecture/isr/eir/transformation.py`) | R1-B D05 | Action | Reason |
|---|---|---|---|---|---|
| `split_module` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | The EIR operator may be a useful canonical operator. |
| `introduce_cache` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `add_rate_limiting` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `convert_to_async` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `extract_interface` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `add_audit_logging` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `change_scaling_policy` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `add_event` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `merge_services` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| `add_circuit_breaker` | ✗ | ✓ (line 961+) | (canonical operator) | **MIGRATE SELECTED** | May be useful. |
| Generic mutation (no specific operator) | ✓ (`evolution/core/operations.py:mutate`) | ✗ | (canonical) | **RETAIN CANONICAL** | The canonical generic mutation is preserved. |

**Summary:** 10 MIGRATE SELECTED (EIR operators; evaluated for canonical absorption in R1-D.5). 1 RETAIN CANONICAL.

---

## 5. Crossover comparison

| Field | Canonical (`evolution/core/operations.py:74-104`) | Constitutional (`constitutional_architecture/engine/crossover_engine.py`) | R1-B D05 | Action | Reason |
|---|---|---|---|---|---|
| Real crossover | ✓ (RNG-pick per gene with 50/50) | ✗ (pseudo-crossover; copies parent A) | (canonical) | **RETAIN CANONICAL** | The canonical real crossover is the authority. |
| Pseudo-crossover | ✗ | ✓ | n/a | **REJECT** | Pseudo-crossover is a known defect; it is NOT canonical. |

**Summary:** 1 RETAIN CANONICAL. 1 REJECT. The constitutional pseudo-crossover is on the retirement path (R1-D.5).

---

## 6. Evaluation / Fitness comparison

| Field | Canonical (`evolution/core/fitness.py` + `fitness_evaluator.py`) | Constitutional (`constitutional_architecture/engine/fitness.py`) | R1-B D05 | Action | Reason |
|---|---|---|---|---|---|
| Fitness base class | ✓ (`evolution/core/fitness.py`) | ✓ (`fitness.py`) | (canonical) | **RETAIN CANONICAL** | The canonical fitness base is preserved. |
| Fitness evaluator | ✓ (`evolution/core/fitness_evaluator.py`) | ✓ (`fitness_evaluator.py` in constitutional) | (canonical) | **RETAIN CANONICAL** | |
| Governance fitness | ✓ (`evolution/governance_fitness_evaluator.py`; **F-C10-02 bypass**) | (F-C10-02 source: `constitutional_architecture/governance/`) | (canonical) | **FIX F-C10-02** | Migrate governance fitness to canonical; remove constitutional imports. |
| Fitness evaluation results | (in-memory) | (in-memory) | (canonical) | **RETAIN CANONICAL** | |
| Fitness from VerificationResult | (not consumed) | (not consumed) | (cross-contract; D14) | **DEFER** | Cross-contract fitness from verification is a future R-phase. |
| Fitness from RuntimeObservation | (not consumed) | (not consumed) | (cross-contract; D14) | **DEFER** | Cross-contract fitness from runtime is D12 (C-17 deferred). |
| Fitness from CertificationEvidence | (not consumed) | (not consumed) | (cross-contract; D14) | **DEFER** | Cross-contract fitness from certification is a future R-phase. |

**Summary:** 4 RETAIN CANONICAL. 1 FIX (F-C10-02). 3 DEFER (cross-contract fitness).

---

## 7. Selection comparison

| Field | Canonical (`evolution/core/operations.py:selection` + `selection.py`) | Constitutional (`constitutional_architecture/engine/population_manager.py` + `pareto_optimizer.py`) | R1-B D05 | Action | Reason |
|---|---|---|---|---|---|
| Selection (generic) | ✓ (`evolution/core/operations.py:selection`) | ✓ (`population_manager.py`) | (canonical) | **RETAIN CANONICAL** | |
| Pareto selection | ✓ (`evolution/pareto.py`) | ✓ (`pareto_optimizer.py`) | (canonical) | **RETAIN CANONICAL** | |
| Elite selection | (in `evolution/core/selection.py`) | ✓ (`elite_manager.py`) | (canonical) | **MIGRATE SELECTED** | The constitutional elite manager may be useful. |
| Novelty search | (in `evolution/`) | ✓ (`novelty_search.py`) | (canonical) | **RETAIN CANONICAL** | |
| Diversity management | (in `evolution/`) | ✓ (`diversity_manager.py`) | (canonical) | **MIGRATE SELECTED** | May be useful. |
| Convergence detection | (in `evolution/`) | ✓ (`convergence_detector.py`) | (canonical) | **MIGRATE SELECTED** | May be useful. |

**Summary:** 4 RETAIN CANONICAL. 3 MIGRATE SELECTED.

---

## 8. Lineage comparison

| Field | Canonical (`evolution/core/construction.py` + `history.py`) | Constitutional (`constitutional_architecture/engine/lineage_tracker.py` + `evolution_memory.py`) | R1-B D06 | Action | Reason |
|---|---|---|---|---|---|
| Parent → child | ✓ (parent_genome_id → child_genome_id) | ✓ (parent_id → child_id) | **semantic; reconstructable** | **RETAIN CANONICAL** | |
| Multi-generation | ✓ | ✓ | **semantic; reconstructable** | **RETAIN CANONICAL** | |
| Branching | ✓ | ✓ | **semantic; reconstructable** | **RETAIN CANONICAL** | |
| Crossover lineage | ✓ (two parents → one child) | ✓ (pseudo; copies parent A) | **semantic; reconstructable** | **RETAIN CANONICAL** | Canonical real crossover preserves both parents. |
| Missing parent rejection | (implicit; raise on missing) | (implicit) | **semantic; required** | **RETAIN CANONICAL** | |
| Durable lineage | ✗ (in-memory; R1-E.6) | ✗ (in-memory; R1-E.6) | **semantic; hash-chained** | **DEFER (R1-E.6)** | Durable lineage is R1-E.6 work. |

**Summary:** 5 RETAIN CANONICAL. 1 DEFER (durable lineage).

---

## 9. EvolutionRecord / EIR comparison

| Field | Canonical (R1-B D06 contract; not yet implemented as a module) | Constitutional (`constitutional_architecture/isr/eir/model.py:EIR`) | R1-B D06 | Action | Reason |
|---|---|---|---|---|---|
| Event identity | (in D06 contract; content hash) | ✗ (frozen dataclass; no hash) | **semantic; required** | **MIGRATE** | The constitutional EIR has no content hash. The future canonical EvolutionRecord module has a content hash. |
| Parent identity | (in D06 contract) | ✓ (`source_isr_hash` + parent lineage via `evolution_loop.py`) | **semantic; required** | **MIGRATE** | |
| Operation identity | (in D06 contract; UUIDv5) | ✗ | **semantic; required** | **MIGRATE** | |
| Child identity | (in D06 contract) | ✓ (`target_isr_hash`) | **semantic; required** | **MIGRATE** | |
| Transition semantics | (in D06 contract) | (implicit; ISR delta) | **semantic; required** | **MIGRATE** | |
| Evaluation relationship | (in D06 contract) | (fitness is external) | **semantic; required** | **MIGRATE** | |
| Selection relationship | (in D06 contract) | (selection is external) | **semantic; required** | **MIGRATE** | |
| Verification relationship | (in D06 contract) | (not linked) | **semantic; required** | **MIGRATE** | |
| Provenance | (in D06 contract) | (metadata only) | **semantic; required** | **MIGRATE** | |
| Immutability | (in D06 contract; frozen) | ✓ (frozen dataclass) | **semantic; required** | **RETAIN CANONICAL** | |
| Failure semantics | (in D06 contract) | (not defined) | **semantic; required** | **MIGRATE** | |
| `transformations` | (in D06 contract; required non-empty for OPERATION_OK) | **✗ (empty; defect at `evolution_loop.py:110`)** | **semantic; required** | **FIX (R1-D.3)** | The constitutional EIR has the `transformations=[]` defect. Fix: populate from actual mutations. |
| `transformation_id` | (in D06 contract; required per transformation) | ✗ | **semantic; required** | **MIGRATE** | |
| `source_isr` / `target_isr` | (in D06 contract; required) | ✓ (`source_isr_hash` / `target_isr_hash`) | **semantic; required** | **MIGRATE** | The constitutional has these as hashes; D06 requires content hashes. |
| `operator` | (in D06 contract; required) | ✗ | **semantic; required** | **MIGRATE** | |
| `parent_architecture` / `child_architecture` | (in D06 contract; required) | ✗ | **semantic; required** | **MIGRATE** | |
| `evolution_run_id` | (in D06 contract; required) | ✓ (`evolution_run_id` in provenance) | **semantic; required** | **MIGRATE** | |
| `parameters` | (in D06 contract; required) | ✗ | **semantic; required** | **MIGRATE** | |
| `seed` | (in D06 contract; required for stochastic) | ✗ | **semantic; required** | **MIGRATE** | |
| `evaluation_results` | (in D06 contract; required if part of operation) | ✗ | **semantic; required** | **MIGRATE** | |
| `status` | (in D06 contract; required) | (implicit; frozen) | **semantic; required** | **MIGRATE** | |
| `failure_information` | (in D06 contract; required when status is not OK) | ✗ | **semantic; required** | **MIGRATE** | |
| `evidence_refs` | (in D06 contract; required) | ✗ | **semantic; required** | **MIGRATE** | |

**Summary:** 14 MIGRATE, 1 RETAIN CANONICAL (immutability), 1 FIX (R1-D.3; `transformations=[]` defect).

---

## 10. Determinism comparison

| Aspect | Canonical | Constitutional | R1-D.3 action |
|---|---|---|---|
| Crossover determinism | **Deterministic with seed** (RNG-pick per gene with 50/50; reproducible with same seed) | **Pseudo-deterministic** (copies parent A) | Canonical real crossover is the authority. Constitutional pseudo-crossover is R1-D.5. |
| Mutation determinism | **Deterministic with seed** (RNG-based; reproducible with same seed) | **Deterministic with seed** (RNG-based) | Both are deterministic with seed. |
| Selection determinism | **Deterministic** (Pareto; no RNG) | **Deterministic** | Both are deterministic. |
| Evaluation determinism | **Deterministic** (fitness function; no RNG) | **Deterministic** | Both are deterministic. |
| Overall evolution determinism | **Seeded-deterministic** (same seed → same evolution) | **Seeded-deterministic** (with the pseudo-crossover caveat) | Both are seeded-deterministic. |

---

## 11. Failure semantics comparison

| Failure mode | Canonical | Constitutional | R1-D.3 action |
|---|---|---|---|
| Invalid mutation | Fail-closed (operator raises) | Fail-closed (constraint validation) | Both are fail-closed. |
| Invalid crossover | Fail-closed (crossover raises) | Pseudo-succeeds (copies parent A) | Canonical real crossover is fail-closed. Constitutional pseudo-crossover is R1-D.5. |
| Constraint violation | Fail-closed (validator raises) | Fail-closed (validator raises) | Both are fail-closed. |
| Verification failure | (not consumed by evolution) | (not consumed) | Cross-contract fitness from verification is a future R-phase. |
| Evaluation failure | Fail-closed (fitness raises) | Fail-closed (fitness raises) | Both are fail-closed. |
| Selection failure | (selection is deterministic) | (selection is deterministic) | Both are deterministic. |
| Lineage failure (missing parent) | Fail-closed (lineage raises) | Fail-closed (lineage raises) | Both are fail-closed. |
| Serialization failure | (in-memory; no serialization) | (in-memory; no serialization) | Both are in-memory. Durable is R1-E.6. |
| Provenance failure | (metadata only) | (metadata only) | Both are metadata-only. Durable is R1-E.6. |
| Duplicate candidate | (population manages; may allow) | (population manages; may allow) | Both are population-managed. |
| Non-deterministic operation | (seeded-deterministic) | (seeded-deterministic) | Both are seeded-deterministic. |
| Missing parent | Fail-closed (lineage raises) | Fail-closed (lineage raises) | Both are fail-closed. |
| Missing evidence | (in-memory; no evidence) | (in-memory; no evidence) | Both are in-memory. Durable is R1-E.6. |

---

## 12. Provenance comparison

| Aspect | Canonical | Constitutional | R1-D.3 action |
|---|---|---|---|
| Operation provenance | (in D05 contract; not yet implemented) | (in `evolution_loop.py`; partial) | MIGRATE to canonical. |
| Candidate provenance | (in `evolution/core/construction.py`; partial) | (in `lineage_tracker.py`; partial) | MIGRATE to canonical. |
| Evaluation provenance | (in `evolution/core/fitness.py`; metadata) | (in `fitness.py`; metadata) | MIGRATE to canonical. |
| Verification linkage | (not consumed) | (not consumed) | DEFER (cross-contract; D12). |
| Content-derived identity | (none; in-memory) | (none; in-memory) | MIGRATE (R1-E.6 durable lineage). |

---

## 13. Cross-references

- D3-01: `folder/R1_D3_EVOLUTION_INVENTORY.md`
- D3-02: `folder/R1_D3_EVOLUTION_EXECUTION_GRAPH.md`
- D05 (R1-B): `folder/CONTRACT_EvolutionOperation.md`
- D06 (R1-B): `folder/CONTRACT_EvolutionRecord_EIR.md`
- D04 (R1-B): `folder/CONTRACT_ArchitectureCandidate.md`
- D3-04 through D3-07: Contract refinements (next).

---

*End of D3-03. The R1-D.3 semantic comparison is complete. 14 MIGRATE for EvolutionRecord/EIR. 6 MIGRATE for EvolutionOperation. 10 MIGRATE SELECTED for EIR mutation operators. 1 FIX (transformations=[] defect). 2 FIX (F-C10-01, F-C10-02). Multiple RETAIN CANONICAL. Multiple DEFER (R1-E.6 durable lineage; cross-contract). D3-04 through D3-07 (contract refinements) follow.*
