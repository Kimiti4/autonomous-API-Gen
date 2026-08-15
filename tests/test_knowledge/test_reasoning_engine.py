"""Tests for the reasoning engine."""

import pytest

from constitutional_architecture.knowledge.reasoning_engine import ReasoningEngine
from constitutional_architecture.knowledge.pattern_repository import PatternRepository, PatternEntry
from constitutional_architecture.knowledge.anti_pattern_repository import AntiPatternRepository, AntiPatternEntry
from constitutional_architecture.knowledge.knowledge_types import (
    ConfidenceLevel,
    FitnessRecord,
    HeuristicRule,
    DomainFact,
)


class TestReasoningEngine:
    def test_infer_best_pattern(self):
        pattern_repo = PatternRepository()
        pattern_repo.register(PatternEntry(
            name="CQRS", description="Command Query Responsibility Segregation scalability",
            category="architectural", tags=("scalability",),
            evidence_count=10,
        ))
        engine = ReasoningEngine(pattern_repo=pattern_repo)
        results = engine.infer_best_pattern("scalability")
        assert len(results) >= 1

    def test_detect_anti_patterns(self):
        ap_repo = AntiPatternRepository()
        ap_repo.register(AntiPatternEntry(
            name="Big Ball of Mud",
            description="No discernible architecture",
            symptoms=("no clear module boundaries", "circular dependencies"),
            severity="critical",
        ))
        engine = ReasoningEngine(anti_pattern_repo=ap_repo)
        results = engine.detect_anti_patterns("no clear module boundaries in the system")
        assert len(results) >= 1
        assert "Big Ball of Mud" in results[0].description

    def test_suggest_mutation_strategy(self):
        from constitutional_architecture.knowledge.mutation_repository import (
            MutationRepository, MutationRecordEntry,
        )
        mutation_repo = MutationRepository()
        for _ in range(3):
            mutation_repo.record_mutation(MutationRecordEntry(
                operator_name="split_module",
                target_context="ecommerce",
                fitness_before={"complexity": 0.5},
                fitness_after={"complexity": 0.3},
                fitness_delta={"complexity": -0.2},
                accepted=True, generation=1,
            ))
        engine = ReasoningEngine(mutation_repo=mutation_repo)
        result = engine.suggest_mutation_strategy("split_module", "ecommerce")
        assert result is not None
        assert len(result.supporting_evidence) >= 1

    def test_register_heuristic_and_domain_fact(self):
        engine = ReasoningEngine()
        engine.register_heuristic(HeuristicRule(
            name="test_rule", description="Test",
            priority=1, success_count=5,
        ))
        engine.register_domain_fact(DomainFact(
            domain="ecommerce", statement="Test fact",
        ))
        assert len(engine.heuristics) == 1
        assert len(engine.domain_facts) == 1
