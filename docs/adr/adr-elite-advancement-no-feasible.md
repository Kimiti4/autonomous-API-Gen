# ADR: Elite Advancement on No-Feasible Generations (R2.9.3)

Status: Accepted (R2.9.3)

## Context

R2.9.3 introduced multi-generation evolution. A generation produces a
population, evaluates every candidate through the R2.8 boundary, selects by
multi-objective Pareto, and threads the selected ISR as the next generation's
parent. The original design terminated the run with
`NO_FEASIBLE_CANDIDATES` whenever a generation had no candidate that passed
every gate.

## Problem

On the FSM substrate, `feasible ⟺ resolved`: the `TargetFailureGate`
requires exit code 0 with all tests passing, which in turn requires every
awaiting surface to be resolved. A candidate is therefore feasible if and
only if the observed defect is already fixed. With a feasible-only
advancement rule, evolution cannot make incremental progress — the search
either fixes the defect in one generation or terminates. Multi-generation
convergence is *unprovable by construction*, which is exactly the property
R2.9.3 exists to demonstrate. A no-feasible generation does not mean the
search has failed; it means the hypotheses evaluated so far do not yet pass
every gate.

## Decision

1. **Elite advancement.** When a generation's Pareto frontier is empty, the
   deterministic elite — best by lexicographic `FitnessVector` objectives in
   an explicit safety-first canonical order
   (`structural_validity` → `causal_validity` → `invariant_compliance` →
   `regression_safety` → `correctness` → `complexity_efficiency`), with
   `candidate_id` tie-break — becomes the next generation's parent
   (`elite_advanced=True`). The run terminates `NO_FEASIBLE_CANDIDATES` only
   when the elite is identical to the current parent (no progress possible).
2. **Never a scalar.** The elite rule is lexicographic over named objectives,
   never a collapsed aggregate score (Constitution: *avoid relying on a
   single aggregate score*).
3. **Safety-first ordering.** The elite is the *parent* of the next
   generation, so it must be the safest viable foundation: never structurally
   broken, never causally unsound (no forged evidence), never deceptive
   (invariant-violating), never regression-prone. Occam is the final
   tie-break among equally-safe candidates. Because the boundary re-evaluates
   every generation, this is defense-in-depth, not a correctness hole.
4. **Replaceable policy.** Elite advancement is `EliteAdvancementStrategy`, a
   `SelectionStrategy` injected as `elite_strategy=` on
   `MultiGenerationEvolutionCoordinator`, alongside R2.6's
   `DeterministicComplexityPreference` (Constitution: *each stage must remain
   independently replaceable*). R2.9.4/R2.9.5 swap selection policies without
   touching the coordinator.
5. **Deviations are recorded.** Elite advancement is recorded per generation
   (`elite_advanced=True`) in `EvolutionState` and the ledger's
   `generation_completed` event, so no-feasible advancement is auditable, not
   hidden.

## Alternatives considered

- **Terminate on no-feasible (original design):** rejected — makes
  multi-generation convergence unprovable on the FSM substrate where
  `feasible ⟺ resolved`; evolution degenerates to a one-shot search.
- **Scalar elite score (e.g. weighted sum):** rejected — violates the
  multi-objective principle; a single aggregate score can let diverse-but-
  wrong or deceptive candidates outcompete safe ones.
- **Random or non-deterministic advancement:** rejected — breaks replay
  determinism (R2.9.3 acceptance criterion) and reproducibility of evidence.

## Trade-offs

- **A worse parent may temporarily be advanced.** An infeasible elite is, by
  definition, not a complete fix. This is acceptable because every subsequent
  generation re-evaluates the parent fresh through the R2.8 boundary; an
  unsound foundation cannot launder evidence (the CausalGate binds every
  verdict to the generation's own compile/recompile hashes).
- **Extra generations on some runs.** Staged-repair scenarios (R2.9.3's
  two-generation convergence test) need one or more elite-advanced
  generations before the repair is available. This is the intended cost of
  evolution over time.

## Risks

- **Monoculture through repeated elite advancement.** A restricted variation
  ensemble may advance the same elite repeatedly. Mitigated: stagnation
  detection terminates the run when the same ISR is selected for
  `stagnation_window` generations, and R2.9.4's anti-monoculture work
  (diversity preservation, observe-first) targets this at the population
  level.

## Consequences

- Multi-generation convergence is demonstrable: the R2.9.3 harness proves a
  defect survives a repair-less generation and is resolved in a later one,
  with the lineage chain intact.
- `NO_FEASIBLE_CANDIDATES` now means "the search is stuck" (elite equals
  parent), not "no candidate was perfect".
- The elite policy is a swap point for R2.9.4/R2.9.5 without coordinator
  changes.

## Tracked debt (logged, not normalized)

- **Docker container-load flakes (2 known).** Docker-gated tests fail
  intermittently under heavy combined load (sequential container starts),
  passing in dedicated runs. Signature: `"rejected all N candidates; Pareto
  frontier empty after filtering infeasible candidates"` — an environment/
  daemon-freshness artifact, not a code defect. Tracked for R2.9.7
  (long-horizon stability) or test-infrastructure work; must not become
  expected failures.
- **`DockerExecutionEnvironment.available()` probe timeout** raised 10s → 30s
  (R2.9.3): a warm Docker Desktop daemon takes ~9s to answer `docker info`;
  the old probe misclassified slow-but-up as down, skipping all Docker-gated
  tests. Same class of bug as R2.9.1's CLI-present-but-daemon-down fix: a
  capability probe that lies.

## Future evolution

- R2.9.4: anti-monoculture — diversity preservation as an injectable policy
  at the population level; the elite rule's ordering and the diagnostic
  thresholds will be tuned from R2.9.3-recorded diversity trajectories
  (evidence-first).