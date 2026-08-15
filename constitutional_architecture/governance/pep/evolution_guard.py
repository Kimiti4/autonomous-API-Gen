"""
Phase 28.1 — Evolution Engine promotion guard (Milestone 5C).

A policy enforcement adapter for the Evolution Engine (Phase 21 boundary).
The Evolution Engine 2.0 orchestrator is constitutionally constrained to
import only isr.* and engine.*; governance lives outside that boundary, so
the guard sits at the promotion seam: the engine calls the guard, the guard
evaluates the promotion proposal against the governance kernel, enforces
the decision, and — only when allowed — invokes the supplied promotion
action (which applies the ISR mutation). The guard then records lineage,
rollback, and audit references.

This is an enforcement adapter, not a new evolution capability: it does not
implement promotion itself.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.pep.client import GovernanceClient
from constitutional_architecture.governance.pep.context import EvolutionContextBuilder
from constitutional_architecture.governance.pep.enforcement import PEPEnforcer
from constitutional_architecture.governance.pep.errors import (
    ApprovalRequiredError,
    ConstraintsNotSatisfiedError,
    GovernanceDeniedError,
    GovernanceEnforcementError,
    GovernanceUnavailableError,
    MissingEvidenceError,
    PromotionExecutionError,
)

ROLLBACK_CONTEXT_KEY = "rollback_plan_ref"
DECISION_REF_KEY = "decision_ref"
APPROVAL_REFS_KEY = "approval_refs"
EVIDENCE_REFS_KEY = "evidence_refs"


class EvolutionPromotionGuard:
    """PEP enforcement at the evolution promotion boundary."""

    def __init__(
        self,
        kernel: GovernanceKernel,
        *,
        enforcer: Optional[PEPEnforcer] = None,
    ) -> None:
        self.kernel = kernel
        self.client = GovernanceClient(kernel)
        self.enforcer = enforcer or PEPEnforcer(self.client)

    def context_for(self, proposal: dict, actor: Any) -> EvolutionContextBuilder:
        """Maps an evolution proposal dict to the governed context."""
        proposal_id = proposal.get("id", proposal.get("proposal_id", "unknown"))
        builder = EvolutionContextBuilder(
            proposal_id=str(proposal_id),
            proposal_version=str(proposal.get("version", proposal.get("proposal_version", "1.0"))),
            proposal_content_hash=str(
                proposal.get("content_hash", proposal.get("proposal_content_hash", ""))
            ),
            actor=actor,
            environment=proposal.get("environment", "staging"),
            parent_isr_hash=str(proposal.get("parent_isr_hash", "")),
            has_rollback_plan=bool(
                proposal.get("has_rollback_plan", proposal.get("rollback_plan_ref"))
            ),
            rollback_plan_ref=str(proposal.get("rollback_plan_ref", "")),
            verification_status=str(proposal.get("verification_status", "unknown")),
            simulation_status=str(proposal.get("simulation_status", "unknown")),
            fitness_evaluation_id=str(proposal.get("fitness_evaluation_id", "")),
            mutation_type=str(proposal.get("mutation_type", "feature")),
            audit_commitment=bool(proposal.get("audit_commitment", True)),
            evidence_refs=proposal.get("evidence_refs", []),
        )
        return builder

    def guard_promote(
        self,
        proposal: dict,
        actor: Any,
        promotion_action: Callable[[Dict[str, Any]], Dict[str, Any]],
        *,
        constraint_handler: Optional[Callable[[list], bool]] = None,
        rollback_action: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> dict:
        """Enforce governance for a promotion; on allow, run promotion_action
        (which must apply the ISR mutation), then record lineage + audit
        references. If promotion_action raises, the rollback plan is executed
        (via rollback_action when supplied) and an ACTION_ROLLED_BACK audit
        event is recorded — the promotion is never silently half-applied.

        Raises the PEP errors on any non-ALLOW decision."""
        builder = self.context_for(proposal, actor)
        request = builder.build()
        enforcement = self.enforcer.enforce(
            subject_type=request.subject_type,
            subject_id=request.subject_id,
            action=request.action,
            actor=request.actor,
            context=request.context,
            evidence_refs=request.evidence_refs,
            constraint_handler=constraint_handler,
        )
        if not enforcement.allowed:
            raise GovernanceDeniedError(
                f"promotion not allowed: {enforcement.reason}",
                decision_id=enforcement.decision_id,
                reason=enforcement.reason,
            )

        payload = {
            "proposal_id": request.subject_id,
            "decision_id": enforcement.decision_id,
            "final_decision": enforcement.final_decision
            or getattr(enforcement.decision, "value", None),
            "parent_isr_hash": request.context.get("parent_isr_hash"),
            "rollback_plan_ref": request.context.get("rollback_plan_ref"),
        }
        try:
            outcome = promotion_action(payload)
        except Exception as exc:
            rollback_outcome: Optional[Dict[str, Any]] = None
            if rollback_action is not None:
                rollback_outcome = rollback_action(payload)
            self.kernel.audit.record(
                event_type="ACTION_ROLLED_BACK",
                actor=actor,
                subject_type=request.subject_type,
                subject_id=request.subject_id,
                action=request.action,
                decision_id=enforcement.decision_id,
                context={
                    "rollback_plan_ref": request.context.get("rollback_plan_ref") or "",
                    "rollback_executed": rollback_action is not None,
                },
            )
            raise PromotionExecutionError(
                f"promotion execution failed after governance allowed it: {type(exc).__name__}: {exc}",
                decision_id=enforcement.decision_id,
                reason=f"promotion failed: {type(exc).__name__}",
                request=request.context,
                cause=exc,
                rollback_executed=rollback_action is not None,
                rollback_outcome=rollback_outcome or {},
            ) from exc

        rollback_ref = request.context.get("rollback_plan_ref") or ""
        self.kernel.record_lineage(
            parent_artifact_type="ISR_REVISION",
            parent_artifact_id=str(request.context.get("parent_isr_hash") or "root"),
            parent_artifact_hash=str(request.context.get("parent_isr_hash") or ""),
            child_artifact_type="ISR_REVISION",
            child_artifact_id=str(outcome.get("child_isr_hash", outcome.get("result_id", request.subject_id))),
            child_artifact_hash=str(outcome.get("child_isr_hash", "")),
            change_type="PROMOTION",
            cause_ref=request.subject_id,
            decision_ref=enforcement.decision_id,
            approval_refs=enforcement.approval_ids,
            evidence_refs=request.evidence_refs,
            rollback_plan_ref=rollback_ref,
        )
        return {
            "allowed": True,
            "decision_id": enforcement.decision_id,
            "outcome": outcome,
            "lineage_recorded": True,
        }
