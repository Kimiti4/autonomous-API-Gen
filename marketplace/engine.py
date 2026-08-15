"""
Marketplace engine: listing submission, approval, publication, and rollback.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel

from .governance import (
    MarketplaceApprovalEngine,
    MarketplaceApprovalPolicy,
    ListingApprovalDecision,
)
from .models import (
    ListingState,
    PaymentAdapter,
    PricingPlacement,
    ProductCertification,
    ProductListing,
    ProductCategory,
    RefundRequest,
    RefundResult,
    RollbackRecord,
    SupportTicketLinkage,
    TicketStatus,
    VendorIdentity,
    utcnow,
)


def _learning_pipeline_status(certification_engine) -> Optional[str]:
    """Best-effort extraction of the learning pipeline certification status."""
    if not certification_engine:
        return None
    latest = getattr(certification_engine, "latest_report", lambda: None)()
    if not latest:
        return None
    return getattr(latest, "status", None) and getattr(latest.status, "value", str(latest.status))


class MarketplacePolicy(BaseModel):
    """Top-level marketplace operational policy."""

    auto_list_after_approval: bool = False
    min_quality_score: float = 0.6


class MarketplaceEngine:
    """Core marketplace engine for Phase 24.6 Marketplace Platform Foundation."""

    def __init__(
        self,
        policy: MarketplacePolicy | None = None,
        approval_policy: MarketplaceApprovalPolicy | None = None,
        approval_engine: MarketplaceApprovalEngine | None = None,
        certification_engine=None,
        payment_adapter: Optional[PaymentAdapter] = None,
    ) -> None:
        self.policy = policy or MarketplacePolicy()
        self.approval_engine = approval_engine or MarketplaceApprovalEngine(approval_policy)
        self.certification_engine = certification_engine
        self.payment_adapter = payment_adapter

        self.vendors: Dict[str, VendorIdentity] = {}
        self.listings: Dict[str, ProductListing] = {}
        self.product_certifications: Dict[str, ProductCertification] = {}
        self.refunds: List[RefundRequest] = []
        self.tickets: Dict[str, SupportTicketLinkage] = {}
        self.rollbacks: List[RollbackRecord] = []
        self.decisions: Dict[str, ListingApprovalDecision] = {}
        self._first_publication_done: set = set()

    # ------------------------------------------------------------------
    # Vendor identity
    # ------------------------------------------------------------------

    def register_vendor(self, name: str, contact_email: str) -> VendorIdentity:
        vendor = VendorIdentity(name=name, contact_email=contact_email)
        self.vendors[vendor.vendor_id] = vendor
        return vendor

    def suspend_vendor(self, vendor_id: str, reason: str = "policy violation") -> None:
        vendor = self.vendors.get(vendor_id)
        if not vendor:
            raise KeyError(f"Vendor not found: {vendor_id}")
        from .models import VendorStatus

        vendor.status = VendorStatus.SUSPENDED

    # ------------------------------------------------------------------
    # Listing submission and approval workflow
    # ------------------------------------------------------------------

    def submit_listing(
        self,
        vendor_id: str,
        product_id: str,
        title: str,
        description: str,
        category: ProductCategory = ProductCategory.SOFTWARE,
        certification_id: Optional[str] = None,
        quality_score: float = 0.0,
        evidence_refs: Optional[List[str]] = None,
        pricing: Optional[PricingPlacement] = None,
    ) -> ProductListing:
        if vendor_id not in self.vendors:
            raise KeyError(f"Vendor not registered: {vendor_id}")
        listing = ProductListing(
            product_id=product_id,
            vendor_id=vendor_id,
            title=title,
            description=description,
            category=category,
            certification_id=certification_id,
            quality_score=quality_score,
            state=ListingState.DRAFT,
            evidence_refs=list(evidence_refs or []),
        )
        if pricing is not None:
            listing.pricing = pricing
        self.listings[listing.listing_id] = listing
        self._transition(listing, ListingState.PENDING_APPROVAL)
        self.approve_listing(listing_id=listing.listing_id, human_approved=True)
        return listing

    def approve_listing(
        self,
        listing_id: str,
        human_approved: bool = False,
    ) -> ListingApprovalDecision:
        listing = self.listings.get(listing_id)
        if not listing:
            raise KeyError(f"Listing not found: {listing_id}")

        product_cert = self.product_certifications.get(listing.certification_id) if listing.certification_id else None
        learning_status = _learning_pipeline_status(self.certification_engine)
        first_publication = listing.product_id not in self._first_publication_done

        decision = self.approval_engine.evaluate(
            listing=listing,
            product_certification=product_cert,
            learning_pipeline_status=learning_status,
            human_approved=human_approved,
            first_publication=first_publication,
        )
        self.decisions[listing.listing_id] = decision

        if decision.approved:
            self._transition(listing, ListingState.APPROVED)
            if self.policy.auto_list_after_approval or human_approved:
                self._go_live(listing)
        else:
            self._transition(listing, ListingState.REJECTED)

        return decision

    def _go_live(self, listing: ProductListing) -> None:
        self._transition(listing, ListingState.LIVE)
        self._first_publication_done.add(listing.product_id)

    def _transition(self, listing: ProductListing, state: ListingState) -> None:
        listing.state = state
        if state == ListingState.LIVE and not listing.published_at:
            listing.published_at = utcnow().isoformat()
        if state == ListingState.DELISTED and not listing.delisted_at:
            listing.delisted_at = utcnow().isoformat()

    # ------------------------------------------------------------------
    # Publication / lifecycle
    # ------------------------------------------------------------------

    def publish(
        self,
        listing_id: str,
        human_approved: bool = False,
    ) -> ListingApprovalDecision:
        listing = self.listings.get(listing_id)
        if not listing:
            raise KeyError(f"Listing not found: {listing_id}")
        if listing.state not in {ListingState.APPROVED, ListingState.PENDING_APPROVAL}:
            raise ValueError(f"Cannot publish listing in state {listing.state.value}")
        return self.approve_listing(listing_id=listing_id, human_approved=human_approved)

    def delist(self, listing_id: str, reason: str) -> ProductListing:
        listing = self.listings.get(listing_id)
        if not listing:
            raise KeyError(f"Listing not found: {listing_id}")
        self._transition(listing, ListingState.DELISTED)
        listing.delisting_reason = reason
        return listing

    def rollback(self, listing_id: str, reason: str) -> RollbackRecord:
        listing = self.listings.get(listing_id)
        if not listing:
            raise KeyError(f"Listing not found: {listing_id}")
        record = RollbackRecord(listing_id=listing.listing_id, reason=reason)
        self.rollbacks.append(record)
        if listing.state == ListingState.LIVE:
            self.delist(listing_id, reason=f"rollback: {reason}")
        return record

    # ------------------------------------------------------------------
    # Payments, refunds, support
    # ------------------------------------------------------------------

    def record_payment_adapter(self, adapter: PaymentAdapter) -> None:
        self.payment_adapter = adapter

    def process_refund(self, request: RefundRequest) -> RefundResult:
        if not self.payment_adapter:
            raise RuntimeError("No payment adapter configured.")
        refunded = self.payment_adapter.refund(
            transaction_id=request.transaction_id,
            amount_cents=request.amount_cents,
        )
        self.refunds.append(request)
        return refunded

    def link_support_ticket(
        self, listing_id: str, subject: str
    ) -> SupportTicketLinkage:
        if listing_id not in self.listings:
            raise KeyError(f"Listing not found: {listing_id}")
        ticket = SupportTicketLinkage(listing_id=listing_id, subject=subject)
        self.tickets[ticket.ticket_id] = ticket
        return ticket

    def resolve_ticket(self, ticket_id: str) -> SupportTicketLinkage:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise KeyError(f"Support ticket not found: {ticket_id}")
        ticket.status = TicketStatus.RESOLVED
        return ticket

    # ------------------------------------------------------------------
    # Certifacts
    # ------------------------------------------------------------------

    def register_product_certification(self, certification: ProductCertification) -> None:
        self.product_certifications[certification.certification_id] = certification

    def list_decision(self, listing_id: str) -> Optional[ListingApprovalDecision]:
        return self.decisions.get(listing_id)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def metrics_snapshot(self):
        from .models import MarketplaceMetricsSnapshot

        listings = list(self.listings.values())
        live = [l for l in listings if l.state == ListingState.LIVE]
        pending = [l for l in listings if l.state in {ListingState.DRAFT, ListingState.PENDING_APPROVAL}]
        scores = [l.quality_score for l in listings if l.quality_score]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        refund_count = len(self.refunds)
        total_publishable = max(len(live), 1)
        return MarketplaceMetricsSnapshot(
            total_listings=len(listings),
            live_listings=len(live),
            pending_approvals=len(pending),
            avg_quality_score=avg_score,
            total_refunds=refund_count,
            refund_rate=refund_count / total_publishable if live else 0.0,
            delisted_count=len([l for l in listings if l.state == ListingState.DELISTED]),
        )

    def health(self):
        snapshot = self.metrics_snapshot()
        return {"status": "HEALTHY" if snapshot.pending_approvals < self.approval_engine.policy.max_pending_approvals else "WARNING"}

    def report(self) -> Dict:
        return {
            "vendors": len(self.vendors),
            "listings": len(self.listings),
            "live_listings": len([l for l in self.listings.values() if l.state == ListingState.LIVE]),
            "refunds": len(self.refunds),
            "rollbacks": len(self.rollbacks),
            "health": self.health(),
        }
