# R1_D3_EVOLUTION_LEGACY_DISPOSITION (R1-D.3 D3-10)

**Status:** R1-D.3 Deliverable D3-10. Legacy disposition. Index: `folder/R1_D3_EVOLUTION_INVENTORY.md` (D3-01), `folder/R1_D3_EVOLUTION_MIGRATION_MAP.md` (D3-08).

**Authority:** R1-A; R1-B D02–D20; R1-C C01–C12; R1-D.1; R1-D.2; R1-D.3 master prompt.

---

## 1. Purpose

Document: constitutional EIR, legacy evolution APIs, distributed evolution implementations, category-specific evolution, obsolete evolution models, compatibility adapters. Each receives KEEP / MIGRATE / ADAPT / DEPRECATE / RETIRE / DEFER.

---

## 2. Disposition table

| Item | Disposition | Rationale |
|---|---|---|
| `constitutional_architecture/isr/eir/{model,taxonomy}.py` | RETIRE (R1-D.5) | Superseded by D06 contract; no canonical consumer. |
| `constitutional_architecture/isr/eir/transformation.py` (10 operators) | MIGRATE SELECTED (evaluated in D3-03 §4) | Operator semantics available as donors; generic canonical mutation retained. No operator auto-promoted. |
| `constitutional_architecture/engine/evolution_engine.py`, `evolution_loop.py`, `individual.py` | RETIRE (R1-D.5) | Competing runtime; `transformations=[]` defect (F-D3-01) dies with the file. |
| `constitutional_architecture/engine/crossover_engine.py` | RETIRE (R1-D.5) | Pseudo-crossover; canonical real crossover retained. |
| `constitutional_architecture/engine/mutation_{engine,operators,planner,registry,validator}.py`, `adaptive_mutation.py` | RETIRE (R1-D.5) | Competing runtime; selected semantics donors only. |
| `constitutional_architecture/engine/{population_manager,elite_manager,diversity_manager,convergence_detector,novelty_search,pareto_optimizer}.py` | RETIRE (R1-D.5) | Competing runtime. |
| `constitutional_architecture/engine/{lineage_tracker,evolution_memory,evolution_events,evolution_metrics,evolution_scheduler,fitness,verification_bridge,plugins,config}.py` | RETIRE (R1-D.5) | Competing runtime; durable lineage is R1-E.6 greenfield. |
| `constitutional_architecture/engine/isr_adapter.py` | RETIRE (R1-D.5) | Lossy TypedGraph adapter; canonical ISR needs no cross-representation. |
| `constitutional_architecture/engine/compiler_bridge.py` | RETIRE (R1-D.5; immediate candidate) | Dead code; no callers. |
| `constitutional_architecture/governance/{governance_design_fitness,governance_fitness,schemas}.py` (as consumed by evolution) | MIGRATED (R1-D.3) | Vocabulary + heuristics absorbed into `evolution/core/governance_{design,fitness}.py`. Constitutional files themselves untouched (governance layer retains them; evolution no longer imports them). |
| `distributed_evolution/` | DEFER (R2/R3) | Execution infrastructure, not competing semantics. |
| `civilization/` evolution-adjacent | DEFER (R2/R3) | Higher-level platform. |
| Category-specific evolution (in compilers/backends/domain generators) | RETIRE as authority; plugin/operator/constraint roles permitted | Per R1-D.3 §21; none found as independent authority in inventory. |
| `evolution/governance_fitness_evaluator.py` (post-fix) | KEEP | Canonical; now constitutional-import-free. |
| `evolution/mutation.py` (post-fix) | KEEP | Canonical; now constitutional-import-free. |
| `evolution/core/{operations,genome,fitness,selection,construction}` | KEEP | Canonical substrate. |
| `evolution/history.py:EvolutionHistoryRepository` | KEEP | Canonical record surface (hash-chained). |

---

## 3. Compatibility adapters

None created. The two bypasses were removed by migration, not adapted. No LEGACY → CANONICAL adapter was necessary because the migrated semantics are self-contained (dict in → dict/scores out).

---

## 4. Verdict

Every discovered implementation is classified. No unexplained duplicate authority remains. Constitutional files are untouched (retirement is R1-D.5 execution, not R1-D.3).

---

*End of D3-10. D3-11 follows.*
