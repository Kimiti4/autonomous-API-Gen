"""
Policy enforcement helpers.
"""

from __future__ import annotations

from .engine import PolicyEngine
from .models import (
    PolicyEvaluationDecision,
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
)


class PolicyEnforcementError(Exception):
    """Base enforcement error."""


class PolicyDeniedError(PolicyEnforcementError):
    """Raised when policy denies an action."""

    def __init__(self, message: str, result: PolicyEvaluationResult):
        super().__init__(message)
        self.result = result


class PolicyApprovalRequiredError(PolicyEnforcementError):
    """Raised when policy requires approval."""

    def __init__(self, message: str, result: PolicyEvaluationResult):
        super().__init__(message)
        self.result = result


class PolicyEnforcer:
    """Enforces policy evaluation outcomes."""

    def __init__(self, engine: PolicyEngine) -> None:
        self.engine = engine

    def enforce(
        self,
        request: PolicyEvaluationRequest,
    ) -> PolicyEvaluationResult:
        result = self.engine.evaluate(request)

        if result.decision == PolicyEvaluationDecision.DENY:
            raise PolicyDeniedError(result.reason, result)

        if result.decision == PolicyEvaluationDecision.REQUIRE_APPROVAL:
            raise PolicyApprovalRequiredError(result.reason, result)

        if result.applied_delegation_id:
            self.engine.record_delegation_use(result.applied_delegation_id)

        return result
