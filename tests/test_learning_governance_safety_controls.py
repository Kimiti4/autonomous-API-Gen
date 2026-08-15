"""
Tests for Phase 26.5 Learning Governance and Safety Controls.
"""

from learning.analytics.engine import AnomalyCorrelationEngine
from learning.engine import ContinuousLearningEngine
from learning.evolution_integration.engine import (
    EvolutionFitnessIntegrationEngine,
)
from learning.evolution_integration.gateway import InMemoryEvolutionGateway
from learning.evolution_integration.models import EvolutionFeedbackPolicy
from learning.governance.engine import LearningGovernanceEngine
from learning.governance.models import LearningGovernancePolicy
from learning.models import LearningInsight, Severity


def build_integration_engine(min_confidence: float = 0.5):
    learning_engine = ContinuousLearningEngine()

    analytics_engine = AnomalyCorrelationEngine(
        learning_engine=learning_engine,
    )

    analytics_engine.insights["insight_security"] = LearningInsight(
        id="insight_security",
        title="Security concern detected",
        description="Critical security finding detected.",
        affected_subjects=["billing_service"],
        signal_ids=["signal_security_1", "signal_security_2"],
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

    integration_policy = EvolutionFeedbackPolicy(
        min_confidence=min_confidence,
        pressure_threshold=0.1,
        high_pressure_threshold=0.5,
        critical_security_requires_governance=True,
        high_pressure_requires_governance=True,
    )

    return EvolutionFitnessIntegrationEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        gateway=gateway,
        policy=integration_policy,
    )


def test_critical_security_requires_approval():
    integration_engine = build_integration_engine()

    governance_engine = LearningGovernanceEngine(
        integration_engine=integration_engine,
        policy=LearningGovernancePolicy(
            min_quality_score=0.5,
            min_confidence=0.5,
            min_corroboration=0.2,
            critical_security_requires_approval=True,
        ),
    )

    report = governance_engine.governed_sync(
        scope="billing_service",
        requested_by="test",
    )

    assert report.status == "PENDING_APPROVAL"
    assert report.approval_id is not None
    assert report.submission_id is None

    approved_report = governance_engine.approve(
        approval_id=report.approval_id,
        approver_id="human_approver",
        comments="Approved after security review.",
    )

    assert approved_report.status in {"ACCEPTED", "PENDING_GOVERNANCE"}
    assert approved_report.submission_id is not None


def test_low_quality_evidence_blocks_sync():
    integration_engine = build_integration_engine(min_confidence=0.1)

    analytics_engine = integration_engine.analytics_engine

    analytics_engine.insights["insight_low_quality"] = LearningInsight(
        id="insight_low_quality",
        title="Weak signal",
        description="Low-confidence signal.",
        affected_subjects=["billing_service"],
        signal_ids=["signal_weak"],
        objectives=["performance_efficiency"],
        severity=Severity.LOW,
        confidence=0.2,
    )

    governance_engine = LearningGovernanceEngine(
        integration_engine=integration_engine,
        policy=LearningGovernancePolicy(
            min_quality_score=0.7,
            min_confidence=0.5,
            min_corroboration=0.2,
        ),
    )

    report = governance_engine.governed_sync(
        scope="billing_service",
        requested_by="test",
    )

    assert report.status == "BLOCKED"
    assert report.safety.allowed is False
    assert "evidence_quality_failed" in report.safety.blockers


def test_kill_switch_blocks_sync():
    integration_engine = build_integration_engine()

    governance_engine = LearningGovernanceEngine(
        integration_engine=integration_engine,
        policy=LearningGovernancePolicy(),
    )

    governance_engine.activate_kill_switch(
        reason="Critical operational incident.",
        activated_by="human_operator",
    )

    report = governance_engine.governed_sync(
        scope="billing_service",
        requested_by="test",
    )

    assert report.status == "BLOCKED"
    assert report.safety.kill_switch_active is True
    assert "kill_switch_active" in report.safety.blockers


def test_reject_approval_prevents_submission():
    integration_engine = build_integration_engine()

    governance_engine = LearningGovernanceEngine(
        integration_engine=integration_engine,
        policy=LearningGovernancePolicy(
            critical_security_requires_approval=True,
        ),
    )

    report = governance_engine.governed_sync(
        scope="billing_service",
        requested_by="test",
    )

    assert report.status == "PENDING_APPROVAL"

    rejected_report = governance_engine.reject(
        approval_id=report.approval_id,
        approver_id="human_approver",
        comments="Rejected due to insufficient evidence.",
    )

    assert rejected_report.status == "REJECTED"
    assert rejected_report.submission_id is None
