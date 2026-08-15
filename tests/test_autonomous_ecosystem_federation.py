"""
Tests for Phase 27 Autonomous Ecosystem and Cross-Marketplace Federation.
"""

import pytest

from ecosystem.engine import EcosystemEngine
from ecosystem.gateway import StaticGovernanceGateway
from ecosystem.models import (
    PartnerType,
    RoutingRequest,
    SLADefinition,
    SLAOperator,
)


def build_engine(governance_decision: str = "ALLOW") -> EcosystemEngine:
    gateway = StaticGovernanceGateway(decision=governance_decision)
    return EcosystemEngine(governance_gateway=gateway)


def test_treaty_activation_requires_governance():
    engine = build_engine("ALLOW")

    treaty = engine.federation.create_treaty(
        name="Marketplace Federation",
        source_marketplace_id="marketplace_a",
        target_marketplace_id="marketplace_b",
        revenue_share_pct=10.0,
    )

    activated = engine.federation.activate_treaty(
        treaty_id=treaty.id,
        actor_id="governance_admin",
    )

    assert activated.status.value == "ACTIVE"


def test_treaty_activation_denied_by_governance():
    engine = build_engine("DENY")

    treaty = engine.federation.create_treaty(
        name="Denied Federation",
        source_marketplace_id="marketplace_a",
        target_marketplace_id="marketplace_b",
        revenue_share_pct=10.0,
    )

    with pytest.raises(PermissionError):
        engine.federation.activate_treaty(
            treaty_id=treaty.id,
            actor_id="governance_admin",
        )


def test_routing_selects_active_treaty_target():
    engine = build_engine("ALLOW")

    treaty = engine.federation.create_treaty(
        name="Federation A-B",
        source_marketplace_id="marketplace_a",
        target_marketplace_id="marketplace_b",
        revenue_share_pct=15.0,
    )

    engine.federation.activate_treaty(
        treaty_id=treaty.id,
        actor_id="governance_admin",
    )

    decision = engine.routing.evaluate(
        RoutingRequest(
            source_marketplace_id="marketplace_a",
            product_id="product_1",
            candidate_marketplace_ids=[
                "marketplace_b",
                "marketplace_c",
            ],
        )
    )

    assert decision.selected_marketplace_id == "marketplace_b"
    assert decision.score > 0.5


def test_partner_trust_and_activation():
    engine = build_engine("ALLOW")

    partner = engine.partners.register_partner(
        name="Autonomous Vendor",
        partner_type=PartnerType.VENDOR,
        capabilities=["payment_processing"],
        evidence_refs=["certification_1"],
    )

    assert partner.status.value == "PENDING"

    activated = engine.partners.activate_partner(
        partner_id=partner.id,
        actor_id="ecosystem_admin",
    )

    assert activated.status.value == "ACTIVE"

    adjusted = engine.partners.adjust_trust(
        partner_id=partner.id,
        delta=0.2,
        reason="Strong SLA history.",
    )

    assert adjusted.trust_score == 0.7


def test_sla_breach_detection():
    engine = build_engine("ALLOW")

    partner = engine.partners.register_partner(
        name="SLA Partner",
        partner_type=PartnerType.VENDOR,
    )

    contract = engine.contracts.create_contract(
        partner_id=partner.id,
        marketplace_id="marketplace_a",
        contract_type="SERVICE_LEVEL",
    )

    engine.contracts.add_sla(
        contract_id=contract.id,
        sla=SLADefinition(
            metric="p95_latency_ms",
            threshold=200.0,
            operator=SLAOperator.LTE,
        ),
    )

    breach = engine.contracts.ingest_metric(
        contract_id=contract.id,
        metric="p95_latency_ms",
        value=350.0,
    )

    assert breach is not None
    assert breach.metric == "p95_latency_ms"
    assert breach.observed_value == 350.0


def test_governance_pending_state():
    gateway = StaticGovernanceGateway(decision="REQUIRE_APPROVAL", reason="Manual review required.")
    engine = EcosystemEngine(governance_gateway=gateway)

    treaty = engine.federation.create_treaty(
        name="Manual Review Treaty",
        source_marketplace_id="marketplace_a",
        target_marketplace_id="marketplace_b",
        revenue_share_pct=5.0,
    )

    activated = engine.federation.activate_treaty(
        treaty_id=treaty.id,
        actor_id="governance_admin",
    )
    assert activated.status.value == "PENDING_GOVERNANCE"
    assert activated.governance_ref is None


def test_ecosystem_sync_and_report():
    engine = build_engine("ALLOW")

    treaty = engine.federation.create_treaty(
        name="Sync Treaty",
        source_marketplace_id="marketplace_a",
        target_marketplace_id="marketplace_b",
        revenue_share_pct=12.0,
    )
    engine.federation.activate_treaty(treaty_id=treaty.id, actor_id="governance_admin")

    partner = engine.partners.register_partner(name="Sync Partner", partner_type=PartnerType.VENDOR)
    engine.partners.activate_partner(partner_id=partner.id, actor_id="admin")

    contract = engine.contracts.create_contract(
        partner_id=partner.id,
        marketplace_id="marketplace_a",
        contract_type="SLA",
    )

    synced = engine.sync_all()
    assert synced == 3  # one treaty + one partner + one contract

    report = engine.report()
    assert report.active_treaties == 1
    assert report.active_partners == 1
    assert report.active_contracts == 1
    assert report.synced_records == 3


def test_no_active_link_blocks_routing():
    engine = build_engine("ALLOW")
    with pytest.raises(ValueError):
        engine.routing.evaluate(
            RoutingRequest(source_marketplace_id="marketplace_a", product_id="p1")
        )


def test_api_routes_work():
    pytest.importorskip("httpx")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from ecosystem.api import enable_ecosystem

    app = FastAPI()
    enable_ecosystem(app, governance_gateway=StaticGovernanceGateway(decision="ALLOW"))
    client = TestClient(app)

    treaty_resp = client.post(
        "/v1/ecosystem/federations/treaties",
        json={
            "name": "API Treaty",
            "source_marketplace_id": "marketplace_a",
            "target_marketplace_id": "marketplace_b",
            "revenue_share_pct": 10.0,
        },
    )
    assert treaty_resp.status_code == 201
    treaty_id = treaty_resp.json()["id"]

    activate_resp = client.post(
        f"/v1/ecosystem/federations/treaties/{treaty_id}/activate",
        json={"actor_id": "governance_admin"},
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["status"] == "ACTIVE"

    partner_resp = client.post(
        "/v1/ecosystem/partners",
        json={"name": "API Partner", "partner_type": "VENDOR"},
    )
    assert partner_resp.status_code == 201

    report_resp = client.get("/v1/ecosystem/report")
    assert report_resp.status_code == 200
    assert report_resp.json()["active_treaties"] == 1


# ── Real Phase 28 GovernanceKernel integration ──────────────────────────────

def test_build_ecosystem_governance_kernel_default_allow():
    pytest.importorskip("constitutional_architecture")
    from ecosystem.gateway import build_ecosystem_governance_kernel

    kernel, policy_set = build_ecosystem_governance_kernel()
    assert policy_set.status.value == "ACTIVE"
    assert len(policy_set.policy_rules) == len(
        [
            "FEDERATION_TREATY_ACTIVATION",
            "PARTNER_ONBOARDING_HIGH_RISK",
            "CROSS_MARKETPLACE_ROUTING_POLICY_CHANGE",
            "B2B_SLA_PENALTY_ENFORCEMENT",
            "ECOSYSTEM_SUSPENSION",
        ]
    )


def test_phase28_kernel_allows_normal_actor():
    pytest.importorskip("constitutional_architecture")
    from ecosystem.gateway import (
        GovernanceKernelGateway,
        build_ecosystem_governance_kernel,
    )

    kernel, _ = build_ecosystem_governance_kernel()
    gateway = GovernanceKernelGateway(kernel)

    decision = gateway.evaluate_action(
        "FEDERATION_TREATY_ACTIVATION",
        {"actor_id": "governance_admin", "treaty_id": "t1"},
    )
    assert decision.decision == "ALLOW"


def test_phase28_kernel_denies_banned_actor():
    pytest.importorskip("constitutional_architecture")
    from ecosystem.gateway import (
        GovernanceKernelGateway,
        build_ecosystem_governance_kernel,
    )

    deny_rule = {
        "id": "ecosystem_deny_banned_actor",
        "name": "Deny ecosystem actions by banned actor",
        "effect": "DENY",
        "subject_types": ["ecosystem"],
        "actions": ["FEDERATION_TREATY_ACTIVATION"],
        "conditions": [
            {"field": "actor.actor_id", "operator": "EQUALS", "value": "banned_actor"}
        ],
        "priority": 10,
    }
    allow_rule = {
        "id": "ecosystem_allow_treaty_activation",
        "name": "Allow treaty activation",
        "effect": "ALLOW",
        "subject_types": ["ecosystem"],
        "actions": ["FEDERATION_TREATY_ACTIVATION"],
        "priority": 100,
    }
    kernel, _ = build_ecosystem_governance_kernel(rule_definitions=[deny_rule, allow_rule])
    gateway = GovernanceKernelGateway(kernel)

    denied = gateway.evaluate_action(
        "FEDERATION_TREATY_ACTIVATION",
        {"actor_id": "banned_actor", "treaty_id": "t1"},
    )
    assert denied.decision == "DENY"

    allowed = gateway.evaluate_action(
        "FEDERATION_TREATY_ACTIVATION",
        {"actor_id": "governance_admin", "treaty_id": "t1"},
    )
    assert allowed.decision == "ALLOW"


def test_phase28_kernel_round_trip_through_engine():
    pytest.importorskip("constitutional_architecture")
    from ecosystem.gateway import (
        GovernanceKernelGateway,
        build_ecosystem_governance_kernel,
    )

    deny_rule = {
        "id": "ecosystem_deny_banned_actor",
        "name": "Deny ecosystem actions by banned actor",
        "effect": "DENY",
        "subject_types": ["ecosystem"],
        "actions": ["FEDERATION_TREATY_ACTIVATION"],
        "conditions": [
            {"field": "actor.actor_id", "operator": "EQUALS", "value": "banned_actor"}
        ],
        "priority": 10,
    }
    allow_rule = {
        "id": "ecosystem_allow_treaty_activation",
        "name": "Allow treaty activation",
        "effect": "ALLOW",
        "subject_types": ["ecosystem"],
        "actions": ["FEDERATION_TREATY_ACTIVATION"],
        "priority": 100,
    }
    kernel, _ = build_ecosystem_governance_kernel(rule_definitions=[deny_rule, allow_rule])
    gateway = GovernanceKernelGateway(kernel)
    engine = EcosystemEngine(governance_gateway=gateway)

    treaty = engine.federation.create_treaty(
        name="Kernel-Governed Treaty",
        source_marketplace_id="marketplace_a",
        target_marketplace_id="marketplace_b",
        revenue_share_pct=10.0,
    )

    activated = engine.federation.activate_treaty(treaty.id, actor_id="governance_admin")
    assert activated.status.value == "ACTIVE"

    with pytest.raises(PermissionError):
        engine.federation.activate_treaty(treaty.id, actor_id="banned_actor")


# ── Gating of the remaining ecosystem actions ────────────────────────────────

def test_partner_activation_denied_by_governance():
    eng = EcosystemEngine(governance_gateway=StaticGovernanceGateway(decision="DENY"))
    partner = eng.partners.register_partner(name="Denied Partner", partner_type=PartnerType.VENDOR)
    with pytest.raises(PermissionError):
        eng.partners.activate_partner(partner_id=partner.id, actor_id="admin")


def test_suspend_treaty_denied_by_governance():
    eng = EcosystemEngine(governance_gateway=StaticGovernanceGateway(decision="DENY"))
    treaty = eng.federation.create_treaty(
        name="Suspend Treaty", source_marketplace_id="a", target_marketplace_id="b"
    )
    with pytest.raises(PermissionError):
        eng.suspend_treaty(treaty_id=treaty.id, reason="policy", actor_id="admin")


def test_update_routing_policy_denied_by_governance():
    eng = EcosystemEngine(governance_gateway=StaticGovernanceGateway(decision="DENY"))
    treaty = eng.federation.create_treaty(
        name="Routing Treaty", source_marketplace_id="a", target_marketplace_id="b"
    )
    with pytest.raises(PermissionError):
        eng.update_routing_policy(treaty_id=treaty.id, routing_policy={"x": 1}, actor_id="admin")


def test_enforce_penalty_denied_by_governance():
    eng = EcosystemEngine(governance_gateway=StaticGovernanceGateway(decision="DENY"))
    partner = eng.partners.register_partner(name="P", partner_type=PartnerType.VENDOR)
    contract = eng.contracts.create_contract(
        partner_id=partner.id, marketplace_id="m", contract_type="SLA"
    )
    eng.contracts.add_sla(
        contract_id=contract.id,
        sla=SLADefinition(metric="latency", threshold=200.0, operator=SLAOperator.LTE),
    )
    breach = eng.contracts.ingest_metric(contract_id=contract.id, metric="latency", value=350.0)
    assert breach is not None
    with pytest.raises(PermissionError):
        eng.enforce_penalty(
            contract_id=contract.id, breach_id=breach.id, penalty_amount=50.0, actor_id="admin"
        )


def test_gated_actions_allowed_by_static_gateway():
    eng = EcosystemEngine(governance_gateway=StaticGovernanceGateway(decision="ALLOW"))
    treaty = eng.federation.create_treaty(
        name="Gated Treaty", source_marketplace_id="a", target_marketplace_id="b", revenue_share_pct=3.0
    )
    activated = eng.federation.activate_treaty(treaty.id, actor_id="admin")
    assert activated.status.value == "ACTIVE"

    updated = eng.update_routing_policy(treaty_id=treaty.id, routing_policy={"mode": "strict"}, actor_id="admin")
    assert updated.routing_policy == {"mode": "strict"}

    suspended = eng.suspend_treaty(treaty_id=treaty.id, reason="maintenance", actor_id="admin")
    assert suspended.status.value == "SUSPENDED"


# ── Default kernel gateway + approval workflow ────────────────────────────────

def test_default_engine_uses_phase28_kernel():
    pytest.importorskip("constitutional_architecture")
    from ecosystem.gateway import GovernanceKernelGateway, _default_governance_gateway

    assert isinstance(_default_governance_gateway(), GovernanceKernelGateway)

    engine = EcosystemEngine()  # no explicit gateway -> real kernel by default
    assert isinstance(engine.governance_gateway, GovernanceKernelGateway)

    treaty = engine.federation.create_treaty(
        name="Default Kernel Treaty", source_marketplace_id="a", target_marketplace_id="b", revenue_share_pct=5.0
    )
    activated = engine.federation.activate_treaty(treaty.id, actor_id="governance_admin")
    assert activated.status.value == "ACTIVE"


def test_phase28_kernel_approval_workflow_round_trip():
    pytest.importorskip("constitutional_architecture")
    from ecosystem.gateway import GovernanceKernelGateway, build_ecosystem_governance_kernel

    req_rule = {
        "id": "ecosystem_require_approval_treaty",
        "name": "Require approval for treaty activation",
        "effect": "REQUIRE_APPROVAL",
        "subject_types": ["ecosystem"],
        "actions": ["FEDERATION_TREATY_ACTIVATION"],
        "required_approvals": [{"approver_type": "FEDERATION_COUNCIL"}],
        "priority": 10,
    }
    allow_rule = {
        "id": "ecosystem_allow_treaty_activation",
        "name": "Allow treaty activation",
        "effect": "ALLOW",
        "subject_types": ["ecosystem"],
        "actions": ["FEDERATION_TREATY_ACTIVATION"],
        "priority": 100,
    }
    kernel, _policy_set = build_ecosystem_governance_kernel(rule_definitions=[req_rule, allow_rule])
    gateway = GovernanceKernelGateway(kernel)
    engine = EcosystemEngine(governance_gateway=gateway)

    treaty = engine.federation.create_treaty(
        name="Approval Treaty", source_marketplace_id="a", target_marketplace_id="b", revenue_share_pct=5.0
    )

    pending = engine.federation.activate_treaty(treaty.id, actor_id="governance_admin")
    assert pending.status.value == "PENDING_GOVERNANCE"
    assert pending.governance_ref  # comma-joined approval ids surfaced by the kernel

    approval_id = pending.governance_ref.split(",")[0]
    status = engine.submit_approval(approval_id, actor="council", comments="approved")
    assert status == "APPROVED"

    activated = engine.federation.activate_treaty(treaty.id, actor_id="governance_admin")
    assert activated.status.value == "ACTIVE"
