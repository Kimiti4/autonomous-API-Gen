import random

import pytest

from constitutional_architecture.core.evolution.fitness import SystemFitnessEvaluator
from constitutional_architecture.core.evolution.operators import GenomeMutator, MutationEvent
from constitutional_architecture.core.models.genome import (
    ApplicationArchitecture, ArchitectureGenome,
)
from constitutional_architecture.core.models.intent import QualityAttribute


class TestGenomeMutator:
    def test_mutate_returns_clone(self):
        g = ArchitectureGenome()
        mutator = GenomeMutator()
        result = mutator.mutate(g, rate=0.0)
        assert isinstance(result, ArchitectureGenome)
        assert result is not g

    def test_mutate_zero_rate(self):
        g = ArchitectureGenome()
        old = g.serialize()
        mutator = GenomeMutator()
        result = mutator.mutate(g, rate=0.0)
        assert result.serialize() == old

    def test_mutate_high_rate(self):
        g = ArchitectureGenome()
        mutator = GenomeMutator(rng=random.Random(42))
        result = mutator.mutate(g, rate=1.0)
        old_app = g.get_gene("app_arch")
        new_app = result.get_gene("app_arch")
        assert old_app != new_app

    def test_mutate_history(self):
        g = ArchitectureGenome()
        mutator = GenomeMutator(rng=random.Random(42))
        mutator.mutate(g, rate=1.0)
        assert len(mutator.history) > 0
        event = mutator.history[0]
        assert isinstance(event, MutationEvent)
        assert event.gene_id in g.categorical_genes or event.gene_id in g.continuous_genes

    def test_clear_history(self):
        g = ArchitectureGenome()
        mutator = GenomeMutator(rng=random.Random(99))
        mutator.mutate(g, rate=1.0)
        assert len(mutator.history) > 0
        mutator.clear_history()
        assert len(mutator.history) == 0

    def test_mutate_weighted_respects_weights(self):
        g = ArchitectureGenome()
        mutator = GenomeMutator(rng=random.Random(42))
        result = mutator.mutate_weighted(g, {"app_arch": 0.0, "data_arch": 1.0})
        assert result.get_gene("app_arch") == g.get_gene("app_arch")
        assert result.get_gene("data_arch") != g.get_gene("data_arch")


class TestSystemFitnessEvaluator:
    def test_evaluate_returns_all_attributes(self):
        g = ArchitectureGenome()
        evaluator = SystemFitnessEvaluator()
        scores = evaluator.evaluate(g)
        for qa in QualityAttribute:
            assert qa in scores

    def test_scores_are_between_zero_and_one(self):
        g = ArchitectureGenome()
        evaluator = SystemFitnessEvaluator()
        scores = evaluator.evaluate(g)
        for qa, score in scores.items():
            assert 0.0 <= score <= 1.0, f"{qa}: {score}"

    def test_evaluate_weighted(self):
        g = ArchitectureGenome()
        evaluator = SystemFitnessEvaluator()
        weights = {QualityAttribute.SCALABILITY: 0.8, QualityAttribute.SECURITY: 0.2}
        score = evaluator.evaluate_weighted(g, weights)
        assert 0.0 <= score <= 1.0

    def test_evaluate_weighted_handles_empty(self):
        g = ArchitectureGenome()
        evaluator = SystemFitnessEvaluator()
        score = evaluator.evaluate_weighted(g, {})
        assert score == 0.0

    def test_scalability_microservices_scores_high(self):
        g = ArchitectureGenome()
        g.set_gene("app_arch", ApplicationArchitecture.MICROSERVICES)
        g.set_gene("data_arch", "database_per_service")
        g.set_gene("deployment_topology", "multi_region")
        evaluator = SystemFitnessEvaluator()
        scores = evaluator.evaluate(g)
        assert scores[QualityAttribute.SCALABILITY] > 0.5

    def test_scalability_monolithic_scores_low(self):
        g = ArchitectureGenome()
        g.set_gene("app_arch", ApplicationArchitecture.MONOLITHIC)
        g.set_gene("data_arch", "single_database")
        g.set_gene("deployment_topology", "single_region")
        evaluator = SystemFitnessEvaluator()
        scores = evaluator.evaluate(g)
        assert scores[QualityAttribute.SCALABILITY] < 0.5
