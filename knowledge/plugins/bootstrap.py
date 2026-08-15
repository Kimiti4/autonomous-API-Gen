"""
Plugin bootstrap helpers.

These helpers wire the plugin registry into a FastAPI application and
instantiate default reference plugins.
"""

from __future__ import annotations

from fastapi import FastAPI

from ..adapters.sqlite_plugin import (
    SQLITE_GRAPH_MANIFEST,
    SQLITE_SEARCH_MANIFEST,
    sqlite_graph_factory,
    sqlite_search_factory,
)
from .registry import PluginRegistry
from .routes import router as plugin_router


def create_default_registry() -> PluginRegistry:
    """Create the default plugin registry."""

    registry = PluginRegistry()

    registry.register(
        SQLITE_GRAPH_MANIFEST,
        sqlite_graph_factory,
    )

    registry.register(
        SQLITE_SEARCH_MANIFEST,
        sqlite_search_factory,
    )

    return registry


def bootstrap_default_plugins(
    app: FastAPI,
    database_path: str,
) -> tuple[object, object]:
    """
    Bootstrap default plugins into a FastAPI app.

    Returns the active graph store and search store.
    """

    registry = create_default_registry()

    graph_store = registry.create_graph_store(
        "sqlite.graph",
        {
            "database_path": database_path,
        },
    )

    search_store = registry.create_search_store(
        "sqlite.search",
        {
            "database_path": database_path,
        },
    )

    app.state.plugin_registry = registry
    app.state.graph_store = graph_store
    app.state.search_store = search_store

    app.include_router(plugin_router)

    return graph_store, search_store