"""
Marketplace Platform Foundation.

Phase 24.6 deliverables: vendor identity, product listings, product
certification, listing approval workflow, product categories, pricing
placement, payment adapter interface, refund workflow, support ticket
linkage, marketplace observability, and delisting / rollback.
"""

from .engine import MarketplaceEngine, MarketplacePolicy
from .governance import (
    ApprovalGate,
    ApprovalGateResult,
    ListingApprovalDecision,
    MarketplaceApprovalEngine,
    MarketplaceApprovalPolicy,
)
from .models import (
    ListingState,
    PaymentAdapter,
    PaymentResult,
    PricingPlacement,
    ProductCategory,
    ProductCertification,
    ProductCertificationStatus,
    ProductListing,
    RefundRequest,
    RefundResult,
    RollbackRecord,
    SupportTicketLinkage,
    VendorIdentity,
    VendorStatus,
)
from .api import enable_marketplace

__version__ = "0.1.0"

__all__ = [
    "ApprovalGate",
    "ApprovalGateResult",
    "enable_marketplace",
    "ListingApprovalDecision",
    "ListingState",
    "MarketplaceApprovalEngine",
    "MarketplaceApprovalPolicy",
    "MarketplaceEngine",
    "MarketplacePolicy",
    "PaymentAdapter",
    "PaymentResult",
    "PricingPlacement",
    "ProductCategory",
    "ProductCertification",
    "ProductCertificationStatus",
    "ProductListing",
    "RefundRequest",
    "RefundResult",
    "RollbackRecord",
    "SupportTicketLinkage",
    "VendorIdentity",
    "VendorStatus",
]
