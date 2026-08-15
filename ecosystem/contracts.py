"""
B2B contract and SLA engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .gateway import GovernanceGateway
from .models import (
    B2BContract,
    ContractStatus,
    PenaltyRecord,
    PenaltyStatus,
    SLABreach,
    SLADefinition,
    SLAOperator,
)


class ContractSLAEngine:
    """Manages B2B contracts, SLA monitoring, and penalty enforcement.

    Penalty enforcement (``B2B_SLA_PENALTY_ENFORCEMENT``) is gated through the
    governance gateway when one is configured.
    """

    def __init__(
        self,
        governance_gateway: GovernanceGateway | None = None,
    ) -> None:
        self.governance_gateway = governance_gateway
        self.contracts: Dict[str, B2BContract] = {}
        self.slas: Dict[str, List[SLADefinition]] = {}
        self.breaches: Dict[str, List[SLABreach]] = {}
        self.penalties: Dict[str, List[PenaltyRecord]] = {}

    def create_contract(
        self,
        partner_id: str,
        marketplace_id: str,
        contract_type: str,
        terms: Dict | None = None,
    ) -> B2BContract:
        contract = B2BContract(
            partner_id=partner_id,
            marketplace_id=marketplace_id,
            contract_type=contract_type,
            terms=terms or {},
        )

        self.contracts[contract.id] = contract
        self.slas[contract.id] = []
        self.breaches[contract.id] = []
        self.penalties[contract.id] = []

        return contract

    def add_sla(
        self,
        contract_id: str,
        sla: SLADefinition,
    ) -> SLADefinition:
        contract = self.get_contract(contract_id)

        if contract.status != ContractStatus.ACTIVE:
            raise ValueError("Contract is not active.")

        self.slas[contract_id].append(sla)

        return sla

    def ingest_metric(
        self,
        contract_id: str,
        metric: str,
        value: float,
    ) -> SLABreach | None:
        contract = self.get_contract(contract_id)

        if contract.status != ContractStatus.ACTIVE:
            return None

        for sla in self.slas.get(contract_id, []):
            if sla.metric != metric:
                continue

            if self._is_breach(sla, value):
                breach = SLABreach(
                    contract_id=contract_id,
                    metric=metric,
                    observed_value=value,
                    threshold=sla.threshold,
                    operator=sla.operator,
                )

                self.breaches[contract_id].append(breach)

                return breach

        return None

    def enforce_penalty(
        self,
        contract_id: str,
        breach_id: str,
        penalty_amount: float,
        actor_id: str,
        evidence_refs: Optional[List[str]] = None,
    ) -> PenaltyRecord:
        """Enforce a penalty for a breach (gated: B2B_SLA_PENALTY_ENFORCEMENT)."""
        self.get_contract(contract_id)
        breach = self._get_breach(contract_id, breach_id)

        decision = self.governance_gateway.evaluate_action(
            "B2B_SLA_PENALTY_ENFORCEMENT",
            {
                "contract_id": contract_id,
                "breach_id": breach_id,
                "actor_id": actor_id,
                "evidence_refs": list(evidence_refs or []),
            },
        )

        if decision.decision == "DENY":
            raise PermissionError(
                f"SLA penalty enforcement denied by governance: {decision.reason}"
            )

        if decision.decision == "REQUIRE_APPROVAL":
            return PenaltyRecord(
                contract_id=contract_id,
                breach_id=breach_id,
                penalty_amount=penalty_amount,
                governance_ref=decision.approval_ref,
                evidence_refs=list(evidence_refs or []),
            )

        return PenaltyRecord(
            contract_id=contract_id,
            breach_id=breach_id,
            penalty_amount=penalty_amount,
            status=PenaltyStatus.ENFORCED,
            governance_ref=decision.approval_ref,
            evidence_refs=list(evidence_refs or []),
        )

    def get_contract(self, contract_id: str) -> B2BContract:
        contract = self.contracts.get(contract_id)

        if not contract:
            raise KeyError(f"Contract not found: {contract_id}")

        return contract

    def breaches_for_contract(self, contract_id: str) -> List[SLABreach]:
        return self.breaches.get(contract_id, [])

    def penalties_for_contract(self, contract_id: str) -> List[PenaltyRecord]:
        return self.penalties.get(contract_id, [])

    def _get_breach(self, contract_id: str, breach_id: str) -> SLABreach:
        for breach in self.breaches.get(contract_id, []):
            if breach.id == breach_id:
                return breach
        raise KeyError(f"Breach not found: {breach_id}")

    def _is_breach(self, sla: SLADefinition, value: float) -> bool:
        # An SLA ``operator`` describes the *target* (satisfaction) condition,
        # e.g. ``p95_latency_ms LTE 200`` means the SLA holds only while
        # ``value <= 200``. A breach is therefore the negation of satisfaction.
        if sla.operator == SLAOperator.GT:
            return not (value > sla.threshold)

        if sla.operator == SLAOperator.GTE:
            return not (value >= sla.threshold)

        if sla.operator == SLAOperator.LT:
            return not (value < sla.threshold)

        if sla.operator == SLAOperator.LTE:
            return not (value <= sla.threshold)

        return False
