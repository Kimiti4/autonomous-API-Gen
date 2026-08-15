"""
Anomaly Detector.

Statistical anomaly detection for operational metrics.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.operations.metrics_collector import MetricSeries
from constitutional_architecture.operations.observation_model import Anomaly, ObservationSeverity


@dataclass(frozen=True)
class AnomalyDetectionResult:
    anomalies: tuple[Anomaly, ...] = ()
    mean: float = 0.0
    std_dev: float = 0.0
    threshold: float = 0.0


class AnomalyDetector:

    def __init__(
        self,
        z_threshold: float = 3.0,
        min_samples: int = 10,
        window_size: int = 100,
    ) -> None:
        self._z_threshold = z_threshold
        self._min_samples = min_samples
        self._window_size = window_size

    def detect(self, series: MetricSeries) -> AnomalyDetectionResult:
        if len(series.points) < self._min_samples:
            return AnomalyDetectionResult()

        values = [p.value for p in series.points[-self._window_size:]]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0001

        anomalies: list[Anomaly] = []
        threshold = mean + self._z_threshold * std_dev

        for point in series.points[-self._window_size:]:
            z_score = (point.value - mean) / std_dev
            if abs(z_score) > self._z_threshold:
                severity = (
                    ObservationSeverity.CRITICAL if abs(z_score) > self._z_threshold * 2
                    else ObservationSeverity.ERROR if abs(z_score) > self._z_threshold * 1.5
                    else ObservationSeverity.WARNING
                )
                anomalies.append(Anomaly(
                    id=f"anomaly-{uuid.uuid4().hex[:12]}",
                    metric_name=series.name, timestamp=point.timestamp,
                    observed_value=point.value, expected_value=mean,
                    deviation=z_score, severity=severity,
                    description=(
                        f"Metric '{series.name}' value {point.value:.2f} "
                        f"is {abs(z_score):.1f} standard deviations from mean {mean:.2f}"
                    ),
                    service_name=point.service_name,
                    deployment_id=point.deployment_id,
                ))

        return AnomalyDetectionResult(
            anomalies=tuple(anomalies), mean=mean, std_dev=std_dev, threshold=threshold,
        )

    def detect_collective(
        self, series: MetricSeries, window: int = 5
    ) -> list[Anomaly]:
        if len(series.points) < window + self._min_samples:
            return []

        values = [p.value for p in series.points[-self._window_size:]]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0001

        anomalies: list[Anomaly] = []
        for i in range(len(series.points) - window + 1):
            window_values = [p.value for p in series.points[i:i + window]]
            window_mean = sum(window_values) / len(window_values)
            z_score = (window_mean - mean) / std_dev
            if abs(z_score) > self._z_threshold:
                anomalies.append(Anomaly(
                    id=f"collective-{uuid.uuid4().hex[:12]}",
                    metric_name=series.name, timestamp=series.points[i].timestamp,
                    observed_value=window_mean, expected_value=mean,
                    deviation=z_score, severity=ObservationSeverity.WARNING,
                    description=(
                        f"Collective anomaly: {window} consecutive values "
                        f"averaging {window_mean:.2f} (expected {mean:.2f})"
                    ),
                    service_name=series.points[i].service_name,
                    deployment_id=series.points[i].deployment_id,
                ))
        return anomalies
