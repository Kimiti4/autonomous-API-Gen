"""
Strategy Optimizer.

Optimizes mutation strategies based on historical performance.
"""

from __future__ import annotations

from constitutional_architecture.meta.platform_genome import PlatformGenome
from constitutional_architecture.meta.platform_mutation import PlatformMutator


class StrategyOptimizer:
    def __init__(self, mutator: PlatformMutator) -> None:
        self._mutator = mutator

    def optimize_mutation_rates(self, genome: PlatformGenome) -> dict[str, float]:
        success_rates = self._mutator.success_rates
        recommendations: dict[str, float] = {}
        for param in genome.get_mutable_parameters():
            current_rate = param.mutation_rate
            success = success_rates.get(param.id, 0.5)
            if success > 0.6:
                recommendations[param.id] = min(current_rate * 1.2, 0.5)
            elif success < 0.3:
                recommendations[param.id] = max(current_rate * 0.8, 0.01)
            else:
                recommendations[param.id] = current_rate
        return recommendations

    def recommend_strategy(self, genome: PlatformGenome) -> str:
        success_rates = self._mutator.success_rates
        if not success_rates:
            return "random"
        avg_success = sum(success_rates.values()) / len(success_rates)
        if avg_success > 0.6:
            return "adaptive"
        elif avg_success < 0.3:
            return "random"
        else:
            return "guided"
