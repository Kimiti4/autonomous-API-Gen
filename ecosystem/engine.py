"""
Ecosystem coordination engine.

Wires the treaty (federation), partner, routing, B2B contract, and SLA
engines together behind a single facade. When no ``governance_gateway`` is
provided the engine auto-builds a real Phase 28 ``GovernanceKernel`` (via
:func:`ecosystem.gateway._default_governance_gateway`) so that all high-risk
ecosystem actions are governed by default; a permissive static gateway is
used only when Phase 28 is unavailable.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .contracts import ContractSLAEngine
from .federation import FederationEngine
from .gateway import (
    GovernanceGateway,
    _default_governance_gateway,
)
from .models import EcosystemReport, EcosystemSyncRecord, PenaltyRecord
from .partners import PartnerEngine
from .routing import RoutingEngine


class EcosystemSyncEngine:
    """In-memory ecosystem knowledge sync engine."""

    def __init__(self) -> None:
        self.records: list[EcosystemSyncRecord] = []

    def record(
        self,
        entity_type: str,
        entity_id: str,
        payload: Dict,
    ) -> EcosystemSyncRecord:
        sync_record = EcosystemSyncRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )

        self.records.append(sync_record)

        return sync_record


class EcosystemEngine:
    """Coordinates ecosystem subsystems."""

    def __init__(
        self,
        governance_gateway: GovernanceGateway | None = None,
    ) -> None:
        self.governance_gateway = (
            governance_gateway or _default_governance_gateway()
        )

        self.federation = FederationEngine(self.governance_gateway)
        self.partners = PartnerEngine(self.governance_gateway)
        self.contracts = ContractSLAEngine(self.governance_gateway)
        self.routing = RoutingEngine(self.federation, self.partners)
        self.sync = EcosystemSyncEngine()

    def sync_all(self) -> int:
        for treaty in self.federation.treaties.values():
            self.sync.record(
                entity_type="FEDERATION_TREATY",
                entity_id=treaty.id,
                payload=treaty.model_dump(mode="json"),
            )

        for partner in self.partners.partners.values():
            self.sync.record(
                entity_type="PARTNER_ORGANIZATION",
                entity_id=partner.id,
                payload=partner.model_dump(mode="json"),
            )

        for contract in self.contracts.contracts.values():
            self.sync.record(
                entity_type="B2B_CONTRACT",
                entity_id=contract.id,
                payload=contract.model_dump(mode="json"),
            )

        return len(self.sync.records)

    def report(self) -> EcosystemReport:
        active_treaties = len(
            [
                treaty
                for treaty in self.federation.treaties.values()
                if self.federation._is_active(treaty)
            ]
        )

        active_partners = len(self.partners.active_partners())

        active_contracts = len(
            [
                contract
                for contract in self.contracts.contracts.values()
                if contract.status.value == "ACTIVE"
            ]
        )

        sla_breaches = sum(
            len(breaches)
            for breaches in self.contracts.breaches.values()
        )

        return EcosystemReport(
            active_treaties=active_treaties,
            active_partners=active_partners,
            active_contracts=active_contracts,
            sla_breaches=sla_breaches,
            synced_records=len(self.sync.records),
        )

    def suspend_treaty(self, treaty_id: str, reason: str, actor_id: str):
        return self.federation.suspend_treaty(treaty_id, reason, actor_id)

    def update_routing_policy(
        self,
        treaty_id: str,
        routing_policy: Dict,
        actor_id: str,
    ):
        return self.federation.update_routing_policy(treaty_id, routing_policy, actor_id)

    def enforce_penalty(
        self,
        contract_id: str,
        breach_id: str,
        penalty_amount: float,
        actor_id: str,
    ) -> PenaltyRecord:
        return self.contracts.enforce_penalty(
            contract_id=contract_id,
            breach_id=breach_id,
            penalty_amount=penalty_amount,
            actor_id=actor_id,
        )

    def submit_approval(self, approval_id: str, actor: str = "ecosystem", comments: Optional[str] = None) -> str:
        if hasattr(self.governance_gateway, "submit_approval"):
            return self.governance_gateway.submit_approval(  # type: ignore[union-attr]
                approval_id, actor=actor, comments=comments
            )
        raise PermissionError("Governance gateway does not support approval submission.")

    def list_pending_approvals(self, action: str) -> List[str]:
        if hasattr(self.governance_gateway, "list_pending_approvals"):
            return self.governance_gateway.list_pending_approvals(action)  # type: ignore[union-attr]
        return []
