"""
Phase 18 — Constitutional Knowledge Base (CKB) Updater.

Closes the continuous evolution loop by adjusting architectural heuristics
based on real-world empirical evidence.

Compares what the Evolution Engine *predicted* (static fitness) with what
*actually happened* (empirical fitness). Patterns that consistently
underperform are penalized; patterns that exceed expectations are rewarded.

Safety gates: a Minimum Sample Size prevents learning from statistical
noise, and a bounded LEARNING_RATE prevents catastrophic forgetting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from constitutional_architecture.core.learning.empirical_fitness import (
    EmpiricalFitnessCalculator,
)
from constitutional_architecture.core.learning.telemetry_ingestor import (
    GenomeTelemetryProfile,
)
from constitutional_architecture.core.models.intent import QualityAttribute


class CKBUpdater:
    """
    Updates the Constitutional Knowledge Base based on production evidence.

    `ckb` must expose `adjust_heuristic(pattern, attr, direction, rate)`
    (e.g., HeuristicAdjustmentStore).
    """

    MIN_SAMPLE_SIZE = 50
    LEARNING_RATE = 0.05
    SIGNIFICANCE_THRESHOLD = 0.15

    def __init__(self, ckb: Any) -> None:
        self.ckb = ckb
        self.fitness_calc = EmpiricalFitnessCalculator()

    def evaluate_and_learn(
        self,
        profile: GenomeTelemetryProfile,
        predicted_fitness: Dict[QualityAttribute, float],
    ) -> Optional[Dict[str, Any]]:
        """
        Compare predicted vs empirical fitness and adjust CKB weights.

        Returns None when the evidence is below the statistical
        significance gate; otherwise a summary of penalties/rewards.
        """
        if profile.sample_size < self.MIN_SAMPLE_SIZE:
            return None

        empirical_fitness = self.fitness_calc.calculate_real_world_fitness(profile)

        summary: Dict[str, Any] = {
            "genome_id": profile.genome_id,
            "architecture_style": profile.architecture_style,
            "penalized": [],
            "rewarded": [],
            "deltas": {},
        }

        for attr, empirical_score in empirical_fitness.items():
            predicted_score = predicted_fitness.get(attr, 0.5)
            delta = empirical_score - predicted_score

            if delta < -self.SIGNIFICANCE_THRESHOLD:
                self._penalize_architecture_pattern(
                    profile.architecture_style, attr, delta)
                summary["penalized"].append({
                    "attribute": attr.value,
                    "delta": round(delta, 4),
                })
                summary["deltas"][attr.value] = round(delta, 4)
            elif delta > self.SIGNIFICANCE_THRESHOLD:
                self._reward_architecture_pattern(
                    profile.architecture_style, attr, delta)
                summary["rewarded"].append({
                    "attribute": attr.value,
                    "delta": round(delta, 4),
                })
                summary["deltas"][attr.value] = round(delta, 4)

        return summary

    def _penalize_architecture_pattern(self, style: str,
                                       attr: QualityAttribute,
                                       delta: float) -> None:
        self.ckb.adjust_heuristic(
            style, attr, direction=-1, rate=self.LEARNING_RATE)

    def _reward_architecture_pattern(self, style: str,
                                     attr: QualityAttribute,
                                     delta: float) -> None:
        self.ckb.adjust_heuristic(
            style, attr, direction=1, rate=self.LEARNING_RATE)
