"""
Fitness Vector.

Multi-dimensional fitness representation for evolved architectures.
Supports Pareto dominance, distance computation, and composite scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FitnessVector:
    """
    Multi-dimensional fitness vector for an ISR architecture.

    All dimensions are normalised to [0.0, 1.0] where 1.0 is optimal.
    Supports Pareto dominance comparison for multi-objective optimisation.
    """

    values: dict[str, float] = field(default_factory=dict)

    def get(self, dimension: str, default: float = 0.0) -> float:
        return self.values.get(dimension, default)

    @property
    def dimensions(self) -> list[str]:
        return list(self.values.keys())

    @property
    def dimension_count(self) -> int:
        return len(self.values)

    def dominates(self, other: "FitnessVector") -> bool:
        if set(self.values.keys()) != set(other.values.keys()):
            raise ValueError("Cannot compare fitness vectors with different dimensions")

        at_least_one_better = False
        for dim in self.values:
            if self.values[dim] < other.values[dim]:
                return False
            if self.values[dim] > other.values[dim]:
                at_least_one_better = True
        return at_least_one_better

    def distance(self, other: "FitnessVector") -> float:
        if set(self.values.keys()) != set(other.values.keys()):
            raise ValueError("Cannot compute distance for different dimensions")
        sum_sq = sum(
            (self.values[d] - other.values[d]) ** 2 for d in self.values
        )
        return sum_sq ** 0.5

    def composite_score(self, weights: Optional[dict[str, float]] = None) -> float:
        if not self.values:
            return 0.0
        if weights is None:
            weights = {d: 1.0 for d in self.values}
        total_weight = sum(weights.get(d, 0.0) for d in self.values)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(
            self.values[d] * weights.get(d, 0.0) for d in self.values
        )
        return weighted_sum / total_weight

    def add(self, other: "FitnessVector") -> "FitnessVector":
        return FitnessVector(values={
            d: self.values.get(d, 0.0) + other.values.get(d, 0.0)
            for d in set(self.values) | set(other.values)
        })

    def scale(self, factor: float) -> "FitnessVector":
        return FitnessVector(values={d: v * factor for d, v in self.values.items()})

    def delta(self, other: "FitnessVector") -> "FitnessVector":
        return FitnessVector(values={
            d: self.values.get(d, 0.0) - other.values.get(d, 0.0)
            for d in set(self.values) | set(other.values)
        })

    @staticmethod
    def zero(dimensions: tuple[str, ...]) -> "FitnessVector":
        return FitnessVector(values={d: 0.0 for d in dimensions})

    @staticmethod
    def from_dict(data: dict[str, float]) -> "FitnessVector":
        return FitnessVector(values=dict(data))

    def to_dict(self) -> dict[str, float]:
        return dict(self.values)
