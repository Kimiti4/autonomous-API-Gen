"""
Partner and vendor identity engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .gateway import GovernanceGateway
from .models import PartnerOrganization, PartnerStatus, PartnerType


class PartnerEngine:
    """Manages ecosystem partners.

    High-risk partner onboarding (activation) is gated through the governance
    gateway when one is configured.
    """

    def __init__(
        self,
        governance_gateway: GovernanceGateway | None = None,
    ) -> None:
        self.governance_gateway = governance_gateway
        self.partners: Dict[str, PartnerOrganization] = {}

    def register_partner(
        self,
        name: str,
        partner_type: PartnerType = PartnerType.VENDOR,
        capabilities: List[str] | None = None,
        evidence_refs: List[str] | None = None,
    ) -> PartnerOrganization:
        partner = PartnerOrganization(
            name=name,
            partner_type=partner_type,
            capabilities=capabilities or [],
            evidence_refs=evidence_refs or [],
        )

        self.partners[partner.id] = partner

        return partner

    def activate_partner(
        self,
        partner_id: str,
        actor_id: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> PartnerOrganization:
        partner = self.get_partner(partner_id)

        if self.governance_gateway is not None:
            decision = self.governance_gateway.evaluate_action(
                "PARTNER_ONBOARDING_HIGH_RISK",
                {
                    "partner_id": partner_id,
                    "partner_name": partner.name,
                    "actor_id": actor_id,
                    "evidence_refs": list(evidence_refs or []),
                },
            )
            if decision.decision == "DENY":
                raise PermissionError(
                    f"Partner activation denied by governance: {decision.reason}"
                )
            if decision.decision == "REQUIRE_APPROVAL":
                partner.governance_ref = decision.approval_ref
                # Remains PENDING until governance approval is submitted.
                return partner
            partner.governance_ref = decision.approval_ref

        partner.status = PartnerStatus.ACTIVE

        return partner

    def suspend_partner(
        self,
        partner_id: str,
        reason: str,
        actor_id: str,
    ) -> PartnerOrganization:
        partner = self.get_partner(partner_id)

        partner.status = PartnerStatus.SUSPENDED

        return partner

    def adjust_trust(
        self,
        partner_id: str,
        delta: float,
        reason: str,
    ) -> PartnerOrganization:
        partner = self.get_partner(partner_id)

        partner.trust_score = max(0.0, min(1.0, partner.trust_score + delta))

        return partner

    def get_partner(self, partner_id: str) -> PartnerOrganization:
        partner = self.partners.get(partner_id)

        if not partner:
            raise KeyError(f"Partner not found: {partner_id}")

        return partner

    def active_partners(self) -> List[PartnerOrganization]:
        return [
            partner
            for partner in self.partners.values()
            if partner.status == PartnerStatus.ACTIVE
        ]
