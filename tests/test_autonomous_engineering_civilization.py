"""
Tests for Phase 22 Autonomous Engineering Civilization.
"""

import pytest

from civilization.engine import (
    CivilizationEngine,
    CivilizationError,
    StaticCivilizationGovernanceGateway,
)
from civilization.models import OrganizationCharter


def build_engine(governance_decision: str = "ALLOW") -> CivilizationEngine:
    return CivilizationEngine(
        governance_gateway=StaticCivilizationGovernanceGateway(
            decision=governance_decision,
            reason="Static governance decision.",
        )
    )


def create_basic_organization(engine: CivilizationEngine):
    charter = OrganizationCharter(
        mission="Deliver governed engineering outcomes.",
        principles=[
            "Evidence before action.",
            "Governance before production change.",
        ],
        required_roles=[
            "software_architect",
            "backend_engineer",
            "security_engineer",
        ],
        max_agents=10,
        high_impact_requires_governance=True,
    )

    organization = engine.create_organization(
        name="Platform Engineering Organization",
        charter=charter,
    )

    architect = engine.create_agent(
        name="Architect Agent",
        role_id="software_architect",
        trust_level=0.9,
    )

    backend_engineer = engine.create_agent(
        name="Backend Agent",
        role_id="backend_engineer",
        trust_level=0.8,
    )

    security_engineer = engine.create_agent(
        name="Security Agent",
        role_id="security_engineer",
        trust_level=0.85,
    )

    engine.assign_agent_to_organization(organization.id, architect.agent_id)
    engine.assign_agent_to_organization(organization.id, backend_engineer.agent_id)
    engine.assign_agent_to_organization(organization.id, security_engineer.agent_id)

    return organization, architect, backend_engineer, security_engineer


def test_organization_task_lifecycle():
    engine = build_engine()

    organization, *_ = create_basic_organization(engine)

    task = engine.create_task(
        organization_id=organization.id,
        title="Review billing service architecture",
        objective="Improve billing service reliability.",
        task_type="architecture_review",
        required_roles=["software_architect", "backend_engineer"],
        inputs={
            "target_ref": "billing_service",
        },
    )

    recommendations = engine.run_task(task.id)

    assert len(recommendations) == 2

    decision = engine.finalize_task(task.id)

    assert decision.status.value == "COMPLETED"

    refreshed_task = engine.get_task(task.id)

    assert refreshed_task.status.value == "COMPLETED"


def test_conflict_detection_and_resolution():
    engine = build_engine()

    organization, *_ = create_basic_organization(engine)

    task = engine.create_task(
        organization_id=organization.id,
        title="Security review",
        objective="Resolve authentication concern.",
        task_type="security_review",
        required_roles=["backend_engineer", "security_engineer"],
        inputs={
            "target_ref": "authentication_service",
        },
    )

    engine.run_task(task.id)

    conflicts = engine.detect_conflicts(task.id)

    assert len(conflicts) >= 1

    decision = engine.finalize_task(task.id)

    assert decision.status.value == "COMPLETED"

    resolved_conflicts = engine.list_conflicts(task.id)

    assert resolved_conflicts
    assert all(
        conflict.status.value == "RESOLVED"
        for conflict in resolved_conflicts
    )


def test_high_impact_task_denied_by_governance():
    engine = build_engine(governance_decision="DENY")

    organization, *_ = create_basic_organization(engine)

    task = engine.create_task(
        organization_id=organization.id,
        title="High-impact architecture change",
        objective="Change authentication architecture.",
        task_type="architecture_change",
        required_roles=["software_architect", "security_engineer"],
        inputs={
            "target_ref": "authentication_service",
        },
        high_impact=True,
    )

    engine.run_task(task.id)

    decision = engine.finalize_task(task.id)

    assert decision.status.value == "FAILED"

    refreshed_task = engine.get_task(task.id)

    assert refreshed_task.status.value == "FAILED"


def test_leadership_election():
    engine = build_engine()

    organization, architect, *_ = create_basic_organization(engine)

    term = engine.elect_leader(organization.id)

    assert term.leader_agent_id == architect.agent_id

    refreshed_organization = engine.organizations[organization.id]

    assert refreshed_organization.leader_agent_id == architect.agent_id


def test_organizational_memory_records():
    engine = build_engine()

    organization, *_ = create_basic_organization(engine)

    records = engine.get_memory(organization.id)

    assert len(records) >= 4

    record_types = {record.record_type for record in records}

    assert "ORGANIZATION_CREATED" in record_types
    assert "AGENT_ASSIGNED" in record_types


def test_communication_bus_records_events():
    engine = build_engine()

    organization, *_ = create_basic_organization(engine)

    engine.create_task(
        organization_id=organization.id,
        title="Test task",
        objective="Test objective.",
        task_type="test_task",
    )

    organization_created_messages = engine.bus.list_messages(
        topic="ORGANIZATION_CREATED",
        organization_id=organization.id,
    )

    assert len(organization_created_messages) == 1

    task_created_messages = engine.bus.list_messages(
        topic="TASK_CREATED",
    )

    assert len(task_created_messages) == 1


def test_agent_is_not_assigned_recommending():
    engine = build_engine()

    organization, *_ = create_basic_organization(engine)

    unassigned_agent = engine.create_agent(
        name="Unassigned Agent",
        role_id="qa_engineer",
        trust_level=0.5,
    )

    task = engine.create_task(
        organization_id=organization.id,
        title="Test task",
        objective="Test objective.",
        task_type="test_task",
        required_roles=["software_architect"],
    )

    engine.allocate_task(task.id)

    from civilization.models import RecommendationInput

    with pytest.raises(CivilizationError):
        engine.submit_recommendation(
            task_id=task.id,
            agent_id=unassigned_agent.agent_id,
            payload=RecommendationInput(
                action="test",
                target_ref="test",
                rationale="Test rationale.",
            ),
        )


def test_organization_at_max_agents():
    engine = build_engine()

    charter = OrganizationCharter(
        mission="Deliver outcomes.",
        required_roles=["software_architect"],
        max_agents=1,
    )

    organization = engine.create_organization(
        name="Small Org",
        charter=charter,
    )

    agent1 = engine.create_agent(
        name="Agent 1",
        role_id="software_architect",
        trust_level=0.5,
    )

    engine.assign_agent_to_organization(organization.id, agent1.agent_id)

    agent2 = engine.create_agent(
        name="Agent 2",
        role_id="software_architect",
        trust_level=0.5,
    )

    with pytest.raises(CivilizationError):
        engine.assign_agent_to_organization(organization.id, agent2.agent_id)


def test_unknown_role_rejected():
    engine = build_engine()

    with pytest.raises(CivilizationError):
        engine.create_agent(
            name="Invalid Agent",
            role_id="nonexistent_role",
            trust_level=0.5,
        )
