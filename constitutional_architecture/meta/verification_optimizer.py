"""
Verification Optimizer.

Optimizes verification thresholds and configuration.
"""

from __future__ import annotations

from typing import Any

from constitutional_architecture.meta.platform_genome import PlatformGenome


class VerificationOptimizer:
    def recommend_max_level(self, genome: PlatformGenome, verification_metrics: dict[str, Any]) -> int:
        false_negative_rate = verification_metrics.get("false_negative_rate", 0.0)
        avg_duration = verification_metrics.get("avg_duration_ms", 0.0)
        current = genome.get_parameter("verif.max_level")
        if current is None:
            return 3
        if false_negative_rate > 0.1:
            return min(6, current.value + 1)
        if avg_duration > 30000:
            return max(1, current.value - 1)
        return current.value
