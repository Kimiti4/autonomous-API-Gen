"""
Sandbox Evaluator.

Evaluates platform mutations in a sandboxed environment before approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.meta.platform_fitness import PlatformFitness, PlatformFitnessEvaluator
from constitutional_architecture.meta.platform_genome import PlatformGenome


@dataclass(frozen=True)
class SandboxResult:
    genome_id: str
    genome_version: int
    fitness_before: Optional[PlatformFitness] = None
    fitness_after: Optional[PlatformFitness] = None
    fitness_delta: float = 0.0
    passed: bool = False
    duration_seconds: float = 0.0
    errors: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SandboxEvaluator:
    def __init__(
        self,
        fitness_evaluator: Optional[PlatformFitnessEvaluator] = None,
        improvement_threshold: float = 0.0,
        max_degradation: float = 0.05,
    ) -> None:
        self._fitness_evaluator = fitness_evaluator or PlatformFitnessEvaluator()
        self._improvement_threshold = improvement_threshold
        self._max_degradation = max_degradation
        self._results: list[SandboxResult] = []

    def evaluate(
        self,
        current_genome: PlatformGenome,
        proposed_genome: PlatformGenome,
        baseline_metrics: dict[str, Any],
        simulated_metrics: dict[str, Any],
    ) -> SandboxResult:
        fitness_before = self._fitness_evaluator.evaluate(baseline_metrics)
        fitness_after = self._fitness_evaluator.evaluate(simulated_metrics)
        delta = fitness_after.composite_score - fitness_before.composite_score
        passed = delta >= -self._max_degradation
        result = SandboxResult(
            genome_id=proposed_genome.genome_id,
            genome_version=proposed_genome.version,
            fitness_before=fitness_before,
            fitness_after=fitness_after,
            fitness_delta=delta,
            passed=passed,
        )
        self._results.append(result)
        return result

    @property
    def results(self) -> list[SandboxResult]:
        return list(self._results)

    @property
    def approval_rate(self) -> float:
        if not self._results:
            return 0.0
        return sum(1 for r in self._results if r.passed) / len(self._results)
