"""
Models for the Autonomous Product Factory.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .utils import utcnow


class ProductOpportunity(BaseModel):
    """A product opportunity discovered by the factory."""

    id: str

    name: str

    problem_statement: str
    target_market: str

    business_model_hypothesis: str = "subscription"

    severity_score: float = Field(default=0.6, ge=0.0, le=1.0)
    market_size_score: float = Field(default=0.6, ge=0.0, le=1.0)
    feasibility_score: float = Field(default=0.6, ge=0.0, le=1.0)
    strategic_alignment_score: float = Field(default=0.6, ge=0.0, le=1.0)

    total_score: float = Field(default=0.0, ge=0.0, le=1.0)

    status: str = "DISCOVERED"

    evidence_refs: List[str] = Field(default_factory=list)

    created_at: str


class MarketSegment(BaseModel):
    """Market segment discovered during research."""

    id: str
    name: str

    description: str = ""

    priority: str = "MEDIUM"

    size_estimate: str = "unknown"

    evidence_refs: List[str] = Field(default_factory=list)


class CompetitorInfo(BaseModel):
    """Competitor information."""

    name: str

    offering: str = ""

    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)


class MarketResearchReport(BaseModel):
    """Market research evidence for an opportunity."""

    opportunity_id: str

    problem_statement: str
    target_market: str

    segments: List[MarketSegment] = Field(default_factory=list)
    competitors: List[CompetitorInfo] = Field(default_factory=list)

    trends: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    created_at: str


class ProductRequirement(BaseModel):
    """Product requirement derived from strategy."""

    id: str

    statement: str

    priority: str = "MEDIUM"

    source: str = "product_factory"

    evidence_refs: List[str] = Field(default_factory=list)


class ProductCapability(BaseModel):
    """Business capability required by the product."""

    id: str

    name: str

    description: str = ""


class ProductStrategy(BaseModel):
    """Product strategy generated from opportunity and research."""

    product_id: str

    name: str

    vision: str
    positioning: str

    personas: List[str] = Field(default_factory=list)

    core_capabilities: List[ProductCapability] = Field(default_factory=list)
    requirements: List[ProductRequirement] = Field(default_factory=list)

    mvp_scope: List[str] = Field(default_factory=list)
    non_goals: List[str] = Field(default_factory=list)

    roadmap: List[Dict[str, Any]] = Field(default_factory=list)

    monetization_model: str = "subscription"

    created_at: str


class BrandAsset(BaseModel):
    """Brand kit generated for the product."""

    name: str

    tagline: str = ""

    palette: List[str] = Field(default_factory=list)

    voice: List[str] = Field(default_factory=list)

    messaging: Dict[str, Any] = Field(default_factory=dict)

    logo_brief: str = ""


class UXFlow(BaseModel):
    """UX flow specification."""

    name: str

    trigger: str = ""

    steps: List[str] = Field(default_factory=list)

    success_criteria: List[str] = Field(default_factory=list)

    accessibility_requirements: List[str] = Field(default_factory=list)


class UXSpec(BaseModel):
    """UX specification generated for the product."""

    product_id: str

    information_architecture: List[str] = Field(default_factory=list)

    flows: List[UXFlow] = Field(default_factory=list)

    design_principles: List[str] = Field(default_factory=list)

    accessibility: List[str] = Field(default_factory=list)

    created_at: str


class PricingTier(BaseModel):
    """Pricing tier."""

    id: str
    name: str

    price: float = 0.0

    interval: str = "month"

    currency: str = "USD"

    features: List[str] = Field(default_factory=list)

    limits: Dict[str, Any] = Field(default_factory=dict)

    target_segment: str = "general"


class PricingPlan(BaseModel):
    """Pricing plan generated for the product."""

    product_id: str

    model: str = "subscription"

    tiers: List[PricingTier] = Field(default_factory=list)

    free_trial: Dict[str, Any] = Field(default_factory=dict)

    enterprise_options: Dict[str, Any] = Field(default_factory=dict)

    created_at: str


class MarketingCampaign(BaseModel):
    """Marketing campaign compiled for the product."""

    product_id: str

    positioning: str

    channels: List[str] = Field(default_factory=list)

    content_items: List[str] = Field(default_factory=list)

    launch_checklist: List[str] = Field(default_factory=list)

    seo_keywords: List[str] = Field(default_factory=list)

    created_at: str


class RevenueAssumptions(BaseModel):
    """Assumptions used for revenue simulation."""

    visitors: int = Field(default=10_000, ge=0)

    signup_conversion: float = Field(default=0.05, ge=0.0, le=1.0)

    activation_rate: float = Field(default=0.40, ge=0.0, le=1.0)

    paid_conversion: float = Field(default=0.10, ge=0.0, le=1.0)

    monthly_churn: float = Field(default=0.05, ge=0.0, le=1.0)

    avg_revenue_per_user: Optional[float] = None

    months: int = Field(default=12, ge=1, le=60)


class RevenueProjection(BaseModel):
    """Monthly revenue projection."""

    month: int

    visitors: int
    signups: int
    activated: int

    paying_customers: int
    churned_customers: int

    mrr: float
    arr: float

    cumulative_revenue: float


class RevenueScenario(BaseModel):
    """Revenue scenario."""

    name: str

    assumptions: RevenueAssumptions

    projections: List[RevenueProjection] = Field(default_factory=list)


class RevenueSimulation(BaseModel):
    """Revenue simulation result."""

    product_id: str

    scenarios: List[RevenueScenario] = Field(default_factory=list)

    created_at: str


class DeploymentPlan(BaseModel):
    """Deployment and compilation plan."""

    product_id: str

    environments: List[str] = Field(default_factory=list)

    infrastructure_requirements: List[str] = Field(default_factory=list)

    ci_cd_steps: List[str] = Field(default_factory=list)

    observability_requirements: List[str] = Field(default_factory=list)

    rollback_plan: List[str] = Field(default_factory=list)

    compiler_targets: List[str] = Field(default_factory=list)

    approval_required: bool = True

    created_at: str


class CustomerEvent(BaseModel):
    """Customer analytics event."""

    event_type: str

    user_id: Optional[str] = None

    value: Optional[float] = None

    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())

    properties: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsReport(BaseModel):
    """Customer analytics report."""

    product_id: str

    total_signups: int = 0
    total_activations: int = 0
    total_churns: int = 0
    total_payments: int = 0

    mrr: float = 0.0

    activation_rate: float = 0.0
    churn_rate: float = 0.0

    recommendations: List[str] = Field(default_factory=list)

    generated_at: str


class ProductFactoryReport(BaseModel):
    """Full product factory output."""

    product_id: str

    opportunity: ProductOpportunity

    research: MarketResearchReport

    strategy: ProductStrategy

    brand: BrandAsset

    ux: UXSpec

    pricing: PricingPlan

    revenue: RevenueSimulation

    marketing: MarketingCampaign

    deployment: DeploymentPlan

    isr: Dict[str, Any] = Field(default_factory=dict)

    status: str = "BUILT"

    created_at: str


class BuildProductRequest(BaseModel):
    """Request to build a product."""

    name: str

    problem_statement: str

    target_market: str

    business_model_hypothesis: str = "subscription"

    assumptions: Optional[RevenueAssumptions] = None

    context: Dict[str, Any] = Field(default_factory=dict)


class LaunchRequest(BaseModel):
    """Request to launch a product."""

    approval_refs: List[str] = Field(default_factory=list)
