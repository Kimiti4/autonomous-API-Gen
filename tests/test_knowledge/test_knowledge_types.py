"""Tests for knowledge types."""

import pytest
from datetime import datetime

from constitutional_architecture.knowledge.knowledge_types import (
    KnowledgeCategory,
    ConfidenceLevel,
    FitnessRecord,
    CompatibilityRecord,
    EvolutionLesson,
    DomainFact,
    HeuristicRule,
)


class TestKnowledgeTypes:
    def test_knowledge_category_enum(self):
        assert KnowledgeCategory.PATTERN.value == "pattern"
        assert KnowledgeCategory.ANTI_PATTERN.value == "anti_pattern"

    def test_confidence_level_enum(self):
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.CONFIRMED.value == "confirmed"

    def test_fitness_record_creation(self):
        record = FitnessRecord(
            mutation_type="split_module",
            dimensions={"complexity": 0.3, "coupling": -0.2},
            sample_size=5,
            context="ecommerce",
            avg_fitness_delta={"complexity": 0.05, "coupling": -0.04},
        )
        assert record.mutation_type == "split_module"
        assert record.sample_size == 5
        assert record.avg_fitness_delta["complexity"] == 0.05

    def test_compatibility_record_creation(self):
        record = CompatibilityRecord(
            pattern_a="CQRS", pattern_b="Event Sourcing",
            compatibility_score=0.85, sample_size=10,
        )
        assert record.pattern_a == "CQRS"
        assert record.compatibility_score == 0.85

    def test_evolution_lesson_creation(self):
        lesson = EvolutionLesson(
            title="Avoid deep service chains",
            description="Deep call chains increase latency",
            severity="warning",
        )
        assert lesson.title == "Avoid deep service chains"
        assert lesson.severity == "warning"

    def test_domain_fact_creation(self):
        fact = DomainFact(
            domain="ecommerce",
            statement="CQRS improves read scalability",
            evidence_strength=0.8,
        )
        assert fact.domain == "ecommerce"
        assert fact.evidence_strength == 0.8

    def test_heuristic_rule_creation(self):
        rule = HeuristicRule(
            name="split_large_modules",
            description="Split modules with >10 entities",
            priority=1,
            success_count=15,
        )
        assert rule.priority == 1
        assert rule.success_count == 15
