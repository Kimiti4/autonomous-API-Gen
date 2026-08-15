"""
Models for marketplace financial reconciliation and settlement.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Generate a prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class FinancialEventType(str, Enum):
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUND_ISSUED = "REFUND_ISSUED"
    REFUND_FAILED = "REFUND_FAILED"
    FEE_CHARGED = "FEE_CHARGED"
    TAX_CHARGED = "TAX_CHARGED"
    CHARGEBACK_OPENED = "CHARGEBACK_OPENED"
    ADJUSTMENT = "ADJUSTMENT"
    PAYOUT_REQUESTED = "PAYOUT_REQUESTED"
    PAYOUT_COMPLETED = "PAYOUT_COMPLETED"


class LedgerEntryType(str, Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    FEE = "FEE"
    TAX = "TAX"
    ADJUSTMENT = "ADJUSTMENT"
    SETTLEMENT = "SETTLEMENT"


class FinancialEvent(BaseModel):
    """Normalized financial event."""

    id: str = Field(default_factory=lambda: new_id("financial_event"))

    idempotency_key: str

    event_type: FinancialEventType

    marketplace_id: str

    tenant_id: str

    order_id: Optional[str] = None

    amount: float = Field(default=0.0, ge=0.0)

    currency: str = "USD"

    payload: Dict[str, Any] = Field(default_factory=dict)

    occurred_at: datetime = Field(default_factory=utcnow)


class LedgerEntry(BaseModel):
    """Financial ledger entry."""

    id: str = Field(default_factory=lambda: new_id("ledger_entry"))

    event_id: Optional[str] = None

    idempotency_key: str

    entry_type: LedgerEntryType

    marketplace_id: str

    tenant_id: str

    order_id: Optional[str] = None

    amount: float

    currency: str

    created_at: datetime = Field(default_factory=utcnow)


class ReconciliationStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


class MismatchStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class ReconciliationMismatch(BaseModel):
    """Reconciliation mismatch."""

    id: str

    marketplace_id: str

    mismatch_type: str

    severity: str

    entity_id: Optional[str] = None

    expected: str

    observed: str

    details: Dict[str, Any] = Field(default_factory=dict)

    status: MismatchStatus = MismatchStatus.OPEN

    resolved_by: Optional[str] = None

    resolved_at: Optional[datetime] = None


class ReconciliationReport(BaseModel):
    """Reconciliation report."""

    id: str = Field(default_factory=lambda: new_id("reconciliation_report"))

    marketplace_id: str

    period_start: datetime

    period_end: datetime

    status: ReconciliationStatus

    mismatches: List[ReconciliationMismatch] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=utcnow)


class SettlementStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_GOVERNANCE = "PENDING_GOVERNANCE"
    APPROVED = "APPROVED"
    SETTLING = "SETTLING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class SettlementBatch(BaseModel):
    """Settlement batch for a participant."""

    id: str = Field(default_factory=lambda: new_id("settlement_batch"))

    marketplace_id: str

    tenant_id: str

    currency: str

    period_start: datetime

    period_end: datetime

    gross_amount: float = 0.0

    refund_amount: float = 0.0

    fee_amount: float = 0.0

    tax_amount: float = 0.0

    net_amount: float = 0.0

    entry_ids: List[str] = Field(default_factory=list)

    status: SettlementStatus = SettlementStatus.DRAFT

    governance_ref: Optional[str] = None

    provider_ref: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)

    executed_at: Optional[datetime] = None


class PayoutInstruction(BaseModel):
    """Payout instruction produced from a settlement batch."""

    id: str = Field(default_factory=lambda: new_id("payout_instruction"))

    settlement_batch_id: str

    participant_id: str

    amount: float

    currency: str

    status: str = "CREATED"

    provider_ref: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)


class SettlementPolicy(BaseModel):
    """Policy controlling settlement behavior."""

    require_governance_for_settlement: bool = True

    allow_negative_settlement: bool = False

    allow_negative_balances: bool = False

    min_settlement_amount: float = Field(default=0.0, ge=0.0)

    max_batch_entries: int = Field(default=5000, ge=1)

    settlement_currency: str = "USD"
