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

## 8e. R2.10.3-C — data_migrations (semantic intent, never mechanism)

The highest-risk primitive: migrations are the easiest place for the
semantic layer to accidentally become a database compiler. The boundary
held: **the ISR declares data-evolution intent and invariants; physical
realization is a compiler-backend concern.**

**Construct.** `constitutional_architecture/isr/semantics/migration.py`:
`DataMigrationIntent(migration_id, source_schema_ref, target_schema_ref,
compatibility_policy, preservation_refs, depends_on, rollback_required,
rollback_target_ref, rollback_invariants, postconditions)`. Carrier
`Module.data_migrations` (co-located with the entities it evolves).
Semantic dimensions:
* **Schema identity** — source/target refs resolve to `Module.entities`
  (the data-model genes); no SQL, no ORM, no engine. A dedicated schema
  construct is a noted follow-up if entity-level granularity ever
  suffices no longer.
* **Compatibility INTENT** — `CompatibilityPolicy` (BACKWARD / FORWARD /
  BIDIRECTIONAL / BREAKING / CUSTOM) declares the goal; the enum is never
  the policy. The satisfaction-checker is deliberately NOT built in —
  that is future evaluation, and wiring it in now would couple the
  primitive to an implementation of compatibility checking. CUSTOM
  requires declared postconditions.
* **Preservation** — reference-based (`preservation_refs` = entity ids),
  never implementation-derived.
* **Ordering** — `depends_on` is an explicit dependency graph; dangling
  dependencies and CIRCULAR graphs are rejected pre-execution (a cycle
  makes ordering meaningless) — the R2.10.2 graph discipline applied
  inside a primitive.
* **Rollback** — `rollback_required` / `rollback_target_ref` /
  `rollback_invariants` and NO command field, structurally: there is
  nowhere to put a rollback command. `rollback_target_ref` must be the
  source schema.
* **Validation** — `postconditions` declare what success requires
  (target schema valid, preserved entities, compatibility satisfied,
  rollback available) — future Evolution Engine evaluation inputs.

**The dangerous boundary — two guards.** (1) A field-name test over the
dataclass: no `command`/`script`/`sql`/`statement` field can exist.
(2) `MIGRATION_MECHANISM_TERMS` lint (`alembic`, `ecto`, `prisma`,
`flyway`, `liquibase`, `migration_command`, `rollback_command`,
`orm_model`, `ddl`, `dml`, …) gates the canonical semantic form —
`assert_migration_technology_agnostic` fails the primitive if mechanism
leaks in. No migration primitive may cause the ISR to acquire an
implementation-specific execution mechanism.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carrier identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` / semantic identity — add→hash moves,
policy-change→hash moves, remove→hash restores / validation /
locality — adding a migration touches no behavior/capability/temporal/
entity gene; policy change moves only the migration gene / projection —
`project_data_migrations`, semantics only / compilation —
`async_resolution_module` byte-identical / evidence / lineage —
MEASUREMENT attribution with before/after hashes / reproducibility /
audit).

**Non-inference proven both directions.** Different declared policies over
identical data models → different migration genes; equivalent declarations
over differently structured data models → the same migration gene. The
migration primitive is not an implementation fingerprint.

**Audit gate — exactly one row moved** (with the corrected pre-landing
matrix 4/18/0/8, per the R2.10.3-B delta correction): `data_migrations`:
MISSING → EXPRESSED, asserted mechanically as `moved_rows ==
{"data_migrations": ("MISSING", "EXPRESSED")}`. Re-attested matrix:
**5 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 7 MISSING**, matrix content
hash `e6fbdd1f2792584314bb2b2063cf03d2…` (recipe isr_hash unchanged —
Option A, third use).

The compatibility/preservation/ordering/rollback semantics are the
foundation R2.10.3-D (`reliability_resilience`) and R2.10.3-E
(`architecture_boundaries`) build on.

---

## 8f. R2.10.3-D — reliability_resilience (required behavior under failure)

The strictest boundary yet. Reliability is the primitive most prone to
silently becoming an infrastructure specification, because resilience is
culturally expressed as patterns (retry, circuit breaker, supervisor)
rather than as required behavior. The primitive says **what must remain
true when the system encounters failure** — and is STRUCTURALLY incapable
of saying **how a technology achieves it**. The ISR declares the contract;
a backend earns the right to choose the mechanism.

**Construct.** `constitutional_architecture/isr/semantics/reliability.py`:
`ReliabilityRequirement(requirement_id, target_refs, failure_modes,
recovery_objectives, degradation_policy, preservation_invariants,
dependency_constraints)` with `FailureMode` (WHAT fails, never how it is
handled: TRANSIENT/PERMANENT_DEPENDENCY_FAILURE, RESOURCE_EXHAUSTION,
PARTIAL_CAPACITY_LOSS, DATA_INTEGRITY_VIOLATION, CASCADE_FAILURE),
`RecoveryBehavior` (WHAT must happen: EVENTUAL_RECOVERY, IMMEDIATE_FAILOVER,
GRACEFUL_DEGRADATION, CONTROLLED_SHUTDOWN), `DegradationPolicy` (acceptable
service STATE: NO_DEGRADATION, PARTIAL_SERVICE, READ_ONLY_SERVICE,
DEGRADED_THROUGHPUT), `RecoveryObjective` (behavior + semantic deadline +
data-loss tolerance). Carrier `System.reliability_requirements` —
system-level, because a requirement can protect identities spanning
modules. Targets resolve against business capabilities (R2.10.3-B),
modules, and services — explicit ISR identities, never inferred modules.

**The core distinction, made structural — two guards.** (1) A field-name
test over the dataclass: no `retry`/`backoff`/`replica`/`restart`/`probe`/
`queue`/`circuit` field can exist — the construct has NOWHERE to put a
mechanism. (2) `RELIABILITY_MECHANISM_TERMS` lint (kubernetes, k8s, docker,
systemd, supervisor, restart_policy, retry_count, max_retries, backoff,
exponential_backoff, circuit_breaker, bulkhead, replica_count,
replication_config, failover_config, liveness_probe, readiness_probe,
queue_name, database_replica) gates the canonical semantic form. The terms
are chosen to collide with *mechanisms*, never with *semantic behaviors* —
the asymmetry is the point and is itself a test: `IMMEDIATE_FAILOVER` (a
behavior) passes the lint while `failover_config` (a mechanism) fails it;
`EVENTUAL_RECOVERY` passes while `retry_count` fails.

**Compatibility-as-intent precedent, sharpened.** `retry_count = 3` is
implementation drift; the semantic form is `failure_mode =
TRANSIENT_DEPENDENCY_FAILURE`, `required_behavior = EVENTUAL_RECOVERY`,
`recovery_objective = max_recovery_duration_ms(5000)`. A backend may then
realize EVENTUAL_RECOVERY via retry, queue replay, supervisor restart, or
replica failover — **provided the declared semantic contract is satisfied**.
The mechanism is the backend's choice; the contract is the ISR's.

**Temporal composition — disjoint genes, shared duration semantics.** The
recovery deadline uses the same semantic-duration representation as
temporal's `duration_ms`; adding a requirement with a 5000ms deadline
leaves the temporal genes byte-identical (asserted by gene hash). Neither
primitive carries timer machinery; the full failure → degraded → recovery
deadline → restored sequence remains expressible via temporal
EVENT_ORDERING when it is needed.

**Structural validation (pre-execution).** Rejects: empty identifiers,
dangling target refs, recovery objectives addressing failure modes the
requirement never declared, contradictory recovery (the same failure mode
demanding two different required behaviors), duplicate requirement ids.
Recovery deadlines must be non-negative at construction.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carrier identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` / semantic identity — add→hash moves,
degradation-change→hash moves, remove→hash restores / validation /
locality — adding a requirement touches no behavior/capability/migration/
temporal/entity gene; changing a recovery objective moves only the
reliability gene / projection — `project_reliability_requirements`,
semantics only, zero coupling terms, zero mechanism terms / compilation —
`async_resolution_module` byte-identical / evidence / lineage —
MEASUREMENT attribution with before/after hashes / reproducibility /
audit).

**Non-inference proven both directions.** Different resilience declarations
over identical implementations → different reliability genes (CASCADE_FAILURE
vs TRANSIENT_DEPENDENCY_FAILURE over the same protected targets); equivalent
declarations over differently structured implementations → the same
reliability gene. Failure-mode identity: distinct modes never collapse into
the same canonical form. The reliability gene is a declared contract, never
an implementation fingerprint.

**Audit gate — exactly one row moved** (pre-landing matrix 5/18/0/7, after
R2.10.3-C): `reliability_resilience`: MISSING → EXPRESSED, asserted
mechanically as `moved_rows == {"reliability_resilience": ("MISSING",
"EXPRESSED")}`. Re-attested matrix: **6 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 6 MISSING**, matrix content hash
`8e31b0164421c5c41bd15a156d0fadef…` (recipe isr_hash unchanged — Option A,
fourth use).

**The architectural warning, enforced as a gate.** If `max_retries`,
`backoff_strategy`, `replica_count`, `restart_policy`, `kubernetes_probe`,
`queue_name`, or `database_replica` ever appears in the reliability gene,
stop and move those concerns to a compiler/backend projection. The ISR says
what must remain true under failure; a backend earns the right to choose
how. Once green, the semantic contract it establishes — required behavior
under failure — becomes a first-class input the Evolution Engine can select
on: evolving *reliable* architecture rather than merely generating it.

The remaining MISSING (6): architecture_boundaries, deployment_rollout_rollback,
requirements_acceptance_traceability, documentation, testing_anchoring,
evolution_objectives_protected_regions.

---

## 8g. R2.10.3-E — architecture_boundaries (constraint on relationships)

A boundary is a SEMANTIC constraint on relationships between genes — NOT a
module, a service, or a deployment unit. It declares what may or may not
cross it. A backend may realize it as a module / package / process /
service / network boundary / repository / container, but NONE of those
realizations is part of the primitive.

**Construct.** `constitutional_architecture/isr/semantics/boundary.py`:
`ArchitecturalBoundary(boundary_id, member_refs, forbidden_dependency_refs,
protected, crossing_invariants)` — deliberately the MINIMUM carrier R2.8.6
already proved. `member_refs` + `forbidden_dependency_refs` + `protected` is
exactly the semantic content the architectural-integrity gate enforced on
the FSM substrate, now elevated into the constitutional ISR as a
first-class gene. `allowed_crossings` and richer dependency-direction
semantics are future extensions, added only when a concrete substrate needs
them. Carrier `System.architectural_boundaries` — system-level, since
boundaries span the architecture. References resolve against the R2.9.7
ArchitecturalSkeleton identity space (modules, services, workflows,
interfaces, policies, entities) plus business capabilities.

**The migration, explicit.** Architecture protection moves from anti-gaming
infrastructure into the constitutional ISR:

```
R2.8.6  architectural invariant enforcement (substrate-specific)
  → R2.10.3-E  first-class architectural boundary gene (general ISR)
    → future substrates: component / requirement / service / deployment graphs
```

Two scope boundaries held: (1) E does NOT wire the R2.8.6 enforcement
machinery to read from the gene — that is a follow-up integration, and
doing both in one slice would blur the "gene lands, then enforcement
consumes it" sequencing; (2) E does NOT add capability→boundary or
reliability→boundary references — those compositions belong to B and D once
the boundary gene exists to reference. E only makes the boundary
referenceable.

**Protected-boundary preservation, elevated into the operator.** Removal of
a `protected` boundary raises `ConstitutionalViolation` — the R2.8.6
silent-removal rule, upheld at the mutation boundary by `BoundaryOperator`
itself. Unprotected removal restores the exact prior content hash.

**Realization-neutrality — the double guard.** (1) Field-name test: no
`package`/`container`/`process`/`pod`/`network`/`deploy` field can exist —
nowhere to put a realization. (2) `BOUNDARY_MECHANISM_TERMS` lint (package,
namespace, container, pod, process_id, service_mesh, network_zone, vpc,
subnet, region, deployment_unit, kubernetes, docker) gates the canonical
semantic form. The lint rejects realization TECHNOLOGY terms, never
references to ISR genes — `member_refs` referencing `Module`/capability
identities passes (proven by test).

**The substance of the slice — reference-by-identity.** The boundary gene
stays byte-identical while its members' implementations evolve; a boundary
mutation moves only the boundary gene. Architecture is therefore an
independently evolvable dimension — the precondition for the Evolution
Engine to one day ask "re-architect this boundary" rather than only
"mutate this workflow".

**Non-inference proven both directions.** Different declared memberships
over identical module structures → different boundary genes; equivalent
declarations over differently structured implementations → the same
boundary gene.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carrier identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` / semantic identity — add→hash moves,
forbidden-change→hash moves, remove→hash restores / validation /
locality — adding a boundary touches no behavior/capability/migration/
temporal/reliability/entity gene / projection —
`project_architectural_boundaries`, semantics only, zero coupling terms,
zero realization terms / compilation — `async_resolution_module`
byte-identical / evidence / lineage — MEASUREMENT attribution with
before/after hashes / reproducibility — deterministic generation incl.
single-module fallback to capability-enclosing boundaries / audit).

**Audit gate — exactly one row moved** (pre-landing matrix 6/18/0/6, after
R2.10.3-D): `architecture_boundaries`: MISSING → EXPRESSED, asserted
mechanically as `moved_rows == {"architecture_boundaries": ("MISSING",
"EXPRESSED")}`. Re-attested matrix: **7 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 5 MISSING**, matrix content hash
`140f0e41d51409111afdfef340d70d75…` (recipe isr_hash unchanged — Option A,
fifth use).

Remaining MISSING (5): deployment_rollout_rollback,
requirements_acceptance_traceability, documentation, testing_anchoring,
evolution_objectives_protected_regions.

---

## 8h. R2.10.3-F — requirements_acceptance_traceability (obligations, not tasks)

The ISR declares what the system must accomplish (`Requirement`) and what
must be demonstrably true for acceptance (`AcceptanceCriterion`). The
acceptance criterion is the deliberately calibrated MIDDLE LAYER between
"too weak to evaluate" (`statement = "system is reliable"` — nothing
mechanically determinable) and "too coupled to a testing technology"
(`pytest_test = "test_reliability.py"` — the ISR becomes a test manifest).
It carries an obligation + a semantic KIND + subjects: enough for an
evaluation substrate to dispatch on, no mechanism for how.

**Construct.** `constitutional_architecture/isr/semantics/requirement.py`:
`Requirement(requirement_id, statement, target_refs, acceptance_refs,
constraint_refs)` — `target_refs` (BusinessCapability ids) is REQUIRED: an
obligation must bind to something explicit. `AcceptanceCriterion(criterion_id,
obligation, kind, subject_refs)` with `ObligationKind` (ORDERING, PRESENCE,
ABSENCE, INVARIANT, THRESHOLD). NO `is_satisfied()`, no verdict, no score,
no test-reference field exists anywhere in the primitive (structural tests
pin that). The criterion is the thing evidence will later be bound TO (the
testing/anchoring primitive H), never the thing that evaluates. Two
carriers: `System.requirements` + `System.acceptance_criteria`, both empty
identity-neutral (Option A).

**The reservation ACTIVATED, without touching B.** Since R2.10.3-B,
`BusinessCapability.requirement_refs` was carried empty and unvalidated.
F introduces `Requirement` and makes those refs resolvable against
`System.requirements` — `validate_system_capability_constraints` and the
new `validate_system_requirement_constraints` both enforce it, with the
`BusinessCapability` construct itself untouched. The R2.10.2 derived
dependency graph held: a capability with empty `requirement_refs` is
byte-identical before and after activation (proven by test).

**The substance of the slice — reference-by-identity asymmetry.** Changing
a requirement's statement/criteria moves the REQUIREMENT gene but NOT the
capability that references it by id; adding a `requirement_ref` to a
capability is an EXPLICITLY DECLARED cross-reference and DOES move the
capability gene. Both directions proven mechanically. Requirements are
declared, never inferred from behavior or implementation structure.

**Acceptance neutrality — the double guard.** (1) Field-name test: no
`test`/`assert`/`runner`/`file`/`suite`/`verdict`/`satisfied`/`score`
field can exist — nowhere to put a verdict. (2) `REQUIREMENT_MECHANISM_TERMS`
lint (pytest, junit, cypress, selenium, jest, mocha, testng, test_file,
test_name, test_case, assertion_library, http_request, sql_query,
browser_action, grpc_call) gates the canonical semantic form: the lint
rejects test-mechanism terms, never semantic obligations —
"Order cancellation must become effective before settlement" passes,
"run test_cancel_order.py via pytest" fails (proven by test).

**Operator.** `tiannara/application/evolution/requirement_mutation.py`
(`RequirementOperator`, operator_id `requirement`, evolution_id
`r2.10.3-f`): add/remove_requirement, set_statement (the identity
asymmetry op), add_criterion, assign_criterion, link_capability (the
declared cross-reference), deterministic generate. Every mutation is
attributed as a ledger MEASUREMENT with before/after hashes.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carriers identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` — sixth Option A use / semantic identity — add→hash
moves, respecify→hash moves, remove→hash restores / validation — dangling
target/acceptance/constraint/subject refs + duplicate ids rejected
pre-execution, capability `requirement_refs` resolve / locality — adding a
requirement touches no behavior/capability/migration/temporal/reliability/
boundary/entity gene / projection — `project_requirements` +
`project_acceptance_criteria`, semantics only, zero coupling terms, zero
mechanism terms / compilation — `async_resolution_module` byte-identical /
evidence / lineage — MEASUREMENT attribution with before/after hashes /
reproducibility / audit).

**Audit gate — exactly one row moved** (pre-landing matrix 7/18/0/5, after
R2.10.3-E): `requirements_acceptance_traceability`: MISSING → EXPRESSED,
asserted mechanically as `moved_rows == {"requirements_acceptance_traceability":
("MISSING", "EXPRESSED")}`. Re-attested matrix: **8 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 4 MISSING**, recipe isr_hash unchanged `317b62a8…` — Option A,
sixth use.

Remaining MISSING (4): deployment_rollout_rollback, documentation,
testing_anchoring, evolution_objectives_protected_regions.

---

## 8i. R2.10.3-G — deployment_rollout_rollback (intent and lifecycle guarantees)

Deployment is where the gravity toward infrastructure specification is
strongest — the entire culture expresses deployment as Kubernetes manifests,
replica counts, and CI/CD pipelines. G holds TWO distinct boundaries because
they fail differently:

1. **NO realization technology in the gene.** The construct is STRUCTURALLY
   incapable of carrying one (field-name test: nowhere to put `replica_count`,
   `pod_spec`, `container_image`, `manifest`, `pipeline`, `command`,
   `script`) AND the `DEPLOYMENT_MECHANISM_TERMS` lint gates the canonical
   semantic form — orchestration platforms (kubernetes, k8s, docker, ecs,
   ec2, lambda, nomad, mesos), IaC tooling (terraform, pulumi,
   cloudformation, ansible, helm, kubectl), cloud providers (aws, gcp,
   azure), realization mechanics (replica_count, pod_spec, container_image,
   deployment_manifest, ingress, load_balancer_config, service_mesh), CI/CD
   tooling (jenkins, github_actions, gitlab_ci, circleci, argo). The lint
   asymmetry is proven: CANARY / BLUE_GREEN are SEMANTIC strategies and
   PASS; kubernetes and replica_count FAIL.

2. **NO backward leak into architecture.** Deployment references
   architecture (targets = capabilities/modules) by identity; a deployment
   mutation must never propagate into the boundary genes it references. The
   G-specific proof: changing the rollout strategy CANARY → BLUE_GREEN moves
   only the deployment gene — every boundary gene stays byte-identical.

**Construct.** `constitutional_architecture/isr/semantics/deployment.py`:
`DeploymentIntent(deployment_id, target_refs, rollout_strategy,
rollout_constraints, health_requirements, rollback_required,
rollback_target_ref, rollback_invariants, preservation_requirements)` with
`RolloutStrategy` (IMMEDIATE, CANARY, BLUE_GREEN, PROGRESSIVE) — semantic
rollout behaviors, WHAT the rollout accomplishes, never HOW. A backend may
realize CANARY via K8s, ECS, or manual traffic shifting, provided the
declared semantic holds.

**CARRIER DECISION (documented, not ambiguous).** `System.deployment_intents`
is a NEW carrier alongside the pre-existing `System.deployment` environment
placeholder — two DIFFERENT semantic layers: `System.deployment` describes
the ENVIRONMENT (tier, scaling bounds, networking, monitoring paths,
storage, secrets — static attributes of where the system runs);
`System.deployment_intents` declares the LIFECYCLE contract (WHAT a change
must accomplish, under what conditions, WHAT must remain preserved, WHEN
rollback is required). Folding intent into the environment placeholder
would mix "what the environment is" with "how a change must proceed". Both
carriers are empty identity-neutral (Option A).

**Rollback reuses C's rollback-as-invariant pattern.** Rollback is a
contract about what must be restored, never a command: no `rollback_command`,
no scripts, no kubectl. `rollback_target_ref` must name one of the intent's
OWN targets (C's rule: rollback restores a member of the operation's own
refs) — validated pre-execution, along with duplicate ids and dangling
target refs (resolving against capabilities + modules, E's member-ref
identity space).

**The substance of the slice — deployment as an independently evolvable
lifecycle dimension.** Forward: a deployed target's implementation evolves
while the deployment gene stays byte-identical. Backward: a deployment
policy change moves only the deployment gene, never the boundary genes it
references. Together they prove deployment composes with architecture by
reference only — a lifecycle concern over architecture, never a trojan
horse for re-encoding it.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carrier identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` — seventh Option A use / semantic identity —
add→hash moves, strategy-change→hash moves, remove→hash restores /
validation / locality — adding an intent touches no behavior/capability/
migration/temporal/reliability/boundary/requirement/entity gene /
projection — `project_deployment_intents`, semantics only, zero coupling
terms, zero realization terms / compilation — `async_resolution_module`
byte-identical / evidence / lineage — MEASUREMENT attribution with
before/after hashes / reproducibility / audit).

**Audit gate — exactly one row moved** (pre-landing matrix 8/18/0/4, after
R2.10.3-F): `deployment_rollout_rollback`: MISSING → EXPRESSED, asserted
mechanically as `moved_rows == {"deployment_rollout_rollback": ("MISSING",
"EXPRESSED")}`. Re-attested matrix: **9 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 3 MISSING**, recipe isr_hash unchanged `317b62a8…` — Option
A, seventh use.

Remaining MISSING (3): documentation, testing_anchoring,
evolution_objectives_protected_regions.

---

## 8j. R2.10.3-H — testing_anchoring (the declaration side of the ISR↔evidence loop)

H closes the loop between the ISR's semantic obligations and the evaluation
boundary WITHOUT becoming a test-generation primitive. The inversion that
lets the testing layer define the software's meaning is the failure mode H
exists to avoid; the principle held since R2.8: **the ISR declares what
evidence must establish; the evaluation system determines how that evidence
is produced.** H is the declaration side, full stop — structurally incapable
of the dangerous half.

**Scope holds (asserted).** (1) H does NOT evaluate: no `is_satisfied`, no
verdict, no score, no execution — field-name test proves there is nowhere to
put them. (2) H does NOT wire obligation→anchor→evidence into the live
evaluation loop: `obligation_refs` merely RESOLVE against F's
`AcceptanceCriterion` ids (the F→H edge) without editing F — H's validator
rejects dangling obligation refs pre-execution; BINDING anchors to produced
evidence is the evaluation system's follow-up, exactly where R2.8.14 ANCHOR
events already live.

**Construct.** `constitutional_architecture/isr/semantics/testing_anchor.py`:
`TestingAnchor(anchor_id, subject_refs, obligation_refs,
evidence_requirements, protection_policy, authority)` — `anchor_id` +
`subject_refs` required. `ProtectionPolicy` (PROTECTED / EVOLVABLE) reuses
R2.8.7's protected-evaluation-surface semantics generalized into the ISR;
`AnchorAuthority` (AUTHORITATIVE / DERIVED) distinguishes fixed reference
anchors from derived ones. `TESTING_MECHANISM_TERMS` gates the canonical
semantic form (pytest, junit, cypress, selenium, jest, mocha, testng, rspec,
test_file, test_function, test_name, test_case, fixture, conftest,
pytest_marker, assert_function, mock_object, docker_command, shell_command,
ci_step, runner_config). Asymmetry proven: "ORDERING must be demonstrated
before authorization" PASSES; "test_file test_cancel_order.py via pytest"
FAILS.

**Subject / obligation identity space.** `subject_refs` resolve against
behaviors (workflow ids), capabilities, and requirement ids — reference by
identity, exactly E's member-ref discipline. `obligation_refs` resolve
against F's `AcceptanceCriterion` ids. H adds NOTHING to F: the criterion
construct carries no `anchor_refs`/`testing_refs` (asserted) — the edge
activates by resolution only.

**The R2.8 connection — ONE protection mechanism across primitives.**
PROTECTED anchor removal/modification raises `ConstitutionalViolation` — the
SAME violation E's `BoundaryOperator` raises for protected boundaries. Not a
parallel security model: the governance kernel already understands this
violation; a protected anchor is as untouchable as a protected boundary.
Elevation EVOLVABLE→PROTECTED is authorized; downgrade PROTECTED→EVOLVABLE
is a violation.

**The substance of the slice — three proofs.** (1) Changing testing intent
(respecify) moves ONLY the testing gene — every subject/behavior gene stays
byte-identical (the full-locality proof). (2) A subject's implementation
evolves while the anchor holds — reference-by-identity stability. (3) A
PROTECTED anchor's removal/modification is constitutionally rejected;
EVOLVABLE removal restores the exact prior hash.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carrier identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` — eighth Option A use / semantic identity / validation —
duplicate ids, dangling subject + obligation refs rejected pre-execution /
locality / projection — `project_testing_anchors`, semantics only, zero
TECHNOLOGY_COUPLING_TERMS, zero TESTING_MECHANISM_TERMS / compilation —
`async_resolution_module` byte-identical with anchors present / evidence /
lineage — MEASUREMENT attribution with before/after hashes / reproducibility
/ audit).

**Audit gate — exactly one row moved** (pre-landing matrix 9/18/0/3, after
R2.10.3-G): `testing_anchoring`: MISSING → EXPRESSED, asserted mechanically
as `moved_rows == {"testing_anchoring": ("MISSING", "EXPRESSED")}`.
Re-attested matrix: **10 EXPRESSED / 18 PARTIAL / 0 PROJECTED /
2 MISSING**, recipe isr_hash unchanged `317b62a8…` — Option A, eighth use.

Remaining MISSING (2): documentation, evolution_objectives_protected_regions.

---

## 8k. R2.10.3-I — documentation (intent, never artifact)

Documentation as an ISR-owned SEMANTIC artifact — NOT generated Markdown,
HTML, source comments, or diagrams. A `DocumentationIntent` declares what
must be documented, for whom, and why; the realization (Markdown, HTML, API
docs, diagrams, anything else) is a compiler/backend concern and never part
of this primitive.

**The constraint this slice holds firm on — documentation must NOT become a
second source of truth.** Direction is one-way: **ISR semantics →
documentation intent → realization**, never the reverse. The non-authority
is STRUCTURAL: the construct carries no override/redefine/replace/author/
source-of field — there is no mechanism to author anything but its own
intent. Proven by locality in both directions: changing documentation moves
only the documentation gene (respecify purpose → capability gene
byte-identical); a subject's implementation evolves while the documentation
gene holds (reference-by-identity, exactly like the other primitives).

**Construct.** `constitutional_architecture/isr/semantics/documentation.py`:
`DocumentationIntent(documentation_id, subject_refs, purpose, audience,
obligations)` — five fields, deliberately small. `DocumentationPurpose`
(OPERATIONAL_REFERENCE, ARCHITECTURAL_RATIONALE, API_CONTRACT, ONBOARDING,
COMPLIANCE) and `DocumentationAudience` (OPERATOR, DEVELOPER, ARCHITECT,
SECURITY_AUDITOR, END_USER) are semantic, never formats or channels.
`coverage_refs` collapsed into `subject_refs`; an `evolution_policy` would
only ever have one valid value (derived), because non-authority makes
documentation inherently non-authoritative — both are future extensions if
a concrete substrate needs them.

**Two-layer defense.** Structural exclusion: no format/path/template/
generator field anywhere (field-name test). Semantic lint:
`DOCUMENTATION_MECHANISM_TERMS` (markdown, html, rst, mdx, latex, asciidoc,
template, filepath, file_path, output_path, render_config, docusaurus,
mkdocs, sphinx, javadoc, typedoc, doxygen, gitbook) over the canonical
form. Asymmetry proven: `purpose=OPERATIONAL_REFERENCE, audience=OPERATOR`
PASSES; `obligations=("render markdown via mkdocs",)` FAILS.

**Subject identity space.** `subject_refs` resolve against behaviors
(workflow ids), capabilities, requirements, modules, and boundaries — the
documentable genes. Dangling refs and duplicate ids rejected pre-execution.

**No realization hook in the ISR.** The projection emits the semantic
intent only; whichever backend renders Markdown/HTML/diagrams consumes it
downstream. Landing I did NOT add a "render hint" field — that would be the
realization leaking back in, refused.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carrier identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` — ninth Option A use / semantic identity /
validation / locality — adding an intent touches no behavior/capability/
migration/temporal/reliability/boundary/requirement/deployment/anchor gene /
projection — `project_documentation_intents`, semantics only, zero
TECHNOLOGY_COUPLING_TERMS, zero DOCUMENTATION_MECHANISM_TERMS /
compilation — `async_resolution_module` byte-identical with intents present /
evidence / lineage — MEASUREMENT attribution with before/after hashes /
reproducibility / audit).

**Audit gate — exactly one row moved** (pre-landing matrix 10/18/0/2, after
R2.10.3-H): `documentation`: MISSING → EXPRESSED, asserted mechanically as
`moved_rows == {"documentation": ("MISSING", "EXPRESSED")}`.
Re-attested matrix: **11 EXPRESSED / 18 PARTIAL / 0 PROJECTED /
1 MISSING**, recipe isr_hash unchanged `317b62a8…` — Option A, ninth use.

Remaining MISSING (1): evolution_objectives_protected_regions.

---

## 8l. R2.10.3-J — evolution_objectives_protected_regions (the constitutional capstone)

J answers two distinct questions: **what is this evolution allowed to
optimize?** (`EvolutionObjective`) and **what must this evolution never
sacrifice?** (`ProtectedRegion`). An objective may be traded against another
objective; a protected region may NOT be traded away for fitness. The
enforcement boundary is a **FEASIBILITY GATE** — `EvolutionProtectionEvaluator`
removes violating candidates from the feasible search space BEFORE objective
evaluation — never a fitness penalty, which a sufficiently large competing
fitness could overwhelm.

**The three architectural proofs that gate promotion** (all asserted):

1. **No self-authorization.** `ConstitutionalAuthorization` lives in
   `constitutional_architecture/governance/` — OUTSIDE the evolution package,
   which cannot import or construct it (module-boundary AST test, not
   convention). The registry issues chain-anchored authorizations; the
   evaluator receives them as opaque values and verifies the anchor against
   the governance authority. An authorization that was never issued through
   the governance seam does not verify; without a registry no CONSTITUTIONAL
   change can ever be authorized. Ordinary evolution cannot satisfy a
   constitutional authorization: the process being constrained does not
   control the constraint.
2. **No fitness/objective conflation.** No measured-value field exists on the
   objective structurally (`value/score/fitness/measurement/metric/result`
   field-name test). Changing objective weights changes per-objective
   declarations only — the projection can never contain a combined
   weighted-scalar artifact (no-scalarization guard + behavioral test).
   Lexicographic tiers: `ObjectiveTier.CONSTITUTIONAL` (priority 0, subject
   presence is a feasibility condition) vs `OPTIMIZATION` preference (tier
   order by priority, intra-tier preference by weight — weight is never
   scalarization).
3. **No authority duplication between E/H/J.** J protects semantic identities
   by REFERENCE (capabilities, requirements, boundaries, testing anchors,
   reliability requirements, deployment intents, migrations, temporal
   constraints, documentation, behaviors — ten domains) and never re-implements
   E's boundary or H's anchor mechanics. Locality both ways: J's region
   mutations never touch boundary/anchor genes; E/H mutations never touch
   region genes.

**Constructs.**

- `constitutional_architecture/isr/semantics/evolution_policy.py` —
  `EvolutionObjective(objective_id, dimension ×8, direction, tier, priority,
  weight, subject_refs)` = tradeable preference; `ProtectedRegion(region_id,
  subject_refs, protection_kind IMMUTABLE/CONSTITUTIONAL/PRESERVATION,
  invariants)` = non-tradeable constraint; `EvolutionPolicy(objective_refs,
  protected_region_refs, selection_constraints)` = composition. Structural
  guards: PRESERVATION requires ≥1 invariant; only THRESHOLD invariants carry
  a bound; CONSTITUTIONAL objectives are priority 0. `EVOLUTION_MECHANISM_TERMS`
  (optimizer, algorithm, fitness_function, selection_algorithm, mutation_rate,
  population_size, annealing, tournament, roulette, genetic_algorithm, pymoo,
  nsga, reinforcement_learning) over the canonical form — asymmetry proven:
  `maximize reliability` PASSES, `tournament selection with population_size
  100` FAILS.
- `tiannara/application/evolution/evolution_policy_mutation.py` —
  `EvolutionPolicyOperator` (add/remove/respecify objective/region/policy +
  deterministic `generate`), the only operator touching the three J carriers.
- `tiannara/application/evolution/protection.py` — `EvolutionProtectionEvaluator`
  operating ONLY on `EvolutionDiff(added_subjects, removed_subjects,
  changed_subjects, ordering_changes)` — subjects are semantic identity ids
  resolved from the gene index; `affected_subjects` is a projection output,
  not a J-owned primitive. Regions and objectives resolve from the PARENT
  constitution, never from a declaration the candidate could have weakened.
  Preservation invariants reuse F's `ObligationKind` (PRESENCE/ABSENCE/
  INVARIANT/ORDERING/THRESHOLD) — one predicate model across the ISR.
- `constitutional_architecture/governance/constitutional_authorization.py` —
  the governance seam: `ConstitutionalAuthorization` (a REFERENCE to
  authority, never authority itself — `anchor_ref` identifies governance
  evidence rather than duplicating it) + `ConstitutionalAuthorizationRegistry`
  (chain-anchored issuance, membership verification).

**Feasibility semantics.** IMMUTABLE: any touch → INFEASIBLE. CONSTITUTIONAL:
same, unless an external governance authorization covers the change.
PRESERVATION: change permitted iff every invariant holds on the parent →
candidate semantic diff. Constitutional objectives are feasibility gates
themselves: their subjects must remain present in any feasible candidate —
the never-sacrifice guarantee closed at the objective level (a candidate that
removes a constitutional objective's subject is INFEASIBLE even though no
region mentions it). Protection is EXPLICITLY DECLARED, never inferred from
structure/files/tests/config.

**Gates (all green).** Eleven-gate protocol reused (representation /
canonicalization — empty carriers identity-neutral, recipe `isr_hash`
unchanged `317b62a8…` — tenth Option A use / semantic identity /
validation — duplicate ids, dangling subject/policy refs, policies that
govern nothing rejected pre-execution / locality — adding an objective
touches no other gene / projection — `project_evolution_policy`,
per-objective declarations only, no scalar aggregation, zero
TECHNOLOGY_COUPLING_TERMS, zero EVOLUTION_MECHANISM_TERMS / compilation —
`async_resolution_module` byte-identical with policy present / evidence /
lineage — MEASUREMENT attribution with before/after hashes /
reproducibility / audit).

**Audit gate — exactly one row moved** (pre-landing matrix 11/18/0/1, after
R2.10.3-I): `evolution_objectives_protected_regions`: MISSING → EXPRESSED,
asserted mechanically as `moved_rows == {"evolution_objectives_protected_regions": ("MISSING", "EXPRESSED")}`.
Re-attested matrix: **12 EXPRESSED / 18 PARTIAL / 0 PROJECTED /
0 MISSING** — the FINAL R2.10.3 matrix — recipe isr_hash unchanged
`317b62a8…` — Option A, tenth use. R2.10.3 is complete: no MISSING rows
remain.

---

## 8m. R2.10.4 — SemanticEvolutionGate (universal ISR evolution integration)

R2.10.1 proved per-gene identity; R2.10.2/R2.10.3 added the semantic
primitives. R2.10.4 proves they **COMPOSE**: one candidate evolves ≥4
independent genes across distinct domains (capability + reliability +
deployment + temporal) while every integration guarantee holds — and the
negative variants FAIL VISIBLY.

**The gate contract** (`tiannara/application/evolution/semantic_evolution_gate.py`):

1. **Feasibility first.** The J protection projection — resolved from the
   PARENT constitution — runs before any proof and before any objective
   evaluation. An infeasible candidate returns immediately: no proofs, no
   ledger event (source-order + behavioral tests).
2. **≥4 independent genes across ≥4 distinct domains.** `GeneEdit(domain,
   gene_id, new_gene)` + `MultiGeneDelta(delta_id, edits, edited_domains)`.
   A single-gene evolution is not a composition and cannot be substituted
   for it (no single-gene fallback).
3. **Four proofs** (`GateProof(proof_id, held, evidence)`):
   - `locality` — exactly the declared genes moved, nothing else disturbed
     (identity-index hashes, ONE namespace). Negative variant: an
     application layer that silently touches an unrelated gene is DETECTED.
   - `reference_integrity` — the candidate introduces no new dangling
     cross-gene reference (via the identity index). Negative variant: a
     delta that dangles is rejected BY THE GATE, not merely by the
     constructor.
   - `backend_independence` — all ten primitives' mechanism lints aggregate
     on the candidate: the 8 named `assert_*_technology_agnostic` lints +
     capability free-text `intent` scan against the union of all eight term
     sets + temporal by-construction (typed fields). Negative variant: one
     coupled gene among otherwise-clean genes fails the whole composition.
   - `r28_evidence_path` — the gate holds no evaluation machinery of its
     own: AST scan of the gate + protection sources for
     `fitness/score/metric/measurement` identifiers; the protection
     projection is consumed by the R2.8 gate stack.
4. **Ledger binding.** Every feasible evaluation records a chain-anchored
   `MEASUREMENT` event with the canonical edit list (sorted by
   domain/gene_id), seed, proof outcomes, and before/after hashes. Same
   parent + delta + seed → same candidate hash and identical event content
   (event hashes differ only by chain anchoring).

**Shared identity namespace.** `tiannara/application/evolution/
identity_index.py` — `SemanticIdentityIndex` is now THE single resolution
mechanism for all ten protected-identity domains: `path_identities` (the
R2.10.3-J walk, preserved exactly), `genes`/`gene_hashes`/`gene_hash`
((domain, gene_id) → canonical hash, same canonicalization as the ISR
content hash), `replace_gene` (deterministic single-gene replacement,
KeyError for unknown genes = rejection before evaluation),
`resolvable_ids`, `dangling_references`. J's `EvolutionProtectionEvaluator`
now consumes the shared index (the private path-index walk is gone) and
gains multi-region semantics: violations accumulate, the strictest kind
wins, every triggered region is evidenced in `regions_evaluated` — no
region short-circuits another. The rule the R2.10.3-J fail-open fix
established is now structural: identity is resolved through the index;
paths are only a projection artifact — never compare an identity to a path.

**Parent authority (permanent, enforced two ways).** AST proof: the gate
source resolves the policy only as `resolve_evolution_policy(parent_isr)`
— never from the candidate. Behavioral proof: a candidate that strips its
own evolution-policy carriers is still judged under the PARENT's regions
(region_A protects the capability the delta changes → infeasible).
Multi-policy parents merge deterministically (`merged` = union of refs,
first-occurrence order); no policy → a default that governs nothing.

**Matrix.** R2.10.4 adds no carriers and moves no matrix row: the recipe
ISR is byte-identical (`isr_hash` unchanged `317b62a8…` — the **eleventh
Option A use**) and the matrix stays **12 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 0 MISSING**, asserted mechanically.

**Verification.** `tests/test_r29_10_4_semantic_evolution_gate.py` — 14
tests: the 8 acceptance tests (multi-gene preserves unrelated genes /
disturbed gene detected / cross-gene references hold / dangling reference
rejected / projection backend-independent / coupling rejected in
composition / reproducible + ledger verifiable / Option A under
composition) plus parent authority ×2, multi-region strictest-wins,
feasibility-precedes-objectives (both failure paths + source order), the
R2.8 evidence substrate, and deterministic merged-policy resolution.
Full suite: **2109 passed / 10 skipped** (R2.10 suites: 352 passed).

---

## 8n. R2.10.5 — UniversalEvolutionLoop (universal evolutionary search)

R2.9 proved population dynamics on the FSM substrate; R2.10.4 proved the
universal semantic transaction (≥4 independent genes across distinct
domains under one gate). R2.10.5 fuses them: multi-generation search whose
final selected ISR is reconstructable **byte-exactly from the ledger
alone** — replaying only the recorded delta material (each recorded
generation event carries the full canonical content of every edit).

**Locked invariants (before implementation).**

1. `IdentityIndex` stays a **DERIVED PROJECTION** — a frozen dataclass with
   no mutation surface (no `add_`/`remove_`/`replace_`/`set_` methods),
   constructible only through `derive(isr)`. Gene replacement is the
   module-level `identity_index_replace_gene` producing a new ISR version
   (the R2.10.4 `SemanticIdentityIndex` is renamed/refactored to this
   under R2.10.5; gate/protection/tests all consume the new surface).
2. Parent-authoritativeness is **per-step**: each generation is judged by
   that generation's parent constitution, never by rules the candidate
   authored; a governance-authorized policy change may propagate to the
   next generation.

**Machinery** (`tiannara/application/evolution/universal_evolution.py`):

- `UniversalVariationOperator` — a population of 4-domain universal deltas,
  drawn deterministically from `random.Random(seed)`; only domains with a
  declared mutator participate (mechanism, never content).
- `lexicographic_tiers(parent)` — the objective evaluation order: the
  CONSTITUTIONAL presence gates first, then OPTIMIZATION objectives by
  (priority, weight descending, objective_id) — resolved from the PARENT.
- `UniversalSelector` — the profile is a TUPLE (never a scalar) of
  per-objective engagement bits, compared lexicographically with a
  deterministic `delta_id` tie-break.
- `UniversalEvolutionLoop` — per-generation seed `seed + generation`;
  `_apply` seam judged by the gate like any application layer; records
  only selected generations; `_verify_reconstruction` replays the ledger's
  recorded deltas and requires a byte-exact (hash-identical) final ISR
  with an intact identity namespace.
- `rebuild_gene` — the exact inverse of `canonical_form` for the ten
  identity domains (type-directed via `get_type_hints`; `tuple[X, ...]`
  handles the `Ellipsis` arg; `(str, Enum)` canonicalize as their value —
  the projection's str branch catches them before the Enum branch).
- Ledger (`ledger.py`): `record_generation` records MEASUREMENT events
  carrying the full canonical delta content; `recorded_deltas()` is the
  reconstruction input. The ledger never imports the search module
  (duck-typed record).

**Self-governance seam** (`protection.py`): a candidate that weakens its
OWN evolution-policy carriers — carriers removed, subject_refs reduced,
protection kind downgraded, CONSTITUTIONAL objective downgraded — is a
CONSTITUTIONAL violation unless a governance-issued authorization
(`SELF_GOVERNANCE_REF` + `ConstitutionalAuthorizationRegistry` anchor
verification) permits it. Content-only differences that do not reduce the
governance surface (e.g. an invariant bound) are NOT weakening — the fix
for a false positive surfaced by J's `test_preservation_threshold_invariant`
(kind PRESERVATION restored, not CONSTITUTIONAL).

**Acceptance evidence.** `tests/test_r29_10_5_universal_evolution.py` — 15
tests: reconstructable from the ledger (in-memory AND durable reload) /
lineage chain intact / locality every generation / reference integrity
every generation / parent-authoritative every generation (behavioral +
AST) / self-weakening rejected → honest halt / authorized constitutional
change propagates and governs the next search (unauthorized → rejected at
the seam) / E-H carriers byte-identical across the search / R2.8 is the
only trust boundary (the scan now covers `universal_evolution.py`, which
carries no evaluation identifiers and imports no observation machinery) /
candidate identity deterministic / competing candidates comparable
deterministically / identity index derived + non-mutable / diversity
observed over universal genes (entropy > 0) without perturbing selection /
all-infeasible halts honestly (`generations_run == 0`, reconstructable
True, nothing recorded) / Option A under universal search.

**Matrix.** R2.10.5 adds no carriers and moves no matrix row: the recipe
ISR is byte-identical (`isr_hash` unchanged `317b62a8…` — the **twelfth
Option A use**) and the matrix stays **12 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 0 MISSING**, asserted mechanically.

**Verification.** Full suite: **2124 passed / 10 skipped** (R2.10 suites:
381 passed); R2.10.4 + R2.10.3-J suites green together (68 passed).

---

## 8o. R2.10.6 — ISR → Compiler Backend consumption contract (read-only backend)

R2.10.4/5 proved universal ISR evolution under one gate; R2.10.6 proves the
DOWNSTREAM contract: a compiler backend CONSUMES the ISR without ever
participating in it. The backend is a consumer, never a participant — it may
read the semantic projection and realize it, but it may never mutate the
ISR, add meaning, infer requirements, inject technology concepts, rewrite
evolution decisions, or weaken constitutional constraints.

**Locked invariants (user-specified, before implementation).**

1. The backend is a consumer, never a participant (never mutates the ISR,
   adds meaning, infers requirements, injects tech concepts, rewrites
   evolution decisions, or weakens constitutional constraints).
2. `CompilationTarget` is a REALIZATION SELECTION — passed to the backend
   at compile time, never embedded in ISR genes.
3. The projection boundary (`BackendSemanticModel`) is deterministic and
   faithful.
4. The three-layer contamination guard: (L1) the backend module is
   structurally read-only, (L2) the ISR stays technology-neutral under
   compilation, (L3) no reverse contamination flows artifact → ISR.
5. Capability mismatch is EXPLICIT (SUPPORTED / PARTIALLY_SUPPORTED /
   UNSUPPORTED) — never silent omission.
6. The semantic source is invariant across backends.

**Machinery** (`tiannara/application/compilation/` — new package; the real
compiler backends under `constitutional_architecture/compilers/` are NOT
touched — that is R2.10.7):

- `consumption_contract.py` — `CapabilitySupport` / `CapabilityCoverage` /
  `CompilationTarget` / `CompilationProvenance` / `CompilationResult`;
  `CompilerBackend` Protocol (runtime-checkable, read-only surface);
  `BackendSemanticModel` (model_hash, source_isr_hash, capabilities,
  constraints as (kind, canonical_form) pairs, protected_regions);
  `derive_backend_semantic_model` (constraints walked through the identity
  index — the single identity namespace — + the two policy carriers, sorted
  by (kind, content)); `enumerate_isr_semantics` (the 14 carrier ids);
  `constitutional_surface_intact` (the 7 per-kind content comparisons);
  `reconstruct_semantic_source` (reads the hash back from the artifact);
  `isr_has_no_target_genes`; `REALIZATION_TECHNOLOGY_LEXICON` (react,
  fastapi, postgres, postgresql + the deployment/boundary guard terms);
  `ContaminationGuard` (layers 1–3).
- `integrity_gate.py` — `CompilationIntegrityGate` with the eight gates:
  A read-only, B determinism, C provenance, D semantic coverage, E backend
  independence (compile under a DIFFERENT target), F round-trip,
  G constitutional preservation, H evidence binding (no ledger bound = not
  certifiable).
- `reference_backend.py` — `ReferenceCompilerBackend` (json / manifest /
  fragment artifact styles, all embedding `semantic_source`; conformance
  variants: `declared_unsupported` (explicit, Gate D holds) vs `omitted`
  (silent, Gate D fails)).
- `ledger.py` — duck-typed `record_compilation` (EventType.COMPILATION,
  payload binds isr_hash / target / backend / artifact / coverage). The
  ledger never imports the contract module.

**Acceptance evidence.** `tests/test_r29_10_6_consumption_contract.py` — 21
tests: all eight gates hold / Gate A read-only / Gate B determinism /
Gate C provenance / Gate D silent omission impossible (the omitting backend
is rejected with "silently discarded: ['reliability']") / Gate D explicit
UNSUPPORTED is not silent / Gate E independence / Gate F round-trip /
Gate G constitutional preservation (+ tampered-projection rejection) /
Gate H evidence binding (chain-anchored COMPILATION event, payload binds) /
Gate H requires a ledger / multi-backend semantic-source invariance (three
artifact styles → one semantic source, distinct artifacts) / Layer 1
structural read-only (positive + negative AST) / Layer 2 technology
neutrality under compilation (+ realization-leak and mechanism-leak
negatives) / Layer 3 no reverse contamination (+ forged-provenance
negative) / target never embedded (ISR neutral before and after; the target
lives in the artifact) / model deterministic and faithful / Option A.

**Matrix.** R2.10.6 adds no carriers and moves no matrix row: the recipe
ISR is byte-identical (`isr_hash` unchanged `317b62a8…` — the **thirteenth
Option A use**) and the matrix stays **12 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 0 MISSING**, asserted mechanically.

**Verification.** Full suite: **2145 passed / 10 skipped** (R2.10.6 suite:
21 passed; R2.10.4 + R2.10.5 + R2.10.6 together: 50 passed).

---

## 8p. R2.10.7 — Real-backend conformance behind the frozen R2.10.6 contract

R2.10.6 froze the consumption contract and the eight-gate certifier; R2.10.7
is the first time the contract meets backends that were built BEFORE it
existed (the Phase 8-22 compilers under `constitutional_architecture/
compilers/`). Governing principle, locked before implementation: **conform
the backends to the contract, never weaken the contract to fit a backend** —
a failing gate is a FINDING to remediate, never a gate to weaken.

**Pre-implementation audit** (recorded as findings, not silently fixed): all
seven real backends consume the pre-contract input surface — the raw
`UniversalISR` object graph (`isr.nodes.values()`, `isr.edges`,
`isr.intent_hash`, `isr.genome_hash`, `semantic_attributes`) plus
`ArchitectureGenome` genes (`get_gene(...)`, `persistence_model`,
`tenancy_strategy`, …) — with signature `compile(isr: UniversalISR, genome:
ArchitectureGenome, context) -> CompilationBundle`; none has a
model-consumption seam. **FastAPI** is the backend most likely to fail first
(deepest graph consumption across four generation layers plus genome genes);
**Markdown** has a latent Gate-B risk (`datetime.date.today()` in ADRs).

**Machinery** (`tiannara/application/compilation/backend_conformance.py`):

- `BackendCapabilityDeclaration` — a backend's EXPLICIT declaration of which
  ISR semantics it realizes; an undeclared semantic defaults to UNSUPPORTED
  (honest by default, never silently skipped).
- `translate_projection_to_universal_inputs` — the projection-only
  translation seam: behaviors (workflows) become SERVICE nodes, capabilities
  become CAPABILITY nodes, from the model's canonical constraints alone —
  the real backend never receives the semantic ISR object graph. Structural
  genes (entities, interfaces, events) are outside the 14-semantic
  projection and are recorded as a finding rather than invented.
- `BackendConformanceAdapter` — wraps the real backend behind the frozen
  `CompilerBackend`: consumes `BackendSemanticModel`, translates the
  projection deterministically, invokes the real generation logic
  READ-ONLY, and wraps the bundle (pydantic → `model_dump(mode="json")`)
  in a provenance-bound artifact carrying `semantic_source` (Gate F
  round-trips through it) + declared coverage.
- `BackendConformanceReport` — the durable conformance artifact: gate
  results, capability coverage, contamination findings, findings with
  remediation notes, ISR semantic hash at conformance; `conforms` requires
  every gate to hold AND zero contamination findings; `failed_gates` names
  what did not.
- `BackendConformanceEvaluator` — applies the EIGHT GATES UNCHANGED through
  the integrity gate plus the three-layer contamination guard (Layer 1 scans
  the real backend's module AST for mutation fragments). It has NO
  gate-weakening surface.
- `ledger.py` — duck-typed `record_conformance` (EventType.CERTIFICATION,
  payload binds backend id / verdict / failed gates / coverage summary /
  ISR hash). The report is chain-anchored alongside the COMPILATION events.

**Acceptance evidence.** `tests/test_r29_10_7_backend_conformance.py` — 12
tests: FastAPI (the first-fail candidate) conforms with all eight gates
holding / the declaration enumerates all fourteen semantics / no silent
omission (Gate D) / multi-backend invariance with the REAL backend (one
semantic source, distinct artifacts) / Layer-2 neutrality before and after
the real compile / the report binds to the ISR semantic hash / the
evaluator has no gate-weakening surface ("relax"/"skip_gate"/"override_gate"
absent from its source) / a non-deterministic backend (the markdown
`date.today()` class of defect) is surfaced with Gate B naming the failure /
undeclared semantics default to explicit UNSUPPORTED / honest findings are
durable (pre-contract input surface + structural-gene projection gap with
remediation notes) / the report is chain-anchored (CERTIFICATION event,
chain verifies) / Option A (fourteenth use).

**Matrix.** R2.10.7 adds no carriers and moves no matrix row: the recipe ISR
is byte-identical (`isr_hash` unchanged `317b62a8…` — the **fourteenth
Option A use**) and the matrix stays **12 EXPRESSED / 18 PARTIAL /
0 PROJECTED / 0 MISSING**, asserted mechanically.

**Verification.** Full suite: **2157 passed / 10 skipped** (R2.10.7 suite:
12 passed; R2.10.4 + R2.10.5 + R2.10.6 + R2.10.7 together: 62 passed).
FastAPI is the first backend conformed; the remaining six (react, postgres,
terraform, cicd, pytest, markdown) follow the same adapter pattern in
subsequent passes.

---

## 8q. R2.10.7 expansion — conformance of the remaining six real backends

R2.10.7 proved the frozen contract against FastAPI, the first-fail
candidate. The expansion conforms the remaining six real backends one at a
time through the same discipline, then runs the milestone: the cross-backend
conformance campaign. Governing principle, preserved: **conform the
backends to the contract, never weaken the contract** — and the declaration
is the honesty boundary: SUPPORTED where the backend consumes the
dimension's content through its seam, PARTIALLY_SUPPORTED where the
dimension is realized only in part or at presence level, UNSUPPORTED where
it is not — never OMITTED, never aspirational ("an aspirational PARTIAL is
the same dishonesty as a silent omission, just with a nicer label").

**Source-verified declarations** (each verified against the real backend's
generation surface before being treated as authoritative;
`backend_capability_registry.py` — the twelve SEMANTIC_IDS, `declaration()`
with UNSUPPORTED as the implicit default):

- **react** — SUPPORTED: behavior_transitions (workflow -> views + service
  components), business_capabilities (capabilities -> COMPONENT pages);
  UNSUPPORTED: await surface, temporal, requirements traceability,
  documentation (the generated UI consumes none of them — aspirational
  PARTIALs removed with findings).
- **postgres** — SUPPORTED: data_migrations (migration target_schema_ref
  -> DATA_ENTITY -> DDL + alembic); UNSUPPORTED: capabilities, reliability,
  boundaries (attribute/FK/policy content is structural, outside the
  projection).
- **terraform** — PARTIAL: deployment_rollout_rollback (deployment
  artifacts exist but generation is genome-driven — NO carrier content is
  consumable through the projection; rollout strategy / health requirements
  / rollback invariants unrealized); everything else UNSUPPORTED.
- **cicd** — PARTIAL: deployment_rollout_rollback, testing_anchoring,
  reliability_resilience (presence-level: the seam composes a
  SystemDeploymentBundle from carrier PRESENCE — behaviors -> backend
  bundle, migrations -> database bundle, deployment -> infra bundle,
  testing anchors -> tests bundle, reliability -> operations bundle — the
  meta-compiler's pipeline stages derive from it).
- **pytest** — PARTIAL: testing_anchoring (tests are generated, not bound
  to anchor evidence); UNSUPPORTED: behavior (contract tests gated off by
  the default MODULAR_MONOLITH genome), requirements traceability.
- **markdown** — SUPPORTED: documentation (README/ADRs/runbook); the
  DocumentationIntent content is not consumed (docs are genome-derived) and
  the ADRs embed datetime.date.today() — latent cross-day determinism risk,
  recorded as a finding.
- **fastapi** (registry entry for the campaign) — SUPPORTED:
  behavior_transitions, business_capabilities; PARTIAL: reliability,
  boundaries, deployment (unchanged from the frozen declaration).

**Machinery** (all projection-only — the semantic ISR object graph is never
handed to a backend):

- `projection_seams.py` — `UniversalInputs` (universal graph + genome +
  context + optional deployment bundle), `ProjectionSeam` Protocol, and the
  six seams: React (behaviors -> FRONTEND_VIEW + SERVICE, capabilities ->
  COMPONENT), Postgres (migrations -> DATA_ENTITY targets), Terraform
  (empty graph — nothing consumable), Cicd (carrier presence ->
  SystemDeploymentBundle), Pytest (behaviors -> SERVICE), Markdown (empty
  graph — ERD is entity-driven).
- `backend_conformance.py` — the adapter generalizes: `projection_seam`
  parameter (default FastAPIProjectionSeam — the frozen behavior is
  byte-identical), `compile_system` dispatch for the meta-compiler, and the
  12 -> 14 coverage expansion (`CAPABILITY_TO_CARRIERS` + `_resolve_support`
  best-of-facets merge: a carrier with ANY supported facet is at least
  PARTIALLY_SUPPORTED). The frozen 14-key declaration vocabulary still works
  (direct declaration wins).
- `backend_capability_registry.py` — SEMANTIC_IDS (the twelve),
  `declaration()`, BACKEND_DECLARATIONS (seven), BACKEND_FINDINGS
  (per-backend remediation notes), `BackendRegistry` (real implementations,
  versions, seams, targets), `conform_all_backends` (conform + chain-anchor
  every report).
- `cross_backend_campaign.py` — `CrossBackendConformanceReport`
  (isr_semantic_hash, per_backend, semantic_invariance_held,
  artifact_divergence_count, all_conform) + `CrossBackendConformanceCampaign`
  — the milestone: same ISR through all seven realizations, one invariant
  semantic source, artifacts required to diverge.

**Acceptance evidence.** `tests/test_r29_10_7_backend_conformance_expansion.py`
— 11 tests: every declaration covers all twelve semantics / undeclared is
UNSUPPORTED / all six conform (all eight gates hold, failures never silent)
/ Gate D across the six (14-carrier coverage, no omission) / Layer-2
neutrality across six real compilations / **the milestone: one invariant
semantic source across all SEVEN divergent realizations, all conforming** /
seven chain-anchored CERTIFICATION events on a verifying chain / the seams
deliver real content (react pages from workflows + capabilities, postgres
DDL from migration targets, cicd pipeline stages from carrier presence) /
Option A (fifteenth use).

**Matrix.** The expansion adds no carriers and moves no matrix row: the
recipe ISR is byte-identical (`isr_hash` unchanged `317b62a8…` — the
**fifteenth Option A use**) and the matrix stays **12 EXPRESSED / 18
PARTIAL / 0 PROJECTED / 0 MISSING**, asserted mechanically.

**Verification.** Full suite: **2168 passed / 10 skipped** (expansion suite:
11 passed; R2.10.4 + R2.10.5 + R2.10.6 + R2.10.7 + expansion together:
113 passed). The question Phase 31 needs is now answered in evidence:
different realizations preserve the same ISR semantics.

### 8r. R2.10.8 — Artifact Verification & Provenance

R2.10.7 proved the backend consumed the ISR correctly. R2.10.8 proves the
resulting artifact can independently demonstrate where it came from and
what semantic source it represents — judged by a verifier that trusts
nothing (`tiannara/application/compilation/artifact_verification.py`).

**The claim.** `ArtifactProvenance` binds the artifact identity
(`artifact_hash`), the semantic source (`isr_hash`), the realization
(`target_id`), the producer (`backend_id` + `backend_version`), and the two
chain-anchored references: the COMPILATION event (Gate H) and the R2.10.7
CERTIFICATION evidence (`conformance_evidence_ref`), whose existence the
`ConformanceEvidenceRegistry` confirms — conformance is judged to EXIST,
never re-run.

**The judge.** `ArtifactVerifier` re-derives everything: the artifact hash
from the artifact content (`hash_artifact_canonical` — the same no-default-
str canonicalization the compile used at Gate H, raising
`CanonicalizationError` on unhandled types so identity is never manufactured
by a silent `str()`), the semantic hash from the ISR, and the expected
provenance from the ledger's independently-recorded compilation event
(`event_by_ref` + `verify_event_chain`). Coverage is checked against the
expressed carriers: a silent omission is fatal
(`silently_discarded:<ids>`), an explicit UNSUPPORTED boundary is
permitted. The verdict itself is chain-anchored
(`ledger.record_verification`, `EventType.VERIFICATION`) — recorded only
when the chain is intact. The verifier never mutates the ISR, the artifact,
or the claim (Option A, sixteenth use — zero identity requirement).

**The milestone.** `verify_cross_backend` runs the same judge across the
cross-backend campaign's seven DIVERGENT realizations: all seven verify,
all resolve to ONE semantic source, and artifact equality is never required
(`artifact_equality_required=False`) — divergence is the point of real
backends; semantic agreement is the point of the platform.

**Boundaries.** No verification semantics enter the ISR (the ISR stays the
sole semantic authority); no backend defines what counts as valid
provenance; the verifier does not re-run conformance; the matrix does not
move.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **sixteenth Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2182 passed / 10 skipped** (R2.10.8 suite:
14 passed; R2.10.4 + R2.10.5 + R2.10.6 + R2.10.7 + expansion + R2.10.8
together: 104 passed).

---

### 8s. R2.10.9 — Campaign readiness (deterministic, budget-respecting, ledger-faithful orchestration)

R2.10.8 proved a single artifact can independently demonstrate its
provenance. R2.10.9 proves the campaign machinery that will drive Phase 31 —
the orchestrator itself — is deterministic, resource-budget-respecting, and
ledger-faithful at small scale (26 intents, 2 per category, across all 13
`ProjectCategory`s) before it scales to thousands.

**The architecture.** The intent → ISR → evolution → compilation →
verification → metrics pipeline is a dependency-inverted orchestration
(`tiannara/application/campaign/`): `corpus.py` (intents, never ISRs — the
corpus is `technology-free` by construction and the evolution Contamination
Guard enforces it), `failure_taxonomy.py` (8 categories incl.
CompilationContractViolation — non-recoverable — vs TimeoutError — recoverable;
an uncategorized failure is itself a failure), `harness.py`
(`CampaignHarness`: orchestrates and measures; AST-scanned to contain no
ISR-mutation or verdict-override surface — the harness is an evidence
collector, never an authority), `dry_run.py` (the same campaign run twice
under the same seed with an honest verdict: `harness_deterministic`,
`resource_budget_respected`, `all_failures_classified`,
`ledger_intact_under_load`, `corpus_category_coverage`, `ready_to_scale`).

**The declared seam.** The constitution's Problem → ISR pipeline exists
(`tiannara.application.intent.IntentCompiler`) but is LLM-driven and not
hermetic; the dry run derives ISRs through the `DeclaredIntentPipelineStub`
and says so on every campaign result (`CampaignResult.declared_assumptions`)
— never a silent approximation. Phase 31 injects the real pipeline behind
the same duck-typed surface.

**The parallel-safety discovery.** Running the frozen R2.10.5 loop from
parallel campaign threads is unsafe by construction: the loop scopes its
byte-exact reconstruction by ledger-length slices and keeps `_run_evolution_id`
on the instance, so the R2.10.5 design assumes one loop per run. A shared
loop leaked deltas and evolution ids across intents under `max_parallel=4`.
`CampaignEvolution` therefore isolates every intent run behind fresh
loop/gate/variation/ledger instances — the campaign ledger remains the
durable evidence ledger (outcomes, compilations, verifications; the
`_append_lock` serializes appends), while per-run evolution internals live
in the run's own ledger. Ledger additions are additive and duck-typed:
`EventType.GENERATION_OUTCOME` + `record_generation_outcome` (binds
intent_id, isr_hash, target/backend, artifact_hash, compilation_event_ref,
verification refs, failures — the full provenance chain) — `load()` is
lock-guarded, and the chain stays intact under parallel load.

**The milestone.** The dry run verdict is `ready_to_scale`: deterministic
(same seed → identical outcomes, incl. hashes), budget-respecting
(120 s / intent budget honored), every failure classified (none UNKNOWN),
ledger chain intact under parallel load, all 13 categories covered, and
every successful outcome carries its provenance chain.

**Boundaries.** No Phase 31 scale (tens of intents, not thousands); no new
compiler or evolution capability (R2.10.5–8 invoked as black boxes); no
deployment execution (`deployment_attempted=False`); no lint/complexity
scoring; the matrix does not move.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **seventeenth Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2195 passed / 10 skipped** (R2.10.9 suite:
13 passed — the 10 acceptance tests plus the declared-stub test, the
constitutional-ISR derivation test, and the `ready_to_scale` verdict test).

---

### 8t. R2.10.31.1 — Calibration (the baseline everything else in Phase 31 is measured against)

31.1 is the first slice of the staged Phase 31 (31.1 calibration → 31.2
backend matrix → 31.3 failure-taxonomy validation → 31.4 scale ramp → 31.5
certification). Calibration is a MEASUREMENT phase, not a certification:
it establishes the reference distribution and proves the campaign pipeline
is deterministic and fully provenanced at the 26-intent scale, but makes
no claim about compiler correctness at scale. The epistemic chain stays
clean: R2.10.9's `ready_to_scale` (infrastructure structurally ready) →
31.1's calibration (baseline established and reproducible) → 31.5's
certification (compiler correctness proven). Each earns the next; none is
conflated.

**The machinery.** `tiannara/application/campaign/calibration.py` —
`CalibrationHarness` runs the same 26-intent corpus through the frozen
R2.10.9 `CampaignHarness` TWICE with the same seed (per-intent seeds are
derived from `(config.seed, intent_id)` — determinism holds per intent,
not just in aggregate), establishes `BaselineDistribution` (per-category
outcomes + per-failure-class counts — a shift at higher scale is a signal
to understand, not noise), and applies three gates: determinism (same
intent → same outcome, same artifact hash), complete provenance
(`ledger.chain_complete` — every successful outcome's ref AND its
compilation + verification anchors must resolve mechanically; an outcome
without provenance is unauditable), and full classification (no silent
UNKNOWN). The verdict is `READY_FOR_31_2` or `NOT_READY` — deliberately
no `CERTIFIED` (calibration measures; 31.5 certifies). The report is
chain-anchored (`ledger.record_calibration`,
`EventType.CALIBRATION` — JSON-safe baseline payload, duck-typed, the
ledger never imports the campaign package).

**The declared limitation.** The intent → ISR pipeline behind the dry run
is the DECLARED stub (the real `IntentCompiler` is LLM-driven and not
hermetic); the report records this on every calibration — a calibration
over stubbed derivations is a calibration of the stub, and says so
explicitly (`CalibrationReport.declared_assumptions`), never hidden.

**The milestone.** The calibration report is `READY_FOR_31_2`: baseline
established across all thirteen categories (26 intents, 26 successes,
0 failures — the same distribution the dry run produced), deterministic
across two runs (and reproducible across independent harness
invocations), every successful outcome carrying a resolvable provenance
chain, zero UNKNOWN failures, substrate undisturbed, and the calibration
event on an intact ledger chain.

**Boundaries.** No certification claim; no corpus growth (how the corpus
grows to thousands is 31.4's design decision — derived-from-26-seeds
measures variation-on-a-theme, genuinely new intents measure the space);
no new backends or semantics (R2.10.5–9 invoked as black boxes); no
matrix movement.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **eighteenth Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2207 passed / 10 skipped** (31.1 suite:
12 passed — the 10 acceptance tests plus the declared-stub-limitation
test and the JSON-safe-payload test).

---

### 8u. R2.10.31.2 — The backend matrix experiment (coverage and invariance at matrix scale, not throughput)

31.1 calibrated the campaign; 31.2 multiplies the baseline against the
seven real backends: **26 intents × 7 backends = 182 cases**, each disposed
into exactly one of the five disposition classes. The guardrail: 31.1's
26/26 is NOT a success baseline every backend must match — R2.10.7's
capability declarations already establish that the seven backends have
different semantic coverage, so a backend that honestly declares
UNSUPPORTED semantics is correct, not failing. The matrix is a
coverage-and-invariance experiment, never a throughput tally.

**The machinery.** `tiannara/application/campaign/backend_matrix.py` —
`MatrixHarness` derives each intent's ISR ONCE (the same declared-stub
pipeline 31.1 calibrated, no evolution — compile-side coverage is what the
matrix measures) and compiles it through all seven backends, each with its
own registry target (the R2.10.7/8 cross-backend precedent; `target_for`
selects only the category's backend, so per-backend targets are the
comparison's unit). Every case: `evaluator.conform` + `record_report`
(R2.10.7 evidence on the chain) → `adapter.compile` → `provenance_claim`
(R2.10.8) → `ArtifactVerifier.verify` — the frozen foundations invoked as
black boxes. The EXPLICITLY_UNSUPPORTED decision is made BEFORE compiling,
from the backend's declared coverage (`adapter.coverage_for` + the
mechanical `unsupported_required`): a case whose required semantics are ALL
declared UNSUPPORTED is disposed honestly, never compiled into a doomed
artifact; the unsupported semantics are named, never silent.

**The five-way disposition.** VERIFIED_COMPILATION (compiled AND
independently verified), SUCCESSFUL_COMPILATION (compiled; verification
ran, did not verify — the R2.10.8 gap stays visible, never averaged away),
EXPLICITLY_UNSUPPORTED (declared, legitimate), DIAGNOSED_FAILURE
(attempted and failed, classified by the R2.10.9 taxonomy),
INFRASTRUCTURE_FAILURE (environment/resource — recoverable
RESOURCE_EXHAUSTION/TIMEOUT classes). A case with no disposition is the
only fatal outcome: it can't be audited.

**The invariance assertion.** Per intent, every backend that compiled it
binds to ONE semantic source while artifacts are REQUIRED to diverge
structurally — divergence of realization, invariance of meaning. A
disagreement fails the experiment regardless of how many cases succeeded.

**The verdict.** `READY_FOR_31_3` ⇔ all 182 cases carry a complete,
chain-resolvable disposition, every non-VERIFIED case is classified into
the four other classes, per-intent cross-backend invariance holds, and the
31.1 declared-stub assumption is mechanically carried into the report and
its ledger event (`record_matrix`, `EventType.MATRIX` — JSON-safe per-case
payloads; never re-derived, never dropped). Deliberately no CERTIFIED —
31.2 earns 31.3, not the Phase 31 claim.

**The measured result.** All 182 cases disposed as VERIFIED_COMPILATION
(26 per backend across all seven: react, fastapi, postgres, terraform,
cicd, pytest, markdown), zero SUCCESSFUL/UNSUPPORTED/DIAGNOSED/
INFRASTRUCTURE, invariance held, artifacts diverging with one semantic
source per intent. No 26-intent corpus case is all-unsupported on any real
backend (each backend realizes at least one of the stub's expressed
carriers); the EXPLICITLY_UNSUPPORTED mechanism is exercised and proven
mechanically in the suite (`unsupported_required` — named semantics, all
required vs partially covered).

**Boundaries.** No certification claim; no throughput metric as the gate
(a backend with many EXPLICITLY_UNSUPPORTED cases is honest, not weak);
no failure-rate comparison against 31.1's 26/26 (that baseline measured
the campaign pipeline, not per-backend coverage); no new backends,
semantics, or corpus; no matrix movement.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **nineteenth Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2220 passed / 10 skipped** (31.2 suite:
13 passed — the 11 acceptance tests plus the verdict-has-no-CERTIFIED test
and the mechanical-unsupported-decision test).

---

### 8v. R2.10.31.3 — Failure taxonomy validation (the epistemic layer between scale and trust)

31.1 proved the baseline reproduces; 31.2 proved it reproduces across all
seven realizations; 31.3 proves that **when a compilation does not verify,
the platform can correctly determine WHY** — without conflating an
infrastructure failure, an unsupported semantic, a contract violation, a
genuine generated-software defect, and a harness bug. That is the layer
without which Phase 31's certification is untrustworthy: a success rate
you can't decompose into causes is a number you can't act on and can't
certify.

**The constitutional invariant.** The classifier consumes execution
evidence and produces a disposition — it NEVER reinterprets the failure to
make the campaign pass. The taxonomy is ORTHOGONAL to compiler success:
the disposition derives from what the evidence shows, never from whether
the compile succeeded. That is structural, not aspirational: the suite
AST-parses `TaxonomyClassifier.classify` and asserts it contains no
outcome vocabulary (`succeeded`, `compile_success`, `passed`) — the
classifier cannot rationalize because it cannot see the outcome.

**The validation problem.** 31.2 produced 182/182 verified compilations —
a strength of the platform but a problem for 31.3: a failure taxonomy that
is never exercised is unvalidated. Every class is therefore INDUCED as a
real execution condition and classified from evidence that actually
occurred: the actual R2.10.9 exception types raised at the actual stage
(infrastructure), the real declaration builder + 12→14 support resolver
over a real derived ISR (unsupported), real compile-then-silent-omission
caught by the real verifier (`silently_discarded` — contract/conformance),
real compile-then-tamper caught by the real verifier (`artifact_modified`
— generated-software), and a genuinely malformed corpus intent that really
fails derivation (campaign/harness). The injector knows what it induced;
the classifier knows only the evidence — the gap between those two is
exactly what is validated. Where a condition is induced (the resource cap
is raised rather than observed from live budget enforcement; the
UNSUPPORTED condition uses an all-unsupported declaration built by the
real builder, since no corpus backend is all-unsupported for any corpus
intent), the report declares it — the declared-limitation discipline
applies to injection too (`INJECTION_ASSUMPTIONS`).

**The root-cause ordering.** The classifier derives the class in
root-cause order: resource evidence first (a resource exhaustion that
CAUSES a verification failure is INFRASTRUCTURE, never the
GENERATED_SOFTWARE it corrupted — the symptom), then contract evidence
(UNSUPPORTED before CONTRACT_CONFORMANCE), then verification evidence
(GENERATED_SOFTWARE only when `is_artifact_fault` — derived from the
R2.10.8 failure reason), then stage evidence (CAMPAIGN_HARNESS). The two
dangerous confusions are proven absent: infrastructure never laundered
into generated-software (manufactures false failures) and
generated-software never hidden behind infrastructure (conceals real
bugs); contract violations never misread as artifact defects.

**The coherence mapping.** The five 31.3 classes and the eight R2.10.9
`FailureCategory` values are one system, not two drifting vocabularies
(`failure_category_map`, asserted mechanically): RESOURCE_EXHAUSTION /
TIMEOUT → INFRASTRUCTURE; COMPILATION_CONTRACT_VIOLATION →
CONTRACT_CONFORMANCE; VERIFICATION_FAILED → GENERATED_SOFTWARE;
INTENT_DERIVATION_FAILED / EVOLUTION_HALTED / COMPILATION_FAILED / UNKNOWN
→ CAMPAIGN_HARNESS.

**The verdict.** `READY_FOR_31_4` ⇔ all 910 induced cases (26 intents × 7
backends × 5 classes) classified correctly from evidence alone, the
conflation checks hold, and the 31.1 declared-stub assumption is carried
forward into the report and its ledger event
(`record_taxonomy_validation`, `EventType.TAXONOMY_VALIDATION`) — every
case is chain-addressable too (`record_taxonomy_case`,
`EventType.TAXONOMY_CASE`: observation payload + disposition payload on
the same event). Deliberately no CERTIFIED — 31.3 earns the scale ramp,
not the Phase 31 claim.

**The measured result.** All 910 induced cases classified correctly
(13/13 suite green: 11 acceptance tests + the taxonomy-coherence-mapping
test + the real-evidence test), no conflation, verdict
`READY_FOR_31_4` — every deviation can be correctly explained, and the
explanation is grounded in evidence, not rationalization.

**Boundaries.** No certification claim; no outcome-peeking classifier
(structurally enforced); no synthetic labels (injections are real
execution conditions; the two induced-condition limitations are declared);
no taxonomy revision to make cases pass (misclassification is a classifier
defect, never a taxonomy rationalization); no new backends, semantics, or
corpus; no matrix movement.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **twentieth Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2233 passed / 10 skipped** (31.3 suite:
13 passed).

---

### 8w. R2.10.31.4 — The scale ramp (the envelope, measured not assumed)

31.1-31.3 established the semantic contract at small scale. 31.4 stops
asking "can the system do this?" and asks **"do the properties established
at small scale remain true as workload increases?"** It is OBSERVATIONAL,
never architectural: the ramp never changes the semantic contract to fit
scale — it runs the REAL campaign pipeline at every level (real derivation,
real evolution, real compilation, real verification, real ledger records)
and measures where a property stops holding. The invariant that governs it:

> Scale must not become a source of epistemic ambiguity.

At 26 intents every outcome is individually inspectable; at 500 it is not,
and the danger at scale is not that failures occur but that they become
blurry. The ten gates are what keep scale honest, and they reduce to one
requirement: every property proven in 31.1-31.3 either still holds at
larger scale or fails visibly and is classified.

**The declared methodology (on the report and its ledger event, never
implicit):**

  * **Corpus growth: DERIVED_FROM_SEEDS.** Every scale corpus is the 26
    calibrated seeds (byte-identical, in the same order) plus deterministic
    derived variants — a pure function of (seed intent, tier index), no
    RNG. The ramp therefore measures *volume-of-similar*, never
    diversity-at-scale; NEW_INTENTS / MIXED are declared unreachable on
    this platform (`UnreachableCorpusStrategy` — a declared exception, not
    a silent approximation).
  * **The rerun subset (the canary) is predeclared.** `canary-6` — the
    first six calibrated seed intents — chosen in the fixture BEFORE the
    ramp runs (post-hoc selection would invite picking the cases that
    still pass, the rationalization 31.3 made structurally impossible),
    and replayed at every level through the full seven-backend matrix with
    real verification and real provenance.
  * **The reachable top is DECLARED, never silently capped.** Levels 1000
    and 5000 are scheduled but not run: full real per-intent compilation
    bounds the runnable top within the declared per-level budget. The
    measured cost at the reached top is recorded; the unreached levels are
    NAMED in the report and the assumptions.
  * **The per-level budget is a real resource measured by the real
    clock** — a breach is envelope evidence, never a campaign defect.

**The ten gates, evaluated at every level.** SCALE_MONOTONICITY (every
seed intent's outcome — success and artifact hash — byte-identical to its
level-26 outcome; the 26 seeds are present at every level, so growing the
corpus cannot silently change per-intent semantic behavior);
FAILURE_RATE_ACCOUNTING (every case has exactly one terminal disposition:
succeeded-with-chain-anchor XOR classified-failure, and the counts sum
exactly); TAXONOMY_STABILITY (every real failure classified by the SAME
31.3 classifier over the SAME real evidence — the `evidence_to_observation`
bridge — must match the R2.10.9→31.3 category map); NO_SILENT_OMISSION
(level generation events on the chain equal the success count — no dropped
cases — every canary case binds to its conformance evidence, and any
EXPLICITLY_UNSUPPORTED case names its semantics); LEDGER_COMPLETENESS
(chain intact and every outcome and canary case chain-addressable — the
canary's anchors are the verification event, the compilation event by its
deterministic id, and the conformance evidence); PROVENANCE_PRESERVATION
(ISR → target → backend → artifact → verification reconstructible, one
semantic source per intent across backends); RESOURCE_BOUND_HONESTY (a
resource-classified failure MUST flag the envelope — exhaustion is
INFRASTRUCTURE evidence, never blurred into the failure rate);
DETERMINISTIC_RERUN_SUBSET (the canary's 42 cases — disposition, isr_hash,
artifact_hash, verification — identical at every level); NO_CROSS_INTENT_
CONTAMINATION (every level outcome event binds to its own intent and to
its own category's declared backend — the R2.10.9 isolation at scale);
NO_CERTIFICATION_INFLATION (the verdict space has no CERTIFIED).

**The envelope is a measurement, not an encounter.** `_detect_envelope_hit`
reads REAL resource signals: a real classified RESOURCE_EXHAUSTION/TIMEOUT
from the real execution, a real MemoryError, or the measured wall-clock
duration exceeding the declared budget. On the run machine the ramp climbed
26 → 100 → 500 with all ten gates held at every level; at 500 the measured
level duration exceeded the declared 300s per-level budget — the envelope
was therefore **measured at 500**, the breach named precisely in the report
(`envelope_hit_at`, `envelope_reason`), and the ramp stopped honestly.
Verdict: `READY_FOR_31_5` — the properties hold as workload increases up to
a measured boundary, and nothing degraded silently on the way.

**The canary sang.** The 42 subset cases compiled and independently
verified at every level (`canary_tally["VERIFIED_COMPILATION"] == 42`,
invariance held, identical artifacts level over level) — determinism did
not degrade as the corpus grew. The 26 seeds produced byte-identical
outcomes at every level. The ledger chain stayed intact across the whole
climb. And the ramp observed **zero failures** at scale — the report
declares `taxonomy_exercised: False` rather than letting the taxonomy gate
masquerade as exercised (31.3 remains the validated domain of
failure-classification; the vacuity is named, never blurred).

**The synthetic proofs keep the machinery honest.** A declared 1ms budget
is breached by the real measured duration of level 26 — the ramp stops,
names the breach, and still reports its envelope and `READY_FOR_31_5`
(gates held); and a corpus builder that genuinely changes one seed's
problem at scale 100 makes the canary's artifact genuinely differ — the
ramp refuses readiness (`NOT_READY`, envelope at 26), proving that a
silently degraded determinism CANNOT be certified.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **twenty-first Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2253 passed / 10 skipped** (31.4 suite:
20 passed — the ten gates at every level, the envelope probes, the
not-ready drift proof, the ledger entry, and the identity assertions).

**Boundaries.** No semantic-contract change; no certification claim
(`READY_FOR_31_5`, never CERTIFIED); no post-hoc subset selection; no
exhaustion-as-failure (the envelope is measured and declared); no matrix
movement; levels 1000/5000 declared-not-run with the reachable top named;
no re-injection at scale (31.4 observes; 31.3 injects).

---

### 8x. R2.10.31.5 — Certification (consume the evidence, earn the word)

31.1-31.4 accumulated the evidence; 31.5 certifies it. It is the one
phase whose verdict may finally say `CERTIFIED` — every prior phase
deliberately used `READY_FOR_X` precisely so this one could earn the word.
But the certification is **bounded, never inflated**: an unbounded
certification is the inflation the nine invariants exist to prevent. The
certifier ASSEMBLES and VERIFIES the evidence chain — it does not run new
machinery that could change what the evidence shows. The two deliberate
exceptions are the canary **re-run** (a certification that trusts
yesterday's evidence without reproducing it is one step from trusting
yesterday's claim) and the **novelty-grounding check** (the capstone that
operationalizes the constitution's foundational principle — "requirements
should never directly generate source code; all work must flow through
the ISR").

**The seven dimensions, each bound to its evidence and its bounds.**
`calibration` (the baseline is reproducible, on the declared pipeline);
`backend_matrix` (the invariant survives seven realizations of one
semantic source); `failure_taxonomy` (every deviation correctly attributed
from real evidence — 910 induced cases, intact); `scale_ramp` (the ten
gates held at every level to the measured envelope); `canary` (the 42-case
rerun subset **replayed through the seven-backend matrix at certification
time** — reproduced, never cited); `envelope` (the measured boundary is
first-class certification content, and the budget exceedance stays
INFRASTRUCTURE-classified — a real resource signal, never reinterpreted as
a software defect); `novelty_grounding` (a genuinely new intent — outside
the calibration corpus, so the check exercises generative capacity, never
corpus recall — flows through the ISR, verifies against its source, and
contains not one untraceable semantic element).

**Grounding is decidable because both sides speak the same language.** The
R2.10.6 `BackendSemanticModel` projection is the common vocabulary: the
ISR's semantic surface (capability ids, constraint forms, protected
regions) versus the semantic elements the artifact actually carries (its
declared coverage, its embedded projection). An artifact element with no
counterpart in the source ISR is **hallucination, by definition** — the
generator asserting what the source of truth never said — and there is no
minor-hallucination pass: any untraced element fails the check. The
grounding comparison is proven real, not tautological: a tampered artifact
carrying a foreign capability id is detected and the untraced element is
named.

**The qualification belongs in the verdict, not in a footnote.** The
honest verdict is `QUALIFIED_PARTIAL`: 31.4 observed zero failures, so the
taxonomy was validated on induced failures (31.3) but never exercised on
natural failures at scale (`taxonomy_exercised: False`, already declared).
That is not a defect — it is a bound on the certification's scope, and it
is carried in the verdict, in the scale_ramp dimension's bounds, and in
the certification statement. `CERTIFIED` is earned, never issued by
default: the pure verdict renderer returns it only when every dimension
passes. And the machinery refuses to certify a canary that genuinely
drifts: a baseline with one differing artifact hash fails the canary
dimension → `NOT_CERTIFIED`, with the failure named.

**The artifact is bound to the ledger, not a document about it.** Each
dimension names the refs it is reconstructed from; the content hash
commits to (verdict, dimensions, evidence_chain_refs) under the
no-default-str canonicalization; the certification event on the chain
carries the same claim; every ref resolves to a real event; the chain
stays intact across the whole certification. The measured result on the
run machine: envelope **500** (measured, never assumed), canary re-run
**42/42 VERIFIED_COMPILATION with identical artifacts**, novelty intent
`inventory-lot-01` derived → compiled → verified → **zero untraced
semantics**, verdict **`QUALIFIED_PARTIAL`** with the taxonomy-at-scale
bound declared.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **twenty-second Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2273 passed / 10 skipped** (31.5 suite:
20 passed — the seven dimensions, the canary re-run, the novelty
grounding, the negative probes, the verdict discipline, the ledger
binding, and the identity assertions).

**Boundaries.** No semantic-contract change; no unbounded statement (the
statement names the envelope, the assumptions, and the novelty result);
`QUALIFIED_PARTIAL` is the honest verdict (the taxonomy-at-scale bound
declared, never hidden); `CERTIFIED` only when every dimension passes;
no criterion retroactively weakened to fit the measured envelope (the
certifier has no criterion-mutation surface — enforced structurally);
no hallucination tolerance; no matrix movement; no re-run of the campaign
itself (the evidence chain is consumed, the canary reproduced, the
novelty check performed).

---

### 8y. R2.10.32 — Engineering Certification (gates, never averages)

Phase 32 certifies the engineering of the generated product itself: one
artifact against the ISR that produced it, under the declared R2.10.32
contract. It is a measurement harness — the certifier never mutates the
ISR or the artifact (no mutation surface, enforced structurally via AST);
the EvolutionaryQualityLoop is the only remediation surface, and it
mutates ONLY the ISR through the declared mutation operators
(reliability / deployment / testing-anchor), then recompiles and
re-certifies.

**The contract** (`tiannara/application/quality/engineering_contract.py`):
eight gates — **ISR Conformance** (dispositive, checked FIRST) plus
IMPLEMENTATION, ARCHITECTURE, DESIGN, FAILURE_ENGINEERING, SECURITY,
EVOLVABILITY, OPERATIONS. The verdict is rendered from the gates, never
averaged, never scored: any CRITICAL finding is structurally dispositive
(`NOT_CERTIFIED`); otherwise all-meet → `CERTIFIED`, else
`QUALIFIED_PARTIAL`. The gate calibration is declared — severity
calibration, vacuity policy (insufficient evidence is ADVISORY and named,
never blurred), and the abstraction-justified threshold (0.50) that
conjoins the EVOLVABILITY complexity gate so over-abstraction cannot game
a cheap simulated evolution cost.

**The harness** (`engineering_certification.py`): `extract_isr_obligations`
lifts every carrier out of the ISR (mandatory: requirement, acceptance
criterion, boundary, reliability, deployment, migration, temporal,
testing anchor, protected region; advisory: documentation, evolution
objective, evolution policy). `ISRConformanceCheck` binds the artifact to
its ISR via `semantic_source.isr_hash` (divergence violates every
obligation) and enforces each obligation through the artifact's real
declared evidence — its own coverage claims, projection content, and
bundle files. The seven built-in analyzers are deterministic over that
same evidence (coverage / projection / bundle / ISR carriers — no
external tools). Every dimension result and every certificate is
chain-anchored (`ENGINEERING_DIMENSION` / `ENGINEERING_CERTIFICATION`
events); the certificate's content hash commits to its content and its
evidence refs.

**Honest runs (the test suite's narratives).** The reference artifact over
the full derived ISR certifies (conformance enforced, all seven gates
met, 3/3 failure scenarios handled). The FastAPI artifact over the same
ISR is NOT_CERTIFIED on conformance — its own declared coverage leaves
most mandatory obligations UNSUPPORTED/PARTIAL: locally well-formed
(hexagonal layers, acyclic) but architecturally wrong, named as such. The
FastAPI artifact over a behavior-only ISR passes conformance vacuously
(named) and is then NOT_CERTIFIED structurally: wildcard CORS +
`allow_credentials` + OAuth bearer is a CRITICAL SECURITY violation. The
Postgres artifact over a migration-only ISR passes conformance but fails
EVOLVABILITY: abstraction not justified (1 of 5 expressed semantics
realized) despite a cheap evolution cost — the conjoined gate refuses
over-abstraction. Wrong-source artifacts stop before any dimension runs.

**The loop.** Starting from the behavior-only ISR (`QUALIFIED_PARTIAL` —
no failure scenarios MAJOR, no deployment semantics MAJOR), the loop
applies its declared mutations in generation order — reliability
requirement, then testing anchor, then deployment intent — reaching
`CERTIFIED` within the declared generation budget, every generation
chain-anchored. Weaknesses without a declared mutation mapping (a
backend's declared-unsupported semantics) are carried in the diagnosis,
never papered over; already-satisfied mutations are declined, never
re-applied.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **twenty-third Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2289 passed / 10 skipped** (Phase 32
suite: 16 passed — the dispositive conformance probes, the
locally-perfect-but-wrong case, the structural CRITICAL block, the
scenario-driven failure coverage, the ungameable evolvability gate, the
evidence binding, the idempotent chain, the vacuity-named-never-blurred
policy, the AST-enforced no-mutation surface, the declared gate
calibration, the loop's discovered better architecture, and the matrix
identity).

**Boundaries.** No semantic-contract change; no matrix movement; no
unbounded statement (gates name thresholds and calibration); vacuity is
named, never blurred; the certifier cannot mutate (enforced
structurally); the loop mutates only the ISR through declared operators;
no external tooling assumed (analyzers are deterministic over declared
evidence); `CERTIFIED` only when every gate meets and no CRITICAL
finding exists.

---

### 8z. R2.10.32.1 — the ArchitecturalDecision ISR carrier (the decision record)

Architectural decisions became first-class ISR objects: WHY the system's
shape is what it is, in ADR-complete form. The carrier lives in the ISR
(`constitutional_architecture/isr/semantics/decision.py`) — the ISR is the
source of truth; Phase 32 (certification) is its CONSUMER, never its
author, and that authorship boundary is enforced structurally (the
certification package contains no construction surface for
`ArchitecturalDecision`).

The carrier is constitutionally ADR-complete: arc42 Context → `context`,
Problem → `question`, Alternatives → `alternatives`, Selection →
`selected_strategy`, Trade-offs → `trade_offs`, Benefits → `benefits`,
Risks → `risks`/`rejected`, Future evolution → `future_evolution`. It is a
RECORD of an actual choice: `selected_strategy` must be among at least two
alternatives (a single option is not a decision), and an unexplained
decision (no trade_offs, no benefits) is rejected at construction.

Reference edges resolve against the existing constructs and author no new
obligation: `requirement_refs` → F's requirements, `invariant_refs` → the
invariant-bearing carriers of E/D/J (boundary ids, reliability requirement
ids, protected region ids), `architectural_scope` → modules,
`verification_refs` → H's testing anchors. The verification edge is an
OBLIGATION/PROVENANCE edge, never proof that verification occurred — a
decision structurally cannot claim a verdict (the three-layer separation
holds: the ISR declares what evidence must establish, evaluation produces
it, certification judges it). No `architecture_ref`/`implementation_refs`
fields yet — resolving decisions to their implementations is the
traceability phase's job (R2.10.32.2).

The carrier participates in the semantic identity like any other gene:
`architectural_decisions` joins the identity-index DOMAINS, is
path-identifiable, ref-checked against the existing carriers (dangling
edges rejected), referenceable by J's protected regions, and carried by
the consumption contract — all automatically identity-neutral when empty.

**Matrix.** The recipe ISR is byte-identical (`isr_hash` unchanged
`317b62a8…` — the **twenty-fourth Option A use**) and the matrix stays
**12 EXPRESSED / 18 PARTIAL / 0 PROJECTED / 0 MISSING**, asserted
mechanically.

**Verification.** Full suite: **2304 passed / 10 skipped** (R2.10.32.1
suite: 15 passed — the ADR-complete carrier, the selected-in-alternatives
rule, the single-option rejection, the unexplained-decision rejection,
empty identity neutrality, the canonical omission, the locked matrix, the
identity-index participation with intact reference edges, the dangling
reference rejection, the obligation-edge-not-verdict structure, J
protectability, the semantics-only projection, technology neutrality,
realization-term rejection, and the structural no-author certification
boundary).

**Boundaries.** No decision generation, no ADR inference, no traceability
evaluation, no design-quality certification, no Phase 32 mutation — the
carrier is a record; records do not judge themselves. The runtime→ISR
feedback loop remains deferred to R2.10.31.5's `natural_failure_at_scale`
(learning-governance), untouched by this phase.

---

## 9. Next phase boundary

**R2.10 — Production software generation**, sequenced (order is mandatory):

```
R2.10.1  ISR capability/expressivity audit        ← executed
R2.10.2  Missing ISR primitives (the 10 MISSING rows above)  ← contract suite + Option A migration
R2.10.3  Primitive roots, in derived order         ← A temporal (3/18/0/9) + B capabilities (4/18/0/8) + C migrations (5/18/0/7) + D reliability (6/18/0/6) + E boundaries (7/18/0/5) + F requirements (8/18/0/4) + G deployment (9/18/0/3) + H testing_anchoring (10/18/0/2) + I documentation (11/18/0/1) + J evolution_objectives_protected_regions (12/18/0/0) landed — R2.10.3 COMPLETE, no MISSING rows remain
R2.10.4  Universal ISR evolution integration (SemanticEvolutionGate) ← executed
R2.10.5  Universal evolutionary search (UniversalEvolutionLoop) ← executed
R2.10.6  ISR → Compiler Backend consumption contract (read-only CompilerBackend) ← executed
R2.10.7  Real-backend conformance behind the frozen R2.10.6 contract (FastAPI conformed; react, postgres, terraform, cicd, pytest, markdown follow) ← executed
R2.10.7  Cross-backend conformance campaign (one ISR, seven realizations, one invariant semantic source) ← executed
R2.10.8  Artifact verification & provenance (independent judge: artifact integrity, ISR binding, target/backend binding, coverage, ledger chain, conformance evidence — seven divergent realizations resolve to one semantic source) ← executed
R2.10.9  Campaign readiness (orchestration, measurement, and failure classification proven deterministic, budget-respecting, ledger-faithful at tens of intents; dry-run verdict ready_to_scale) ← executed
R2.10.31.1  Calibration — Phase 31 staged campaign slice 1 (baseline established across all thirteen categories, deterministic replay, complete provenance, failures classified; verdict READY_FOR_31_2 — a measurement, never a certification) ← executed
R2.10.31.2  Backend matrix — Phase 31 staged campaign slice 2 (26 intents × 7 backends = 182 cases, five-way disposition, cross-backend invariance per intent, declared-stub assumption propagated; verdict READY_FOR_31_3) ← executed
R2.10.31.3  Failure taxonomy validation — Phase 31 staged campaign slice 3 (all five failure classes induced as real execution conditions, classifier correct on every one from evidence alone — AST-enforced no-outcome-peeking — no conflation, chain-resolvable; verdict READY_FOR_31_4) ← executed
R2.10.31.4  Scale ramp — Phase 31 staged campaign slice 4 (26 → 100 → 500 real campaign runs, all ten gates held at every level, predeclared canary replayed through all seven backends, envelope measured and declared at 500, no silent degradation, no certification inflation; verdict READY_FOR_31_5) ← executed
R2.10.31.5  Certification — Phase 31 staged campaign slice 5, the culmination (the 31.1-31.4 evidence chain consumed and bound: seven dimensions with evidence refs and declared bounds, canary re-run 42/42 at certification time, novel intent outside the corpus derived → verified → zero untraced semantics, content hash committing to the evidence refs; verdict QUALIFIED_PARTIAL — the taxonomy-at-scale bound declared in the verdict, never a footnote) ← executed
R2.10.32  Engineering Certification (gates, never averages: the dispositive ISR-conformance check first, seven gradable dimensions over the artifact's real declared evidence, verdict rendered from gates with no score, certifier with no mutation surface, EvolutionaryQualityLoop as the only remediation seam mutating only the ISR through declared operators; honest runs: reference certifies, FastAPI-full is locally-perfect-but-architecturally-wrong on conformance, FastAPI-minimal is structurally blocked by a CRITICAL CORS/credentials security violation, Postgres-migration probe fails the ungameable evolvability gate, the loop reaches CERTIFIED in declared generations; full suite 2289 passed / 10 skipped) ← executed
R2.10.32.1  ArchitecturalDecision ISR carrier (the decision record in ADR-complete form, empty identity-neutral, participating in the identity index and consumption contract, reference edges resolving against F/E/D/J/modules/H with no new obligation authored, structural no-author boundary for Phase 32; full suite 2304 passed / 10 skipped) ← executed
R2.10.32.2  Decision traceability (resolve decisions to their implementing structures — next)
R2.10.6  Safe structural crossover (chromosome families/genes: Architecture,
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