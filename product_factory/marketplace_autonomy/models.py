"""
Models for autonomous marketplace design and economics.
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


class PricingModel(str, Enum):
    SUBSCRIPTION = "subscription"
    FREEMIUM = "freemium"
    USAGE = "usage"
    ONE_TIME = "one_time"


class ProposalType(str, Enum):
    CATEGORY_STRUCTURE = "CATEGORY_STRUCTURE"
    RANKING_POLICY = "RANKING_POLICY"
    PRICING_POLICY = "PRICING_POLICY"
    CURATION_POLICY = "CURATION_POLICY"
    PRODUCT_PORTFOLIO = "PRODUCT_PORTFOLIO"
    UX_FLOW = "UX_FLOW"
    FRAUD_CONTROL = "FRAUD_CONTROL"


class ProposalStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_GOVERNANCE = "PENDING_GOVERNANCE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPERIMENTING = "EXPERIMENTING"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"


class ExperimentStatus(str, Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    GUARDRAIL_TRIGGERED = "GUARDRAIL_TRIGGERED"
    CONCLUDED = "CONCLUDED"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"


class MarketplaceAutonomyPolicy(BaseModel):
    """Policy controlling autonomous marketplace behavior."""

    default_currency: str = "USD"

    allowed_pricing_models: List[PricingModel] = Field(
        default_factory=lambda: [
            PricingModel.SUBSCRIPTION,
            PricingModel.FREEMIUM,
            PricingModel.USAGE,
            PricingModel.ONE_TIME,
        ]
    )

    max_fee_change_pct: float = Field(default=10.0, ge=0.0)

    require_human_approval_for_fee_change: bool = True

    require_human_approval_for_ranking_change: bool = True

    require_human_approval_for_curation_change: bool = True

    max_experiment_traffic_pct: float = Field(default=20.0, ge=0.0, le=100.0)

    block_uncertified_products: bool = True

    block_products_with_fraud_alert: bool = True

    refund_rate_alert_threshold: float = Field(default=0.15, ge=0.0, le=1.0)

    fraud_score_alert_threshold: float = Field(default=0.70, ge=0.0, le=1.0)

    min_certification_score_for_featured_listing: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
    )


class MarketplaceMetricSnapshot(BaseModel):
    """Marketplace operational metrics snapshot."""

    marketplace_id: str

    period_start: datetime
    period_end: datetime

    listing_count: int = 0
    published_listing_count: int = 0
    certified_listing_count: int = 0

    sales_count: int = 0
    refund_count: int = 0

    gross_revenue: float = 0.0
    net_revenue: float = 0.0
    mrr_estimate: float = 0.0

    conversion_rate: float = 0.0

    average_rating: float = 0.0

    support_ticket_count: int = 0

    fraud_alert_count: int = 0

    category_demand: Dict[str, float] = Field(default_factory=dict)

    category_product_counts: Dict[str, int] = Field(default_factory=dict)

    metadata: Dict[str, Any] = Field(default_factory=dict)


class MarketplaceFitnessReport(BaseModel):
    """Marketplace fitness evaluation."""

    marketplace_id: str

    objectives: Dict[str, float] = Field(default_factory=dict)

    constraints: Dict[str, bool] = Field(default_factory=dict)

    alerts: List[str] = Field(default_factory=list)

    recommendations: List[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=utcnow)


class DemandOpportunity(BaseModel):
    """Demand gap or marketplace opportunity."""

    id: str = Field(default_factory=lambda: new_id("demand_opportunity"))

    marketplace_id: str

    category: str

    demand_score: float = 0.0

    product_count: int = 0

    gap_score: float = 0.0

    evidence_refs: List[str] = Field(default_factory=list)

    recommendation: str = ""

    created_at: datetime = Field(default_factory=utcnow)


class PricingPolicyChange(BaseModel):
    """Proposed pricing or fee policy change."""

    current_fee_pct: Optional[float] = None

    proposed_fee_pct: Optional[float] = None

    pricing_model: Optional[PricingModel] = None

    rationale: str = ""

    expected_impact: Dict[str, float] = Field(default_factory=dict)

    approval_required: bool = False


class RankingPolicy(BaseModel):
    """Marketplace ranking policy."""

    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "certification_score": 0.25,
            "test_score": 0.20,
            "security_score": 0.20,
            "rating": 0.15,
            "support_health": 0.10,
            "novelty": 0.05,
            "revenue_health": 0.05,
        }
    )

    require_certified: bool = True

    block_fraud_flagged: bool = True

    explanation_required: bool = True


class ListingRankingContext(BaseModel):
    """Context used to rank a marketplace listing."""

    listing_id: str

    product_id: str

    certified: bool = False

    certification_score: float = 0.0

    test_score: float = 0.0

    security_score: float = 0.0

    rating: float = 0.0

    support_health: float = 0.0

    novelty: float = 0.0

    revenue_health: float = 0.0

    fraud_score: float = 0.0

    refund_rate: float = 0.0


class RankedListing(BaseModel):
    """Ranked marketplace listing."""

    listing_id: str

    score: float

    included: bool

    exclusion_reasons: List[str] = Field(default_factory=list)

    feature_contributions: Dict[str, float] = Field(default_factory=dict)

    explanation: str = ""


class FraudAssessment(BaseModel):
    """Fraud assessment for a listing or publisher."""

    entity_id: str

    fraud_score: float = 0.0

    indicators: List[str] = Field(default_factory=list)

    severity: str = "LOW"

    recommended_action: str = "MONITOR"


class MarketplaceDesignProposal(BaseModel):
    """Proposal to change marketplace design or economics."""

    id: str = Field(default_factory=lambda: new_id("marketplace_design_proposal"))

    marketplace_id: str

    proposal_type: ProposalType

    title: str

    rationale: str

    changes: Dict[str, Any] = Field(default_factory=dict)

    evidence_refs: List[str] = Field(default_factory=list)

    fitness_impact: Dict[str, float] = Field(default_factory=dict)

    governance_required: bool = True

    status: ProposalStatus = ProposalStatus.DRAFT

    approval_ref: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)

    updated_at: datetime = Field(default_factory=utcnow)


class ExperimentGuardrails(BaseModel):
    """Guardrails for marketplace experiments."""

    max_refund_rate: float = Field(default=0.15, ge=0.0, le=1.0)

    max_fraud_score: float = Field(default=0.70, ge=0.0, le=1.0)

    min_conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    max_support_ticket_increase_pct: float = Field(default=25.0, ge=0.0)


class MarketplaceExperiment(BaseModel):
    """Marketplace experiment."""

    id: str = Field(default_factory=lambda: new_id("marketplace_experiment"))

    proposal_id: str

    marketplace_id: str

    name: str

    variant_config: Dict[str, Any] = Field(default_factory=dict)

    traffic_pct: float = Field(default=5.0, ge=0.0, le=100.0)

    status: ExperimentStatus = ExperimentStatus.DRAFT

    guardrails: ExperimentGuardrails = Field(default_factory=ExperimentGuardrails)

    started_at: Optional[datetime] = None

    ended_at: Optional[datetime] = None

    observed_metrics: Dict[str, float] = Field(default_factory=dict)

    conclusion: str = ""

    created_at: datetime = Field(default_factory=utcnow)


class MarketplaceAutonomyReport(BaseModel):
    """Report produced by marketplace autonomy analysis."""

    marketplace_id: str

    fitness: MarketplaceFitnessReport

    opportunities: List[DemandOpportunity] = Field(default_factory=list)

    fraud_alerts: List[FraudAssessment] = Field(default_factory=list)

    proposals: List[MarketplaceDesignProposal] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=utcnow)
