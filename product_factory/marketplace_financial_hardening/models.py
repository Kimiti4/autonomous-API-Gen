"""
Models for Marketplace Production Hardening and Financial Governance.
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


class PaymentStatus(str, Enum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    CANCELLED = "CANCELLED"
    REQUIRES_ACTION = "REQUIRES_ACTION"


class RefundStatus(str, Enum):
    REQUESTED = "REQUESTED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class LedgerEntryType(str, Enum):
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUND_APPROVED = "REFUND_APPROVED"
    REFUND_COMPLETED = "REFUND_COMPLETED"
    FEE_CHARGED = "FEE_CHARGED"
    FEE_ADJUSTED = "FEE_ADJUSTED"
    TAX_CALCULATED = "TAX_CALCULATED"
    TAX_ADJUSTED = "TAX_ADJUSTED"
    PAYOUT_PLANNED = "PAYOUT_PLANNED"
    PAYOUT_COMPLETED = "PAYOUT_COMPLETED"


class FraudAction(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class SLAStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    BREACH = "BREACH"


class SLAStatusOverall(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BREACH = "BREACH"


class SLADomain(str, Enum):
    PAYMENT_WEBHOOK_PROCESSING_LATENCY = "payment_webhook_processing_latency"
    PAYMENT_EVENT_INGESTION_SUCCESS_RATE = "payment_event_ingestion_success_rate"
    REFUND_PROCESSING_LATENCY = "refund_processing_latency"
    RECONCILIATION_FRESHNESS = "reconciliation_freshness"
    FRAUD_ASSESSMENT_LATENCY = "fraud_assessment_latency"
    TAX_CALCULATION_LATENCY = "tax_calculation_latency"
    MARKETPLACE_API_AVAILABILITY = "marketplace_api_availability"
    LISTING_PUBLICATION_LATENCY = "listing_publication_latency"


class SLAComparator(str, Enum):
    LESS_THAN_MS = "LESS_THAN_MS"
    GREATER_THAN_RATE = "GREATER_THAN_RATE"


class GovernanceAction(str, Enum):
    MARKETPLACE_FEE_CHANGE = "MARKETPLACE_FEE_CHANGE"
    MARKETPLACE_PRICING_POLICY_CHANGE = "MARKETPLACE_PRICING_POLICY_CHANGE"
    REFUND_ABOVE_THRESHOLD = "REFUND_ABOVE_THRESHOLD"
    TAX_POLICY_CHANGE = "TAX_POLICY_CHANGE"
    FRAUD_POLICY_CHANGE = "FRAUD_POLICY_CHANGE"
    PAYOUT_POLICY_CHANGE = "PAYOUT_POLICY_CHANGE"
    FINANCIAL_ROLLBACK = "FINANCIAL_ROLLBACK"
    MARKETPLACE_EMERGENCY_SUSPENSION = "MARKETPLACE_EMERGENCY_SUSPENSION"
    MARKETPLACE_DELISTING = "MARKETPLACE_DELISTING"
    FINANCIAL_COMPLIANCE_CERTIFICATION = "FINANCIAL_COMPLIANCE_CERTIFICATION"


class ReconciliationMismatchKind(str, Enum):
    PAYMENT_EVENT_MISSING_LEDGER = "PAYMENT_EVENT_MISSING_LEDGER"
    LEDGER_MISSING_PAYMENT_EVENT = "LEDGER_MISSING_PAYMENT_EVENT"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    DUPLICATE_IDEMPOTENCY_KEY = "DUPLICATE_IDEMPOTENCY_KEY"
    REFUND_WITHOUT_ORIGINAL_PAYMENT = "REFUND_WITHOUT_ORIGINAL_PAYMENT"
    REFUND_EXCEEDS_CAPTURED = "REFUND_EXCEEDS_CAPTURED"
    FEE_MISMATCH = "FEE_MISMATCH"
    TAX_MISMATCH = "TAX_MISMATCH"


class ReconciliationSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReconciliationStatus(str, Enum):
    HEALTHY = "HEALTHY"
    MISMATCHES_DETECTED = "MISMATCHES_DETECTED"
    FAILED = "FAILED"


class PaymentWebhookEnvelope(BaseModel):
    """Normalized envelope for an inbound provider webhook."""

    provider: str

    provider_event_id: str

    idempotency_key: Optional[str] = None

    signature: Optional[str] = None

    timestamp: Optional[datetime] = None

    payload: Dict[str, Any] = Field(default_factory=dict)


class PaymentIntent(BaseModel):
    """A payment intent managed by the marketplace financial control plane."""

    intent_id: str = Field(default_factory=lambda: new_id("pi"))

    marketplace_id: str

    order_id: str

    listing_id: str

    tenant_id: str

    amount: float

    currency: str = "USD"

    status: PaymentStatus = PaymentStatus.CREATED

    provider: str = ""

    provider_intent_id: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)

    updated_at: datetime = Field(default_factory=utcnow)

    idempotency_key: Optional[str] = None

    approval_ref: Optional[str] = None

    governance_ref: Optional[str] = None


class PaymentEvent(BaseModel):
    """A normalized payment event emitted by the payment adapter engine."""

    event_id: str = Field(default_factory=lambda: new_id("payev"))

    intent_id: Optional[str] = None

    marketplace_id: str

    order_id: str

    listing_id: str

    tenant_id: str

    provider: str

    provider_event_id: str

    status: PaymentStatus

    amount: float

    currency: str = "USD"

    idempotency_key: Optional[str] = None

    timestamp: datetime = Field(default_factory=utcnow)

    normalized: bool = True

    evidence_ref: Optional[str] = None

    audit_ref: Optional[str] = None


class RefundRequest(BaseModel):
    """A refund request governed by marketplace policy."""

    refund_id: str = Field(default_factory=lambda: new_id("refund"))

    marketplace_id: str = "marketplace_1"

    order_id: str

    listing_id: str

    tenant_id: str

    amount: float

    currency: str = "USD"

    original_payment_event_id: Optional[str] = None

    reason_code: str = ""

    reason: str = ""

    requested_by: str

    status: RefundStatus = RefundStatus.REQUESTED

    governance_ref: Optional[str] = None

    approval_ref: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)

    updated_at: datetime = Field(default_factory=utcnow)

    idempotency_key: Optional[str] = None

    completed_at: Optional[datetime] = None


class FinancialLedgerEntry(BaseModel):
    """An append-only, idempotent financial ledger entry."""

    ledger_id: str = Field(default_factory=lambda: new_id("le"))

    marketplace_id: str

    order_id: Optional[str] = None

    listing_id: Optional[str] = None

    tenant_id: Optional[str] = None

    entry_type: LedgerEntryType

    amount: float

    currency: str = "USD"

    status: str = "POSTED"

    idempotency_key: Optional[str] = None

    source_event_id: Optional[str] = None

    governance_ref: Optional[str] = None

    actor: str = "system"

    reason: str = ""

    evidence_ref: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)


class ReconciliationMismatch(BaseModel):
    """A detected mismatch during financial reconciliation."""

    mismatch_id: str = Field(default_factory=lambda: new_id("mismatch"))

    marketplace_id: str

    order_id: Optional[str] = None

    kind: ReconciliationMismatchKind

    severity: ReconciliationSeverity

    details: str = ""

    evidence_refs: List[str] = Field(default_factory=list)

    governance_ref: Optional[str] = None

    detected_at: datetime = Field(default_factory=utcnow)


class ReconciliationReport(BaseModel):
    """A reconciliation run report."""

    report_id: str = Field(default_factory=lambda: new_id("recon"))

    marketplace_id: str

    generated_at: datetime = Field(default_factory=utcnow)

    total_entries: int = 0

    mismatch_count: int = 0

    mismatches: List[ReconciliationMismatch] = Field(default_factory=list)

    summary: Dict[str, int] = Field(default_factory=dict)

    governance_ref: Optional[str] = None

    status: ReconciliationStatus = ReconciliationStatus.HEALTHY


class TaxCalculationRequest(BaseModel):
    """Request to calculate tax for an order/line."""

    tax_request_id: str = Field(default_factory=lambda: new_id("txreq"))

    marketplace_id: str

    order_id: str

    listing_id: str

    tenant_id: str

    jurisdiction: str

    amounts: List[Dict[str, Any]] = Field(default_factory=list)

    currency: str = "USD"

    provider: str = ""

    evidence_ref: Optional[str] = None


class TaxCalculationResult(BaseModel):
    """Normalized tax calculation result."""

    tax_request_id: str

    provider: str

    jurisdiction: str

    tax_rate: float = 0.0

    tax_amount: float = 0.0

    currency: str = "USD"

    provider_reference: Optional[str] = None

    calculated_at: datetime = Field(default_factory=utcnow)

    evidence_ref: Optional[str] = None


class FraudAssessment(BaseModel):
    """Fraud assessment for a listing, order, or tenant."""

    assessment_id: str = Field(default_factory=lambda: new_id("frd"))

    listing_id: Optional[str] = None

    tenant_id: Optional[str] = None

    order_id: Optional[str] = None

    provider: str

    fraud_score: float = 0.0

    risk_indicators: List[str] = Field(default_factory=list)

    action: FraudAction = FraudAction.ALLOW

    provider_reference: Optional[str] = None

    timestamp: datetime = Field(default_factory=utcnow)

    evidence_ref: Optional[str] = None

    governance_ref: Optional[str] = None


class SLADefinition(BaseModel):
    """Definition of a marketplace SLA."""

    domain: SLADomain

    target_value: float

    comparator: SLAComparator = SLAComparator.LESS_THAN_MS

    window_seconds: int = 300

    warning_threshold_pct: float = 0.8

    breach_threshold_pct: float = 0.95

    severity_on_breach: ReconciliationSeverity = ReconciliationSeverity.HIGH


class SLAStatusItem(BaseModel):
    """Observed status for a single SLA domain."""

    domain: SLADomain

    status: SLAStatus = SLAStatus.OK

    current_value: float = 0.0

    target_value: float

    breach_count: int = 0

    last_breach_at: Optional[datetime] = None


class SLAStatusReport(BaseModel):
    """SLA operational report."""

    marketplace_id: str

    generated_at: datetime = Field(default_factory=utcnow)

    items: List[SLAStatusItem] = Field(default_factory=list)

    overall_status: SLAStatusOverall = SLAStatusOverall.HEALTHY

    alerts: List[str] = Field(default_factory=list)

    recommendations: List[str] = Field(default_factory=list)


class FinancialComplianceGate(BaseModel):
    """A single financial compliance certification gate."""

    name: str

    passed: bool

    severity: str = "INFO"

    reason: str = ""

    evidence_refs: List[str] = Field(default_factory=list)


class FinancialComplianceReport(BaseModel):
    """Report certifying marketplace financial production readiness."""

    report_id: str = Field(
        default_factory=lambda: new_id("financial_certification")
    )

    marketplace_id: str

    scope: str = "financial_operations"

    status: str = "NOT_CERTIFIED"

    gates: List[FinancialComplianceGate] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    prerequisite_26_8_report_id: Optional[str] = None

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None


class MarketplaceFinancialPolicy(BaseModel):
    """Policy controlling marketplace financial hardening and governance."""

    marketplace_id: str = "marketplace_1"

    auto_approve_refund_threshold_amount: float = 50.0

    auto_approve_refund_threshold_currency: str = "USD"

    auto_approve_small_refunds: bool = True

    require_governance_for_refund_above_threshold: bool = True

    require_governance_for_fee_changes: bool = True

    require_governance_for_tax_policy: bool = True

    require_governance_for_fraud_policy: bool = True

    block_uncertified_products: bool = True

    block_fraud_flagged_from_publication: bool = True

    min_fraud_score_to_hold: float = 0.70

    min_fraud_score_to_block: float = 0.85

    payment_webhook_signature_required: bool = True

    financial_certification_ttl_days: int = Field(default=90, ge=1)

    require_human_financial_certification: bool = True

    allow_conditional_financial_certification: bool = True

    fail_closed_on_adapter_error: bool = True


class GovernanceDecision(BaseModel):
    """A governance evaluation decision."""

    action: GovernanceAction

    actor: str

    allowed: bool

    decision: str = "APPROVED"

    constraints: Dict[str, Any] = Field(default_factory=dict)

    approval_ref: Optional[str] = None

    audit_ref: str = Field(default_factory=lambda: new_id("gov_audit"))

    evidence_refs: List[str] = Field(default_factory=list)

    evaluated_at: datetime = Field(default_factory=utcnow)


class FinancialAuditEvent(BaseModel):
    """A tamper-evident audit event for financial operations."""

    event_id: str = Field(default_factory=lambda: new_id("audit"))

    marketplace_id: str

    action: str

    actor: str

    status: str

    amount: Optional[float] = None

    currency: Optional[str] = "USD"

    idempotency_key: Optional[str] = None

    source_event_id: Optional[str] = None

    governance_ref: Optional[str] = None

    evidence_ref: Optional[str] = None

    reason: str = ""

    created_at: datetime = Field(default_factory=utcnow)


class MarketplaceFinancialReadinessEvidence(BaseModel):
    """Evidence required for marketplace financial compliance certification."""

    slo_definitions: List[str] = Field(default_factory=list)

    runbooks: List[str] = Field(default_factory=list)

    incident_response_plans: List[str] = Field(default_factory=list)

    backup_restore_evidence: List[str] = Field(default_factory=list)

    observability_evidence: List[str] = Field(default_factory=list)

    dashboard_refs: List[str] = Field(default_factory=list)

    marketplace_metrics_refs: List[str] = Field(default_factory=list)

    payment_adapter_evidence: List[str] = Field(default_factory=list)

    fraud_evidence: List[str] = Field(default_factory=list)

    tax_evidence: List[str] = Field(default_factory=list)

    audit_evidence: List[str] = Field(default_factory=list)
