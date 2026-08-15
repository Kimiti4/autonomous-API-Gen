"""
Scheduler Optimizer.

Optimizes scheduling policies.
"""

from __future__ import annotations

from typing import Any

from constitutional_architecture.meta.platform_genome import PlatformGenome


class SchedulerOptimizer:
    def recommend_concurrency(self, genome: PlatformGenome, scheduler_metrics: dict[str, Any]) -> int:
        utilization = scheduler_metrics.get("utilization", 0.0)
        queue_depth = scheduler_metrics.get("queue_depth", 0)
        current = genome.get_parameter("sched.max_concurrent_evolutions")
        if current is None:
            return 4
        if utilization > 0.9 and queue_depth > 5:
            return min(current.value + 1, 32)
        elif utilization < 0.3:
            return max(current.value - 1, 1)
        return current.value
