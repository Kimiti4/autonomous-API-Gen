"""
Settlement coordination engine.
"""

from __future__ import annotations

from .gateway import GovernanceGateway, SettlementAdapter
from .ledger import FinancialLedgerEngine
from .models import SettlementPolicy
from .reconciliation import ReconciliationEngine
from .settlement import SettlementEngine


class MarketplaceSettlementEngine:
    """Coordinates ledger, reconciliation, and settlement."""

    def __init__(
        self,
        governance_gateway: GovernanceGateway | None = None,
        settlement_adapter: SettlementAdapter | None = None,
        policy: SettlementPolicy | None = None,
    ) -> None:
        self.policy = policy or SettlementPolicy()

        self.ledger = FinancialLedgerEngine(self.policy)

        self.reconciliation = ReconciliationEngine(
            ledger=self.ledger,
            policy=self.policy,
        )

        self.settlement = SettlementEngine(
            ledger=self.ledger,
            reconciliation=self.reconciliation,
            governance_gateway=governance_gateway,
            settlement_adapter=settlement_adapter,
            policy=self.policy,
        )

    def report(self):
        return {
            "ledger_entries": len(self.ledger.entries),
            "financial_events": len(self.ledger.events),
            "reconciliation_reports": len(self.reconciliation.reports),
            "open_mismatches": len(
                [
                    mismatch
                    for mismatch in self.reconciliation.mismatches.values()
                    if mismatch.status.value == "OPEN"
                ]
            ),
            "settlement_batches": len(self.settlement.batches),
            "payout_instructions": len(self.settlement.payouts),
        }
