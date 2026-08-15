"""
Phase 28 — Governance Dashboard acceptance tests (Milestone 5A).

Covers dashboard acceptance criteria AC-1..AC-6 plus read-view health:
  AC-1  decision reconstruction dossier completeness
  AC-2  audit hash-chain verification reports VALID or first broken event
  AC-3  approval/rejection flows through the kernel API and is audited
  AC-4  exception revocation is immediate, kernel-audited, and effective
  AC-5  forward/backward lineage traceability from the dashboard
  AC-6  no governance bypass: dashboard mutations are authorized and
        kernel-only, and the dashboard never writes governance state itself
"""

from __future__ import annotations

import json
import re

import pytest

from constitutional_architecture.governance.dashboard.service import (
    DashboardAuthorizationError,
    DashboardService,
)
from constitutional_architecture.governance.schemas import (
    Actor,
    ActorType,
    ApprovalDecision,
    ApprovalStatus,
    Decision,
    ExceptionStatus,
    GovernanceEvaluationRequest,
)
from constitutional_architecture.governance.audit import decision_id_of

from constitutional_architecture.governance.testing import make_kernel

VIEWER = Actor(
    actor_type=ActorType.HUMAN,
    actor_id="alice",
    roles=["auditor", "platform_operator"],
)
AGENT_ACTOR = Actor(
    actor_type=ActorType.AUTONOMOUS_AGENT,
    actor_id="evolution_agent_01",
    roles=["evolution_proposer"],
    delegated_authority=["propose_isr_changes"],
)
UNAUTHORIZED = Actor(
    actor_type=ActorType.AUTONOMOUS_AGENT,
    actor_id="rogue_bot",
    roles=["propose_isr_changes"],
)


def _request(**overrides) -> GovernanceEvaluationRequest:
    defaults = dict(
        subject_type="EVOLUTION_PROPOSAL",
        subject_id="prop_1",
        action="PROMOTE",
        actor=AGENT_ACTOR,
        context={
            "environment": "staging",
            "has_rollback_plan": True,
            "verification_status": "passed",
            "parent_hash": "h_parent",
            "content_hash": "h_content",
            "audit_commitment": True,
        },
        evidence_refs=["verification_report", "simulation_report"],
    )
    defaults.update(overrides)
    return GovernanceEvaluationRequest(**defaults)


def _evaluate_and_approve(dashboard: DashboardService):
    """A fully approved evaluation ready for reconstruction checks."""
    kernel = dashboard.kernel
    request = _request(subject_id="prop_1")
    evaluation = kernel.evaluate(request)
    if evaluation.required_approvals:
        approval_ids = kernel.create_approvals(evaluation)
        for approval_id in approval_ids:
            kernel.submit_approval(approval_id, ApprovalDecision.APPROVED)
        kernel.finalize(
            evaluation,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            actor=request.actor,
        )
    return decision_id_of(evaluation)


def test_dashboard_requires_authorized_role_for_mutations():
    kernel = make_kernel()
    dashboard = DashboardService(kernel)
    evaluation = kernel.evaluate(_request())
    with pytest.raises(DashboardAuthorizationError):
        dashboard.reject("whatever", UNAUTHORIZED)


def test_ac1_decision_reconstruction_dossier_is_complete():
    dashboard = DashboardService(make_kernel())
    decision_id = _evaluate_and_approve(dashboard)
    dossier = dashboard.decision_dossier(decision_id)
    assert "request" in dossier
    assert dossier["decision"]["decision"] == Decision.REQUIRE_APPROVAL.value
    assert dossier["final_decision"] == Decision.ALLOW.value
    assert dossier["approvals"] and all(a["status"] == ApprovalStatus.APPROVED.value for a in dossier["approvals"])
    assert dossier["lineage"] == []
    assert isinstance(dossier["audit_events"], list)
    assert any(e["event_type"] == "ACTION_FINALIZED" for e in dossier["audit_events"])
    assert dossier["constitution_version"]


def test_ac2_audit_chain_verification_reports_valid_or_broken():
    dashboard = DashboardService(make_kernel())
    _evaluate_and_approve(dashboard)
    assert dashboard.verify_chain()["status"] == "VALID"
    dashboard.kernel.audit._events[0].context["tampered"] = True
    result = dashboard.verify_chain()
    assert result["status"] == "BROKEN"
    assert result["first_broken_index"] == 0


def test_ac3_approval_through_kernel_is_audited():
    kernel = make_kernel()
    dashboard = DashboardService(kernel)
    request = _request()
    evaluation = kernel.evaluate(request)
    approval_ids = kernel.create_approvals(evaluation)
    assert dashboard.approvals(status="PENDING")
    record = dashboard.approve(approval_ids[0], VIEWER, comments="ok")
    assert record["status"] == ApprovalStatus.APPROVED.value
    kernel.finalize(
        evaluation,
        subject_type=request.subject_type,
        subject_id=request.subject_id,
        action=request.action,
        actor=request.actor,
    )
    events = dashboard.audit_events(decision_id=decision_id_of(evaluation))
    assert any(e["event_type"] == "ACTION_FINALIZED" for e in events)


def test_ac4_exception_revocation_is_immediate_and_audited():
    kernel = make_kernel()
    dashboard = DashboardService(kernel)
    exception = kernel.create_exception(
        "temp_dev_widget",
        "temporary widget development",
        granted_by="alice",
    )
    dashboard.revoke_exception(exception.id, VIEWER)
    revoked = kernel.exceptions.get(exception.id)
    assert revoked.status is ExceptionStatus.REVOKED
    events = dashboard.audit_events(event_type="EXCEPTION_REVOKED")
    assert any(e["subject_id"] == exception.id for e in events)


def test_ac5_lineage_traceable_forward_and_backward():
    kernel = make_kernel()
    dashboard = DashboardService(kernel)
    kernel.record_lineage(
        parent_artifact_type="ISR_REVISION",
        parent_artifact_id="rev_1",
        parent_artifact_hash="h_1",
        child_artifact_type="ISR_REVISION",
        child_artifact_id="rev_2",
        child_artifact_hash="h_2",
        change_type="PROMOTION",
        decision_ref="decision_abc",
    )
    kernel.record_lineage(
        parent_artifact_type="ISR_REVISION",
        parent_artifact_id="rev_2",
        parent_artifact_hash="h_2",
        child_artifact_type="ISR_REVISION",
        child_artifact_id="rev_3",
        child_artifact_hash="h_3",
        change_type="PROMOTION",
        decision_ref="decision_def",
    )
    trace = dashboard.lineage_trace("ISR_REVISION", "rev_2")
    assert [l["child_artifact_id"] for l in trace["backward"]] == ["rev_2"]
    assert [l["child_artifact_id"] for l in trace["forward"]] == ["rev_3"]
    assert trace["ancestors"]


def test_ac6_no_governance_bypass_through_dashboard():
    kernel = make_kernel()
    dashboard = DashboardService(kernel)
    baseline_events = len(kernel.audit_events())
    _evaluate_and_approve(dashboard)
    assert len(kernel.audit_events()) > baseline_events
    request = _request(subject_id="prop_bypass")
    evaluation = kernel.evaluate(request)
    approval_ids = kernel.create_approvals(evaluation)
    dashboard.reject(approval_ids[0], VIEWER, comments="denied")
    final = kernel.finalize(
        evaluation,
        subject_type=request.subject_type,
        subject_id=request.subject_id,
        action=request.action,
        actor=request.actor,
    )
    assert final.decision is Decision.DENY
    events = dashboard.audit_events(decision_id=decision_id_of(evaluation))
    assert any(e["event_type"] == "ACTION_FINALIZED" for e in events)


def test_health_summary_aggregates_state():
    dashboard = DashboardService(make_kernel())
    _evaluate_and_approve(dashboard)
    health = dashboard.health()
    assert health["total_evaluations"] >= 1
    assert "ALLOW" in health["by_decision"]
    assert health["audit_chain"]["status"] == "VALID"


def test_render_console_embeds_parseable_state(tmp_path):
    from constitutional_architecture.governance.dashboard import render_console

    snapshot = render_console.collect_snapshot(render_console.build_demo_kernel())
    out = render_console.render(snapshot, tmp_path / "console.html")
    html = out.read_text(encoding="utf-8")
    match = re.search(r"var GOV = (\{.*?\});\s*\n\s*function el", html, re.S)
    assert match, "GOVDATA placeholder must be embedded"
    embedded = json.loads(match.group(1))
    for key in (
        "health",
        "constitutions",
        "policy_sets",
        "evaluations",
        "approvals",
        "exceptions",
        "audit_events",
        "chain",
        "lineage",
    ):
        assert key in embedded
    assert embedded["chain"]["status"] == "VALID"
    assert embedded["health"]["total_evaluations"] >= 2
    assert len(embedded["policy_sets"]) == 6
