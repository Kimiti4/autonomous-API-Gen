"""Tests for Pareto optimisation."""

import pytest

from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.individual import Individual
from constitutional_architecture.engine.pareto_optimizer import ParetoOptimizer
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System


def _make_individual(fitness_values: dict[str, float], ind_id: str = "test") -> Individual:
    return Individual(
        id=ind_id,
        isr=ISR(system=System(id="s", name="S")),
        fitness=FitnessVector(values=fitness_values),
    )


class TestParetoOptimizer:
    def test_dominance(self):
        a = FitnessVector(values={"x": 0.8, "y": 0.9})
        b = FitnessVector(values={"x": 0.5, "y": 0.6})
        assert a.dominates(b)
        assert not b.dominates(a)

    def test_non_domination(self):
        a = FitnessVector(values={"x": 0.9, "y": 0.3})
        b = FitnessVector(values={"x": 0.3, "y": 0.9})
        assert not a.dominates(b)
        assert not b.dominates(a)

    def test_pareto_front(self):
        optimizer = ParetoOptimizer(use_composite=False)
        population = [
            _make_individual({"structural_quality": 0.9, "operational_quality": 0.3}, "a"),
            _make_individual({"structural_quality": 0.3, "operational_quality": 0.9}, "b"),
            _make_individual({"structural_quality": 0.5, "operational_quality": 0.5}, "c"),
            _make_individual({"structural_quality": 0.2, "operational_quality": 0.2}, "d"),
        ]
        front = optimizer.compute_front(population)
        front_ids = {ind.id for ind in front.individuals}
        assert "d" not in front_ids

    def test_crowding_distance(self):
        optimizer = ParetoOptimizer(use_composite=False)
        population = [
            _make_individual({"x": 1.0, "y": 0.0}, "a"),
            _make_individual({"x": 0.5, "y": 0.5}, "b"),
            _make_individual({"x": 0.0, "y": 1.0}, "c"),
        ]
        front = optimizer.compute_front(population)
        distances = optimizer.crowding_distance(front)
        assert distances.get("a", 0) == float("inf") or distances.get("c", 0) == float("inf")
