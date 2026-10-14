"""Adversarial tests for source-unit to requirement-graph coverage."""
import hashlib

from tiannara.application.compiler.source_coverage import (
    SourceUnit,
    SourceUnitBinding,
    verify_source_graph_coverage,
)
from tiannara.domain.models.requirement_graph import (
    GraphProvenance,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from tiannara.domain.models.system_model import Priority


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _graph():
    return RequirementGraph(
        graph_id="coverage-graph",
        nodes=[
            RequirementNode(
                id="REQ-A",
                kind=RequirementKind.CONSTRAINT,
                statement="Only workspace members can access workspace data.",
                priority=Priority.MUST,
            ),
            RequirementNode(
                id="REQ-B",
                kind=RequirementKind.QUALITY,
                statement="Expose readiness status.",
                priority=Priority.SHOULD,
            ),
        ],
        provenance=GraphProvenance(source_statement_hash="a" * 64),
    )


def _unit(unit_id: str, phrase: bytes, start: int) -> SourceUnit:
    return SourceUnit(
        unit_id=unit_id,
        start_byte=start,
        end_byte=start + len(phrase),
        unit_sha256=_sha(phrase),
    )


def test_complete_source_unit_mapping_passes_structural_coverage():
    source = b"Workspace isolation is mandatory. Readiness must be observable."
    first = b"Workspace isolation is mandatory."
    second = b"Readiness must be observable."
    units = (
        _unit("U-A", first, 0),
        _unit("U-B", second, len(first) + 1),
    )
    result = verify_source_graph_coverage(
        source_bytes=source,
        expected_source_sha256=_sha(source),
        graph=_graph(),
        units=units,
        bindings=(
            SourceUnitBinding(unit_id="U-A", graph_node_ids=("REQ-A",)),
            SourceUnitBinding(unit_id="U-B", graph_node_ids=("REQ-B",)),
        ),
    )
    assert result.complete
    assert result.uncovered_unit_ids == ()
    assert result.unbound_required_node_ids == ()


def test_omitted_source_unit_blocks_coverage():
    source = b"Workspace isolation is mandatory. Readiness must be observable."
    first = b"Workspace isolation is mandatory."
    second = b"Readiness must be observable."
    result = verify_source_graph_coverage(
        source_bytes=source,
        expected_source_sha256=_sha(source),
        graph=_graph(),
        units=(
            _unit("U-A", first, 0),
            _unit("U-B", second, len(first) + 1),
        ),
        bindings=(SourceUnitBinding(unit_id="U-A", graph_node_ids=("REQ-A",)),),
    )
    assert not result.complete
    assert result.uncovered_unit_ids == ("U-B",)
    assert any("lack graph mappings" in blocker for blocker in result.blockers)


def test_mandatory_graph_node_without_source_binding_blocks_coverage():
    source = b"Workspace isolation is mandatory."
    unit = _unit("U-A", source, 0)
    result = verify_source_graph_coverage(
        source_bytes=source,
        expected_source_sha256=_sha(source),
        graph=_graph(),
        units=(unit,),
        bindings=(SourceUnitBinding(unit_id="U-A", graph_node_ids=("REQ-B",)),),
    )
    assert not result.complete
    assert result.unbound_required_node_ids == ("REQ-A",)


def test_stale_source_and_unknown_graph_node_are_rejected():
    source = b"Workspace isolation is mandatory."
    unit = _unit("U-A", source, 0)
    result = verify_source_graph_coverage(
        source_bytes=source,
        expected_source_sha256="0" * 64,
        graph=_graph(),
        units=(unit,),
        bindings=(SourceUnitBinding(unit_id="U-A", graph_node_ids=("REQ-NOT-REAL",)),),
    )
    assert not result.complete
    assert any("snapshot hash" in blocker for blocker in result.blockers)
    assert any("unknown graph node" in blocker for blocker in result.blockers)


def test_source_unit_hash_mismatch_is_rejected():
    source = b"Workspace isolation is mandatory."
    bad = SourceUnit(
        unit_id="U-A",
        start_byte=0,
        end_byte=len(source),
        unit_sha256="0" * 64,
    )
    result = verify_source_graph_coverage(
        source_bytes=source,
        expected_source_sha256=_sha(source),
        graph=_graph(),
        units=(bad,),
        bindings=(SourceUnitBinding(unit_id="U-A", graph_node_ids=("REQ-A",)),),
    )
    assert not result.complete
    assert any("unit hash mismatch" in blocker for blocker in result.blockers)



def test_typed_isr_must_trace_every_mandatory_graph_requirement():
    from tiannara.application.compiler.source_coverage import (
        verify_graph_system_model_traceability,
    )
    from tiannara.domain.models.system_model import (
        BusinessCapability, RequirementsReference, SystemModel,
    )

    graph = _graph()
    model = SystemModel(
        system_name="Workspace Service",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id, graph_hash=graph.content_hash()
        ),
        capabilities=[
            BusinessCapability(
                id="CAP-workspace-isolation",
                name="Workspace isolation",
                traced_requirement_ids=["REQ-A"],
            )
        ],
    )
    report = verify_graph_system_model_traceability(graph=graph, system_model=model)
    assert report.complete
    assert report.mapped_required_node_ids == ("REQ-A",)
    assert report.unmapped_required_node_ids == ()


def test_typed_isr_traceability_blocks_missing_or_unknown_requirement_links():
    from tiannara.application.compiler.source_coverage import (
        verify_graph_system_model_traceability,
    )
    from tiannara.domain.models.system_model import (
        BusinessCapability, RequirementsReference, SystemModel,
    )

    graph = _graph()
    model = SystemModel(
        system_name="Workspace Service",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id, graph_hash=graph.content_hash()
        ),
        capabilities=[
            BusinessCapability(
                id="CAP-readiness",
                name="Readiness",
                traced_requirement_ids=["REQ-NOT-REAL"],
            )
        ],
    )
    report = verify_graph_system_model_traceability(graph=graph, system_model=model)
    assert not report.complete
    assert report.unmapped_required_node_ids == ("REQ-A",)
    assert report.unknown_requirement_ids == ("REQ-NOT-REAL",)
