"""
Tests for Phase 24 hardening bundle.
"""

from product_factory.hardening.compilation import (
    CompilationExecutor,
    DryRunCompilerGateway,
    default_compilation_targets,
)
from product_factory.hardening.governance import (
    ProductGovernanceEngine,
    ProductGovernancePolicy,
)
from product_factory.hardening.learning import CustomerLearningEngine, clamp
from product_factory.hardening.market_evidence import MarketEvidenceEngine
from product_factory.hardening.models import (
    BillingEvent,
    CustomerSignal,
    MarketEvidence,
    MarketEvidenceSource,
    PricingPolicy,
    ProductAction,
    ProductEvidenceContext,
    ProductGate,
)
from product_factory.hardening.monetization import (
    BillingPolicy,
    MonetizationOpsEngine,
)


def test_launch_requires_evidence_and_approval():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    context = ProductEvidenceContext(product_id="product_1")

    denied = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.LAUNCH,
        context=context,
    )

    assert denied.allowed is False

    context = ProductEvidenceContext(
        product_id="product_1",
        has_market_research=True,
        has_security_review=True,
        has_pricing_plan=True,
        has_deployment_plan=True,
        has_revenue_simulation=True,
        approval_refs=["approval_1"],
    )

    allowed = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.LAUNCH,
        context=context,
    )

    assert allowed.allowed is True


def test_deploy_requires_evidence_and_approval():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    context = ProductEvidenceContext(
        product_id="product_1",
        has_market_research=True,
        has_security_review=True,
        has_pricing_plan=True,
        has_deployment_plan=True,
        has_revenue_simulation=True,
        approval_refs=[],
    )

    decision = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.DEPLOY,
        context=context,
    )

    assert decision.allowed is False
    assert ProductGate.GOVERNANCE_APPROVAL.value in decision.blockers

    context.approval_refs = ["approval_1"]

    decision = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.DEPLOY,
        context=context,
    )

    assert decision.allowed is True


def test_build_action_does_not_require_approval():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    context = ProductEvidenceContext(product_id="product_1")

    decision = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.BUILD,
        context=context,
    )

    assert decision.allowed is True
    assert decision.required_approvals == []


def test_launch_blocked_by_critical_findings():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    context = ProductEvidenceContext(
        product_id="product_1",
        has_market_research=True,
        has_security_review=True,
        has_pricing_plan=True,
        has_deployment_plan=True,
        has_revenue_simulation=True,
        critical_findings=2,
        approval_refs=["approval_1"],
    )

    decision = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.LAUNCH,
        context=context,
    )

    assert decision.allowed is False
    assert ProductGate.SECURITY.value in decision.blockers


def test_price_change_requires_pricing_plan_and_approval():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    denied_context = ProductEvidenceContext(
        product_id="product_1",
        has_pricing_plan=True,
    )

    denied = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.PRICE_CHANGE,
        context=denied_context,
    )

    assert denied.allowed is False
    assert ProductGate.GOVERNANCE_APPROVAL.value in denied.blockers

    allowed_context = ProductEvidenceContext(
        product_id="product_1",
        has_pricing_plan=True,
        approval_refs=["price_approval"],
    )

    allowed = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.PRICE_CHANGE,
        context=allowed_context,
    )

    assert allowed.allowed is True


def test_price_change_blocked_without_pricing_plan():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    context = ProductEvidenceContext(
        product_id="product_1",
        has_pricing_plan=False,
        approval_refs=["price_approval"],
    )

    decision = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.PRICE_CHANGE,
        context=context,
    )

    assert decision.allowed is False
    assert ProductGate.PRICING.value in decision.blockers


def test_marketing_publish_requires_market_evidence_and_approval():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    context = ProductEvidenceContext(
        product_id="product_1",
        has_market_research=True,
        approval_refs=["marketing_approval"],
    )

    decision = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.MARKETING_PUBLISH,
        context=context,
    )

    assert decision.allowed is True

    context_no_evidence = ProductEvidenceContext(
        product_id="product_1",
        has_market_research=False,
        approval_refs=["marketing_approval"],
    )

    decision = engine.evaluate_action(
        product_id="product_1",
        action=ProductAction.MARKETING_PUBLISH,
        context=context_no_evidence,
    )

    assert decision.allowed is False
    assert ProductGate.MARKET_EVIDENCE.value in decision.blockers


def test_approval_submit_and_decide_flow():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    approval = engine.submit_approval(
        product_id="product_1",
        action=ProductAction.LAUNCH,
        requested_by="product_owner",
        evidence_refs=["evidence_a", "evidence_b"],
    )

    assert approval.id is not None
    assert approval.status.value == "PENDING"
    assert approval.action == ProductAction.LAUNCH

    decided = engine.decide_approval(
        approval_id=approval.id,
        decided_by="governance_board",
        approved=True,
        comments="All gates passed.",
    )

    assert decided.status.value == "APPROVED"
    assert decided.decided_by == "governance_board"
    assert decided.comments == "All gates passed."


def test_decide_nonexistent_approval_raises():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    try:
        engine.decide_approval(
            approval_id="nonexistent",
            decided_by="board",
            approved=True,
        )
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_decide_rejects_approval():
    engine = ProductGovernanceEngine(ProductGovernancePolicy())

    approval = engine.submit_approval(
        product_id="product_1",
        action=ProductAction.LAUNCH,
        requested_by="product_owner",
    )

    decided = engine.decide_approval(
        approval_id=approval.id,
        decided_by="governance_board",
        approved=False,
        comments="Insufficient evidence.",
    )

    assert decided.status.value == "REJECTED"


def test_market_evidence_quality():
    engine = MarketEvidenceEngine()

    engine.register_source(
        MarketEvidenceSource(
            source_id="source_1",
            source_type="customer_interview",
            reliability=0.9,
        )
    )

    engine.register_source(
        MarketEvidenceSource(
            source_id="source_2",
            source_type="competitor_scan",
            reliability=0.7,
        )
    )

    engine.ingest_evidence(
        MarketEvidence(
            product_id="product_1",
            claim="Manual reconciliation is painful.",
            source_id="source_1",
            confidence=0.8,
        )
    )

    engine.ingest_evidence(
        MarketEvidence(
            product_id="product_1",
            claim="Manual reconciliation is painful.",
            source_id="source_2",
            confidence=0.7,
        )
    )

    report = engine.report("product_1")

    assert report.evidence_count == 2
    assert report.corroboration_score > 0
    assert report.overall_quality > 0


def test_market_evidence_with_unknown_source_downgrades_confidence():
    engine = MarketEvidenceEngine()

    evidence = MarketEvidence(
        product_id="product_1",
        claim="Manual reconciliation is painful.",
        source_id="unknown_source",
        confidence=0.8,
    )

    result = engine.ingest_evidence(evidence)

    assert result.id is not None
    assert result.confidence < 0.8
    assert result.confidence == round(0.8 * 0.7, 4)


def test_market_evidence_report_no_evidence():
    engine = MarketEvidenceEngine()

    report = engine.report("nonexistent_product")

    assert report.evidence_count == 0
    assert report.average_confidence == 0.0
    assert report.corroboration_score == 0.0
    assert report.overall_quality == 0.0


def test_market_evidence_confidence_clamped_to_max():
    engine = MarketEvidenceEngine()

    engine.register_source(
        MarketEvidenceSource(
            source_id="high_reliability",
            source_type="survey",
            reliability=1.0,
        )
    )

    evidence = MarketEvidence(
        product_id="product_1",
        claim="High confidence claim.",
        source_id="high_reliability",
        confidence=1.0,
    )

    result = engine.ingest_evidence(evidence)

    assert result.confidence <= 1.0


def test_compilation_dry_run():
    executor = CompilationExecutor()

    report = executor.execute(
        product_id="product_1",
        isr={
            "isr_id": "product_1:isr",
            "version": "0.1.0",
            "name": "Test Product",
        },
    )

    assert report.success is True
    assert report.artifact_count > 0
    assert len(report.jobs) == 5


def test_default_compilation_targets_count():
    targets = default_compilation_targets()

    assert len(targets) == 5
    backend_ids = [t.backend_id for t in targets]
    assert "openapi.spec" in backend_ids
    assert "cicd.github_actions" in backend_ids


def test_compilation_required_backend_failure_blocks_success():
    failing_gateway = _FailingGateway(fail_backend="postgres.schema")

    executor = CompilationExecutor(gateway=failing_gateway)

    report = executor.execute(
        product_id="product_1",
        isr={"name": "Test Product"},
    )

    assert report.success is False
    assert "postgres.schema" in report.missing_required_backends


def test_compilation_optional_backend_failure_does_not_block():
    failing_gateway = _FailingGateway(fail_backend="cicd.github_actions")

    custom_targets = [
        _optional_target("cicd.github_actions"),
    ]

    executor = CompilationExecutor(gateway=failing_gateway)

    report = executor.execute(
        product_id="product_1",
        isr={"name": "Test Product"},
        targets=custom_targets,
    )

    assert report.success is False
    assert "cicd.github_actions" not in report.missing_required_backends


class _FailingGateway(DryRunCompilerGateway):
    def __init__(self, fail_backend: str) -> None:
        self.fail_backend = fail_backend

    def compile_isr(self, isr, backend_id, environment):
        if backend_id == self.fail_backend:
            raise RuntimeError(f"Simulated failure for {backend_id}")
        return super().compile_isr(isr, backend_id, environment)


def _optional_target(backend_id: str):
    from product_factory.hardening.models import CompilationTarget

    return CompilationTarget(backend_id=backend_id, required=False)


def test_compilation_tracks_jobs_and_artifacts():
    executor = CompilationExecutor()

    report = executor.execute(
        product_id="product_1",
        isr={"name": "Test Product"},
    )

    assert len(report.jobs) == 5
    for job in report.jobs:
        assert job.status == "SUCCEEDED"
        assert job.artifacts
        assert job.created_at


def test_customer_learning_generates_recommendations():
    engine = CustomerLearningEngine()

    engine.ingest(
        [
            CustomerSignal(product_id="product_1", event_type="signup"),
            CustomerSignal(product_id="product_1", event_type="signup"),
            CustomerSignal(product_id="product_1", event_type="signup"),
            CustomerSignal(product_id="product_1", event_type="activated"),
            CustomerSignal(product_id="product_1", event_type="churned"),
            CustomerSignal(product_id="product_1", event_type="incident"),
        ]
    )

    report = engine.product_fitness("product_1")

    assert report.objectives["activation"] < 0.5
    assert report.recommendations


def test_customer_learning_objectives_computed():
    engine = CustomerLearningEngine()

    engine.ingest(
        [
            CustomerSignal(
                product_id="product_1", event_type="signup"
            )
            for _ in range(10)
        ]
        + [
            CustomerSignal(
                product_id="product_1", event_type="activated"
            )
            for _ in range(8)
        ]
        + [
            CustomerSignal(
                product_id="product_1", event_type="payment_succeeded", value=99.0
            )
            for _ in range(5)
        ]
    )

    report = engine.product_fitness("product_1")

    assert report.objectives["activation"] == 0.8
    assert report.objectives["retention"] > 0.0
    assert report.objectives["revenue_health"] > 0.0
    assert report.constraints["sufficient_customer_data"] is True
    assert report.constraints["sufficient_payment_data"] is True


def test_customer_learning_no_signals_sufficiency_constraints():
    engine = CustomerLearningEngine()

    report = engine.product_fitness("product_1")

    assert report.constraints["sufficient_customer_data"] is False
    assert report.constraints["sufficient_payment_data"] is False
    assert len(report.recommendations) >= 1


def test_customer_learning_evolution_feedback_generates_genome_hints():
    engine = CustomerLearningEngine()

    engine.ingest(
        [
            CustomerSignal(
                product_id="product_1", event_type="signup"
            )
            for _ in range(5)
        ]
        + [
            CustomerSignal(
                product_id="product_1", event_type="activated"
            )
            for _ in range(1)
        ]
    )

    feedback = engine.evolution_feedback("product_1")

    assert feedback["product_id"] == "product_1"
    assert len(feedback["genome_hints"]) > 0
    assert len(feedback["recommendations"]) > 0

    for hint in feedback["genome_hints"]:
        assert hint["action"] == "STRENGTHEN"
        assert "chromosome_family" in hint


def test_monetization_price_change_requires_approval():
    engine = MonetizationOpsEngine()

    old_plan = {
        "model": "subscription",
        "tiers": [
            {
                "id": "tier_starter",
                "name": "Starter",
                "price": 20.0,
                "currency": "USD",
            }
        ],
    }

    new_plan = {
        "model": "subscription",
        "tiers": [
            {
                "id": "tier_starter",
                "name": "Starter",
                "price": 40.0,
                "currency": "USD",
            }
        ],
    }

    result = engine.validate_price_change(old_plan, new_plan)

    assert result["approval_required"] is True


def test_monetization_validate_pricing_plan_allowed():
    engine = MonetizationOpsEngine()

    plan = {
        "model": "subscription",
        "tiers": [
            {
                "id": "tier_starter",
                "name": "Starter",
                "price": 29.0,
                "currency": "USD",
                "features": ["core"],
            }
        ],
    }

    result = engine.validate_pricing_plan(plan)

    assert result["allowed"] is True
    assert result["issues"] == []


def test_monetization_validate_pricing_plan_rejects_bad_model():
    engine = MonetizationOpsEngine()

    plan = {
        "model": "unsupported_model",
        "tiers": [
            {
                "id": "tier_starter",
                "name": "Starter",
                "price": 29.0,
                "currency": "USD",
            }
        ],
    }

    result = engine.validate_pricing_plan(plan)

    assert result["allowed"] is False
    assert any("not allowed" in issue for issue in result["issues"])


def test_monetization_validate_pricing_plan_rejects_negative_price():
    engine = MonetizationOpsEngine()

    plan = {
        "model": "subscription",
        "tiers": [
            {
                "id": "tier_starter",
                "name": "Starter",
                "price": -10.0,
                "currency": "USD",
            }
        ],
    }

    result = engine.validate_pricing_plan(plan)

    assert result["allowed"] is False
    assert any("negative price" in issue for issue in result["issues"])


def test_monetization_validate_pricing_plan_rejects_bad_currency():
    engine = MonetizationOpsEngine()

    plan = {
        "model": "subscription",
        "tiers": [
            {
                "id": "tier_starter",
                "name": "Starter",
                "price": 29.0,
                "currency": "EUR",
            }
        ],
    }

    result = engine.validate_pricing_plan(plan)

    assert result["allowed"] is False
    assert any("currency" in issue for issue in result["issues"])


def test_monetization_revenue_ops_report_with_events():
    engine = MonetizationOpsEngine()

    engine.ingest_billing_events(
        [
            BillingEvent(
                product_id="product_1",
                tenant_id="tenant_1",
                event_type="payment_succeeded",
                amount=99.0,
            ),
            BillingEvent(
                product_id="product_1",
                tenant_id="tenant_2",
                event_type="payment_failed",
                amount=0.0,
            ),
            BillingEvent(
                product_id="product_1",
                tenant_id="tenant_3",
                event_type="subscription_cancelled",
                amount=0.0,
            ),
        ]
    )

    report = engine.revenue_ops_report("product_1")

    assert report.successful_payments == 1
    assert report.failed_payments == 1
    assert report.cancellations == 1
    assert report.recognized_revenue == 99.0
    assert "Failed payments detected." in report.alerts
    assert "Subscription cancellations detected." in report.alerts
    assert "Start dunning workflow." in report.recommendations
    assert "Trigger retention workflow." in report.recommendations


def test_monetization_revenue_ops_report_no_events():
    engine = MonetizationOpsEngine()

    report = engine.revenue_ops_report("product_1")

    assert report.successful_payments == 0
    assert report.recognized_revenue == 0.0
    assert "Validate monetization funnel." in report.recommendations


def test_monetization_custom_policy_currency():
    policy = PricingPolicy(currency="EUR")
    engine = MonetizationOpsEngine(pricing_policy=policy)

    plan = {
        "model": "subscription",
        "tiers": [
            {
                "id": "tier_1",
                "name": "Tier 1",
                "price": 49.0,
                "currency": "EUR",
            }
        ],
    }

    result = engine.validate_pricing_plan(plan)

    assert result["allowed"] is True


def test_monetization_custom_price_change_threshold():
    policy = PricingPolicy(max_price_change_pct=5.0)
    engine = MonetizationOpsEngine(pricing_policy=policy)

    old_plan = {
        "model": "subscription",
        "tiers": [
            {"id": "t1", "name": "T1", "price": 100.0, "currency": "USD"}
        ],
    }

    new_plan = {
        "model": "subscription",
        "tiers": [
            {"id": "t1", "name": "T1", "price": 106.0, "currency": "USD"}
        ],
    }

    result = engine.validate_price_change(old_plan, new_plan)

    assert result["approval_required"] is True


def test_clamp_function():
    assert clamp(1.5) == 1.0
    assert clamp(-0.5) == 0.0
    assert clamp(0.5) == 0.5
    assert clamp(0.12345) == 0.1235
