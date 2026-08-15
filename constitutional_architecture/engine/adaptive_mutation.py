"""
Adaptive Mutation.

Learns which mutations improve architectures and adjusts
mutation probabilities over time. Learning survives process restarts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.isr.eir.taxonomy import MutationCategory


@dataclass
class OperatorStats:
    applications: int = 0
    acceptances: int = 0
    rejections: int = 0
    mean_fitness_delta: float = 0.0
    variance: float = 0.0
    weight: float = 1.0
    last_applied_generation: int = 0
    _sum_delta: float = 0.0
    _sum_delta_sq: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.applications == 0:
            return 0.0
        return self.acceptances / self.applications

    def record(self, accepted: bool, fitness_delta: float, generation: int) -> None:
        self.applications += 1
        if accepted:
            self.acceptances += 1
        else:
            self.rejections += 1
        self._sum_delta += fitness_delta
        self._sum_delta_sq += fitness_delta ** 2
        self.mean_fitness_delta = self._sum_delta / self.applications
        self.variance = (self._sum_delta_sq / self.applications) - (self.mean_fitness_delta ** 2)
        self.last_applied_generation = generation


@dataclass
class MutationSequence:
    operator_ids: tuple[str, ...] = ()
    fitness_delta: float = 0.0
    success: bool = False
    generation: int = 0


class AdaptiveMutation:
    """
    Adaptive mutation probability management.

    Learns:
    - Which mutations improve architectures
    - Which combinations are successful
    - Mutation success rates
    - Domain-specific preferences
    - Architecture pattern effectiveness

    Continuously updates mutation weights based on evidence.
    """

    def __init__(self, config: EvolutionConfig) -> None:
        self._config = config
        self._operator_stats: dict[str, OperatorStats] = {}
        self._category_stats: dict[str, OperatorStats] = {}
        self._successful_sequences: list[MutationSequence] = []
        self._failed_sequences: list[MutationSequence] = []
        self._compatibility: dict[tuple[str, str], float] = {}

    def register_operator(self, operator_id: str, initial_weight: float = 1.0) -> None:
        self._operator_stats[operator_id] = OperatorStats(weight=initial_weight)

    def record_result(
        self,
        operator_id: str,
        accepted: bool,
        fitness_delta: float,
        generation: int,
        category: Optional[str] = None,
    ) -> None:
        if operator_id not in self._operator_stats:
            self.register_operator(operator_id)

        self._operator_stats[operator_id].record(accepted, fitness_delta, generation)

        if category:
            if category not in self._category_stats:
                self._category_stats[category] = OperatorStats()
            self._category_stats[category].record(accepted, fitness_delta, generation)

    def record_sequence(
        self,
        operator_ids: list[str],
        fitness_delta: float,
        success: bool,
        generation: int,
    ) -> None:
        seq = MutationSequence(
            operator_ids=tuple(operator_ids),
            fitness_delta=fitness_delta,
            success=success,
            generation=generation,
        )
        if success:
            self._successful_sequences.append(seq)
        else:
            self._failed_sequences.append(seq)

        for i in range(len(operator_ids) - 1):
            pair = (operator_ids[i], operator_ids[i + 1])
            current = self._compatibility.get(pair, 0.5)
            update = 0.1 if success else -0.1
            self._compatibility[pair] = max(0.0, min(1.0, current + update))

    def get_weights(self) -> dict[str, float]:
        weights: dict[str, float] = {}
        baseline_rate = 0.5

        for op_id, stats in self._operator_stats.items():
            if stats.applications < 5:
                weights[op_id] = stats.weight
                continue

            lr = self._config.adaptive_learning_rate
            adjustment = 1.0 + lr * (stats.success_rate - baseline_rate)
            new_weight = stats.weight * adjustment

            new_weight = max(self._config.adaptive_min_weight, new_weight)
            new_weight = min(self._config.adaptive_max_weight, new_weight)

            stats.weight = new_weight
            weights[op_id] = new_weight

        return weights

    def get_compatibility(self, op_a: str, op_b: str) -> float:
        return self._compatibility.get((op_a, op_b), 0.5)

    def get_best_sequences(self, n: int = 10) -> list[MutationSequence]:
        sorted_seqs = sorted(
            self._successful_sequences,
            key=lambda s: s.fitness_delta,
            reverse=True,
        )
        return sorted_seqs[:n]

    def save(self, path: str | Path) -> None:
        data = {
            "operator_stats": {
                op_id: {
                    "applications": s.applications,
                    "acceptances": s.acceptances,
                    "rejections": s.rejections,
                    "mean_fitness_delta": s.mean_fitness_delta,
                    "weight": s.weight,
                }
                for op_id, s in self._operator_stats.items()
            },
            "successful_sequences": [
                {"operators": list(s.operator_ids), "delta": s.fitness_delta}
                for s in self._successful_sequences[-100:]
            ],
            "compatibility": {
                f"{k[0]}|{k[1]}": v for k, v in self._compatibility.items()
            },
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: str | Path) -> None:
        p = Path(path)
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8"))
        for op_id, stats_data in data.get("operator_stats", {}).items():
            self._operator_stats[op_id] = OperatorStats(
                applications=stats_data.get("applications", 0),
                acceptances=stats_data.get("acceptances", 0),
                rejections=stats_data.get("rejections", 0),
                mean_fitness_delta=stats_data.get("mean_fitness_delta", 0.0),
                weight=stats_data.get("weight", 1.0),
            )
