"""
Traceability API routes.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from ..auth import Actor
from ..errors import NotFound
from .engine import TraceabilityEngine
from .models import ImpactRequest, PathExplanationRequest


router = APIRouter(
    prefix="/v1/knowledge/trace",
    tags=["knowledge-traceability"],
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


def build_engine(request: Request) -> TraceabilityEngine:
    runtime = request.app.state.runtime
    return TraceabilityEngine(runtime=runtime)


@router.post("/impact")
def impact_post(
    payload: ImpactRequest,
    request: Request,
    actor: Actor = Depends(get_viewer_actor),
):
    """Compute impact entries."""

    engine = build_engine(request)

    try:
        return engine.impact(payload, actor=actor)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/impact")
def impact_get(
    request: Request,
    entity_id: str = Query(...),
    mode: Literal["forward", "backward"] = Query(default="forward"),
    depth: int = Query(default=3, ge=1, le=6),
    min_score: float = Query(default=0.05, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=1000),
    relation_types: Optional[str] = Query(default=None),
    entity_types: Optional[str] = Query(default=None),
    include_explanations: bool = Query(default=True),
    redact_sensitive: bool = Query(default=True),
    actor: Actor = Depends(get_viewer_actor),
):
    """GET variant for impact analysis."""

    relation_type_list = [
        item.strip()
        for item in (relation_types or "").split(",")
        if item.strip()
    ]

    entity_type_list = [
        item.strip()
        for item in (entity_types or "").split(",")
        if item.strip()
    ]

    payload = ImpactRequest(
        entity_id=entity_id,
        mode=mode,
        depth=depth,
        min_score=min_score,
        limit=limit,
        relation_types=relation_type_list,
        entity_types=entity_type_list,
        include_explanations=include_explanations,
        redact_sensitive=redact_sensitive,
    )

    return impact_post(payload, request, actor)


@router.get("/{entity_id}/impact")
def entity_impact_get(
    entity_id: str,
    request: Request,
    mode: Literal["forward", "backward"] = Query(default="forward"),
    depth: int = Query(default=3, ge=1, le=6),
    min_score: float = Query(default=0.05, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=1000),
    relation_types: Optional[str] = Query(default=None),
    entity_types: Optional[str] = Query(default=None),
    include_explanations: bool = Query(default=True),
    redact_sensitive: bool = Query(default=True),
    actor: Actor = Depends(get_viewer_actor),
):
    """Convenience route for entity impact."""

    return impact_get(
        request=request,
        entity_id=entity_id,
        mode=mode,
        depth=depth,
        min_score=min_score,
        limit=limit,
        relation_types=relation_types,
        entity_types=entity_types,
        include_explanations=include_explanations,
        redact_sensitive=redact_sensitive,
        actor=actor,
    )


@router.post("/explain")
def explain_post(
    payload: PathExplanationRequest,
    request: Request,
    actor: Actor = Depends(get_viewer_actor),
):
    """Explain paths between two entities."""

    engine = build_engine(request)

    try:
        return engine.explain_path(payload, actor=actor)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/explain")
def explain_get(
    request: Request,
    source_entity_id: str = Query(...),
    target_entity_id: str = Query(...),
    depth: int = Query(default=5, ge=1, le=8),
    max_paths: int = Query(default=3, ge=1, le=10),
    relation_types: Optional[str] = Query(default=None),
    include_provenance: bool = Query(default=False),
    redact_sensitive: bool = Query(default=True),
    actor: Actor = Depends(get_viewer_actor),
):
    """GET variant for path explanation."""

    relation_type_list = [
        item.strip()
        for item in (relation_types or "").split(",")
        if item.strip()
    ]

    payload = PathExplanationRequest(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        depth=depth,
        max_paths=max_paths,
        relation_types=relation_type_list,
        include_provenance=include_provenance,
        redact_sensitive=redact_sensitive,
    )

    return explain_post(payload, request, actor)
