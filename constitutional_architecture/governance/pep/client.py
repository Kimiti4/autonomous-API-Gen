"""
Phase 28.1 — Policy Enforcement Point client (Milestone 5B).

Thin, synchronous client over the GovernanceKernel evaluation contract.
The kernel is the Policy Decision Point; the client only marshals requests
and decisions. All evaluation inputs are explicit (principal, action,
subject, context, evidence) so a subsystem can become a PEP with minimal
code and no access to kernel internals.
"""

from __future__ import annotations

from typing import List, Optional

from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.schemas import (
    Actor,
    ActorType,
    Decision,
    GovernanceDecision,
    GovernanceEvaluationRequest,
)

EVOLUTION_COORDINATOR_ROLES = ["evolution_proposer", "evolution_coordinator"]
EVOLUTION_DELEGATED_AUTHORITY = ["propose_isr_changes"]


def autonomous_agent(
    actor_id: str,
    *,
    roles: Optional[List[str]] = None,
    delegated_authority: Optional[List[str]] = None,
) -> Actor:
    return Actor(
        actor_type=ActorType.AUTONOMOUS_AGENT,
        actor_id=actor_id,
        roles=roles or EVOLUTION_COORDINATOR_ROLES,
        delegated_authority=delegated_authority or EVOLUTION_DELEGATED_AUTHORITY,
    )


class GovernanceClient:
    """PEP facade over the kernel evaluation + approval flow."""

    def __init__(self, kernel: GovernanceKernel) -> None:
        self.kernel = kernel

    def evaluate(
        self,
        *,
        subject_type: str,
        subject_id: str,
        action: str,
        actor: Actor,
        environment: str = "staging",
        context: Optional[dict] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> GovernanceDecision:
        request = GovernanceEvaluationRequest(
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            actor=actor,
            context={**({"environment": environment} if environment else {}), **(context or {})},
            evidence_refs=evidence_refs or [],
        )
        return self.kernel.evaluate(request)

    def decision_id(self, decision: GovernanceDecision) -> str:
        from constitutional_architecture.governance.audit import decision_id_of

        return decision_id_of(decision)

    def create_approvals(self, decision: GovernanceDecision) -> List[str]:
        return self.kernel.create_approvals(decision)

    def submit_approval(
        self, approval_id: str, decision: str, comments: str = ""
    ):
        from constitutional_architecture.governance.schemas import ApprovalDecision

        return self.kernel.submit_approval(
            approval_id,
            ApprovalDecision(decision),
            comments=comments,
        )

    def finalize(
        self,
        decision: GovernanceDecision,
        *,
        subject_type: str,
        subject_id: str,
        action: str,
        actor: Actor,
    ) -> GovernanceDecision:
        return self.kernel.finalize(
            decision,
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            actor=actor,
        )
