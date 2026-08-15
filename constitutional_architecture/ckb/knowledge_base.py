"""
Constitutional Knowledge Base (CKB) — Phase -1 bootstrapping.

The CKB is a versioned, queryable repository of architectural expertise.
It serves as the "Standard Library" for the compiler pipeline and the seed
for the Product Topology Resolver (Pass 3).

This initial bootstrap loads patterns from the existing InMemoryKnowledgeGraph
and makes them queryable via the CKB interface.
"""

from __future__ import annotations

from typing import Any, Optional

from constitutional_architecture.meta.genome.knowledge_graph.iknowledge_graph import (
    IKnowledgeGraph, DesignPattern, GenomeModifier, ChromosomeTarget,
    ModifierOperation, PatternCategory,
)
from constitutional_architecture.meta.genome.knowledge_graph.in_memory_graph import (
    InMemoryKnowledgeGraph,
)


class ConstitutionalKnowledgeBase:
    """Bootstrapped CKB — seeded from the Design Knowledge Graph patterns.

    In production, this would wrap Neo4j, FalkorDB, or a vector database.
    The IKnowledgeGraph interface ensures pluggability.
    """

    def __init__(self, source: Optional[IKnowledgeGraph] = None) -> None:
        self._source = source or InMemoryKnowledgeGraph()
        self._version = "v0.1.0"

    def resolve_archetype(self, context_tags: list[str]) -> list[DesignPattern]:
        """Resolve context tags to architectural patterns (Pass 3 bridge)."""
        return self._source.resolve_patterns(context_tags)

    def get_pattern(self, pattern_id: str) -> Optional[DesignPattern]:
        return self._source.get_pattern(pattern_id)

    def register_pattern(self, pattern: DesignPattern) -> None:
        self._source.register_pattern(pattern)

    def get_archetypes(self) -> list[str]:
        patterns = self._source.resolve_patterns([])
        all_tags: set[str] = set()
        for p in patterns:
            all_tags.update(p.applicability)
        return sorted(all_tags)

    @property
    def version(self) -> str:
        return self._version

    @property
    def pattern_count(self) -> int:
        return self._source.pattern_count  # type: ignore[attr-defined]
