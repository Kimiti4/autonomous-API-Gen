"""Genome projection unit tests (pure functions)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.backend.domain import (
    EpistemicStatus, EventCategory, new_event)
from observatory.backend.projections_genomes import (
    build_genome_chromosomes,
    build_genome_detail,
    build_genome_genes,
    build_genomes_overview,
    chromosome_sort_key,
    derive_genome_status,
    derive_pareto_state,
    extract_chromosome,
    extract_gene_id,
    extract_genome_id,
)


def _event(**overrides):
    base = {"category": EventCategory.EVOLUTION, "source": "test",
            "type": "genome_defined", "subject_id": "GEN-1",
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    base.update(overrides)
    return new_event(**base)


class Extraction(unittest.TestCase):
    def test_payload_keys_win(self):
        event = _event(subject_id="OTHER",
                       payload={"candidate_genome_id": "GEN-9"})
        self.assertEqual(extract_genome_id(event), "GEN-9")

    def test_type_prefix(self):
        event = _event(type="mutation_recorded", subject_id="whatever")
        self.assertEqual(extract_genome_id(event), "whatever")

    def test_gene_prefix_subjects(self):
        self.assertEqual(extract_genome_id(_event(subject_id="CAND-1")),
                         "CAND-1")
        self.assertIsNone(extract_genome_id(
            _event(type="process_started", subject_id="PROC-1")))

    def test_gene_extraction(self):
        self.assertEqual(
            extract_gene_id(_event(subject_id="GENE-X",
                                   payload={"genome_id": "GEN-1"})),
            "GENE-X")
        self.assertEqual(
            extract_gene_id(_event(type="gene_defined",
                                   subject_id="GENE-Y")),
            "GENE-Y")
        self.assertIsNone(extract_gene_id(_event()))

    def test_chromosome_extraction(self):
        self.assertEqual(
            extract_chromosome(_event(payload={"family": "Security"})),
            "Security")
        self.assertIsNone(extract_chromosome(_event()))

    def test_chromosome_ordering(self):
        self.assertLess(chromosome_sort_key("Security"),
                        chromosome_sort_key("Custom Family"))
        self.assertLess(chromosome_sort_key("Architecture"),
                        chromosome_sort_key("Security"))


class StatusDerivation(unittest.TestCase):
    def test_explicit_status_wins(self):
        events = [_event(payload={"status": "custom"})]
        self.assertEqual(derive_genome_status(events), "custom")

    def test_lifecycle_order(self):
        self.assertEqual(
            derive_genome_status([_event(type="gene_mutated")]), "mutated")
        self.assertEqual(
            derive_genome_status([_event(type="gene_crossover")]),
            "crossed_over")
        self.assertEqual(
            derive_genome_status(
                [_event(type="candidate_selected")]), "selected")

    def test_rejection_never_defaults_selected(self):
        # candidate_rejected without an outcome payload must not read as
        # "selected": rejection membership decides, not outcome parsing.
        events = [_event(type="candidate_rejected")]
        self.assertEqual(derive_genome_status(events), "rejected")

    def test_empty_unknown(self):
        # F-003 (D36 T4): absence yields "unknown", sibling-consistent with
        # experiments/fitness projections. Never "observed".
        self.assertEqual(derive_genome_status([]), "unknown")

    def test_pareto_unknown_unless_recorded(self):
        self.assertEqual(derive_pareto_state([]), "unknown")
        self.assertEqual(derive_pareto_state([_event()]), "unknown")
        self.assertEqual(
            derive_pareto_state(
                [_event(type="pareto_observed",
                        payload={"pareto_status": "non_dominated"})]),
            "non_dominated")


class GenesChromosomes(unittest.TestCase):
    def _events(self):
        return [
            _event(type="gene_defined", subject_id="GENE-ENGINE",
                   payload={"genome_id": "GEN-1", "gene_id": "GENE-ENGINE",
                            "chromosome": "Persistence", "value": "sqlite"}),
            _event(type="gene_mutated", subject_id="GENE-ENGINE",
                   payload={"genome_id": "GEN-1", "gene_id": "GENE-ENGINE",
                            "chromosome": "Persistence",
                            "previous_value": "sqlite",
                            "new_value": "postgresql",
                            "reason": "Durability review."}),
            _event(type="gene_defined", subject_id="GENE-UI",
                   payload={"genome_id": "GEN-1", "gene_id": "GENE-UI",
                            "chromosome": "Custom Shell", "value": "v1"}),
        ]

    def test_gene_history(self):
        genes = {gene["gene_id"]: gene
                 for gene in build_genome_genes(self._events())}
        engine = genes["GENE-ENGINE"]
        self.assertEqual(engine["value"], "postgresql")
        self.assertEqual(engine["previous_value"], "sqlite")
        self.assertEqual(engine["status"], "mutated")
        self.assertEqual(engine["mutation_count"], 1)
        self.assertEqual(genes["GENE-UI"]["status"], "defined")

    def test_chromosome_ordering_custom_last(self):
        chromosomes = build_genome_chromosomes(self._events())
        names = [chromosome["name"] for chromosome in chromosomes]
        self.assertEqual(names, ["Persistence", "Custom Shell"])
        persistence = chromosomes[0]
        self.assertEqual(persistence["gene_count"], 1)
        self.assertEqual(persistence["mutation_count"], 1)


class OverviewDetail(unittest.TestCase):
    def _lifecycle(self):
        return [
            _event(payload={"genome_id": "GEN-1",
                            "candidate_id": "vs1-obj001-candidate-313b071dd7d4",
                            "generation": 1,
                            "objective": "Priority capability.",
                            "summary": "Genome defined"}),
            _event(type="gene_defined", subject_id="GENE-ENGINE",
                   payload={"genome_id": "GEN-1", "gene_id": "GENE-ENGINE",
                            "chromosome": "Persistence", "value": "sqlite"}),
            _event(type="selection_recorded", subject_id="GEN-1",
                   payload={"genome_id": "GEN-1",
                            "candidate_id": "vs1-obj001-candidate-313b071dd7d4",
                            "outcome": "selected"}),
        ]

    def test_overview_empty(self):
        self.assertEqual(build_genomes_overview([]), [])

    def test_overview_populated(self):
        overview = build_genomes_overview(self._lifecycle())
        self.assertEqual(len(overview), 1)
        item = overview[0]
        self.assertEqual(item["genome_id"], "GEN-1")
        self.assertEqual(item["status"], "selected")
        self.assertEqual(item["gene_count"], 1)
        self.assertEqual(item["selection_count"], 1)
        self.assertEqual(item["pareto_state"], "unknown")

    def test_detail_sections(self):
        detail = build_genome_detail("GEN-1", self._lifecycle())
        assert detail is not None
        self.assertEqual(
            detail["candidate_id"], "vs1-obj001-candidate-313b071dd7d4")
        self.assertEqual(len(detail["genes"]), 1)
        self.assertEqual(len(detail["chromosomes"]), 1)
        self.assertEqual(len(detail["selections"]), 1)
        self.assertEqual(detail["selections"][0]["outcome"], "selected")
        self.assertEqual(detail["mutations"], [])
        self.assertEqual(detail["unknowns"], [])
        self.assertEqual(len(detail["timeline"]), 3)

    def test_detail_missing_none(self):
        self.assertIsNone(build_genome_detail("GEN-nope", self._lifecycle()))

    def test_rejected_renders(self):
        events = self._lifecycle() + [_event(type="genome_rejected")]
        detail = build_genome_detail("GEN-1", events)
        assert detail is not None
        self.assertEqual(detail["status"], "rejected")


class AbsenceDefaultsUnknown(unittest.TestCase):
    """F-003 (D36 T4): absence yields "unknown" at genome, gene, and
    chromosome level — sibling-consistent with experiments/fitness."""

    def _bare_gene_events(self):
        # "note_recorded" belongs to no lifecycle set: a gene the system has
        # seen but never classified. Absence of outcome evidence.
        return [_event(type="note_recorded", subject_id="GENE-X",
                       payload={"genome_id": "GEN-1", "gene_id": "GENE-X",
                                "chromosome": "Persistence"})]

    def test_genome_fallthrough_unknown(self):
        self.assertEqual(
            derive_genome_status(self._bare_gene_events()), "unknown")

    def test_gene_fallthrough_unknown(self):
        genes = build_genome_genes(self._bare_gene_events())
        self.assertEqual(len(genes), 1)
        self.assertEqual(genes[0]["status"], "unknown")

    def test_chromosome_fallthrough_unknown(self):
        chromosomes = build_genome_chromosomes(self._bare_gene_events())
        self.assertEqual(len(chromosomes), 1)
        self.assertEqual(chromosomes[0]["status"], "unknown")

    def test_explicit_status_still_wins(self):
        events = [_event(type="genome_defined", subject_id="GENE-X",
                         payload={"genome_id": "GEN-1", "gene_id": "GENE-X",
                                  "chromosome": "Persistence",
                                  "status": "quarantined"})]
        genes = build_genome_genes(events)
        self.assertEqual(genes[0]["status"], "quarantined")

    def test_lifecycle_statuses_unchanged(self):
        # Rejection/selection/mutation/crossover/proposal outcomes keep
        # their exact contracted values after the F-003 alignment.
        cases = [("candidate_rejected", "rejected"),
                 ("candidate_selected", "selected"),
                 ("gene_mutated", "mutated"),
                 ("gene_crossover", "crossed_over"),
                 ("genome_proposed", "proposed")]
        for event_type, expected in cases:
            with self.subTest(event_type=event_type):
                self.assertEqual(
                    derive_genome_status([_event(type=event_type)]), expected)


if __name__ == "__main__":
    unittest.main()
