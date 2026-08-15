"""
Phase 28 — Governance Kernel v0.1 (facade).

The minimal enforceable core of Phase 28. Wires the Policy Enforcement
Point flow:

    evaluate -> (REQUIRE_APPROVAL) -> approvals -> finalize -> audit

In-memory for v0.1; each manager is swappable for a database-backed store
without changing the evaluation contract.
"""

from __future__ import annotations

from typing import List, Optional

from constitutional_architecture.governance.approval_workflow import (
    ApprovalWorkflowEngine,
)
from constitutional_architecture.governance.audit import AuditFramework
from constitutional_architecture.governance.compliance import ComplianceEngine
from constitutional_architecture.governance.constitution import ConstitutionManager
from constitutional_architecture.governance.exception_manager import (
    GovernanceExceptionManager,
)
from constitutional_architecture.governance.lineage import LineageRepository
from constitutional_architecture.governance.policy_compiler import (
    PolicyCompiler,
    PolicySetManager,
)
from constitutional_architecture.governance.schemas import (
    Actor,
    ActorType,
    ApprovalDecision,
    ChangeLineage,
    ConstitutionISR,
    ExceptionScope,
    GovernanceDecision,
    GovernanceEvaluationRequest,
    GovernanceException,
    PolicySetISR,
)
from constitutional_architecture.governance.audit import decision_id_of

KERNEL_SERVICE_ACTOR = Actor(
    actor_type=ActorType.SERVICE,
    actor_id="governance_kernel",
    roles=["governance_kernel"],
)


class GovernanceKernel:
    """The constitutional control plane for the entire platform."""

    def __init__(
        self,
        *,
        constitutions: Optional[ConstitutionManager] = None,
        policy_sets: Optional[PolicySetManager] = None,
        exceptions: Optional[GovernanceExceptionManager] = None,
        approvals: Optional[ApprovalWorkflowEngine] = None,
        audit: Optional[AuditFramework] = None,
        lineage: Optional[LineageRepository] = None,
    ) -> None:
        self.constitutions = constitutions or ConstitutionManager()
        self.policy_sets = policy_sets or PolicySetManager(PolicyCompiler())
        self.exceptions = exceptions or GovernanceExceptionManager()
        self.approvals = approvals or ApprovalWorkflowEngine()
        self.audit = audit or AuditFramework()
        self.lineage = lineage or LineageRepository()
        self.compliance = ComplianceEngine(self.policy_sets, self.exceptions)

    # ── constitution lifecycle ──────────────────────────────────────────
    def create_constitution(self, **kwargs) -> ConstitutionISR:
        return self.constitutions.create(**kwargs)

    def activate_constitution(self, constitution_id: str) -> ConstitutionISR:
        return self.constitutions.activate(constitution_id)

    def get_constitution(self, constitution_id: str) -> ConstitutionISR:
        return self.constitutions.get(constitution_id)

    # ── policy lifecycle ────────────────────────────────────────────────
    def create_policy_set(
        self,
        name: str,
        constitution_id: str,
        constitution_version: str,
        rule_definitions: List[dict],
    ) -> PolicySetISR:
        return self.policy_sets.create(
            name=name,
            constitution_id=constitution_id,
            constitution_version=constitution_version,
            rule_definitions=rule_definitions,
        )

    def activate_policy_set(self, policy_set_id: str) -> PolicySetISR:
        return self.policy_sets.activate(policy_set_id)

    def get_policy_set(self, policy_set_id: str) -> PolicySetISR:
        return self.policy_sets.get(policy_set_id)

    # ── enforcement ─────────────────────────────────────────────────────
    def evaluate(self, request: GovernanceEvaluationRequest) -> GovernanceDecision:
        """Policy Decision Point. Pure: returns a decision and records an
        audit event + decision dossier."""
        decision = self.compliance.evaluate(request)
        self.audit.record_decision_dossier(
            decision,
            request.model_dump(),
            approval_ids=[],
        )
        self.audit.record(
            event_type="POLICY_EVALUATED",
            actor=request.actor,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            decision_id=decision_id_of(decision),
            evidence_refs=request.evidence_refs,
            context={"decision": decision.decision.value},
        )
        return decision

    def create_approvals(
        self, evaluation: GovernanceDecision
    ) -> List[str]:
        records = self.approvals.create_approval_request(
            decision_id_of(evaluation), evaluation.required_approvals
        )
        for record in records:
            self.audit.record_approval(record)
        return [r.id for r in records]

    def submit_approval(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        comments: Optional[str] = None,
        actor=None,
    ):
        record = self.approvals.submit_decision(
            approval_id, decision, comments=comments
        )
        self.audit.record_approval(record)
        if actor is not None:
            self.audit.record(
                event_type="APPROVAL_DECIDED",
                actor=actor,
                subject_type="GOVERNANCE_APPROVAL",
                subject_id=approval_id,
                action=decision.value,
                decision_id=record.evaluation_id,
                context={"decision": decision.value, "comments": comments or ""},
            )
        return record

    def finalize(
        self,
        evaluation: GovernanceDecision,
        *,
        subject_type: str,
        subject_id: str,
        action: str,
        actor,
    ) -> GovernanceDecision:
        """After approvals, produce the final decision (ALLOW or DENY)."""
        final = self.approvals.approve(
            decision_id_of(evaluation), evaluation.required_approvals
        )
        approval_ids = [
            r.id
            for r in self.approvals.approvals_for(decision_id_of(evaluation))
        ]
        self.audit.attach_approval_ids(decision_id_of(evaluation), approval_ids)
        self.audit.finalize_dossier_decision(decision_id_of(evaluation), final.value)
        self.audit.record(
            event_type="ACTION_FINALIZED",
            actor=actor,
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            decision_id=decision_id_of(evaluation),
            approval_ids=approval_ids,
            context={"final_decision": final.value},
        )
        return evaluation.model_copy(update={"decision": final})

    def record_lineage(self, **kwargs) -> ChangeLineage:
        return self.lineage.record(**kwargs)

    def create_exception(
        self,
        name: str,
        justification: str,
        *,
        scope: Optional[ExceptionScope] = None,
        granted_by: str = "governance_kernel",
        expires_at=None,
        max_uses: Optional[int] = None,
    ) -> GovernanceException:
        return self.exceptions.create(
            name,
            justification,
            scope=scope,
            granted_by=granted_by,
            expires_at=expires_at,
            max_uses=max_uses,
        )

    def revoke_exception(
        self, exception_id: str, *, actor: Optional[Actor] = None
    ) -> GovernanceException:
        exception = self.exceptions.revoke(exception_id)
        self.audit.record(
            event_type="EXCEPTION_REVOKED",
            actor=actor or KERNEL_SERVICE_ACTOR,
            subject_type="GOVERNANCE_EXCEPTION",
            subject_id=exception_id,
            action="REVOKE_EXCEPTION",
            context={"exception_name": exception.name},
        )
        return exception

    def reconstruct(self, decision_id: str) -> dict:
        return self.audit.reconstruct(decision_id)

    def evaluations(self, **filters) -> list:
        return self.audit.list_evaluations(**filters)

    def audit_events(self, **filters) -> list:
        return self.audit.query(**filters)

    def audit_chain_intact(self) -> bool:
        return self.audit.verify_chain()

    def audit_chain_detail(self) -> tuple[bool, Optional[int]]:
        return self.audit.verify_chain_detail()
