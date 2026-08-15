"""Tests for the anomaly detector."""

import pytest

from constitutional_architecture.operations.metrics_collector import MetricPoint
from constitutional_architecture.operations.anomaly_detector import AnomalyDetector


class TestAnomalyDetector:
    def test_no_anomaly_with_few_samples(self):
        detector = AnomalyDetector(min_samples=5)
        from constitutional_architecture.operations.metrics_collector import MetricSeries
        series = MetricSeries(
            name="cpu",
            points=(
                MetricPoint(name="cpu", value=50.0),
                MetricPoint(name="cpu", value=51.0),
            ),
        )
        result = detector.detect(series)
        assert len(result.anomalies) == 0

    def test_detects_outlier(self):
        detector = AnomalyDetector(z_threshold=2.0, min_samples=5)
        from constitutional_architecture.operations.metrics_collector import MetricSeries
        points = [MetricPoint(name="cpu", value=50.0) for _ in range(20)]
        points.append(MetricPoint(name="cpu", value=500.0))
        series = MetricSeries(name="cpu", points=tuple(points))
        result = detector.detect(series)
        assert len(result.anomalies) >= 1

    def test_detect_collective(self):
        detector = AnomalyDetector(z_threshold=1.9, min_samples=10, window_size=50)
        from constitutional_architecture.operations.metrics_collector import MetricSeries
        points = [MetricPoint(name="cpu", value=50.0) for _ in range(50)]
        for _ in range(10):
            points.append(MetricPoint(name="cpu", value=500.0))
        series = MetricSeries(name="cpu", points=tuple(points))
        anomalies = detector.detect_collective(series, window=3)
        assert len(anomalies) >= 1
