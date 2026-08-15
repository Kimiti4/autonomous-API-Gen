"""
Compiler Optimizer.

Optimizes compiler pass configuration.
"""

from __future__ import annotations

from typing import Any

from constitutional_architecture.meta.platform_genome import PlatformGenome


class CompilerOptimizer:
    def recommend_optimization_level(self, genome: PlatformGenome, compilation_metrics: dict[str, Any]) -> int:
        success_rate = compilation_metrics.get("success_rate", 0.0)
        avg_duration = compilation_metrics.get("avg_duration_ms", 0.0)
        if success_rate < 0.8:
            return 0
        elif avg_duration > 5000:
            return 1
        else:
            return 2

    def recommend_normalization(self, genome: PlatformGenome, compilation_metrics: dict[str, Any]) -> bool:
        error_rate = compilation_metrics.get("normalization_error_rate", 0.0)
        return error_rate < 0.01
