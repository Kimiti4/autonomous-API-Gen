"""
Population Manager.

Manages the evolutionary population of ISR architectures.
Handles creation, selection, replacement, and aging.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.individual import Individual
from constitutional_architecture.isr.model.isr import ISR


@dataclass
class PopulationStats:
    size: int = 0
    generation: int = 0
    mean_fitness: float = 0.0
    max_fitness: float = 0.0
    min_fitness: float = 0.0
    diversity: float = 0.0
    species_count: int = 0
    elite_count: int = 0


class PopulationManager:
    """
    Manages the evolutionary population.

    Responsibilities:
    - Population initialisation
    - Individual creation
    - Selection (tournament, roulette, rank)
    - Replacement
    - Aging
    - Statistics
    """

    def __init__(self, config: EvolutionConfig, rng: Optional[random.Random] = None) -> None:
        self._config = config
        self._rng = rng or random.Random(config.seed)
        self._population: list[Individual] = []
        self._generation: int = 0

    @property
    def population(self) -> list[Individual]:
        return list(self._population)

    @property
    def size(self) -> int:
        return len(self._population)

    @property
    def generation(self) -> int:
        return self._generation

    def initialise(self, seed_isr: ISR) -> None:
        self._population = []
        for i in range(self._config.population_size):
            individual = Individual(
                id=f"ind-{uuid.uuid4().hex[:12]}",
                isr=seed_isr,
                fitness=FitnessVector.zero(self._config.fitness_dimensions),
                generation=0,
                age=0,
            )
            self._population.append(individual)
        self._generation = 0

    def set_population(self, individuals: list[Individual]) -> None:
        self._population = list(individuals)

    def add(self, individual: Individual) -> None:
        self._population.append(individual)

    def advance_generation(self) -> None:
        self._generation += 1
        self._population = [ind.with_age(ind.age + 1) for ind in self._population]

    def select_tournament(self, k: Optional[int] = None) -> Individual:
        k = k or self._config.tournament_size
        k = min(k, len(self._population))
        contestants = self._rng.sample(self._population, k)
        return max(contestants, key=lambda ind: ind.composite_fitness)

    def select_roulette(self) -> Individual:
        fitnesses = [max(ind.composite_fitness, 0.001) for ind in self._population]
        total = sum(fitnesses)
        if total == 0:
            return self._rng.choice(self._population)
        r = self._rng.uniform(0, total)
        cumulative = 0.0
        for ind, fit in zip(self._population, fitnesses):
            cumulative += fit
            if cumulative >= r:
                return ind
        return self._population[-1]

    def select_rank(self) -> Individual:
        sorted_pop = sorted(self._population, key=lambda ind: ind.composite_fitness)
        n = len(sorted_pop)
        ranks = list(range(1, n + 1))
        total_rank = sum(ranks)
        r = self._rng.uniform(0, total_rank)
        cumulative = 0.0
        for ind, rank in zip(sorted_pop, ranks):
            cumulative += rank
            if cumulative >= r:
                return ind
        return sorted_pop[-1]

    def select(self) -> Individual:
        if self._config.selection_algorithm == "tournament":
            return self.select_tournament()
        elif self._config.selection_algorithm == "roulette":
            return self.select_roulette()
        elif self._config.selection_algorithm == "rank":
            return self.select_rank()
        return self.select_tournament()

    def select_pair(self) -> tuple[Individual, Individual]:
        if len(self._population) < 2:
            raise ValueError("Population too small for pair selection")
        a = self.select()
        b = self.select()
        attempts = 0
        while b.id == a.id and attempts < 10:
            b = self.select()
            attempts += 1
        return a, b

    def get_best(self, n: int = 1) -> list[Individual]:
        sorted_pop = sorted(self._population, key=lambda ind: ind.composite_fitness, reverse=True)
        return sorted_pop[:n]

    def get_worst(self, n: int = 1) -> list[Individual]:
        sorted_pop = sorted(self._population, key=lambda ind: ind.composite_fitness)
        return sorted_pop[:n]

    def get_elites(self) -> list[Individual]:
        return [ind for ind in self._population if ind.is_elite]

    def replace(self, old_id: str, new_individual: Individual) -> None:
        self._population = [
            new_individual if ind.id == old_id else ind
            for ind in self._population
        ]

    def stats(self) -> PopulationStats:
        if not self._population:
            return PopulationStats()

        fitnesses = [ind.composite_fitness for ind in self._population]
        species = set(ind.species_id for ind in self._population if ind.species_id)

        return PopulationStats(
            size=len(self._population),
            generation=self._generation,
            mean_fitness=sum(fitnesses) / len(fitnesses),
            max_fitness=max(fitnesses),
            min_fitness=min(fitnesses),
            species_count=len(species),
            elite_count=sum(1 for ind in self._population if ind.is_elite),
        )
