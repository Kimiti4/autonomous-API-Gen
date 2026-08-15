"""
Plugin API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from .manifest import PluginHealth


router = APIRouter(
    prefix="/v1/knowledge/plugins",
    tags=["knowledge-plugins"],
)


@router.get("")
def list_plugins(request: Request):
    """List registered plugins."""

    registry = getattr(request.app.state, "plugin_registry", None)

    if not registry:
        return []

    return registry.list_manifests()


@router.get("/health")
def plugin_health(request: Request):
    """Report health of active Knowledge Graph plugins."""

    health: list[PluginHealth] = []

    graph_store = getattr(request.app.state, "graph_store", None)
    search_store = getattr(request.app.state, "search_store", None)

    if graph_store is None:
        health.append(
            PluginHealth(
                plugin_id="graph_store",
                status="degraded",
                message="No active graph store configured.",
            )
        )
    elif hasattr(graph_store, "health_check"):
        health.append(graph_store.health_check())
    else:
        health.append(
            PluginHealth(
                plugin_id="graph_store",
                status="degraded",
                message="Graph store does not implement health_check.",
            )
        )

    if search_store is None:
        health.append(
            PluginHealth(
                plugin_id="search_store",
                status="degraded",
                message="No active search store configured.",
            )
        )
    elif hasattr(search_store, "health_check"):
        health.append(search_store.health_check())
    else:
        health.append(
            PluginHealth(
                plugin_id="search_store",
                status="degraded",
                message="Search store does not implement health_check.",
            )
        )

    return health