"""Multi-objective fitness and Pareto selection for full-stack evolution."""
from __future__ import annotations
from dataclasses import dataclass
from .fullstack_population import GenomeIndividual


@dataclass(frozen=True)
class Fitness:
    correctness: float
    security: float
    performance: float
    resilience: float
    accessibility: float
    maintainability: float

    def values(self) -> tuple[float, ...]:
        return (
            self.correctness, self.security, self.performance,
            self.resilience, self.accessibility, self.maintainability,
        )


@dataclass(frozen=True)
class EvaluatedIndividual:
    individual: GenomeIndividual
    fitness: Fitness
    evidence: tuple[str, ...]


def dominates(a: Fitness, b: Fitness) -> bool:
    av, bv = a.values(), b.values()
    return all(x >= y for x, y in zip(av, bv)) and any(x > y for x, y in zip(av, bv))


def pareto_front(
    individuals: tuple[EvaluatedIndividual, ...],
) -> tuple[EvaluatedIndividual, ...]:
    return tuple(
        candidate for candidate in individuals
        if not any(
            other is not candidate and dominates(other.fitness, candidate.fitness)
            for other in individuals
        )
    )


def select_pareto(
    individuals: tuple[EvaluatedIndividual, ...],
    limit: int,
) -> tuple[EvaluatedIndividual, ...]:
    if limit < 1:
        raise ValueError("limit-must-be-positive")
    front = pareto_front(individuals)
    return front[:limit]


def fitness_is_valid(fitness: Fitness) -> bool:
    return all(0.0 <= x <= 1.0 for x in fitness.values())
