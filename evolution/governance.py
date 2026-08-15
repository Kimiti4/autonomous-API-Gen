"""
Evolution governance client.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from .models import EvolutionProposal, GovernanceDecision


class EvolutionGovernanceClient(Protocol):
    """Abstract governance client."""

    def evaluate(
        self,
        proposal: EvolutionProposal,
        context: dict,
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
        proposal: EvolutionProposal,
        context: dict,
    ) -> GovernanceDecision:
        return GovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


class HttpGovernanceKernelClient:
    """
    HTTP client for the Phase 28 Governance Kernel.

    This client fails closed if governance is unavailable.
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
        proposal: EvolutionProposal,
        context: dict,
    ) -> GovernanceDecision:
        url = f"{self._base_url}/v1/governance/evaluate"

        payload = {
            "subject_type": "EVOLUTION_PROPOSAL",
            "subject_id": proposal.id,
            "action": "EVOLVE_ISR",
            "actor": {
                "actor_type": "AUTONOMOUS_AGENT",
                "actor_id": "self_evolution_engine",
                "roles": ["evolution_proposer"],
                "delegated_authority": [],
            },
            "context": context,
            "evidence_refs": [
                f"evolution_proposal:{proposal.id}",
            ],
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()

                return GovernanceDecision.model_validate(response.json())

        except Exception as exc:
            return GovernanceDecision(
                decision="DENY",
                reason=f"Governance Kernel unavailable or error: {exc}",
            )
