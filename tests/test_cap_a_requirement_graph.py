import pytest
from pydantic import ValidationError

from tiannara.domain.models.requirement_graph import (
    DIRECTED_EDGE_KINDS,
    EdgeKind,
    RequirementEdge,
    RequirementGraph,
    RequirementGraphValidationError,
    RequirementKind,
    RequirementNode,
)


def _node(node_id: str, kind=RequirementKind.FUNCTIONAL, priority="must"):
    return RequirementNode(id=node_id, kind=kind, statement=f"Statement {node_id}")


def _edge(src: str, dst: str, kind: EdgeKind = EdgeKind.REFINES) -> RequirementEdge:
    return RequirementEdge(source_id=src, target_id=dst, kind=kind)


def test_empty_graph_is_valid():
    g = RequirementGraph(graph_id="g")
    assert g.content_hash() == RequirementGraph(graph_id="g").content_hash()


def test_dangling_edge_rejected():
    with pytest.raises(ValidationError, match="dangling edge"):
        RequirementGraph(
            graph_id="g", nodes=[_node("a"), _node("b")],
            edges=[_edge("a", "ghost")],
        )


def test_duplicate_node_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate node ids"):
        RequirementGraph(graph_id="g", nodes=[_node("a"), _node("a")])


def test_duplicate_edge_rejected():
    with pytest.raises(ValidationError, match="duplicate edge"):
        RequirementGraph(
            graph_id="g", nodes=[_node("a"), _node("b")],
            edges=[_edge("a", "b"), _edge("a", "b")],
        )


def test_directed_self_loop_rejected():
    with pytest.raises(ValidationError, match="self-loop"):
        RequirementGraph(
            graph_id="g", nodes=[_node("a")],
            edges=[RequirementEdge(source_id="a", target_id="a", kind=EdgeKind.DEPENDS_ON)],
        )


def test_analysis_excluded_from_hash():
    from tiannara.domain.services.graph_analysis import analyze
    g = RequirementGraph(graph_id="g", nodes=[_node("a"), _node("b")])
    before = g.content_hash()
    g.analysis = analyze(g)
    assert g.content_hash() == before


def test_directed_edge_kinds_subset():
    assert EdgeKind.CONFLICTS_WITH not in DIRECTED_EDGE_KINDS
    assert EdgeKind.DEPENDS_ON in DIRECTED_EDGE_KINDS
