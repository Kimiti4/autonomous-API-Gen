"""
Tests for Phase 21 Self-Evolution Engine.
"""

from fastapi.testclient import TestClient

from evolution.api import create_app
from evolution.engine import EvolutionPolicy, SelfEvolutionEngine
from evolution.governance import StaticGovernanceClient


def base_isr() -> dict:
    return {
        "isr_id": "isr_billing_001",
        "version": "1.0.0",
        "name": "Billing System",
        "domains": [
            {
                "name": "billing",
                "services": [
                    {
                        "name": "BillingService",
                        "apis": [
                            {
                                "name": "createInvoice"
                            }
                        ],
                        "depends_on": [],
                    }
                ],
            }
        ],
        "security": {
            "authentication": "OIDC",
        },
        "observability": {
            "metrics": True,
        },
        "deployment": {
            "container": True,
        },
        "testing": {
            "unit_tests": True,
        },
    }


def mutation_payload() -> dict:
    return {
        "id": "mutation_add_list_invoices",
        "operator": "architecture_mutator",
        "chromosome_family": "backend",
        "gene_id": "billing_api_surface",
        "rationale": "Add invoice listing capability.",
        "operations": [
            {
                "operation": "ADD_ITEM",
                "path": "domains.0.services.0.apis",
                "value": {
                    "name": "listInvoices"
                },
            }
        ],
    }


def proposal_payload(target_type="APPLICATION_ARCHITECTURE") -> dict:
    return {
        "request": {
            "title": "Add invoice listing capability",
            "description": "Evolve billing architecture to support listing invoices.",
            "target_type": target_type,
            "target_ref": "billing_system",
            "base_isr": base_isr(),
            "mutation": mutation_payload(),
            "high_impact": False,
            "allow_breaking_changes": False,
            "environment": "development",
        },
        "actor_id": "test_architect",
    }


def build_engine(governance_decision: str = "ALLOW") -> SelfEvolutionEngine:
    return SelfEvolutionEngine(
        governance_client=StaticGovernanceClient(
            decision=governance_decision,
            reason="Static governance decision.",
        ),
        policy=EvolutionPolicy(),
    )


def run_lifecycle_until_submit(client: TestClient, target_type="APPLICATION_ARCHITECTURE"):
    proposal_response = client.post(
        "/v1/evolution/proposals",
        json=proposal_payload(target_type),
    )

    assert proposal_response.status_code == 200

    proposal_id = proposal_response.json()["id"]

    mutate_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/mutate"
    )
    assert mutate_response.status_code == 200

    simulate_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/simulate"
    )
    assert simulate_response.status_code == 200

    verify_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/verify"
    )
    assert verify_response.status_code == 200

    fitness_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/fitness"
    )
    assert fitness_response.status_code == 200

    submit_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/submit"
    )
    assert submit_response.status_code == 200

    return proposal_id, submit_response.json()


def test_full_evolution_lifecycle():
    engine = build_engine("ALLOW")
    app = create_app(engine)
    client = TestClient(app)

    proposal_id, submitted = run_lifecycle_until_submit(client)

    assert submitted["status"] == "APPROVED"

    promote_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/promote",
        json={
            "environment": "staging"
        },
    )

    assert promote_response.status_code == 200

    promotion = promote_response.json()

    assert promotion["status"] == "ACTIVE"

    proposal_response = client.get(
        f"/v1/evolution/proposals/{proposal_id}"
    )

    assert proposal_response.json()["status"] == "PROMOTED"

    rollback_response = client.post(
        f"/v1/evolution/promotions/{promotion['id']}/rollback",
        json={
            "reason": "Test rollback."
        },
    )

    assert rollback_response.status_code == 200

    rolled_back = rollback_response.json()

    assert rolled_back["status"] == "ROLLED_BACK"

    final_proposal = client.get(
        f"/v1/evolution/proposals/{proposal_id}"
    )

    assert final_proposal.json()["status"] == "ROLLED_BACK"


def test_high_impact_requires_approval():
    engine = build_engine("ALLOW")
    app = create_app(engine)
    client = TestClient(app)

    proposal_id, submitted = run_lifecycle_until_submit(
        client,
        target_type="PLATFORM_CORE",
    )

    assert submitted["status"] == "PENDING_APPROVAL"

    approve_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/approve",
        json={
            "approver_id": "human_architect",
            "decision": "APPROVED",
            "comments": "Approved after review.",
        },
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"


def test_governance_denial_blocks_evolution():
    engine = build_engine("DENY")
    app = create_app(engine)
    client = TestClient(app)

    proposal_id, submitted = run_lifecycle_until_submit(client)

    assert submitted["status"] == "REJECTED"

    promote_response = client.post(
        f"/v1/evolution/proposals/{proposal_id}/promote",
        json={
            "environment": "staging"
        },
    )

    assert promote_response.status_code == 409
