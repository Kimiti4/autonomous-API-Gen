"""
Federation treaty engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .gateway import GovernanceGateway
from .models import FederationTreaty, TreatyStatus, utcnow


class FederationEngine:
    """Manages federation treaties."""

    def __init__(
        self,
        governance_gateway: GovernanceGateway | None = None,
        require_governance: bool = True,
    ) -> None:
        self.governance_gateway = governance_gateway
        self.require_governance = require_governance

        self.treaties: Dict[str, FederationTreaty] = {}

    def create_treaty(
        self,
        name: str,
        source_marketplace_id: str,
        target_marketplace_id: str,
        revenue_share_pct: float = 0.0,
        routing_policy: Dict | None = None,
        expires_at=None,
    ) -> FederationTreaty:
        treaty = FederationTreaty(
            name=name,
            source_marketplace_id=source_marketplace_id,
            target_marketplace_id=target_marketplace_id,
            revenue_share_pct=revenue_share_pct,
            routing_policy=routing_policy or {},
            expires_at=expires_at,
        )

        self.treaties[treaty.id] = treaty

        return treaty

    def activate_treaty(
        self,
        treaty_id: str,
        actor_id: str,
        approval_ref: str | None = None,
    ) -> FederationTreaty:
        treaty = self.get_treaty(treaty_id)

        if self._is_expired(treaty):
            treaty.status = TreatyStatus.EXPIRED
            raise ValueError("Treaty is expired.")

        if self.require_governance:
            if not self.governance_gateway:
                raise PermissionError(
                    "Governance gateway is required for treaty activation."
                )

            decision = self.governance_gateway.evaluate_action(
                action="FEDERATION_TREATY_ACTIVATION",
                context={
                    "treaty_id": treaty.id,
                    "source_marketplace_id": treaty.source_marketplace_id,
                    "target_marketplace_id": treaty.target_marketplace_id,
                    "actor_id": actor_id,
                    "approval_ref": approval_ref,
                },
            )

            if decision.decision == "DENY":
                raise PermissionError(
                    f"Treaty activation denied by governance: {decision.reason}"
                )

            if decision.decision == "REQUIRE_APPROVAL":
                treaty.status = TreatyStatus.PENDING_GOVERNANCE
                treaty.governance_ref = decision.approval_ref
                return treaty

            treaty.governance_ref = decision.approval_ref or approval_ref

        treaty.status = TreatyStatus.ACTIVE

        return treaty

    def update_routing_policy(
        self,
        treaty_id: str,
        routing_policy: Dict,
        actor_id: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> FederationTreaty:
        """Update a treaty's cross-marketplace routing policy.

        Gated by ``CROSS_MARKETPLACE_ROUTING_POLICY_CHANGE``.
        """
        treaty = self.get_treaty(treaty_id)

        if self._is_expired(treaty):
            treaty.status = TreatyStatus.EXPIRED
            raise ValueError("Treaty is expired.")

        if self.require_governance:
            if not self.governance_gateway:
                raise PermissionError(
                    "Governance gateway is required for routing policy change."
                )

            decision = self.governance_gateway.evaluate_action(
                action="CROSS_MARKETPLACE_ROUTING_POLICY_CHANGE",
                context={
                    "treaty_id": treaty_id,
                    "actor_id": actor_id,
                    "evidence_refs": list(evidence_refs or []),
                },
            )

            if decision.decision == "DENY":
                raise PermissionError(
                    f"Routing policy change denied by governance: {decision.reason}"
                )

            if decision.decision == "REQUIRE_APPROVAL":
                treaty.status = TreatyStatus.PENDING_GOVERNANCE
                treaty.governance_ref = decision.approval_ref
                return treaty

            treaty.governance_ref = decision.approval_ref or treaty.governance_ref

        treaty.routing_policy = routing_policy

        return treaty

    def suspend_treaty(
        self,
        treaty_id: str,
        reason: str,
        actor_id: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> FederationTreaty:
        treaty = self.get_treaty(treaty_id)

        if self.require_governance:
            if not self.governance_gateway:
                raise PermissionError(
                    "Governance gateway is required for treaty suspension."
                )

            decision = self.governance_gateway.evaluate_action(
                action="ECOSYSTEM_SUSPENSION",
                context={
                    "treaty_id": treaty_id,
                    "reason": reason,
                    "actor_id": actor_id,
                    "evidence_refs": list(evidence_refs or []),
                },
            )

            if decision.decision == "DENY":
                raise PermissionError(
                    f"Treaty suspension denied by governance: {decision.reason}"
                )

            if decision.decision == "REQUIRE_APPROVAL":
                treaty.status = TreatyStatus.PENDING_GOVERNANCE
                treaty.governance_ref = decision.approval_ref
                return treaty

            treaty.governance_ref = decision.approval_ref or treaty.governance_ref

        treaty.status = TreatyStatus.SUSPENDED

        return treaty

    def get_treaty(self, treaty_id: str) -> FederationTreaty:
        treaty = self.treaties.get(treaty_id)

        if not treaty:
            raise KeyError(f"Treaty not found: {treaty_id}")

        return treaty

    def active_treaties_for(self, marketplace_id: str) -> List[FederationTreaty]:
        active = []

        for treaty in self.treaties.values():
            if treaty.source_marketplace_id != marketplace_id:
                continue

            if self._is_active(treaty):
                active.append(treaty)

        return active

    def _is_active(self, treaty: FederationTreaty) -> bool:
        if self._is_expired(treaty):
            treaty.status = TreatyStatus.EXPIRED
            return False

        return treaty.status == TreatyStatus.ACTIVE

    def _is_expired(self, treaty: FederationTreaty) -> bool:
        if not treaty.expires_at:
            return False

        return treaty.expires_at < utcnow()
