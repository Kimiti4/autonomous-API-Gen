import pytest

from constitutional_architecture.core.evolution.pareto import (
    SystemParetoIntegration, UnifiedEvolutionaryCandidate,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import QualityAttribute
from constitutional_architecture.meta.genome.chromosomes import FrontendGenome


class TestUnifiedEvolutionaryCandidate:
    def test_combined_score_system_only(self):
        cand = UnifiedEvolutionaryCandidate(
            architecture_genome=ArchitectureGenome(),
            frontend_genome=FrontendGenome(),
            system_scores={QualityAttribute.SECURITY: 0.8, QualityAttribute.SCALABILITY: 0.6},
            frontend_score=0.0,
        )
        assert 0.0 < cand.combined_score < 1.0

    def test_combined_score_full(self):
        cand = UnifiedEvolutionaryCandidate(
            architecture_genome=ArchitectureGenome(),
            frontend_genome=FrontendGenome(),
            system_scores={QualityAttribute.SECURITY: 1.0, QualityAttribute.SCALABILITY: 1.0},
            frontend_score=1.0,
        )
        assert cand.combined_score == 1.0

    def test_combined_score_zero(self):
        cand = UnifiedEvolutionaryCandidate(
            architecture_genome=ArchitectureGenome(),
            frontend_genome=FrontendGenome(),
            system_scores={},
            frontend_score=0.0,
        )
        assert cand.combined_score == 0.0

    def test_default_values(self):
        cand = UnifiedEvolutionaryCandidate(
            architecture_genome=ArchitectureGenome(),
            frontend_genome=FrontendGenome(),
        )
        assert cand.system_scores == {}
        assert cand.frontend_score == 0.0
        assert cand.pareto_rank == 0
        assert cand.crowding_distance == 0.0


class TestSystemParetoIntegration:
    def test_evaluate_candidate(self):
        arch = ArchitectureGenome()
        front = FrontendGenome()
        integration = SystemParetoIntegration()
        cand = integration.evaluate_candidate(arch, front)
        assert isinstance(cand, UnifiedEvolutionaryCandidate)
        assert len(cand.system_scores) == len(list(QualityAttribute))
