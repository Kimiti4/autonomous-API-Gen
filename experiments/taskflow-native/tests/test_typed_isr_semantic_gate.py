import sys
from pathlib import Path

import pytest

from tiannara.domain.models.requirement_graph import (
    GraphProvenance,
    RequirementGraph,
)
from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    UnresolvedSemanticsError,
)

_PROVIDER_FREE = Path(__file__).parents[1] / "provider_free"
sys.path.insert(0, str(_PROVIDER_FREE))
from typed_isr_gate import build_taskflow_typed_isr  # noqa: E402


def _graph():
    return RequirementGraph(
        graph_id="rg-taskflow-gate-test",
        nodes=[],
        edges=[],
        provenance=GraphProvenance(
            origin="immutable_taskflow_snapshot",
            source_statement_hash="c" * 64,
            taxonomy_version="test.v1",
        ),
    )


def _resolution(graph, *, resolved):
    item = SemanticResolution(
        field_path="security.authorization",
        kind=ResolutionKind.SNAPSHOT if resolved else ResolutionKind.UNRESOLVED,
        value="rbac" if resolved else None,
        source="snapshot:problem#security" if resolved else None,
    )
    return SemanticResolutionRecord(
        graph_id=graph.graph_id,
        graph_hash=graph.content_hash(),
        required_fields=("security.authorization",),
        resolutions=(item,),
    )


def test_unresolved_semantics_block_before_model_builder_is_called():
    graph = _graph()
    calls = []

    def builder():
        calls.append("called")
        raise AssertionError("SystemModel builder must not run")

    with pytest.raises(UnresolvedSemanticsError):
        build_taskflow_typed_isr(
            graph=graph,
            resolutions=_resolution(graph, resolved=False),
            build_system_model=builder,
            system_id="taskflow",
        )
    assert calls == []


def test_graph_mismatch_blocks_before_model_builder_is_called():
    graph = _graph()
    other_graph = _graph().model_copy(update={"graph_id": "other-graph"})
    calls = []

    with pytest.raises(ValueError, match="does not match"):
        build_taskflow_typed_isr(
            graph=graph,
            resolutions=_resolution(other_graph, resolved=True),
            build_system_model=lambda: calls.append("called"),
            system_id="taskflow",
        )
    assert calls == []
