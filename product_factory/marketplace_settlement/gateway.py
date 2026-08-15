"""
Governance and settlement gateways.
"""

from __future__ import annotations

from typing import Dict, Literal, Optional, Protocol

from pydantic import BaseModel


class GovernanceDecision(BaseModel):
    """Decision returned by governance."""

    decision: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]

    reason: str = ""

    approval_ref: Optional[str] = None


class GovernanceGateway(Protocol):
    """Abstract governance gateway."""

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> GovernanceDecision:
        ...


class StaticGovernanceGateway:
    """Static governance gateway for tests and local development."""

    def __init__(
        self,
        decision: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"] = "ALLOW",
        reason: str = "Static governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> GovernanceDecision:
        return GovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


class SettlementAdapter(Protocol):
    """Abstract settlement adapter."""

    def execute_settlement(self, batch) -> str:
        ...


class StaticSettlementAdapter:
    """Static settlement adapter for tests and local development."""

    def execute_settlement(self, batch) -> str:
        return f"static_settlement:{batch.id}"
