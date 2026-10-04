"""Bucket 2 specialized capability operators."""

from __future__ import annotations

from .specialized_mutations import _spec
from .architecture_mutation import domain_operator


def documentation_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "documentation", paths, rationale, evidence, operator),
        ("documentation-accuracy", "implementation-traceability"),
        "low",
    )


def test_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "testing", paths, rationale, evidence, operator),
        ("test-correctness", "regression-preservation", "coverage-traceability"),
        "medium",
    )


def architecture_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "architecture", paths, rationale, evidence, operator),
        ("architecture-consistency", "dependency-integrity", "requirement-traceability"),
        "high",
    )


def migration_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "migration", paths, rationale, evidence, operator),
        ("migration-safety", "data-integrity", "rollback-readiness"),
        "high",
    )


def refactor_mutation(mutation_id, paths, rationale, evidence, operator):
    return _spec(
        domain_operator(mutation_id, "refactor", paths, rationale, evidence, operator),
        ("behavior-preservation", "dependency-integrity", "regression-preservation"),
        "high",
    )
