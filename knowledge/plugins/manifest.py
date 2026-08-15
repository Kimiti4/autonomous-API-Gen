"""
Plugin manifest and health models.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PluginCapability(str, Enum):
    """Capabilities a plugin may provide."""

    GRAPH_STORE = "graph_store"
    SEARCH_STORE = "search_store"
    EMBEDDINGS = "embeddings"
    VISUALIZATION = "visualization"


class PluginHealth(BaseModel):
    """Health status for a plugin instance."""

    plugin_id: str
    status: Literal[
        "ok",
        "degraded",
        "error",
    ]
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class PluginManifest(BaseModel):
    """Declarative description of a plugin."""

    plugin_id: str
    name: str
    version: str

    description: str = ""

    capabilities: list[PluginCapability] = Field(default_factory=list)

    entrypoint: str = ""

    config_schema: dict[str, Any] = Field(default_factory=dict)

    requires_external_dependencies: bool = False

    governance_decision_ref: Optional[str] = None