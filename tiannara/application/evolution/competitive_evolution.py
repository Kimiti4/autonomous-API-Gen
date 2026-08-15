"""R2.6 -- competitive evolution: generate, score, Pareto, select.

Where R2.5 scores one candidate against the validation frontier, R2.6 searches
a *frontier* of competing candidates and selects by multi-objective Pareto
preference rather than a single aggregate score (Constitution: "avoid relying on
a single aggregate score").

Pipeline:

    broken ISR + observation
        | candidate generation (tuple of MutationOperator)
        | evaluate each through the R2.5 CandidateGate (compile+run ONCE per
        |   candidate; the identity/null candidate reuses the broken run)
        | fitness evaluation (gate verdict -> FitnessVector)
        | filter feasible -> Pareto frontier
        | selection (replaceable strategy)
        v
    SelectionDecision -> SelectionRecord on the causal ledger
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass
from typing import Optional, Protocol

from constitutional_architecture.isr.model import ISR

from tiannara.application.evolution.candidate_gate import (
    GateContext,
    CandidateGate,
    CandidateVerdict,
)
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.compiler_sandbox import hash_artifact
from tiannara.application.evolution.ledger import (
    EvolutionLedger,
    stable_isr_hash,
)
from tiannara.application.evolution.fitness import (
    FitnessVector,
    ScoredCandidate,
    compute_fitness,
)
from tiannara.application.evolution.mutation_operators import MutationCandidate
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import FailureObservation


@dataclass(frozen=True)
class SelectionDecision:
    """The auditable outcome of a competitive-evolution round."""

    selected_candidate_id: Optional[str]
    candidates: tuple[ScoredCandidate, ...]
    pareto_frontier_ids: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "pareto_frontier_ids": list(self.pareto_frontier_ids),
            "rationale": self.rationale,
            "candidates": [s.to_dict() for s in self.candidates],
        }

    def content_hash(self) -> str:
        from tiannara.domain.services.canonical import canonical_hash

        return canonical_hash(self.to_dict())


def pareto_frontier(scored: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Maximal feasible candidates -- those not dominated by any other feasible
    candidate. Infeasible candidates never enter the frontier."""

    feasible = [s for s in scored if s.feasible]
    frontier: list[ScoredCandidate] = []
    for cand in feasible:
        dominated = any(
            other is not cand and other.fitness.dominates(cand.fitness)
            for other in feasible
        )
        if not dominated:
            frontier.append(cand)
    return frontier


class SelectionStrategy(Protocol):
    """Replaceable selection stage. Given a Pareto frontier of feasible
    candidates, choose one (or none)."""

    def select(self, frontier: list[ScoredCandidate]) -> Optional[ScoredCandidate]:
        ...


class DeterministicComplexityPreference:
    """R2.6 default strategy: prefer the smallest feasible mutation.

    Among Pareto-equivalent candidates (same correctness/safety), pick the one
    with the highest ``complexity_efficiency`` (Occam). Ties broken by
    candidate_id for determinism.
    """

    def select(self, frontier: list[ScoredCandidate]) -> Optional[ScoredCandidate]:
        if not frontier:
            return None
        return sorted(
            frontier,
            key=lambda s: (
                -s.fitness.get("complexity_efficiency"),
                s.candidate.candidate_id,
            ),
        )[0]


class EliteAdvancementStrategy:
    """R2.9.3 no-feasible policy: deterministic elite advancement.

    When a generation has no feasible candidate, the elite -- best by
    lexicographic FitnessVector objectives in SAFETY-FIRST canonical order,
    candidate_id tie-break, never a scalar -- becomes the next generation's
    parent. It is a selection policy and sits alongside
    ``DeterministicComplexityPreference`` as an independently replaceable
    stage (Constitution: "each stage must remain independently replaceable");
    R2.9.4/R2.9.5 may swap selection policies without touching the
    coordinator.

    Safety-first ordering: the elite is the PARENT of the next generation, so
    it must be the safest viable foundation -- never structurally broken,
    never causally unsound, never deceptive (invariant-violating), never
    regression-prone. Occam is the final tie-break among equally-safe
    candidates. Because the boundary re-evaluates every generation anyway,
    this is defense-in-depth, not a correctness hole.
    """

    #: Canonical lexicographic order. Deliberate, not alphabetical: safety
    #: dimensions precede efficiency so the elite can never be a broken or
    #: deceptive foundation.
    OBJECTIVE_ORDER = (
        "structural_validity",      # compiles + ISR-valid (build nothing on rubble)
        "causal_validity",          # delta is genuinely causal (no forged evidence)
        "invariant_compliance",     # identity/protected invariants intact (no deception)
        "regression_safety",        # no regression against the known-good baseline
        "correctness",              # resolves the observed failure
        "complexity_efficiency",    # Occam, last
    )

    def select(self, candidates: list[ScoredCandidate]) -> Optional[ScoredCandidate]:
        if not candidates:
            return None

        def key(s):
            fitness = dict(s.fitness.objectives)
            return (
                tuple(-fitness.get(name, 0.0) for name in self.OBJECTIVE_ORDER),
                s.candidate.candidate_id,
            )

        return min(candidates, key=key)


def score_candidate(
    sandbox: "RealBackendSandbox",
    gate: CandidateGate,
    candidate: MutationCandidate,
    baseline_artifact: CompiledCandidate,
    baseline_run: TestRunResult,
    observation: FailureObservation,
    broken_isr: ISR,
    broken_artifact: CompiledCandidate,
    broken_run: TestRunResult,
    broken_artifact_hash: str,
    protected_invariants: tuple,
) -> ScoredCandidate:
    """Score one candidate through the R2.5/R2.8 evaluation boundary.

    Shared by every coordinator (R2.6 competitive ensemble, R2.9.2 autonomous
    variation) so no search strategy can bypass the boundary: compile + run
    exactly once per candidate, gate, fitness, feasibility.
    """
    is_identity = stable_isr_hash(candidate.candidate_isr) == stable_isr_hash(broken_isr)
    if is_identity:
        # NullMutation: candidate IS the broken ISR; reuse its artifact/run.
        cand_artifact = broken_artifact
        cand_run = broken_run
        indep_hash = broken_artifact_hash
    else:
        cand_artifact = sandbox.build(
            candidate.candidate_isr, workspace=tempfile.mkdtemp(prefix="r26-cand-")
        )
        cand_run = sandbox.run_tests(cand_artifact)
        indep_hash = hash_artifact(
            sandbox.build(
                candidate.candidate_isr,
                workspace=tempfile.mkdtemp(prefix="r26-recomp-"),
            ).source_root
        )

    ctx = GateContext(
        candidate_isr=candidate.candidate_isr,
        candidate_artifact=cand_artifact,
        candidate_run=cand_run,
        baseline_artifact=baseline_artifact,
        baseline_run=baseline_run,
        observation=observation,
        mutation=candidate,
        parent_isr=candidate.parent_isr,
        protected_invariants=protected_invariants,
        broken_artifact=broken_artifact,
        broken_artifact_hash=broken_artifact_hash,
        independent_recompile_hash=indep_hash,
    )
    verdict: CandidateVerdict = gate.evaluate(ctx)
    fitness = compute_fitness(verdict, candidate)
    return ScoredCandidate(candidate, verdict, fitness, verdict.accept)


class CompetitiveEvolutionCoordinator:
    """Runs one competitive-evolution round over an ensemble of operators.

    The coordinator owns compile/run/plumb (the R2.5 gate stays a pure evaluator
    over a pre-populated ``GateContext``). The broken artifact/run are reused for
    the identity (null) candidate, which is semantically identical to the broken
    ISR -- avoiding a redundant Docker run while remaining evidence-faithful.
    """

    def __init__(
        self,
        sandbox: "RealBackendSandbox",
        gate: CandidateGate,
        operators: tuple,
        selection: SelectionStrategy,
        ledger: Optional[EvolutionLedger] = None,
    ):
        self._sandbox = sandbox
        self._gate = gate
        self._operators = operators
        self._selection = selection
        self._ledger = ledger

    def _score(
        self,
        candidate: MutationCandidate,
        baseline_artifact: CompiledCandidate,
        baseline_run: TestRunResult,
        observation: FailureObservation,
        broken_isr: ISR,
        broken_artifact: CompiledCandidate,
        broken_run: TestRunResult,
        broken_artifact_hash: str,
        protected_invariants: tuple,
    ) -> ScoredCandidate:
        return score_candidate(
            self._sandbox, self._gate, candidate, baseline_artifact,
            baseline_run, observation, broken_isr, broken_artifact,
            broken_run, broken_artifact_hash, protected_invariants,
        )

    def run(
        self,
        broken_isr: ISR,
        broken_artifact: CompiledCandidate,
        broken_run: TestRunResult,
        baseline_isr: ISR,
        baseline_artifact: CompiledCandidate,
        baseline_run: TestRunResult,
        observation: FailureObservation,
        protected_invariants: tuple = (),
    ) -> SelectionDecision:
        broken_artifact_hash = hash_artifact(broken_artifact.source_root)

        # 1. candidate generation (de-duplicated by candidate_id)
        candidates: list[MutationCandidate] = []
        for op in self._operators:
            proposed = op.propose(broken_isr, observation)
            if proposed is None:
                continue
            if any(c.candidate_id == proposed.candidate_id for c in candidates):
                continue
            candidates.append(proposed)

        # 2. evaluate each candidate through the frontier (compile+run once)
        scored = [
            self._score(
                cand, baseline_artifact, baseline_run, observation,
                broken_isr, broken_artifact, broken_run, broken_artifact_hash,
                protected_invariants,
            )
            for cand in candidates
        ]

        # 3. Pareto frontier over feasible candidates
        frontier = pareto_frontier(scored)
        frontier_ids = tuple(c.candidate.candidate_id for c in frontier)

        # 4. selection (replaceable strategy)
        selected = self._selection.select(frontier)
        selected_id = selected.candidate.candidate_id if selected else None
        selected_is_feasible = selected is not None and selected.feasible

        if not scored:
            rationale = "no operators proposed any candidate"
        elif selected_is_feasible:
            rationale = (
                f"selected {selected_id} from a {len(frontier)}-member Pareto "
                f"frontier of {len(scored)} evaluated candidates"
            )
        else:
            rationale = (
                f"rejected all {len(scored)} candidates; Pareto frontier empty "
                f"after filtering infeasible candidates"
            )

        decision = SelectionDecision(
            selected_candidate_id=selected_id,
            candidates=tuple(scored),
            pareto_frontier_ids=frontier_ids,
            rationale=rationale,
        )

        # 5. record the decision (every candidate's verdict + fitness) on the ledger
        if self._ledger is not None:
            self._ledger.append_selection(decision.to_dict())

        return decision
