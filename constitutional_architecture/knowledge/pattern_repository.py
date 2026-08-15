"""
Pattern Repository — Stores and queries architectural patterns.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

from constitutional_architecture.knowledge.knowledge_types import (
    ConfidenceLevel,
    KnowledgeBaseEntity,
    KnowledgeCategory,
    KnowledgeProvenance,
)
from constitutional_architecture.knowledge.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeEdge,
    RELATION_COMPOSES,
    RELATION_CONFLICTS_WITH,
    RELATION_COMPLEMENTS,
)


@dataclass
class PatternEntry:
    name: str
    description: str
    category: str = "architectural"
    benefits: tuple[str, ...] = ()
    costs: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    suitable_for: tuple[str, ...] = ()
    contra_indicators: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    evidence_count: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    pattern_id: str = ""


class PatternRepository:

    def __init__(self, graph: Optional[KnowledgeGraph] = None) -> None:
        self._graph = graph or KnowledgeGraph()
        self._patterns: dict[str, PatternEntry] = {}

    def register(self, pattern: PatternEntry) -> str:
        pid = pattern.pattern_id or f"pat-{uuid.uuid4().hex[:12]}"
        entry = PatternEntry(
            pattern_id=pid, name=pattern.name,
            description=pattern.description, category=pattern.category,
            benefits=pattern.benefits, costs=pattern.costs,
            prerequisites=pattern.prerequisites,
            suitable_for=pattern.suitable_for,
            contra_indicators=pattern.contra_indicators,
            tags=pattern.tags, evidence_count=pattern.evidence_count,
            confidence=pattern.confidence,
        )
        self._patterns[pid] = entry

        self._graph.add_node(KnowledgeNode(
            node_id=pid, category=KnowledgeCategory.PATTERN,
            label=pattern.name, description=pattern.description,
            attributes={
                "category": pattern.category,
                "benefits": list(pattern.benefits),
                "costs": list(pattern.costs),
                "evidence_count": pattern.evidence_count,
            },
            tags=pattern.tags,
        ))
        return pid

    def get(self, pattern_id: str) -> Optional[PatternEntry]:
        return self._patterns.get(pattern_id)

    def get_by_name(self, name: str) -> Optional[PatternEntry]:
        for p in self._patterns.values():
            if p.name == name:
                return p
        return None

    def query(
        self,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        text: Optional[str] = None,
        min_evidence: int = 0,
        max_results: int = 50,
    ) -> list[PatternEntry]:
        results = list(self._patterns.values())
        if category:
            results = [p for p in results if p.category == category]
        if tags:
            results = [p for p in results if any(t in p.tags for t in tags)]
        if text:
            search = text.lower()
            results = [
                p for p in results
                if search in p.name.lower() or search in p.description.lower()
            ]
        if min_evidence > 0:
            results = [p for p in results if p.evidence_count >= min_evidence]
        results.sort(key=lambda p: p.evidence_count, reverse=True)
        return results[:max_results]

    def get_compatible_patterns(self, pattern_id: str) -> list[PatternEntry]:
        compatible: list[PatternEntry] = []
        for edge in self._graph.get_outgoing_edges(pattern_id):
            if edge.relation_type == RELATION_COMPLEMENTS:
                neighbor = self._graph.get_node(edge.target_id)
                if neighbor and neighbor.node_id in self._patterns:
                    compatible.append(self._patterns[neighbor.node_id])
        return compatible

    def get_conflicting_patterns(self, pattern_id: str) -> list[PatternEntry]:
        conflicts: list[PatternEntry] = []
        for edge in self._graph.get_outgoing_edges(pattern_id):
            if edge.relation_type == RELATION_CONFLICTS_WITH:
                neighbor = self._graph.get_node(edge.target_id)
                if neighbor and neighbor.node_id in self._patterns:
                    conflicts.append(self._patterns[neighbor.node_id])
        return conflicts

    def add_relation(
        self, source_id: str, target_id: str, relation: str, weight: float = 1.0
    ) -> None:
        self._graph.add_edge(KnowledgeEdge(
            edge_id=f"e-{uuid.uuid4().hex[:8]}",
            source_id=source_id, target_id=target_id,
            relation_type=relation, weight=weight,
        ))

    @property
    def count(self) -> int:
        return len(self._patterns)

    @property
    def all_patterns(self) -> list[PatternEntry]:
        return list(self._patterns.values())
