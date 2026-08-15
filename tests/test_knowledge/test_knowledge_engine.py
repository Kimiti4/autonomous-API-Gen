"""Integration tests for the Knowledge Engine."""

import pytest

from constitutional_architecture.knowledge.knowledge_engine import KnowledgeEngine
from constitutional_architecture.knowledge.pattern_repository import PatternEntry
from constitutional_architecture.knowledge.anti_pattern_repository import AntiPatternEntry
from constitutional_architecture.knowledge.mutation_repository import MutationRecordEntry
from constitutional_architecture.knowledge.knowledge_types import (
    CompatibilityRecord,
    FitnessRecord,
    ConfidenceLevel,
)


class TestKnowledgeEngine:
    def test_register_and_query_patterns(self):
        engine = KnowledgeEngine()
        pid = engine.register_pattern(PatternEntry(
            name="CQRS", description="Command Query Responsibility Segregation",
            category="architectural", tags=("scalability",),
            evidence_count=10,
        ))
        assert pid is not None
        results = engine.query_patterns(tags=["scalability"])
        assert len(results) >= 1
        assert results[0].name == "CQRS"

    def test_register_anti_pattern(self):
        engine = KnowledgeEngine()
        aid = engine.register_anti_pattern(AntiPatternEntry(
            name="Big Ball of Mud",
            description="No discernible architecture",
            symptoms=("no clear module boundaries",),
            severity="critical",
        ))
        assert aid is not None
        results = engine.detect_anti_patterns("no clear module boundaries")
        assert len(results) >= 1

    def test_record_mutation(self):
        engine = KnowledgeEngine()
        rid = engine.record_mutation(MutationRecordEntry(
            operator_name="split_module",
            target_context="ecommerce",
            fitness_delta={"complexity": -0.2},
            accepted=True, generation=1,
        ))
        assert rid is not None
        assert engine.mutations.total_mutations == 1

    def test_record_fitness(self):
        engine = KnowledgeEngine()
        engine.record_fitness(FitnessRecord(
            mutation_type="split_module",
            dimensions={"complexity": -0.2},
            sample_size=5, context="ecommerce",
            avg_fitness_delta={"complexity": -0.2},
        ))
        assert engine.fitness.total_records == 1

    def test_record_compatibility(self):
        engine = KnowledgeEngine()
        engine.register_pattern(PatternEntry(name="CQRS", description="CQRS"))
        engine.register_pattern(PatternEntry(name="Event Sourcing", description="Event Sourcing"))
        engine.record_compatibility(CompatibilityRecord(
            pattern_a="CQRS", pattern_b="Event Sourcing",
            compatibility_score=0.85, sample_size=10,
        ))
        score = engine.compatibility.get_compatibility("CQRS", "Event Sourcing")
        assert score is not None
        assert score == pytest.approx(0.85)

    def test_get_recommendations(self):
        engine = KnowledgeEngine()
        engine.register_pattern(PatternEntry(
            name="CQRS", description="CQRS",
            category="architectural", evidence_count=5,
        ))
        recs = engine.get_recommendations(
            "need better read scalability",
            constraints=["Event Sourcing"],
        )
        assert isinstance(recs, list)

    def test_metrics_tracking(self):
        engine = KnowledgeEngine()
        engine.query_patterns(text="CQRS")
        engine.query_patterns(text="Saga")
        snap = engine.metrics_snapshot
        assert snap.total_queries >= 0
        assert snap.hit_rate >= 0.0

    def test_subscribe_to_events(self):
        engine = KnowledgeEngine()
        from constitutional_architecture.knowledge.events import KnowledgeEventType
        events = []
        engine.subscribe(KnowledgeEventType.KNOWLEDGE_ADDED, lambda e: events.append(e))
        engine.register_pattern(PatternEntry(name="Test", description="Test"))
        assert len(events) >= 1
