"""
Fitness Feedback.

Translates operational observations into fitness signals
for the Evolution Engine's Dynamic Fitness Interface.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.operations.classification import ObservationClassifier
from constitutional_architecture.operations.observation_model import (
    FitnessSignal,
    Observation,
    ObservationClassification,
    ObservationSeverity,
)


class FitnessFeedbackProducer:

    SEVERITY_PENALTY = {
        ObservationSeverity.INFO: 0.01,
        ObservationSeverity.WARNING: 0.05,
        ObservationSeverity.ERROR: 0.15,
        ObservationSeverity.CRITICAL: 0.30,
    }

    DIMENSION_MAPPING = {
        ObservationClassification.ARCHITECTURAL_DEFICIENCY: {
            "reliability": -1.0,
            "performance": -0.5,
            "scalability": -0.5,
        },
        ObservationClassification.OPERATIONAL_MISCONFIGURATION: {
            "deployment_completeness": -1.0,
            "observability": -0.5,
        },
    }

    def __init__(self, classifier: Optional[ObservationClassifier] = None) -> None:
        self._classifier = classifier or ObservationClassifier()
        self._signals: list[FitnessSignal] = []

    def produce_signal(
        self,
        observations: list[Observation],
        deployment_id: str = "",
        isr_hash: str = "",
    ) -> Optional[FitnessSignal]:
        relevant = [
            o for o in observations
            if o.classification.produces_fitness_signal
        ]

        if not relevant:
            return None

        dimensions: dict[str, float] = {}
        total_confidence = 0.0

        for obs in relevant:
            penalty = self.SEVERITY_PENALTY.get(obs.severity, 0.0)
            dimension_mapping = self.DIMENSION_MAPPING.get(obs.classification, {})

            for dim, weight in dimension_mapping.items():
                impact = penalty * weight
                dimensions[dim] = dimensions.get(dim, 0.0) + impact

            total_confidence += obs.classification_confidence

        normalized = {}
        for dim, impact in dimensions.items():
            score = max(0.0, min(1.0, 1.0 + impact))
            normalized[dim] = score

        avg_confidence = total_confidence / len(relevant) if relevant else 0.0

        from collections import Counter
        classifications = [o.classification for o in relevant]
        primary_classification = Counter(classifications).most_common(1)[0][0]

        signal = FitnessSignal(
            id=f"fitness-{uuid.uuid4().hex[:12]}",
            deployment_id=deployment_id, isr_hash=isr_hash,
            dimensions=normalized,
            observation_ids=tuple(o.id for o in relevant),
            classification=primary_classification,
            confidence=avg_confidence,
            reasoning=f"Fitness signal from {len(relevant)} observation(s)",
        )

        self._signals.append(signal)
        return signal

    def compute_aggregate_signal(
        self, signals: list[FitnessSignal],
    ) -> Optional[FitnessSignal]:
        if not signals:
            return None

        all_dims: set[str] = set()
        for signal in signals:
            all_dims.update(signal.dimensions.keys())

        aggregated: dict[str, float] = {}
        for dim in all_dims:
            values = [s.dimensions.get(dim, 1.0) for s in signals]
            aggregated[dim] = sum(values) / len(values)

        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        all_obs_ids: list[str] = []
        for s in signals:
            all_obs_ids.extend(s.observation_ids)

        return FitnessSignal(
            id=f"fitness-agg-{uuid.uuid4().hex[:12]}",
            dimensions=aggregated,
            observation_ids=tuple(all_obs_ids),
            confidence=avg_confidence,
            reasoning=f"Aggregated from {len(signals)} signal(s)",
        )

    @property
    def signals(self) -> list[FitnessSignal]:
        return list(self._signals)
