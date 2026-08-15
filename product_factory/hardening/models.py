"""
Shared models for Phase 24 hardening.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils import deterministic_id, utcnow


class ProductAction(str, Enum):
    BUILD = "BUILD"
    COMPILE = "COMPILE"
    LAUNCH = "LAUNCH"
    DEPLOY = "DEPLOY"
    PRICE_CHANGE = "PRICE_CHANGE"
    MARKETING_PUBLISH = "MARKETING_PUBLISH"
    ROLLBACK = "ROLLBACK"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProductGate(str, Enum):
    MARKET_EVIDENCE = "MARKET_EVIDENCE"
    SECURITY = "SECURITY"
    PRICING = "PRICING"
    DEPLOYMENT = "DEPLOYMENT"
    REVENUE_SIMULATION = "REVENUE_SIMULATION"
    GOVERNANCE_APPROVAL = "GOVERNANCE_APPROVAL"


class ProductEvidenceContext(BaseModel):
    """Evidence context used for product governance gates."""

    product_id: str

    has_market_research: bool = False
    has_security_review: bool = False
    has_pricing_plan: bool = False
    has_deployment_plan: bool = False
    has_revenue_simulation: bool = False
    has_customer_analytics: bool = False

    security_findings: int = 0
    critical_findings: int = 0

    approval_refs: List[str] = Field(default_factory=list)


class GovernanceGateResult(BaseModel):
    """Result of one governance gate."""

    gate: ProductGate

    passed: bool

    issues: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)


class ProductGovernanceDecision(BaseModel):
    """Decision produced by product governance."""

    product_id: str

    action: ProductAction

    allowed: bool

    blockers: List[str] = Field(default_factory=list)

    gates: List[GovernanceGateResult] = Field(default_factory=list)

    required_approvals: List[str] = Field(default_factory=list)

    timestamp: str


class ProductApprovalRequest(BaseModel):
    """Approval request for a product action."""

    id: Optional[str] = None

    product_id: str

    action: ProductAction

    requested_by: str

    evidence_refs: List[str] = Field(default_factory=list)

    status: ApprovalStatus = ApprovalStatus.PENDING

    created_at: str
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    comments: str = ""


class MarketEvidenceSource(BaseModel):
    """Source of market evidence."""

    source_id: str

    source_type: str

    reliability: float = Field(default=0.5, ge=0.0, le=1.0)

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class MarketEvidence(BaseModel):
    """Market evidence claim."""

    id: Optional[str] = None

    product_id: str

    claim: str

    source_id: str

    evidence_type: str = "observation"

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    occurred_at: str = Field(default_factory=lambda: utcnow().isoformat())

    payload: Dict[str, Any] = Field(default_factory=dict)


class MarketEvidenceReport(BaseModel):
    """Report describing market evidence quality."""

    product_id: str

    evidence_count: int = 0

    average_confidence: float = 0.0

    corroboration_score: float = 0.0

    overall_quality: float = 0.0

    claims: List[str] = Field(default_factory=list)

    created_at: str


class CompilationTarget(BaseModel):
    """Compiler backend target."""

    backend_id: str

    required: bool = True

    parameters: Dict[str, Any] = Field(default_factory=dict)


class CompilationJob(BaseModel):
    """Compilation job for one backend."""

    id: str

    product_id: str

    backend_id: str

    status: str = "PENDING"

    artifacts: List[str] = Field(default_factory=list)

    logs: List[str] = Field(default_factory=list)

    created_at: str


class CompilationReport(BaseModel):
    """Report produced after product compilation execution."""

    product_id: str

    success: bool = False

    jobs: List[CompilationJob] = Field(default_factory=list)

    missing_required_backends: List[str] = Field(default_factory=list)

    artifact_count: int = 0

    created_at: str


class CustomerSignal(BaseModel):
    """Customer or product operational signal."""

    product_id: str

    event_type: str

    metric: Optional[str] = None

    value: float = 0.0

    severity: str = "INFO"

    segment: Optional[str] = None

    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())


class ProductImprovementRecommendation(BaseModel):
    """Recommendation generated from customer learning."""

    id: Optional[str] = None

    product_id: str

    capability: str

    action: str

    rationale: str

    evidence_refs: List[str] = Field(default_factory=list)

    priority: str = "MEDIUM"


class ProductFitnessReport(BaseModel):
    """Product fitness report generated from customer learning."""

    product_id: str

    objectives: Dict[str, float] = Field(default_factory=dict)

    constraints: Dict[str, bool] = Field(default_factory=dict)

    recommendations: List[ProductImprovementRecommendation] = Field(
        default_factory=list
    )

    created_at: str


class PricingPolicy(BaseModel):
    """Policy for pricing governance."""

    currency: str = "USD"

    allowed_models: List[str] = Field(
        default_factory=lambda: [
            "subscription",
            "freemium",
            "usage",
            "one_time",
        ]
    )

    max_price_change_pct: float = Field(default=20.0, ge=0.0)

    require_approval_for_price_change: bool = True


class BillingPolicy(BaseModel):
    """Policy for billing operations."""

    grace_period_days: int = Field(default=7, ge=0)

    max_payment_retries: int = Field(default=4, ge=0)

    require_tax_compliance: bool = True


class Entitlement(BaseModel):
    """Entitlement granted to a tenant."""

    id: Optional[str] = None

    product_id: str

    tenant_id: str

    plan_id: str

    status: str = "active"

    limits: Dict[str, Any] = Field(default_factory=dict)


class BillingEvent(BaseModel):
    """Billing or revenue event."""

    product_id: str

    tenant_id: str

    event_type: str

    amount: float = 0.0

    currency: str = "USD"

    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())


class RevenueOpsReport(BaseModel):
    """Revenue operations report."""

    product_id: str

    successful_payments: int = 0

    failed_payments: int = 0

    cancellations: int = 0

    recognized_revenue: float = 0.0

    mrr_estimate: float = 0.0

    alerts: List[str] = Field(default_factory=list)

    recommendations: List[str] = Field(default_factory=list)

    created_at: str
