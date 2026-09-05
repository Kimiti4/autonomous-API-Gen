"""VS-D01 tests: the task-tracker RequirementGraph validates fail-closed,
is deterministic, and covers the slice scope (CRUD + authN/authZ)."""
from __future__ import annotations

import unittest

from reqgraph.core.graph import RequirementEdgeType, RequirementKind
from reqgraph.core.invariants import validate_requirement_graph
from vertical_slice.requirements import build_task_tracker_requirements


class TestSliceRequirements(unittest.TestCase):
    def test_graph_validates_fail_closed(self):
        graph = build_task_tracker_requirements()
        validate_requirement_graph(graph)  # must not raise

    def test_scope_counts(self):
        graph = build_task_tracker_requirements()
        self.assertEqual(len(graph.nodes), 19)
        self.assertEqual(len(graph.edges), 36)

    def test_deterministic(self):
        first = build_task_tracker_requirements()
        second = build_task_tracker_requirements()
        self.assertEqual(first, second)

    def test_functional_requirements_have_acceptance_criteria(self):
        graph = build_task_tracker_requirements()
        functional = [n for n in graph.nodes.values()
                      if n.kind is RequirementKind.FUNCTIONAL]
        self.assertGreaterEqual(len(functional), 9)
        for node in functional:
            self.assertTrue(node.acceptance_criteria, node.id)

    def test_crud_authz_covered(self):
        graph = build_task_tracker_requirements()
        for req_id in ("req-task-create", "req-task-read", "req-task-update",
                       "req-task-delete", "req-task-assign", "req-auth-register",
                       "req-auth-login", "req-workspace-members",
                       "req-credential-safety", "req-tenant-isolation"):
            self.assertIn(req_id, graph.nodes)

    def test_conflict_is_resolved(self):
        graph = build_task_tracker_requirements()
        conflicts = [e for e in graph.edges.values()
                     if e.type is RequirementEdgeType.CONFLICTS_WITH]
        self.assertEqual(len(conflicts), 1)
        self.assertTrue(conflicts[0].resolution_ref)

    def test_technology_neutral_statements(self):
        forbidden = ("fastapi", "postgres", "docker", "react", "pytest",
                     "kubernetes", "redis", "aws")
        graph = build_task_tracker_requirements()
        for node in graph.nodes.values():
            blob = " ".join([node.statement, *node.acceptance_criteria]).lower()
            for term in forbidden:
                self.assertNotIn(term, blob, f"{node.id} leaks {term}")


if __name__ == "__main__":
    unittest.main()
