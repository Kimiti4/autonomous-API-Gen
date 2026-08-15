"""
Tests for Phase 30 — Autonomous Software Engineering Network.
"""

import pytest

from autonomous_network.engine import (
    AutonomousSoftwareEngineeringNetwork,
    StaticNetworkGovernanceGateway,
)
from autonomous_network.models import (
    ContractStatus,
    PipelineStageName,
    PipelineStatus,
)


def build_network(
    governance_decision: str = "ALLOW",
) -> AutonomousSoftwareEngineeringNetwork:
    return AutonomousSoftwareEngineeringNetwork(
        governance=StaticNetworkGovernanceGateway(decision=governance_decision),
        policy_version="constitution.v1",
    )


def register_two_orgs(network: AutonomousSoftwareEngineeringNetwork):
    network.register_organization(
        org_id="org_requirements",
        name="Requirements Organization",
        capabilities=["requirements", "architecture"],
        policy_version="constitution.v1",
        public_key_ref="key:org_requirements",
    )

    network.register_organization(
        org_id="org_delivery",
        name="Delivery Organization",
        capabilities=["compiler", "deployment", "monitoring"],
        policy_version="constitution.v1",
        public_key_ref="key:org_delivery",
    )


def test_end_to_end_pipeline_completes():
    network = build_network()

    register_two_orgs(network)

    contract = network.create_contract(
        parties=["org_requirements", "org_delivery"],
        objective="Build a billing system.",
        obligations=[
            "org_requirements produces requirements and ISR.",
            "org_delivery compiles, deploys, and monitors.",
        ],
    )

    network.approve_contract(
        contract_id=contract.contract_id,
        approver_id="human_governance_admin",
    )

    run = network.submit_objective(
        contract_id=contract.contract_id,
        objective="Generate a production-ready billing service.",
        requirements={
            "capability": "billing",
            "priority": "high",
        },
    )

    completed_run = network.run_pipeline(run.run_id)

    assert completed_run.status == PipelineStatus.COMPLETED

    artifacts = completed_run.artifacts

    assert PipelineStageName.REQUIREMENT_ANALYSIS.value in artifacts
    assert PipelineStageName.ISR_CONSTRUCTION.value in artifacts
    assert PipelineStageName.EVOLUTION.value in artifacts
    assert PipelineStageName.VERIFICATION.value in artifacts
    assert PipelineStageName.COMPILATION.value in artifacts
    assert PipelineStageName.DEPLOYMENT.value in artifacts
    assert PipelineStageName.MONITORING.value in artifacts
    assert PipelineStageName.LEARNING.value in artifacts

    assert "evolution_proposal" in artifacts[PipelineStageName.LEARNING.value]

    assert network.verify_events() is True

    snapshot = network.monitoring_snapshot()

    assert snapshot.completed_runs == 1
    assert snapshot.failed_runs == 0
    assert snapshot.active_contracts == 1

    memory_records = network.memory.query(entity_type="ARTIFACT")

    assert len(memory_records) > 0


def test_unattested_organization_cannot_form_contract():
    network = build_network()

    network.register_organization(
        org_id="org_good",
        name="Good Organization",
        capabilities=["architecture"],
        policy_version="constitution.v1",
        public_key_ref="key:org_good",
    )

    network.register_organization(
        org_id="org_bad",
        name="Unattested Organization",
        capabilities=["compiler"],
        policy_version="wrong-policy",
        public_key_ref="key:org_bad",
    )

    with pytest.raises(PermissionError):
        network.create_contract(
            parties=["org_good", "org_bad"],
            objective="Attempt unattested collaboration.",
        )


def test_governance_can_reject_contract():
    network = build_network(governance_decision="DENY")

    register_two_orgs(network)

    contract = network.create_contract(
        parties=["org_requirements", "org_delivery"],
        objective="Governance-rejected collaboration.",
    )

    with pytest.raises(PermissionError):
        network.approve_contract(
            contract_id=contract.contract_id,
            approver_id="human_governance_admin",
        )

    refreshed = network.contracts[contract.contract_id]

    assert refreshed.status == ContractStatus.REJECTED


def test_suspended_organization_blocks_pipeline_submission():
    network = build_network()

    register_two_orgs(network)

    contract = network.create_contract(
        parties=["org_requirements", "org_delivery"],
        objective="Collaboration before suspension.",
    )

    network.approve_contract(
        contract_id=contract.contract_id,
        approver_id="human_governance_admin",
    )

    network.suspend_organization("org_delivery")

    with pytest.raises(PermissionError):
        network.submit_objective(
            contract_id=contract.contract_id,
            objective="Attempt pipeline while organization suspended.",
        )


def test_missing_stage_adapter_fails_pipeline():
    network = build_network()

    register_two_orgs(network)

    contract = network.create_contract(
        parties=["org_requirements", "org_delivery"],
        objective="Pipeline with missing adapter.",
    )

    network.approve_contract(
        contract_id=contract.contract_id,
        approver_id="human_governance_admin",
    )

    run = network.submit_objective(
        contract_id=contract.contract_id,
        objective="Run pipeline with missing compilation adapter.",
    )

    del network.stage_adapters[PipelineStageName.COMPILATION]

    failed_run = network.run_pipeline(run.run_id)

    assert failed_run.status == PipelineStatus.FAILED

    snapshot = network.monitoring_snapshot()

    assert snapshot.failed_runs == 1
    assert snapshot.alerts_count > 0
