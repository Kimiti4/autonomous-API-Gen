"""
Phase 4: In-Memory Knowledge Graph — default implementation.

Stores seed patterns in memory. Implements the IKnowledgeGraph interface.
In production, swap for Neo4jKnowledgeGraph or VectorGraphKnowledgeGraph.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from constitutional_architecture.meta.genome.knowledge_graph.iknowledge_graph import (
    IKnowledgeGraph, DesignPattern, GenomeModifier, PatternCategory,
    ChromosomeTarget, ModifierOperation,
)


_SEED_PATH = os.path.join(os.path.dirname(__file__), "graph_data.json")


def _load_seed_patterns() -> list[dict]:
    if os.path.exists(_SEED_PATH):
        with open(_SEED_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("patterns", [])
    return []


def _dict_to_pattern(d: dict) -> DesignPattern:
    modifiers = tuple(
        GenomeModifier(
            target_chromosome=ChromosomeTarget(m["targetChromosome"]),
            target_gene=m["targetGene"],
            operation=ModifierOperation(m["operation"]),
            value=m["value"],
        )
        for m in d.get("genomeModifiers", [])
    )
    return DesignPattern(
        id=d["id"],
        name=d["name"],
        category=PatternCategory(d["category"]),
        description=d.get("description", ""),
        applicability=tuple(d.get("applicability", [])),
        conflicts_with=tuple(d.get("conflictsWith", [])),
        genome_modifiers=modifiers,
    )


class InMemoryKnowledgeGraph(IKnowledgeGraph):
    def __init__(self, patterns: Optional[list[DesignPattern]] = None) -> None:
        self._patterns: dict[str, DesignPattern] = {}
        if patterns:
            for p in patterns:
                self._patterns[p.id] = p
            return
        raw = _load_seed_patterns()
        for r in raw:
            p = _dict_to_pattern(r)
            self._patterns[p.id] = p

    def resolve_patterns(self, context_tags: list[str]) -> list[DesignPattern]:
        if not context_tags:
            return list(self._patterns.values())
        tags_lower = [t.lower() for t in context_tags]
        matched: list[DesignPattern] = []
        for pattern in self._patterns.values():
            app_lower = [a.lower() for a in pattern.applicability]
            if any(tag in app_lower for tag in tags_lower):
                matched.append(pattern)
        return matched

    def get_pattern(self, pattern_id: str) -> Optional[DesignPattern]:
        return self._patterns.get(pattern_id)

    def register_pattern(self, pattern: DesignPattern) -> None:
        self._patterns[pattern.id] = pattern

    def get_conflicting(self, pattern_id: str) -> list[DesignPattern]:
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            return []
        return [self._patterns[pid] for pid in pattern.conflicts_with if pid in self._patterns]

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)
