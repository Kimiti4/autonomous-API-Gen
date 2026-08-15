"""
Elite Manager.

Preserves the best architectures across generations.
Elites are never lost to selection pressure.
"""

from __future__ import annotations

from typing import Optional

from constitutional_architecture.engine.individual import Individual


class EliteManager:
    """
    Manages elite preservation across generations.

    The top N individuals (by composite fitness or Pareto rank)
    are preserved unchanged into the next generation.
    """

    def __init__(self, elite_count: int = 5) -> None:
        self._elite_count = elite_count
        self._elites: list[Individual] = []
        self._historical_best: Optional[Individual] = None

    @property
    def elites(self) -> list[Individual]:
        return list(self._elites)

    @property
    def historical_best(self) -> Optional[Individual]:
        return self._historical_best

    def update(self, population: list[Individual]) -> list[Individual]:
        sorted_pop = sorted(population, key=lambda ind: ind.composite_fitness, reverse=True)
        self._elites = [ind.with_elite(True) for ind in sorted_pop[:self._elite_count]]

        if self._elites:
            best = self._elites[0]
            if self._historical_best is None or best.composite_fitness > self._historical_best.composite_fitness:
                self._historical_best = best

        return self._elites

    def inject(self, population: list[Individual]) -> list[Individual]:
        if not self._elites:
            return population

        sorted_pop = sorted(population, key=lambda ind: ind.composite_fitness)

        result = list(sorted_pop)
        for i, elite in enumerate(self._elites):
            if i < len(result):
                result[i] = elite
            else:
                result.append(elite)

        return result

    @property
    def best_fitness_ever(self) -> float:
        if self._historical_best is None:
            return 0.0
        return self._historical_best.composite_fitness
