"""
Knowledge Graph — Graph structure linking knowledge entities.

Allows traversal between patterns, anti-patterns, mutations, fitness
outcomes, and domain facts to support reasoning and inference.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.knowledge.knowledge_types import KnowledgeCategory


@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    category: KnowledgeCategory
    label: str
    description: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)


RELATION_COMPOSES = "composes"
RELATION_DEPENDS_ON = "depends_on"
RELATION_CONFLICTS_WITH = "conflicts_with"
RELATION_COMPLEMENTS = "complements"
RELATION_LEADS_TO = "leads_to"
RELATION_MITIGATES = "mitigates"
RELATION_CAUSES = "causes"
RELATION_REFINES = "refines"
RELATION_EVIDENCES = "evidences"
RELATION_CONTRAINS = "contra_indicates"


class KnowledgeGraph:

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: dict[str, KnowledgeEdge] = {}
        self._outgoing: dict[str, list[str]] = {}
        self._incoming: dict[str, list[str]] = {}

    def add_node(self, node: KnowledgeNode) -> str:
        self._nodes[node.node_id] = node
        self._outgoing.setdefault(node.node_id, [])
        self._incoming.setdefault(node.node_id, [])
        return node.node_id

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self._nodes.get(node_id)

    def add_edge(self, edge: KnowledgeEdge) -> str:
        self._edges[edge.edge_id] = edge
        self._outgoing.setdefault(edge.source_id, []).append(edge.edge_id)
        self._incoming.setdefault(edge.target_id, []).append(edge.edge_id)
        return edge.edge_id

    def get_outgoing_edges(self, node_id: str) -> list[KnowledgeEdge]:
        return [self._edges[eid] for eid in self._outgoing.get(node_id, []) if eid in self._edges]

    def get_incoming_edges(self, node_id: str) -> list[KnowledgeEdge]:
        return [self._edges[eid] for eid in self._incoming.get(node_id, []) if eid in self._edges]

    def get_neighbors(self, node_id: str) -> list[KnowledgeNode]:
        result: list[KnowledgeNode] = []
        for edge in self.get_outgoing_edges(node_id):
            if edge.target_id in self._nodes:
                result.append(self._nodes[edge.target_id])
        for edge in self.get_incoming_edges(node_id):
            if edge.source_id in self._nodes:
                result.append(self._nodes[edge.source_id])
        return result

    def get_nodes_by_category(self, category: KnowledgeCategory) -> list[KnowledgeNode]:
        return [n for n in self._nodes.values() if n.category == category]

    def get_nodes_by_tag(self, tag: str) -> list[KnowledgeNode]:
        return [n for n in self._nodes.values() if tag in n.tags]

    def find_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> list[list[str]]:
        paths: list[list[str]] = []
        visited: set[str] = set()

        def _dfs(current: str, path: list[str]) -> None:
            if len(path) > max_depth:
                return
            if current == target_id:
                paths.append(list(path))
                return
            if current in visited:
                return
            visited.add(current)
            for edge in self.get_outgoing_edges(current):
                _dfs(edge.target_id, path + [edge.target_id])
            visited.remove(current)

        _dfs(source_id, [source_id])
        return paths

    def query(
        self,
        category: Optional[KnowledgeCategory] = None,
        tag: Optional[str] = None,
        text_search: Optional[str] = None,
        max_results: int = 50,
    ) -> list[KnowledgeNode]:
        results = list(self._nodes.values())

        if category is not None:
            results = [n for n in results if n.category == category]

        if tag is not None:
            results = [n for n in results if tag in n.tags]

        if text_search is not None:
            search = text_search.lower()
            results = [
                n for n in results
                if search in n.label.lower() or search in n.description.lower()
            ]

        return results[:max_results]

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._outgoing.clear()
        self._incoming.clear()
