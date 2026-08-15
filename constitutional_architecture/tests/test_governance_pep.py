"""
Phase 28.1 — PEP SDK acceptance tests (Milestone 5B/5C).

Covers the PEP acceptance criteria:
  A1  unsafe promotion is denied and no ISR mutation occurs
  A2  missing evidence blocks the action and cannot be bypassed by an
      approval request (no workaround)
  A3  approval-required actions are paused in PENDING with no ISR mutation
  A4  after approvals are granted and the decision finalized, the action
      proceeds
  A5  ALLOW_WITH_CONSTRAINTS enforces its constraints (handler must
      satisfy them)
  A6  a revoked exception no longer suppresses deny rules
Plus: the PEP fails closed when the kernel itself errors.
"""

from __future__ import annotations

import pytest

from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.pep import (
    ApprovalRequiredError,
    ConstraintsNotSatisfiedError,
    GovernanceClient,
    GovernanceDeniedError,
    GovernanceUnavailableError,
    MissingEvidenceError,
    PEPEnforcer,
    autonomous_agent,
)
from constitutional_architecture.governance.pep.evolution_guard import (
    EvolutionPromotionGuard,
)
from constitutional_architecture.governance.pep.errors import (
    PromotionExecutionError,
)
from constitutional_architecture.governance.schemas import (
    ApprovalDecision,
    Decision,
)

from constitutional_architecture.governance.testing import make_kernel


def _proposal(**overrides) -> dict:
    proposal = dict(
        id="proposal_42",
        version="1.0",
        content_hash="h_proposal_42",
        parent_isr_hash="h_parent",
        has_rollback_plan=True,
        rollback_plan_ref="rollback:plan:42",
        verification_status="passed",
        simulation_status="passed",
        fitness_evaluation_id="fitness:42",
        mutation_type="feature",
        audit_commitment=True,
        evidence_refs=["verification_report", "simulation_report"],
    )
    proposal.update(overrides)
    return proposal


def _promotion_action(executed: list) -> callable:
    def action(payload: dict) -> dict:
        executed.append(payload)
        return {
            "child_isr_hash": "h_child",
            "result_id": "isr_rev_43",
        }

    return action


def test_pep_a1_unsafe_promotion_denied_no_mutation():
    kernel = make_kernel()
    guard = EvolutionPromotionGuard(kernel)
    executed: list = []
    with pytest.raises(GovernanceDeniedError) as exc_info:
        guard.guard_promote(
            _proposal(has_rollback_plan=False, verification_status="failed"),
            autonomous_agent("evolution_agent_01"),
            _promotion_action(executed),
        )
    assert "denied" in exc_info.value.reason.lower() or "denied" in str(exc_info.value).lower()
    assert executed == []
    assert "rollback" in exc_info.value.to_dict()["reason"].lower()


def test_pep_a2_missing_evidence_blocks_and_has_no_approval_workaround():
    kernel = make_kernel()
    enforcer = PEPEnforcer(GovernanceClient(kernel))
    with pytest.raises(MissingEvidenceError) as exc_info:
        enforcer.enforce(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_43",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
            context={
                "has_rollback_plan": True,
                "audit_commitment": True,
            },
            evidence_refs=[],
        )
    assert "verification_report" in exc_info.value.missing_evidence
    assert not kernel.approvals.all_approvals(), (
        "no approval request may be created as an evidence workaround"
    )


def test_pep_a3_approval_required_pauses_pending_no_mutation():
    kernel = make_kernel()
    enforcer = PEPEnforcer(GovernanceClient(kernel))
    executed: list = []
    with pytest.raises(ApprovalRequiredError) as exc_info:
        enforcer.enforce(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_44",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
            context={
                "has_rollback_plan": True,
                "audit_commitment": True,
            },
            evidence_refs=["verification_report", "simulation_report"],
            on_allowed=lambda r: executed.append(r),
        )
    assert exc_info.value.approval_ids
    assert executed == []
    approval = kernel.approvals.get(exc_info.value.approval_ids[0])
    assert approval.status.value == "PENDING"
    assert not kernel.lineage.all()


def test_pep_a4_approved_and_finalized_action_proceeds():
    kernel = make_kernel()
    client = GovernanceClient(kernel)
    enforcer = PEPEnforcer(client)
    executed: list = []
    try:
        enforcer.enforce(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_45",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
            context={"has_rollback_plan": True, "audit_commitment": True},
            evidence_refs=["verification_report", "simulation_report"],
            on_allowed=lambda r: executed.append(r),
        )
        pytest.fail("expected ApprovalRequiredError")
    except ApprovalRequiredError as exc:
        for approval_id in exc.approval_ids:
            kernel.submit_approval(approval_id, ApprovalDecision.APPROVED)
        client.finalize(
            exc.decision,
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_45",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
        )
        result = enforcer.confirm(
            exc.decision_id,
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_45",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
            context={"has_rollback_plan": True, "audit_commitment": True},
            evidence_refs=["verification_report", "simulation_report"],
        )
    assert result.allowed
    assert result.final_decision == Decision.ALLOW.value


def test_pep_a5_constraints_are_enforced_or_fail():
    kernel = make_kernel()
    policy_set = kernel.create_policy_set(
        name="constrained",
        constitution_id=kernel.constitutions.active()[0].id,
        constitution_version=kernel.constitutions.active()[0].version,
        rule_definitions=[
            {
                "id": "constrained_rule",
                "name": "Constraint rule",
                "effect": "ALLOW_WITH_CONSTRAINTS",
                "subject_types": ["WIDGET_MODULE"],
                "actions": ["COMPILE"],
                "constraints": [
                    {
                        "id": "retain_log",
                        "name": "Retain log",
                        "description": "must retain log",
                    }
                ],
            }
        ],
    )
    kernel.activate_policy_set(policy_set.id)
    enforcer = PEPEnforcer(GovernanceClient(kernel))
    with pytest.raises(ConstraintsNotSatisfiedError):
        enforcer.enforce(
            subject_type="WIDGET_MODULE",
            subject_id="widget_1",
            action="COMPILE",
            actor=autonomous_agent("widget_bot"),
            context={"audit_commitment": True},
        )
    result = enforcer.enforce(
        subject_type="WIDGET_MODULE",
        subject_id="widget_1",
        action="COMPILE",
        actor=autonomous_agent("widget_bot"),
        context={"audit_commitment": True},
        constraint_handler=lambda constraints: True,
    )
    assert result.allowed
    assert result.constraints[0]["name"] == "Retain log"


def test_pep_a6_revoked_exception_no_longer_suppresses_deny():
    kernel = make_kernel()
    enforcer = PEPEnforcer(GovernanceClient(kernel))
    exception = kernel.create_exception(
        "temporary_rollback_waiver",
        "waive rollback plan temporarily",
        granted_by="alice",
    )
    kernel.revoke_exception(exception.id)
    with pytest.raises(GovernanceDeniedError):
        enforcer.enforce(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_47",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
            context={"has_rollback_plan": False, "audit_commitment": True},
            evidence_refs=["verification_report", "simulation_report"],
        )


def test_pep_fails_closed_when_kernel_errors():
    kernel = make_kernel()

    class BrokenClient:
        def evaluate(self, **kwargs):
            raise RuntimeError("kernel down")

    class FakeDecision:
        decision = Decision.DENY

    enforcer = PEPEnforcer(BrokenClient())
    with pytest.raises(GovernanceUnavailableError):
        enforcer.enforce(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_48",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
        )


def test_evolution_guard_records_lineage_after_allowed_promotion():
    kernel = make_kernel(excluded_packs=["pack_006_approvals"])
    guard = EvolutionPromotionGuard(kernel)
    executed: list = []
    result = guard.guard_promote(
        _proposal(),
        autonomous_agent("evolution_agent_01"),
        _promotion_action(executed),
    )
    assert result["allowed"] is True
    assert executed, "promotion action must run when allowed"
    links = kernel.lineage.all()
    assert len(links) == 1
    link = links[0]
    assert link.child_artifact_id == "h_child"
    assert link.decision_ref == result["decision_id"]
    assert link.rollback_plan_ref == "rollback:plan:42"


def test_evolution_guard_attaches_evidence_refs_to_lineage():
    kernel = make_kernel(excluded_packs=["pack_006_approvals"])
    guard = EvolutionPromotionGuard(kernel)
    result = guard.guard_promote(
        _proposal(evidence_refs=["verification_report", "simulation_report"]),
        autonomous_agent("evolution_agent_01"),
        _promotion_action([]),
    )
    assert result["allowed"] is True
    link = kernel.lineage.all()[0]
    assert link.evidence_refs == ["verification_report", "simulation_report"]


def test_evolution_guard_executes_rollback_when_promotion_fails():
    kernel = make_kernel(excluded_packs=["pack_006_approvals"])
    guard = EvolutionPromotionGuard(kernel)
    rolled_back: list = []

    def failing_action(payload):
        raise RuntimeError("isr apply failed mid-way")

    def rollback(payload):
        rolled_back.append(payload)
        return {"rolled_back_isr_rev": payload["proposal_id"]}

    with pytest.raises(PromotionExecutionError) as exc_info:
        guard.guard_promote(
            _proposal(),
            autonomous_agent("evolution_agent_01"),
            failing_action,
            rollback_action=rollback,
        )
    assert exc_info.value.rollback_executed is True
    assert rolled_back, "rollback must execute when the promotion action fails"
    assert exc_info.value.cause.__class__.__name__ == "RuntimeError"
    events = kernel.audit_events(event_type="ACTION_ROLLED_BACK")
    assert any(
        e.subject_id == "proposal_42" and e.decision_id == exc_info.value.decision_id
        for e in events
    ), "rollback must be audit-recorded"
    assert not kernel.lineage.all(), "failed promotion must not record success lineage"


def test_evolution_guard_failure_without_rollback_is_recorded():
    kernel = make_kernel(excluded_packs=["pack_006_approvals"])
    guard = EvolutionPromotionGuard(kernel)

    def failing_action(payload):
        raise RuntimeError("no rollback plan available")

    with pytest.raises(PromotionExecutionError) as exc_info:
        guard.guard_promote(
            _proposal(),
            autonomous_agent("evolution_agent_01"),
            failing_action,
        )
    assert exc_info.value.rollback_executed is False
    events = kernel.audit_events(event_type="ACTION_ROLLED_BACK")
    assert any(e.context.get("rollback_executed") is False for e in events)


def test_active_exception_permits_previously_denied_promotion():
    """Complement of A6: while an exception is ACTIVE it may suppress the
    deny rule; once revoked it no longer does."""
    kernel = make_kernel(excluded_packs=["pack_006_approvals"])
    exception = kernel.create_exception(
        "temporary_rollback_waiver",
        "waive rollback plan temporarily",
        granted_by="alice",
        scope={
            "subject_types": ["EVOLUTION_PROPOSAL"],
            "actions": ["PROMOTE"],
            "subject_ids": ["proposal_49"],
            "environment": "staging",
        },
        max_uses=5,
    )
    enforcer = PEPEnforcer(GovernanceClient(kernel))
    context = {
        "environment": "staging",
        "has_rollback_plan": False,
        "audit_commitment": True,
        "parent_hash": "h_p49",
        "content_hash": "h_p49_content",
    }
    result = enforcer.enforce(
        subject_type="EVOLUTION_PROPOSAL",
        subject_id="proposal_49",
        action="PROMOTE",
        actor=autonomous_agent("evolution_agent_01"),
        context=context,
        evidence_refs=["verification_report", "simulation_report"],
    )
    assert result.allowed
    assert exception.id in result.exceptions_applied
    assert kernel.exceptions.get(exception.id).use_count == 1

    kernel.revoke_exception(exception.id)
    with pytest.raises(GovernanceDeniedError):
        enforcer.enforce(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_49",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
            context=context,
            evidence_refs=["verification_report", "simulation_report"],
        )
