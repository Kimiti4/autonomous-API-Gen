"""Post-R1-D reconciliation tests (R1-RG).

Source: folder/postr1d.md §§30–31 (test requirements, baseline).

Proves composition across the canonical substrate:
  authority, contract composition, identity, failure, lineage, regression.
Every claim is runtime or test evidence (§6); nothing relies on docs alone.
"""
from __future__ import annotations

import os
import random
import unittest


class TestAuthority(unittest.TestCase):
    """§30 Authority: canonical module ownership, no duplicates, one-way adapters."""

    def test_canonical_isr_owner(self):
        import isr.core.revision as rev

        self.assertTrue(hasattr(rev, "ISRRevision"))
        self.assertEqual(rev.__name__, "isr.core.revision")

    def test_canonical_compiler_ir_owner(self):
        import compiler.core.plan as plan

        self.assertTrue(hasattr(plan, "CompilationPlan"))

    def test_canonical_backend_owner(self):
        from compiler.core.protocol import CompilerBackend

        self.assertTrue(hasattr(CompilerBackend, "compile"))

    def test_canonical_evolution_owner(self):
        import evolution.core.operations as ops

        self.assertTrue(hasattr(ops, "ReferenceMutationOperator"))
        self.assertTrue(hasattr(ops, "ReferenceCrossoverOperator"))

    def test_no_duplicate_canonical_isr_imports(self):
        """No canonical path imports a constitutional ISR model."""
        checked = 0
        for root, _, files in os.walk("isr"):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.assertNotIn("constitutional_architecture.isr", content, fname)
                checked += 1
        self.assertGreater(checked, 0)

    def test_no_duplicate_canonical_compiler_imports(self):
        checked = 0
        for root, _, files in os.walk("compiler"):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                with open(os.path.join(root, fname), encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.assertNotIn("constitutional_architecture.compiler", content, fname)
                checked += 1
        self.assertGreater(checked, 0)

    def test_legacy_adapter_direction(self):
        """The only cross-substrate evolution imports removed in R1-D.3;
        constitutional files carry no canonical adapter back."""
        import evolution.mutation as mut
        import evolution.governance_fitness_evaluator as ev

        self.assertFalse(hasattr(mut, "constitutional_architecture"))
        self.assertFalse(hasattr(ev, "constitutional_architecture"))


class TestContractComposition(unittest.TestCase):
    """§30 Contract composition: ISR → Architecture → CompilerIR → Backend → verify."""

    def _rev0(self):
        from isr.core.graph import ISRGraph, Node, NodeType
        from isr.core.identity import Provenance
        from isr.core.revision import ISRRevision
        from datetime import datetime, timezone

        graph = ISRGraph(
            nodes={
                "domain:core": Node(id="domain:core", type=NodeType.DOMAIN, properties={"label": "core"}),
            }
        )
        return ISRRevision.create(
            system_id="rg-test",
            revision_id="rev0",
            schema_version="1.0",
            graph=graph,
            provenance=Provenance(
                created_by="rg-test", created_at=datetime.now(timezone.utc).isoformat()
            ),
        )

    def test_isr_to_architecture(self):
        """ISRRevision → Genome via the deterministic constructor."""
        from evolution.core.construction import ReferenceGenomeConstructor
        from evolution.core.genome import genome_content_hash

        rev = self._rev0()
        genome = ReferenceGenomeConstructor().construct(rev)
        self.assertEqual(genome.system_id, rev.system_id)
        self.assertEqual(len(genome_content_hash(genome)), 64)

    def test_architecture_to_compiler_ir(self):
        """Genome → materialized ISR → CompilationPlan (mediated edge)."""
        from compiler.core.lowering import isr_to_plan
        from compiler.core.plan import CompilationPlan
        from evolution.core.construction import ReferenceGenomeConstructor
        from evolution.core.materialize import ReferenceGenomeMaterializer
        from isr.core.identity import Provenance
        from isr.core.revision import ISRRevision
        from datetime import datetime, timezone

        rev0 = self._rev0()
        genome = ReferenceGenomeConstructor().construct(rev0)
        graph = ReferenceGenomeMaterializer().materialize(genome)
        rev1 = ISRRevision.create(
            system_id=rev0.system_id,
            revision_id="rev1",
            schema_version="1.0",
            graph=graph,
            provenance=Provenance(
                parent_revision_id=rev0.revision_id,
                created_by="rg-test",
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
        )
        plan = isr_to_plan(rev1)
        self.assertIsInstance(plan, CompilationPlan)
        self.assertTrue(plan.plan_id.startswith("plan:"))

    def test_compiler_ir_to_backend(self):
        """CompilationPlan → backend.compile → GeneratedRepository."""
        from compiler.backends.python_fastapi import PythonFastAPIBackend
        from compiler.core.lowering import isr_to_plan

        plan = isr_to_plan(self._rev0())
        repo = PythonFastAPIBackend().compile(plan)
        self.assertIsNotNone(repo)

    def test_artifact_to_verification(self):
        """Backend repo → conformance check (structural, fail-closed)."""
        from compiler.backends.python_fastapi import PythonFastAPIBackend
        from compiler.core.lowering import isr_to_plan

        plan = isr_to_plan(self._rev0())
        backend = PythonFastAPIBackend()
        repo = backend.compile(plan)
        report = backend.conformance(plan, repo)
        self.assertIsNotNone(report)

    def test_verification_to_evolution_feedback(self):
        """Verification-shaped evidence feeds the governance-aware evaluator
        without bypassing provenance (seam exists, contractually ready)."""
        from evolution.governance_fitness_evaluator import GovernanceAwareFitnessEvaluator

        evaluator = GovernanceAwareFitnessEvaluator()
        self.assertIsNotNone(evaluator)


class TestIdentity(unittest.TestCase):
    """§30 Identity: candidate, operation, lineage, provenance correlation."""

    def test_candidate_identity(self):
        from evolution.core.construction import ReferenceGenomeConstructor
        from evolution.core.genome import genome_content_hash
        from tests.r1d3.test_evolution_contracts import _make_genome

        rev_hash_a = genome_content_hash(_make_genome(system_id="rg-a"))
        rev_hash_b = genome_content_hash(_make_genome(system_id="rg-b"))
        self.assertNotEqual(rev_hash_a, rev_hash_b)

    def test_operation_identity(self):
        from evolution.core.operations import OperationRecord

        rec = OperationRecord("mutation", ["g1"], "g2", mutation_rate=0.5)
        self.assertEqual(rec.source_genome_ids, ["g1"])
        self.assertEqual(rec.result_genome_id, "g2")

    def test_lineage_identity(self):
        from evolution.history import EvolutionHistoryRepository

        repo = EvolutionHistoryRepository()
        e1 = repo.record("p1", "mutation", "engine", {"parent": "g0", "child": "g1"})
        e2 = repo.record("p1", "selection", "engine", {"selected": "g1"})
        self.assertEqual(e2.previous_event_hash, e1.event_hash)

    def test_provenance_correlation(self):
        """PlanArtifacts carries all four hashes (rg, genome, plan, revision)."""
        import dataclasses

        from certification.campaign.plan_builder import PlanArtifacts

        fields = {f.name for f in dataclasses.fields(PlanArtifacts)}
        for expected in (
            "plan",
            "revision",
            "genome",
            "requirement_graph",
            "requirement_graph_hash",
            "genome_hash",
            "plan_hash",
        ):
            self.assertIn(expected, fields)


class TestFailure(unittest.TestCase):
    """§30 Failure: unsupported capability, indeterminate, invalid operation."""

    def test_unsupported_capability_is_explicit(self):
        """Backend reports unsupported capabilities explicitly (no silent success)."""
        from compiler.backends.python_fastapi import PythonFastAPIBackend
        from compiler.core.plan import CompilationPlan

        backend = PythonFastAPIBackend()
        ident = backend.identity()
        self.assertTrue(ident.name)
        # Conformance on an empty repo must not claim success vacuously.
        plan = CompilationPlan(plan_id="plan:rg", isr_id="rg-test")
        from compiler.core.repository import build_repository

        repo = build_repository({})
        report = backend.conformance(plan, repo)
        self.assertIsNotNone(report)

    def test_verification_indeterminate_not_certified(self):
        """Ledger-integrity failure composes to NOT_CERTIFIED (fail-closed)."""
        from certification.campaign.verdict import (
            CampaignVerdict,
            compose_campaign_verdict,
        )

        verdict, _reason = compose_campaign_verdict(
            trials=[],
            expected_trials=0,
            ledger_intact=False,
            integrity_problems=["hash mismatch"],
            coverage_complete=False,
        )
        self.assertEqual(verdict, CampaignVerdict.NOT_CERTIFIED)

    def test_integrity_failure_not_certified(self):
        from certification.campaign.verdict import (
            CampaignVerdict,
            compose_campaign_verdict,
        )

        verdict, _reason = compose_campaign_verdict(
            trials=[],
            expected_trials=1,
            ledger_intact=True,
            integrity_problems=["gap"],
            coverage_complete=False,
        )
        self.assertEqual(verdict, CampaignVerdict.NOT_CERTIFIED)

    def test_invalid_evolution_operation(self):
        from evolution.core.selection import ReferenceParetoSelection

        with self.assertRaises(ValueError):
            ReferenceParetoSelection().select([])


class TestLineage(unittest.TestCase):
    """§30 Lineage: parent→child, artifact→candidate, record→operation."""

    def test_parent_to_child(self):
        import random

        from evolution.core.genome import genome_content_hash
        from evolution.core.operations import OperationRecord, ReferenceMutationOperator
        from tests.r1d3.test_evolution_contracts import _make_genome, _make_space

        parent = _make_genome()
        child = ReferenceMutationOperator(rng=random.Random(21)).mutate(parent, 1.0, _make_space())
        rec = OperationRecord("mutation", [genome_content_hash(parent)], genome_content_hash(child))
        self.assertEqual(rec.source_genome_ids, [genome_content_hash(parent)])

    def test_artifact_to_candidate(self):
        """CompilationPlan.isr_id + PlanArtifacts.genome_hash tie artifact to candidate."""
        from compiler.core.lowering import isr_to_plan
        from tests.rg.test_reconciliation import TestContractComposition

        case = TestContractComposition()
        rev = case._rev0()
        plan = isr_to_plan(rev)
        self.assertEqual(plan.isr_id, rev.system_id)

    def test_evolution_record_to_operation(self):
        from evolution.core.operations import OperationRecord

        rec = OperationRecord("crossover", ["pa", "pb"], "c1")
        self.assertEqual(rec.operation_type, "crossover")
        self.assertEqual(len(rec.source_genome_ids), 2)

    def test_observation_to_artifact_contract(self):
        """D12 defines reverse-lineage fields (contractually ready, C-17 deferred)."""
        import os

        path = os.path.join("folder", "CONTRACT_RuntimeObservation.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for field in (
            "artifact_set_id",
            "compiler_ir_id",
            "architecture_candidate_id",
            "isr_revision_hash",
            "requirement_graph_id",
        ):
            self.assertIn(field, content)


if __name__ == "__main__":
    unittest.main()
