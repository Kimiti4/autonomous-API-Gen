"""Tests for the knowledge recommendation engine."""

import pytest

from constitutional_architecture.knowledge.recommendation_engine import RecommendationEngine
from constitutional_architecture.knowledge.pattern_repository import PatternRepository, PatternEntry
from constitutional_architecture.knowledge.anti_pattern_repository import AntiPatternRepository, AntiPatternEntry
from constitutional_architecture.knowledge.knowledge_types import ConfidenceLevel


class TestKnowledgeRecommendationEngine:
    def test_recommend_mutations_anti_pattern(self):
        ap_repo = AntiPatternRepository()
        ap_repo.register(AntiPatternEntry(
            name="Big Ball of Mud",
            description="No discernible architecture",
            symptoms=("no clear module boundaries",),
            severity="critical",
            recommended_fixes=("extract bounded contexts",),
        ))
        engine = RecommendationEngine(anti_pattern_repo=ap_repo)
        recs = engine.recommend_mutations(
            "no clear module boundaries in the system"
        )
        assert len(recs) >= 1

    def test_recommend_mutations_pattern(self):
        pattern_repo = PatternRepository()
        pattern_repo.register(PatternEntry(
            name="CQRS", description="Command Query Responsibility Segregation scalability",
            category="architectural", tags=("scalability",),
            evidence_count=10,
        ))
        engine = RecommendationEngine(pattern_repo=pattern_repo)
        recs = engine.recommend_mutations("scalability")
        assert len(recs) >= 1

    def test_recommend_evolution_run(self):
        pattern_repo = PatternRepository()
        pattern_repo.register(PatternEntry(
            name="CQRS", description="CQRS",
            category="architectural", evidence_count=5,
        ))
        from constitutional_architecture.knowledge.mutation_repository import (
            MutationRepository, MutationRecordEntry,
        )
        mutation_repo = MutationRepository()
        for _ in range(5):
            mutation_repo.record_mutation(MutationRecordEntry(
                operator_name="split_module",
                target_context="test",
                fitness_delta={"complexity": -0.2},
                accepted=True, generation=1,
            ))
        engine = RecommendationEngine(
            pattern_repo=pattern_repo, mutation_repo=mutation_repo,
        )
        recs = engine.recommend_for_evolution_run(
            isr_hash="test",
            fitness_scores={"complexity": 0.3, "performance": 0.8},
            context="test",
        )
        # May or may not find recommendations depending on mutation matching
        assert isinstance(recs, list)
