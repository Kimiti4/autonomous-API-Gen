"""
Visualization API routes.

These routes expose read-only graph export and inspection endpoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from ..auth import Actor
from ..errors import NotFound
from .export import GraphExporter
from .models import GraphExportRequest, VisualizationFormat


router = APIRouter(
    prefix="/v1/knowledge/visualize",
    tags=["knowledge-visualization"],
)


def get_viewer_actor(
    x_actor_id: Optional[str] = Header(default=None, alias="X-Actor-Id"),
    x_actor_roles: Optional[str] = Header(default=None, alias="X-Actor-Roles"),
) -> Actor:
    """
    Build a viewer actor from request headers.

    Replace this with the platform identity provider and Phase 28
    authorization integration in production.
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


@router.post("/export")
def export_graph(
    payload: GraphExportRequest,
    request: Request,
    actor: Actor = Depends(get_viewer_actor),
):
    """
    Export a graph slice as JSON, Mermaid, or DOT.
    """

    runtime = request.app.state.runtime
    exporter = GraphExporter(runtime=runtime)

    try:
        return exporter.export(payload, actor=actor)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/export")
def export_graph_get(
    request: Request,
    root_entity_id: str = Query(...),
    depth: int = Query(default=2, ge=1, le=5),
    direction: Literal["backward", "forward", "both"] = Query(default="both"),
    relation_types: Optional[str] = Query(default=None),
    entity_types: Optional[str] = Query(default=None),
    include_provenance: bool = Query(default=False),
    redact_sensitive: bool = Query(default=True),
    format: VisualizationFormat = Query(default=VisualizationFormat.JSON),
    actor: Actor = Depends(get_viewer_actor),
):
    """
    GET variant of graph export for simple links and browser usage.
    """

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

    payload = GraphExportRequest(
        root_entity_id=root_entity_id,
        depth=depth,
        direction=direction,
        relation_types=relation_type_list,
        entity_types=entity_type_list,
        include_provenance=include_provenance,
        redact_sensitive=redact_sensitive,
        format=format,
    )

    return export_graph(payload, request, actor)


@router.get("/ui", response_class=HTMLResponse)
def visualization_ui(
    root_entity_id: Optional[str] = Query(default=None),
):
    """
    Minimal graph inspection UI.

    This UI is intentionally simple and replaceable.
    """

    html_path = Path(__file__).parent / "static" / "graph.html"

    if not html_path.exists():
        raise HTTPException(
            status_code=500,
            detail="Visualization UI asset missing: graph.html",
        )

    return html_path.read_text(encoding="utf-8")
