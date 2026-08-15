"""
Agent Optimizer.

Optimizes agent collaboration parameters.
"""

from __future__ import annotations

from typing import Any

from constitutional_architecture.meta.platform_genome import PlatformGenome


class AgentOptimizer:
    def recommend_consensus_rounds(self, genome: PlatformGenome, agent_metrics: dict[str, Any]) -> int:
        arbitration_rate = agent_metrics.get("arbitration_rate", 0.0)
        avg_rounds = agent_metrics.get("avg_rounds_to_consensus", 1.0)
        current = genome.get_parameter("agent.consensus_max_rounds")
        if current is None:
            return 3
        if arbitration_rate > 0.3:
            return min(current.value + 1, 10)
        elif avg_rounds < 1.5 and arbitration_rate < 0.05:
            return max(current.value - 1, 1)
        return current.value

    def recommend_approval_threshold(self, genome: PlatformGenome, agent_metrics: dict[str, Any]) -> float:
        proposal_quality = agent_metrics.get("proposal_quality", 0.5)
        if proposal_quality > 0.8:
            return 0.5
        elif proposal_quality < 0.4:
            return 0.75
        return 0.6
