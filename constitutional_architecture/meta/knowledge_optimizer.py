"""
Knowledge Optimizer.

Optimizes knowledge retrieval strategies.
"""

from __future__ import annotations

from typing import Any

from constitutional_architecture.meta.platform_genome import PlatformGenome


class KnowledgeOptimizer:
    def recommend_query_limit(self, genome: PlatformGenome, knowledge_metrics: dict[str, Any]) -> int:
        utilization = knowledge_metrics.get("query_utilization", 0.0)
        current = genome.get_parameter("know.query_limit")
        if current is None:
            return 10
        if utilization < 0.3:
            return max(current.value - 2, 1)
        elif utilization > 0.9:
            return min(current.value + 5, 100)
        return current.value

    def recommend_min_confidence(self, genome: PlatformGenome, knowledge_metrics: dict[str, Any]) -> float:
        recommendation_accuracy = knowledge_metrics.get("recommendation_accuracy", 0.5)
        if recommendation_accuracy > 0.8:
            return 0.3
        elif recommendation_accuracy < 0.4:
            return 0.7
        return 0.5
