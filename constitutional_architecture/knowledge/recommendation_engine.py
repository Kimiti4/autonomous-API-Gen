"""
Knowledge Recommendation Engine — Generates actionable recommendations.

Combines pattern knowledge, anti-pattern detection, fitness history,
and reasoning to produce recommendations for the evolution engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.knowledge.anti_pattern_repository import (
    AntiPatternRepository,
)
from constitutional_architecture.knowledge.compatibility_repository import (
    CompatibilityRepository,
)
from constitutional_architecture.knowledge.fitness_repository import (
    FitnessRepository,
)
from constitutional_architecture.knowledge.knowledge_types import ConfidenceLevel
from constitutional_architecture.knowledge.mutation_repository import (
    MutationRepository,
)
from constitutional_architecture.knowledge.pattern_repository import PatternRepository
from constitutional_architecture.knowledge.reasoning_engine import ReasoningEngine


@dataclass(frozen=True)
class KnowledgeRecommendation:
    recommendation_id: str
    category: str
    title: str
    description: str
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    suggested_mutation: str = ""
    target_context: str = ""
    reasoning: str = ""
    supporting_evidence: tuple[str, ...] = ()
    priority: int = 5
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class RecommendationEngine:

    def __init__(
        self,
        pattern_repo: Optional[PatternRepository] = None,
        anti_pattern_repo: Optional[AntiPatternRepository] = None,
        mutation_repo: Optional[MutationRepository] = None,
        fitness_repo: Optional[FitnessRepository] = None,
        compatibility_repo: Optional[CompatibilityRepository] = None,
        reasoning: Optional[ReasoningEngine] = None,
    ) -> None:
        self._reasoning = reasoning or ReasoningEngine(
            pattern_repo=pattern_repo,
            anti_pattern_repo=anti_pattern_repo,
            mutation_repo=mutation_repo,
            fitness_repo=fitness_repo,
            compatibility_repo=compatibility_repo,
        )
        self._recommendations: list[KnowledgeRecommendation] = []

    def recommend_mutations(
        self, context: str, constraints: Optional[list[str]] = None
    ) -> list[KnowledgeRecommendation]:
        recs: list[KnowledgeRecommendation] = []

        # Anti-pattern detection recommendations
        anti_pattern_results = self._reasoning.detect_anti_patterns(context)
        for result in anti_pattern_results:
            recs.append(KnowledgeRecommendation(
                recommendation_id=f"krec-{uuid.uuid4().hex[:12]}",
                category="anti_pattern",
                title=f"Avoid: {result.related_patterns[0] if result.related_patterns else 'Anti-pattern'}",
                description=result.description,
                confidence=result.confidence,
                suggested_mutation="structural_refactor",
                target_context=context,
                reasoning="Anti-pattern detected in context",
                supporting_evidence=tuple(result.supporting_evidence),
                priority=1 if result.confidence == ConfidenceLevel.HIGH else 3,
            ))

        # Pattern recommendations
        pattern_results = self._reasoning.infer_best_pattern(context, constraints)
        for result in pattern_results:
            priority_map = {
                ConfidenceLevel.HIGH: 1,
                ConfidenceLevel.MEDIUM: 3,
                ConfidenceLevel.LOW: 5,
                ConfidenceLevel.SPECULATIVE: 7,
                ConfidenceLevel.CONFIRMED: 0,
            }
            recs.append(KnowledgeRecommendation(
                recommendation_id=f"krec-{uuid.uuid4().hex[:12]}",
                category="pattern",
                title=f"Apply: {result.related_patterns[0] if result.related_patterns else 'Pattern'}",
                description=result.description,
                confidence=result.confidence,
                suggested_mutation="structural_add_entity",
                target_context=context,
                reasoning="Pattern matched to context",
                supporting_evidence=tuple(result.supporting_evidence),
                priority=priority_map.get(result.confidence, 5),
            ))

        self._recommendations.extend(recs)
        return recs

    def recommend_for_evolution_run(
        self,
        isr_hash: str,
        fitness_scores: dict[str, float],
        context: str = "",
    ) -> list[KnowledgeRecommendation]:
        recs: list[KnowledgeRecommendation] = []

        # Find dimensions with low fitness
        low_dimensions = [k for k, v in fitness_scores.items() if v < 0.5]
        for dim in low_dimensions:
            # Find mutations that improve this dimension
            successful_ops = self._reasoning._mutations.get_most_successful_operators()
            for op_name, rate in successful_ops:
                if rate > 0.5:
                    prediction = self._reasoning.suggest_mutation_strategy(op_name, context)
                    if prediction and any(dim in ev for ev in prediction.supporting_evidence):
                        recs.append(KnowledgeRecommendation(
                            recommendation_id=f"krec-{uuid.uuid4().hex[:12]}",
                            category="evolution",
                            title=f"Improve {dim} via {op_name}",
                            description=prediction.description,
                            confidence=prediction.confidence,
                            suggested_mutation=op_name,
                            target_context=context,
                            reasoning=f"Low fitness in '{dim}' suggests '{op_name}' mutation",
                            supporting_evidence=tuple(prediction.supporting_evidence),
                            priority=1,
                        ))

        self._recommendations.extend(recs)
        return recs

    @property
    def recommendations(self) -> list[KnowledgeRecommendation]:
        return list(self._recommendations)

    def get_by_category(self, category: str) -> list[KnowledgeRecommendation]:
        return [r for r in self._recommendations if r.category == category]

    def get_high_priority(self, threshold: int = 3) -> list[KnowledgeRecommendation]:
        return [r for r in self._recommendations if r.priority <= threshold]
