"""
Graph Operations.

Provides primitive operations for manipulating the ISR graph.
These are used by mutation operators in the Evolution Engine.
"""

from __future__ import annotations

import uuid
from typing import Optional

from constitutional_architecture.isr.graph.typed_graph import GraphEdge, GraphNode, TypedGraph
from constitutional_architecture.isr.model.edges import EdgeAttributes, EdgeType
from constitutional_architecture.isr.model.nodes import NodeType


class GraphOperations:
    """
    Primitive graph operations for ISR manipulation.

    All operations return a NEW graph (immutability guarantee).
    The original graph is never modified.
    """

    @staticmethod
    def add_node(
        graph: TypedGraph,
        node_id: str,
        node_type: NodeType,
        label: str = "",
        parent_id: Optional[str] = None,
        attributes: Optional[dict] = None,
    ) -> TypedGraph:
        new_graph = graph.clone()
        new_graph.add_node(GraphNode(
            id=node_id,
            node_type=node_type,
            label=label,
            parent_id=parent_id,
            attributes=attributes or {},
        ))
        return new_graph

    @staticmethod
    def remove_node(graph: TypedGraph, node_id: str) -> TypedGraph:
        new_graph = graph.clone()
        new_graph.remove_node(node_id)
        return new_graph

    @staticmethod
    def add_edge(
        graph: TypedGraph,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        attributes: Optional[EdgeAttributes] = None,
    ) -> TypedGraph:
        new_graph = graph.clone()
        edge_id = f"edge-{uuid.uuid4().hex[:12]}"
        new_graph.add_edge(GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            attributes=attributes or EdgeAttributes(),
        ))
        return new_graph

    @staticmethod
    def remove_edge(graph: TypedGraph, edge_id: str) -> TypedGraph:
        new_graph = graph.clone()
        new_graph.remove_edge(edge_id)
        return new_graph

    @staticmethod
    def replace_node(
        graph: TypedGraph,
        old_node_id: str,
        new_node: GraphNode,
    ) -> TypedGraph:
        new_graph = graph.clone()
        incoming = new_graph.get_incoming_edges(old_node_id)
        outgoing = new_graph.get_outgoing_edges(old_node_id)
        new_graph.remove_node(old_node_id)
        new_graph.add_node(new_node)
        for edge in incoming:
            new_graph.add_edge(GraphEdge(
                id=f"edge-{uuid.uuid4().hex[:12]}",
                source_id=edge.source_id,
                target_id=new_node.id,
                edge_type=edge.edge_type,
                attributes=edge.attributes,
            ))
        for edge in outgoing:
            new_graph.add_edge(GraphEdge(
                id=f"edge-{uuid.uuid4().hex[:12]}",
                source_id=new_node.id,
                target_id=edge.target_id,
                edge_type=edge.edge_type,
                attributes=edge.attributes,
            ))
        return new_graph

    @staticmethod
    def split_node(
        graph: TypedGraph,
        node_id: str,
        child_nodes: list[GraphNode],
        edge_mapping: dict[str, str],
    ) -> TypedGraph:
        new_graph = graph.clone()
        original = new_graph.get_node(node_id)
        if original is None:
            raise ValueError(f"Node '{node_id}' not found")
        for child in child_nodes:
            new_graph.add_node(child)
        outgoing = new_graph.get_outgoing_edges(node_id)
        for edge in outgoing:
            new_target = edge_mapping.get(edge.target_id, edge.target_id)
            new_graph.add_edge(GraphEdge(
                id=f"edge-{uuid.uuid4().hex[:12]}",
                source_id=node_id,
                target_id=new_target,
                edge_type=edge.edge_type,
                attributes=edge.attributes,
            ))
        return new_graph

    @staticmethod
    def merge_nodes(
        graph: TypedGraph,
        node_ids: list[str],
        merged_node: GraphNode,
    ) -> TypedGraph:
        new_graph = graph.clone()
        all_incoming: list[GraphEdge] = []
        all_outgoing: list[GraphEdge] = []
        for nid in node_ids:
            all_incoming.extend(new_graph.get_incoming_edges(nid))
            all_outgoing.extend(new_graph.get_outgoing_edges(nid))
        for nid in node_ids:
            new_graph.remove_node(nid)
        new_graph.add_node(merged_node)
        seen_targets: set[tuple[str, EdgeType]] = set()
        for edge in all_outgoing:
            if edge.target_id not in node_ids:
                key = (edge.target_id, edge.edge_type)
                if key not in seen_targets:
                    seen_targets.add(key)
                    new_graph.add_edge(GraphEdge(
                        id=f"edge-{uuid.uuid4().hex[:12]}",
                        source_id=merged_node.id,
                        target_id=edge.target_id,
                        edge_type=edge.edge_type,
                        attributes=edge.attributes,
                    ))
        seen_sources: set[tuple[str, EdgeType]] = set()
        for edge in all_incoming:
            if edge.source_id not in node_ids:
                key = (edge.source_id, edge.edge_type)
                if key not in seen_sources:
                    seen_sources.add(key)
                    new_graph.add_edge(GraphEdge(
                        id=f"edge-{uuid.uuid4().hex[:12]}",
                        source_id=edge.source_id,
                        target_id=merged_node.id,
                        edge_type=edge.edge_type,
                        attributes=edge.attributes,
                    ))
        return new_graph

    @staticmethod
    def retype_edge(
        graph: TypedGraph,
        edge_id: str,
        new_edge_type: EdgeType,
    ) -> TypedGraph:
        new_graph = graph.clone()
        edge = new_graph.get_edge(edge_id)
        if edge is None:
            raise ValueError(f"Edge '{edge_id}' not found")
        new_graph.remove_edge(edge_id)
        new_graph.add_edge(GraphEdge(
            id=edge_id,
            source_id=edge.source_id,
            target_id=edge.target_id,
            edge_type=new_edge_type,
            attributes=edge.attributes,
            metadata=edge.metadata,
        ))
        return new_graph
