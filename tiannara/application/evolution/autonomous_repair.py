"""R2.9.2 -- autonomous repair coordinator.

The coordinator runs one autonomous repair round:

    defective ISR + observation
        | population generation (ConstructiveVariationOperator, seeded)
        | score every candidate through the R2.8 boundary (score_candidate:
        |   compile + run once per candidate, gate, fitness, feasibility)
        | filter feasible -> Pareto frontier
        | selection (replaceable strategy, same as R2.6)
        v
    AutonomousRepairResult -> SelectionRecord on the causal ledger

The R2.10 crossover port is carried here (``crossover``, default
``NullCrossover``) so the generation loop can be spliced later without
touching the evaluation boundary. Nothing in this module judges: the
boundary is the R2.6/R2.8 gate stack shared with
``CompetitiveEvolutionCoordinator`` via ``score_candidate``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.isr.model import ISR

from tiannara.application.evolution.candidate_gate import CandidateGate
from tiannara.application.evolution.candidate_sandbox import CompiledCandidate
from tiannara.application.evolution.competitive_evolution import (
    SelectionStrategy,
    pareto_frontier,
    score_candidate,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.evolution.variation import (
    ConstructiveVariationOperator,
    CrossoverOperator,
    NullCrossover,
)
from tiannara.domain.models.evidence import TestRunResult
from tiannara.domain.models.observation import FailureObservation


@dataclass(frozen=True)
class AutonomousRepairResult:
    """The auditable outcome of one autonomous repair round."""

    selected_candidate_id: Optional[str]
    population: tuple
    pareto_frontier_ids: tuple[str, ...]
    rationale: str
    seed: int

    def to_dict(self) -> dict:
        return {
            "selected_candidate_id": self.selected_candidate_id,
            "pareto_frontier_ids": list(self.pareto_frontier_ids),
            "population_size": len(self.population),
            "rationale": self.rationale,
            "seed": self.seed,
            "candidates": [s.to_dict() for s in self.population],
        }

    def content_hash(self) -> str:
        from tiannara.domain.services.canonical import canonical_hash

        return canonical_hash(self.to_dict())


class AutonomousRepairCoordinator:
    """Runs one autonomous repair round over a constructive variation operator."""

    def __init__(
        self,
        sandbox: "RealBackendSandbox",
        gate: CandidateGate,
        variation: ConstructiveVariationOperator,
        selection: SelectionStrategy,
        crossover: CrossoverOperator = None,
        ledger: Optional[EvolutionLedger] = None,
    ):
        self._sandbox = sandbox
        self._gate = gate
        self._variation = variation
        self._selection = selection
        self._crossover = crossover or NullCrossover()
        self._ledger = ledger

    def run(
        self,
        defective_isr: ISR,
        broken_artifact: CompiledCandidate,
        broken_run: TestRunResult,
        baseline_isr: ISR,
        baseline_artifact: CompiledCandidate,
        baseline_run: TestRunResult,
        observation: FailureObservation,
        population_size: int = 8,
        seed: int = 0,
        protected_invariants: tuple = (),
    ) -> AutonomousRepairResult:
        from tiannara.application.evolution.compiler_sandbox import hash_artifact

        broken_artifact_hash = hash_artifact(broken_artifact.source_root)

        # 1. population generation (deterministic under (ISR, observation, seed))
        population = self._variation.generate(
            defective_isr, observation, population_size, seed
        )

        # 2. score every candidate through the R2.8 boundary
        scored = [
            score_candidate(
                self._sandbox, self._gate, cand, baseline_artifact,
                baseline_run, observation, defective_isr, broken_artifact,
                broken_run, broken_artifact_hash, protected_invariants,
            )
            for cand in population
        ]

        # 3. Pareto frontier over feasible candidates
        frontier = pareto_frontier(list(scored))
        frontier_ids = tuple(c.candidate.candidate_id for c in frontier)

        # 4. selection (replaceable strategy)
        selected = self._selection.select(frontier)
        selected_id = selected.candidate.candidate_id if selected else None
        selected_is_feasible = selected is not None and selected.feasible

        if not scored:
            rationale = "variation proposed no candidates"
        elif selected_is_feasible:
            rationale = (
                f"selected {selected_id} from a {len(frontier)}-member Pareto "
                f"frontier of {len(scored)} evaluated candidates (seed={seed})"
            )
        else:
            rationale = (
                f"rejected all {len(scored)} candidates; Pareto frontier empty "
                f"after filtering infeasible candidates"
            )

        result = AutonomousRepairResult(
            selected_candidate_id=selected_id,
            population=tuple(scored),
            pareto_frontier_ids=frontier_ids,
            rationale=rationale,
            seed=seed,
        )

        # 5. record the decision on the causal ledger (same chain as R2.6)
        if self._ledger is not None:
            self._ledger.append_selection(result.to_dict())

        return result