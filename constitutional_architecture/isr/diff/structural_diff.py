"""
Structural Diff.

Computes the structural difference between two ISR graphs.
Identifies added, removed, and modified nodes and edges.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constitutional_architecture.isr.graph.typed_graph import GraphEdge, GraphNode, TypedGraph


@dataclass(frozen=True)
class NodeChange:
    """A change to a single node."""

    change_type: str
    node: GraphNode
    old_node: GraphNode | None = None


@dataclass(frozen=True)
class EdgeChange:
    """A change to a single edge."""

    change_type: str
    edge: GraphEdge
    old_edge: GraphEdge | None = None


@dataclass(frozen=True)
class StructuralDiffResult:
    """Result of a structural diff between two ISR graphs."""

    node_changes: tuple[NodeChange, ...] = ()
    edge_changes: tuple[EdgeChange, ...] = ()

    @property
    def nodes_added(self) -> int:
        return sum(1 for c in self.node_changes if c.change_type == "added")

    @property
    def nodes_removed(self) -> int:
        return sum(1 for c in self.node_changes if c.change_type == "removed")

    @property
    def nodes_modified(self) -> int:
        return sum(1 for c in self.node_changes if c.change_type == "modified")

    @property
    def edges_added(self) -> int:
        return sum(1 for c in self.edge_changes if c.change_type == "added")

    @property
    def edges_removed(self) -> int:
        return sum(1 for c in self.edge_changes if c.change_type == "removed")

    @property
    def total_changes(self) -> int:
        return len(self.node_changes) + len(self.edge_changes)


class StructuralDiff:
    """Computes structural differences between two ISR graphs."""

    @staticmethod
    def compute(graph_a: TypedGraph, graph_b: TypedGraph) -> StructuralDiffResult:
        node_changes: list[NodeChange] = []
        edge_changes: list[EdgeChange] = []

        nodes_a = {n.id: n for n in graph_a.nodes()}
        nodes_b = {n.id: n for n in graph_b.nodes()}

        for node_id, node in nodes_b.items():
            if node_id not in nodes_a:
                node_changes.append(NodeChange(change_type="added", node=node))
            elif node != nodes_a[node_id]:
                node_changes.append(NodeChange(
                    change_type="modified", node=node, old_node=nodes_a[node_id]
                ))

        for node_id, node in nodes_a.items():
            if node_id not in nodes_b:
                node_changes.append(NodeChange(change_type="removed", node=node))

        edges_a = {e.id: e for e in graph_a.edges()}
        edges_b = {e.id: e for e in graph_b.edges()}

        for edge_id, edge in edges_b.items():
            if edge_id not in edges_a:
                edge_changes.append(EdgeChange(change_type="added", edge=edge))
            elif edge != edges_a[edge_id]:
                edge_changes.append(EdgeChange(
                    change_type="modified", edge=edge, old_edge=edges_a[edge_id]
                ))

        for edge_id, edge in edges_a.items():
            if edge_id not in edges_b:
                edge_changes.append(EdgeChange(change_type="removed", edge=edge))

        return StructuralDiffResult(
            node_changes=tuple(node_changes),
            edge_changes=tuple(edge_changes),
        )
