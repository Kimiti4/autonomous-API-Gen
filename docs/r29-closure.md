# R2.9 Closure Record — Autonomous Evolutionary Search

**Status:** CLOSED · CERTIFIED
**R2.9.8 certification commit:** `19499b8`
**R2.9.7 checkpoint commit:** `7ce559c`
**Full hermetic suite at closure:** 1732 passed, 2 skipped, 6 deselected (299s)
**Docker real-substrate certification:** CERTIFIED (1 passed, 186.97s)

---

## 1. Purpose

This record closes **R2.9**, the campaign that transformed the Evolution Engine
from a human-directed repair tool into a **certified autonomous evolutionary
search system**. It documents what was proven, how it was certified, what
remains KNOWN_DEBT, and which constitutional principles each slice enforced.

R2.9 completes the arc begun in R2.4:

```
R2.4  deterministic repair
  → R2.6  competing candidates / Pareto selection
    → R2.8  adversarial trust boundary (anti-gaming)
      → R2.9  certified autonomous evolutionary search   ← this phase
```

R2.9 does **not** include:
- The Phase-28 `content_hash` migration (separately gated — see ADR).
- Generation from requirements / richer ISR / structural crossover (R2.10).

---

## 2. The arc — slice by slice

| Slice | Capability | Constitutional invariant established |
|---|---|---|
| **R2.9.1** | Execution-environment honesty | Capability probes must not lie. `DockerExecutionEnvironment.available()` pings the daemon, not just the CLI. Four "failures" were `ENVIRONMENT_GAP`, not code defects. |
| **R2.9.2** | Autonomous constructive variation | Variation proposes **ISR deltas only**, never source patches. `NullCrossover` defers structural recombination. No scalar objective — R2.6 `FitnessVector` + Pareto remain authoritative. |
| **R2.9.3** | Multi-generation evolution | `EvolutionState` is **search-process state, kept outside the ISR**. Lineage threads the selected ISR as the sole parent of the next generation. Six explicit termination modes. |
| **R2.9.4** | Diversity / anti-monoculture | Diversity is **observed first, then minimally intervened**, never used as a selection objective. Collapse signal read from the raw population before dedup. |
| **R2.9.5** | Adaptive operator scheduling | The scheduler answers *"where to search,"* **never** *"which candidate is correct."* Laplace smoothing + mandatory exploration floor + largest-remainder apportionment. `BudgetAllocation` cannot carry a candidate, fitness, or verdict. |
| **R2.9.6** | Multiple simultaneous defects | Partial repair = **Pareto subset dominance**, never a scalar count. Cumulative resolution tracker prevents fix-A/break-A oscillation. Interaction detected **by execution**, not by rules. |
| **R2.9.7** | Identity separation / reproducibility audit | `semantic_hash` / `provenance_identity` / `runtime_execution_id` are **never conflated**. Inclusion-based semantic projection; canonicalization without `default=str`. |
| **R2.9.8** | Evolution Engine Certification | Ten behavioral dimensions certified by running the live machinery. Debt recorded as `KNOWN_DEBT`, **never silently reinterpreted** as pass or fail. |

---

## 3. Certification result (R2.9.8)

Engine verdict derived **only** from the mandatory behavioral dimensions.
Debt dimensions are recorded for transparency and do not block the behavioral
certification.

### Mandatory behavioral dimensions (all must PASS)

| Dimension | Status | Verified by |
|---|---|---|
| constructive_capability | PASS | R2.9.2 — generates a candidate that resolves the injected defect |
| boundary_compliance | PASS | R2.8 — deceptive candidate rejected by evidence/holdout/invariant gates |
| causal_validity | PASS | R2.9.2/R2.4 — selected change is an ISR delta; fresh recompile matches |
| regression_safety | PASS | R2.9.6 — cumulative resolution preserved; no oscillation |
| diversity_preservation | PASS | R2.9.4 — entropy above collapse floor; intervention effective |
| adaptive_scheduling | PASS | R2.9.5 — allocation responds to evidence; exploration floor holds |
| multi_generation_lineage | PASS | R2.8.11/R2.9.3 — parent → candidate → selection chain intact |
| semantic_reproducibility | PASS | R2.9.7 — same seed → same semantic trajectory |
| evidence_integrity | PASS | R2.8.9/10 — ledger/environment bindings valid; tampering fails |
| identity_separation | PASS | R2.9.7 — semantic identity independent of provenance/runtime |

### Recorded debt dimensions (non-blocking)

| Dimension | Status | Remediation target |
|---|---|---|
| provenance_content_identity | **KNOWN_DEBT** | `phase28_identity_migration` |
| phase28_identity_migration | **NOT_CERTIFIED** | — (pending, separately gated) |
| real-substrate evolution (Docker) | **KNOWN_DEBT** when `POPULATION_EXHAUSTION` | `r29.3_substrate_population_exhaustion` |

**Overall engine verdict:** `CERTIFIED` (hermetic) · `CERTIFIED` (Docker real path).

---

## 4. The semantic-reproducibility model (R2.9.7)

The constitution declares *"The ISR is the constitutional source of truth."*
A source of truth whose identity shifts with `created_at` is not a source of
truth. R2.9.7 established three identities that must never be conflated:

```
semantic_hash          = H(canonical(Semantic Architecture))   — stable
provenance_identity    = lineage (parent, mutation source, evolution, created_at)
runtime_execution_id   = execution-instance identity            — ephemeral
```

- `semantic_hash` is the **canonical reproducibility identity**, computed by an
  **inclusion-based projection** (the projector defines what architecture *is*,
  not "everything except volatile fields").
- Canonical serialization has **no `default=str` fallback** — unhandled types
  raise, forcing explicit canonicalization.
- The Phase-28 `content_hash` is **known to be tainted by provenance** and is
  recorded as `KNOWN_DEBT`; it is **not** the reproducibility identity.

Reproducibility contract proven:
```
semantic_reproducible = true
content_reproducible  = false
divergence_cause      = provenance_volatility   (compounds at gen ≥ 1)
```

---

## 5. Known-debt register

| Debt | Status | Remediation target | ADR |
|---|---|---|---|
| Phase-28 `content_hash` conflates provenance into semantic identity | KNOWN_DEBT | `phase28_identity_migration` | `docs/adr/adr-phase28-identity-migration.md` |
| Phase-28 identity migration not yet executed | NOT_CERTIFIED | — | same ADR |
| Real-substrate evolution hits `POPULATION_EXHAUSTION` under Docker | KNOWN_DEBT | `r29.3_substrate_population_exhaustion` | `docs/adr/adr-population-exhaustion-disposition.md` |

Every `KNOWN_DEBT` entry carries a remediation target and evidence. Debt is
tracked, never buried.

---

## 6. Constitutional alignment

| Constitutional principle | How R2.9 enforced it |
|---|---|
| ISR is the sole architectural source of truth | All variation/selection on ISR deltas; `EvolutionState` kept outside the ISR; semantic identity separated (R2.9.7) |
| Evolution Engine operates exclusively on the ISR | No source patches; backends never redefine architecture |
| Multi-objective optimisation; avoid single aggregate score | `FitnessVector`, Pareto frontier, subset dominance for partial repair; no scalar objective |
| Each evolution stage independently replaceable | Protocols for variation, crossover, scheduling, diversity policy, semantic projection |
| Security by design / anti-gaming | Every candidate traverses the R2.8 boundary; scheduler cannot escalate authority |
| Architectural reasoning transparent | Every decision recorded in the `EvolutionLedger`; `KNOWN_DEBT` recorded with remediation targets |
| ADRs for significant decisions | Two ADRs committed with this closure |
| Documentation evolves with implementation | This closure record |

---

## 7. What R2.9 enables

The engine can now **autonomously**:
- generate constructive repair hypotheses (ISR deltas),
- iterate them across generations with intact lineage,
- preserve diversity and avoid monoculture,
- adapt search allocation from evidence,
- repair multiple interacting defects without regression,
- do all of this reproducibly under a stable semantic identity,
- and certify itself honestly.

This is the trust foundation R2.10 (production software generation) stands on.

---

## 8. Next phase boundary

**R2.10 — Production software generation.** Transitions from *evolving an
existing artifact* to *generating from requirements*: exercises the
Requirement Graph → ISR pipeline, expands the ISR beyond the FSM substrate
into Component/Requirement graphs, and introduces structural crossover. R2.10
inherits the three-identity model and must resolve the Phase-28 identity
migration before relying on `content_hash` for reproducibility.