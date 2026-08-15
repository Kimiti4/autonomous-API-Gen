"""
Benchmarking Engine.

Compares platform performance before and after mutations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.meta.platform_fitness import PlatformFitness


@dataclass(frozen=True)
class BenchmarkResult:
    benchmark_id: str
    genome_version_before: int
    genome_version_after: int
    fitness_before: PlatformFitness
    fitness_after: PlatformFitness
    improvement: float = 0.0
    dimensions_improved: tuple[str, ...] = ()
    dimensions_degraded: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BenchmarkingEngine:
    def __init__(self) -> None:
        self._results: list[BenchmarkResult] = []

    def benchmark(
        self,
        genome_version_before: int,
        genome_version_after: int,
        fitness_before: PlatformFitness,
        fitness_after: PlatformFitness,
    ) -> BenchmarkResult:
        before_dict = fitness_before.to_dict()
        after_dict = fitness_after.to_dict()
        improved: list[str] = []
        degraded: list[str] = []
        for dim in before_dict:
            if dim == "composite_score":
                continue
            before_val = before_dict.get(dim, 0.0)
            after_val = after_dict.get(dim, 0.0)
            if after_val > before_val + 0.01:
                improved.append(dim)
            elif after_val < before_val - 0.01:
                degraded.append(dim)
        improvement = fitness_after.composite_score - fitness_before.composite_score
        result = BenchmarkResult(
            benchmark_id=f"bench-{genome_version_before}-{genome_version_after}",
            genome_version_before=genome_version_before,
            genome_version_after=genome_version_after,
            fitness_before=fitness_before,
            fitness_after=fitness_after,
            improvement=improvement,
            dimensions_improved=tuple(improved),
            dimensions_degraded=tuple(degraded),
        )
        self._results.append(result)
        return result

    @property
    def results(self) -> list[BenchmarkResult]:
        return list(self._results)

    @property
    def average_improvement(self) -> float:
        if not self._results:
            return 0.0
        return sum(r.improvement for r in self._results) / len(self._results)

    def get_best_mutation(self) -> Optional[BenchmarkResult]:
        if not self._results:
            return None
        return max(self._results, key=lambda r: r.improvement)
