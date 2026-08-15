"""
Tests for Phase 27 ecosystem hardening.
"""

from ecosystem.engine import EcosystemEngine
from ecosystem.gateway import StaticGovernanceGateway
from ecosystem.models import (
    PartnerType,
    RoutingRequest,
    SLADefinition,
    SLAOperator,
)

from ecosystem.hardening.engine import (
    EcosystemHardeningEngine,
    EcosystemHardeningPolicy,
)
from ecosystem.hardening.models import EcosystemComplianceEvidence


def build_base_ecosystem():
    gateway = StaticGovernanceGateway(decision="ALLOW")

    ecosystem = EcosystemEngine(governance_gateway=gateway)

    treaty = ecosystem.federation.create_treaty(
        name="Federation A-B",
        source_marketplace_id="marketplace_a",
        target_marketplace_id="marketplace_b",
        revenue_share_pct=10.0,
        routing_policy={"mode": "active"},
    )

    ecosystem.federation.activate_treaty(
        treaty_id=treaty.id,
        actor_id="governance_admin",
        approval_ref="treaty_activation_approved",
    )

    partner = ecosystem.partners.register_partner(
        name="Trusted Vendor",
        partner_type=PartnerType.VENDOR,
        capabilities=["payments"],
        evidence_refs=["partner_certification_1"],
    )

    ecosystem.partners.activate_partner(
        partner_id=partner.id,
        actor_id="ecosystem_admin",
    )

    ecosystem.partners.adjust_trust(
        partner_id=partner.id,
        delta=0.3,
        reason="Initial trust bootstrap.",
    )

    contract = ecosystem.contracts.create_contract(
        partner_id=partner.id,
        marketplace_id="marketplace_a",
        contract_type="SERVICE_LEVEL",
    )

    ecosystem.contracts.add_sla(
        contract_id=contract.id,
        sla=SLADefinition(
            metric="p95_latency_ms",
            threshold=200.0,
            operator=SLAOperator.LTE,
        ),
    )

    return ecosystem, treaty, partner, contract


def build_hardening_engine(ecosystem):
    policy = EcosystemHardeningPolicy(
        min_partner_trust=0.60,
        max_revenue_share_pct=50.0,
        max_sla_breaches_before_escalation=2,
    )

    return EcosystemHardeningEngine(
        ecosystem_engine=ecosystem,
        governance_gateway=StaticGovernanceGateway(decision="ALLOW"),
        policy=policy,
    )


def test_treaty_risk_assessment():
    ecosystem, treaty, _, _ = build_base_ecosystem()
    hardening = build_hardening_engine(ecosystem)

    assessment = hardening.assess_treaty(treaty.id)

    assert assessment.risk_level.value == "LOW"
    assert assessment.requires_governance is False


def test_partner_trust_assessment():
    ecosystem, _, partner, _ = build_base_ecosystem()
    hardening = build_hardening_engine(ecosystem)

    assessment = hardening.assess_partner(partner.id)

    assert assessment.trust_score >= 0.60
    assert assessment.risk_level.value == "LOW"
    assert assessment.recommended_action == "ALLOW"


def test_guarded_routing_allows_low_risk_route():
    ecosystem, _, partner, _ = build_base_ecosystem()
    hardening = build_hardening_engine(ecosystem)

    decision = hardening.guarded_routing(
        RoutingRequest(
            source_marketplace_id="marketplace_a",
            product_id="product_1",
            candidate_marketplace_ids=["marketplace_b"],
            partner_id=partner.id,
        )
    )

    assert decision.allowed is True
    assert decision.base_decision is not None


def test_sla_enforcement_escalates_after_threshold():
    ecosystem, _, _, contract = build_base_ecosystem()
    hardening = build_hardening_engine(ecosystem)

    first = hardening.enforce_sla(
        contract_id=contract.id,
        metric="p95_latency_ms",
        value=300.0,
    )

    second = hardening.enforce_sla(
        contract_id=contract.id,
        metric="p95_latency_ms",
        value=350.0,
    )

    assert first.breach_detected is True
    assert first.escalated is False

    assert second.breach_detected is True
    assert second.escalated is True
    assert second.recommended_action == "ESCALATE_TO_GOVERNANCE"


def test_ecosystem_compliance_certification():
    ecosystem, _, _, _ = build_base_ecosystem()
    hardening = build_hardening_engine(ecosystem)

    evidence = EcosystemComplianceEvidence(
        governance_refs=["governance_report_1"],
        treaty_risk_refs=["treaty_risk_report_1"],
        partner_trust_refs=["partner_trust_report_1"],
        sla_refs=["sla_report_1"],
        financial_refs=["financial_control_report_1"],
        security_refs=["security_report_1"],
        learning_refs=["learning_certification_1"],
        audit_refs=["audit_bundle_1"],
    )

    report = hardening.certify_ecosystem(
        evidence=evidence,
        certified_by="human",
    )

    assert report.status.value == "CERTIFIED"


def test_ecosystem_observability_report():
    ecosystem, _, _, _ = build_base_ecosystem()
    hardening = build_hardening_engine(ecosystem)

    report = hardening.observability_report()

    assert report.active_treaties == 1
    assert report.active_partners == 1
    assert report.active_contracts == 1


def test_resilience_circuit_opens_after_failures():
    ecosystem, _, _, _ = build_base_ecosystem()
    hardening = build_hardening_engine(ecosystem)

    hardening.record_dependency_failure("partner_api")
    hardening.record_dependency_failure("partner_api")

    degraded = hardening.record_dependency_failure("partner_api")

    assert degraded.status.value == "OPEN"
    assert degraded.failure_count == 3
