# R2.9 Closure Record — Autonomous Evolutionary Search

**Status:** CLOSED · CERTIFIED
**R2.9.8 certification commit:** `19499b8`
**R2.9.7 checkpoint commit:** `7ce559c`
**Phase-28 identity migration commit:** `582356b`
**Full hermetic suite at closure:** 1744 passed, 2 skipped, 7 Docker-gated deselected (811.88s)
**Docker real-substrate certification:** CERTIFIED (1 passed, 186.97s)
**Post-migration real-substrate:** R2.9.7 audit passed (243.54s) · R2.9.8 real path passed (295.43s) · R2.9.3 real path passed pre- and post-migration (238.43s / 264.27s)

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
- Generation from requirements / richer ISR / structural crossover (R2.10).
- The Phase-28 `content_hash` migration was separately gated from R2.9 and is
  **now executed** (see ADR `adr-phase28-identity-migration.md`, Status:
  EXECUTED).

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

### Recorded debt dimensions (non-blocking) — CLOSED post-migration

| Dimension | Status | Remediation target |
|---|---|---|
| provenance_content_identity | **PASS** (was KNOWN_DEBT) | `phase28_identity_migration` — executed |
| phase28_identity_migration | **PASS** (was NOT_CERTIFIED) | — (executed; gates green) |
| real-substrate evolution (Docker) | **PASS** — exhaustion falsified by controlled experiment (pre- and post-migration runs both converge; certifier's `KNOWN_DEBT` path remains as honest flake-handling) | `r29.3_substrate_population_exhaustion` — closed |

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
  not "everything except volatile fields"). POST-MIGRATION the projection lives
  in `constitutional_architecture/isr/semantics/projection.py` and **is**
  `ISR.content_hash` — `content_hash == semantic_hash == stable_isr_hash` on
  every substrate.
- Canonical serialization has **no `default=str` fallback** — unhandled types
  raise, forcing explicit canonicalization.
- The Phase-28 `content_hash` provenance taint is **eliminated** by the
  executed migration; provenance (`created_at`, `parent_hash`) feeds lineage
  only, never the semantic hash.

Reproducibility contract proven (post-migration):
```
semantic_reproducible = true
content_reproducible  = true
divergence_cause      = None        (was provenance_volatility)
phase28_tainted_by_provenance = false
```

---

## 5. Known-debt register

| Debt | Status | Remediation target | ADR |
|---|---|---|---|
| Phase-28 `content_hash` conflated provenance into semantic identity | **RESOLVED** (migration executed; `content_hash` is the semantic projection) | `phase28_identity_migration` | `docs/adr/adr-phase28-identity-migration.md` |
| Phase-28 identity migration | **EXECUTED** (13 migration gates + full-suite regression green) | — | same ADR |
| Real-substrate `POPULATION_EXHAUSTION` under Docker | **CLOSED** — falsified by controlled experiment: the R2.9.3 real-substrate test converges to SUCCESS on both `45e8a77` (pre-migration) and `582356b` (post-migration); observed exhaustion was an infra-transient flake, not systematic; phantom elite advancement (the hermetic mechanism) is fixed by the migration | `r29.3_substrate_population_exhaustion` — closed | `docs/adr/adr-population-exhaustion-disposition.md` |

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
| ADRs for significant decisions | Three ADRs committed with this closure |
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

## 8. R2.10.1 — ISR capability / expressivity audit (signed matrix)

**Status:** executed · diagnostic-only (no new ISR primitives — that is R2.10.2)
**Suite:** 17 new tests green (`tests/test_r29_10_1_capability_audit.py`, criteria A–H)
**Full hermetic suite at R2.10.1:** 1761 passed, 2 skipped, 7 Docker-gated deselected (197.29s)

The audit answers the question R2.10 stands on: *which constitutional
capabilities does the ISR represent, and which can the evolution machinery
evolve end-to-end (mutate → validate pre-execution → compile → observe →
lineage)?* It is a measuring instrument, not a feature phase.

### 8.1 Machinery

- `tiannara/application/evolution/isr_capability_audit.py` — `CapabilityStatus`
  (EXPRESSED / PARTIAL / PROJECTED / MISSING), six-dimension
  `CapabilityAssessment` (represented, independently_mutatable,
  independently_validatable, compilable, observable, lineage_tracked +
  `projected_via`), `derive_status` (**the only** status rule — status is
  derived, never asserted), `ISRCapability`, `ISRCapabilityAuditResult`
  (integrity / unclassified / by_status / content_hash), `CapabilityProbe`
  protocol + 30-probe default matrix, `MutationLocalityProbe` /
  `LocalityResult` (per-gene hashing), `ISRCapabilityAudit` runner.
- **Per-gene semantic identity** is the enabling mechanism: every gene is
  addressed by a path into the semantic projection and hashed with the same
  `canonicalize` as `content_hash` — gene hashes compose with ISR identity.
- The signed matrix is anchored as an **`ISR_CAPABILITY_AUDIT`** ledger event
  (content-hashed, chain-anchored — the R2.8.14 certification pattern), so
  R2.10.2 starts from an attested baseline.
- Compile surface measured against the real backend: only
  `WorkflowState.metadata['awaits']` + `WorkflowTransition.trigger` are
  lowered (`async_resolution_module`); the `SystemModel` stub ignores all
  other genes.

### 8.2 Attested matrix (full-carrier recipe ISR)

`isr_hash 07d774f1…` · matrix content hash `8cfb4c90…` · integrity `true`

| Status | Count | Capabilities |
|---|---|---|
| **EXPRESSED** | 2 | `behavior_transitions`, `behavior_await_surface` |
| **PARTIAL** | 18 | `architecture_components`, `architecture_dependencies`, `architecture_interfaces_apis`, `architecture_modules`, `behavior_error_states`, `behavior_events_triggers`, `behavior_guards_actions`, `behavior_state_semantics`, `data_entities_schema`, `data_persistence_consistency`, `deployment_topology`, `evolution_lineage_provenance`, `observability`, `operational_policies`, `performance_scalability`, `requirements_constraints`, `security_authentication_trust`, `security_authorization` |
| **PROJECTED** | 0 | — (no capability is sufficiently carried by an existing projection today — recorded honestly, not forced) |
| **MISSING** | 10 | `architecture_boundaries`, `behavior_temporal_semantics`, `business_capabilities`, `data_migrations`, `deployment_rollout_rollback`, `documentation`, `evolution_objectives_protected_regions`, `reliability_resilience`, `requirements_acceptance_traceability`, `testing_anchoring` |

### 8.3 Findings

- The **FSM substrate is the only end-to-end evolvable surface** — the two
  EXPRESSED rows are exactly the transition/await genes the R2.4–R2.9
  machinery mutates, gates, compiles, observes, and tracks.
- The 18 PARTIAL rows are overwhelmingly "represented but not evolvable":
  no mutation operator exists for entities/services/interfaces/policies/
  events/deployment, and the compiler backend does not lower them. Guards
  and actions are mutatable (`GuardRelaxationOperator`,
  `ActionInjectionOperator`) but never compiled/observed.
- The 10 MISSING rows are the **R2.10.2 primitive backlog** (dependency
  direction/boundaries, temporal semantics, migrations, rollout/rollback,
  acceptance/traceability, resilience, objectives/protected regions,
  documentation, testing anchoring, business capabilities). None has a
  carrier today; `PROJECTED` stays empty because free-form `Constraint`
  strings are not sufficient projections (no enforced semantics).
- Acceptance criteria A–H proven: coverage/integrity, per-EXPRESSED-class
  mutation locality (target gene changes, zero unintended gene changes),
  compile→artifact→project round-trip, pre-execution rejection of invalid
  mutations (`validate_structure`, `AwaitingSurfaceIntactInvariant`),
  evidence per assessment, tamper-evident ledger anchoring, and
  determinism (same ISR + mutation + seed → same semantic candidate).

### 8.4 Next

R2.10.2 adds the MISSING primitives; R2.10.3 builds the gene-level mutation
model on the per-gene addressing proven here.

---

## 8b. R2.10.2 — ISR primitive design & dependency ordering (contract suite)

**Status:** EXECUTED · design-and-contract slice (no schema changes — primitives land in R2.10.3+)
**ADR:** `docs/adr/adr-r2-10-2-primitive-contract.md`
**Contract content hash:** `f7b8901b…` (chain-anchored as `PRIMITIVE_CONTRACT` ledger event)
**Full hermetic suite:** 1784 passed, 2 skipped, 7 Docker-gated deselected (189.87s)
**New tests:** 23 (`tests/test_r29_10_2_primitive_contract.py`)

Five artifacts, all attested:

**1. Primitive specification** — all ten MISSING capabilities fully specified
(meaning / ownership / dependencies / constraints / mutation / validation /
compiler projection / evidence projection / lineage requirements / type
signature) in `tiannara/application/evolution/primitive_contract.py`.

**2. Dependency graph — derived mechanically** (structural / mutation /
validation / projection edges), asserted acyclic, topologically sorted:

```
behavior_temporal_semantics → business_capabilities → data_migrations
  → reliability_resilience → architecture_boundaries
  → requirements_acceptance_traceability → deployment_rollout_rollback
  → testing_anchoring → documentation → evolution_objectives_protected_regions
```

The derived graph **refutes** the sketch's "requirements first": capability
declarations precede traceability (trace links target capabilities);
requirement nodes arrive with R2.10.4's top half. Objectives/protected regions
correctly sort last (they protect genes that must first exist).

**3. ISR extension contract** — six rules: projection (Option A), probe rule
(new gene ⇒ new audit probe + `gene_index` entries), locality rule (EXPRESSED
⇒ R2.10.1 mutation-locality proof), tech-agnostic rule (lint gate), 
compatibility rule, readiness rule.

**4. Compatibility contract — proven.** Old ISR ⇒ same semantic hash ⇒ same
artifact (`async_resolution_module` byte-identical) ⇒ same evolution behavior
(invariants unchanged); Phase-28 gates 13/13 green.

**5. Evolution-readiness matrix** — every primitive declares completion
criteria for all eight stages; `EXPRESSED` is gated on mutation locality.

### Option A migration (executed with before/after gates)

`canonical_form` now omits empty carriers (None / "" / [] / () / {}) — the
projection rule every future primitive inherits. Empty optional primitives are
identity-neutral; non-empty ones are hash-sensitive (change-detection
preserved). R2.10.1 matrix re-attested post-migration: same 2/18/0/10 split,
new matrix hash `317b62a8…`. Booleans/zero/non-empty strings remain meaningful.

### Technology-agnostic lint (mechanical, not by review)

`assert_technology_agnostic` gates every primitive specification against
`TECHNOLOGY_COUPLING_TERMS` (frameworks, datastores, messaging,
infrastructure, security mechanisms, observability vendors). `rollout_rollback`
and `data_migrations` express *semantics* — Kubernetes/Alembic realization
stays in compiler backends.

### R2.10.3 entry

Primitives implement in the derived order, each gated by the extension
contract + readiness targets, with the audit matrix re-attested after every
landing; the 18 PARTIAL capabilities remain R2.10.3/4 gene-level work.

---

## 8c. R2.10.3-A — behavior_temporal_semantics (first primitive landing)

The proving run: the protocol's first use on a gene surface already
EXPRESSED. The primitive landed end-to-end through the eleven-gate protocol
(`PRIMITIVE_GATE` in `tiannara/application/evolution/primitive_gate.py`),
mechanized as a single parameterized harness every future primitive reuses.

**Construct.** `constitutional_architecture/isr/semantics/temporal.py`:
`TemporalConstraint(constraint_id, kind, target_ref, duration_ms,
reference_ref)` with `TemporalConstraintKind` (TRANSITION_DEADLINE /
STATE_MIN_DURATION / EVENT_ORDERING). Timing INTENT on behavior — duration,
ordering, deadline; never timer mechanism (no asyncio.sleep / scheduler /
liveness probe). Carrier: `Module.temporal_constraints` — constraints
REFERENCE behavior genes by id and never alter them, so a transition can be
awaited AND carry a deadline, and mutating the deadline leaves the
await-surface and transition genes byte-identical (locality proven).

**Boundary with behavior_await_surface.** `behavior_await_surface` is the
structural async surface (which transitions await); `behavior_temporal_semantics`
is timing intent (deadlines, minimum durations, ordering windows). They
compose; the temporal constraint never changes await structure.

**Gates (all green).** Representation / canonicalization (empty carrier
identity-neutral — recipe `isr_hash` unchanged `317b62a8…`) / semantic
identity (add→hash moves, edit→hash moves, remove→hash restores) / validation
(negative duration and missing ordering reference rejected at construction;
dangling targets and references rejected pre-execution by
`ISR.validate_structure()`) / locality (MutationLocalityProbe: only the
temporal gene changes) / projection (`project_temporal_semantics` —
backend-independent semantic artifact, deterministic, no coupling terms) /
compilation (`async_resolution_module` byte-identical with the temporal gene
present) / evidence (`project_temporal_evidence`) / lineage (MEASUREMENT
events attribute each mutation with before/after hashes, chain-anchored) /
reproducibility (same ISR + seed ⇒ same candidates) / audit.

**Audit gate — exactly one row moved.** `behavior_temporal_semantics`:
MISSING → EXPRESSED; the other 29 rows untouched. Re-attested matrix:
**3 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 9 MISSING**, matrix content hash
`d2aa03e7119d510d293adcd38b7198ab…` (recipe isr_hash unchanged — Option A).

**Compile surface discipline.** The temporal gene compiles into the semantic
projection artifact; no backend lowers it yet, and no backend may INFER
timing the ISR did not declare. If a backend later needs timing it cannot
derive from the ISR, that is an ISR capability gap, not permission to invent
it in the backend.

---

## 8d. R2.10.3-B — business_capabilities (first-class semantic genes)

The primitive that matters most for the behavioral → architectural
transition. The design hinges on **reference-by-identity**: a capability
references implementation by identity, never by content — so its identity
does not change when a referenced workflow evolves, and it can anchor
architectural replacement ("can I replace the architecture implementing
this capability?" ≠ "can I mutate this workflow?").

**Construct.** `constitutional_architecture/isr/semantics/capability.py`:
`BusinessCapability(capability_id, intent, behavior_refs, interface_refs,
constraint_refs, requirement_refs)`. First-class, system-level carrier
`System.business_capabilities` (capabilities are cross-cutting: they may
reference genes spanning modules). Explicitly NOT an alias for
Workflow/Module — the dependency is `BusinessCapability → references
behaviors/interfaces/constraints → implementation projection`.
`requirement_refs` is reserved and carried empty until
requirements_acceptance_traceability lands (derived order: capabilities
precede traceability); its reference integrity is NOT checked yet.

**Gates (all green).** Eleven-gate protocol reused via the same
parameterized harness (representation / canonicalization — empty carrier
identity-neutral, recipe `isr_hash` unchanged `317b62a8…` / semantic
identity — add→hash moves, intent-change→hash moves, remove→hash restores /
validation — empty id/intent rejected at construction, duplicate ids and
dangling behavior/interface/constraint references rejected pre-execution /
locality / projection (`project_business_capabilities` — intent + reference
identities, no coupling terms) / compilation — `async_resolution_module`
byte-identical / evidence / lineage — MEASUREMENT attribution with
before/after hashes / reproducibility / audit).

**Capability-specific proofs (the substance of the landing):**
* **Non-inference** — identical workflows with different declared
  capabilities produce different capability genes (identity is declared,
  not derived from structure); equivalent declarations over differently
  structured implementations keep the same capability gene (identity is
  semantic, not implementation-derived).
* **Mutation locality** — adding a capability leaves every pre-existing
  gene byte-identical; respecifying intent moves only the capability gene.
* **Reference-by-identity stability** — the referenced behavior gene can
  evolve (content changes) while the capability definition stays
  byte-identical. This is the proof that the platform now has a semantic
  unit it can re-architect around.
* **Reference integrity** — dangling references die pre-execution.

**Audit gate — exactly one row moved.** `business_capabilities`:
MISSING → EXPRESSED; the other 29 rows untouched (asserted as a mechanical
delta vs the 3/18/0/9 pre-landing matrix). Re-attested matrix:
**4 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 8 MISSING**, matrix content hash
`28646fcdb57eee25e6f3dbd2e5bbce3a…` (recipe isr_hash unchanged — Option A).
If any gate had failed — especially locality or non-inference — the row
would have stayed PARTIAL rather than weakening the classification.

---

## 9. Next phase boundary

**R2.10 — Production software generation**, sequenced (order is mandatory):

```
R2.10.1  ISR capability/expressivity audit        ← executed
R2.10.2  Missing ISR primitives (the 10 MISSING rows above)  ← contract suite + Option A migration
R2.10.3  Primitive roots, in derived order         ← A behavior_temporal_semantics (3/18/0/9) + B business_capabilities (4/18/0/8) landed; C data_migrations, D reliability_resilience next
R2.10.4  Architectural subgraph mutation — includes the Requirement Graph
         → ISR construction (the unbuilt top half), explicitly sequenced, not deferred
R2.10.5  Safe structural crossover (chromosome families/genes: Architecture,
         Persistence, Infrastructure, Security, Messaging, Observability,
         Testing, Deployment, Governance, Performance, Reliability)
R2.10.6  Multi-objective architectural evolution
R2.10.7  Architecture candidate competition
R2.10.8  Architectural certification
```

R2.10 inherits the three-identity model with `content_hash` already semantic
(Phase-28 identity migration executed), so cross-run reproducibility is
structural, not patched. Every recombinant must preserve dependency
acyclicity, interface compatibility, and boundary integrity, and traverse the
R2.8 anti-gaming boundary.