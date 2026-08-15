"""
Tests for Phase 24.12 Phase 24 Closure Certification.
"""

from product_factory.phase24_closure.engine import (
    Phase24ClosureEngine,
    Phase24ClosurePolicy,
)
from product_factory.phase24_closure.models import (
    ClosureStatus,
    Phase24Evidence,
)


def build_full_phase24_evidence() -> Phase24Evidence:
    return Phase24Evidence(
        product_factory_core_refs=["product_factory_core_green"],
        monetization_ops_refs=["phase_24_5_green"],
        marketplace_foundation_refs=["phase_24_6_green"],
        product_certification_publishing_refs=["phase_24_7_green"],
        marketplace_design_economics_refs=["phase_24_8_green"],
        financial_hardening_refs=["phase_24_9_green"],
        reconciliation_settlement_refs=["phase_24_10_green"],
        marketplace_compliance_refs=["phase_24_11_green"],
        learning_certification_refs=["phase_26_8_green"],
        governance_integration_refs=["phase_28_integration_green"],
        observability_refs=["observability_green"],
        documentation_refs=["phase_24_documentation_complete"],
        test_suite_refs=["pytest_all_green"],
    )


def test_phase24_closure_passes_with_human():
    engine = Phase24ClosureEngine(Phase24ClosurePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=build_full_phase24_evidence(),
    )

    assert report.status == ClosureStatus.CERTIFIED
    assert report.expires_at is not None


def test_phase24_closure_fails_without_evidence():
    engine = Phase24ClosureEngine(Phase24ClosurePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=Phase24Evidence(),
    )

    assert report.status == ClosureStatus.NOT_CERTIFIED


def test_phase24_closure_conditional_for_system():
    engine = Phase24ClosureEngine(Phase24ClosurePolicy())

    report = engine.certify(
        certified_by="system",
        evidence=build_full_phase24_evidence(),
    )

    assert report.status == ClosureStatus.CONDITIONALLY_CERTIFIED


def test_phase24_closure_can_be_revoked():
    engine = Phase24ClosureEngine(Phase24ClosurePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=build_full_phase24_evidence(),
    )

    revoked = engine.revoke(
        report_id=report.id,
        reason="Phase 24 regression detected.",
        revoked_by="architecture_board",
    )

    assert revoked.status == ClosureStatus.REVOKED
