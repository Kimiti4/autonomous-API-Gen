"""
Tests for Phase 26.8 Production Learning Certification.
"""

from datetime import timedelta
from types import SimpleNamespace

from learning.production_certification.engine import (
    ProductionLearningCertificationEngine,
)
from learning.production_certification.models import (
    CertificationStatus,
    OperationalReadinessEvidence,
    ProductionLearningCertificationPolicy,
    utcnow,
)


def build_fake_26_7_engine(status: str = "CERTIFIED"):
    report = SimpleNamespace(
        id="learning_pipeline_certification_1",
        status=status,
        expires_at=utcnow() + timedelta(days=30),
        revoked_at=None,
    )

    return SimpleNamespace(
        reports={report.id: report},
        latest_report=lambda: report,
    )


def build_full_evidence() -> OperationalReadinessEvidence:
    return OperationalReadinessEvidence(
        slo_definitions=["slo_learning_pipelineavailability"],
        runbooks=["runbook_learning_pipeline"],
        incident_response_plans=["incident_response_learning_pipeline"],
        backup_restore_evidence=["backup_restore_learning_pipeline"],
        observability_evidence=["observability_dashboard_learning"],
        dashboard_refs=["dashboard_learning_pipeline"],
        marketplace_metrics_refs=["marketplace_metrics_dashboard"],
        fraud_learning_evidence=["fraud_learning_report"],
        pricing_learning_evidence=["pricing_learning_report"],
        conversion_learning_evidence=["conversion_learning_report"],
        refund_support_learning_evidence=["refund_support_learning_report"],
        revenue_ops_learning_evidence=["revenue_ops_learning_report"],
    )


def build_engine(
    learning_pipeline_engine=None,
    marketplace_engine=None,
    policy=None,
):
    return ProductionLearningCertificationEngine(
        learning_pipeline_certification_engine=learning_pipeline_engine,
        telemetry_engine=SimpleNamespace(),
        anomaly_engine=SimpleNamespace(),
        knowledge_sync_engine=SimpleNamespace(),
        evolution_feedback_engine=SimpleNamespace(),
        learning_governance_engine=SimpleNamespace(),
        observability_engine=SimpleNamespace(),
        marketplace_autonomy_engine=marketplace_engine or SimpleNamespace(),
        policy=policy or ProductionLearningCertificationPolicy(),
    )


def test_production_learning_certification_passes_with_human():
    engine = build_engine(
        learning_pipeline_engine=build_fake_26_7_engine("CERTIFIED"),
    )

    report = engine.certify(
        certified_by="human",
        evidence=build_full_evidence(),
    )

    assert report.status == CertificationStatus.CERTIFIED
    assert report.expires_at is not None


def test_production_learning_certification_conditional_for_system():
    engine = build_engine(
        learning_pipeline_engine=build_fake_26_7_engine("CERTIFIED"),
    )

    report = engine.certify(
        certified_by="system",
        evidence=build_full_evidence(),
    )

    assert report.status == CertificationStatus.CONDITIONALLY_CERTIFIED


def test_missing_26_7_certification_fails():
    engine = build_engine(
        learning_pipeline_engine=None,
    )

    report = engine.certify(
        certified_by="human",
        evidence=build_full_evidence(),
    )

    assert report.status == CertificationStatus.NOT_CERTIFIED


def test_missing_marketplace_learning_evidence_fails():
    engine = build_engine(
        learning_pipeline_engine=build_fake_26_7_engine("CERTIFIED"),
    )

    evidence = build_full_evidence()
    evidence.fraud_learning_evidence = []

    report = engine.certify(
        certified_by="human",
        evidence=evidence,
    )

    assert report.status == CertificationStatus.NOT_CERTIFIED


def test_certification_can_be_revoked():
    engine = build_engine(
        learning_pipeline_engine=build_fake_26_7_engine("CERTIFIED"),
    )

    report = engine.certify(
        certified_by="human",
        evidence=build_full_evidence(),
    )

    revoked = engine.revoke(
        report_id=report.id,
        reason="Marketplace learning regression detected.",
        revoked_by="operations",
    )

    assert revoked.status == CertificationStatus.REVOKED
