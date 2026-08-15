"""
API routes for the Autonomous Product Factory.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import ProductFactoryEngine, ProductFactoryPolicy
from .models import (
    BuildProductRequest,
    CustomerEvent,
    LaunchRequest,
    RevenueAssumptions,
)


router = APIRouter(
    prefix="/v1/product-factory",
    tags=["autonomous-product-factory"],
)


def enable_product_factory(
    app: FastAPI,
    policy: ProductFactoryPolicy | None = None,
) -> ProductFactoryEngine:
    """Enable product factory endpoints."""

    engine = ProductFactoryEngine(policy=policy)

    app.state.product_factory_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> ProductFactoryEngine:
    engine = getattr(request.app.state, "product_factory_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Product factory engine is not configured.",
        )

    return engine


class DiscoverOpportunitiesRequest(BaseModel):
    ideas: List[Dict[str, Any]] = []


class IngestAnalyticsEventsRequest(BaseModel):
    events: List[CustomerEvent] = []


@router.post("/opportunities/discover")
def discover_opportunities(
    payload: DiscoverOpportunitiesRequest,
    request: Request,
):
    engine = _engine(request)

    return engine.opportunity_engine.discover(payload.model_dump())


@router.post("/build", status_code=201)
def build_product(payload: BuildProductRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.build_product(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{product_id}/report")
def get_product_report(product_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.get_report(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{product_id}/isr")
def get_product_isr(product_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.get_isr(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{product_id}/launch")
def launch_product(
    product_id: str,
    payload: LaunchRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.launch_product(product_id, payload.approval_refs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{product_id}/revenue/simulate")
def simulate_revenue(
    product_id: str,
    payload: RevenueAssumptions,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.simulate_revenue(product_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{product_id}/analytics/events", status_code=201)
def ingest_analytics_events(
    product_id: str,
    payload: IngestAnalyticsEventsRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        count = engine.ingest_analytics_events(product_id, payload.events)

        return {
            "product_id": product_id,
            "ingested_events": count,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{product_id}/analytics/report")
def analytics_report(product_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.analytics_report(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
