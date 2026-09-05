# R1_D3_EVOLUTION_MIGRATION_MAP (R1-D.3 D3-08)

**Status:** R1-D.3 Deliverable D3-08. Evolution migration map. Index: `folder/R1_D3_EVOLUTION_INVENTORY.md` (D3-01), `folder/R1_D3_EVOLUTION_SEMANTIC_COMPARISON.md` (D3-03).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; R1-D.1 D1–D9; R1-D.2 D2-D1–D2-D10; the R1-D.3 master prompt.

---

## 1. Purpose

Every discovered evolution implementation receives a disposition: MIGRATE / ADAPT / KEEP / DEPRECATE / RETIRE / DEFER. No unexplained duplicate authority may remain.

---

## 2. Migration actions

### 2.1 MIGRATE (canonical implementation established in R1-D.3)

| # | Source | Destination | Rationale |
|---|---|---|---|
| M-01 | `constitutional_architecture.governance.governance_design_fitness.baseline_governance_design` | `evolution/core/governance_design.py:baseline_governance_design` (NEW) | F-C10-01 fix. Same 11-key dict, no constitutional schema dependency. Behavioral equivalence verified by `test_canonical_baseline_matches_constitutional`. |
| M-02 | `constitutional_architecture.governance.{governance_design_fitness,governance_fitness}` (6-objective vocabulary + scoring heuristics) | `evolution/core/governance_fitness.py` (NEW; ALL_OBJECTIVES, GovernanceDesignFitness, design_objectives, to_fitness_objectives) | F-C10-02 fix. Same vocabulary, same order, same scores (verified to 9 decimal places by `test_canonical_objectives_match_constitutional`). Fail-closed validation added for malformed designs. |

### 2.2 ADAPT (narrow adapter, one-way LEGACY → CANONICAL)

| # | Source | Destination | Rationale |
|---|---|---|---|
| A-01 | `evolution/mutation.py:15` import | `evolution/core/governance_design.py` import | Same function name, same return shape. One-line import change. |
| A-02 | `evolution/governance_fitness_evaluator.py` imports + `GovernanceDesignISR(**design_dict)` construction | `evolution/core/governance_fitness.py` imports + validated dict pass-through | Same public function names (`governance_objectives_for`, `fail_closed_governance_objectives`, `GovernanceAwareFitnessEvaluator`). Fail-closed behavior preserved and strengthened. |

### 2.3 KEEP (canonical, no change)

`evolution/core/{operations,genome,fitness,fitness_evaluator,selection,construction,materialize,refinement}.py`, `evolution/{engine,genome,mutation,recombination,selection,fitness,pareto,history,memory,models,feedback*,governance,governance_api,governance_safety,population,multi*,orchestration*,observability*,compiler_loop,compiler_fitness,analytics,verification,promotion*,simulation,errors,utils,api}.py`, `evolution/history.py:EvolutionHistoryRepository` (hash-chained audit trail — the canonical record surface).

### 2.4 DEPRECATE (still imported, scheduled for removal)

None in R1-D.3. The constitutional EIR remains importable but is not consumed by the canonical runtime.

### 2.5 RETIRE (R1-D.5; documented, not executed in R1-D.3)

Constitutional evolution engine files (27 in `constitutional_architecture/engine/`), constitutional EIR model files, `compiler_bridge.py` (dead code), per-category evolution consumers. Retirement is R1-D.5 scope; R1-D.3 only classifies.

### 2.6 DEFER (out of R1-D.3 scope)

| Item | Deferred to | Reason |
|---|---|---|
| `transformations=[]` repair inside `constitutional_architecture/engine/evolution_loop.py:107-114` | R1-D.5 (with retirement) | The file is constitutional legacy, not canonical runtime. Repairing it would be remediation of a retired component (R1-C F11 analog). Documented as finding F-D3-01. |
| Durable lineage (`release/evidence/lineage/`) | R1-E.6 | In-memory lineage is canonical and tested; durability is a later phase. |
| New `evolution/core/record.py` module | **NOT CREATED (decision)** | `EvolutionEvent` + `EvolutionHistoryRepository` + `CandidateEvaluationRecord` already provide the record surface (hash-chained, append-only). A new module would duplicate authority (audit §39). Documented as decision D-D3-01. |
| Cross-contract fitness from VerificationResult/RuntimeObservation | Future R-phase | D12 deferred (C-17); D14 mapping exists but no consumer yet. |
| New evolution algorithms, distributed execution, population scaling | Out of scope | R1-D.3 §5. |

---

## 3. Decisions

### Decision D-D3-01: no new `evolution/core/record.py` module

The D06 contract §12–14 forward-references "a new `evolution/core/record.py` (R1-D.3)". Investigation found the record surface already exists: `EvolutionEvent` (hash-chained audit event with id, proposal, type, actor, details, timestamp, previous/event hashes) + `EvolutionHistoryRepository` (append-only, hash-chained) + `CandidateEvaluationRecord` (per-candidate evaluation state). Creating `record.py` would introduce a parallel representation (audit §39 anti-pattern). **Decision: no new module.** The D06 contract fields map onto `EvolutionEvent.details` + history; the mapping is documented in D3-11.

### Decision D-D3-02: constitutional `transformations=[]` documented, not repaired

`constitutional_architecture/engine/evolution_loop.py:107-114` constructs EIR with `transformations=[]`. The file is constitutional legacy consumed only by constitutional tests, never by the canonical runtime. Repairing it = remediation of a retired component. **Decision: document as finding F-D3-01, retire with the file in R1-D.5.** Canonical lineage (OperationRecord + history) records sources explicitly (pinned by `test_constitutional_transformations_defect_documented`).

---

## 4. Findings

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-D3-01 | P1 | Constitutional `evolution_loop.py:110` `transformations=[]` despite performed mutations. | Documented; file retired in R1-D.5. Canonical lineage unaffected (verified: canonical runtime never imports the file). |
| F-C10-01 | P1 (R1-C) | `evolution/mutation.py:15` constitutional import. | **FIXED in R1-D.3** (M-01/A-01). |
| F-C10-02 | P1 (R1-C) | `evolution/governance_fitness_evaluator.py` constitutional imports. | **FIXED in R1-D.3** (M-02/A-02). |

---

## 5. Code change scope (actual)

| File | Change |
|---|---|
| `evolution/core/governance_design.py` | NEW (M-01). |
| `evolution/core/governance_fitness.py` | NEW (M-02). |
| `evolution/mutation.py` | Import rewired (A-01). Docstring untouched otherwise. |
| `evolution/governance_fitness_evaluator.py` | Imports rewired + `GovernanceDesignISR(**design_dict)` replaced by validated dict pass-through (A-02). Module docstring updated (constitutional reuse note removed). |
| `folder/CONTRACT_EvolutionOperation.md` | Part II refinement (D3-04). |
| `tests/r1d3/` | NEW (32 tests). |

No other production files modified.

---

## 6. Cross-references

- D3-09: `folder/R1_D3_EVOLUTION_CONSUMER_MIGRATION.md` (next)
- D3-12: `folder/R1_D3_EVOLUTION_TEST_REPORT.md`
- D3-13: `folder/R1_D3_GATE_REPORT.md`

---

*End of D3-08. 2 MIGRATE, 2 ADAPT, 0 broad rewrites. 2 R1-C findings fixed. 2 decisions recorded. D3-09 follows.*
