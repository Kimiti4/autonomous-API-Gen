"""
Visualization and graph export models.

These models define the contract for exporting graph slices from the
Knowledge Graph in a read-only, governed, and replaceable way.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ..ids import deterministic_id
from ..models import utcnow


class VisualizationFormat(str, Enum):
    """Supported visualization export formats."""

    JSON = "json"
    MERMAID = "mermaid"
    DOT = "dot"


class GraphExportRequest(BaseModel):
    """Request to export a graph slice."""

    root_entity_id: str
    depth: int = Field(default=2, ge=1, le=5)
    direction: Literal["backward", "forward", "both"] = "both"

    relation_types: list[str] = Field(default_factory=list)
    entity_types: list[str] = Field(default_factory=list)

    include_provenance: bool = False
    redact_sensitive: bool = True

    format: VisualizationFormat = VisualizationFormat.JSON


class VisualizationNode(BaseModel):
    """A node in an exported graph slice."""

    id: str
    label: str
    entity_type: str
    namespace: str
    status: str
    sensitivity: str
    description: Optional[str] = None
    source_ref_count: int = 0
    source_refs: list[dict[str, Any]] = Field(default_factory=list)


class VisualizationEdge(BaseModel):
    """An edge in an exported graph slice."""

    id: str
    label: str
    relation_type: str
    source: str
    target: str
    derived: bool = False
    status: str = "ACTIVE"


class GraphExportMetadata(BaseModel):
    """Metadata describing a graph export."""

    export_id: str
    root_entity_id: str
    depth: int
    direction: str
    format: VisualizationFormat
    node_count: int
    edge_count: int
    redactions_applied: int
    unauthorized_nodes_removed: int
    generated_at: str


class GraphExportResponse(BaseModel):
    """Response containing an exported graph slice."""

    metadata: GraphExportMetadata
    nodes: list[VisualizationNode]
    edges: list[VisualizationEdge]
    content: Optional[str] = None


def build_export_id(request: GraphExportRequest) -> str:
    """Build a deterministic export ID for auditability."""
    return deterministic_id(
        "graph_export",
        request.model_dump(mode="json"),
    )


def build_export_metadata(
    request: GraphExportRequest,
    nodes: list[VisualizationNode],
    edges: list[VisualizationEdge],
    redactions_applied: int,
    unauthorized_nodes_removed: int,
) -> GraphExportMetadata:
    """Build export metadata."""
    return GraphExportMetadata(
        export_id=build_export_id(request),
        root_entity_id=request.root_entity_id,
        depth=request.depth,
        direction=request.direction,
        format=request.format,
        node_count=len(nodes),
        edge_count=len(edges),
        redactions_applied=redactions_applied,
        unauthorized_nodes_removed=unauthorized_nodes_removed,
        generated_at=utcnow().isoformat(),
    )
