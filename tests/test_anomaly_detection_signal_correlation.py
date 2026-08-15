"""
Tests for Phase 26.2 anomaly detection and signal correlation.
"""

from datetime import timedelta

from learning.analytics.engine import AnomalyCorrelationEngine
from learning.analytics.models import AnomalyDetectionPolicy
from learning.engine import ContinuousLearningEngine
from learning.models import LearningSignal, LearningSignalType, Severity
from learning.utils import utcnow


def build_learning_engine() -> ContinuousLearningEngine:
    return ContinuousLearningEngine()


def test_metric_anomaly_detection():
    learning_engine = build_learning_engine()

    policy = AnomalyDetectionPolicy(
        min_samples=3,
        z_threshold=2.0,
        baseline_training=True,
    )

    analytics_engine = AnomalyCorrelationEngine(
        learning_engine=learning_engine,
        policy=policy,
    )

    now = utcnow()

    for index in range(3):
        learning_engine.ingest_signal(
            LearningSignal(
                source="observability",
                subject_ref="billing_service",
                signal_type=LearningSignalType.PERFORMANCE,
                severity=Severity.INFO,
                metric="p95_latency_ms",
                value=100.0,
                unit="ms",
                timestamp=(now - timedelta(minutes=10 - index)).isoformat(),
            )
        )

    learning_engine.ingest_signal(
        LearningSignal(
            source="observability",
            subject_ref="billing_service",
            signal_type=LearningSignalType.PERFORMANCE,
            severity=Severity.HIGH,
            metric="p95_latency_ms",
            value=900.0,
            unit="ms",
            timestamp=now.isoformat(),
        )
    )

    report = analytics_engine.analyze()

    assert report.analyzed_signals == 4
    assert report.anomalies >= 1

    anomaly = list(analytics_engine.anomalies.values())[0]

    assert anomaly.metric == "p95_latency_ms"
    assert anomaly.value == 900.0
    assert anomaly.anomaly_score > 0


def test_signal_correlation_and_cluster_insight():
    learning_engine = build_learning_engine()

    policy = AnomalyDetectionPolicy(
        min_samples=1,
        cluster_window_minutes=60,
        correlation_threshold=0.3,
        min_cluster_signals=2,
    )

    analytics_engine = AnomalyCorrelationEngine(
        learning_engine=learning_engine,
        policy=policy,
    )

    now = utcnow()

    learning_engine.ingest_signal(
        LearningSignal(
            source="observability",
            subject_ref="billing_service",
            signal_type=LearningSignalType.PERFORMANCE,
            severity=Severity.HIGH,
            metric="p95_latency_ms",
            value=900.0,
            unit="ms",
            timestamp=now.isoformat(),
        )
    )

    learning_engine.ingest_signal(
        LearningSignal(
            source="incident_manager",
            subject_ref="billing_service",
            signal_type=LearningSignalType.INCIDENT,
            severity=Severity.CRITICAL,
            message="Billing API outage detected.",
            timestamp=(now + timedelta(minutes=1)).isoformat(),
        )
    )

    learning_engine.ingest_signal(
        LearningSignal(
            source="security_scanner",
            subject_ref="billing_service",
            signal_type=LearningSignalType.SECURITY,
            severity=Severity.CRITICAL,
            message="Exposed credential detected.",
            timestamp=(now + timedelta(minutes=2)).isoformat(),
        )
    )

    report = analytics_engine.analyze()

    assert report.clusters >= 1

    cluster = list(analytics_engine.clusters.values())[0]

    assert cluster.affected_subjects == ["billing_service"]
    assert cluster.root_cause_candidates
    assert cluster.confidence > 0

    objectives = set(cluster.objectives)

    assert "performance_efficiency" in objectives
    assert "reliability" in objectives
    assert "security_posture" in objectives

    assert report.insights >= 1

    insight = list(analytics_engine.insights.values())[0]

    assert insight.title == "Correlated anomaly cluster detected"
    assert insight.signal_ids
