# R1_D3_EVOLUTION_TEST_REPORT (R1-D.3 D3-12)

**Status:** R1-D.3 Deliverable D3-12. Contract and regression tests. Index: `folder/R1_D3_EVOLUTION_INVENTORY.md` (D3-01).

**Authority:** R1-A; R1-B D02–D20; R1-C; R1-D.1; R1-D.2; R1-D.3 master prompt §§23–24, 32.

---

## 1. Test commands and counts

| Suite | Command | Count | Result |
|---|---|---|---|
| Tier-A | `python -m pytest tests/cbc1/` | 243 | PASS |
| R1-C | `python -m pytest tests/r1c/` | 15 | PASS |
| R1-D.1 | `python -m pytest tests/r1d1/` | 21 | PASS |
| R1-D.2 | `python -m pytest tests/r1d2/` | 33 | PASS |
| R1-D.3 | `python -m pytest tests/r1d3/` | 32 | PASS |
| v12 | `python -m pytest tests/v12/` | 23 | PASS |
| Governance evaluator | `python -m pytest tests/test_governance_fitness_evaluator.py` | 12 | PASS |
| Governance recombination | `python -m pytest tests/test_governance_recombination_invariant.py` | 1 | PASS |
| **Combined** | all of the above | **380** | **PASS (1 deselected, pre-existing)** |

Wall time: ~96s. No failures. No regressions. No weakened assertions.

---

## 2. R1-D.3 test coverage (32 tests)

| Area | Tests | What is proven |
|---|---|---|
| Contract (OperationRecord, identity) | 4 | sources/result preserved; crossover has 2 sources; genome hash stable 64-hex |
| Lineage (parent→child, multi-gen, branching, crossover, hash chain, append-only) | 6 | reconstructable linear/branching/crossover lineage; history hash links; prior events immutable |
| Mutation (valid, zero-rate, decision-space, full-rate) | 4 | valid output; rate-0 identity; values ⊆ space; full-rate changes |
| Crossover (two parents, gene provenance, reproducibility, single-parent families) | 4 | child from both parents; every child gene ∈ parent values; same seed → same child |
| Determinism (same seed, explicit rng) | 2 | reproducibility; stochasticity explicit |
| Provenance (record fields, design_id, history actor/proposal) | 3 | OperationRecord carries rate/genes; design_id preserved; history carries actor/proposal/details |
| Failure (empty selection, malformed/absent governance, invalid space value) | 4 | `select([])` raises; malformed `{design_id:x}` raises; `{}` raises; invalid value rejected |
| Compatibility (no constitutional imports ×2, baseline equivalence, objectives equivalence, defect pin) | 5 | both bypasses removed (static); canonical baseline dict == constitutional; canonical scores == constitutional to 1e-9; canonical records never drop sources |

---

## 3. Semantic coverage

| Migration | Test coverage | Status |
|---|---|---|
| M-01 (baseline_governance_design) | `test_canonical_baseline_matches_constitutional` + mutation injection test (existing suite) | COVERED |
| M-02 (6-objective vocabulary + heuristics) | `test_canonical_objectives_match_constitutional` (9-decimal equivalence) + 12 existing evaluator tests | COVERED |
| A-01/A-02 (import rewire) | static no-import tests + full evaluator suite | COVERED |
| D-D3-01 (no record.py) | `test_history_*` hash-chain/append-only | COVERED (existing surface) |
| F-D3-01 (transformations=[]) | `test_constitutional_transformations_defect_documented` | PINNED (canonical contrast) |

---

## 4. Negative cases

Missing parent: covered by `test_selection_empty_rejected` (fail-closed selection) and fail-closed governance tests. Invalid operation: covered by malformed/absent governance raising. Constraint violation: covered by `test_decision_space_rejects_invalid_value`. Verification/provenance failure: governance fail-closed vector propagates to Pareto exclusion (existing `test_select_pareto_ranks_governance_candidate_over_absent`).

---

## 5. Regression analysis

| Suite | Before R1-D.3 | After R1-D.3 | Delta |
|---|---|---|---|
| Tier-A | 243 | 243 | 0 |
| R1-C | 15 | 15 | 0 |
| R1-D.1 | 21 | 21 | 0 |
| R1-D.2 | 33 | 33 | 0 |
| v12 | 23 | 23 | 0 |
| Governance (2 files) | 13 | 13 | 0 |
| R1-D.3 | 0 | 32 | +32 |
| **Total** | **348** | **380** | **+32, 0 regressions** |

---

## 6. Failures / skipped / pre-existing

Failures: none. Skipped: 1 deselected (pre-existing Tier-A marker, unrelated). Pre-existing failures: none.

---

*End of D3-12. D3-13 follows.*
