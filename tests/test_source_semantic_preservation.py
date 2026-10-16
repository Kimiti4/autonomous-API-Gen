"""Regression tests for requirement semantics surviving genome materialization."""
from __future__ import annotations

from genesis.mapper import ReferenceDeterministicMapper
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.core.graph import Priority, RequirementGraph, RequirementKind, RequirementNode
from evolution.core.construction import ReferenceGenomeConstructor
from evolution.core.materialize import ReferenceGenomeMaterializer
from evolution.core.operations import ReferenceCrossoverOperator, ReferenceMutationOperator
from evolution.core.genome import DecisionSpace


def _revision(statement: str = "authenticate users") -> ISRRevision:
    requirement = RequirementNode(
        id="req-auth",
        kind=RequirementKind.FUNCTIONAL,
        statement=statement,
        priority=Priority.MUST,
        acceptance_criteria=["valid credentials create a session"],
        source_refs=["spec:auth#1"],
    )
    graph = RequirementGraph(schema_version="1.0", nodes={requirement.id: requirement})
    genesis = ReferenceDeterministicMapper().map(graph, "map-1.0")
    return ISRRevision.create(
        system_id="semantic-preservation-test",
        revision_id="rev0",
        schema_version="1.0",
        graph=genesis.graph,
        provenance=Provenance(
            requirement_refs=[requirement.id],
            derivation_refs=["genesis:map-1.0"],
            created_by="test",
            created_at="2026-01-01T00:00:00Z",
        ),
    )


def test_requirement_semantics_survive_genome_and_isr_materialization() -> None:
    rev0 = _revision()
    genome = ReferenceGenomeConstructor().construct(rev0)
    mutated = ReferenceMutationOperator().mutate(genome, 0.0, DecisionSpace())
    materialized = ReferenceGenomeMaterializer().materialize(mutated)

    ref = materialized.nodes["requirement_ref:req-auth"]
    assert ref.properties["semantic_content"] == "authenticate users"
    assert ref.properties["acceptance_criteria"] == ["valid credentials create a session"]
    assert ref.properties["source_refs"] == ["spec:auth#1"]
    edge = materialized.edges["satisfies:req-auth"]
    assert edge.source_id == "capability:req-auth"
    assert edge.target_id == "requirement_ref:req-auth"


def test_crossover_preserves_shared_source_semantic_substrate() -> None:
    genome = ReferenceGenomeConstructor().construct(_revision())
    child = ReferenceCrossoverOperator().crossover(genome, genome)
    materialized = ReferenceGenomeMaterializer().materialize(child)
    assert "requirement_ref:req-auth" in materialized.nodes
    assert "satisfies:req-auth" in materialized.edges


def test_crossover_rejects_different_source_semantic_substrates() -> None:
    left = ReferenceGenomeConstructor().construct(_revision("authenticate users"))
    right = ReferenceGenomeConstructor().construct(_revision("delete users"))
    try:
        ReferenceCrossoverOperator().crossover(left, right)
    except ValueError as exc:
        assert "different source ISR semantic substrates" in str(exc)
    else:
        raise AssertionError("crossover silently combined different authoritative sources")
