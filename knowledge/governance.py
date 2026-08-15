"""
Governance Kernel integration for the Knowledge Graph.

The Knowledge Graph must remain governed.

This module defines the minimal governance client contract and a fail-closed
HTTP implementation.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field


class GovernanceEvaluationRequest(BaseModel):
    """Request sent to the Phase 28 Governance Kernel."""

    subject_type: str
    subject_id: str
    action: str
    actor: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)


class GovernanceDecision(BaseModel):
    """Decision returned by the Governance Kernel."""

    decision: str
    reason: str
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    constraints: list[dict[str, Any]] = Field(default_factory=list)


class GovernanceClient(Protocol):
    """Abstract governance client."""

    def evaluate(self, request: GovernanceEvaluationRequest) -> GovernanceDecision:
        ...


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

    def evaluate(self, request: GovernanceEvaluationRequest) -> GovernanceDecision:
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
