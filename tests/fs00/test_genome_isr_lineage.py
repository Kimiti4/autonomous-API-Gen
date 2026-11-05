import random

import pytest

from evolution.core.construction import ReferenceGenomeConstructor
from evolution.core.genome import DecisionSpace, Genome, genome_content_hash
from evolution.core.operations import ReferenceCrossoverOperator, ReferenceMutationOperator
from evolution.core.refinement import ReferenceArchitectureRefinement
from evolution.core.fitness import FitnessDimension
from isr.core.graph import ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _revision(created_by: str = "source-a") -> ISRRevision:
    graph = ISRGraph(
        nodes={
            "domain:payroll": Node(
                id="domain:payroll",
                type=NodeType.DOMAIN,
                properties={"label": "Payroll"},
            )
        },
        edges={},
    )
    return ISRRevision.create(
        system_id="payroll",
        revision_id=f"revision-{created_by}",
        schema_version="2.0",
        graph=graph,
        provenance=Provenance(
            created_by=created_by,
            created_at="2026-11-05T00:00:00Z",
        ),
    )


def test_genome_binds_both_semantic_and_exact_isr_revision_identity():
    revision = _revision()
    genome = ReferenceGenomeConstructor().construct(revision)
    assert genome.source_isr_revision_id == revision.revision_id
    assert genome.source_isr_schema_version == revision.schema_version
    assert genome.source_isr_content_hash == revision.content_hash
    assert genome.source_isr_revision_hash == revision.revision_hash


def test_genome_hash_changes_when_only_isr_revision_provenance_changes():
    first = ReferenceGenomeConstructor().construct(_revision("source-a"))
    second = ReferenceGenomeConstructor().construct(_revision("source-b"))
    assert first.source_isr_content_hash == second.source_isr_content_hash
    assert first.source_isr_revision_hash != second.source_isr_revision_hash
    assert genome_content_hash(first) != genome_content_hash(second)


def test_evolution_operators_preserve_exact_isr_revision_binding():
    revision = _revision()
    genome = ReferenceGenomeConstructor().construct(revision)
    mutated = ReferenceMutationOperator(random.Random(1)).mutate(
        genome,
        mutation_rate=1.0,
        space=DecisionSpace(choices={"payroll": ["bounded-context", "domain-driven"]}),
    )
    refined = ReferenceArchitectureRefinement().refine(
        genome, [FitnessDimension.MODULARITY]
    )
    crossed = ReferenceCrossoverOperator(random.Random(2)).crossover(genome, genome)

    for child in (mutated, refined, crossed):
        assert child.source_isr_revision_id == revision.revision_id
        assert child.source_isr_content_hash == revision.content_hash
        assert child.source_isr_revision_hash == revision.revision_hash
        assert child.source_graph == genome.source_graph


def test_crossover_rejects_same_graph_with_different_revision_envelopes():
    left = ReferenceGenomeConstructor().construct(_revision("source-a"))
    right = ReferenceGenomeConstructor().construct(_revision("source-b"))
    assert left.source_graph == right.source_graph
    with pytest.raises(ValueError, match="different source ISR revision identities"):
        ReferenceCrossoverOperator(random.Random(3)).crossover(left, right)


def test_isr_derived_genome_cannot_omit_or_forge_source_identity():
    revision = _revision()
    source_graph = revision.graph.model_dump(mode="json")
    with pytest.raises(ValueError, match="complete source ISR revision identity"):
        Genome(system_id="payroll", source_graph=source_graph)

    with pytest.raises(ValueError, match="content hash"):
        Genome(
            system_id="payroll",
            source_graph=source_graph,
            source_isr_revision_id=revision.revision_id,
            source_isr_schema_version=revision.schema_version,
            source_isr_content_hash="0" * 64,
            source_isr_revision_hash=revision.revision_hash,
            source_isr_provenance={
                **revision.provenance.model_dump(mode="json"),
                "created_by": "forged-source",
            },
        )


def test_genome_rejects_forged_provenance_even_when_revision_hash_is_well_formed():
    revision = _revision()
    with pytest.raises(ValueError, match="revision hash"):
        Genome(
            system_id=revision.system_id,
            source_graph=revision.graph.model_dump(mode="json"),
            source_isr_revision_id=revision.revision_id,
            source_isr_schema_version=revision.schema_version,
            source_isr_content_hash=revision.content_hash,
            source_isr_revision_hash=revision.revision_hash,
            source_isr_provenance={
                **revision.provenance.model_dump(mode="json"),
                "created_by": "forged",
            },
        )
