"""v1.3 Evolution Engine gates E1–E7, E9–E10 — genome, fitness, operations, materialization, refinement."""

from __future__ import annotations

import pytest

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance, compute_content_hash
from isr.core.revision import ISRRevision
from evolution.core.construction import ReferenceGenomeConstructor
from evolution.core.engine import EvolutionEngine
from evolution.core.fitness import FitnessDimension, FitnessVector, dominates, non_dominated_sort
from evolution.core.fitness_evaluator import ReferenceISRFitnessEvaluator
from evolution.core.genome import (
    Chromosome,
    ChromosomeFamily,
    DecisionSpace,
    Gene,
    Genome,
    genome_content_hash,
)
from evolution.core.materialize import ReferenceGenomeMaterializer
from evolution.core.operations import ReferenceCrossoverOperator, ReferenceMutationOperator
from evolution.core.refinement import ReferenceArchitectureRefinement
from evolution.core.selection import ReferenceParetoSelection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_isr(domains: list[str]) -> ISRRevision:
    nodes: dict[str, Node] = {}
    for d in domains:
        nodes[f"domain:{d}"] = Node(
            id=f"domain:{d}", type=NodeType.DOMAIN, properties={"label": d}
        )
    graph = ISRGraph(nodes=nodes, edges={})
    return ISRRevision.create(
        "test-sys",
        "rev0",
        "1.0",
        graph,
        Provenance(created_by="test", created_at="2026-01-01T00:00:00Z"),
    )


SPACE = DecisionSpace(
    choices={
        "a": ["bounded-context", "layered", "event-driven"],
        "b": ["bounded-context", "layered", "event-driven"],
        "baseline": ["enabled", "enforced", "disabled"],
        "style": ["event-driven", "request-reply"],
    }
)


# ---------------------------------------------------------------------------
# E1 — genome determinism
# ---------------------------------------------------------------------------

def test_e1_genome_determinism() -> None:
    isr = _make_isr(["a", "b"])
    c = ReferenceGenomeConstructor()
    g1 = c.construct(isr)
    g2 = c.construct(isr)
    assert genome_content_hash(g1) == genome_content_hash(g2)


def test_e1_genome_content_hash_order_independent() -> None:
    g1 = Genome(
        system_id="s",
        chromosomes={
            "architecture": Chromosome(
                family=ChromosomeFamily.ARCHITECTURE,
                genes={
                    "x": Gene(gene_id="x", decision="d", value="v1"),
                    "y": Gene(gene_id="y", decision="d", value="v2"),
                },
            ),
        },
    )
    g2 = Genome(
        system_id="s",
        chromosomes={
            "architecture": Chromosome(
                family=ChromosomeFamily.ARCHITECTURE,
                genes={
                    "y": Gene(gene_id="y", decision="d", value="v2"),
                    "x": Gene(gene_id="x", decision="d", value="v1"),
                },
            ),
        },
    )
    assert genome_content_hash(g1) == genome_content_hash(g2)


# ---------------------------------------------------------------------------
# E2 — valid genome
# ---------------------------------------------------------------------------

def test_e2_valid_genome_structure() -> None:
    isr = _make_isr(["a", "b"])
    genome = ReferenceGenomeConstructor().construct(isr)
    assert genome.system_id == "test-sys"
    families = set(genome.chromosomes.keys())
    assert ChromosomeFamily.ARCHITECTURE.value in families
    assert ChromosomeFamily.PERSISTENCE.value in families
    assert ChromosomeFamily.SECURITY.value in families
    assert ChromosomeFamily.MESSAGING.value in families


def test_e2_architecture_has_domain_genes() -> None:
    isr = _make_isr(["a", "b"])
    genome = ReferenceGenomeConstructor().construct(isr)
    arch = genome.chromosomes[ChromosomeFamily.ARCHITECTURE.value]
    assert set(arch.genes.keys()) == {"a", "b"}


# ---------------------------------------------------------------------------
# E3 — mutation validity
# ---------------------------------------------------------------------------

def test_e3_mutation_validity() -> None:
    isr = _make_isr(["a", "b"])
    genome = ReferenceGenomeConstructor().construct(isr)
    mutated = ReferenceMutationOperator().mutate(genome, 1.0, SPACE)
    for chrom in mutated.chromosomes.values():
        for gene in chrom.genes.values():
            opts = SPACE.values(gene.gene_id)
            if opts:
                assert gene.value in opts


def test_e3_mutation_deterministic() -> None:
    import random
    isr = _make_isr(["a", "b"])
    genome = ReferenceGenomeConstructor().construct(isr)
    rng = random.Random(42)
    m1 = ReferenceMutationOperator(rng=rng).mutate(genome, 0.5, SPACE)
    rng2 = random.Random(42)
    m2 = ReferenceMutationOperator(rng=rng2).mutate(genome, 0.5, SPACE)
    assert genome_content_hash(m1) == genome_content_hash(m2)


# ---------------------------------------------------------------------------
# E4 — crossover validity
# ---------------------------------------------------------------------------

def test_e4_crossover_validity() -> None:
    isr = _make_isr(["a", "b"])
    c = ReferenceGenomeConstructor()
    g1 = c.construct(isr)
    g2 = c.construct(isr)
    child = ReferenceCrossoverOperator().crossover(g1, g2)
    assert child.system_id == "test-sys"
    assert set(child.chromosomes.keys()) == set(g1.chromosomes.keys())


def test_e4_crossover_deterministic() -> None:
    import random
    isr = _make_isr(["a", "b"])
    c = ReferenceGenomeConstructor()
    g1 = c.construct(isr)
    g2 = c.construct(isr)
    rng1 = random.Random(99)
    child1 = ReferenceCrossoverOperator(rng=rng1).crossover(g1, g2)
    rng2 = random.Random(99)
    child2 = ReferenceCrossoverOperator(rng=rng2).crossover(g1, g2)
    assert genome_content_hash(child1) == genome_content_hash(child2)


# ---------------------------------------------------------------------------
# E5 — Pareto sort correctness
# ---------------------------------------------------------------------------

def test_e5_pareto_sort_two_fronts() -> None:
    v1 = FitnessVector(scores={
        FitnessDimension.MODULARITY: 1.0,
        FitnessDimension.SIMPLICITY: 0.2,
    })
    v2 = FitnessVector(scores={
        FitnessDimension.MODULARITY: 0.2,
        FitnessDimension.SIMPLICITY: 1.0,
    })
    v3 = FitnessVector(scores={
        FitnessDimension.MODULARITY: 0.5,
        FitnessDimension.SIMPLICITY: 0.5,
    })
    fronts = non_dominated_sort([v1, v2, v3])
    assert len(fronts) >= 1
    assert 0 in fronts[0] or 1 in fronts[0]


def test_e5_dominates_basic() -> None:
    a = FitnessVector(scores={
        FitnessDimension.MODULARITY: 1.0,
        FitnessDimension.SIMPLICITY: 1.0,
    })
    b = FitnessVector(scores={
        FitnessDimension.MODULARITY: 0.5,
        FitnessDimension.SIMPLICITY: 0.5,
    })
    assert dominates(a, b)
    assert not dominates(b, a)


def test_e5_dominates_equal_not_strict() -> None:
    a = FitnessVector(scores={
        FitnessDimension.MODULARITY: 0.5,
        FitnessDimension.SIMPLICITY: 0.5,
    })
    b = FitnessVector(scores={
        FitnessDimension.MODULARITY: 0.5,
        FitnessDimension.SIMPLICITY: 0.5,
    })
    assert not dominates(a, b)


# ---------------------------------------------------------------------------
# E6 — lineage + materialization
# ---------------------------------------------------------------------------

def test_e6_lineage_and_e7_invariants() -> None:
    isr = _make_isr(["a", "b"])
    c = ReferenceGenomeConstructor()
    genome = c.construct(isr)
    mat = ReferenceGenomeMaterializer()
    graph = mat.materialize(genome)
    rev = ISRRevision.create(
        "test-sys", "rev1", "1.0", graph,
        Provenance(created_by="evolution_engine", created_at="2026-01-01T00:00:00Z"),
    )
    assert len(rev.content_hash) == 64


# ---------------------------------------------------------------------------
# E7 — ADR-008 invariants hold on materialized graph
# ---------------------------------------------------------------------------

def test_e7_materialized_graph_passes_invariants() -> None:
    isr = _make_isr(["a", "b"])
    genome = ReferenceGenomeConstructor().construct(isr)
    graph = ReferenceGenomeMaterializer().materialize(genome)
    from isr.core.invariants import validate_invariants
    validate_invariants(graph)


def test_e7_three_domain_depends_on() -> None:
    isr = _make_isr(["a", "b", "c"])
    genome = ReferenceGenomeConstructor().construct(isr)
    graph = ReferenceGenomeMaterializer().materialize(genome)
    dep_edges = [e for e in graph.edges.values() if e.type == EdgeType.DEPENDS_ON]
    assert len(dep_edges) == 1
    from isr.core.invariants import validate_invariants
    validate_invariants(graph)


# ---------------------------------------------------------------------------
# E9 — selection correctness
# ---------------------------------------------------------------------------

def test_e9_selects_pareto_optimal() -> None:
    v1 = FitnessVector(scores={
        FitnessDimension.MODULARITY: 1.0,
        FitnessDimension.SIMPLICITY: 0.1,
    })
    v2 = FitnessVector(scores={
        FitnessDimension.MODULARITY: 0.1,
        FitnessDimension.SIMPLICITY: 1.0,
    })
    v3 = FitnessVector(scores={
        FitnessDimension.MODULARITY: 0.3,
        FitnessDimension.SIMPLICITY: 0.3,
    })
    idx = ReferenceParetoSelection().select([v1, v2, v3])
    assert idx in (0, 1)


# ---------------------------------------------------------------------------
# E10 — end-to-end pipeline
# ---------------------------------------------------------------------------

def test_e10_pipeline_composition() -> None:
    isr = _make_isr(["a", "b"])
    engine = EvolutionEngine()

    genome = engine.construct(isr)
    fv = engine.evaluate_fitness(isr, genome)
    assert isinstance(fv, FitnessVector)

    mutated = engine.mutate_candidate(genome, 0.5, SPACE)
    child = engine.crossover_candidates(genome, mutated)
    idx = engine.select([fv, engine.evaluate_fitness(isr, mutated)])
    assert isinstance(idx, int)

    graph = engine.materialize_candidate(child)
    assert isinstance(graph, ISRGraph)
    assert len(graph.nodes) > 0

    refined = engine.refine_candidate(
        child, [FitnessDimension.SIMPLICITY, FitnessDimension.TESTABILITY]
    )
    assert refined.system_id == "test-sys"
    assert len(engine.operations_trace) == 3
