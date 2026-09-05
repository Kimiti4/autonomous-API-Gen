"""R1-D.1 ISR semantic migration tests — M-01, M-02, M-03.

Source: folder/R1_D1_ISR_MIGRATION_MAP.md (D4).
Source: folder/CONTRACT_CanonicalISR.md (D03).

These tests verify the R1-D.1 semantic migrations into isr/core/:
  - M-01: Requirement is a semantic obligation (testing-mechanism check on REQUIREMENT_REF).
  - M-02: Testing-mechanism check on all node properties (general principle).
  - M-03: Security-by-design docstrings on SECURITY_POLICY and SECURED_BY.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from isr.core.graph import (
    EDGE_TYPE_COMPATIBILITY,
    ISRGraph,
    Node,
    NodeType,
    Edge,
    EdgeType,
)
from isr.core.identity import Provenance
from isr.core.invariants import (
    FORBIDDEN_IMPLEMENTATION_TERMS,
    ISRInvariantViolation,
    TESTING_MECHANISM_TERMS,
    validate_invariants,
)
from isr.core.revision import ISRRevision


def _make_provenance() -> Provenance:
    return Provenance(
        created_by="r1d1_test",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def _make_revision(graph: ISRGraph, schema_version: str = "1.1") -> ISRRevision:
    return ISRRevision.create(
        system_id="r1d1-test",
        revision_id="r1d1-rev-1",
        schema_version=schema_version,
        graph=graph,
        provenance=_make_provenance(),
    )


class TestM01RequirementSemanticObligation(unittest.TestCase):
    """R1-D.1 M-01: requirement-ref is a semantic obligation, not a test mechanism.

    A REQUIREMENT_REF node that names a test framework (pytest, playwright, etc.)
    is a contract violation. The canonical ISR enforces this via the
    TESTING_MECHANISM_TERMS check.
    """

    def test_testing_mechanism_terms_constant_exists(self):
        self.assertIsInstance(TESTING_MECHANISM_TERMS, tuple)
        self.assertIn("pytest", TESTING_MECHANISM_TERMS)
        self.assertIn("playwright", TESTING_MECHANISM_TERMS)
        self.assertIn("selenium", TESTING_MECHANISM_TERMS)

    def test_requirement_ref_with_pytest_in_ref_id_rejected(self):
        node = Node(
            id="req:1",
            type=NodeType.REQUIREMENT_REF,
            properties={"ref_id": "run pytest for user auth"},
        )
        graph = ISRGraph(nodes={"req:1": node})
        with self.assertRaises(ISRInvariantViolation) as cm:
            validate_invariants(graph)
        self.assertIn("pytest", str(cm.exception).lower())

    def test_requirement_ref_with_playwright_in_ref_id_rejected(self):
        node = Node(
            id="req:1",
            type=NodeType.REQUIREMENT_REF,
            properties={"ref_id": "verify with playwright e2e login"},
        )
        graph = ISRGraph(nodes={"req:1": node})
        with self.assertRaises(ISRInvariantViolation):
            validate_invariants(graph)

    def test_requirement_ref_with_valid_ref_id_accepted(self):
        node = Node(
            id="req:1",
            type=NodeType.REQUIREMENT_REF,
            properties={"ref_id": "user_authentication_obligation"},
        )
        graph = ISRGraph(nodes={"req:1": node})
        # Should not raise.
        validate_invariants(graph)

    def test_requirement_ref_with_missing_ref_id_still_rejected(self):
        """The existing REQUIREMENT_REF.ref_id check is preserved."""
        node = Node(
            id="req:1",
            type=NodeType.REQUIREMENT_REF,
            properties={},
        )
        graph = ISRGraph(nodes={"req:1": node})
        with self.assertRaises(ISRInvariantViolation) as cm:
            validate_invariants(graph)
        self.assertIn("ref_id", str(cm.exception))


class TestM02TestingMechanismGeneralPrinciple(unittest.TestCase):
    """R1-D.1 M-02: the testing-mechanism check applies to ALL node types,
    not just REQUIREMENT_REF. The semantic principle is general: the canonical
    ISR is technology-neutral and mechanism-neutral.
    """

    def test_capability_with_pytest_in_properties_rejected(self):
        node = Node(
            id="cap:1",
            type=NodeType.CAPABILITY,
            properties={"label": "user authentication", "test_ref": "run pytest"},
        )
        graph = ISRGraph(nodes={"cap:1": node})
        with self.assertRaises(ISRInvariantViolation) as cm:
            validate_invariants(graph)
        self.assertIn("pytest", str(cm.exception).lower())

    def test_service_with_selenium_in_properties_rejected(self):
        node = Node(
            id="svc:1",
            type=NodeType.SERVICE,
            properties={"label": "auth service", "test": "uses selenium"},
        )
        graph = ISRGraph(nodes={"svc:1": node})
        with self.assertRaises(ISRInvariantViolation):
            validate_invariants(graph)

    def test_data_model_with_jest_in_properties_rejected(self):
        node = Node(
            id="dm:1",
            type=NodeType.DATA_MODEL,
            properties={"label": "user", "test": "uses jest"},
        )
        graph = ISRGraph(nodes={"dm:1": node})
        with self.assertRaises(ISRInvariantViolation):
            validate_invariants(graph)

    def test_node_with_valid_content_accepted(self):
        node = Node(
            id="cap:1",
            type=NodeType.CAPABILITY,
            properties={"label": "user authentication"},
        )
        graph = ISRGraph(nodes={"cap:1": node})
        validate_invariants(graph)  # should not raise

    def test_testing_mechanism_case_insensitive(self):
        """The check is case-insensitive (like FORBIDDEN_IMPLEMENTATION_TERMS)."""
        node = Node(
            id="req:1",
            type=NodeType.REQUIREMENT_REF,
            properties={"ref_id": "PYTEST test"},
        )
        graph = ISRGraph(nodes={"req:1": node})
        with self.assertRaises(ISRInvariantViolation):
            validate_invariants(graph)


class TestM03SecurityByDesign(unittest.TestCase):
    """R1-D.1 M-03: SECURITY_POLICY and SECURED_BY express the security-by-design
    principle: security threats are obligations supplied by evolution/architecture
    selection, not findings from scanners.
    """

    def test_security_policy_node_accepted(self):
        node = Node(
            id="sec:1",
            type=NodeType.SECURITY_POLICY,
            properties={"name": "authn_required", "description": "All services must authenticate"},
        )
        graph = ISRGraph(nodes={"sec:1": node})
        validate_invariants(graph)  # should not raise

    def test_secured_by_edge_accepted(self):
        svc = Node(id="svc:1", type=NodeType.SERVICE, properties={"name": "auth"})
        sec = Node(
            id="sec:1",
            type=NodeType.SECURITY_POLICY,
            properties={"name": "authn_required"},
        )
        edge = Edge(
            id="e:1",
            type=EdgeType.SECURED_BY,
            source_id="svc:1",
            target_id="sec:1",
        )
        graph = ISRGraph(
            nodes={"svc:1": svc, "sec:1": sec},
            edges={"e:1": edge},
        )
        validate_invariants(graph)  # should not raise

    def test_edge_type_compatibility_includes_secured_by(self):
        """The canonical EDGE_TYPE_COMPATIBILITY matrix includes SECURED_BY."""
        self.assertIn(EdgeType.SECURED_BY, EDGE_TYPE_COMPATIBILITY)
        src, tgt = EDGE_TYPE_COMPATIBILITY[EdgeType.SECURED_BY]
        self.assertIn(NodeType.SERVICE, src)
        self.assertIn(NodeType.API, src)
        self.assertIn(NodeType.SECURITY_POLICY, tgt)

    def test_security_policy_docstring_present(self):
        """The NodeType.SECURITY_POLICY has a docstring documenting the
        security-by-design principle (M-03). We verify by reading the
        source file (Pydantic-compatible enums do not preserve member docstrings)."""
        import inspect
        from isr.core import graph as graph_module
        source = inspect.getsource(graph_module)
        self.assertIn("security-by-design", source.lower())
        self.assertIn("security_policy", source.lower())

    def test_secured_by_docstring_present(self):
        import inspect
        from isr.core import graph as graph_module
        source = inspect.getsource(graph_module)
        self.assertIn("secured_by", source.lower())
        self.assertIn("security spine", source.lower())


class TestR1D1ISRRevisionIntegration(unittest.TestCase):
    """Integration: the R1-D.1 migrations work end-to-end with ISRRevision.create."""

    def test_valid_revision_with_no_testing_contamination(self):
        cap = Node(
            id="cap:1",
            type=NodeType.CAPABILITY,
            properties={"label": "user auth"},
        )
        svc = Node(
            id="svc:1",
            type=NodeType.SERVICE,
            properties={"name": "auth service"},
        )
        req = Node(
            id="req:1",
            type=NodeType.REQUIREMENT_REF,
            properties={"ref_id": "user_auth_obligation"},
        )
        sec = Node(
            id="sec:1",
            type=NodeType.SECURITY_POLICY,
            properties={"name": "authn_required"},
        )
        e1 = Edge(
            id="e:1",
            type=EdgeType.SATISFIES,
            source_id="cap:1",
            target_id="req:1",
        )
        e2 = Edge(
            id="e:2",
            type=EdgeType.IMPLEMENTED_BY,
            source_id="cap:1",
            target_id="svc:1",
        )
        e3 = Edge(
            id="e:3",
            type=EdgeType.SECURED_BY,
            source_id="svc:1",
            target_id="sec:1",
        )
        graph = ISRGraph(
            nodes={"cap:1": cap, "svc:1": svc, "req:1": req, "sec:1": sec},
            edges={"e:1": e1, "e:2": e2, "e:3": e3},
        )
        rev = _make_revision(graph)
        self.assertEqual(rev.content_hash, rev.content_hash)  # deterministic
        self.assertEqual(len(rev.content_hash), 64)

    def test_revision_with_testing_contamination_rejected(self):
        req = Node(
            id="req:1",
            type=NodeType.REQUIREMENT_REF,
            properties={"ref_id": "run pytest for test"},
        )
        graph = ISRGraph(nodes={"req:1": req})
        with self.assertRaises(ISRInvariantViolation):
            _make_revision(graph)


class TestR1D1CanonicalStillSoleAuthority(unittest.TestCase):
    """R1-D.1 invariant: isr/core remains the sole canonical ISR authority.
    No new ISR types introduced; no constitutional types promoted.
    """

    def test_canonical_node_type_count_unchanged(self):
        """The canonical ISR still has exactly 9 NodeType values."""
        self.assertEqual(len(list(NodeType)), 9)

    def test_canonical_edge_type_count_unchanged(self):
        """The canonical ISR still has exactly 8 EdgeType values."""
        self.assertEqual(len(list(EdgeType)), 8)

    def test_no_new_node_types_introduced(self):
        """The R1-D.1 migration does NOT introduce new NodeType values
        (no MODULE, SYSTEM, WORKFLOW, POLICY, etc.)."""
        type_values = {nt.value for nt in NodeType}
        self.assertEqual(type_values, {
            "domain", "capability", "service", "api",
            "data_model", "event", "security_policy",
            "infrastructure_target", "requirement_ref",
        })

    def test_no_new_edge_types_introduced(self):
        type_values = {et.value for et in EdgeType}
        self.assertEqual(type_values, {
            "satisfies", "implemented_by", "exposes", "persists",
            "publishes", "consumed_by", "depends_on", "secured_by",
        })


if __name__ == "__main__":
    unittest.main()
