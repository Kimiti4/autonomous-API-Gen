"""
API routes for the Marketplace platform (Phase 24.6).
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import MarketplaceEngine, MarketplacePolicy
from .governance import MarketplaceApprovalPolicy
from .models import (
    ListingState,
    PaymentAdapter,
    PricingPlacement,
    ProductCategory,
    ProductCertification,
    ProductListing,
    RefundRequest,
    VendorIdentity,
)

router = APIRouter(
    prefix="/v1/marketplace",
    tags=["marketplace"],
)


def enable_marketplace(
    app: FastAPI,
    policy: MarketplacePolicy | None = None,
    approval_policy: MarketplaceApprovalPolicy | None = None,
    certification_engine=None,
    payment_adapter: Optional[PaymentAdapter] = None,
) -> MarketplaceEngine:
    """Mount marketplace platform endpoints on the application."""
    engine = MarketplaceEngine(
        policy=policy,
        approval_policy=approval_policy,
        certification_engine=certification_engine,
        payment_adapter=payment_adapter,
    )
    app.state.marketplace_engine = engine
    app.state.learning_certification_engine = certification_engine
    app.include_router(router)
    return engine


def _engine(request: Request) -> MarketplaceEngine:
    engine = getattr(request.app.state, "marketplace_engine", None)
    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Marketplace engine is not configured.",
        )
    return engine


class RegisterVendorRequest(BaseModel):
    name: str
    contact_email: str


class SubmitListingRequest(BaseModel):
    vendor_id: str
    product_id: str
    title: str
    description: str
    category: ProductCategory = ProductCategory.SOFTWARE
    certification_id: Optional[str] = None
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_refs: List[str] = Field(default_factory=list)
    pricing: Optional[PricingPlacement] = None


class ApproveListingRequest(BaseModel):
    human_approved: bool = False


class RefundRequestPayload(BaseModel):
    listing_id: str
    transaction_id: str
    amount_cents: int
    currency: str = "USD"
    reason: str = ""


class SupportTicketRequest(BaseModel):
    listing_id: str
    subject: str


@router.post("/vendors", response_model=VendorIdentity)
def register_vendor(payload: RegisterVendorRequest, request: Request):
    return _engine(request).register_vendor(
        name=payload.name, contact_email=payload.contact_email
    )


@router.post("/listings", response_model=ProductListing)
def submit_listing(payload: SubmitListingRequest, request: Request):
    try:
        listing = _engine(request).submit_listing(
            vendor_id=payload.vendor_id,
            product_id=payload.product_id,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            certification_id=payload.certification_id,
            quality_score=payload.quality_score,
            evidence_refs=payload.evidence_refs,
            pricing=payload.pricing,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return listing


@router.post("/listings/{listing_id}/approve")
def approve_listing(listing_id: str, payload: ApproveListingRequest, request: Request):
    try:
        return _engine(request).approve_listing(
            listing_id=listing_id, human_approved=payload.human_approved
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/listings/{listing_id}/publish")
def publish_listing(listing_id: str, payload: ApproveListingRequest, request: Request):
    try:
        return _engine(request).publish(
            listing_id=listing_id, human_approved=payload.human_approved
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/listings/{listing_id}/delist")
def delist_listing(listing_id: str, reason: str, request: Request):
    try:
        return _engine(request).delist(listing_id, reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/listings/{listing_id}/rollback")
def rollback_listing(listing_id: str, reason: str, request: Request):
    try:
        return _engine(request).rollback(listing_id, reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/refunds")
def process_refund(payload: RefundRequestPayload, request: Request):
    try:
        result = _engine(request).process_refund(
            RefundRequest(**payload.model_dump())
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@router.post("/support-tickets")
def link_support_ticket(payload: SupportTicketRequest, request: Request):
    try:
        return _engine(request).link_support_ticket(
            listing_id=payload.listing_id, subject=payload.subject
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/listings")
def list_listings(request: Request):
    return {"listings": list(_engine(request).listings.values())}


@router.get("/report")
def marketplace_report(request: Request):
    return _engine(request).report()
