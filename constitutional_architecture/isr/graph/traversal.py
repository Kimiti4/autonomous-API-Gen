"""
Graph Traversal Algorithms.

Provides BFS, DFS, topological sort, and cycle detection for the ISR graph.
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Optional

from constitutional_architecture.isr.graph.typed_graph import GraphEdge, GraphNode, TypedGraph
from constitutional_architecture.isr.model.edges import EdgeType


class GraphTraversal:
    """Traversal algorithms for the ISR typed graph."""

    @staticmethod
    def bfs(
        graph: TypedGraph,
        start_id: str,
        edge_filter: Optional[Callable[[GraphEdge], bool]] = None,
    ) -> list[GraphNode]:
        visited: set[str] = set()
        result: list[GraphNode] = []
        queue: deque[str] = deque([start_id])

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            node = graph.get_node(node_id)
            if node:
                result.append(node)
            for edge in graph.get_outgoing_edges(node_id):
                if edge_filter and not edge_filter(edge):
                    continue
                if edge.target_id not in visited:
                    queue.append(edge.target_id)

        return result

    @staticmethod
    def dfs(
        graph: TypedGraph,
        start_id: str,
        edge_filter: Optional[Callable[[GraphEdge], bool]] = None,
    ) -> list[GraphNode]:
        visited: set[str] = set()
        result: list[GraphNode] = []

        def _dfs(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            node = graph.get_node(node_id)
            if node:
                result.append(node)
            for edge in graph.get_outgoing_edges(node_id):
                if edge_filter and not edge_filter(edge):
                    continue
                _dfs(edge.target_id)

        _dfs(start_id)
        return result

    @staticmethod
    def topological_sort(
        graph: TypedGraph,
        edge_type: EdgeType = EdgeType.DEPENDS_ON,
    ) -> list[GraphNode]:
        nodes = {n.id: n for n in graph.nodes()}
        in_degree: dict[str, int] = {nid: 0 for nid in nodes}
        adjacency: dict[str, list[str]] = {nid: [] for nid in nodes}

        for edge in graph.edges():
            if edge.edge_type == edge_type:
                if edge.source_id in nodes and edge.target_id in nodes:
                    adjacency[edge.source_id].append(edge.target_id)
                    in_degree[edge.target_id] += 1

        queue: deque[str] = deque(
            nid for nid, deg in in_degree.items() if deg == 0
        )
        result: list[GraphNode] = []

        while queue:
            node_id = queue.popleft()
            result.append(nodes[node_id])
            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(nodes):
            raise ValueError("Cycle detected in dependency graph")

        return result

    @staticmethod
    def detect_cycles(
        graph: TypedGraph,
        edge_type: EdgeType = EdgeType.DEPENDS_ON,
    ) -> list[list[str]]:
        nodes = {n.id for n in graph.nodes()}
        adjacency: dict[str, list[str]] = {nid: [] for nid in nodes}

        for edge in graph.edges():
            if edge.edge_type == edge_type:
                if edge.source_id in nodes and edge.target_id in nodes:
                    adjacency[edge.source_id].append(edge.target_id)

        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def _dfs(node_id: str) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in adjacency.get(node_id, []):
                if neighbor not in visited:
                    _dfs(neighbor)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.discard(node_id)

        for node_id in nodes:
            if node_id not in visited:
                _dfs(node_id)

        return cycles

    @staticmethod
    def find_path(
        graph: TypedGraph,
        source_id: str,
        target_id: str,
        edge_filter: Optional[Callable[[GraphEdge], bool]] = None,
    ) -> Optional[list[str]]:
        visited: set[str] = set()
        parent: dict[str, Optional[str]] = {source_id: None}
        queue: deque[str] = deque([source_id])

        while queue:
            node_id = queue.popleft()
            if node_id == target_id:
                path: list[str] = []
                current: Optional[str] = target_id
                while current is not None:
                    path.append(current)
                    current = parent[current]
                return list(reversed(path))

            if node_id in visited:
                continue
            visited.add(node_id)

            for edge in graph.get_outgoing_edges(node_id):
                if edge_filter and not edge_filter(edge):
                    continue
                if edge.target_id not in visited:
                    parent[edge.target_id] = node_id
                    queue.append(edge.target_id)

        return None
