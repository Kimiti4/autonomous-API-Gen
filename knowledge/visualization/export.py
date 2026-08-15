"""
Graph export service.

This service converts a Knowledge Graph query result into a read-only
visualization export.

It enforces:
- Read-only behavior
- Entity-type filtering
- Relation-type filtering
- Sensitivity redaction
- Provenance gating
"""

from __future__ import annotations

from typing import Any, Optional

from ..auth import Actor
from ..errors import NotFound
from ..models import QueryRequest
from .models import (
    GraphExportRequest,
    GraphExportResponse,
    VisualizationEdge,
    VisualizationNode,
    build_export_metadata,
)


SENSITIVE_LEVELS = {"CONFIDENTIAL", "RESTRICTED"}
SENSITIVE_VIEWER_ROLES = {"knowledge_auditor", "knowledge_admin"}


class GraphExporter:
    """Exports graph slices for visualization."""

    def __init__(self, runtime) -> None:
        self._runtime = runtime

    def export(
        self,
        request: GraphExportRequest,
        actor: Optional[Actor] = None,
    ) -> GraphExportResponse:
        """
        Export a graph slice.

        This operation is strictly read-only.
        """

        query_request = QueryRequest(
            query_type="NEIGHBORS",
            entity_id=request.root_entity_id,
            direction=request.direction,
            relation_types=request.relation_types,
            depth=request.depth,
            include_provenance=request.include_provenance,
        )

        result = self._runtime.query(query_request)

        raw_nodes: list[dict[str, Any]] = result.get("nodes", [])
        raw_edges: list[dict[str, Any]] = result.get("edges", [])

        allowed_nodes: dict[str, VisualizationNode] = {}
        redactions_applied = 0
        unauthorized_nodes_removed = 0

        for raw_node in raw_nodes:
            node_id = raw_node.get("id")

            if not node_id:
                continue

            if not self._entity_type_allowed(raw_node, request):
                continue

            if self._is_sensitive(raw_node) and request.redact_sensitive:
                if not self._can_view_sensitive(actor):
                    unauthorized_nodes_removed += 1
                    continue

                redactions_applied += 1

            allowed_nodes[node_id] = self._to_visualization_node(
                raw_node=raw_node,
                request=request,
                actor=actor,
            )

        edges: list[VisualizationEdge] = []

        for raw_edge in raw_edges:
            source_id = raw_edge.get("source_entity_id")
            target_id = raw_edge.get("target_entity_id")

            if not source_id or not target_id:
                continue

            if source_id not in allowed_nodes or target_id not in allowed_nodes:
                continue

            edges.append(
                VisualizationEdge(
                    id=raw_edge.get("id", ""),
                    label=raw_edge.get("relation_type", "RELATED_TO"),
                    relation_type=raw_edge.get("relation_type", "RELATED_TO"),
                    source=source_id,
                    target=target_id,
                    derived=bool(raw_edge.get("derived", False)),
                    status=raw_edge.get("status", "ACTIVE"),
                )
            )

        nodes = list(allowed_nodes.values())

        metadata = build_export_metadata(
            request=request,
            nodes=nodes,
            edges=edges,
            redactions_applied=redactions_applied,
            unauthorized_nodes_removed=unauthorized_nodes_removed,
        )

        content: Optional[str] = None

        if request.format == "mermaid":
            content = self._to_mermaid(nodes, edges)
        elif request.format == "dot":
            content = self._to_dot(nodes, edges)

        return GraphExportResponse(
            metadata=metadata,
            nodes=nodes,
            edges=edges,
            content=content,
        )

    def _entity_type_allowed(
        self,
        raw_node: dict[str, Any],
        request: GraphExportRequest,
    ) -> bool:
        if not request.entity_types:
            return True

        if raw_node.get("id") == request.root_entity_id:
            return True

        return raw_node.get("entity_type", "") in request.entity_types

    def _is_sensitive(self, raw_node: dict[str, Any]) -> bool:
        classification = raw_node.get("classification") or {}
        sensitivity = classification.get("sensitivity", "INTERNAL")
        return sensitivity in SENSITIVE_LEVELS

    def _can_view_sensitive(self, actor: Optional[Actor]) -> bool:
        if not actor:
            return False

        return any(actor.has_role(role) for role in SENSITIVE_VIEWER_ROLES)

    def _to_visualization_node(
        self,
        raw_node: dict[str, Any],
        request: GraphExportRequest,
        actor: Optional[Actor],
    ) -> VisualizationNode:
        classification = raw_node.get("classification") or {}
        sensitivity = classification.get("sensitivity", "INTERNAL")

        source_refs = raw_node.get("source_refs", [])
        source_ref_count = len(source_refs)

        include_full_provenance = (
            request.include_provenance
            and (
                sensitivity not in SENSITIVE_LEVELS
                or self._can_view_sensitive(actor)
            )
        )

        description = raw_node.get("description")

        if sensitivity in SENSITIVE_LEVELS and not self._can_view_sensitive(actor):
            description = None

        return VisualizationNode(
            id=raw_node.get("id", ""),
            label=raw_node.get("name", raw_node.get("id", "unknown")),
            entity_type=raw_node.get("entity_type", "UNKNOWN"),
            namespace=raw_node.get("namespace", "unknown"),
            status=raw_node.get("status", "ACTIVE"),
            sensitivity=sensitivity,
            description=description,
            source_ref_count=source_ref_count,
            source_refs=source_refs if include_full_provenance else [],
        )

    def _escape_mermaid(self, value: str) -> str:
        return (
            value.replace('"', "'")
            .replace("|", "/")
            .replace("\n", " ")
        )

    def _escape_dot(self, value: str) -> str:
        return (
            value.replace('"', '\\"')
            .replace("\n", "\\n")
        )

    def _to_mermaid(
        self,
        nodes: list[VisualizationNode],
        edges: list[VisualizationEdge],
    ) -> str:
        lines: list[str] = ["graph TD"]
        id_map: dict[str, str] = {}

        for index, node in enumerate(nodes):
            safe_id = f"n{index}"
            id_map[node.id] = safe_id

            label = self._escape_mermaid(f"{node.label} ({node.entity_type})")
            lines.append(f'  {safe_id}["{label}"]')

        for edge in edges:
            source = id_map.get(edge.source)
            target = id_map.get(edge.target)

            if not source or not target:
                continue

            label = self._escape_mermaid(edge.label)
            lines.append(f"  {source} -->|{label}| {target}")

        return "\n".join(lines)

    def _to_dot(
        self,
        nodes: list[VisualizationNode],
        edges: list[VisualizationEdge],
    ) -> str:
        lines: list[str] = [
            "digraph KnowledgeGraph {",
            "  node [shape=box];",
        ]

        id_map: dict[str, str] = {}

        for index, node in enumerate(nodes):
            safe_id = f"n{index}"
            id_map[node.id] = safe_id

            label = self._escape_dot(f"{node.label}\n{node.entity_type}")
            lines.append(f'  {safe_id} [label="{label}"];')

        for edge in edges:
            source = id_map.get(edge.source)
            target = id_map.get(edge.target)

            if not source or not target:
                continue

            label = self._escape_dot(edge.label)
            lines.append(f'  {source} -> {target} [label="{label}"];')

        lines.append("}")

        return "\n".join(lines)
