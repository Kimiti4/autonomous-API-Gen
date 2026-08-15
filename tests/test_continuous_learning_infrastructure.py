"""
Tests for Phase 26 Continuous Learning Infrastructure.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from learning.api import enable_continuous_learning, router
from learning.engine import ContinuousLearningEngine
from learning.models import (
    LearningPolicy,
    LearningSignal,
    LearningSignalType,
    Severity,
)


def build_engine() -> ContinuousLearningEngine:
    policy = LearningPolicy(
        latency_threshold_ms=500.0,
        monthly_cost_threshold=1000.0,
        min_signals_for_insight=1,
        critical_security_requires_governance=True,
        high_severity_requires_governance=True,
    )

    return ContinuousLearningEngine(policy=policy)


def test_continuous_learning_pipeline_and_feedback_bundle():
    engine = build_engine()

    engine.ingest_batch(
        [
            LearningSignal(
                source="observability",
                subject_ref="billing_service",
                signal_type=LearningSignalType.PERFORMANCE,
                severity=Severity.HIGH,
                metric="p95_latency_ms",
                value=900.0,
                unit="ms",
                labels={
                    "service": "billing_service",
                },
            ),
            LearningSignal(
                source="incident_manager",
                subject_ref="billing_service",
                signal_type=LearningSignalType.INCIDENT,
                severity=Severity.CRITICAL,
                message="Billing API outage detected.",
                labels={
                    "service": "billing_service",
                },
            ),
            LearningSignal(
                source="security_scanner",
                subject_ref="billing_service",
                signal_type=LearningSignalType.SECURITY,
                severity=Severity.CRITICAL,
                message="Exposed secret detected.",
                labels={
                    "service": "billing_service",
                },
            ),
            LearningSignal(
                source="cloud_cost",
                subject_ref="billing_service",
                signal_type=LearningSignalType.COST,
                severity=Severity.HIGH,
                value=5000.0,
                unit="USD",
                labels={
                    "service": "billing_service",
                    "cost_anomaly": "true",
                },
            ),
            LearningSignal(
                source="customer_support",
                subject_ref="billing_service",
                signal_type=LearningSignalType.CUSTOMER_FEEDBACK,
                severity=Severity.MEDIUM,
                message="Customers report slow invoice creation.",
                labels={
                    "service": "billing_service",
                    "sentiment": "negative",
                },
            ),
        ]
    )

    insights = engine.analyze()

    assert len(insights) >= 5

    titles = {insight.title for insight in engine.insights.values()}

    assert "Reliability incident detected" in titles
    assert "Performance degradation detected" in titles
    assert "Security concern detected" in titles
    assert "Cost pressure detected" in titles
    assert "Negative customer feedback detected" in titles

    bundle = engine.compile_feedback(scope="billing_service")

    assert bundle.governance_required is True

    assert bundle.genome_hints

    chromosome_families = {
        hint.chromosome_family
        for hint in bundle.genome_hints
    }

    assert "Reliability" in chromosome_families
    assert "Security" in chromosome_families
    assert "Performance" in chromosome_families
    assert "Infrastructure" in chromosome_families
    assert "Frontend" in chromosome_families

    assert bundle.fitness_updates

    security_update = next(
        update
        for update in bundle.fitness_updates
        if "security_posture" in update.objective_pressures
    )

    assert security_update.constraints["security_review_required"] is True


def test_learning_report():
    engine = build_engine()

    engine.ingest_signal(
        LearningSignal(
            source="observability",
            subject_ref="auth_service",
            signal_type=LearningSignalType.PERFORMANCE,
            severity=Severity.MEDIUM,
            metric="p95_latency_ms",
            value=700.0,
            unit="ms",
        )
    )

    engine.analyze()

    report = engine.report()

    assert report["signal_count"] == 1
    assert report["insight_count"] >= 1
    assert report["recommendation_count"] >= 1


def test_learning_api_endpoints():
    app = FastAPI()

    enable_continuous_learning(app)

    client = TestClient(app)

    response = client.post(
        "/v1/learning/signals",
        json={
            "signals": [
                {
                    "source": "observability",
                    "subject_ref": "checkout_service",
                    "signal_type": "PERFORMANCE",
                    "severity": "HIGH",
                    "metric": "p95_latency_ms",
                    "value": 900.0,
                    "unit": "ms",
                    "labels": {"service": "checkout_service"},
                },
                {
                    "source": "incident_manager",
                    "subject_ref": "checkout_service",
                    "signal_type": "INCIDENT",
                    "severity": "CRITICAL",
                    "message": "Checkout API outage detected.",
                    "labels": {"service": "checkout_service"},
                },
                {
                    "source": "security_scanner",
                    "subject_ref": "checkout_service",
                    "signal_type": "SECURITY",
                    "severity": "CRITICAL",
                    "message": "Exposed secret detected.",
                    "labels": {"service": "checkout_service"},
                },
                {
                    "source": "cloud_cost",
                    "subject_ref": "checkout_service",
                    "signal_type": "COST",
                    "severity": "HIGH",
                    "value": 5000.0,
                    "unit": "USD",
                    "labels": {"service": "checkout_service", "cost_anomaly": "true"},
                },
                {
                    "source": "customer_support",
                    "subject_ref": "checkout_service",
                    "signal_type": "CUSTOMER_FEEDBACK",
                    "severity": "MEDIUM",
                    "message": "Customers report checkout errors.",
                    "labels": {"service": "checkout_service", "sentiment": "negative"},
                },
            ]
        },
    )

    assert response.status_code == 201

    assert response.json()["ingested_signals"] == 5

    response = client.post(
        "/v1/learning/analyze",
        json={"subject_ref": "checkout_service"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_insights"] >= 5

    response = client.post(
        "/v1/learning/feedback-bundle",
        json={"scope": "checkout_service", "subject_ref": "checkout_service"},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["governance_required"] is True

    assert body["genome_hints"]

    chromosome_families = {
        hint["chromosome_family"] for hint in body["genome_hints"]
    }

    assert "Reliability" in chromosome_families
    assert "Security" in chromosome_families
    assert "Performance" in chromosome_families
    assert "Infrastructure" in chromosome_families
    assert "Frontend" in chromosome_families

    response = client.get("/v1/learning/report")

    assert response.status_code == 200

    report = response.json()

    assert report["signal_count"] == 5
    assert report["insight_count"] >= 5
    assert report["recommendation_count"] >= 5
    assert report["bundle_count"] >= 1
