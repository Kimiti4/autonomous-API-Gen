"""
Knowledge Engine — Accumulated architectural wisdom.

The platform accumulates architectural knowledge from evolution runs
and operational feedback. This knowledge base makes mutations
increasingly informed rather than purely stochastic.

Key capabilities:
- Pattern storage and retrieval
- Anti-pattern detection
- Fitness impact prediction
- Mutation sequence learning
- Compatibility analysis
- Reasoning and inference
- Recommendation generation
"""

from constitutional_architecture.knowledge.knowledge_engine import KnowledgeEngine
from constitutional_architecture.knowledge.knowledge_types import (
    CompatibilityRecord,
    ConfidenceLevel,
    DomainFact,
    EvolutionLesson,
    FitnessRecord,
    HeuristicRule,
    KnowledgeCategory,
)
from constitutional_architecture.knowledge.pattern_repository import PatternEntry
from constitutional_architecture.knowledge.anti_pattern_repository import AntiPatternEntry
from constitutional_architecture.knowledge.mutation_repository import MutationRecordEntry
from constitutional_architecture.knowledge.reasoning_engine import ReasoningResult
from constitutional_architecture.knowledge.recommendation_engine import KnowledgeRecommendation

__all__ = [
    "KnowledgeEngine",
    "PatternEntry",
    "AntiPatternEntry",
    "MutationRecordEntry",
    "FitnessRecord",
    "CompatibilityRecord",
    "KnowledgeRecommendation",
    "ReasoningResult",
    "KnowledgeCategory",
    "ConfidenceLevel",
    "DomainFact",
    "EvolutionLesson",
    "HeuristicRule",
]
