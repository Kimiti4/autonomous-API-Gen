from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from constitutional_architecture.core.evolution.fitness import SystemFitnessEvaluator
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import QualityAttribute
from constitutional_architecture.meta.genome.chromosomes import FrontendGenome
from constitutional_architecture.meta.genome.evolution.pareto_coordinator import (
    ParetoEvolutionCoordinator, Candidate,
)


@dataclass
class UnifiedEvolutionaryCandidate:
    architecture_genome: ArchitectureGenome
    frontend_genome: FrontendGenome
    system_scores: Dict[QualityAttribute, float] = field(default_factory=dict)
    frontend_score: float = 0.0
    pareto_rank: int = 0
    crowding_distance: float = 0.0

    @property
    def combined_score(self) -> float:
        system_avg = sum(self.system_scores.values()) / max(1, len(self.system_scores))
        return (system_avg + self.frontend_score) / 2.0


class SystemParetoIntegration:
    """Bridges system-level ArchitectureGenome scores with frontend Pareto coordinator."""

    def __init__(self, pareto_coordinator: Optional[ParetoEvolutionCoordinator] = None,
                 system_evaluator: Optional[SystemFitnessEvaluator] = None) -> None:
        self._pareto = pareto_coordinator or ParetoEvolutionCoordinator()
        self._system_evaluator = system_evaluator or SystemFitnessEvaluator()

    def evaluate_candidate(self, arch_genome: ArchitectureGenome,
                           frontend_genome: FrontendGenome) -> UnifiedEvolutionaryCandidate:
        system_scores = self._system_evaluator.evaluate(arch_genome)
        return UnifiedEvolutionaryCandidate(
            architecture_genome=arch_genome,
            frontend_genome=frontend_genome,
            system_scores=system_scores,
            frontend_score=0.5,
        )

    def rank_candidates(self, candidates: List[UnifiedEvolutionaryCandidate]) -> List[UnifiedEvolutionaryCandidate]:
        scored = sorted(candidates, key=lambda c: c.combined_score, reverse=True)
        for rank, cand in enumerate(scored):
            cand.pareto_rank = rank
        return scored
