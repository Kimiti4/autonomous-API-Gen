"""
Tests for Phase 24.11 Marketplace Compliance, Audit, and Financial Certification.
"""

from product_factory.marketplace_compliance.engine import (
    MarketplaceComplianceEngine,
    MarketplaceCompliancePolicy,
)
from product_factory.marketplace_compliance.models import (
    ComplianceStatus,
    MarketplaceComplianceEvidence,
)


def build_full_evidence() -> MarketplaceComplianceEvidence:
    return MarketplaceComplianceEvidence(
        financial_reconciliation_refs=["reconciliation_report_1"],
        settlement_governance_refs=["settlement_approval_1"],
        refund_governance_refs=["refund_policy_1"],
        tax_evidence_refs=["tax_evidence_1"],
        fraud_controls_refs=["fraud_control_1"],
        sla_monitoring_refs=["sla_report_1"],
        audit_trail_refs=["audit_bundle_1"],
        marketplace_certification_refs=["marketplace_certification_1"],
        learning_certification_refs=["learning_certification_1"],
        security_controls_refs=["security_controls_1"],
    )


def test_compliance_certification_passes_with_human():
    engine = MarketplaceComplianceEngine(MarketplaceCompliancePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=build_full_evidence(),
    )

    assert report.status == ComplianceStatus.CERTIFIED
    assert report.expires_at is not None


def test_compliance_certification_fails_without_evidence():
    engine = MarketplaceComplianceEngine(MarketplaceCompliancePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=MarketplaceComplianceEvidence(),
    )

    assert report.status == ComplianceStatus.NOT_CERTIFIED


def test_compliance_certification_conditional_for_system():
    engine = MarketplaceComplianceEngine(MarketplaceCompliancePolicy())

    report = engine.certify(
        certified_by="system",
        evidence=build_full_evidence(),
    )

    assert report.status == ComplianceStatus.CONDITIONALLY_CERTIFIED


def test_compliance_report_can_be_revoked():
    engine = MarketplaceComplianceEngine(MarketplaceCompliancePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=build_full_evidence(),
    )

    revoked = engine.revoke(
        report_id=report.id,
        reason="Financial control regression detected.",
        revoked_by="compliance_admin",
    )

    assert revoked.status == ComplianceStatus.REVOKED


def test_audit_bundle_hash_exists():
    engine = MarketplaceComplianceEngine(MarketplaceCompliancePolicy())

    bundle = engine.build_audit_bundle(
        records=[
            {
                "event": "settlement_approved",
                "actor": "governance_admin",
            }
        ]
    )

    assert bundle.bundle_hash
