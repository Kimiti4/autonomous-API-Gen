"""
Governance client abstraction.

The production reference integration should connect this client to the
Phase 28 Governance Kernel.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from .models import GovernanceDecision, GovernanceEvaluationRequest


class GovernanceClient(Protocol):
    """Abstract governance client."""

    def evaluate(
        self,
        request: GovernanceEvaluationRequest,
    ) -> GovernanceDecision:
        ...


class StaticGovernanceClient:
    """Static governance client useful for tests and local development."""

    def __init__(
        self,
        decision: str = "ALLOW",
        reason: str = "Static governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate(
        self,
        request: GovernanceEvaluationRequest,
    ) -> GovernanceDecision:
        return GovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


class HttpGovernanceKernelClient:
    """
    HTTP client for the Phase 28 Governance Kernel.

    This client fails closed if the Governance Kernel is unavailable.
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def evaluate(
        self,
        request: GovernanceEvaluationRequest,
    ) -> GovernanceDecision:
        url = f"{self._base_url}/v1/governance/evaluate"

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    url,
                    json=request.model_dump(mode="json"),
                )

                response.raise_for_status()

                return GovernanceDecision.model_validate(response.json())

        except Exception as exc:
            return GovernanceDecision(
                decision="DENY",
                reason=f"Governance Kernel unavailable or error: {exc}",
            )
