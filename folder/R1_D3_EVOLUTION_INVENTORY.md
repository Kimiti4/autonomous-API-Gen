# R1_D3_EVOLUTION_INVENTORY (R1-D.3 D3-01)

**Status:** R1-D.3 Deliverable D3-01. Evolution substrate inventory. Index: `folder/CONTRACT_EvolutionOperation.md` (D05 R1-B), `folder/CONTRACT_EvolutionRecord_EIR.md` (D06 R1-B), `folder/CONTRACT_ArchitectureCandidate.md` (D04 R1-B), `folder/R1_D2_GATE_REPORT.md` (D2-D10).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; R1-D.2 D2-D1–D2-D10; the R1-D.3 master prompt (`folder/r1d3.md`).

**Baseline:** HEAD = `4ae1b10` (R1-D.2 PASS). Working tree clean for tracked files.

**Method:** File:line-cited enumeration of every evolution implementation. OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN markers.

**Scope:** R1-D.3 ONLY. Portfolio generation, full-stack evolution, and autonomous self-engineering are HARD-STOPPED.

---

## 0. Inventory scope

The R1-D.3 master prompt requires inventorying:
- Root evolution (`evolution/`)
- Constitutional evolution (`constitutional_architecture/engine/`, `constitutional_architecture/isr/eir/`)
- All evolution-related tests
- All consumers

The inventory covers:
1. Canonical evolution substrate (Section 1).
2. Constitutional evolution (Gen-C) (Section 2).
3. Constitutional EIR (Section 3).
4. Distributed evolution (Section 4).
5. Civilization evolution (Section 5).
6. Evolution consumers (Section 6).
7. Tests (Section 7).
8. Cross-cutting symbols (Section 8).
9. Ownership summary (Section 9).

---

## 1. Canonical evolution substrate (`evolution/`)

### 1.1 Top-level files

| File | Purpose |
|---|---|
| `evolution/__init__.py` | Package init |
| `evolution/api.py` | Public API |
| `evolution/engine.py` | Self-evolution engine (canonical) |
| `evolution/genome.py` | Genome (canonical Architecture Candidate) |
| `evolution/genome_mutations.py` | Genome mutations |
| `evolution/mutation.py` | Mutation operations |
| `evolution/recombination.py` | Crossover / recombination (real crossover; RNG-pick per gene) |
| `evolution/selection.py` | Selection |
| `evolution/fitness.py` | Fitness base class |
| `evolution/refinement.py` | Refinement |
| `evolution/materialize.py` | Materialization |
| `evolution/construction.py` | Construction |
| `evolution/feedback.py` | Feedback |
| `evolution/feedback_engine.py` | Feedback engine |
| `evolution/feedback_api.py` | Feedback API |
| `evolution/compiler_loop.py` | Compiler loop |
| `evolution/compiler_fitness.py` | Compiler fitness |
| `evolution/governance.py` | Governance |
| `evolution/governance_api.py` | Governance API |
| `evolution/governance_fitness_evaluator.py` | **Governance fitness evaluator (F-C10-02 bypass)** |
| `evolution/governance_safety.py` | Governance safety |
| `evolution/population.py` | Population management |
| `evolution/elitism.py` | (if present) Elitism |
| `evolution/pareto.py` | Pareto optimization |
| `evolution/history.py` | Evolution history |
| `evolution/memory.py` | Evolution memory |
| `evolution/models.py` | Evolution models |
| `evolution/observability.py` | Observability |
| `evolution/observability_api.py` | Observability API |
| `evolution/orchestration.py` | Orchestration |
| `evolution/orchestration_api.py` | Orchestration API |
| `evolution/multi.py` | Multi-candidate evolution |
| `evolution/multi_api.py` | Multi-candidate API |
| `evolution/multi_generation.py` | Multi-generation evolution |
| `evolution/multi_generation_api.py` | Multi-generation API |
| `evolution/simulation.py` | Simulation |
| `evolution/promotion.py` | Promotion |
| `evolution/promotion_audit.py` | Promotion audit |
| `evolution/analytics.py` | Analytics |
| `evolution/verification.py` | Verification |
| `evolution/errors.py` | Errors |
| `evolution/utils.py` | Utilities |

### 1.2 Canonical evolution core (`evolution/core/`)

| File | Purpose |
|---|---|
| `evolution/core/__init__.py` | Package init |
| `evolution/core/engine.py` | Evolution engine core |
| `evolution/core/genome.py` | Genome (Architecture Candidate) |
| `evolution/core/operations.py` | Evolution operations (mutation, crossover, recombination, selection, evaluation) — **D05 EvolutionOperation** |
| `evolution/core/fitness.py` | Fitness base |
| `evolution/core/fitness_evaluator.py` | Fitness evaluator |
| `evolution/core/construction.py` | Construction |
| `evolution/core/materialize.py` | Materialization |
| `evolution/core/refinement.py` | Refinement |
| `evolution/core/selection.py` | Selection |

**Observation:** The canonical evolution core has 9 files. The `operations.py` (D05) is the canonical EvolutionOperation. The `genome.py` is the canonical Architecture Candidate (D04). The `construction.py`, `materialize.py`, `refinement.py`, `selection.py`, `fitness.py`, `fitness_evaluator.py` are supporting infrastructure.

### 1.3 Known canonical bypasses (from R1-C C10)

| Bypass | File:Line | Status |
|---|---|---|
| F-C10-01 (P1) | `evolution/mutation.py:15` imports from `constitutional_architecture/governance/governance_design_fitness` | R1-D.3 remediation |
| F-C10-02 (P1) | `evolution/governance_fitness_evaluator.py:7,28,35,39,42` imports from `constitutional_architecture/governance/*` | R1-D.3 remediation |

These are explicit R1-D.3 work (per R1-C C12 and the R1-D.3 prompt).

---

## 2. Constitutional evolution (Gen-C) (`constitutional_architecture/engine/`)

### 2.1 Files

| File | Size | Purpose |
|---|---|---|
| `constitutional_architecture/engine/__init__.py` | (small) | Package init |
| `constitutional_architecture/engine/adaptive_mutation.py` | (medium) | Adaptive mutation |
| `constitutional_architecture/engine/compiler_bridge.py` | (medium) | **Dead code** (R1-C C02; R1-D.5) |
| `constitutional_architecture/engine/config.py` | (medium) | Configuration |
| `constitutional_architecture/engine/convergence_detector.py` | (medium) | Convergence detection |
| `constitutional_architecture/engine/crossover_engine.py` | (medium) | **Pseudo-crossover** (R1-D.5) |
| `constitutional_architecture/engine/diversity_manager.py` | (medium) | Diversity management |
| `constitutional_architecture/engine/elite_manager.py` | (medium) | Elite management |
| `constitutional_architecture/engine/evolution_engine.py` | (large) | **Substrate B evolution engine** |
| `constitutional_architecture/engine/evolution_events.py` | (medium) | Evolution events |
| `constitutional_architecture/engine/evolution_loop.py` | (medium) | **Evolution loop; `transformations=[]` defect at line 107-114** |
| `constitutional_architecture/engine/evolution_memory.py` | (medium) | Evolution memory |
| `constitutional_architecture/engine/evolution_metrics.py` | (medium) | Evolution metrics |
| `constitutional_architecture/engine/evolution_scheduler.py` | (medium) | Evolution scheduler |
| `constitutional_architecture/engine/fitness.py` | (medium) | Fitness |
| `constitutional_architecture/engine/individual.py` | (medium) | Individual (genome) |
| `constitutional_architecture/engine/isr_adapter.py` | (medium) | **Lossy TypedGraph adapter** (R1-D.5) |
| `constitutional_architecture/engine/lineage_tracker.py` | (medium) | Lineage tracker (in-memory) |
| `constitutional_architecture/engine/mutation_engine.py` | (medium) | Mutation engine |
| `constitutional_architecture/engine/mutation_operators.py` | (medium) | Mutation operators (6 files in `constitutional_architecture/isr/semantics/`; 10 in `constitutional_architecture/eir/transformation.py`) |
| `constitutional_architecture/engine/mutation_planner.py` | (medium) | Mutation planner |
| `constitutional_architecture/engine/mutation_registry.py` | (medium) | Mutation registry |
| `constitutional_architecture/engine/mutation_validator.py` | (medium) | Mutation validator |
| `constitutional_architecture/engine/novelty_search.py` | (medium) | Novelty search |
| `constitutional_architecture/engine/pareto_optimizer.py` | (medium) | Pareto optimizer |
| `constitutional_architecture/engine/plugins.py` | (medium) | Plugins |
| `constitutional_architecture/engine/population_manager.py` | (medium) | Population manager |
| `constitutional_architecture/engine/verification_bridge.py` | (medium) | Verification bridge |

**Total: 27 files in `constitutional_architecture/engine/`.**

### 2.2 Key constitutional evolution defects (from R0)

| Defect | File:Line | Severity |
|---|---|---|
| `transformations=[]` defect | `constitutional_architecture/engine/evolution_loop.py:107-114` | **P0** (per R1-B D06 INV-B04) |
| Pseudo-crossover | `constitutional_architecture/engine/crossover_engine.py` | **P0** (per R0; copies parent A) |
| Lossy TypedGraph adapter | `constitutional_architecture/engine/isr_adapter.py` | **P0** (per R1-D.1 D3 G03) |
| compiler_bridge dead code | `constitutional_architecture/engine/compiler_bridge.py` | **P3** (no callers) |
| In-memory lineage | `constitutional_architecture/engine/lineage_tracker.py` | **P1** (durable lineage is R1-E.6) |

### 2.3 Constitutional EIR (`constitutional_architecture/isr/eir/`)

| File | Purpose |
|---|---|
| `constitutional_architecture/isr/eir/__init__.py` | Package init |
| `constitutional_architecture/isr/eir/model.py` | EIR data model (TransformationClass, Transformation, EIR) |
| `constitutional_architecture/isr/eir/taxonomy.py` | EIR taxonomy (5 transformation classes: STRUCTURAL, STRATEGIC, ADDITIVE, PARAMETRIC, TOPOLOGICAL) |
| `constitutional_architecture/isr/eir/transformation.py` | 10 mutation operators (split_module, introduce_cache, add_rate_limiting, convert_to_async, extract_interface, add_audit_logging, change_scaling_policy, add_event, merge_services, add_circuit_breaker) |

**Observation:** The constitutional EIR is a rich semantic donor. Its 10 mutation operators may be selectively absorbed into the canonical EvolutionOperation. The EIR model lacks the audit-required fields (`transformation_id`, `source_isr`, `target_isr`, `operator`, `parent_architecture`, `child_architecture`, `evolution_run_id`); these are added in the canonical EvolutionRecord (R1-B D06).

---

## 3. Distributed evolution (`distributed_evolution/`)

The R1-D.3 prompt §20 requires investigating `distributed_evolution/`. Per R0 reconnaissance, this is **infrastructure** (execution strategy), not canonical evolution semantics. The canonical Evolution Engine remains in `evolution/`; `distributed_evolution/` is an **execution strategy** backend.

**Classification:** INFRASTRUCTURE (per R1-D.3 §20). Not a competing evolution authority.

---

## 4. Civilization evolution (`civilization/`)

The R1-D.3 prompt §19 lists `civilization/` as a potential donor. Per R0, `civilization/` is a high-level platform layer (resilience, reputation, federation, certification, policy, security hardening, memory consolidation). It is **not** a canonical evolution engine. It is a **higher-level platform capability**.

**Classification:** DEFER (out of R1 scope; R2/R3). Not a competing evolution authority.

---

## 5. Evolution consumers

### 5.1 Direct importers of `evolution/core/*` (canonical)

| Path | Imports | Purpose |
|---|---|---|
| `genesis/mapper.py:8` | `evolution.core.*` | Genesis mapper |
| `genesis/validator.py:7-9` | `evolution.core.*` | Genesis validator |
| `certification/campaign/plan_builder.py:21-25` (uses `reqgraph.core`) | (indirect; not evolution) | (n/a) |
| `tests/cbc1/*` | (indirect) | Tier A tests |

**Total: 2 direct canonical evolution consumers (genesis).**

### 5.2 Direct importers of `evolution/*` (top-level canonical)

| Path | Imports | Purpose |
|---|---|---|
| `tests/cbc1/test_cbc1_gates.py:43-45` | `evolution.core.*` | CBC1 gates |
| `tests/cbc1/test_campaign_a.py:23-25` | `evolution.core.*` | Campaign A |
| `tests/v12/test_evolution_gates.py:7-9` | `evolution.core.*` | Evolution gates |
| `tests/v14/test_multi_backend.py` (indirect) | (n/a) | Multi-backend |
| `tests/test_evolution_*.py` (multiple) | `evolution.*` | Evolution tests |
| `tests/test_multi_candidate_evolution.py` | `evolution.multi` | Multi-candidate |
| `tests/test_recombination_*.py` | `evolution.recombination` | Recombination tests |
| `tests/test_macro_evolution.py` | `evolution.*` | Macro evolution |
| `tests/test_genome_validator.py` | `evolution.core.genome` | Genome validator |
| `tests/test_phase17_*.py`, `tests/test_phase18_*.py`, `tests/test_phase31_*.py` | `evolution.*` | Phase tests |

**Total: ~15+ canonical evolution test consumers (all in `tests/`).**

### 5.3 Direct importers of `constitutional_architecture/engine/*` (constitutional)

| Path | Imports | Purpose |
|---|---|---|
| `constitutional_architecture/tests/test_end_to_end.py` | `constitutional_architecture.engine.*` | Constitutional tests |
| `constitutional_architecture/tests/test_*evolution*.py` (multiple) | `constitutional_architecture.engine.*` | Constitutional evolution tests |
| `constitutional_architecture/tests/test_*crossover*.py` | `constitutional_architecture.engine.crossover_engine` | Constitutional crossover tests |

**Total: ~10+ constitutional evolution test consumers.**

### 5.4 F-C10-01 / F-C10-02 bypass consumers

| Consumer | Imports from constitutional | Severity |
|---|---|---|
| `evolution/mutation.py:15` | `constitutional_architecture.governance.governance_design_fitness` | P1 (F-C10-01) |
| `evolution/governance_fitness_evaluator.py:7,28,35,39,42` | `constitutional_architecture.governance.*` | P1 (F-C10-02) |

These are the two explicit R1-D.3 inputs from R1-C C10. The fix is to migrate the governance fitness logic from `constitutional_architecture/governance/*` into the canonical evolution (`evolution/core/`).

---

## 6. Tests

### 6.1 Canonical evolution tests

| Test file | Purpose |
|---|---|
| `tests/cbc1/test_cbc1_gates.py` | CBC1 gates (uses `evolution.core.*`) |
| `tests/cbc1/test_campaign_a.py` | Campaign A |
| `tests/v12/test_evolution_gates.py` | Evolution gates |
| `tests/test_evolution_*.py` (multiple) | Evolution tests |
| `tests/test_multi_candidate_evolution.py` | Multi-candidate |
| `tests/test_recombination_*.py` | Recombination |
| `tests/test_macro_evolution.py` | Macro evolution |
| `tests/test_genome_validator.py` | Genome validator |
| `tests/test_phase17_*.py`, `tests/test_phase18_*.py`, `tests/test_phase31_*.py` | Phase tests |

### 6.2 Constitutional evolution tests

| Test file | Purpose |
|---|---|
| `constitutional_architecture/tests/test_end_to_end.py` | End-to-end |
| `constitutional_architecture/tests/test_*evolution*.py` | Constitutional evolution |
| `constitutional_architecture/tests/test_*crossover*.py` | Constitutional crossover |
| `constitutional_architecture/tests/test_*genome*.py` | Constitutional genome |
| `constitutional_architecture/tests/test_*fitness*.py` | Constitutional fitness |
| `constitutional_architecture/tests/test_*selection*.py` | Constitutional selection |

**Note:** The constitutional tests are NOT in the canonical Tier A. They run only in `constitutional_architecture/tests/`, not in `tests/cbc1/`.

---

## 7. Cross-cutting symbols

### 7.1 `EvolutionOperation` (canonical; D05 R1-B)

| File | Type | Status |
|---|---|---|
| `evolution/core/operations.py` | Module (functions: mutation, crossover, recombination, selection, evaluation) | **CANONICAL** |
| `evolution/mutation.py`, `recombination.py`, `selection.py` | Top-level wrappers | **CANONICAL** |
| `constitutional_architecture/engine/mutation_operators.py` | Constitutional mutation operators | **LEGACY → R1-D.5** |
| `constitutional_architecture/engine/crossover_engine.py` | Pseudo-crossover | **LEGACY → R1-D.5** |

### 7.2 `EvolutionRecord / EIR` (canonical; D06 R1-B)

| File | Type | Status |
|---|---|---|
| `evolution/core/construction.py` (lineage) | Canonical lineage (in-memory) | **CANONICAL** (durable lineage is R1-E.6) |
| `evolution/history.py` | History | **CANONICAL** |
| `evolution/memory.py` | Evolution memory (in-memory) | **CANONICAL** (durable is R1-E.6) |
| `constitutional_architecture/isr/eir/model.py:EIR` | Constitutional EIR (defective: `transformations=[]`) | **LEGACY → R1-D.5** |
| `constitutional_architecture/isr/eir/transformation.py:Transformation` | Constitutional transformation (10 operators) | **SEMANTIC DONOR** (R1-D.3 selective absorption) |
| `constitutional_architecture/engine/lineage_tracker.py` | Constitutional lineage (in-memory) | **LEGACY → R1-D.5** |
| `constitutional_architecture/engine/evolution_memory.py` | Constitutional memory | **LEGACY → R1-D.5** |

### 7.3 `ArchitectureCandidate` (canonical; D04 R1-B)

| File | Type | Status |
|---|---|---|
| `evolution/core/genome.py:Genome` | Canonical genome (Architecture Candidate) | **CANONICAL** |
| `evolution/models.py:CandidateArchitecture` | Canonical model | **CANONICAL** |
| `evolution/core/materialize.py` | Materialization | **CANONICAL** |
| `constitutional_architecture/engine/individual.py` | Constitutional individual | **LEGACY → R1-D.5** |
| `constitutional_architecture/isr/model/system.py:System` | Constitutional System (rich) | **LEGACY → R1-D.5** (rich model; R1-D.1 rejected) |

### 7.4 `Mutation`

| File | Type | Status |
|---|---|---|
| `evolution/core/operations.py` (mutation function) | Canonical mutation | **CANONICAL** |
| `evolution/mutation.py` | Top-level wrapper | **CANONICAL** |
| `evolution/genome_mutations.py` | Genome mutations | **CANONICAL** |
| `constitutional_architecture/engine/mutation_engine.py` | Constitutional mutation engine | **LEGACY → R1-D.5** |
| `constitutional_architecture/engine/mutation_operators.py` | Constitutional mutation operators | **MIGRATE SELECTED** (R1-D.3 / R1-D.5) |
| `constitutional_architecture/isr/eir/transformation.py` | 10 EIR mutation operators | **SEMANTIC DONOR** (R1-D.3 selective absorption) |

### 7.5 `Crossover`

| File | Type | Status |
|---|---|---|
| `evolution/core/operations.py:74-104` (real crossover) | **Real crossover** (RNG-pick per gene with 50/50) | **CANONICAL** |
| `constitutional_architecture/engine/crossover_engine.py` | **Pseudo-crossover** (copies parent A) | **LEGACY → R1-D.5** |

### 7.6 `Selection`

| File | Type | Status |
|---|---|---|
| `evolution/core/operations.py` (selection function) | Canonical selection | **CANONICAL** |
| `evolution/core/selection.py` | Selection | **CANONICAL** |
| `evolution/pareto.py` | Pareto selection | **CANONICAL** |
| `constitutional_architecture/engine/pareto_optimizer.py` | Constitutional Pareto | **LEGACY → R1-D.5** |

### 7.7 `Evaluation / Fitness`

| File | Type | Status |
|---|---|---|
| `evolution/core/fitness.py` | Canonical fitness base | **CANONICAL** |
| `evolution/core/fitness_evaluator.py` | Canonical fitness evaluator | **CANONICAL** |
| `evolution/fitness.py` | Top-level wrapper | **CANONICAL** |
| `evolution/feedback.py` | Feedback | **CANONICAL** |
| `evolution/governance_fitness_evaluator.py` | **Governance fitness (F-C10-02 bypass)** | **R1-D.3 remediation** |
| `constitutional_architecture/governance/governance_design_fitness.py` | Constitutional governance design fitness | **SEMANTIC DONOR** (R1-D.3 selective absorption) |
| `constitutional_architecture/governance/governance_fitness.py` | Constitutional governance fitness | **SEMANTIC DONOR** (R1-D.3 selective absorption) |
| `constitutional_architecture/engine/fitness.py` | Constitutional fitness | **LEGACY → R1-D.5** |

### 7.8 `Lineage`

| File | Type | Status |
|---|---|---|
| `evolution/core/construction.py` | Canonical lineage (in-memory) | **CANONICAL** (durable is R1-E.6) |
| `evolution/history.py` | History | **CANONICAL** |
| `constitutional_architecture/engine/lineage_tracker.py` | Constitutional lineage (in-memory) | **LEGACY → R1-D.5** |

---

## 8. Ownership summary

| Module | Owner | Status | R1-D.3 classification |
|---|---|---|---|
| `evolution/core/operations.py` | Canonical | KEEP | (canonical; D05) |
| `evolution/core/genome.py` | Canonical | KEEP | (canonical; D04) |
| `evolution/core/fitness.py` | Canonical | KEEP | (canonical) |
| `evolution/core/fitness_evaluator.py` | Canonical | KEEP | (canonical) |
| `evolution/core/selection.py` | Canonical | KEEP | (canonical) |
| `evolution/core/materialize.py` | Canonical | KEEP | (canonical) |
| `evolution/core/construction.py` | Canonical | KEEP | (canonical; in-memory lineage) |
| `evolution/core/refinement.py` | Canonical | KEEP | (canonical) |
| `evolution/engine.py` | Canonical | KEEP | (canonical) |
| `evolution/genome.py` | Canonical | KEEP | (canonical) |
| `evolution/mutation.py` | Canonical | **FIX F-C10-01** | R1-D.3 (remove constitutional import) |
| `evolution/recombination.py` | Canonical | KEEP | (real crossover; preserve) |
| `evolution/selection.py` | Canonical | KEEP | (canonical) |
| `evolution/fitness.py` | Canonical | KEEP | (canonical) |
| `evolution/feedback.py`, `feedback_engine.py`, `feedback_api.py` | Canonical | KEEP | (canonical) |
| `evolution/governance.py`, `governance_api.py`, `governance_safety.py` | Canonical | KEEP | (canonical) |
| `evolution/governance_fitness_evaluator.py` | Canonical | **FIX F-C10-02** | R1-D.3 (remove constitutional imports) |
| `evolution/population.py`, `pareto.py`, `multi*.py` | Canonical | KEEP | (canonical) |
| `evolution/history.py`, `memory.py` | Canonical | KEEP | (canonical; in-memory; durable is R1-E.6) |
| `evolution/models.py` | Canonical | KEEP | (canonical) |
| `evolution/observability*.py` | Canonical | KEEP | (canonical) |
| `evolution/orchestration*.py` | Canonical | KEEP | (canonical) |
| `evolution/compiler_loop.py`, `compiler_fitness.py` | Canonical | KEEP | (canonical) |
| `evolution/analytics.py`, `verification.py`, `promotion*.py`, `simulation.py` | Canonical | KEEP | (canonical) |
| `evolution/errors.py`, `utils.py`, `__init__.py`, `api.py` | Canonical | KEEP | (canonical) |
| `constitutional_architecture/engine/evolution_engine.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/evolution_loop.py` | Constitutional | LEGACY | FIX `transformations=[]` (R1-D.3); RETIRE (R1-D.5) |
| `constitutional_architecture/engine/evolution_events.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/evolution_memory.py` | Constitutional | LEGACY | RETIRE (R1-D.5); MIGRATE SELECTED (durable) |
| `constitutional_architecture/engine/evolution_metrics.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/evolution_scheduler.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/mutation_engine.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/mutation_operators.py` | Constitutional | LEGACY | MIGRATE SELECTED (R1-D.5) |
| `constitutional_architecture/engine/mutation_planner.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/mutation_registry.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/mutation_validator.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/adaptive_mutation.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/crossover_engine.py` | Constitutional | LEGACY | RETIRE (R1-D.5; pseudo-crossover) |
| `constitutional_architecture/engine/individual.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/isr_adapter.py` | Constitutional | LEGACY | RETIRE (R1-D.5; lossy) |
| `constitutional_architecture/engine/lineage_tracker.py` | Constitutional | LEGACY | MIGRATE SELECTED (durable lineage R1-E.6); RETIRE (R1-D.5) |
| `constitutional_architecture/engine/population_manager.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/elite_manager.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/diversity_manager.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/convergence_detector.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/novelty_search.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/pareto_optimizer.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/fitness.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/verification_bridge.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/plugins.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/config.py` | Constitutional | LEGACY | RETIRE (R1-D.5) |
| `constitutional_architecture/engine/compiler_bridge.py` | Constitutional | LEGACY | RETIRE (R1-D.5; dead code) |
| `constitutional_architecture/isr/eir/model.py` | Constitutional | LEGACY | RETAIN AS DONOR → RETIRE (R1-D.5) |
| `constitutional_architecture/isr/eir/taxonomy.py` | Constitutional | LEGACY | RETAIN AS DONOR → RETIRE (R1-D.5) |
| `constitutional_architecture/isr/eir/transformation.py` | Constitutional | LEGACY | **MIGRATE SELECTED** (R1-D.3; 10 mutation operators) |
| `constitutional_architecture/governance/governance_design_fitness.py` | Constitutional | LEGACY | **MIGRATE SELECTED** (R1-D.3; F-C10-01/02) |
| `constitutional_architecture/governance/governance_fitness.py` | Constitutional | LEGACY | **MIGRATE SELECTED** (R1-D.3) |
| `constitutional_architecture/governance/schemas.py` | Constitutional | LEGACY | RETAIN AS DONOR (R1-D.3) |
| `distributed_evolution/` | Constitutional | INFRASTRUCTURE | DEFER (R2/R3; not a competing authority) |
| `civilization/` | Constitutional | HIGHER-LEVEL | DEFER (R2/R3) |

---

## 9. Cross-references

- D05 (R1-B): `folder/CONTRACT_EvolutionOperation.md`
- D06 (R1-B): `folder/CONTRACT_EvolutionRecord_EIR.md`
- D04 (R1-B): `folder/CONTRACT_ArchitectureCandidate.md`
- D2-D10: `folder/R1_D2_GATE_REPORT.md`
- R1-C C10: `folder/R1_C_LEGACY_BOUNDARY_REPORT.md` (F-C10-01, F-C10-02)
- R0: `folder/R0_RECONNAISSANCE_REPORT.md`

---

*End of D3-01. The R1-D.3 evolution inventory is complete. 30+ canonical evolution files; 27+ constitutional evolution files; 4 constitutional EIR files; 2 distributed evolution; 2+ civilization. 2 R1-C findings (F-C10-01, F-C10-02) are explicit R1-D.3 work. D3-02 (execution graph) follows.*
