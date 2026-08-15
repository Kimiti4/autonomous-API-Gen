"""
Phase 28 — Milestone 5A spec §15.4.2: dashboard view tests (tasks 5A.5–5A.7).

Every section of the BFF renders for an authenticated user: health home,
constitutions, policy sets, evaluations, decision reconstruction,
approvals, exceptions, audit log + integrity, lineage, and observability
(metrics + readiness). Values on the page must come from the kernel.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def bob(tc, login):
    login("bob")
    return tc


def test_health_live_is_public(tc):
    r = tc.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_ready_reports_dependencies(tc, login):
    login("bob")
    r = tc.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"
    for dep in ("kernel", "auth", "templates", "static"):
        assert dep in r.json()["checks"]


def test_home_shows_governance_health(tc, bob):
    body = bob.get("/").text
    assert "Governance Health" in body


def test_home_health_matches_kernel(client, tc, bob):
    health = client.governance_health()
    body = bob.get("/").text
    assert str(health.audit_chain_events) in body
    assert "VALID" in body


def test_constitutions_list(tc, bob, client):
    body = bob.get("/constitutions").text
    constitution = client.list_constitutions()[0]
    assert constitution.name in body


def test_constitution_detail(tc, bob, client):
    constitution = client.list_constitutions()[0]
    body = bob.get(f"/constitutions/{constitution.id}").text
    assert constitution.name in body
    assert "Version" in body


def test_policy_sets_list(tc, bob, client):
    body = bob.get("/policy-sets").text
    policy_set = client.list_policy_sets()[0]
    assert policy_set.name in body


def test_policy_set_detail_shows_rules(tc, bob, client):
    policy_set = client.list_policy_sets()[0]
    body = bob.get(f"/policy-sets/{policy_set.id}").text
    assert policy_set.id in body
    assert "Rules" in body


def test_evaluations_list(tc, bob, client):
    body = bob.get("/evaluations").text
    evaluation = client.list_evaluations()[0]
    assert evaluation.decision_id[:12] in body


def test_evaluations_list_filters(tc, bob, client):
    evaluation = client.list_evaluations()[0]
    action = evaluation.action or "PROMOTE"
    body = bob.get(f"/evaluations?action={action}").text
    assert "evaluations" in body.lower() or "decisions" in body.lower()
    # an impossible filter yields an empty (but valid) page
    empty = bob.get("/evaluations?action=DOES_NOT_EXIST_XYZ").text
    assert "No evaluations" in empty or "none" in empty.lower()


def test_evaluation_detail(tc, bob, client):
    evaluation = client.list_evaluations()[0]
    body = bob.get(f"/evaluations/{evaluation.decision_id}").text
    assert evaluation.decision_id[:12] in body


def test_reconstruction_contains_eight_sections(tc, bob, client):
    evaluation = client.list_evaluations()[0]
    body = bob.get(f"/evaluations/{evaluation.decision_id}/reconstruct").text
    for section in (
        "Request",
        "Decision",
        "Policy evaluations",
        "Evidence",
        "Approvals",
        "Exceptions applied",
        "Audit events",
        "Lineage",
    ):
        assert section in body, f"reconstruction missing section {section}"


def test_reconstruction_matches_kernel_dossier(client, tc, bob):
    evaluation = client.list_evaluations()[0]
    dossier = client.reconstruct_decision(evaluation.decision_id)
    body = bob.get(f"/evaluations/{evaluation.decision_id}/reconstruct").text
    assert dossier.decision_id in body


def test_approvals_queue(tc, bob):
    body = bob.get("/approvals").text
    assert "Approval Queue" in body


def test_approvals_queue_status_filter(tc, bob, client):
    approved = [a for a in client.list_approvals() if a.status == "APPROVED"]
    if approved:
        body = bob.get("/approvals?status=APPROVED").text
        assert approved[0].id in body


def test_approval_detail(tc, bob, client):
    approval = client.list_approvals()[0]
    body = bob.get(f"/approvals/{approval.id}").text
    assert approval.id in body


def test_exceptions_list(tc, bob):
    body = bob.get("/exceptions").text
    assert "Exception Registry" in body


def test_exception_detail(tc, bob, client, active_exception):
    body = bob.get(f"/exceptions/{active_exception.id}").text
    assert active_exception.id in body


def test_audit_log_list(tc, bob, client):
    body = bob.get("/audit").text
    event = client.list_audit_events()[0]
    assert event.event_id[:12] in body


def test_audit_event_detail(tc, bob, client):
    event = client.list_audit_events()[0]
    body = bob.get(f"/audit/{event.event_id}").text
    assert event.event_type in body


def test_audit_integrity_page(tc, bob, client):
    integrity = client.verify_audit_chain()
    body = bob.get("/audit/integrity").text
    assert integrity.status in body
    assert str(integrity.verified_events) in body


def test_lineage_explorer(tc, bob):
    body = bob.get("/lineage").text
    assert "Lineage" in body


def test_lineage_artifact_detail(tc, bob, client):
    link = client.list_lineage()[0]
    body = bob.get(f"/lineage/{link.id}").text
    assert link.id in body


def test_lineage_backward_route(tc, bob, client):
    link = client.list_lineage()[0]
    body = bob.get(f"/lineage/{link.id}/backward").text
    assert link.id in body


def test_lineage_forward_route(tc, bob, client):
    link = client.list_lineage()[0]
    body = bob.get(f"/lineage/{link.id}/forward").text
    assert link.id in body


def test_metrics_counts_page_views(tc, bob):
    bob.get("/approvals")
    bob.get("/approvals")
    metrics = bob.get("/metrics").json()
    assert metrics["dashboard_page_views_total"] >= 2
    assert isinstance(metrics["dashboard_kernel_request_duration_seconds"], float)


def test_sensitive_context_is_redacted(tc, bob, client, kernel):
    from constitutional_architecture.governance.testing import EVOLUTION_AGENT_ACTOR
    from constitutional_architecture.governance.schemas import (
        Actor,
        ActorType,
        GovernanceEvaluationRequest,
    )

    request = GovernanceEvaluationRequest(
        subject_type="EVOLUTION_PROPOSAL",
        subject_id="redaction_probe",
        action="PROMOTE",
        actor=EVOLUTION_AGENT_ACTOR,
        context={
            "environment": "staging",
            "api_token": "super-secret-token-value",
            "has_rollback_plan": True,
            "verification_status": "passed",
        },
        evidence_refs=["verification_report"],
    )
    kernel.evaluate(request)
    evaluations = client.list_evaluations()
    probe = [e for e in evaluations if e.subject_id == "redaction_probe"][0]
    body = bob.get(f"/evaluations/{probe.decision_id}/reconstruct").text
    assert "super-secret-token-value" not in body
    assert "REDACTED" in body
