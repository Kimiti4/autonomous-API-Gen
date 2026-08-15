"""
Metric baseline registry.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from ..models import LearningSignal
from ..utils import utcnow
from .models import AnomalyDetectionPolicy, BaselineState


class BaselineRegistry:
    """Maintains rolling baselines for metric signals."""

    def __init__(self, policy: AnomalyDetectionPolicy) -> None:
        self.policy = policy
        self.baselines: Dict[str, BaselineState] = {}

    def get_or_create(self, signal: LearningSignal) -> BaselineState:
        key = self._key(signal)

        baseline = self.baselines.get(key)

        if baseline:
            return baseline

        baseline = BaselineState(key=key)

        self.baselines[key] = baseline

        return baseline

    def score(
        self,
        baseline: BaselineState,
        value: float,
    ) -> Tuple[float, float, float]:
        """
        Return anomaly score, baseline mean, and standard deviation.
        """

        if baseline.count < self.policy.min_samples:
            return 0.0, baseline.mean, 0.0

        variance = baseline.m2 / max(1, baseline.count - 1)

        stddev = math.sqrt(max(variance, self.policy.min_value_variance))

        z_score = abs(value - baseline.mean) / stddev

        ewm_stddev = math.sqrt(
            max(baseline.ewm_var, self.policy.min_value_variance)
        )

        ewma_z_score = abs(value - baseline.ewma) / ewm_stddev

        score = max(z_score, ewma_z_score)

        return score, baseline.mean, stddev

    def update(self, baseline: BaselineState, value: float) -> None:
        """
        Update baseline using Welford variance and EWMA smoothing.
        """

        baseline.count += 1

        delta = value - baseline.mean

        baseline.mean += delta / baseline.count

        delta_2 = value - baseline.mean

        baseline.m2 += delta * delta_2

        alpha = self.policy.ewma_alpha

        if baseline.count == 1:
            baseline.ewma = value
            baseline.ewm_var = 0.0
        else:
            diff = value - baseline.ewma

            baseline.ewma += alpha * diff

            baseline.ewm_var = (1.0 - alpha) * (
                baseline.ewm_var + alpha * diff * diff
            )

        baseline.updated_at = utcnow().isoformat()

    def _key(self, signal: LearningSignal) -> str:
        subject = signal.subject_ref or "unknown"

        metric = signal.metric or "value"

        return f"{subject}:{signal.signal_type.value}:{metric}"
