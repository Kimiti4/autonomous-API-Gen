"""
Architecture Knowledge Base — Accumulated architectural wisdom.

The platform accumulates knowledge from evolution runs and operational
feedback. This makes mutations increasingly informed rather than purely
stochastic. The knowledge base stores patterns, anti-patterns, evidence
records, mutation histories, and compatibility data.

Per the Constitution:
- Evolution should not rely solely on random mutation and fitness.
- The platform accumulates architectural knowledge.
"""

from __future__ import annotations

import uuid
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from datetime import datetime


class PatternCategory(Enum):
    """Categories of architectural patterns."""
    ARCHITECTURAL = "architectural"
    STRUCTURAL = "structural"
    BEHAVIOURAL = "behavioural"
    SECURITY = "security"
    DATA = "data"
    DEPLOYMENT = "deployment"
    INTEGRATION = "integration"
    OBSERVABILITY = "observability"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"


@dataclass(frozen=True)
class Pattern:
    """An architectural pattern with known fitness impact."""
    name: str
    category: PatternCategory
    description: str
    benefits: List[str] = field(default_factory=list)
    costs: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    suitable_for: List[str] = field(default_factory=list)
    contra_indicators: List[str] = field(default_factory=list)
    evidence: List[EvidenceRecord] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AntiPattern:
    """An anti-pattern to avoid."""
    name: str
    description: str
    symptoms: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    recommended_fixes: List[str] = field(default_factory=list)
    severity: str = "warning"  # "info" | "warning" | "critical"
    evidence: List[EvidenceRecord] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceRecord:
    """A record of evidence for a pattern's fitness impact."""
    context: str  # e.g., "ecommerce", "internal_tool", "saas"
    fitness_delta: Dict[str, float] = field(default_factory=dict)
    system_size: str = "medium"  # "small" | "medium" | "large"
    generation_count: int = 10
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass(frozen=True)
class MutationRecord:
    """A record of a mutation's outcome."""
    operator_name: str
    target_context: str
    fitness_before: Dict[str, float]
    fitness_after: Dict[str, float]
    fitness_delta: Dict[str, float]
    accepted: bool
    generation: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: str = ""


@dataclass(frozen=True)
class KnowledgeQuery:
    """A query against the knowledge base."""
    context: Optional[str] = None
    category: Optional[PatternCategory] = None
    tags: Optional[List[str]] = None
    min_evidence_count: int = 0
    fitness_dimension: Optional[str] = None
    max_results: int = 10


class ArchitectureKnowledgeBase:
    """Accumulates and provides architectural knowledge.

    The knowledge base is append-only. It grows with every evolution
    run and every deployment. It provides evidence-based recommendations
    for mutation selection, crossover guidance, fitness prediction,
    anti-pattern avoidance, and explanation.
    """

    def __init__(self):
        self._patterns: Dict[str, Pattern] = {}
        self._anti_patterns: Dict[str, AntiPattern] = {}
        self._mutation_records: List[MutationRecord] = []
        self._compatibility_cache: Dict[Tuple[str, str], float] = {}

    # ─── Pattern Management ───

    def register_pattern(self, pattern: Pattern) -> str:
        """Register an architectural pattern."""
        self._patterns[pattern.name] = pattern
        return pattern.name

    def get_pattern(self, name: str) -> Optional[Pattern]:
        """Get a pattern by name."""
        return self._patterns.get(name)

    def query_patterns(self, query: KnowledgeQuery) -> List[Pattern]:
        """Query patterns by context, category, tags, and evidence."""
        results = list(self._patterns.values())

        if query.context:
            results = [
                p for p in results
                if any(e.context == query.context for e in p.evidence)
            ]

        if query.category:
            results = [p for p in results if p.category == query.category]

        if query.tags:
            results = [
                p for p in results
                if all(tag in p.tags for tag in query.tags)
            ]

        if query.min_evidence_count > 0:
            results = [
                p for p in results
                if len(p.evidence) >= query.min_evidence_count
            ]

        # Sort by evidence count (most evidence first)
        results.sort(key=lambda p: len(p.evidence), reverse=True)

        return results[:query.max_results]

    def get_patterns_by_category(self, category: PatternCategory) -> List[Pattern]:
        """Get all patterns in a category."""
        return [p for p in self._patterns.values() if p.category == category]

    # ─── Anti-Pattern Management ───

    def register_anti_pattern(self, anti_pattern: AntiPattern) -> str:
        """Register an anti-pattern to avoid."""
        self._anti_patterns[anti_pattern.name] = anti_pattern
        return anti_pattern.name

    def get_anti_pattern(self, name: str) -> Optional[AntiPattern]:
        """Get an anti-pattern by name."""
        return self._anti_patterns.get(name)

    def detect_anti_patterns(self, context: str) -> List[AntiPattern]:
        """Detect applicable anti-patterns for a context."""
        return [
            ap for ap in self._anti_patterns.values()
            if any(ap.name.lower() in context.lower() for ap in self._anti_patterns.values())
        ]

    # ─── Mutation Records ───

    def record_mutation(self, record: MutationRecord):
        """Record the outcome of a mutation."""
        self._mutation_records.append(record)

    def query_successful_mutations(self, operator_name: str,
                                    context: str) -> List[MutationRecord]:
        """Get successful mutations of a given operator in a context."""
        return [
            r for r in self._mutation_records
            if r.operator_name == operator_name
            and r.target_context == context
            and r.accepted
        ]

    def get_operator_success_rate(self, operator_name: str) -> float:
        """Get the success rate of an operator."""
        relevant = [r for r in self._mutation_records
                    if r.operator_name == operator_name]
        if not relevant:
            return 0.5  # Unknown operators get neutral score
        accepted = sum(1 for r in relevant if r.accepted)
        return accepted / len(relevant)

    def get_average_fitness_delta(self, operator_name: str,
                                   dimension: str) -> float:
        """Get average fitness delta for an operator on a dimension."""
        relevant = [r for r in self._mutation_records
                    if r.operator_name == operator_name and r.accepted]
        if not relevant:
            return 0.0
        deltas = [r.fitness_delta.get(dimension, 0.0) for r in relevant]
        return sum(deltas) / len(deltas)

    # ─── Compatibility ───

    def record_compatibility(self, pattern_a: str, pattern_b: str,
                              compatibility: float):
        """Record compatibility between two patterns."""
        key = tuple(sorted([pattern_a, pattern_b]))
        self._compatibility_cache[key] = compatibility

    def get_compatibility(self, pattern_a: str, pattern_b: str) -> Optional[float]:
        """Get compatibility score between two patterns."""
        key = tuple(sorted([pattern_a, pattern_b]))
        return self._compatibility_cache.get(key)

    # ─── Persistence ───

    def to_dict(self) -> dict:
        """Serialize the knowledge base to a dict."""
        return {
            "patterns": {
                name: {
                    "name": p.name,
                    "category": p.category.value,
                    "description": p.description,
                    "benefits": p.benefits,
                    "costs": p.costs,
                    "prerequisites": p.prerequisites,
                    "evidence_count": len(p.evidence),
                }
                for name, p in self._patterns.items()
            },
            "anti_patterns": {
                name: {
                    "name": ap.name,
                    "description": ap.description,
                    "severity": ap.severity,
                }
                for name, ap in self._anti_patterns.items()
            },
            "mutation_record_count": len(self._mutation_records),
            "compatibility_count": len(self._compatibility_cache),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


# ─── Default Pattern Registry ───

def register_default_patterns(kb: ArchitectureKnowledgeBase):
    """Register the default set of architectural patterns."""
    patterns = [
        Pattern(
            name="CQRS",
            category=PatternCategory.ARCHITECTURAL,
            description="Command Query Responsibility Segregation - separate read and write models",
            benefits=["high scalability", "separation of concerns", "independent scaling"],
            costs=["operational complexity", "eventual consistency", "debugging difficulty"],
            prerequisites=["event bus", "separate read/write models"],
            suitable_for=["high write contention", "complex read patterns"],
            contra_indicators=["simple CRUD", "low traffic", "small team"],
            evidence=[
                EvidenceRecord(
                    context="ecommerce",
                    fitness_delta={"performance": 0.3, "complexity": -0.2},
                    system_size="medium",
                ),
                EvidenceRecord(
                    context="internal_tool",
                    fitness_delta={"performance": 0.05, "complexity": -0.4},
                    system_size="small",
                ),
            ],
            tags=["scalability", "patterns", "event-driven"],
        ),
        Pattern(
            name="Event Sourcing",
            category=PatternCategory.ARCHITECTURAL,
            description="Store state changes as a sequence of events",
            benefits=["complete audit trail", "temporal queries", "event-driven integrations"],
            costs=["storage growth", "event schema evolution", "eventual consistency"],
            prerequisites=["event store", "idempotent event handlers"],
            suitable_for=["audit-heavy domains", "financial systems", "collaborative editing"],
            contra_indicators=["simple CRUD", "high-frequency updates", "strong consistency needs"],
            tags=["patterns", "event-driven", "audit"],
        ),
        Pattern(
            name="Repository Pattern",
            category=PatternCategory.STRUCTURAL,
            description="Abstract data access behind a repository interface",
            benefits=["testability", "data access abstraction", "swappable implementations"],
            costs=["boilerplate code", "leaky abstractions for complex queries"],
            prerequisites=["interface definitions", "dependency injection"],
            suitable_for=["most applications", "team of any size"],
            contra_indicators=["very simple CRUD", "prototypes"],
            tags=["patterns", "data", "testing"],
        ),
        Pattern(
            name="Circuit Breaker",
            category=PatternCategory.RELIABILITY,
            description="Prevent cascade failures by detecting and isolating faults",
            benefits=["fault isolation", "graceful degradation", "system resilience"],
            costs=["increased latency on failure detection", "state management complexity"],
            prerequisites=["service discovery", "timeout configuration", "health checks"],
            suitable_for=["distributed systems", "microservices", "external API calls"],
            contra_indicators=["monolithic apps", "in-process calls"],
            tags=["reliability", "patterns", "resilience"],
        ),
        Pattern(
            name="Event-Driven Architecture",
            category=PatternCategory.ARCHITECTURAL,
            description="Decouple services through asynchronous event communication",
            benefits=["loose coupling", "scalability", "extensibility"],
            costs=["eventual consistency", "debugging complexity", "schema management"],
            prerequisites=["event bus/message broker", "event schema registry"],
            suitable_for=["distributed systems", "microservices", "workflow automation"],
            contra_indicators=["simple linear flows", "strong consistency requirements"],
            tags=["patterns", "event-driven", "scalability"],
        ),
        Pattern(
            name="Strangler Fig Pattern",
            category=PatternCategory.ARCHITECTURAL,
            description="Gradually replace legacy systems with new implementations",
            benefits=["low-risk migration", "continuous delivery", "parallel operation"],
            costs=["routing complexity", "dual maintenance", "data synchronization"],
            prerequisites=["feature flags", "routing layer", "data sync mechanism"],
            suitable_for=["legacy system migration", "monolith decomposition"],
            contra_indicators=["greenfield projects", "small systems"],
            tags=["patterns", "migration", "legacy"],
        ),
        Pattern(
            name="Saga Pattern",
            category=PatternCategory.BEHAVIOURAL,
            description="Manage distributed transactions with compensating actions",
            benefits=["distributed transaction management", "no distributed lock", "resilience"],
            costs=["compensation complexity", "eventual consistency", "monitoring overhead"],
            prerequisites=["event bus", "compensation handlers", "correlation IDs"],
            suitable_for=["distributed transactions", "multi-service workflows"],
            contra_indicators=["single-service transactions", "strong consistency needs"],
            tags=["patterns", "transactions", "consistency"],
        ),
        Pattern(
            name="API Gateway",
            category=PatternCategory.STRUCTURAL,
            description="Single entry point for client-to-backend communication",
            benefits=["request routing", "cross-cutting concerns", "protocol translation"],
            costs=["single point of failure", "performance bottleneck", "development overhead"],
            prerequisites=["routing configuration", "authentication integration"],
            suitable_for=["microservices", "mobile backends", "multi-protocol systems"],
            contra_indicators=["single service", "direct client-service communication"],
            tags=["patterns", "api", "microservices"],
        ),
    ]

    for pattern in patterns:
        kb.register_pattern(pattern)

    anti_patterns = [
        AntiPattern(
            name="Big Ball of Mud",
            description="A system with no discernible architecture, tangled dependencies",
            symptoms=["no clear module boundaries", "circular dependencies", "spaghetti code"],
            consequences=["high maintenance cost", "hard to evolve", "brittle"],
            recommended_fixes=["extract bounded contexts", "apply dependency inversion", "introduce interfaces"],
            severity="critical",
        ),
        AntiPattern(
            name="Golden Hammer",
            description="Applying a familiar pattern to every problem regardless of suitability",
            symptoms=["every service uses the same architecture", "over-engineered solutions"],
            consequences=["unnecessary complexity", "wasted resources", "reduced agility"],
            recommended_fixes=["evaluate alternatives", "match pattern to context"],
            severity="warning",
        ),
        AntiPattern(
            name="Distributed Monolith",
            description="Microservices that are tightly coupled, deployed together",
            symptoms=["shared databases", "synchronous calls everywhere", "coordinated deployments"],
            consequences=["microservice costs without benefits", "hard to test", "fragile"],
            recommended_fixes=["introduce async boundaries", "database per service", "independent deployment"],
            severity="critical",
        ),
        AntiPattern(
            name="God Service",
            description="A single service that knows about everything",
            symptoms=["large service with many responsibilities", "most workflows pass through it"],
            consequences=["single point of failure", "bottleneck", "hard to maintain"],
            recommended_fixes=["split by business capability", "extract subdomains"],
            severity="warning",
        ),
    ]

    for ap in anti_patterns:
        kb.register_anti_pattern(ap)