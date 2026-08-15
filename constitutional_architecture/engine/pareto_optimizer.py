"""
Pareto Optimizer.

Multi-objective optimisation using Pareto dominance.
Maintains the Pareto front of non-dominated architectures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.individual import Individual


@dataclass(frozen=True)
class ParetoFront:
    individuals: tuple[Individual, ...] = ()
    generation: int = 0

    @property
    def size(self) -> int:
        return len(self.individuals)

    def contains(self, individual_id: str) -> bool:
        return any(ind.id == individual_id for ind in self.individuals)


class ParetoOptimizer:
    COMPOSITE_OBJECTIVES: dict[str, tuple[str, ...]] = {
        "structural_quality": ("complexity", "coupling", "cohesion", "maintainability", "extensibility"),
        "operational_quality": ("reliability", "scalability", "observability"),
        "security_compliance": ("security_coverage", "deployment_completeness"),
        "knowledge_quality": ("documentation", "architecture_quality"),
    }

    def __init__(self, use_composite: bool = True) -> None:
        self._use_composite = use_composite
        self._history: list[ParetoFront] = []

    def compute_front(self, population: list[Individual], generation: int = 0) -> ParetoFront:
        if not population:
            return ParetoFront(generation=generation)

        if self._use_composite:
            reduced = [
                (ind, self._reduce_fitness(ind.fitness))
                for ind in population
            ]
            non_dominated = self._fast_non_dominated_sort(reduced)
        else:
            non_dominated = self._fast_non_dominated_sort_full(population)

        front = ParetoFront(individuals=tuple(non_dominated), generation=generation)
        self._history.append(front)
        return front

    def _reduce_fitness(self, fitness: FitnessVector) -> FitnessVector:
        reduced: dict[str, float] = {}
        for obj_name, dims in self.COMPOSITE_OBJECTIVES.items():
            values = [fitness.get(d, 0.0) for d in dims]
            reduced[obj_name] = sum(values) / len(values) if values else 0.0
        return FitnessVector(values=reduced)

    def _fast_non_dominated_sort(
        self,
        individuals: list[tuple[Individual, FitnessVector]],
    ) -> list[Individual]:
        n = len(individuals)
        if n == 0:
            return []

        domination_count: dict[int, int] = {i: 0 for i in range(n)}
        dominated_set: dict[int, list[int]] = {i: [] for i in range(n)}
        front: list[int] = []

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if individuals[i][1].dominates(individuals[j][1]):
                    dominated_set[i].append(j)
                elif individuals[j][1].dominates(individuals[i][1]):
                    domination_count[i] += 1

            if domination_count[i] == 0:
                front.append(i)

        return [individuals[i][0] for i in front]

    def _fast_non_dominated_sort_full(
        self, population: list[Individual]
    ) -> list[Individual]:
        indexed = [(ind, ind.fitness) for ind in population]
        return self._fast_non_dominated_sort(indexed)

    def crowding_distance(self, front: ParetoFront) -> dict[str, float]:
        if front.size <= 2:
            return {ind.id: float("inf") for ind in front.individuals}

        distances: dict[str, float] = {ind.id: 0.0 for ind in front.individuals}
        dimensions = list(front.individuals[0].fitness.values.keys()) if front.individuals else []

        for dim in dimensions:
            sorted_inds = sorted(
                front.individuals,
                key=lambda ind: ind.fitness.get(dim, 0.0),
            )
            distances[sorted_inds[0].id] = float("inf")
            distances[sorted_inds[-1].id] = float("inf")

            f_min = sorted_inds[0].fitness.get(dim, 0.0)
            f_max = sorted_inds[-1].fitness.get(dim, 0.0)
            range_f = f_max - f_min
            if range_f == 0:
                continue

            for i in range(1, len(sorted_inds) - 1):
                prev_val = sorted_inds[i - 1].fitness.get(dim, 0.0)
                next_val = sorted_inds[i + 1].fitness.get(dim, 0.0)
                distances[sorted_inds[i].id] += (next_val - prev_val) / range_f

        return distances

    @property
    def history(self) -> list[ParetoFront]:
        return list(self._history)

    def select_by_preference(
        self,
        front: ParetoFront,
        preference: str,
    ) -> Optional[Individual]:
        if front.size == 0:
            return None

        preference_map: dict[str, str] = {
            "lowest_cost": "deployment_completeness",
            "highest_scalability": "scalability",
            "highest_maintainability": "maintainability",
            "highest_security": "security_coverage",
            "balanced": "",
        }

        dim = preference_map.get(preference, "")
        if not dim or preference == "balanced":
            return max(front.individuals, key=lambda ind: ind.composite_fitness)

        return max(front.individuals, key=lambda ind: ind.fitness.get(dim, 0.0))
