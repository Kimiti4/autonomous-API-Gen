"""
Recommendation analytics API routes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from ..auth import Actor
from .engine import RecommendationAnalyticsEngine
from .models import RecommendationAnalyticsRequest


router = APIRouter(
    prefix="/v1/knowledge/recommendations",
    tags=["recommendation-analytics"],
)


def get_viewer_actor(
    x_actor_id: Optional[str] = Header(default=None, alias="X-Actor-Id"),
    x_actor_roles: Optional[str] = Header(default=None, alias="X-Actor-Roles"),
) -> Actor:
    """
    Build a viewer actor from request headers.

    Replace with platform identity and Phase 28 authorization in production.
    """

    roles = [
        role.strip()
        for role in (x_actor_roles or "").split(",")
        if role.strip()
    ]

    return Actor(
        actor_id=x_actor_id or "anonymous",
        roles=roles,
    )


@router.post("/analyze")
def analyze_recommendations(
    payload: RecommendationAnalyticsRequest,
    actor: Actor = Depends(get_viewer_actor),
):
    """Analyze recommendations."""

    engine = RecommendationAnalyticsEngine()
    return engine.analyze(payload, actor=actor)


@router.post("/rank")
def rank_recommendations(
    payload: RecommendationAnalyticsRequest,
    actor: Actor = Depends(get_viewer_actor),
):
    """Rank recommendations without producing a full packet."""

    engine = RecommendationAnalyticsEngine()

    payload = payload.model_copy(
        update={
            "include_packet": False,
        }
    )

    return engine.analyze(payload, actor=actor)


@router.post("/duplicates")
def duplicate_recommendations(
    payload: RecommendationAnalyticsRequest,
    actor: Actor = Depends(get_viewer_actor),
):
    """Detect duplicate recommendations."""

    engine = RecommendationAnalyticsEngine()
    result = engine.analyze(payload, actor=actor)

    return {
        "metadata": result.metadata,
        "duplicate_clusters": result.duplicate_clusters,
    }


@router.post("/conflicts")
def conflicting_recommendations(
    payload: RecommendationAnalyticsRequest,
    actor: Actor = Depends(get_viewer_actor),
):
    """Detect conflicting recommendations."""

    engine = RecommendationAnalyticsEngine()
    result = engine.analyze(payload, actor=actor)

    return {
        "metadata": result.metadata,
        "conflicts": result.conflicts,
    }


@router.post("/packet")
def recommendation_packet(
    payload: RecommendationAnalyticsRequest,
    actor: Actor = Depends(get_viewer_actor),
):
    """Prepare a governance-ready recommendation packet."""

    engine = RecommendationAnalyticsEngine()

    payload = payload.model_copy(
        update={
            "include_packet": True,
        }
    )

    result = engine.analyze(payload, actor=actor)

    if not result.packet:
        raise HTTPException(
            status_code=500,
            detail="Recommendation packet generation failed.",
        )

    return result.packet
