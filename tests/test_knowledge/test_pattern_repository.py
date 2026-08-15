"""Tests for the pattern repository."""

import pytest

from constitutional_architecture.knowledge.pattern_repository import PatternRepository, PatternEntry
from constitutional_architecture.knowledge.knowledge_types import ConfidenceLevel


class TestPatternRepository:
    def test_register_and_get(self):
        repo = PatternRepository()
        pid = repo.register(PatternEntry(
            name="CQRS", description="Command Query Responsibility Segregation",
            category="architectural", tags=("scalability",),
            evidence_count=5,
        ))
        assert pid is not None
        entry = repo.get(pid)
        assert entry is not None
        assert entry.name == "CQRS"

    def test_get_by_name(self):
        repo = PatternRepository()
        repo.register(PatternEntry(
            name="CQRS", description="CQRS pattern",
        ))
        entry = repo.get_by_name("CQRS")
        assert entry is not None
        assert entry.name == "CQRS"

    def test_query_by_category(self):
        repo = PatternRepository()
        repo.register(PatternEntry(
            name="CQRS", category="architectural",
            description="CQRS", evidence_count=3,
        ))
        repo.register(PatternEntry(
            name="Repository", category="structural",
            description="Repository pattern", evidence_count=5,
        ))
        results = repo.query(category="architectural")
        assert len(results) == 1
        assert results[0].name == "CQRS"

    def test_query_by_text(self):
        repo = PatternRepository()
        repo.register(PatternEntry(
            name="CQRS", category="architectural",
            description="Separate read and write models",
        ))
        results = repo.query(text="read")
        assert len(results) >= 1

    def test_query_min_evidence(self):
        repo = PatternRepository()
        repo.register(PatternEntry(
            name="CQRS", description="CQRS", evidence_count=2,
        ))
        repo.register(PatternEntry(
            name="Saga", description="Saga", evidence_count=10,
        ))
        results = repo.query(min_evidence=5)
        assert len(results) == 1
        assert results[0].name == "Saga"

    def test_add_relation(self):
        repo = PatternRepository()
        pid1 = repo.register(PatternEntry(name="CQRS", description="CQRS"))
        pid2 = repo.register(PatternEntry(name="Event Sourcing", description="Event Sourcing"))
        repo.add_relation(pid1, pid2, "complements")
        compatible = repo.get_compatible_patterns(pid1)
        assert len(compatible) == 1
        assert compatible[0].name == "Event Sourcing"
