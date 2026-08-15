"""
Tests for Phase 21.7 evolutionary governance, safety interlocks, and promotion.
"""

import pytest

from evolution.governance_safety import (
    EvolutionEvidence,
    SafetyInterlockEngine,
    SafetyInterlockPolicy,
)
from evolution.promotion import (
    PromotionControlEngine,
    PromotionControlPolicy,
    PromotionError,
    PromotionRequestStatus,
    StaticGovernanceGateway,
)


def passing_evidence() -> EvolutionEvidence:
    return EvolutionEvidence(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        isr_content_hash="sha256:candidate",
        simulation_status="PASSED",
        verification_valid=True,
        fitness_passed=True,
        objectives={
            "simplicity": 0.8,
            "modularity": 0.9,
        },
        constraints={
            "simulation_passed": True,
            "verification_valid": True,
        },
        compiler_passed=True,
        feedback_passed=True,
        critical_incident=False,
        critical_security_finding=False,
        pareto_selected=True,
        complexity=12.0,
        public_api_removed=False,
        breaking_changes_allowed=False,
        rollback_plan={
            "steps": [
                "Restore parent ISR.",
            ],
        },
    )


def test_safety_interlocks_pass():
    engine = SafetyInterlockEngine()

    report = engine.evaluate(passing_evidence())

    assert report.passed is True
    assert report.error_count == 0


def test_safety_interlocks_fail_without_verification():
    engine = SafetyInterlockEngine()

    evidence = passing_evidence()
    evidence.verification_valid = False

    report = engine.evaluate(evidence)

    assert report.passed is False
    assert any(
        issue.code == "VERIFICATION_NOT_VALID"
        for issue in report.issues
    )


def test_safety_interlocks_fail_on_critical_incident():
    engine = SafetyInterlockEngine()

    evidence = passing_evidence()
    evidence.critical_incident = True

    report = engine.evaluate(evidence)

    assert report.passed is False
    assert any(
        issue.code == "CRITICAL_INCIDENT_PRESENT"
        for issue in report.issues
    )


def test_promotion_flow_with_allow():
    engine = PromotionControlEngine(
        governance_gateway=StaticGovernanceGateway(
            decision="ALLOW",
            reason="Allowed.",
        ),
        policy=PromotionControlPolicy(),
    )

    request = engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="production",
        actor_id="tester",
        evidence=passing_evidence(),
    )

    assert request.status == PromotionRequestStatus.APPROVED

    promoted = engine.promote(request.id, "tester")

    assert promoted.status == PromotionRequestStatus.PROMOTED

    rolled_back = engine.rollback(
        request.id,
        "tester",
        "Test rollback.",
    )

    assert rolled_back.status == PromotionRequestStatus.ROLLED_BACK


def test_promotion_flow_with_denial():
    engine = PromotionControlEngine(
        governance_gateway=StaticGovernanceGateway(
            decision="DENY",
            reason="Denied by governance.",
        ),
        policy=PromotionControlPolicy(),
    )

    request = engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="production",
        actor_id="tester",
        evidence=passing_evidence(),
    )

    assert request.status == PromotionRequestStatus.GOVERNANCE_DENIED

    with pytest.raises(PromotionError):
        engine.promote(request.id, "tester")


def test_promotion_flow_with_required_approval():
    engine = PromotionControlEngine(
        governance_gateway=StaticGovernanceGateway(
            decision="REQUIRE_APPROVAL",
            reason="Human approval required.",
        ),
        policy=PromotionControlPolicy(),
    )

    request = engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="production",
        actor_id="tester",
        evidence=passing_evidence(),
    )

    assert request.status == PromotionRequestStatus.GOVERNANCE_PENDING

    approved = engine.approve(
        request.id,
        "human_approver",
        "Approved after review.",
    )

    assert approved.status == PromotionRequestStatus.APPROVED

    promoted = engine.promote(request.id, "tester")

    assert promoted.status == PromotionRequestStatus.PROMOTED


def test_promotion_flow_with_safety_failure():
    engine = PromotionControlEngine(
        governance_gateway=StaticGovernanceGateway(
            decision="ALLOW",
            reason="Allowed.",
        ),
        policy=PromotionControlPolicy(),
    )

    evidence = passing_evidence()
    evidence.fitness_passed = False

    request = engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="production",
        actor_id="tester",
        evidence=evidence,
    )

    assert request.status == PromotionRequestStatus.SAFETY_FAILED
    assert request.safety_report is not None
    assert request.safety_report.passed is False

    with pytest.raises(PromotionError):
        engine.promote(request.id, "tester")


def test_promotion_flow_without_governance_requirement():
    engine = PromotionControlEngine(
        governance_gateway=StaticGovernanceGateway(
            decision="DENY",
            reason="Should not reach governance.",
        ),
        policy=PromotionControlPolicy(
            governance_required_environments=["production"],
        ),
    )

    request = engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="staging",
        actor_id="tester",
        evidence=passing_evidence(),
    )

    assert request.status == PromotionRequestStatus.APPROVED
    assert request.governance_decision is None


def test_promotion_packet_includes_all_state():
    engine = PromotionControlEngine(
        governance_gateway=StaticGovernanceGateway(
            decision="ALLOW",
            reason="Allowed.",
        ),
        policy=PromotionControlPolicy(),
    )

    request = engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="production",
        actor_id="tester",
        evidence=passing_evidence(),
    )

    engine.promote(request.id, "tester")

    packet = engine.get_packet(request.id)

    assert packet.request.id == request.id
    assert packet.evidence is not None
    assert packet.safety_report is not None
    assert packet.governance_decision is not None
    assert packet.governance_decision.decision == "ALLOW"


def test_promotion_flow_fail_closed_without_governance_gateway():
    engine = PromotionControlEngine(
        governance_gateway=None,
        policy=PromotionControlPolicy(
            auto_submit_governance=True,
            fail_closed_if_governance_unavailable=True,
        ),
    )

    request = engine.create_promotion_request(
        proposal_id="proposal_1",
        candidate_id="candidate_1",
        environment="production",
        actor_id="tester",
        evidence=passing_evidence(),
    )

    assert request.status == PromotionRequestStatus.GOVERNANCE_DENIED
    assert request.governance_decision is not None
    assert request.governance_decision.decision == "DENY"
