"""
Tax adapter framework and tax calculation engine.

Tax calculation is delegated to a pluggable adapter. The engine normalizes
results and emits tax ledger adjustments.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .ledger import FinancialLedgerEngine
from .models import (
    FinancialLedgerEntry,
    LedgerEntryType,
    TaxCalculationRequest,
    TaxCalculationResult,
)


class TaxProviderAdapter:
    """Base contract for a tax provider adapter."""

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResult:
        raise NotImplementedError

    def validate_tax_registration(self, tax_id: str) -> bool:
        return False

    def get_tax_report(self, *args, **kwargs) -> Dict:
        return {}


class NoopTaxAdapter(TaxProviderAdapter):
    """Default no-op tax adapter."""

    def calculate_tax(self, request: TaxCalculationRequest) -> TaxCalculationResult:
        tax_amount = 0.0

        for line in request.amounts:
            amount = float(line.get("amount", 0.0))
            tax_amount += amount * 0.0

        return TaxCalculationResult(
            tax_request_id=request.tax_request_id,
            provider=request.provider or "noop",
            jurisdiction=request.jurisdiction,
            tax_rate=0.0,
            tax_amount=tax_amount,
            currency=request.currency,
            provider_reference=None,
            evidence_ref=request.evidence_ref,
        )


class TaxAdapterEngine:
    """Calculates tax through an adapter and records ledger adjustments."""

    def __init__(
        self,
        tax_adapter: Optional[TaxProviderAdapter] = None,
        ledger: Optional[FinancialLedgerEngine] = None,
    ) -> None:
        self.tax_adapter = tax_adapter or NoopTaxAdapter()
        self.ledger = ledger

    def calculate_tax(
        self,
        request: TaxCalculationRequest,
    ) -> TaxCalculationResult:
        result = self.tax_adapter.calculate_tax(request)

        if result.tax_amount > 0:
            self._ledgerize_tax(request, result)

        return result

    def validate_tax_registration(self, tax_id: str) -> bool:
        return self.tax_adapter.validate_tax_registration(tax_id)

    def get_tax_report(self, *args, **kwargs) -> Dict:
        return self.tax_adapter.get_tax_report(*args, **kwargs)

    def recent_calculations(self) -> List[TaxCalculationResult]:
        return getattr(self, "_calculations", [])

    def _ledgerize_tax(
        self,
        request: TaxCalculationRequest,
        result: TaxCalculationResult,
    ) -> None:
        if not self.ledger:
            return

        self.ledger.append(
            FinancialLedgerEntry(
                marketplace_id=request.marketplace_id,
                order_id=request.order_id,
                listing_id=request.listing_id,
                tenant_id=request.tenant_id,
                entry_type=LedgerEntryType.TAX_CALCULATED,
                amount=result.tax_amount,
                currency=result.currency,
                status="POSTED",
                idempotency_key=f"tax_{request.tax_request_id}",
                source_event_id=request.tax_request_id,
                evidence_ref=result.evidence_ref or request.evidence_ref,
            )
        )
