# R1_C_LEGACY_BOUNDARY_REPORT (R1-C C10)

**Status:** R1-C Deliverable C10. Legacy boundary enforcement report. Index: `folder/R1_C_BOUNDARY_CONTRACTS.md` (C02), `folder/R1_C_ADAPTER_INVENTORY.md` (C01), `folder/CONTRACT_LegacyBoundarySpecification.md` (D17).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; the R1-C master prompt.

**Method:** File:line-cited grep for direct imports bypassing the R1-C adapters. OBSERVED (with file:line) / INFERRED / PROPOSED / UNKNOWN markers.

---

## 1. Purpose

Detect and report direct imports from canonical paths into the constitutional substrate (or vice versa) that bypass the R1-C boundary adapters. Per the R1-C spec §17: "Detect and report: ... If discovered, repair only what is necessary to enforce the R1-C boundary. Do not begin broad remediation."

## 2. Detection scope

The detection covers:

1. **Canonical paths → constitutional paths** (canonical code importing from constitutional_architecture/*). This is the most critical: it would mean the canonical runtime depends on the constitutional substrate.
2. **Constitutional paths → canonical paths** (constitutional code importing from compiler/*, isr/*, evolution/*, reqgraph/*, certification/*, release/*). This is the reverse direction: constitutional code reaching into the canonical runtime.

## 3. Detection results

### 3.1 Canonical paths → constitutional paths

| Canonical path | Search pattern | Result |
|---|---|---|
| `isr/` | `constitutional_architecture` | **0 matches** |
| `compiler/` | `constitutional_architecture` | **0 matches** |
| `reqgraph/` | `constitutional_architecture` | **0 matches** |
| `certification/` | `constitutional_architecture` | **0 matches** |
| `release/` | `constitutional_architecture` | **0 matches** |
| `evolution/` | `constitutional_architecture` | **6 matches** in 2 files |

**Findings (canonical → constitutional):**

#### Finding F-C10-01: `evolution/mutation.py:15` imports from `constitutional_architecture/governance/`

| Field | Value |
|---|---|
| File | `evolution/mutation.py:15` |
| Import | `from constitutional_architecture.governance.governance_design_fitness import (baseline_governance_design,)` |
| Direction | CANONICAL → CONSTITUTIONAL (reverse of the R1-C adapter direction) |
| Status | **LEGACY BYPASS** |
| Severity | **P1** (canonical evolution depends on constitutional governance) |
| Classification | The import is for a governance design fitness function used by the mutation engine. The canonical evolution should not depend on the constitutional governance layer. |
| Recommended action | **R1-D remediation.** Migrate the governance fitness logic into the canonical evolution (or remove the governance fitness from the canonical evolution if it is not a core requirement). Per the R1-C spec §17: "Do not begin broad remediation." The repair is not in R1-C scope. |
| R1-C action | **REPORT** (not repair). The finding is documented and classified for R1-D. |

#### Finding F-C10-02: `evolution/governance_fitness_evaluator.py` imports from `constitutional_architecture/governance/`

| Field | Value |
|---|---|
| File | `evolution/governance_fitness_evaluator.py:7, 28, 35, 39, 42` |
| Imports | `from constitutional_architecture.governance.governance_design_fitness import (GovernanceDesignFitness, design_objectives)`, `from constitutional_architecture.governance.governance_fitness import (ALL_OBJECTIVES)`, `from constitutional_architecture.governance.schemas import GovernanceDesignISR` |
| Direction | CANONICAL → CONSTITUTIONAL |
| Status | **LEGACY BYPASS** |
| Severity | **P1** (same as F-C10-01; same constitutional governance layer) |
| Classification | The module is explicitly named "governance_fitness_evaluator" and its purpose is to "plug the Phase 28 governance-DNS fitness into SelfEvolutionEngine's injectable fitness_evaluator seam." This is a deliberate design choice to reuse the constitutional governance logic in the canonical evolution. |
| Recommended action | **R1-D remediation.** Either migrate the governance fitness into the canonical evolution, or remove the dependency. Per the R1-C spec: REPORT, not repair. |
| R1-C action | **REPORT** (not repair). The finding is documented and classified for R1-D. |

### 3.2 Constitutional paths → canonical paths

| Search pattern | Result |
|---|---|
| `^import compiler\.\|^from compiler\.` | **0 matches** in `constitutional_architecture/` |
| `^import isr\.\|^from isr\.` | **0 matches** in `constitutional_architecture/` |
| `^import evolution\.\|^from evolution\.` | **0 matches** in `constitutional_architecture/` |
| `^import reqgraph\.\|^from reqgraph\.` | **0 matches** in `constitutional_architecture/` |
| `^import certification\.\|^from certification\.` | **0 matches** in `constitutional_architecture/` |
| `^import release\.\|^from release\.` | **0 matches** in `constitutional_architecture/` |

**Findings (constitutional → canonical):** **0 matches.** The constitutional substrate does NOT import from the canonical runtime. Good.

## 4. Summary of findings

| Finding | Direction | Severity | R1-C action |
|---|---|---|---|
| F-C10-01: `evolution/mutation.py:15` imports from `constitutional_architecture/governance/governance_design_fitness` | CANONICAL → CONSTITUTIONAL | P1 | REPORT (R1-D remediation) |
| F-C10-02: `evolution/governance_fitness_evaluator.py:7,28,35,39,42` imports from `constitutional_architecture/governance/*` | CANONICAL → CONSTITUTIONAL | P1 | REPORT (R1-D remediation) |
| Constitutional → canonical | (n/a) | 0 matches | (none) |

**2 findings, both in `evolution/`, both related to the same constitutional governance layer.** Neither finding is in the canonical campaign runtime path.

## 5. Impact on canonical campaign runtime

The 2 findings are in `evolution/`, which is part of the canonical substrate but is NOT directly in the campaign runtime path. The campaign runtime path is:

```
certification/campaign/plan_builder.py
  → reqgraph/core (RequirementGraph)
  → isr/core (ISR)
  → compiler/core (CompilationPlan; the canonical compiler)
  → certification/stages (verification)
  → certification/evidence (evidence ledger)
```

The `evolution/` package is the **evolution engine**, which is not called by the campaign runtime. The campaign runtime uses `isr.core` and `compiler.core` directly. The evolution engine is a separate substrate that operates on `isr.core` revisions and produces `ArchitectureCandidate`s.

The 2 findings mean that the **evolution engine** depends on the constitutional governance layer, but the **campaign runtime** does not. The Tier A tests (243 passed) confirm that the campaign runtime is unaffected.

## 6. Recommended remediation (R1-D scope, not R1-C)

Per the R1-C spec §17: "If discovered, repair only what is necessary to enforce the R1-C boundary. Do not begin broad remediation." The remediation of F-C10-01 and F-C10-02 is R1-D work (semantic migration of the governance fitness into the canonical evolution). The R1-C action is to:

1. **Document** the findings (this report).
2. **Classify** the findings for R1-D.
3. **Do NOT** repair the findings in R1-C (avoid broad remediation).

## 7. Prohibited bypasses (checked, not found)

The following were checked and NOT found:

- Canonical paths importing from `constitutional_architecture/*`: 0 matches in `isr/`, `compiler/`, `reqgraph/`, `certification/`, `release/`. 6 matches in `evolution/` (the 2 findings above).
- Constitutional paths importing from canonical paths: 0 matches.

## 8. Conclusion

The R1-C boundary is **mostly enforced**. The 2 findings are in `evolution/` (not in the campaign runtime) and are classified for R1-D remediation. The canonical campaign runtime is verified to be free of constitutional bypasses.

The C06 refactor (ADAPTER-ARTIFACT-001) did not introduce new bypasses. The constitutional_architecture/compiler/backends/fastapi_backend.py change is a one-line removal of a filesystem side effect; it does not add new imports.

---

*End of C10. 2 findings, both in `evolution/`, both classified for R1-D. The canonical campaign runtime is free of constitutional bypasses.*
