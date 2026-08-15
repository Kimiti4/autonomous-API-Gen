"""
Convergence Detector.

Detects when evolution has stagnated and triggers diversification.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.engine.config import EvolutionConfig


@dataclass(frozen=True)
class ConvergenceStatus:
    is_converged: bool = False
    is_stagnant: bool = False
    generations_since_improvement: int = 0
    fitness_variance: float = 0.0
    improvement_rate: float = 0.0
    recommendation: str = ""


class ConvergenceDetector:
    """
    Detects premature convergence and stagnation.

    Monitors:
    - Fitness improvement rate over a sliding window
    - Population fitness variance
    - Generations since last improvement

    Triggers diversification when convergence is detected.
    """

    def __init__(self, config: EvolutionConfig) -> None:
        self._config = config
        self._fitness_history: deque[float] = deque(maxlen=config.convergence_window)
        self._best_history: deque[float] = deque(maxlen=config.stagnation_limit)
        self._generations_since_improvement: int = 0
        self._previous_best: float = 0.0

    def update(self, mean_fitness: float, best_fitness: float) -> ConvergenceStatus:
        self._fitness_history.append(mean_fitness)
        self._best_history.append(best_fitness)

        if best_fitness > self._previous_best + self._config.convergence_threshold:
            self._generations_since_improvement = 0
        else:
            self._generations_since_improvement += 1
        self._previous_best = best_fitness

        variance = self._compute_variance()
        improvement_rate = self._compute_improvement_rate()

        is_converged = variance < self._config.convergence_threshold
        is_stagnant = self._generations_since_improvement >= self._config.stagnation_limit

        recommendation = ""
        if is_stagnant:
            recommendation = "diversify"
        elif is_converged:
            recommendation = "increase_mutation_rate"
        else:
            recommendation = "continue"

        return ConvergenceStatus(
            is_converged=is_converged,
            is_stagnant=is_stagnant,
            generations_since_improvement=self._generations_since_improvement,
            fitness_variance=variance,
            improvement_rate=improvement_rate,
            recommendation=recommendation,
        )

    def _compute_variance(self) -> float:
        if len(self._fitness_history) < 2:
            return 1.0
        values = list(self._fitness_history)
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)

    def _compute_improvement_rate(self) -> float:
        if len(self._fitness_history) < 2:
            return 0.0
        values = list(self._fitness_history)
        return (values[-1] - values[0]) / len(values)

    def reset(self) -> None:
        self._fitness_history.clear()
        self._best_history.clear()
        self._generations_since_improvement = 0
