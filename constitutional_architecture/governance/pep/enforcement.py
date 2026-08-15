"""
Phase 28.1 — PEP enforcement (Milestone 5B).

Maps kernel decisions to enforced behavior. The contract:

  DENY                 -> GovernanceDeniedError; nothing may proceed
  REQUIRE_EVIDENCE     -> MissingEvidenceError; no approval workaround
  REQUIRE_APPROVAL     -> ApprovalRequiredError; action paused, no ISR
                          mutation; continue only after finalize() and a
                          re-check
  ALLOW_WITH_CONSTRAINTS -> caller must satisfy/record every constraint,
                          otherwise ConstraintsNotSatisfiedError
  ALLOW                -> proceed; the caller records decision ref, audit,
                          lineage, and rollback plan

Enforcement always fails closed: kernel errors surface as
GovernanceUnavailableError instead of being swallowed.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from constitutional_architecture.governance.schemas import Decision, GovernanceDecision

from constitutional_architecture.governance.pep.errors import (
    ApprovalRequiredError,
    ConstraintsNotSatisfiedError,
    GovernanceDeniedError,
    GovernanceUnavailableError,
    MissingEvidenceError,
)

CONTINUE_KEY = "continue"
DECISION_KEY = "decision"


class EnforcementResult:
    """Outcome of an enforced PEP call."""

    def __init__(
        self,
        decision: Decision,
        *,
        allowed: bool,
        decision_id: Optional[str] = None,
        final_decision: Optional[str] = None,
        approval_ids: Optional[List[str]] = None,
        constraints: Optional[List[dict]] = None,
        exceptions_applied: Optional[List[str]] = None,
        reason: str = "",
    ) -> None:
        self.decision = decision
        self.allowed = allowed
        self.decision_id = decision_id
        self.final_decision = final_decision
        self.approval_ids = approval_ids or []
        self.constraints = constraints or []
        self.exceptions_applied = exceptions_applied or []
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "decision": getattr(self.decision, "value", self.decision),
            "decision_id": self.decision_id,
            "final_decision": self.final_decision,
            "approval_ids": self.approval_ids,
            "constraints": self.constraints,
            "exceptions_applied": self.exceptions_applied,
            "reason": self.reason,
        }


class EnforcementContext:
    """Carries the decision through approval and finalization."""

    def __init__(
        self,
        decision: GovernanceDecision,
        decision_id: str,
        approval_ids: Optional[List[str]] = None,
    ) -> None:
        self.decision = decision
        self.decision_id = decision_id
        self.approval_ids = list(approval_ids or [])

    @property
    def is_approved(self) -> bool:
        return len(self.approval_ids) > 0


class PEPEnforcer:
    """Maps a kernel decision to enforced behavior."""

    def __init__(self, client) -> None:
        self.client = client

    def enforce(
        self,
        *,
        subject_type: str,
        subject_id: str,
        action: str,
        actor,
        environment: str = "staging",
        context: Optional[dict] = None,
        evidence_refs: Optional[List[str]] = None,
        constraint_handler: Optional[Callable[[List[dict]], bool]] = None,
        on_allowed: Optional[Callable[[EnforcementResult], None]] = None,
    ) -> EnforcementResult:
        """Evaluate, enforce, and (if allowed) invoke on_allowed.

        on_allowed is where the subsystem actually performs the governed
        action; it receives the EnforcementResult carrying decision refs.
        """
        try:
            decision = self.client.evaluate(
                subject_type=subject_type,
                subject_id=subject_id,
                action=action,
                actor=actor,
                environment=environment,
                context=context,
                evidence_refs=evidence_refs,
            )
        except Exception as exc:  # fail closed
            raise GovernanceUnavailableError(
                f"governance unavailable: {exc}",
                request={
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "action": action,
                },
            ) from exc

        decision_id = self.client.decision_id(decision)
        kind = decision.decision

        if kind is Decision.DENY:
            raise GovernanceDeniedError(
                f"action denied by policy: {decision.reason}",
                decision_id=decision_id,
                reason=decision.reason,
            )
        if kind is Decision.REQUIRE_EVIDENCE:
            raise MissingEvidenceError(
                f"action blocked: missing required evidence: "
                f"{', '.join(decision.required_evidence)}",
                decision.required_evidence,
                decision_id=decision_id,
                reason=decision.reason,
            )
        if kind is Decision.REQUIRE_APPROVAL:
            approval_ids = self.client.create_approvals(decision)
            raise ApprovalRequiredError(
                "action requires approval; paused in PENDING state",
                approval_ids,
                decision=decision,
                decision_id=decision_id,
                reason=decision.reason,
            )
        if kind is Decision.ALLOW_WITH_CONSTRAINTS:
            constraints = [
                c.model_dump() if hasattr(c, "model_dump") else dict(c)
                for c in decision.constraints
            ]
            if constraint_handler is not None:
                satisfied = constraint_handler(constraints)
            else:
                satisfied = False
            if not satisfied:
                raise ConstraintsNotSatisfiedError(
                    "allowed only with constraints that were not satisfied",
                    decision_id=decision_id,
                    reason=decision.reason,
                )
            result = EnforcementResult(
                decision,
                allowed=True,
                decision_id=decision_id,
                constraints=constraints,
                exceptions_applied=[
                    getattr(e, "id", str(e)) for e in decision.exceptions_applied
                ],
                reason=decision.reason,
            )
            if on_allowed is not None:
                on_allowed(result)
            return result

        result = EnforcementResult(
            decision,
            allowed=True,
            decision_id=decision_id,
            exceptions_applied=[
                getattr(e, "id", str(e)) for e in decision.exceptions_applied
            ],
            reason=decision.reason,
        )
        if on_allowed is not None:
            on_allowed(result)
        return result

    def confirm(
        self,
        original_decision_id: str,
        *,
        subject_type: str,
        subject_id: str,
        action: str,
        actor,
        context: Optional[dict] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> EnforcementResult:
        """Post-approval confirmation. The subsystem re-checks the action
        after approvals were granted and the kernel finalized the decision.
        A fresh evaluation runs first (policies may have changed); the
        original decision's finalized dossier then determines whether the
        approval-gated action may proceed."""
        fresh = self.client.evaluate(
            subject_type=subject_type,
            subject_id=subject_id,
            action=action,
            actor=actor,
            context=context,
            evidence_refs=evidence_refs,
        )
        fresh_id = self.client.decision_id(fresh)
        if fresh.decision is Decision.DENY:
            raise GovernanceDeniedError(
                f"action denied by policy: {fresh.reason}",
                decision_id=fresh_id,
                reason=fresh.reason,
            )
        if fresh.decision is Decision.REQUIRE_EVIDENCE:
            raise MissingEvidenceError(
                f"action blocked: missing required evidence: "
                f"{', '.join(fresh.required_evidence)}",
                fresh.required_evidence,
                decision_id=fresh_id,
                reason=fresh.reason,
            )
        if fresh.decision is Decision.REQUIRE_APPROVAL:
            for entry in self.client.kernel.evaluations():
                if entry["decision_id"] != original_decision_id:
                    continue
                final = entry.get("final_decision")
                if final == getattr(Decision.ALLOW, "value", "ALLOW"):
                    return EnforcementResult(
                        fresh,
                        allowed=True,
                        decision_id=original_decision_id,
                        final_decision=final,
                        reason="approval granted and finalized",
                    )
            raise ApprovalRequiredError(
                "action still requires approval; not finalized",
                [],
                decision_id=original_decision_id,
                reason=fresh.reason,
            )
        if fresh.decision is Decision.ALLOW_WITH_CONSTRAINTS:
            raise ConstraintsNotSatisfiedError(
                "confirmation: constraints not satisfied",
                decision_id=fresh_id,
                reason=fresh.reason,
            )
        return EnforcementResult(
            fresh,
            allowed=True,
            decision_id=original_decision_id,
            final_decision=getattr(fresh.decision, "value", None),
            reason=fresh.reason,
        )
