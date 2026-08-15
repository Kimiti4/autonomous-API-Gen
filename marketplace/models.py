"""
Models for Marketplace Platform Foundation (Phase 24.6).
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from .utils import deterministic_id, utcnow


def marketplace_id(prefix: str) -> str:
    """Generate a deterministic-but-unique marketplace identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class VendorStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class ProductCategory(str, Enum):
    SOFTWARE = "SOFTWARE"
    INTEGRATION = "INTEGRATION"
    DATASET = "DATASET"
    TEMPLATE = "TEMPLATE"
    SERVICE = "SERVICE"


class ListingState(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    LIVE = "LIVE"
    DELISTED = "DELISTED"
    REJECTED = "REJECTED"


class ProductCertificationStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class VendorIdentity(BaseModel):
    vendor_id: str = Field(default_factory=lambda: marketplace_id("vendor"))
    name: str
    contact_email: str
    status: VendorStatus = VendorStatus.ACTIVE
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class PricingTier(BaseModel):
    tier_name: str
    price_cents: int
    currency: str = "USD"
    interval: str = "month"
    features: List[str] = Field(default_factory=list)


class PricingPlacement(BaseModel):
    product_id: str
    default_tier: str
    tiers: List[PricingTier] = Field(default_factory=list)
    currency: str = "USD"


class ProductCertification(BaseModel):
    certification_id: str = Field(default_factory=lambda: marketplace_id("cert"))
    product_id: str
    status: ProductCertificationStatus = ProductCertificationStatus.PENDING
    gate_results: Dict[str, bool] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    certified_at: Optional[str] = None
    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None


class ProductListing(BaseModel):
    listing_id: str = Field(default_factory=lambda: marketplace_id("listing"))
    product_id: str
    vendor_id: str
    title: str
    description: str
    category: ProductCategory = ProductCategory.SOFTWARE
    certification_id: Optional[str] = None
    pricing: Optional[PricingPlacement] = None
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    state: ListingState = ListingState.DRAFT
    evidence_refs: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())
    published_at: Optional[str] = None
    delisted_at: Optional[str] = None
    delisting_reason: Optional[str] = None


class PaymentResult(BaseModel):
    transaction_id: str
    status: str
    amount_cents: int


class RefundResult(BaseModel):
    refund_id: str
    status: str
    amount_cents: int


class PaymentAdapter(Protocol):
    """Interface adapters must implement for marketplace payments."""

    def charge(
        self, amount_cents: int, currency: str, customer_id: str
    ) -> PaymentResult:
        ...

    def refund(
        self, transaction_id: str, amount_cents: int
    ) -> RefundResult:
        ...


class RefundRequest(BaseModel):
    listing_id: str
    transaction_id: str
    amount_cents: int
    currency: str = "USD"
    reason: str = ""


class SupportTicketLinkage(BaseModel):
    ticket_id: str = Field(default_factory=lambda: marketplace_id("ticket"))
    listing_id: str
    subject: str
    status: TicketStatus = TicketStatus.OPEN
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class RollbackRecord(BaseModel):
    rollback_id: str = Field(default_factory=lambda: marketplace_id("rollback"))
    listing_id: str
    from_version: Optional[str] = None
    to_version: Optional[str] = None
    reason: str
    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class MarketplaceMetricsSnapshot(BaseModel):
    total_listings: int = 0
    live_listings: int = 0
    pending_approvals: int = 0
    avg_quality_score: float = 0.0
    total_refunds: int = 0
    refund_rate: float = 0.0
    delisted_count: int = 0
    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())
