"""End-to-end vertical slice: task tracker (CRUD_SAAS).

Proves Requirement → Architecture → Software → Evidence → Evolution through
the canonical substrate with full lineage. One category, one product; the
category is a compiler parameter, not a new authority.

Product: task tracker (intent), CRUD_SAAS (category), seeds ["task"].
"""
from __future__ import annotations

import random
import unittest
from datetime import datetime, timezone

from certification.campaign.plan_builder import build_artifacts_for
from certification.corpus.corpus import Category, Workload
from compiler.backends.python_fastapi import _sanitize_identifier as py_sanitize
from compiler.backends.rust_axum import _sanitize_identifier as rs_sanitize
from compiler.composition import build_backend_registry
from compiler.core.lowering import isr_to_plan
from evolution.core.genome import DecisionSpace, genome_content_hash
from evolution.core.materialize import ReferenceGenomeMaterializer
from evolution.core.operations import OperationRecord, ReferenceMutationOperator
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _workload() -> Workload:
    return Workload(intent="task tracker", category=Category.CRUD_SAAS, seeds=["task"])


def _space() -> DecisionSpace:
    return DecisionSpace(choices={
        "dom:task": ["bounded-context", "modular-monolith"],
        "baseline": ["json", "yaml", "token", "oauth2"],
    })


class TestSanitizer(unittest.TestCase):
    """Lowering boundary: ISR names become valid backend identifiers/paths."""

    def test_colon_collapsed(self):
        self.assertEqual(py_sanitize("dom:task"), "dom_task")
        self.assertEqual(rs_sanitize("dom:task"), "dom_task")

    def test_dash_collapsed(self):
        self.assertEqual(py_sanitize("my-service"), "my_service")

    def test_leading_digit_guarded(self):
        self.assertTrue(py_sanitize("3scale")[0] == "_")

    def test_empty_guarded(self):
        self.assertEqual(py_sanitize(":::"), "unnamed")

    def test_both_backends_agree(self):
        for raw in ["dom:task", "a-b:c", "svc 01"]:
            self.assertEqual(py_sanitize(raw), rs_sanitize(raw))


class TestSliceChain(unittest.TestCase):
    """Requirement → Architecture → Software with lineage."""

    def test_chain_builds_with_lineage(self):
        a = build_artifacts_for(_workload())
        self.assertTrue(a.requirement_graph_hash)
        self.assertTrue(a.genome_hash)
        self.assertTrue(a.plan_hash)
        self.assertEqual(a.revision.revision_id, f"rev1:{a.genome_hash[:16]}")
        self.assertTrue(a.plan.plan_id.startswith("plan:"))

    def test_backends_emit_colon_free_paths(self):
        a = build_artifacts_for(_workload())
        reg = build_backend_registry()
        for name in ("python-fastapi", "rust-axum"):
            repo = reg._backends[name].compile(a.plan)
            bad = [k for k in getattr(repo, "files", {}) if ":" in k]
            self.assertEqual(bad, [], f"{name} emitted colon paths: {bad}")

    def test_python_artifact_syntax_valid(self):
        a = build_artifacts_for(_workload())
        repo = build_backend_registry()._backends["python-fastapi"].compile(a.plan)
        errors = []
        for path, src in sorted(getattr(repo, "files", {}).items()):
            if path.endswith(".py"):
                try:
                    compile(src, path, "exec")
                except SyntaxError as e:
                    errors.append((path, str(e)))
        self.assertEqual(errors, [])

    def test_conformance_both_backends(self):
        a = build_artifacts_for(_workload())
        reg = build_backend_registry()
        for name in ("python-fastapi", "rust-axum"):
            backend = reg._backends[name]
            repo = backend.compile(a.plan)
            report = backend.conformance(a.plan, repo)
            self.assertTrue(report.passed, f"{name}: {report}")


class TestSliceEvolution(unittest.TestCase):
    """Software → Evidence → Evolution: second candidate recompiles clean."""

    def test_evolved_candidate_recompiles(self):
        a = build_artifacts_for(_workload())
        g2 = ReferenceMutationOperator(rng=random.Random(7)).mutate(a.genome, 1.0, _space())
        h1, h2 = genome_content_hash(a.genome), genome_content_hash(g2)
        self.assertNotEqual(h1, h2)
        graph2 = ReferenceGenomeMaterializer().materialize(g2)
        rev2 = ISRRevision.create(
            system_id="task-tracker",
            revision_id="rev2:evo",
            schema_version="1.0",
            graph=graph2,
            provenance=Provenance(
                parent_revision_id=a.revision.revision_id,
                created_by="evolution_engine",
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.assertEqual(rev2.provenance.parent_revision_id, a.revision.revision_id)
        plan2 = isr_to_plan(rev2)
        reg = build_backend_registry()
        for name in ("python-fastapi", "rust-axum"):
            backend = reg._backends[name]
            repo2 = backend.compile(plan2)
            self.assertTrue(backend.conformance(plan2, repo2).passed, name)
            bad = [k for k in getattr(repo2, "files", {}) if ":" in k]
            self.assertEqual(bad, [], name)

    def test_evolution_record_preserved(self):
        a = build_artifacts_for(_workload())
        g2 = ReferenceMutationOperator(rng=random.Random(7)).mutate(a.genome, 1.0, _space())
        h1, h2 = genome_content_hash(a.genome), genome_content_hash(g2)
        rec = OperationRecord("mutation", [h1], h2, mutation_rate=1.0)
        self.assertEqual(rec.source_genome_ids, [h1])
        self.assertEqual(rec.result_genome_id, h2)


if __name__ == "__main__":
    unittest.main()
