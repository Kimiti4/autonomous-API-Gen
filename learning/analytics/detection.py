"""
Anomaly detectors.
"""

from __future__ import annotations

from typing import List, Optional, Protocol

from ..models import LearningSignal, Severity, severity_rank
from ..utils import deterministic_id
from .baseline import BaselineRegistry
from .models import AnomalyDetectionPolicy, AnomalyRecord


class AnomalyDetector(Protocol):
    """Contract for anomaly detectors."""

    def detect(
        self,
        signal: LearningSignal,
        baselines: BaselineRegistry,
        policy: AnomalyDetectionPolicy,
    ) -> Optional[AnomalyRecord]:
        ...


class StatisticalMetricAnomalyDetector:
    """Detects metric anomalies using baseline statistics."""

    def detect(
        self,
        signal: LearningSignal,
        baselines: BaselineRegistry,
        policy: AnomalyDetectionPolicy,
    ) -> Optional[AnomalyRecord]:
        if signal.metric is None and signal.value == 0.0:
            return None

        baseline = baselines.get_or_create(signal)

        score, mean, stddev = baselines.score(baseline, signal.value)

        if policy.baseline_training:
            baselines.update(baseline, signal.value)

        if score < policy.z_threshold:
            return None

        anomaly_id = deterministic_id(
            "anomaly",
            {
                "signal_id": signal.id,
                "method": "statistical_metric",
            },
        )

        return AnomalyRecord(
            id=anomaly_id,
            signal_id=signal.id or "",
            subject_ref=signal.subject_ref,
            signal_type=signal.signal_type.value,
            metric=signal.metric,
            severity=signal.severity,
            value=signal.value,
            baseline_mean=mean,
            baseline_stddev=stddev,
            anomaly_score=round(score, 4),
            detection_method="statistical_metric",
            timestamp=signal.timestamp,
        )


class SeverityAnomalyDetector:
    """Detects anomalies from high-severity signals."""

    def detect(
        self,
        signal: LearningSignal,
        baselines: BaselineRegistry,
        policy: AnomalyDetectionPolicy,
    ) -> Optional[AnomalyRecord]:
        threshold_rank = severity_rank(policy.severity_anomaly_threshold)

        signal_severity_rank = severity_rank(signal.severity)

        if signal_severity_rank < threshold_rank:
            return None

        anomaly_score = 1.0 + (signal_severity_rank * 0.25)

        anomaly_id = deterministic_id(
            "anomaly",
            {
                "signal_id": signal.id,
                "method": "severity_spike",
            },
        )

        return AnomalyRecord(
            id=anomaly_id,
            signal_id=signal.id or "",
            subject_ref=signal.subject_ref,
            signal_type=signal.signal_type.value,
            metric=signal.metric,
            severity=signal.severity,
            value=signal.value,
            baseline_mean=None,
            baseline_stddev=None,
            anomaly_score=round(anomaly_score, 4),
            detection_method="severity_spike",
            timestamp=signal.timestamp,
        )


class CompositeAnomalyDetector:
    """Combines multiple anomaly detectors."""

    def __init__(self) -> None:
        self.detectors: List[AnomalyDetector] = [
            StatisticalMetricAnomalyDetector(),
            SeverityAnomalyDetector(),
        ]

    def detect(
        self,
        signal: LearningSignal,
        baselines: BaselineRegistry,
        policy: AnomalyDetectionPolicy,
    ) -> Optional[AnomalyRecord]:
        selected: Optional[AnomalyRecord] = None

        methods: List[str] = []

        for detector in self.detectors:
            anomaly = detector.detect(signal, baselines, policy)

            if not anomaly:
                continue

            if selected is None:
                selected = anomaly

            methods.append(anomaly.detection_method)

            if anomaly.anomaly_score > selected.anomaly_score:
                selected = anomaly

        if selected:
            selected.detection_method = "+".join(sorted(set(methods)))

        return selected
