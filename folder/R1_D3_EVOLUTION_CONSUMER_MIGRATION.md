# R1_D3_EVOLUTION_CONSUMER_MIGRATION (R1-D.3 D3-09)

**Status:** R1-D.3 Deliverable D3-09. Consumer migration/reconciliation. Index: `folder/R1_D3_EVOLUTION_INVENTORY.md` (D3-01).

**Authority:** R1-A; R1-B D02–D20; R1-C C01–C12; R1-D.1; R1-D.2; R1-D.3 master prompt.

---

## 1. Purpose

Inventory every consumer of evolution representations and classify: CANONICAL / MIGRATED / LEGACY / ADAPTER / UNUSED / DEFERRED.

---

## 2. Consumer table

| Consumer | Current representation | Canonical representation | Action | Status |
|---|---|---|---|---|
| `evolution/engine.py:SelfEvolutionEngine` | `GovernanceAwareFitnessEvaluator` (canonical, post-fix) | same | CANONICAL | unchanged behavior; import chain now canonical-only |
| `evolution/mutation.py:MutationEngine` | `baseline_governance_design()` (canonical, post-fix) | same | MIGRATED | F-C10-01 fixed; output identical (verified) |
| `tests/test_governance_fitness_evaluator.py` | canonical evaluator + constitutional baseline (comparison) | canonical | CANONICAL | passes; constitutional import is test-only comparison |
| `tests/test_governance_recombination_invariant.py` | `governance_objectives_for` (canonical) | same | CANONICAL | passes |
| `tests/r1d3/test_evolution_contracts.py` | canonical only (+ constitutional comparison in 2 tests) | same | CANONICAL | 32/32 pass |
| `genesis/mapper.py`, `genesis/validator.py` | `evolution/core` genome/construction | same | CANONICAL | unchanged |
| `certification/campaign/*` | `compiler/core` (not evolution) | same | CANONICAL | unchanged; campaign does not consume evolution |
| `constitutional_architecture/tests/*` | constitutional engine/EIR | n/a | LEGACY | untouched; not in Tier-A |
| `constitutional_architecture/engine/evolution_loop.py` | constitutional EIR (`transformations=[]`) | n/a | LEGACY | untouched; retired R1-D.5 |
| `distributed_evolution/` | execution infrastructure | n/a | DEFERRED | R2/R3; not a competing authority |
| `civilization/` | higher-level platform | n/a | DEFERRED | R2/R3 |

---

## 3. Adapter inventory

| Adapter | Direction | Status |
|---|---|---|
| `evolution/governance_fitness_evaluator.py:governance_objectives_for` (dict in → objectives out) | internal (canonical → canonical) | CANONICAL (post-fix; was LEGACY → CANONICAL bypass, now removed) |
| None other | — | No adapters introduced. |

No new adapters. The two bypasses were removed, not adapted.

---

## 4. Unused

`constitutional_architecture/engine/compiler_bridge.py` remains unused (dead code; R1-D.5). `constitutional_architecture/compilers/*` evolution-adjacent consumers remain test-only.

---

## 5. Verdict

All canonical consumers are CANONICAL or MIGRATED. No canonical consumer imports constitutional evolution at runtime (verified by `test_no_constitutional_imports_*`). Test-only constitutional imports in 2 R1-D.3 tests are explicit behavioral-equivalence comparisons, not runtime dependencies.

---

*End of D3-09. D3-10 follows.*
