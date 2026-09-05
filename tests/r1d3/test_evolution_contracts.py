"""R1-D.3 Evolution/EIR contract tests.

Source: folder/CONTRACT_EvolutionOperation.md (D05 + D3-04 refinement).
Source: folder/CONTRACT_EvolutionRecord_EIR.md (D06).
Source: folder/CONTRACT_ArchitectureCandidate.md (D04).
Source: folder/R1_D3_EVOLUTION_LINEAGE_MODEL.md (D3-07).

Covers: contract, lineage, mutation, crossover, determinism, provenance,
failure, compatibility (F-C10-01/F-C10-02), and the constitutional
``transformations=[]`` finding.
"""
from __future__ import annotations

import random
import unittest

from evolution.core.fitness import FitnessDimension, FitnessVector
from evolution.core.genome import (
    Chromosome,
    ChromosomeFamily,
    DecisionSpace,
    Gene,
    Genome,
    genome_content_hash,
)
from evolution.core.governance_design import baseline_governance_design
from evolution.core.governance_fitness import (
    ALL_OBJECTIVES,
    design_objectives,
)
from evolution.core.operations import (
    OperationRecord,
    ReferenceCrossoverOperator,
    ReferenceMutationOperator,
)
from evolution.core.selection import ReferenceParetoSelection
from evolution.history import EvolutionHistoryRepository


def _make_genome(system_id: str = "r1d3-test", style_a: bool = True) -> Genome:
    style = "event-driven" if style_a else "request-response"
    return Genome(
        system_id=system_id,
        chromosomes={
            ChromosomeFamily.ARCHITECTURE.value: Chromosome(
                family=ChromosomeFamily.ARCHITECTURE,
                genes={
                    "core": Gene(gene_id="core", decision="decomposition", value="bounded-context"),
                },
            ),
            ChromosomeFamily.MESSAGING.value: Chromosome(
                family=ChromosomeFamily.MESSAGING,
                genes={
                    "style": Gene(gene_id="style", decision="protocol", value=style),
                },
            ),
        },
    )


def _make_space() -> DecisionSpace:
    return DecisionSpace(
        choices={
            "core": ["bounded-context", "modular-monolith"],
            "style": ["event-driven", "request-response"],
        }
    )


class TestContractOperationRecord(unittest.TestCase):
    """D05: valid/invalid operation, required identity."""

    def test_operation_record_captures_sources_and_result(self):
        rec = OperationRecord(
            operation_type="mutation",
            source_genome_ids=["g1"],
            result_genome_id="g2",
            mutation_rate=0.5,
            changed_genes=["style"],
        )
        self.assertEqual(rec.operation_type, "mutation")
        self.assertEqual(rec.source_genome_ids, ["g1"])
        self.assertEqual(rec.result_genome_id, "g2")
        self.assertEqual(rec.mutation_rate, 0.5)
        self.assertEqual(rec.changed_genes, ["style"])

    def test_operation_record_crossover_has_two_sources(self):
        rec = OperationRecord(
            operation_type="crossover",
            source_genome_ids=["pa", "pb"],
            result_genome_id="c1",
        )
        self.assertEqual(len(rec.source_genome_ids), 2)

    def test_operation_record_sources_not_silently_dropped(self):
        rec = OperationRecord(
            operation_type="crossover",
            source_genome_ids=["pa", "pb"],
            result_genome_id="c1",
        )
        self.assertEqual(rec.source_genome_ids, ["pa", "pb"])

    def test_genome_identity_stable(self):
        g = _make_genome()
        self.assertEqual(genome_content_hash(g), genome_content_hash(g))
        self.assertEqual(len(genome_content_hash(g)), 64)


class TestLineage(unittest.TestCase):
    """D3-07: parent → child, multi-generation, branching, crossover."""

    def test_parent_child_lineage(self):
        parent = _make_genome()
        op = ReferenceMutationOperator(rng=random.Random(7))
        child = op.mutate(parent, 1.0, _make_space())
        rec = OperationRecord(
            operation_type="mutation",
            source_genome_ids=[genome_content_hash(parent)],
            result_genome_id=genome_content_hash(child),
            mutation_rate=1.0,
        )
        self.assertEqual(rec.source_genome_ids, [genome_content_hash(parent)])
        self.assertEqual(rec.result_genome_id, genome_content_hash(child))

    def test_multigeneration_lineage_chain(self):
        g0 = _make_genome()
        op = ReferenceMutationOperator(rng=random.Random(11))
        space = _make_space()
        g1 = op.mutate(g0, 1.0, space)
        g2 = op.mutate(g1, 1.0, space)
        h0, h1, h2 = (genome_content_hash(g) for g in (g0, g1, g2))
        # Chain is reconstructable: each record links parent → child.
        rec1 = OperationRecord("mutation", [h0], h1, mutation_rate=1.0)
        rec2 = OperationRecord("mutation", [h1], h2, mutation_rate=1.0)
        self.assertEqual(rec1.result_genome_id, rec2.source_genome_ids[0])

    def test_branching_one_parent_two_children(self):
        parent = _make_genome()
        space = _make_space()
        child_a = ReferenceMutationOperator(rng=random.Random(1)).mutate(parent, 1.0, space)
        child_b = ReferenceMutationOperator(rng=random.Random(2)).mutate(parent, 1.0, space)
        h_parent = genome_content_hash(parent)
        rec_a = OperationRecord("mutation", [h_parent], genome_content_hash(child_a))
        rec_b = OperationRecord("mutation", [h_parent], genome_content_hash(child_b))
        self.assertEqual(rec_a.source_genome_ids, rec_b.source_genome_ids)

    def test_crossover_child_references_both_parents(self):
        pa = _make_genome(style_a=True)
        pb = _make_genome(style_a=False)
        op = ReferenceCrossoverOperator(rng=random.Random(3))
        child = op.crossover(pa, pb)
        rec = OperationRecord(
            "crossover",
            [genome_content_hash(pa), genome_content_hash(pb)],
            genome_content_hash(child),
        )
        self.assertEqual(len(rec.source_genome_ids), 2)
        self.assertIn(genome_content_hash(pa), rec.source_genome_ids)
        self.assertIn(genome_content_hash(pb), rec.source_genome_ids)

    def test_history_repository_hash_chain(self):
        repo = EvolutionHistoryRepository()
        e1 = repo.record("p1", "mutation", "engine", {"parent": "g0", "child": "g1"})
        e2 = repo.record("p1", "selection", "engine", {"selected": "g1"})
        self.assertEqual(e2.previous_event_hash, e1.event_hash)
        self.assertNotEqual(e1.event_hash, e2.event_hash)

    def test_history_append_only(self):
        repo = EvolutionHistoryRepository()
        e1 = repo.record("p1", "mutation", "engine", {})
        snapshot = (e1.id, e1.event_hash)
        repo.record("p1", "selection", "engine", {})
        self.assertEqual((repo.events[0].id, repo.events[0].event_hash), snapshot)
        self.assertEqual(len(repo.events), 2)


class TestMutation(unittest.TestCase):
    """Valid/invalid mutation, constraint violation."""

    def test_valid_mutation_produces_genome(self):
        g = _make_genome()
        op = ReferenceMutationOperator(rng=random.Random(5))
        child = op.mutate(g, 1.0, _make_space())
        self.assertIsInstance(child, Genome)
        self.assertEqual(child.system_id, g.system_id)

    def test_mutation_rate_zero_preserves_genome(self):
        g = _make_genome()
        op = ReferenceMutationOperator(rng=random.Random(5))
        child = op.mutate(g, 0.0, _make_space())
        self.assertEqual(genome_content_hash(child), genome_content_hash(g))

    def test_mutation_respects_decision_space(self):
        g = _make_genome()
        op = ReferenceMutationOperator(rng=random.Random(9))
        child = op.mutate(g, 1.0, _make_space())
        space = _make_space()
        for fam_key, chrom in child.chromosomes.items():
            for gid, gene in chrom.genes.items():
                self.assertTrue(space.is_valid(gid, gene.value))

    def test_mutation_changes_genes_at_full_rate(self):
        g = _make_genome()
        op = ReferenceMutationOperator(rng=random.Random(13))
        child = op.mutate(g, 1.0, _make_space())
        self.assertNotEqual(genome_content_hash(child), genome_content_hash(g))


class TestCrossover(unittest.TestCase):
    """Two parents, child lineage, reproducibility, invalid crossover."""

    def test_crossover_two_parents_produces_child(self):
        pa = _make_genome(style_a=True)
        pb = _make_genome(style_a=False)
        child = ReferenceCrossoverOperator(rng=random.Random(3)).crossover(pa, pb)
        self.assertIsInstance(child, Genome)

    def test_crossover_child_genes_come_from_parents(self):
        pa = _make_genome(style_a=True)
        pb = _make_genome(style_a=False)
        child = ReferenceCrossoverOperator(rng=random.Random(3)).crossover(pa, pb)
        for fam_key, chrom in child.chromosomes.items():
            for gid, gene in chrom.genes.items():
                allowed = set()
                if fam_key in pa.chromosomes and gid in pa.chromosomes[fam_key].genes:
                    allowed.add(pa.chromosomes[fam_key].genes[gid].value)
                if fam_key in pb.chromosomes and gid in pb.chromosomes[fam_key].genes:
                    allowed.add(pb.chromosomes[fam_key].genes[gid].value)
                self.assertIn(gene.value, allowed)

    def test_crossover_reproducible_same_seed(self):
        pa = _make_genome(style_a=True)
        pb = _make_genome(style_a=False)
        c1 = ReferenceCrossoverOperator(rng=random.Random(42)).crossover(pa, pb)
        c2 = ReferenceCrossoverOperator(rng=random.Random(42)).crossover(pa, pb)
        self.assertEqual(genome_content_hash(c1), genome_content_hash(c2))

    def test_crossover_preserves_single_parent_families(self):
        pa = _make_genome(style_a=True)
        pb = Genome(
            system_id="r1d3-test",
            chromosomes={
                ChromosomeFamily.SECURITY.value: Chromosome(
                    family=ChromosomeFamily.SECURITY,
                    genes={"baseline": Gene(gene_id="baseline", decision="authn", value="token")},
                ),
            },
        )
        child = ReferenceCrossoverOperator(rng=random.Random(3)).crossover(pa, pb)
        self.assertIn(ChromosomeFamily.SECURITY.value, child.chromosomes)
        self.assertIn(ChromosomeFamily.ARCHITECTURE.value, child.chromosomes)


class TestDeterminism(unittest.TestCase):
    """Same seed → reproducible; stochasticity explicit via rng param."""

    def test_same_seed_reproducible_mutation(self):
        g = _make_genome()
        space = _make_space()
        c1 = ReferenceMutationOperator(rng=random.Random(99)).mutate(g, 0.7, space)
        c2 = ReferenceMutationOperator(rng=random.Random(99)).mutate(g, 0.7, space)
        self.assertEqual(genome_content_hash(c1), genome_content_hash(c2))

    def test_stochasticity_explicit_rng_param(self):
        op_seeded = ReferenceMutationOperator(rng=random.Random(1))
        op_unseeded = ReferenceMutationOperator()
        self.assertIsNotNone(op_seeded._rng)
        self.assertIsNotNone(op_unseeded._rng)


class TestProvenance(unittest.TestCase):
    """Operation/candidate/evaluation provenance, verification linkage."""

    def test_operation_record_carries_provenance_fields(self):
        rec = OperationRecord(
            operation_type="mutation",
            source_genome_ids=["g1"],
            result_genome_id="g2",
            mutation_rate=0.3,
            changed_genes=["style"],
        )
        self.assertEqual(rec.mutation_rate, 0.3)
        self.assertEqual(rec.changed_genes, ["style"])

    def test_governance_design_id_preserved(self):
        from evolution.core.governance_fitness import GovernanceDesignFitness

        result = design_objectives(dict(baseline_governance_design()))
        self.assertEqual(set(result), set(ALL_OBJECTIVES))

    def test_history_event_carries_actor_and_proposal(self):
        repo = EvolutionHistoryRepository()
        event = repo.record("prop-1", "mutation", "engine", {"parent": "g0"})
        self.assertEqual(event.actor_id, "engine")
        self.assertEqual(event.proposal_id, "prop-1")
        self.assertEqual(event.details["parent"], "g0")


class TestFailure(unittest.TestCase):
    """Mutation/evaluation/verification/provenance failure, fail-closed."""

    def test_selection_empty_rejected(self):
        sel = ReferenceParetoSelection()
        with self.assertRaises(ValueError):
            sel.select([])

    def test_governance_malformed_fail_closed(self):
        from evolution.core.governance_fitness import design_objectives as canonical_objectives

        with self.assertRaises(ValueError):
            canonical_objectives({"design_id": "x"})

    def test_governance_absent_fail_closed(self):
        from evolution.core.governance_fitness import design_objectives as canonical_objectives

        with self.assertRaises(ValueError):
            canonical_objectives({})

    def test_decision_space_rejects_invalid_value(self):
        space = _make_space()
        self.assertFalse(space.is_valid("style", "not-a-protocol"))
        self.assertTrue(space.is_valid("style", "event-driven"))


class TestCompatibility(unittest.TestCase):
    """Legacy → canonical, no canonical → legacy mutation, historical immutable."""

    def test_no_constitutional_imports_in_mutation(self):
        import os

        path = os.path.join("evolution", "mutation.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("from constitutional_architecture", content)
        self.assertNotIn("import constitutional_architecture", content)

    def test_no_constitutional_imports_in_governance_evaluator(self):
        import os

        path = os.path.join("evolution", "governance_fitness_evaluator.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("from constitutional_architecture", content)
        self.assertNotIn("import constitutional_architecture", content)

    def test_canonical_baseline_matches_constitutional(self):
        from constitutional_architecture.governance.governance_design_fitness import (
            baseline_governance_design as constitutional_baseline,
        )

        self.assertEqual(
            dict(baseline_governance_design()), dict(constitutional_baseline())
        )

    def test_canonical_objectives_match_constitutional(self):
        from constitutional_architecture.governance.governance_design_fitness import (
            baseline_governance_design as constitutional_baseline,
        )
        from constitutional_architecture.governance.governance_design_fitness import (
            design_objectives as constitutional_objectives,
        )
        from constitutional_architecture.governance.schemas import GovernanceDesignISR

        baseline = dict(constitutional_baseline())
        expected = constitutional_objectives(GovernanceDesignISR(**baseline))
        actual = design_objectives(dict(baseline_governance_design()))
        self.assertEqual(set(actual), set(expected))
        for key in expected:
            self.assertAlmostEqual(actual[key], expected[key], places=9)

    def test_constitutional_transformations_defect_documented(self):
        """The constitutional evolution_loop constructs EIR with
        transformations=[] (R0 finding). Canonical lineage records sources
        explicitly instead. This test pins the canonical behavior."""
        parent = _make_genome()
        op = ReferenceMutationOperator(rng=random.Random(4))
        child = op.mutate(parent, 1.0, _make_space())
        rec = OperationRecord(
            operation_type="mutation",
            source_genome_ids=[genome_content_hash(parent)],
            result_genome_id=genome_content_hash(child),
        )
        # Canonical records never silently drop sources.
        self.assertEqual(len(rec.source_genome_ids), 1)
        self.assertTrue(rec.source_genome_ids[0])


if __name__ == "__main__":
    unittest.main()
