"""
Tests for Phase 22.1 federated engineering organizations.
"""

from civilization.engine import CivilizationEngine
from civilization.federation.engine import (
    FederationEngine,
    StaticFederationGovernanceGateway,
)
from civilization.federation.models import (
    FederationCharter,
    FederationDecisionPolicy,
    VotePosition,
)
from civilization.models import OrganizationCharter


def create_organization(engine: CivilizationEngine, name: str):
    charter = OrganizationCharter(
        mission="Deliver governed engineering outcomes.",
        principles=[],
        required_roles=[],
        max_agents=10,
        high_impact_requires_governance=True,
    )

    return engine.create_organization(name=name, charter=charter)


def build_federation(governance_decision: str = "ALLOW", quorum_ratio: float = 0.5):
    civilization_engine = CivilizationEngine()

    federation_engine = FederationEngine(
        civilization_engine=civilization_engine,
        governance_gateway=StaticFederationGovernanceGateway(
            decision=governance_decision,
            reason="Static federation governance decision.",
        ),
    )

    org_one = create_organization(
        civilization_engine,
        "Billing Engineering Organization",
    )

    org_two = create_organization(
        civilization_engine,
        "Payments Engineering Organization",
    )

    charter = FederationCharter(
        mission="Coordinate cross-domain engineering initiatives.",
        principles=[
            "Evidence before action.",
            "Governance before high-impact change.",
        ],
        decision_policy=FederationDecisionPolicy.MAJORITY_WEIGHTED,
        quorum_ratio=quorum_ratio,
        high_impact_requires_governance=True,
    )

    federation = federation_engine.create_federation(
        name="Commerce Engineering Federation",
        charter=charter,
    )

    federation_engine.join_federation(
        federation_id=federation.id,
        organization_id=org_one.id,
        weight=1.0,
        jurisdictions=["billing"],
    )

    federation_engine.join_federation(
        federation_id=federation.id,
        organization_id=org_two.id,
        weight=1.0,
        jurisdictions=["payments"],
    )

    return civilization_engine, federation_engine, federation, org_one, org_two


def test_federation_initiative_delegation():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation()
    )

    initiative = federation_engine.create_initiative(
        federation_id=federation.id,
        title="Improve billing reliability",
        objective="Reduce billing failure rate.",
        initiative_type="architecture_review",
        required_roles=["software_architect"],
        high_impact=False,
        inputs={
            "target_ref": "billing_service",
        },
    )

    federation_engine.authorize_initiative(initiative.id)

    delegations = federation_engine.delegate_initiative_tasks(initiative.id)

    assert len(delegations) == 2

    refreshed_initiative = federation_engine.initiatives[initiative.id]

    assert refreshed_initiative.status.value == "EXECUTING"

    assert len(civilization_engine.tasks) == 2


def test_federation_council_approves_high_impact_initiative():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation()
    )

    initiative = federation_engine.create_initiative(
        federation_id=federation.id,
        title="Replace authentication architecture",
        objective="Improve authentication security posture.",
        initiative_type="architecture_change",
        required_roles=["software_architect", "security_engineer"],
        high_impact=True,
        inputs={
            "target_ref": "authentication_service",
        },
    )

    decision = federation_engine.propose_decision(
        federation_id=federation.id,
        title="Authorize authentication initiative",
        decision_type="INITIATIVE_AUTHORIZATION",
        initiative_id=initiative.id,
        rationale="Security evidence supports the change.",
    )

    federation_engine.cast_vote(
        decision_id=decision.id,
        organization_id=org_one.id,
        position=VotePosition.APPROVE,
        reason="Billing organization approves.",
    )

    federation_engine.cast_vote(
        decision_id=decision.id,
        organization_id=org_two.id,
        position=VotePosition.APPROVE,
        reason="Payments organization approves.",
    )

    tallied = federation_engine.tally_decision(decision.id)

    assert tallied.status.value == "APPROVED"

    refreshed_initiative = federation_engine.initiatives[initiative.id]

    assert refreshed_initiative.status.value == "COORDINATING"


def test_cross_organization_conflict_resolution():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation()
    )

    conflict = federation_engine.create_conflict(
        federation_id=federation.id,
        party_organization_ids=[org_one.id, org_two.id],
        subject_ref="invoice_settlement_boundary",
        conflict_type="JURISDICTION",
    )

    resolved = federation_engine.resolve_conflict(
        conflict_id=conflict.id,
        resolved_by="federation_coordinator",
        rationale="Boundary assigned to billing organization.",
    )

    assert resolved.status.value == "RESOLVED"


def test_high_impact_initiative_denied_by_governance():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation(governance_decision="DENY")
    )

    initiative = federation_engine.create_initiative(
        federation_id=federation.id,
        title="High-impact infrastructure change",
        objective="Replace deployment topology.",
        initiative_type="infrastructure_change",
        high_impact=True,
        inputs={
            "target_ref": "deployment_topology",
        },
    )

    denied = federation_engine.authorize_initiative(initiative.id)

    assert denied.status.value == "FAILED"


def test_security_veto_blocks_decision():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation()
    )

    security_org = create_organization(
        civilization_engine,
        "Security Engineering Organization",
    )

    federation_engine.join_federation(
        federation_id=federation.id,
        organization_id=security_org.id,
        weight=1.0,
        jurisdictions=["security"],
    )

    initiative = federation_engine.create_initiative(
        federation_id=federation.id,
        title="High-impact security change",
        objective="Change authentication architecture.",
        initiative_type="security_change",
        high_impact=False,
        member_organization_ids=[org_one.id, security_org.id],
    )

    decision = federation_engine.propose_decision(
        federation_id=federation.id,
        title="Authorize security initiative",
        decision_type="INITIATIVE_AUTHORIZATION",
        initiative_id=initiative.id,
    )

    federation_engine.cast_vote(
        decision_id=decision.id,
        organization_id=org_one.id,
        position=VotePosition.APPROVE,
    )

    federation_engine.cast_vote(
        decision_id=decision.id,
        organization_id=security_org.id,
        position=VotePosition.REJECT,
        reason="Security concerns.",
    )

    tallied = federation_engine.tally_decision(decision.id)

    assert tallied.result == "SECURITY_VETO"


def test_quorum_enforcement():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation(quorum_ratio=0.6)
    )

    initiative = federation_engine.create_initiative(
        federation_id=federation.id,
        title="Quorum test initiative",
        objective="Test quorum.",
        initiative_type="test_task",
        high_impact=False,
        member_organization_ids=[org_one.id, org_two.id],
    )

    decision = federation_engine.propose_decision(
        federation_id=federation.id,
        title="Authorize test initiative",
        decision_type="INITIATIVE_AUTHORIZATION",
        initiative_id=initiative.id,
    )

    federation_engine.cast_vote(
        decision_id=decision.id,
        organization_id=org_one.id,
        position=VotePosition.APPROVE,
    )

    tallied = federation_engine.tally_decision(decision.id)

    assert tallied.status.value == "ESCALATED"
    assert tallied.result == "QUORUM_NOT_MET"


def test_federation_report():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation()
    )

    federation_engine.create_initiative(
        federation_id=federation.id,
        title="Report test initiative",
        objective="Test federation report.",
        initiative_type="test_task",
        high_impact=False,
    )

    report = federation_engine.federation_report(federation.id)

    assert report["counts"]["members"] == 2
    assert report["counts"]["initiatives"] == 1


def test_suspend_membership():
    civilization_engine, federation_engine, federation, org_one, org_two = (
        build_federation()
    )

    federation_engine.suspend_membership(
        federation_id=federation.id,
        organization_id=org_two.id,
        reason="Organization under review.",
    )

    refreshed_membership = federation_engine.memberships[federation.id][
        org_two.id
    ]

    assert refreshed_membership.status.value == "SUSPENDED"

    active_count = sum(
        1
        for membership in federation_engine.memberships[federation.id].values()
        if membership.status.value == "ACTIVE"
    )

    assert active_count == 1
