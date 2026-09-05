"""VS-D02 tests: the slice ISR is canonical, deterministic, and lineage-bound."""
from __future__ import annotations

import unittest

from isr.core.graph import EdgeType, NodeType
from isr.core.invariants import validate_invariants
from vertical_slice.isr import build_task_tracker_isr
from vertical_slice.requirements import build_task_tracker_requirements


class TestSliceISR(unittest.TestCase):
    def test_validates_fail_closed(self):
        rev = build_task_tracker_isr()
        validate_invariants(rev.graph)  # must not raise

    def test_scope_counts(self):
        rev = build_task_tracker_isr()
        self.assertEqual(len(rev.graph.nodes), 32)
        self.assertEqual(len(rev.graph.edges), 33)

    def test_deterministic(self):
        self.assertEqual(build_task_tracker_isr(), build_task_tracker_isr())

    def test_content_hash_stable(self):
        rev = build_task_tracker_isr()
        self.assertEqual(len(rev.content_hash), 64)
        self.assertEqual(rev.content_hash, build_task_tracker_isr().content_hash)

    def test_requirement_refs_resolve_to_frozen_graph(self):
        graph = build_task_tracker_requirements()
        rev = build_task_tracker_isr()
        refs = [n for n in rev.graph.nodes.values()
                if n.type is NodeType.REQUIREMENT_REF]
        self.assertEqual(len(refs), 11)
        for node in refs:
            self.assertIn(node.properties["ref_id"], graph.nodes)

    def test_provenance_carries_requirement_lineage(self):
        rev = build_task_tracker_isr()
        self.assertIn("vs1-manual-intake-v1", rev.provenance.derivation_refs)
        self.assertIn("req-task-create", rev.provenance.requirement_refs)

    def test_capabilities_satisfy_requirements(self):
        rev = build_task_tracker_isr()
        satisfied = {e.target_id for e in rev.graph.edges.values()
                     if e.type is EdgeType.SATISFIES}
        for node in rev.graph.nodes.values():
            if node.type is NodeType.CAPABILITY:
                targets = {e.target_id for e in rev.graph.edges.values()
                           if e.type is EdgeType.SATISFIES
                           and e.source_id == node.id}
                self.assertEqual(len(targets), 1, node.id)
        self.assertEqual(len(satisfied), 8)

    def test_services_secured(self):
        rev = build_task_tracker_isr()
        for svc in ("svc-identity", "svc-task", "svc-workspace"):
            policies = {e.target_id for e in rev.graph.edges.values()
                        if e.type is EdgeType.SECURED_BY and e.source_id == svc}
            self.assertEqual(policies, {"sec-credential-safety", "sec-tenant-isolation"})


if __name__ == "__main__":
    unittest.main()
