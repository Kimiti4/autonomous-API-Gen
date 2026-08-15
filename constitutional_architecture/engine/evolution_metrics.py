"""
Evolution Metrics.

Continuously measures evolution performance and population health.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.engine.population_manager import PopulationStats


@dataclass
class GenerationMetrics:
    generation: int = 0
    population_size: int = 0
    mean_fitness: float = 0.0
    max_fitness: float = 0.0
    min_fitness: float = 0.0
    diversity: float = 0.0
    entropy: float = 0.0
    mutation_success_rate: float = 0.0
    crossover_count: int = 0
    mutation_count: int = 0
    novel_architectures: int = 0
    species_count: int = 0
    convergence_status: str = ""
    generation_time_ms: float = 0.0


@dataclass
class EvolutionMetrics:
    total_generations: int = 0
    total_mutations: int = 0
    total_crossovers: int = 0
    total_mutation_successes: int = 0
    total_mutation_failures: int = 0
    best_fitness_ever: float = 0.0
    mean_fitness_trend: list[float] = field(default_factory=list)
    max_fitness_trend: list[float] = field(default_factory=list)
    diversity_trend: list[float] = field(default_factory=list)
    generation_history: list[GenerationMetrics] = field(default_factory=list)

    @property
    def overall_mutation_success_rate(self) -> float:
        total = self.total_mutation_successes + self.total_mutation_failures
        return self.total_mutation_successes / total if total > 0 else 0.0

    @property
    def fitness_improvement(self) -> float:
        if len(self.max_fitness_trend) < 2:
            return 0.0
        return self.max_fitness_trend[-1] - self.max_fitness_trend[0]


class MetricsCollector:
    def __init__(self, history_window: int = 1000) -> None:
        self._metrics = EvolutionMetrics()
        self._window = history_window

    @property
    def metrics(self) -> EvolutionMetrics:
        return self._metrics

    def record_generation(
        self,
        gen_metrics: GenerationMetrics,
        pop_stats: PopulationStats,
    ) -> None:
        self._metrics.total_generations += 1
        self._metrics.generation_history.append(gen_metrics)

        if len(self._metrics.generation_history) > self._window:
            self._metrics.generation_history = self._metrics.generation_history[-self._window:]

        self._metrics.mean_fitness_trend.append(pop_stats.mean_fitness)
        self._metrics.max_fitness_trend.append(pop_stats.max_fitness)

        if pop_stats.max_fitness > self._metrics.best_fitness_ever:
            self._metrics.best_fitness_ever = pop_stats.max_fitness

    def record_mutation(self, success: bool) -> None:
        self._metrics.total_mutations += 1
        if success:
            self._metrics.total_mutation_successes += 1
        else:
            self._metrics.total_mutation_failures += 1

    def record_crossover(self) -> None:
        self._metrics.total_crossovers += 1

    def summary(self) -> dict[str, float]:
        return {
            "total_generations": float(self._metrics.total_generations),
            "total_mutations": float(self._metrics.total_mutations),
            "mutation_success_rate": self._metrics.overall_mutation_success_rate,
            "best_fitness_ever": self._metrics.best_fitness_ever,
            "fitness_improvement": self._metrics.fitness_improvement,
        }
