"""
Tests for Phase 27 Closure Certification.
"""

from ecosystem.phase27_closure.engine import (
    Phase27ClosureEngine,
    Phase27ClosurePolicy,
)
from ecosystem.phase27_closure.models import (
    ClosureStatus,
    Phase27Evidence,
)


def build_full_phase27_evidence() -> Phase27Evidence:
    return Phase27Evidence(
        ecosystem_core_refs=["phase_27_core_green"],
        federation_treaty_refs=["federation_treaty_green"],
        partner_identity_trust_refs=["partner_identity_trust_green"],
        cross_marketplace_routing_refs=["cross_marketplace_routing_green"],
        b2b_contract_sla_refs=["b2b_contract_sla_green"],
        ecosystem_hardening_refs=["ecosystem_hardening_green"],
        treaty_risk_refs=["treaty_risk_green"],
        partner_trust_hardening_refs=["partner_trust_hardening_green"],
        guarded_routing_refs=["guarded_routing_green"],
        sla_enforcement_refs=["sla_enforcement_green"],
        ecosystem_compliance_refs=["ecosystem_compliance_green"],
        audit_bundle_refs=["ecosystem_audit_bundle_green"],
        observability_refs=["ecosystem_observability_green"],
        resilience_refs=["ecosystem_resilience_green"],
        governance_integration_refs=["phase_28_integration_green"],
        learning_certification_refs=["phase_26_8_green"],
        documentation_refs=["phase_27_documentation_complete"],
        test_suite_refs=["pytest_phase27_green"],
    )


def test_phase27_closure_passes_with_human():
    engine = Phase27ClosureEngine(Phase27ClosurePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=build_full_phase27_evidence(),
    )

    assert report.status == ClosureStatus.CERTIFIED
    assert report.expires_at is not None


def test_phase27_closure_fails_without_evidence():
    engine = Phase27ClosureEngine(Phase27ClosurePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=Phase27Evidence(),
    )

    assert report.status == ClosureStatus.NOT_CERTIFIED


def test_phase27_closure_conditional_for_system():
    engine = Phase27ClosureEngine(Phase27ClosurePolicy())

    report = engine.certify(
        certified_by="system",
        evidence=build_full_phase27_evidence(),
    )

    assert report.status == ClosureStatus.CONDITIONALLY_CERTIFIED


def test_phase27_closure_can_be_revoked():
    engine = Phase27ClosureEngine(Phase27ClosurePolicy())

    report = engine.certify(
        certified_by="human",
        evidence=build_full_phase27_evidence(),
    )

    revoked = engine.revoke(
        report_id=report.id,
        reason="Phase 27 regression detected.",
        revoked_by="architecture_board",
    )

    assert revoked.status == ClosureStatus.REVOKED
