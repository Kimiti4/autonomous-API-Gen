"""
Tests for Phase 26.4 Evolutionary Fitness Feedback Integration.
"""

from learning.analytics.engine import AnomalyCorrelationEngine
from learning.engine import ContinuousLearningEngine
from learning.evolution_integration.engine import (
    EvolutionFitnessIntegrationEngine,
)
from learning.evolution_integration.gateway import InMemoryEvolutionGateway
from learning.evolution_integration.models import EvolutionFeedbackPolicy
from learning.models import LearningInsight, Severity


def build_engines():
    learning_engine = ContinuousLearningEngine()

    analytics_engine = AnomalyCorrelationEngine(
        learning_engine=learning_engine,
    )

    analytics_engine.insights["insight_security"] = LearningInsight(
        id="insight_security",
        title="Security concern detected",
        description="Critical security finding detected.",
        affected_subjects=["billing_service"],
        signal_ids=["signal_security_1"],
        objectives=["security_posture"],
        severity=Severity.CRITICAL,
        confidence=0.9,
    )

    analytics_engine.insights["insight_reliability"] = LearningInsight(
        id="insight_reliability",
        title="Reliability incident detected",
        description="Operational incident detected.",
        affected_subjects=["billing_service"],
        signal_ids=["signal_incident_1"],
        objectives=["reliability", "operational_resilience"],
        severity=Severity.HIGH,
        confidence=0.8,
    )

    gateway = InMemoryEvolutionGateway()

    policy = EvolutionFeedbackPolicy(
        min_confidence=0.5,
        pressure_threshold=0.1,
        high_pressure_threshold=0.5,
        critical_security_requires_governance=True,
        high_pressure_requires_governance=True,
    )

    integration_engine = EvolutionFitnessIntegrationEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        gateway=gateway,
        policy=policy,
    )

    return integration_engine, gateway


def test_generate_feedback_produces_pressures_and_hints():
    engine, _ = build_engines()

    bundle = engine.generate_feedback(scope="billing_service")

    assert bundle.status == "GENERATED"

    assert "security_posture" in bundle.objective_pressures
    assert "reliability" in bundle.objective_pressures

    security_pressure = bundle.objective_pressures["security_posture"]

    assert security_pressure.pressure > 0.5
    assert security_pressure.severity == Severity.CRITICAL.value

    chromosome_families = {
        hint.chromosome_family
        for hint in bundle.genome_hints
    }

    assert "Security" in chromosome_families
    assert "Reliability" in chromosome_families

    assert bundle.requires_governance is True


def test_submit_feedback_requires_governance():
    engine, gateway = build_engines()

    bundle = engine.generate_feedback(scope="billing_service")

    result = engine.submit_feedback(bundle.id)

    assert result.status == "PENDING_GOVERNANCE"

    assert bundle.id in engine.submissions


def test_sync_generates_and_submits_bundle():
    engine, _ = build_engines()

    report = engine.sync(scope="billing_service")

    assert report.generated_bundle_id is not None
    assert report.submission_id is not None
    assert report.status == "PENDING_GOVERNANCE"


def test_duplicate_suppression():
    engine, _ = build_engines()

    first_bundle = engine.generate_feedback(scope="billing_service")
    second_bundle = engine.generate_feedback(scope="billing_service")

    assert first_bundle.id == second_bundle.id
