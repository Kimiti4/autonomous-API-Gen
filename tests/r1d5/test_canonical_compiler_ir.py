"""Canonical CompilerIR identity, lineage, and loss-preservation tests."""
from __future__ import annotations

import pytest

from compiler.core.canonical_ir import CompilerIR
from compiler.core.lowering import isr_revision_to_compiler_ir, isr_to_plan
from compiler.core.plan import CompilationPlan
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _revision(reverse: bool = False) -> ISRRevision:
    nodes = [
        ("api:billing", Node(
            id="api:billing", type=NodeType.API,
            properties={"label": "Billing API", "source_requirement_ids": ["REQ-1"]},
        )),
        ("route:billing", Node(
            id="route:billing", type=NodeType.FRONTEND_ROUTE,
            properties={"label": "Billing route", "source_requirement_ids": ["REQ-2"]},
        )),
        ("service:billing", Node(
            id="service:billing", type=NodeType.SERVICE,
            properties={"label": "Billing service"},
        )),
    ]
    edges = [
        ("exposes:billing", Edge(
            id="exposes:billing", type=EdgeType.EXPOSES,
            source_id="service:billing", target_id="api:billing",
        )),
        ("routes:billing", Edge(
            id="routes:billing", type=EdgeType.ROUTES_TO,
            source_id="route:billing", target_id="api:billing",
        )),
    ]
    if reverse:
        nodes.reverse()
        edges.reverse()
    return ISRRevision.create(
        system_id="compiler-ir-test",
        revision_id="rev-compiler-ir",
        schema_version="2.0",
        graph=ISRGraph(nodes=dict(nodes), edges=dict(edges)),
        provenance=Provenance(
            created_by="compiler-ir-test",
            created_at="2026-11-05T00:00:00Z",
            requirement_refs=("REQ-1", "REQ-2"),
        ),
    )


def test_canonical_ir_preserves_every_source_node_and_relationship():
    revision = _revision()
    ir = isr_revision_to_compiler_ir(
        revision,
        source_architecture_candidate_content_hash="a" * 64,
    )
    assert isinstance(ir, CompilerIR)
    assert {node.source_node_id for node in ir.nodes} == set(revision.graph.nodes)
    assert {edge.source_edge_id for edge in ir.relationships} == set(revision.graph.edges)
    assert ir.source_isr_content_hash == revision.content_hash
    assert ir.source_isr_revision_hash == revision.revision_hash
    assert ir.source_architecture_candidate_content_hash == "a" * 64
    assert not ir.projection_report.lost_node_ids
    assert not ir.projection_report.lost_relationship_ids
    assert set(ir.projection_report.source_node_ids) == set(revision.graph.nodes)
    assert set(ir.projection_report.source_relationship_ids) == set(revision.graph.edges)
    assert ir.architecture_reference_state == "BOUND"
    assert ir.execution_plan.frontend_routes[0].api_operations[0].id == "api:billing"


def test_canonical_ir_identity_is_invariant_to_graph_insertion_order():
    first = isr_revision_to_compiler_ir(
        _revision(False),
        source_architecture_candidate_content_hash="b" * 64,
        lowering_timestamp="2026-11-05T00:00:00Z",
    )
    second = isr_revision_to_compiler_ir(
        _revision(True),
        source_architecture_candidate_content_hash="b" * 64,
        lowering_timestamp="2026-11-05T00:00:00Z",
    )
    assert first.source_isr_content_hash == second.source_isr_content_hash
    assert first.compilation_id == second.compilation_id
    assert first.content_hash == second.content_hash


def test_missing_architecture_reference_requires_explicit_not_applicable_reason():
    with pytest.raises(ValueError, match="explicit reason"):
        isr_revision_to_compiler_ir(_revision())


def test_not_applicable_architecture_reference_is_explicit_in_ir():
    ir = isr_revision_to_compiler_ir(
        _revision(),
        architecture_reference_reason="This route receives an ISR revision without an ArchitectureCandidate.",
    )
    assert ir.architecture_reference_state == "NOT_APPLICABLE"
    assert ir.architecture_reference_reason


def test_legacy_isr_to_plan_api_is_only_a_compiler_ir_adapter():
    plan = isr_to_plan(_revision())
    assert isinstance(plan, CompilationPlan)


def test_compiler_ir_is_immutable_and_hash_checked():
    ir = isr_revision_to_compiler_ir(
        _revision(),
        architecture_reference_reason="No ArchitectureCandidate is supplied by this test route.",
    )
    with pytest.raises((ValueError, TypeError)):
        ir.content_hash = "0" * 64



def test_compiler_ir_backend_constraints_fail_closed():
    from compiler.core.canonical_ir import assert_compiler_ir_supported
    from compiler.core.capabilities import BackendCapabilities, UnsupportedSemanticsError

    ir = isr_revision_to_compiler_ir(
        _revision(),
        architecture_reference_reason="No ArchitectureCandidate exists in this test route.",
        backend_constraints=("rust-axum",),
    )
    with pytest.raises(UnsupportedSemanticsError, match="excluded by CompilerIR constraints"):
        assert_compiler_ir_supported(
            ir,
            BackendCapabilities(backend_id="python-fastapi", version="1.0"),
        )
    assert ir.execution_plan.backend_constraints == ["rust-axum"]
    from compiler.core.capabilities import assert_plan_supported
    with pytest.raises(UnsupportedSemanticsError, match="excluded by CompilerIR constraints"):
        assert_plan_supported(
            ir.execution_plan,
            BackendCapabilities(backend_id="python-fastapi", version="1.0"),
        )
    from compiler.backends.react_frontend import ReactFrontendBackend
    with pytest.raises(UnsupportedSemanticsError, match="excluded by CompilerIR constraints"):
        ReactFrontendBackend().compile(ir.execution_plan)



def test_invariant_relationship_is_preserved_and_blocks_unsupported_backends():
    from compiler.core.canonical_ir import assert_compiler_ir_supported
    from compiler.core.capabilities import (
        BackendCapabilities, SemanticFeature, UnsupportedSemanticsError,
        required_features,
    )

    graph = ISRGraph(
        nodes={
            "service:payroll": Node(
                id="service:payroll", type=NodeType.SERVICE, properties={"label": "Payroll"}
            ),
            "invariant:nonnegative": Node(
                id="invariant:nonnegative", type=NodeType.INVARIANT,
                properties={"label": "Nonnegative"},
            ),
        },
        edges={
            "requires:nonnegative": Edge(
                id="requires:nonnegative", type=EdgeType.REQUIRES_INVARIANT,
                source_id="service:payroll", target_id="invariant:nonnegative",
            )
        },
    )
    revision = ISRRevision.create(
        system_id="invariant-binding-test",
        revision_id="rev-invariant-binding",
        schema_version="2.0",
        graph=graph,
        provenance=Provenance(
            created_by="test", created_at="2026-11-05T00:00:00Z"
        ),
    )
    ir = isr_revision_to_compiler_ir(
        revision,
        architecture_reference_reason="No ArchitectureCandidate is supplied by this test route.",
    )
    assert ir.execution_plan.invariant_bindings[0].edge_id == "requires:nonnegative"
    assert "requires:nonnegative" in ir.projection_report.projected_relationship_ids
    assert SemanticFeature.INVARIANT_BINDINGS in required_features(ir.execution_plan)
    with pytest.raises(UnsupportedSemanticsError, match="invariant_bindings"):
        assert_compiler_ir_supported(
            ir, BackendCapabilities(backend_id="python-fastapi", version="1.0")
        )



def test_backend_required_semantics_outside_plan_projection_block_lowering():
    from compiler.core.canonical_ir import assert_compiler_ir_supported
    from compiler.core.capabilities import BackendCapabilities, UnsupportedSemanticsError

    revision = ISRRevision.create(
        system_id="required-ir-only-test",
        revision_id="rev-required-ir-only",
        schema_version="2.0",
        graph=ISRGraph(
            nodes={
                "capability:required": Node(
                    id="capability:required",
                    type=NodeType.CAPABILITY,
                    properties={"label": "required capability", "required_for_backend": True},
                )
            },
            edges={},
        ),
        provenance=Provenance(
            created_by="test", created_at="2026-11-05T00:00:00Z"
        ),
    )
    ir = isr_revision_to_compiler_ir(
        revision,
        architecture_reference_reason="No ArchitectureCandidate is supplied by this test route.",
    )
    assert ir.projection_report.blocking_ir_only_node_ids == ("capability:required",)
    with pytest.raises(UnsupportedSemanticsError, match="backend-required semantics"):
        assert_compiler_ir_supported(
            ir, BackendCapabilities(backend_id="python-fastapi", version="1.0")
        )

    # The compatibility adapter cannot discard the blocker and hand a clean
    # CompilationPlan to a backend: the diagnostic is carried into the plan.
    legacy_plan = isr_to_plan(revision)
    assert legacy_plan.blocking_diagnostics
    from compiler.core.capabilities import assert_plan_supported
    with pytest.raises(UnsupportedSemanticsError, match="adapter blocked backend lowering"):
        assert_plan_supported(
            legacy_plan, BackendCapabilities(backend_id="python-fastapi", version="1.0")
        )
    from compiler.backends.react_frontend import ReactFrontendBackend
    with pytest.raises(UnsupportedSemanticsError, match="frontend lowering"):
        ReactFrontendBackend().compile(legacy_plan)

    # Nested Pydantic collections are mutable even on a frozen model. The
    # projection integrity hash detects tampering before any backend entry.
    legacy_plan.blocking_diagnostics.clear()
    with pytest.raises(UnsupportedSemanticsError, match="integrity hash mismatch"):
        assert_plan_supported(
            legacy_plan, BackendCapabilities(backend_id="python-fastapi", version="1.0")
        )



def test_compiler_ir_rejects_forged_compilation_identity_on_reload():
    ir = isr_revision_to_compiler_ir(
        _revision(),
        architecture_reference_reason="No ArchitectureCandidate is supplied by this test route.",
        lowering_timestamp="2026-11-05T00:00:00Z",
    )
    payload = ir.model_dump(mode="json")
    payload["compilation_id"] = "00000000-0000-0000-0000-000000000000"
    with pytest.raises(ValueError, match="compilation_id"):
        CompilerIR.model_validate(payload)



def test_compiler_ir_rejects_plan_nodes_not_bound_to_source_isr():
    from compiler.core.plan import CompilationPlan, Service

    revision = _revision()
    forged_plan = CompilationPlan(
        plan_id="plan:forged",
        isr_id=revision.system_id,
        services=[Service(id="service:invented", name="Invented service")],
    )
    with pytest.raises(ValueError, match="does not match deterministic ISR projection"):
        CompilerIR.from_revision(
            revision,
            execution_plan=forged_plan,
            architecture_reference_reason="Test route has no ArchitectureCandidate.",
            lowering_timestamp="2026-11-05T00:00:00Z",
        )
