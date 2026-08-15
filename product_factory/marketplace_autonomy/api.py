"""
API routes for autonomous marketplace design and economics.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import MarketplaceAutonomyEngine
from .models import (
    ListingRankingContext,
    MarketplaceAutonomyPolicy,
    MarketplaceMetricSnapshot,
)


router = APIRouter(
    prefix="/v1/product-factory/marketplace-autonomy",
    tags=["marketplace-autonomy"],
)


class AnalyzeMarketplaceRequest(BaseModel):
    snapshot: MarketplaceMetricSnapshot
    listings: List[ListingRankingContext] = []


class SubmitProposalRequest(BaseModel):
    approval_ref: str | None = None


def enable_marketplace_autonomy(
    app: FastAPI,
    policy: MarketplaceAutonomyPolicy | None = None,
) -> MarketplaceAutonomyEngine:
    """Enable marketplace autonomy endpoints."""

    engine = MarketplaceAutonomyEngine(policy=policy)

    app.state.marketplace_autonomy_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> MarketplaceAutonomyEngine:
    engine = getattr(request.app.state, "marketplace_autonomy_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Marketplace autonomy engine is not configured.",
        )

    return engine


@router.post("/analyze")
def analyze_marketplace(payload: AnalyzeMarketplaceRequest, request: Request):
    engine = _engine(request)

    return engine.analyze_marketplace(
        snapshot=payload.snapshot,
        listings=payload.listings,
    )


@router.post("/proposals/{proposal_id}/submit")
def submit_proposal(
    proposal_id: str,
    payload: SubmitProposalRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.submit_proposal_to_governance(
            proposal_id=proposal_id,
            approval_ref=payload.approval_ref,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/rankings")
def rank_listings(
    payload: List[ListingRankingContext],
    request: Request,
):
    engine = _engine(request)

    return engine.rank_listings(payload)
