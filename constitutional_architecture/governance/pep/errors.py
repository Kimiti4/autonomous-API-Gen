"""
Phase 28.1 — Policy Enforcement Point SDK errors (Milestone 5B).

Structured failures every subsystem can raise and every caller can handle.
The PEP fails closed: if the kernel itself cannot be reached, callers get
GovernanceUnavailableError and must NOT proceed.
"""

from __future__ import annotations

from typing import List, Optional


class GovernanceEnforcementError(Exception):
    """Base class for all PEP enforcement failures."""

    def __init__(
        self,
        message: str,
        *,
        decision_id: Optional[str] = None,
        reason: str = "",
        request: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.decision_id = decision_id
        self.reason = reason
        self.request = request or {}

    def to_dict(self) -> dict:
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "decision_id": self.decision_id,
            "reason": self.reason,
            "request": self.request,
        }


class GovernanceDeniedError(GovernanceEnforcementError):
    """The action was denied by policy. The subsystem MUST NOT mutate state."""


class MissingEvidenceError(GovernanceEnforcementError):
    """Required evidence is absent. No approval-request workaround exists:
    the action is blocked until the evidence itself is provided."""

    def __init__(
        self,
        message: str,
        missing_evidence: List[str],
        *,
        decision_id: Optional[str] = None,
        reason: str = "",
        request: Optional[dict] = None,
    ) -> None:
        super().__init__(
            message,
            decision_id=decision_id,
            reason=reason,
            request=request,
        )
        self.missing_evidence = list(missing_evidence)

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload["missing_evidence"] = self.missing_evidence
        return payload


class ApprovalRequiredError(GovernanceEnforcementError):
    """The action requires human/role approval. It is paused in PENDING
    state; the subsystem MUST NOT mutate ISR state until approvals are
    granted and the action is finalized through the kernel."""

    def __init__(
        self,
        message: str,
        approval_ids: List[str],
        *,
        decision=None,
        decision_id: Optional[str] = None,
        reason: str = "",
        request: Optional[dict] = None,
    ) -> None:
        super().__init__(
            message,
            decision_id=decision_id,
            reason=reason,
            request=request,
        )
        self.approval_ids = list(approval_ids)
        self.decision = decision

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload["approval_ids"] = self.approval_ids
        return payload


class ConstraintsNotSatisfiedError(GovernanceEnforcementError):
    """ALLOW_WITH_CONSTRAINTS was granted but the subsystem cannot satisfy
    or record the constraints, so the action must not proceed."""


class GovernanceUnavailableError(GovernanceEnforcementError):
    """The governance kernel could not be reached. Fail closed: no action
    may proceed when governance itself is unavailable."""


class PromotionExecutionError(GovernanceEnforcementError):
    """The governed action was allowed but its execution failed, and the
    rollback plan was executed. The subsystem MUST treat the promotion as
    failed; state was reverted (or the failure was recorded)."""

    def __init__(
        self,
        message: str,
        *,
        decision_id: Optional[str] = None,
        reason: str = "",
        request: Optional[dict] = None,
        cause: Optional[Exception] = None,
        rollback_executed: bool = True,
        rollback_outcome: Optional[dict] = None,
    ) -> None:
        super().__init__(
            message,
            decision_id=decision_id,
            reason=reason,
            request=request,
        )
        self.cause = cause
        self.rollback_executed = rollback_executed
        self.rollback_outcome = rollback_outcome or {}

    def to_dict(self) -> dict:
        payload = super().to_dict()
        payload["cause"] = type(self.cause).__name__ if self.cause else None
        payload["rollback_executed"] = self.rollback_executed
        payload["rollback_outcome"] = self.rollback_outcome
        return payload
