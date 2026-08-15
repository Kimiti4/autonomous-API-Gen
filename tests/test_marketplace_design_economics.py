"""
Tests for Phase 24.8 Autonomous Marketplace Design and Economics.
"""

from datetime import timedelta

from product_factory.marketplace_autonomy.engine import MarketplaceAutonomyEngine
from product_factory.marketplace_autonomy.models import (
    ListingRankingContext,
    MarketplaceAutonomyPolicy,
    MarketplaceMetricSnapshot,
    ProposalStatus,
)
from product_factory.marketplace_autonomy.models import utcnow


def build_snapshot() -> MarketplaceMetricSnapshot:
    now = utcnow()

    return MarketplaceMetricSnapshot(
        marketplace_id="marketplace_1",
        period_start=now - timedelta(days=30),
        period_end=now,
        listing_count=100,
        published_listing_count=80,
        certified_listing_count=40,
        sales_count=1000,
        refund_count=30,
        gross_revenue=50000.0,
        net_revenue=45000.0,
        mrr_estimate=15000.0,
        conversion_rate=0.03,
        average_rating=4.2,
        support_ticket_count=50,
        fraud_alert_count=1,
        category_demand={
            "developer-tools": 0.8,
            "productivity": 0.4,
        },
        category_product_counts={
            "developer-tools": 2,
            "productivity": 20,
        },
    )


def build_listing(
    listing_id: str,
    certified: bool = True,
    fraud_score: float = 0.0,
) -> ListingRankingContext:
    return ListingRankingContext(
        listing_id=listing_id,
        product_id=f"product_{listing_id}",
        certified=certified,
        certification_score=0.9 if certified else 0.2,
        test_score=0.9,
        security_score=0.9,
        rating=4.5,
        support_health=0.9,
        novelty=0.6,
        revenue_health=0.7,
        fraud_score=fraud_score,
        refund_rate=0.02,
    )


def test_marketplace_analysis_generates_proposals():
    engine = MarketplaceAutonomyEngine(MarketplaceAutonomyPolicy())

    snapshot = build_snapshot()

    report = engine.analyze_marketplace(
        snapshot=snapshot,
        listings=[
            build_listing("listing_1"),
            build_listing("listing_2", certified=False),
        ],
    )

    assert report.fitness.objectives
    assert report.opportunities
    assert report.proposals

    proposal_types = {proposal.proposal_type.value for proposal in report.proposals}

    assert "PRODUCT_PORTFOLIO" in proposal_types


def test_ranking_excludes_uncertified_and_fraud_listings():
    engine = MarketplaceAutonomyEngine(MarketplaceAutonomyPolicy())

    listings = [
        build_listing("listing_good"),
        build_listing("listing_uncertified", certified=False),
        build_listing("listing_fraud", fraud_score=0.9),
    ]

    ranked = engine.rank_listings(listings)

    good = next(item for item in ranked if item.listing_id == "listing_good")
    uncertified = next(
        item for item in ranked if item.listing_id == "listing_uncertified"
    )
    fraud = next(item for item in ranked if item.listing_id == "listing_fraud")

    assert good.included is True
    assert uncertified.included is False
    assert fraud.included is False


def test_proposal_requires_governance():
    engine = MarketplaceAutonomyEngine(MarketplaceAutonomyPolicy())

    snapshot = build_snapshot()

    report = engine.analyze_marketplace(snapshot=snapshot)

    assert report.proposals

    proposal = report.proposals[0]

    pending = engine.submit_proposal_to_governance(proposal.id)

    assert pending.status == ProposalStatus.PENDING_GOVERNANCE

    approved = engine.submit_proposal_to_governance(
        proposal.id,
        approval_ref="governance_approval_1",
    )

    assert approved.status == ProposalStatus.APPROVED


def test_fee_change_requires_approval():
    engine = MarketplaceAutonomyEngine(MarketplaceAutonomyPolicy())

    snapshot = build_snapshot()

    change = engine.economics_engine.validate_fee_change(
        current_fee_pct=10.0,
        proposed_fee_pct=25.0,
    )

    assert change.approval_required is True
