"""
Knowledge Engine — Top-Level Orchestrator.

The long-term memory of the platform. Accumulates architectural knowledge
from evolution runs and operational feedback. Provides evidence-based
recommendations for mutation selection, anti-pattern avoidance,
compatibility analysis, and fitness prediction.

Constitutional role:
- Observe and accumulate; do not modify the ISR directly
- Provide recommendations; evolution engine decides whether to apply them
- All records are append-only
"""

from __future__ import annotations

import time
from typing import Any, Optional

from constitutional_architecture.knowledge.anti_pattern_repository import (
    AntiPatternEntry,
    AntiPatternRepository,
)
from constitutional_architecture.knowledge.compatibility_repository import (
    CompatibilityRepository,
)
from constitutional_architecture.knowledge.events import (
    KnowledgeEvent,
    KnowledgeEventBus,
    KnowledgeEventType,
)
from constitutional_architecture.knowledge.fitness_repository import (
    FitnessRecord,
    FitnessRepository,
)
from constitutional_architecture.knowledge.knowledge_types import (
    CompatibilityRecord,
    ConfidenceLevel,
    DomainFact,
    EvolutionLesson,
    HeuristicRule,
    KnowledgeCategory,
)
from constitutional_architecture.knowledge.metrics import KnowledgeMetrics
from constitutional_architecture.knowledge.mutation_repository import (
    MutationRecordEntry,
    MutationRepository,
)
from constitutional_architecture.knowledge.pattern_repository import (
    PatternEntry,
    PatternRepository,
)
from constitutional_architecture.knowledge.persistence import KnowledgePersistence
from constitutional_architecture.knowledge.reasoning_engine import ReasoningEngine
from constitutional_architecture.knowledge.recommendation_engine import (
    KnowledgeRecommendation,
    RecommendationEngine,
)


class KnowledgeEngine:

    def __init__(
        self,
        event_bus: Optional[KnowledgeEventBus] = None,
        persistence: Optional[KnowledgePersistence] = None,
    ) -> None:
        self._event_bus = event_bus or KnowledgeEventBus()
        self._persistence = persistence
        self._metrics = KnowledgeMetrics()

        self._patterns = PatternRepository()
        self._anti_patterns = AntiPatternRepository()
        self._mutations = MutationRepository()
        self._fitness = FitnessRepository()
        self._compatibility = CompatibilityRepository()
        self._reasoning = ReasoningEngine(
            pattern_repo=self._patterns,
            anti_pattern_repo=self._anti_patterns,
            mutation_repo=self._mutations,
            fitness_repo=self._fitness,
            compatibility_repo=self._compatibility,
        )
        self._recommender = RecommendationEngine(
            pattern_repo=self._patterns,
            anti_pattern_repo=self._anti_patterns,
            mutation_repo=self._mutations,
            fitness_repo=self._fitness,
            compatibility_repo=self._compatibility,
            reasoning=self._reasoning,
        )

    def register_pattern(self, entry: PatternEntry) -> str:
        start = time.perf_counter()
        pid = self._patterns.register(entry)
        self._event_bus.publish(KnowledgeEvent(
            event_type=KnowledgeEventType.KNOWLEDGE_ADDED,
            data={"type": "pattern", "id": pid, "name": entry.name},
        ))
        self._metrics.record_query(hit=True, latency_ms=(time.perf_counter() - start) * 1000)
        return pid

    def register_anti_pattern(self, entry: AntiPatternEntry) -> str:
        aid = self._anti_patterns.register(entry)
        self._event_bus.publish(KnowledgeEvent(
            event_type=KnowledgeEventType.ANTI_PATTERN_DETECTED,
            data={"type": "anti_pattern", "id": aid, "name": entry.name},
        ))
        return aid

    def record_mutation(self, entry: MutationRecordEntry) -> str:
        rid = self._mutations.record_mutation(entry)
        self._event_bus.publish(KnowledgeEvent(
            event_type=KnowledgeEventType.KNOWLEDGE_ADDED,
            data={"type": "mutation_record", "id": rid, "operator": entry.operator_name},
        ))
        return rid

    def record_fitness(self, record: FitnessRecord) -> None:
        self._fitness.record(record)
        self._mutations.record_fitness(record)

    def record_compatibility(self, record: CompatibilityRecord) -> None:
        self._compatibility.record(record)
        self._event_bus.publish(KnowledgeEvent(
            event_type=KnowledgeEventType.COMPATIBILITY_UPDATED,
            data={
                "pattern_a": record.pattern_a,
                "pattern_b": record.pattern_b,
                "score": record.compatibility_score,
            },
        ))

    def register_heuristic(self, rule: HeuristicRule) -> None:
        self._reasoning.register_heuristic(rule)

    def register_domain_fact(self, fact: DomainFact) -> None:
        self._reasoning.register_domain_fact(fact)

    def register_lesson(self, lesson: EvolutionLesson) -> None:
        self._reasoning.register_lesson(lesson)

    def query_patterns(
        self,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        text: Optional[str] = None,
        min_evidence: int = 0,
        max_results: int = 50,
    ) -> list[PatternEntry]:
        start = time.perf_counter()
        results = self._patterns.query(
            category=category, tags=tags, text=text,
            min_evidence=min_evidence, max_results=max_results,
        )
        self._metrics.record_query(
            hit=len(results) > 0,
            latency_ms=(time.perf_counter() - start) * 1000,
        )
        return results

    def detect_anti_patterns(
        self, context: str, tags: Optional[list[str]] = None
    ) -> list[Any]:
        return self._reasoning.detect_anti_patterns(context, tags)

    def get_recommendations(
        self,
        context: str,
        constraints: Optional[list[str]] = None,
    ) -> list[KnowledgeRecommendation]:
        start = time.perf_counter()
        recs = self._recommender.recommend_mutations(context, constraints)
        for rec in recs:
            self._event_bus.publish(KnowledgeEvent(
                event_type=KnowledgeEventType.RECOMMENDATION_GENERATED,
                data={
                    "id": rec.recommendation_id,
                    "category": rec.category,
                    "title": rec.title,
                    "confidence": rec.confidence.value,
                },
            ))
        self._metrics.record_recommendation()
        return recs

    def get_evolution_recommendations(
        self,
        isr_hash: str,
        fitness_scores: dict[str, float],
        context: str = "",
    ) -> list[KnowledgeRecommendation]:
        recs = self._recommender.recommend_for_evolution_run(
            isr_hash, fitness_scores, context,
        )
        for rec in recs:
            self._metrics.record_recommendation(accepted=False)
        return recs

    def save(self) -> None:
        if self._persistence is None:
            return
        self._persistence.save_fitness_records(self._fitness.get_records())
        self._persistence.save_lessons(self._reasoning.lessons)
        self._event_bus.publish(KnowledgeEvent(
            event_type=KnowledgeEventType.KNOWLEDGE_PERSISTED,
        ))

    def load(self) -> None:
        if self._persistence is None:
            return
        for record in self._persistence.load_fitness_records():
            self._fitness.record(record)
        for lesson in self._persistence.load_lessons():
            self._reasoning.register_lesson(lesson)
        self._event_bus.publish(KnowledgeEvent(
            event_type=KnowledgeEventType.KNOWLEDGE_LOADED,
        ))

    def subscribe(self, event_type: KnowledgeEventType, handler) -> None:
        self._event_bus.subscribe(event_type, handler)

    @property
    def metrics(self) -> KnowledgeMetrics:
        return self._metrics

    @property
    def patterns(self) -> PatternRepository:
        return self._patterns

    @property
    def anti_patterns(self) -> AntiPatternRepository:
        return self._anti_patterns

    @property
    def mutations(self) -> MutationRepository:
        return self._mutations

    @property
    def fitness(self) -> FitnessRepository:
        return self._fitness

    @property
    def compatibility(self) -> CompatibilityRepository:
        return self._compatibility

    @property
    def reasoning(self) -> ReasoningEngine:
        return self._reasoning

    @property
    def recommender(self) -> RecommendationEngine:
        return self._recommender

    @property
    def metrics_snapshot(self) -> Any:
        return self._metrics.snapshot(
            total_patterns=self._patterns.count,
            total_anti_patterns=self._anti_patterns.count,
            total_mutation_records=self._mutations.total_mutations,
            total_fitness_records=self._fitness.total_records,
        )
