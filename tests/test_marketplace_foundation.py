"""
Tests for Phase 24.6 — Marketplace Platform Foundation.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from learning.certification import LearningPipelineCertificationEngine
from learning.models import LearningInsight
from learning.observability.models import (
    LearningMetricsSnapshot,
    OperationalHealth,
    OperationalStatus,
)
from marketplace import (
    ListingState,
    MarketplaceApprovalPolicy,
    MarketplaceEngine,
    MarketplacePolicy,
    PaymentResult,
    ProductCertification,
    ProductCertificationStatus,
    RefundRequest,
    enable_marketplace,
)
from marketplace.governance import ApprovalGate
from marketplace.models import PricingPlacement, ProductListing


class FakeObservability:
    def metrics_snapshot(self):
        return LearningMetricsSnapshot(
            signal_count=5,
            recent_signal_count=3,
            anomaly_count=0,
            pending_approval_count=0,
        )

    def operational_health(self):
        return OperationalHealth(status=OperationalStatus.HEALTHY)


class FakeAnalytics:
    insights = {
        "i1": LearningInsight(
            id="i1", title="t", description="d", confidence=0.85
        )
    }


class FakeGovernance:
    class _KS:
        enabled = False

    kill_switch = _KS()
    safety_blocker_count = 0


EVIDENCE = ["security:scan", "prod:runbook"]


def _pricing(product_id: str) -> PricingPlacement:
    return PricingPlacement(
        product_id=product_id, default_tier="basic", tiers=[], currency="USD"
    )


def _certified_learning_engine() -> LearningPipelineCertificationEngine:
    engine = LearningPipelineCertificationEngine(
        analytics_engine=FakeAnalytics(),
        governance_engine=FakeGovernance(),
        observability_engine=FakeObservability(),
    )
    report = engine.certify(
        certified_by="human",
        evidence_refs=["security:scan", "prod:runbook"],
    )
    assert report.status.value == "CERTIFIED"
    return engine


class _FakePaymentAdapter:
    def charge(self, amount_cents, currency, customer_id):
        return PaymentResult(
            transaction_id="tx_1", status="CHARGED", amount_cents=amount_cents
        )

    def refund(self, transaction_id, amount_cents):
        return PaymentResult(
            transaction_id="tx_1", status="REFUNDED", amount_cents=amount_cents
        )


def _engine(require_human=True, certified=True):
    engine = MarketplaceEngine(
        approval_policy=MarketplaceApprovalPolicy(
            require_product_certification=True,
            require_learning_pipeline_certified=certified,
            require_human_approval_first_publication=require_human,
            min_quality_score=0.6,
        ),
        certification_engine=_certified_learning_engine() if certified else None,
        payment_adapter=_FakePaymentAdapter(),
    )
    vendor = engine.register_vendor(name="Acme", contact_email="ops@example.com")
    cert = ProductCertification(
        product_id="prod_1", status=ProductCertificationStatus.PASSED
    )
    engine.register_product_certification(cert)
    return engine, vendor.vendor_id, cert.certification_id


def _healthy_engine(require_human=False):
    return _engine(require_human=require_human, certified=True)


def test_register_vendor_and_submit_listing_without_certification_is_rejected():
    engine = MarketplaceEngine(
        approval_policy=MarketplaceApprovalPolicy(
            require_human_approval_first_publication=False,
            min_quality_score=0.0,
        ),
        certification_engine=_certified_learning_engine(),
    )
    vendor = engine.register_vendor(name="Acme", contact_email="ops@example.com")
    listing = engine.submit_listing(
        vendor_id=vendor.vendor_id,
        product_id="p1",
        title="Widget",
        description="d",
        certification_id=None,
        quality_score=0.9,
    )
    assert listing.state == ListingState.REJECTED
    decision = engine.list_decision(listing.listing_id)
    assert decision is not None and not decision.approved


def test_approve_without_product_cert_record_fails_certification_gate():
    engine = MarketplaceEngine(
        approval_policy=MarketplaceApprovalPolicy(
            require_human_approval_first_publication=False,
            min_quality_score=0.6,
        ),
        certification_engine=_certified_learning_engine(),
    )
    vendor = engine.register_vendor(name="Acme", contact_email="ops@example.com")
    listing = engine.submit_listing(
        vendor_id=vendor.vendor_id,
        product_id="p1",
        title="Widget",
        description="d",
        certification_id="cert-missing",
        quality_score=0.9,
    )
    decision = engine.list_decision(listing.listing_id)
    cert_gate = next(
        g for g in decision.gates if g.gate == ApprovalGate.PRODUCT_CERTIFICATION
    )
    assert not cert_gate.passed
    assert listing.state == ListingState.REJECTED


def test_approve_with_valid_certification_and_human_approval_goes_live():
    engine, vendor_id, cert_id = _engine(require_human=True, certified=True)
    listing = engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p-live",
        title="Widget",
        description="d",
        certification_id=cert_id,
        quality_score=0.95,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p-live"),
    )
    assert listing.state == ListingState.LIVE, listing.state
    assert listing.published_at is not None
    decision = engine.list_decision(listing.listing_id)
    assert decision.approved


def test_first_publication_requires_human_approval():
    engine, vendor_id, cert_id = _engine(require_human=True, certified=True)
    # Stage a listing manually (bypassing submit_listing auto-publish) so the
    # first-publication human gate can be exercised directly.
    listing = ProductListing(
        product_id="p-brandnew",
        vendor_id=vendor_id,
        title="Widget",
        description="d",
        certification_id=cert_id,
        quality_score=0.9,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p-brandnew"),
    )
    engine.listings[listing.listing_id] = listing
    engine._transition(listing, ListingState.PENDING_APPROVAL)

    # First publication without human approval -> human gate fails -> rejected.
    decision = engine.approve_listing(
        listing_id=listing.listing_id, human_approved=False
    )
    human_gate = next(
        g
        for g in decision.gates
        if g.gate == ApprovalGate.HUMAN_APPROVAL_FIRST_PUBLICATION
    )
    assert not human_gate.passed
    assert listing.state == ListingState.REJECTED

    # With human approval -> approved and goes live.
    decision2 = engine.approve_listing(
        listing_id=listing.listing_id, human_approved=True
    )
    human_gate2 = next(
        g
        for g in decision2.gates
        if g.gate == ApprovalGate.HUMAN_APPROVAL_FIRST_PUBLICATION
    )
    assert human_gate2.passed
    assert decision2.approved
    assert listing.state == ListingState.LIVE


def test_learning_pipeline_not_certified_blocks_approval():
    engine = MarketplaceEngine(
        approval_policy=MarketplaceApprovalPolicy(
            require_learning_pipeline_certified=True,
            require_human_approval_first_publication=False,
            min_quality_score=0.6,
        ),
        certification_engine=None,
    )
    vendor = engine.register_vendor(name="Acme", contact_email="ops@example.com")
    cert = ProductCertification(product_id="p1", status=ProductCertificationStatus.PASSED)
    engine.register_product_certification(cert)
    listing = engine.submit_listing(
        vendor_id=vendor.vendor_id,
        product_id="p1",
        title="Widget",
        description="d",
        certification_id=cert.certification_id,
        quality_score=0.9,
        evidence_refs=["security:scan", "prod:runbook"],
    )
    decision = engine.list_decision(listing.listing_id)
    lp_gate = next(
        g
        for g in decision.gates
        if g.gate == ApprovalGate.LEARNING_PIPELINE_CERTIFICATION
    )
    assert not lp_gate.passed
    assert listing.state == ListingState.REJECTED


def test_quality_score_gate_blocks_low_quality_listing():
    engine, vendor_id, cert_id = _engine(require_human=False, certified=True)
    listing = engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p-low",
        title="Widget",
        description="d",
        certification_id=cert_id,
        quality_score=0.1,
        evidence_refs=["security:scan", "prod:runbook"],
    )
    decision = engine.list_decision(listing.listing_id)
    quality_gate = next(g for g in decision.gates if g.gate == ApprovalGate.QUALITY_SCORE)
    assert not quality_gate.passed


def test_delist_changes_state():
    engine, vendor_id, cert_id = _healthy_engine()
    listing = engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p-delist",
        title="Widget",
        description="d",
        certification_id=cert_id,
        quality_score=0.9,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p-delist"),
    )
    delisted = engine.delist(listing.listing_id, reason="end of life")
    assert delisted.state == ListingState.DELISTED
    assert delisted.delisting_reason == "end of life"


def test_rollback_delists_and_records():
    engine, vendor_id, cert_id = _healthy_engine()
    listing = engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p-rb",
        title="Widget",
        description="d",
        certification_id=cert_id,
        quality_score=0.9,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p-rb"),
    )
    record = engine.rollback(listing.listing_id, reason="quality regression")
    assert record.rollback_id.startswith("rollback_")
    assert listing.state == ListingState.DELISTED


def test_refund_uses_payment_adapter():
    engine, vendor_id, cert_id = _healthy_engine()
    listing = engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p-rf",
        title="Widget",
        description="d",
        certification_id=cert_id,
        quality_score=0.9,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p-rf"),
    )
    result = engine.process_refund(
        RefundRequest(
            listing_id=listing.listing_id,
            transaction_id="tx_1",
            amount_cents=1999,
        )
    )
    assert result.status == "REFUNDED"
    assert engine.refunds[-1].amount_cents == 1999


def test_link_and_resolve_support_ticket():
    engine, vendor_id, cert_id = _healthy_engine()
    listing = engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p-tk",
        title="Widget",
        description="d",
        certification_id=cert_id,
        quality_score=0.9,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p-tk"),
    )
    ticket = engine.link_support_ticket(listing.listing_id, subject="billing question")
    resolved = engine.resolve_ticket(ticket.ticket_id)
    assert resolved.status.value == "RESOLVED"


def test_metrics_snapshot_and_report():
    engine, vendor_id, cert_id = _healthy_engine()
    engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p1",
        title="W1",
        description="d",
        certification_id=cert_id,
        quality_score=0.9,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p1"),
    )
    engine.submit_listing(
        vendor_id=vendor_id,
        product_id="p2",
        title="W2",
        description="d",
        certification_id=cert_id,
        quality_score=0.8,
        evidence_refs=EVIDENCE,
        pricing=_pricing("p2"),
    )
    snapshot = engine.metrics_snapshot()
    assert snapshot.total_listings == 2
    assert snapshot.live_listings == 2
    report = engine.report()
    assert report["live_listings"] == 2
    assert report["health"]["status"] == "HEALTHY"


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


def _app():
    app = FastAPI()
    enable_marketplace(
        app,
        certification_engine=_certified_learning_engine(),
        payment_adapter=_FakePaymentAdapter(),
    )
    return app


def test_api_register_vendor_submit_listing_and_report():
    client = TestClient(_app())

    resp = client.post(
        "/v1/marketplace/vendors",
        json={"name": "Acme", "contact_email": "ops@example.com"},
    )
    assert resp.status_code == 200
    vendor_id = resp.json()["vendor_id"]

    resp = client.post(
        "/v1/marketplace/listings",
        json={
            "vendor_id": vendor_id,
            "product_id": "p-api",
            "title": "Widget",
            "description": "d",
            "quality_score": 0.9,
            "evidence_refs": ["security:scan", "prod:runbook"],
            "certification_id": "missing-cert",
        },
    )
    assert resp.status_code == 200
    listing = resp.json()
    assert listing["state"] == "REJECTED"

    report = client.get("/v1/marketplace/report")
    assert report.status_code == 200
    assert report.json()["listings"] >= 1

    refunds = client.post(
        "/v1/marketplace/refunds",
        json={
            "listing_id": listing["listing_id"],
            "transaction_id": "tx_1",
            "amount_cents": 100,
        },
    )
    assert refunds.status_code == 200
    assert refunds.json()["status"] == "REFUNDED"
