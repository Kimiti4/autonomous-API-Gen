"""
Autonomous Product Factory engine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .models import (
    AnalyticsReport,
    BrandAsset,
    BuildProductRequest,
    CompetitorInfo,
    CustomerEvent,
    DeploymentPlan,
    MarketResearchReport,
    MarketSegment,
    MarketingCampaign,
    PricingPlan,
    PricingTier,
    ProductCapability,
    ProductFactoryReport,
    ProductOpportunity,
    ProductRequirement,
    ProductStrategy,
    RevenueAssumptions,
    RevenueProjection,
    RevenueScenario,
    RevenueSimulation,
    UXFlow,
    UXSpec,
)
from .utils import deterministic_id, sha256_hex, slugify, utcnow


class ProductFactoryPolicy(BaseModel):
    """Policy controlling product factory behavior."""

    require_launch_approval: bool = True

    default_currency: str = "USD"

    max_mvp_capabilities: int = Field(default=5, ge=1, le=20)


class OpportunityDiscoveryEngine:
    """Discovers and scores product opportunities."""

    def discover(self, payload: Dict[str, Any]) -> List[ProductOpportunity]:
        ideas = payload.get("ideas", [])

        if not ideas:
            ideas = [
                {
                    "name": "Generic Autonomous SaaS",
                    "problem_statement": "Automate a manual workflow.",
                    "target_market": "SMB operators",
                    "business_model": "subscription",
                }
            ]

        opportunities: List[ProductOpportunity] = []

        for index, idea in enumerate(ideas):
            created_at = utcnow().isoformat()

            opportunity_id = deterministic_id(
                "product_opportunity",
                {
                    "name": idea.get("name", "unnamed"),
                    "problem_statement": idea.get("problem_statement", ""),
                    "index": index,
                    "created_at": created_at,
                },
            )

            severity = float(idea.get("severity_score", 0.6))
            market_size = float(idea.get("market_size_score", 0.6))
            feasibility = float(idea.get("feasibility_score", 0.6))
            alignment = float(idea.get("strategic_alignment_score", 0.6))

            total_score = round(
                (severity * 0.35)
                + (market_size * 0.30)
                + (feasibility * 0.20)
                + (alignment * 0.15),
                4,
            )

            opportunities.append(
                ProductOpportunity(
                    id=opportunity_id,
                    name=idea.get("name", "Unnamed Opportunity"),
                    problem_statement=idea.get("problem_statement", ""),
                    target_market=idea.get("target_market", ""),
                    business_model_hypothesis=idea.get(
                        "business_model",
                        "subscription",
                    ),
                    severity_score=severity,
                    market_size_score=market_size,
                    feasibility_score=feasibility,
                    strategic_alignment_score=alignment,
                    total_score=total_score,
                    status="DISCOVERED",
                    evidence_refs=idea.get("evidence_refs", []),
                    created_at=created_at,
                )
            )

        opportunities.sort(key=lambda item: item.total_score, reverse=True)

        return opportunities


class MarketResearchEngine:
    """Produces deterministic market research reports."""

    def research(
        self,
        opportunity: ProductOpportunity,
        context: Optional[Dict[str, Any]] = None,
    ) -> MarketResearchReport:
        context = context or {}

        segments = context.get("segments") or [
            MarketSegment(
                id="segment_smb",
                name="SMB Operators",
                description="Small business operators seeking automation.",
                priority="HIGH",
                size_estimate="medium",
            ),
            MarketSegment(
                id="segment_mid_market",
                name="Mid-Market Teams",
                description="Teams needing workflow standardization.",
                priority="MEDIUM",
                size_estimate="medium",
            ),
            MarketSegment(
                id="segment_enterprise",
                name="Enterprise Platforms",
                description="Enterprises needing governance and integration.",
                priority="LOW",
                size_estimate="large",
            ),
        ]

        competitors = context.get("competitors") or [
            CompetitorInfo(
                name="Manual Process",
                offering="Spreadsheets and manual coordination.",
                strengths=["Familiar", "Low initial cost"],
                weaknesses=["Error-prone", "Hard to scale"],
            ),
            CompetitorInfo(
                name="Legacy Suite",
                offering="Existing enterprise suite.",
                strengths=["Brand recognition", "Existing contracts"],
                weaknesses=["Slow innovation", "Complex UX"],
            ),
        ]

        trends = context.get("trends") or [
            "workflow automation",
            "AI-assisted operations",
            "self-serve onboarding",
            "usage-based pricing",
            "operational observability",
        ]

        risks = context.get("risks") or [
            "market education required",
            "integration complexity",
            "data privacy concerns",
            "pricing sensitivity",
        ]

        evidence_refs = list(opportunity.evidence_refs) + [
            f"opportunity:{opportunity.id}"
        ]

        return MarketResearchReport(
            opportunity_id=opportunity.id,
            problem_statement=opportunity.problem_statement,
            target_market=opportunity.target_market,
            segments=segments,
            competitors=competitors,
            trends=trends,
            risks=risks,
            evidence_refs=evidence_refs,
            created_at=utcnow().isoformat(),
        )


class ProductStrategyGenerator:
    """Generates product strategy from opportunity and research."""

    def generate(
        self,
        product_id: str,
        opportunity: ProductOpportunity,
        research: MarketResearchReport,
    ) -> ProductStrategy:
        keywords = (
            f"{opportunity.name} {opportunity.problem_statement}"
        ).lower()

        capabilities: List[ProductCapability] = []

        def add_capability(capability_id: str, name: str, description: str):
            capabilities.append(
                ProductCapability(
                    id=capability_id,
                    name=name,
                    description=description,
                )
            )

        add_capability(
            "identity_access",
            "Identity and Access Management",
            "Authentication, authorization, and tenant isolation.",
        )

        add_capability(
            "core_workflow",
            "Core Workflow",
            "Primary workflow that solves the customer problem.",
        )

        if any(word in keywords for word in ["invoice", "billing", "payment"]):
            add_capability(
                "billing_management",
                "Billing Management",
                "Invoices, subscriptions, payment state, and billing events.",
            )

        if any(word in keywords for word in ["analytic", "metric", "report"]):
            add_capability(
                "analytics_reporting",
                "Analytics and Reporting",
                "Operational metrics, dashboards, and exports.",
            )

        if opportunity.business_model_hypothesis in {
            "subscription",
            "freemium",
            "usage",
        }:
            add_capability(
                "subscription_management",
                "Subscription Management",
                "Plans, entitlements, trials, and lifecycle events.",
            )

        add_capability(
            "notifications",
            "Notifications",
            "Email and in-app notifications for important events.",
        )

        requirements: List[ProductRequirement] = []

        for capability in capabilities:
            requirements.append(
                ProductRequirement(
                    id=f"req-{capability.id}",
                    statement=(
                        f"The product shall provide {capability.name}."
                    ),
                    priority="HIGH",
                    source="product_strategy",
                    evidence_refs=[f"capability:{capability.id}"],
                )
            )

        personas = [
            f"{segment.name} primary user"
            for segment in research.segments[:3]
        ]

        mvp_scope = [
            capability.name
            for capability in capabilities[:5]
        ]

        roadmap = [
            {
                "phase": "MVP",
                "goals": [
                    "Validate core workflow",
                    "Onboard design partners",
                    "Instrument analytics",
                ],
            },
            {
                "phase": "Beta",
                "goals": [
                    "Expand integrations",
                    "Improve activation",
                    "Introduce paid tier",
                ],
            },
            {
                "phase": "GA",
                "goals": [
                    "Harden security",
                    "Expand go-to-market",
                    "Enable enterprise controls",
                ],
            },
        ]

        vision = (
            f"Enable {opportunity.target_market} to solve "
            f"{opportunity.problem_statement} through an autonomous, "
            "productized, production-ready service."
        )

        positioning = (
            f"{opportunity.name} helps {opportunity.target_market} "
            "replace manual work with an observable, governed, and "
            "continuously improving product system."
        )

        return ProductStrategy(
            product_id=product_id,
            name=opportunity.name,
            vision=vision,
            positioning=positioning,
            personas=personas,
            core_capabilities=capabilities,
            requirements=requirements,
            mvp_scope=mvp_scope,
            non_goals=[
                "Do not build unnecessary admin features before activation.",
                "Do not add enterprise procurement before core value is proven.",
                "Do not couple the product to a single cloud provider.",
            ],
            roadmap=roadmap,
            monetization_model=opportunity.business_model_hypothesis,
            created_at=utcnow().isoformat(),
        )


class BrandGenerator:
    """Generates a deterministic brand kit."""

    def generate(self, strategy: ProductStrategy) -> BrandAsset:
        digest = sha256_hex(strategy.name)

        palette = [
            f"#{digest[0:6]}",
            f"#{digest[6:12]}",
            f"#{digest[12:18]}",
        ]

        primary_capability = (
            strategy.core_capabilities[0].name
            if strategy.core_capabilities
            else "core value"
        )

        tagline = (
            f"{strategy.name}: turn {primary_capability.lower()} "
            "into measurable outcomes."
        )

        messaging = {
            "primary": strategy.positioning,
            "secondary": (
                "A production-first product system with observability, "
                "security, and continuous improvement built in."
            ),
            "proof_points": [
                "Deployable without major manual restructuring.",
                "Observable from day one.",
                "Governed launch and rollback controls.",
                "Evidence-driven product improvements.",
            ],
        }

        logo_brief = (
            f"Create a minimal, modern mark for {strategy.name}. "
            "The logo should communicate automation, clarity, and trust. "
            "Avoid overly decorative elements."
        )

        return BrandAsset(
            name=strategy.name,
            tagline=tagline,
            palette=palette,
            voice=[
                "clear",
                "practical",
                "evidence-driven",
                "trustworthy",
                "production-oriented",
            ],
            messaging=messaging,
            logo_brief=logo_brief,
        )


class UXGenerator:
    """Generates a UX specification."""

    def generate(self, strategy: ProductStrategy) -> UXSpec:
        information_architecture = [
            "Home",
            "Dashboard",
            "Core Workflow",
            "Settings",
            "Billing",
            "Analytics",
            "Support",
        ]

        flows = [
            UXFlow(
                name="Onboarding",
                trigger="First product visit",
                steps=[
                    "Landing page explains value proposition.",
                    "User signs up.",
                    "User verifies email.",
                    "User completes profile and workspace setup.",
                    "User reaches first value moment.",
                ],
                success_criteria=[
                    "User activates within first session.",
                    "Core workflow is reachable in under two minutes.",
                ],
                accessibility_requirements=[
                    "WCAG 2.1 AA",
                    "Keyboard navigation",
                    "Accessible form validation",
                ],
            ),
            UXFlow(
                name="Core Workflow",
                trigger="User initiates primary task",
                steps=[
                    "User creates primary object.",
                    "System validates input.",
                    "System processes workflow.",
                    "System displays result and next actions.",
                ],
                success_criteria=[
                    "Task completion rate is measurable.",
                    "Errors are recoverable.",
                ],
                accessibility_requirements=[
                    "WCAG 2.1 AA",
                    "Visible status indicators",
                ],
            ),
            UXFlow(
                name="Billing",
                trigger="User selects paid plan",
                steps=[
                    "User compares pricing tiers.",
                    "User selects plan.",
                    "Payment or trial is activated.",
                    "Entitlements are updated.",
                ],
                success_criteria=[
                    "Payment state is auditable.",
                    "Entitlement changes are observable.",
                ],
                accessibility_requirements=[
                    "Clear pricing disclosure",
                    "Accessible checkout errors",
                ],
            ),
        ]

        design_principles = [
            "Clarity over decoration.",
            "Evidence over opinion.",
            "Progressive disclosure.",
            "Operational visibility.",
            "Safe failure and recovery.",
        ]

        accessibility = [
            "WCAG 2.1 AA",
            "Keyboard-first navigation",
            "High-contrast support",
            "Screen-reader-friendly labels",
        ]

        return UXSpec(
            product_id=strategy.product_id,
            information_architecture=information_architecture,
            flows=flows,
            design_principles=design_principles,
            accessibility=accessibility,
            created_at=utcnow().isoformat(),
        )


class PricingEngine:
    """Generates a pricing plan."""

    def generate(
        self,
        strategy: ProductStrategy,
        research: MarketResearchReport,
    ) -> PricingPlan:
        features = [
            capability.name
            for capability in strategy.core_capabilities
        ]

        tiers: List[PricingTier] = []

        if strategy.monetization_model in {"subscription", "freemium"}:
            tiers = [
                PricingTier(
                    id="tier_free",
                    name="Free",
                    price=0.0,
                    interval="month",
                    features=features[:2],
                    limits={
                        "projects": 1,
                        "seats": 1,
                    },
                    target_segment="product-led",
                ),
                PricingTier(
                    id="tier_starter",
                    name="Starter",
                    price=29.0,
                    interval="month",
                    features=features[:4],
                    limits={
                        "projects": 5,
                        "seats": 5,
                    },
                    target_segment="smb",
                ),
                PricingTier(
                    id="tier_pro",
                    name="Pro",
                    price=99.0,
                    interval="month",
                    features=features,
                    limits={
                        "projects": 25,
                        "seats": 25,
                    },
                    target_segment="mid_market",
                ),
                PricingTier(
                    id="tier_enterprise",
                    name="Enterprise",
                    price=0.0,
                    interval="month",
                    features=features + [
                        "SSO",
                        "Audit exports",
                        "Custom retention",
                        "SLA support",
                    ],
                    limits={
                        "projects": "custom",
                        "seats": "custom",
                    },
                    target_segment="enterprise",
                ),
            ]

        elif strategy.monetization_model == "usage":
            tiers = [
                PricingTier(
                    id="tier_usage",
                    name="Pay As You Go",
                    price=0.10,
                    interval="usage_unit",
                    features=features,
                    limits={
                        "minimum_monthly_commit": 0.0,
                    },
                    target_segment="usage_based",
                ),
            ]

        elif strategy.monetization_model == "one_time":
            tiers = [
                PricingTier(
                    id="tier_license",
                    name="One-Time License",
                    price=499.0,
                    interval="one_time",
                    features=features,
                    limits={},
                    target_segment="general",
                ),
            ]

        else:
            tiers = [
                PricingTier(
                    id="tier_standard",
                    name="Standard",
                    price=49.0,
                    interval="month",
                    features=features,
                    limits={},
                    target_segment="general",
                ),
            ]

        return PricingPlan(
            product_id=strategy.product_id,
            model=strategy.monetization_model,
            tiers=tiers,
            free_trial={
                "enabled": strategy.monetization_model
                in {"subscription", "freemium"},
                "days": 14,
            },
            enterprise_options={
                "sso": True,
                "audit_exports": True,
                "custom_retention": True,
                "sla": True,
            },
            created_at=utcnow().isoformat(),
        )


class RevenueSimulator:
    """Simulates revenue scenarios."""

    def average_monthly_price(self, pricing: PricingPlan) -> float:
        monthly_prices = [
            tier.price
            for tier in pricing.tiers
            if tier.price > 0 and tier.interval == "month"
        ]

        if not monthly_prices:
            return 49.0

        return round(sum(monthly_prices) / len(monthly_prices), 2)

    def simulate(
        self,
        product_id: str,
        pricing: PricingPlan,
        assumptions: RevenueAssumptions,
    ) -> RevenueSimulation:
        base_arpu = (
            assumptions.avg_revenue_per_user
            or self.average_monthly_price(pricing)
        )

        scenarios: List[RevenueScenario] = []

        scenario_multipliers = {
            "conservative": 0.6,
            "base": 1.0,
            "optimistic": 1.4,
        }

        for scenario_name, multiplier in scenario_multipliers.items():
            scenario_assumptions = assumptions.model_copy(
                update={
                    "visitors": int(assumptions.visitors * multiplier),
                    "signup_conversion": min(
                        0.9,
                        assumptions.signup_conversion * multiplier,
                    ),
                    "activation_rate": min(
                        0.9,
                        assumptions.activation_rate * multiplier,
                    ),
                    "paid_conversion": min(
                        0.9,
                        assumptions.paid_conversion * multiplier,
                    ),
                    "avg_revenue_per_user": base_arpu,
                }
            )

            projections: List[RevenueProjection] = []

            paying_customers = 0
            cumulative_revenue = 0.0

            for month in range(1, assumptions.months + 1):
                visitors = scenario_assumptions.visitors

                signups = int(
                    visitors * scenario_assumptions.signup_conversion
                )

                activated = int(
                    signups * scenario_assumptions.activation_rate
                )

                new_paying = int(
                    activated * scenario_assumptions.paid_conversion
                )

                churned = int(
                    paying_customers * scenario_assumptions.monthly_churn
                )

                paying_customers = max(
                    0,
                    paying_customers + new_paying - churned,
                )

                mrr = round(
                    paying_customers
                    * scenario_assumptions.avg_revenue_per_user,
                    2,
                )

                arr = round(mrr * 12, 2)

                cumulative_revenue = round(
                    cumulative_revenue + mrr,
                    2,
                )

                projections.append(
                    RevenueProjection(
                        month=month,
                        visitors=visitors,
                        signups=signups,
                        activated=activated,
                        paying_customers=paying_customers,
                        churned_customers=churned,
                        mrr=mrr,
                        arr=arr,
                        cumulative_revenue=cumulative_revenue,
                    )
                )

            scenarios.append(
                RevenueScenario(
                    name=scenario_name,
                    assumptions=scenario_assumptions,
                    projections=projections,
                )
            )

        return RevenueSimulation(
            product_id=product_id,
            scenarios=scenarios,
            created_at=utcnow().isoformat(),
        )


class MarketingCompiler:
    """Compiles marketing artifacts from product strategy and brand."""

    def compile(
        self,
        strategy: ProductStrategy,
        brand: BrandAsset,
        research: MarketResearchReport,
    ) -> MarketingCampaign:
        primary_capability = (
            strategy.core_capabilities[0].name.lower()
            if strategy.core_capabilities
            else "core value"
        )

        positioning = (
            f"{brand.name} helps {', '.join(strategy.personas[:2])} "
            f"achieve measurable outcomes through {primary_capability}."
        )

        channels = [
            "SEO",
            "Content",
            "Email",
            "Product-led growth",
            "Partnerships",
        ]

        content_items = [
            "Landing page",
            "Founder-led demo",
            "Comparison guide",
            "Onboarding email sequence",
            "Case study template",
            "Launch announcement",
        ]

        launch_checklist = [
            "Analytics instrumented",
            "Pricing approved",
            "Security review passed",
            "Support macros ready",
            "Launch dashboard created",
            "Rollback plan verified",
        ]

        seo_keywords = [
            slugify(strategy.name),
            slugify(research.target_market),
            "automation",
            "SaaS",
            "production readiness",
        ]

        return MarketingCampaign(
            product_id=strategy.product_id,
            positioning=positioning,
            channels=channels,
            content_items=content_items,
            launch_checklist=launch_checklist,
            seo_keywords=seo_keywords,
            created_at=utcnow().isoformat(),
        )


class ProductISRBuilder:
    """Builds the Product ISR."""

    def build(
        self,
        strategy: ProductStrategy,
        pricing: PricingPlan,
        ux: UXSpec,
        marketing: MarketingCampaign,
    ) -> Dict[str, Any]:
        product_slug = slugify(strategy.name)

        services = []

        services.append(
            {
                "name": "CoreService",
                "responsibilities": [
                    "Primary workflow execution",
                    "Validation",
                    "Domain events",
                ],
                "apis": [
                    {
                        "name": "createPrimaryObject",
                        "method": "POST",
                        "path": "/api/v1/objects",
                    },
                    {
                        "name": "getPrimaryObject",
                        "method": "GET",
                        "path": "/api/v1/objects/{id}",
                    },
                    {
                        "name": "listPrimaryObjects",
                        "method": "GET",
                        "path": "/api/v1/objects",
                    },
                ],
            }
        )

        if any(
            capability.id in {"billing_management", "subscription_management"}
            for capability in strategy.core_capabilities
        ):
            services.append(
                {
                    "name": "BillingService",
                    "responsibilities": [
                        "Subscription lifecycle",
                        "Invoices",
                        "Entitlements",
                        "Billing events",
                    ],
                    "apis": [
                        {
                            "name": "createCheckoutSession",
                            "method": "POST",
                            "path": "/api/v1/billing/checkout",
                        },
                        {
                            "name": "getSubscription",
                            "method": "GET",
                            "path": "/api/v1/billing/subscription",
                        },
                    ],
                }
            )

        if any(
            capability.id == "analytics_reporting"
            for capability in strategy.core_capabilities
        ):
            services.append(
                {
                    "name": "AnalyticsService",
                    "responsibilities": [
                        "Event ingestion",
                        "Metrics aggregation",
                        "Dashboard queries",
                    ],
                    "apis": [
                        {
                            "name": "ingestEvent",
                            "method": "POST",
                            "path": "/api/v1/analytics/events",
                        },
                        {
                            "name": "queryMetrics",
                            "method": "GET",
                            "path": "/api/v1/analytics/metrics",
                        },
                    ],
                }
            )

        services.append(
            {
                "name": "IdentityService",
                "responsibilities": [
                    "Authentication",
                    "Authorization",
                    "Tenant isolation",
                ],
                "apis": [
                    {
                        "name": "login",
                        "method": "POST",
                        "path": "/api/v1/auth/login",
                    },
                    {
                        "name": "logout",
                        "method": "POST",
                        "path": "/api/v1/auth/logout",
                    },
                ],
            }
        )

        isr = {
            "isr_id": f"{product_slug}:isr",
            "version": "0.1.0",
            "name": strategy.name,
            "requirements": [
                requirement.model_dump(mode="json")
                for requirement in strategy.requirements
            ],
            "business_capabilities": [
                capability.model_dump(mode="json")
                for capability in strategy.core_capabilities
            ],
            "domains": [
                {
                    "name": "product_core",
                    "services": services,
                }
            ],
            "data_models": [
                {
                    "name": "User",
                    "fields": {
                        "id": "uuid",
                        "email": "string",
                        "tenant_id": "uuid",
                        "role": "string",
                        "created_at": "datetime",
                    },
                },
                {
                    "name": "Workspace",
                    "fields": {
                        "id": "uuid",
                        "name": "string",
                        "owner_id": "uuid",
                        "created_at": "datetime",
                    },
                },
                {
                    "name": "Subscription",
                    "fields": {
                        "id": "uuid",
                        "workspace_id": "uuid",
                        "plan_id": "string",
                        "status": "string",
                        "current_period_end": "datetime",
                    },
                },
                {
                    "name": "ProductEvent",
                    "fields": {
                        "id": "uuid",
                        "workspace_id": "uuid",
                        "event_type": "string",
                        "payload": "object",
                        "occurred_at": "datetime",
                    },
                },
            ],
            "security": {
                "authentication": "OIDC",
                "authorization": "RBAC",
                "encryption_in_transit": True,
                "encryption_at_rest": True,
                "audit_logging": True,
                "secrets_management": True,
            },
            "observability": {
                "structured_logging": True,
                "metrics": True,
                "distributed_tracing": True,
                "health_checks": True,
                "audit_events": True,
            },
            "testing": {
                "unit_tests": True,
                "integration_tests": True,
                "end_to_end_tests": True,
                "security_tests": True,
                "performance_tests": True,
            },
            "deployment": {
                "containerized": True,
                "environments": [
                    "development",
                    "staging",
                    "production",
                ],
                "rollback": True,
            },
            "monetization": pricing.model_dump(mode="json"),
            "ux": ux.model_dump(mode="json"),
            "marketing": marketing.model_dump(mode="json"),
        }

        return isr


class DeploymentPlanner:
    """Plans deployment and compiler targets."""

    def plan(
        self,
        isr: Dict[str, Any],
        strategy: ProductStrategy,
    ) -> DeploymentPlan:
        return DeploymentPlan(
            product_id=strategy.product_id,
            environments=[
                "development",
                "staging",
                "production",
            ],
            infrastructure_requirements=[
                "container_runtime",
                "postgres_database",
                "redis_cache",
                "object_storage",
                "secrets_manager",
                "observability_stack",
            ],
            ci_cd_steps=[
                "lint",
                "unit_tests",
                "integration_tests",
                "build_container",
                "deploy_staging",
                "smoke_tests",
                "approval_gate",
                "deploy_production",
            ],
            observability_requirements=[
                "structured_logging",
                "metrics",
                "distributed_tracing",
                "health_checks",
                "audit_events",
            ],
            rollback_plan=[
                "restore_previous_deployment",
                "disable_feature_flags",
                "verify_database_backward_compatibility",
                "notify_operators",
            ],
            compiler_targets=[
                "openapi.spec",
                "python.fastapi.foundation",
                "postgres.schema",
                "deployment.docker",
                "cicd.github_actions",
            ],
            approval_required=True,
            created_at=utcnow().isoformat(),
        )


class CustomerAnalyticsEngine:
    """Ingests customer analytics events and produces reports."""

    def __init__(self) -> None:
        self.events: Dict[str, List[CustomerEvent]] = {}

    def ingest(
        self,
        product_id: str,
        events: List[CustomerEvent],
    ) -> int:
        self.get_events(product_id).extend(events)

        return len(events)

    def get_events(self, product_id: str) -> List[CustomerEvent]:
        return self.events.setdefault(product_id, [])

    def report(self, product_id: str) -> AnalyticsReport:
        events = self.events.get(product_id, [])

        total_signups = sum(
            1 for event in events if event.event_type == "signup"
        )

        total_activations = sum(
            1 for event in events if event.event_type == "activated"
        )

        total_churns = sum(
            1 for event in events if event.event_type == "churned"
        )

        total_payments = sum(
            1 for event in events if event.event_type == "payment_succeeded"
        )

        mrr = round(
            sum(
                float(event.value or 0.0)
                for event in events
                if event.event_type == "payment_succeeded"
            ),
            2,
        )

        activation_rate = (
            total_activations / total_signups
            if total_signups > 0
            else 0.0
        )

        churn_rate = (
            total_churns / total_activations
            if total_activations > 0
            else 0.0
        )

        recommendations: List[str] = []

        if total_signups == 0:
            recommendations.append(
                "Increase top-of-funnel acquisition experiments."
            )

        if activation_rate < 0.25:
            recommendations.append(
                "Improve onboarding and first-value experience."
            )

        if churn_rate > 0.07:
            recommendations.append(
                "Investigate retention and lifecycle engagement."
            )

        if mrr > 0:
            recommendations.append(
                "Expand pricing experiments and expansion revenue paths."
            )

        return AnalyticsReport(
            product_id=product_id,
            total_signups=total_signups,
            total_activations=total_activations,
            total_churns=total_churns,
            total_payments=total_payments,
            mrr=mrr,
            activation_rate=round(activation_rate, 4),
            churn_rate=round(churn_rate, 4),
            recommendations=recommendations,
            generated_at=utcnow().isoformat(),
        )


class ProductFactoryEngine:
    """Coordinates the Autonomous Product Factory."""

    def __init__(
        self,
        policy: Optional[ProductFactoryPolicy] = None,
    ) -> None:
        self.policy = policy or ProductFactoryPolicy()

        self.opportunity_engine = OpportunityDiscoveryEngine()
        self.market_engine = MarketResearchEngine()
        self.strategy_engine = ProductStrategyGenerator()
        self.brand_engine = BrandGenerator()
        self.ux_engine = UXGenerator()
        self.pricing_engine = PricingEngine()
        self.revenue_engine = RevenueSimulator()
        self.marketing_engine = MarketingCompiler()
        self.isr_builder = ProductISRBuilder()
        self.deployment_planner = DeploymentPlanner()
        self.analytics_engine = CustomerAnalyticsEngine()

        self.reports: Dict[str, ProductFactoryReport] = {}
        self.launch_state: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Product build pipeline
    # ------------------------------------------------------------------

    def build_product(
        self,
        request: BuildProductRequest,
    ) -> ProductFactoryReport:
        created_at = utcnow().isoformat()

        product_id = deterministic_id(
            "product",
            {
                "name": request.name,
                "problem_statement": request.problem_statement,
                "created_at": created_at,
            },
        )

        opportunity_id = deterministic_id(
            "product_opportunity",
            {
                "product_id": product_id,
                "name": request.name,
            },
        )

        opportunity = ProductOpportunity(
            id=opportunity_id,
            name=request.name,
            problem_statement=request.problem_statement,
            target_market=request.target_market,
            business_model_hypothesis=request.business_model_hypothesis,
            severity_score=0.7,
            market_size_score=0.7,
            feasibility_score=0.7,
            strategic_alignment_score=0.7,
            total_score=0.7,
            status="QUALIFIED",
            evidence_refs=[f"product:{product_id}"],
            created_at=created_at,
        )

        research = self.market_engine.research(opportunity, request.context)

        strategy = self.strategy_engine.generate(
            product_id,
            opportunity,
            research,
        )

        brand = self.brand_engine.generate(strategy)

        ux = self.ux_engine.generate(strategy)

        pricing = self.pricing_engine.generate(strategy, research)

        assumptions = request.assumptions or RevenueAssumptions()

        revenue = self.revenue_engine.simulate(
            product_id,
            pricing,
            assumptions,
        )

        marketing = self.marketing_engine.compile(
            strategy,
            brand,
            research,
        )

        isr = self.isr_builder.build(
            strategy,
            pricing,
            ux,
            marketing,
        )

        deployment = self.deployment_planner.plan(isr, strategy)

        report = ProductFactoryReport(
            product_id=product_id,
            opportunity=opportunity,
            research=research,
            strategy=strategy,
            brand=brand,
            ux=ux,
            pricing=pricing,
            revenue=revenue,
            marketing=marketing,
            deployment=deployment,
            isr=isr,
            status="BUILT",
            created_at=created_at,
        )

        self.reports[product_id] = report

        return report

    def get_report(self, product_id: str) -> ProductFactoryReport:
        report = self.reports.get(product_id)

        if not report:
            raise KeyError(f"Product not found: {product_id}")

        return report

    def get_isr(self, product_id: str) -> Dict[str, Any]:
        report = self.get_report(product_id)
        return report.isr

    # ------------------------------------------------------------------
    # Launch governance
    # ------------------------------------------------------------------

    def launch_product(
        self,
        product_id: str,
        approval_refs: List[str],
    ) -> Dict[str, Any]:
        report = self.get_report(product_id)

        if self.policy.require_launch_approval and not approval_refs:
            return {
                "allowed": False,
                "product_id": product_id,
                "reason": "Product launch requires governance approval.",
            }

        self.launch_state[product_id] = {
            "launched": True,
            "launched_at": utcnow().isoformat(),
            "approval_refs": approval_refs,
        }

        report.status = "LAUNCHED"

        return {
            "allowed": True,
            "product_id": product_id,
            "reason": "Product launch authorized.",
            "approval_refs": approval_refs,
        }

    # ------------------------------------------------------------------
    # Revenue and analytics
    # ------------------------------------------------------------------

    def simulate_revenue(
        self,
        product_id: str,
        assumptions: RevenueAssumptions,
    ) -> RevenueSimulation:
        report = self.get_report(product_id)

        return self.revenue_engine.simulate(
            product_id,
            report.pricing,
            assumptions,
        )

    def ingest_analytics_events(
        self,
        product_id: str,
        events: List[CustomerEvent],
    ) -> int:
        self.get_report(product_id)

        return self.analytics_engine.ingest(product_id, events)

    def analytics_report(self, product_id: str) -> AnalyticsReport:
        self.get_report(product_id)

        return self.analytics_engine.report(product_id)
