"""
Anti-Pattern Repository — Stores and queries anti-patterns.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

from constitutional_architecture.knowledge.knowledge_types import ConfidenceLevel
from constitutional_architecture.knowledge.knowledge_graph import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeCategory,
)


@dataclass
class AntiPatternEntry:
    name: str
    description: str
    symptoms: tuple[str, ...] = ()
    consequences: tuple[str, ...] = ()
    recommended_fixes: tuple[str, ...] = ()
    severity: str = "warning"
    tags: tuple[str, ...] = ()
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    anti_pattern_id: str = ""


class AntiPatternRepository:

    def __init__(self, graph: Optional[KnowledgeGraph] = None) -> None:
        self._graph = graph or KnowledgeGraph()
        self._anti_patterns: dict[str, AntiPatternEntry] = {}

    def register(self, entry: AntiPatternEntry) -> str:
        aid = entry.anti_pattern_id or f"ap-{uuid.uuid4().hex[:12]}"
        ap = AntiPatternEntry(
            anti_pattern_id=aid, name=entry.name,
            description=entry.description, symptoms=entry.symptoms,
            consequences=entry.consequences,
            recommended_fixes=entry.recommended_fixes,
            severity=entry.severity, tags=entry.tags,
            confidence=entry.confidence,
        )
        self._anti_patterns[aid] = ap

        self._graph.add_node(KnowledgeNode(
            node_id=aid, category=KnowledgeCategory.ANTI_PATTERN,
            label=entry.name, description=entry.description,
            attributes={
                "severity": entry.severity,
                "symptoms": list(entry.symptoms),
            },
            tags=entry.tags,
        ))
        return aid

    def get(self, anti_pattern_id: str) -> Optional[AntiPatternEntry]:
        return self._anti_patterns.get(anti_pattern_id)

    def get_by_name(self, name: str) -> Optional[AntiPatternEntry]:
        for ap in self._anti_patterns.values():
            if ap.name == name:
                return ap
        return None

    def detect(
        self,
        context_description: str,
        tags: Optional[list[str]] = None,
    ) -> list[AntiPatternEntry]:
        context = context_description.lower()
        matches: list[AntiPatternEntry] = []

        for ap in self._anti_patterns.values():
            score = 0
            # Check symptom matches
            for symptom in ap.symptoms:
                if symptom.lower() in context:
                    score += 1
            # Check description matches
            if ap.description.lower() in context:
                score += 2
            # Check tag matches
            if tags:
                if any(t in ap.tags for t in tags):
                    score += 1
            if score >= 1:
                matches.append(ap)

        matches.sort(key=lambda ap: (
            {"critical": 0, "warning": 1, "info": 2}.get(ap.severity, 3),
            -len(ap.symptoms),
        ))
        return matches

    @property
    def count(self) -> int:
        return len(self._anti_patterns)

    @property
    def all_anti_patterns(self) -> list[AntiPatternEntry]:
        return list(self._anti_patterns.values())
