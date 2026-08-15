"""
Phase 18 — Empirical Fitness Calculator.

Translates real-world telemetry profiles into the constitutional
QualityAttribute Pareto dimensions used by the Pass 5 Evolution Engine,
enabling predicted-vs-actual fitness comparison.

Constitutional Alignment:
- "Avoid relying on a single aggregate score": latency, error rate, cost,
  and MTTR are evaluated as distinct Pareto dimensions.
"""

from __future__ import annotations

from typing import Dict

from constitutional_architecture.core.learning.telemetry_ingestor import (
    GenomeTelemetryProfile,
)
from constitutional_architecture.core.models.intent import QualityAttribute


class EmpiricalFitnessCalculator:
    """Maps real-world telemetry to empirical Pareto-dimension scores."""

    LATENCY_BASELINE_MS = 1000.0   # 50ms -> 1.0, 1000ms -> 0.0
    ERROR_RATE_BASELINE = 5.0      # 0% -> 1.0, 5% -> 0.0
    COST_BASELINE_USD = 1000.0     # $100/mo -> 1.0, $1000/mo -> 0.0
    MTTR_BASELINE_SECONDS = 3600.0  # 0s -> 1.0, 1h -> 0.0

    def calculate_real_world_fitness(
        self, profile: GenomeTelemetryProfile,
    ) -> Dict[QualityAttribute, float]:
        """Return empirical scores (0.0 to 1.0) based on production evidence."""
        scores: Dict[QualityAttribute, float] = {}

        # Performance (lower latency = higher score)
        scores[QualityAttribute.PERFORMANCE] = max(
            0.0, 1.0 - (profile.p99_latency_ms / self.LATENCY_BASELINE_MS))

        # Reliability (lower error rate = higher score)
        scores[QualityAttribute.RELIABILITY] = max(
            0.0, 1.0 - (profile.error_rate_percent / self.ERROR_RATE_BASELINE))

        # Cost Efficiency (lower cost = higher score)
        scores[QualityAttribute.COST_EFFICIENCY] = max(
            0.0, 1.0 - (profile.monthly_infrastructure_cost_usd
                        / self.COST_BASELINE_USD))

        # Maintainability / Operability (faster MTTR = higher score)
        scores[QualityAttribute.MAINTAINABILITY] = max(
            0.0, 1.0 - (profile.mttr_seconds / self.MTTR_BASELINE_SECONDS))

        return scores
