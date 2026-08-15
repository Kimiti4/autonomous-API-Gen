"""
Metrics Collector.

Collects and aggregates operational metrics from running systems.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationSeverity,
    ObservationSource,
)


@dataclass(frozen=True)
class MetricPoint:
    name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: dict[str, str] = field(default_factory=dict)
    service_name: str = ""
    deployment_id: str = ""


@dataclass(frozen=True)
class MetricSeries:
    name: str
    points: tuple[MetricPoint, ...] = ()
    labels: dict[str, str] = field(default_factory=dict)

    @property
    def latest_value(self) -> float:
        if not self.points:
            return 0.0
        return self.points[-1].value

    @property
    def mean(self) -> float:
        if not self.points:
            return 0.0
        return sum(p.value for p in self.points) / len(self.points)

    @property
    def min_value(self) -> float:
        if not self.points:
            return 0.0
        return min(p.value for p in self.points)

    @property
    def max_value(self) -> float:
        if not self.points:
            return 0.0
        return max(p.value for p in self.points)


class MetricsCollector:

    def __init__(self) -> None:
        self._series: dict[str, list[MetricPoint]] = {}
        self._thresholds: dict[str, tuple[float, ObservationSeverity]] = {}

    def set_threshold(
        self,
        metric_name: str,
        threshold: float,
        severity: ObservationSeverity = ObservationSeverity.WARNING,
    ) -> None:
        self._thresholds[metric_name] = (threshold, severity)

    def record(self, point: MetricPoint) -> None:
        self._series.setdefault(point.name, []).append(point)
        if len(self._series[point.name]) > 10000:
            self._series[point.name] = self._series[point.name][-10000:]

    def get_series(self, metric_name: str) -> MetricSeries:
        points = tuple(self._series.get(metric_name, []))
        labels = points[0].labels if points else {}
        return MetricSeries(name=metric_name, points=points, labels=labels)

    def check_thresholds(self) -> list[Observation]:
        observations: list[Observation] = []
        for metric_name, (threshold, severity) in self._thresholds.items():
            series = self.get_series(metric_name)
            if not series.points:
                continue
            latest = series.latest_value
            if latest > threshold:
                observations.append(Observation(
                    id=f"obs-{uuid.uuid4().hex[:12]}",
                    source=ObservationSource.METRICS,
                    severity=severity,
                    title=f"Metric '{metric_name}' exceeded threshold",
                    description=(
                        f"Metric '{metric_name}' value {latest:.2f} "
                        f"exceeded threshold {threshold:.2f}"
                    ),
                    details={
                        "metric_name": metric_name,
                        "value": latest,
                        "threshold": threshold,
                        "mean": series.mean,
                        "max": series.max_value,
                    },
                    service_name=series.points[-1].service_name,
                    deployment_id=series.points[-1].deployment_id,
                ))
        return observations

    @property
    def metric_names(self) -> list[str]:
        return list(self._series.keys())

    @property
    def total_points(self) -> int:
        return sum(len(points) for points in self._series.values())
