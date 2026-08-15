"""
API routes for evolutionary observability, analytics, and promotion auditing.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request

from .analytics import CampaignAnalyticsEngine
from .observability import EvolutionObservabilityBus
from .promotion_audit import AuditedPromotionEngine, PromotionAuditTrail


router = APIRouter(
    prefix="/v1/evolution/observability",
    tags=["evolutionary-observability"],
)


def enable_evolution_observability(
    app: FastAPI,
    memory=None,
    promotion_engine=None,
    observability_bus: Optional[EvolutionObservabilityBus] = None,
    audit_trail: Optional[PromotionAuditTrail] = None,
):
    """Enable observability, analytics, and promotion auditing."""

    memory = memory or getattr(app.state, "evolutionary_memory", None)

    promotion_engine = promotion_engine or getattr(
        app.state,
        "promotion_engine",
        None,
    )

    bus = observability_bus or EvolutionObservabilityBus()

    audit_trail = audit_trail or PromotionAuditTrail()

    analytics_engine = CampaignAnalyticsEngine(
        memory=memory,
        observability_bus=bus,
    )

    if promotion_engine and not isinstance(
        promotion_engine,
        AuditedPromotionEngine,
    ):
        audited_promotion_engine = AuditedPromotionEngine(
            inner=promotion_engine,
            audit_trail=audit_trail,
        )

        app.state.promotion_engine = audited_promotion_engine
    else:
        audited_promotion_engine = promotion_engine

    app.state.evolution_observability_bus = bus
    app.state.evolution_analytics_engine = analytics_engine
    app.state.promotion_audit_trail = audit_trail
    app.state.audited_promotion_engine = audited_promotion_engine

    app.include_router(router)

    return bus


def _observability_bus(request: Request) -> EvolutionObservabilityBus:
    bus = getattr(request.app.state, "evolution_observability_bus", None)

    if not bus:
        raise HTTPException(
            status_code=500,
            detail="Evolution observability bus is not configured.",
        )

    return bus


def _analytics_engine(request: Request) -> CampaignAnalyticsEngine:
    engine = getattr(request.app.state, "evolution_analytics_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Campaign analytics engine is not configured.",
        )

    return engine


def _audit_trail(request: Request) -> PromotionAuditTrail:
    trail = getattr(request.app.state, "promotion_audit_trail", None)

    if not trail:
        raise HTTPException(
            status_code=500,
            detail="Promotion audit trail is not configured.",
        )

    return trail


@router.get("/events")
def list_events(
    request: Request,
    campaign_id: Optional[str] = Query(default=None),
    proposal_id: Optional[str] = Query(default=None),
    candidate_id: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    bus = _observability_bus(request)

    return bus.list_events(
        campaign_id=campaign_id,
        proposal_id=proposal_id,
        candidate_id=candidate_id,
        event_type=event_type,
        limit=limit,
    )


@router.get("/metrics")
def observability_metrics(request: Request):
    bus = _observability_bus(request)
    return bus.metrics()


@router.get("/verify")
def verify_observability_chain(request: Request):
    bus = _observability_bus(request)
    return bus.verify_chain()


@router.get("/analytics/campaigns/{campaign_id}/report")
def campaign_report(campaign_id: str, request: Request):
    engine = _analytics_engine(request)
    return engine.campaign_report(campaign_id)


@router.get("/analytics/campaigns/{campaign_id}/objective-trend")
def objective_trend(
    campaign_id: str,
    request: Request,
    objective: str = Query(...),
):
    engine = _analytics_engine(request)

    return engine.objective_trend(
        campaign_id=campaign_id,
        objective=objective,
    )


@router.get("/promotions/{promotion_id}/audit")
def promotion_audit(
    promotion_id: str,
    request: Request,
):
    trail = _audit_trail(request)
    return trail.list_events(promotion_id)


@router.get("/promotions/{promotion_id}/audit/verify")
def promotion_audit_verify(
    promotion_id: str,
    request: Request,
):
    trail = _audit_trail(request)
    return trail.verify(promotion_id)


@router.get("/promotions/{promotion_id}/audit/reconstruct")
def promotion_audit_reconstruct(
    promotion_id: str,
    request: Request,
):
    trail = _audit_trail(request)
    return trail.reconstruct(promotion_id)
