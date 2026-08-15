# ADR-Phase28: Constitutional Governance Closure

**Status:** Accepted | **Date:** 2026-08-07
**Phase:** Phase 28 — Constitutional Governance

## Context
Phase 28 (per `folder/phase.md`) governs all platform evolution safely,
transparently, and accountably. The Phase 28 `GovernanceKernel`
(PDP/PAP/PEP) was already present and wired into the marketplace gateway,
but the majority of the declared specification was unimplemented:

- Only `ConstitutionISR` and `PolicySetISR` existed in `schemas.py`; the
  declared ISR extensions (`PolicyRuleISR`, `ApprovalWorkflowISR`,
  `ComplianceReportISR`, `AuditEvidenceISR`, `ChangeLineageISR`,
  `GovernanceExceptionISR`, `ConstitutionVersionISR`, ...) were absent.
- Declared runtime components `Voting system`, `Version manager`, and
  `Governance dashboard` did not exist.
- No canonical tests covered Phase 28 in `tests/`; `version manager` and
  `ConstitutionVersionISR` were not implemented at all.

## Problem
Close Phase 28 without breaking the working kernel contract
(`test_governance_kernel_delegates_approval`) and without coupling
governance to any implementation technology.

## Alternatives Considered
1. Modify `GovernanceKernel` in place — **rejected**: risks the tested
   PDP/PAP/PEP contract; violates independent replaceability of subsystems.
2. Event-sourced version history — **deferred**: premature complexity; the
   snapshot + `ChangeLineageISR` approach gives equivalent ratification
   auditability, and a `ConstitutionVersionRepository` port allows an
   event-sourced adapter later without touching `VersionManager`.
3. Single hardcoded voting rule — **rejected**: governance rules must evolve
   independently (Governance chromosome family).
4. Dashboard with mutation capability — **rejected**: would create a second
   enforcement point, violating the single-PDP principle.

## Decision
- Add seven governance ISR schemas (plus supporting enums and
  `normalize_policy_set()`) additively; **fail-closed by design**
  (`PolicyRuleISR.effect` defaults to `DENY`).
- Implement three independent subsystems:
  - `VotingSystem` — replaceable `TallyStrategy` per `VotingRuleKind`
    (unanimity / simple-majority / weighted-majority); deterministic and
    fail-closed.
  - `VersionManager` — append-only, strictly-increasing semver chain over
    `ConstitutionVersionISR`; ratification requires an approved `VoteOutcome`;
    every ratification emits a `ChangeLineageISR`.
  - `GovernanceDashboard` — read-only projection only (no write capability).
- Integrate via `GovernedKernel`, a composition wrapper (opt-in at the
  `GovernanceGateway` seam) that preserves the wrapped kernel's
  `evaluate` contract byte-for-byte for non-amendment requests.

## Trade-offs
- Wrapper adds one indirection layer at the gateway seam
  (acceptable: opt-in, default off).
- In-memory repositories only; durable adapters are a documented extension
  point (deliberately deferred to avoid unnecessary complexity).
- Evidence payloads are retained in-process for chain verification;
  cryptographic external anchoring (e.g. signed/notarized storage) is future
  work.

## Consequences
- Governance is now fully expressible in the ISR: rules, workflows, reports,
  evidence, lineage, exceptions, and ratifiable versions.
- Each subsystem is independently testable and replaceable
  (`TallyStrategy` and `ConstitutionVersionRepository` are the replacement
  seams).
- No framework/language/infrastructure concepts entered the core.
- `test_governance_kernel_delegates_approval` remains unmodified and green.

## Future Evolution
- Governance metrics as fitness dimensions (belongs to the fitness domain —
  deliberately excluded here to avoid coupling).
- Durable repository adapter; cryptographic signing of `AuditEvidenceISR`.
- Governance chromosome family in the architectural genome referencing these
  schemas.

---

## Option (d) Addendum - Governance Fitness Dimension

**Status:** Accepted | **Date:** 2026-08-07
**Phase:** Phase 28 Future Evolution (deferred item: "Governance metrics as fitness
dimensions")

### Context
Phase 28's ADR deferred governance-as-fitness to the fitness domain "to avoid coupling."
The platform now needs a constitutional evolution signal: the selection half of the
governance loop must project governance ISR into fitness so the evolution engine can
drive governance health without coupling governance logic to any fitness framework.

### Problem
Express governance health as a bounded, multi-objective fitness signal while keeping
governance logic pure, framework-neutral, and independently testable — the same
decoupling discipline applied to the Voting/Version/Exception subsystems above.

### Alternatives Considered
1. Fold scoring into `GovernanceDashboard` (read path) — **rejected**: a read
   projection is a query interface, not an evaluation engine; coupling fitness to the
   dashboard would conflate observability with selection.
2. Single scalar governance score — **rejected**: collapses dimensions, masking
   trade-offs (e.g. high compliance but low constitutional currency). Violates the
   "avoid relying on a single aggregate score" constitutional principle.
3. Import the fitness engine into the governance core — **rejected**: would couple
   governance to an implementation framework, breaking the Phase 28 convention that
   `constitutional_architecture/` concepts stay framework-agnostic.
4. Score governance from raw runtime state (non-ISR) — **rejected**: would bypass the
   immutable ISR contract; all inputs must be ISR so the signal is auditable and
   reproducible.

### Decision
- A framework-neutral core, `governance_fitness.py`, reads **only** governance ISR
  (`GovernanceFitnessInput`) and emits `GovernanceFitnessResult` — a vector of six
  bounded objectives in [0.0, 1.0] plus optional opt-in `composite` (default
  `None` = vector-only).
- Fail-closed by construction: absence of evidence scores low; the
  multiple-ratified-heads invariant scores 0.0.
- Deterministic per `(input, now, config)`; each objective carries a
  human-readable rationale.
- The core **never imports** the fitness engine. A thin adapter seam
  (`collect_governance_state` + `to_fitness_objectives`) is the only coupling point:
  it gathers Phase 28 subsystem outputs into ISR and maps the vector to the
  optimiser's objective-map shape.

### Trade-offs
- Vector-only primary output adds shape complexity for consumers that want a scalar;
  mitigated by the opt-in `composite_weights`.
- `collect_governance_state` trusts the caller to supply the post-revocation active
  exception set (per the Phase 28 sourcing contract); an incorrect registry would
  degrade the signal. This is an explicit, documented contract, not a bug.
- The Pareto wiring targets the canonical Phase 21 optimiser
  `constitutional_architecture/engine/pareto_optimizer.py::ParetoOptimizer`
  consuming `Individual.fitness` as an `engine.fitness.FitnessVector`
  (`dict[str, float]`). `to_fitness_objectives` already yields that exact shape
  (six governance dimension keys in [0.0, 1.0]), so the core needed no change.
  The adapter merges this vector with the architecture fitness vector
  (`FitnessVector.add`) so all candidates share identical dimension keys —
  required because `FitnessVector.dominates` raises `ValueError` on mismatched
  dimensions — and the optimiser must be built with `use_composite=False` so the
  governance dimensions are not collapsed away by the `COMPOSITE_OBJECTIVES`
  reduction. This is confirmed (no longer pending).

### Consequences
- Governance health is now a governed, auditable evolutionary signal sourced entirely
  from ISR — closing the Phase 28 Future Evolution deferral.
- The fitness engine depends only on a plain `dict[str, float]`; governance depends
  on nothing from the fitness domain.
- The variation half (governance chromosome family) remains out of scope; registering
   the dimension with the optimiser is a core-untouched adapter action at the
   `engine/plugins.py::FitnessEvaluatorPlugin` seam.

---

## Option (a) Addendum - Governance Chromosome Family (Variation)

**Status:** Accepted | **Date:** 2026-08-07
**Phase:** Post-Phase-30 increment (variation half of the governance loop)

### Context
Option (d) added governance selection and bridged it into the Pareto optimiser,
but the merged governance vector is platform-wide and identical across candidates,
hence Pareto-neutral. Selection exists but no variation: governance cannot
discriminate or improve.

### Problem
Give candidates distinct governance architectures (variation) so the six
governance fitness dimensions can select among them, without fabricating or
coupling to the (unconfirmed) genome contract.

### Alternatives Considered
1. **Reuse option-(d) operational scoring on candidate designs** — rejected:
   candidates have no realized governance history (no reports/evidence), so
   operational scoring would mis-score designs.
2. **One monolithic governance gene** — rejected: would couple independent
   governance levers and block independent mutation/crossover per property.
3. **Register into the genome's gene base / chromosome registry now** —
   rejected: the contract is unconfirmed; this would fabricate an interface.
   Genes are implemented genome-agnostically with an explicit ADAPTATION POINT.

### Decision
- Add `GovernanceDesignISR` (+`VersioningStrategyKind`) as the candidate's
  expressed governance architecture.
- Implement `GovernanceChromosome` with eight independent genes, each with its
  own value space, deterministic mutation, and uniform per-gene crossover;
  `express()` projects to `GovernanceDesignISR` (the engine's ISR), so gene
  internals are never read by evolution.
- Score designs with `GovernanceDesignFitness` across the SAME six objective
  names as option (d), so the bridge's dimension-set-consistency invariant
  holds whether governance is scored by design (candidates) or realized state.

### Trade-offs
- Design scoring heuristics are initial; calibrate via the continuous-evolution
  loop (telemetry -> fitness update -> genome refinement).
- Genes are genome-agnostic; a thin adapter wraps them if the genome defines a
  base `Gene` with required methods (semantics transfer unchanged).
- Policy-rule bodies are requirement-derived and not fabricated; only the
  approval workflow is fully projected to concrete ISR.

### Consequences
- Closes the variation half; governance is now a first-class evolvable dimension.
- Genes encode architectural decisions (ISR-first), not implementation detail.
- Selection + variation now close the governance evolutionary loop end-to-end
  (subject to genome integration at the ADAPTATION POINT).
