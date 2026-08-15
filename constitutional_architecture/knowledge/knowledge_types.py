"""
Knowledge Types — Ontology of architectural knowledge.

Defines the type hierarchy for all knowledge entities stored,
queried, and inferred by the Knowledge Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Optional


@unique
class KnowledgeCategory(str, Enum):
    PATTERN = "pattern"
    ANTI_PATTERN = "anti_pattern"
    MUTATION_RECORD = "mutation_record"
    FITNESS_RECORD = "fitness_record"
    COMPATIBILITY_RECORD = "compatibility_record"
    DOMAIN_FACT = "domain_fact"
    EVOLUTION_LESSON = "evolution_lesson"
    OPERATIONAL_INSIGHT = "operational_insight"
    REQUIREMENT_INSIGHT = "requirement_insight"
    HEURISTIC = "heuristic"

    def __str__(self) -> str:
        return self.value


@unique
class ConfidenceLevel(str, Enum):
    CONFIRMED = "confirmed"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPECULATIVE = "speculative"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class KnowledgeProvenance:
    source_subsystem: str = ""
    evolution_run_id: str = ""
    generation: int = 0
    deployment_id: str = ""
    isr_hash: str = ""
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class KnowledgeBaseEntity:
    id: str
    category: KnowledgeCategory
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    provenance: KnowledgeProvenance = field(default_factory=KnowledgeProvenance)
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM


@dataclass(frozen=True)
class FitnessRecord:
    mutation_type: str
    dimensions: dict[str, float] = field(default_factory=dict)
    sample_size: int = 1
    context: str = ""
    avg_fitness_delta: dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CompatibilityRecord:
    pattern_a: str
    pattern_b: str
    compatibility_score: float = 0.5
    sample_size: int = 1
    evidence: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EvolutionLesson:
    title: str
    description: str
    context: str = ""
    recommendations: tuple[str, ...] = ()
    severity: str = "info"
    source_run_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class DomainFact:
    domain: str
    statement: str
    evidence_strength: float = 0.5
    source: str = ""
    applicability: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class HeuristicRule:
    name: str
    description: str
    condition: str = ""
    action: str = ""
    priority: int = 0
    success_count: int = 0
    failure_count: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
