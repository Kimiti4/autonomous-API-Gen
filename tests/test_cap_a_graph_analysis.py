from tiannara.domain.models.requirement_graph import (
    EdgeKind,
    RequirementEdge,
    RequirementGraph,
    RequirementNode,
)
from tiannara.domain.models.system_model import (
    BusinessCapability,
    RequirementsReference,
    SystemModel,
)
from tiannara.domain.services.graph_analysis import (
    analyze,
    cross_reference,
    detect_cycles,
    find_orphans,
)


def _node(node_id: str, priority="must", kind="functional"):
    return RequirementNode(id=node_id, kind=kind, statement=f"S {node_id}", priority=priority)


def _graph(nodes, edges=None):
    return RequirementGraph(graph_id="g", nodes=nodes, edges=edges or [])


def test_cycle_detection_deterministic():
    g = _graph(
        [_node("a"), _node("b"), _node("c")],
        edges=[
            RequirementEdge(source_id="a", target_id="b", kind=EdgeKind.DEPENDS_ON),
            RequirementEdge(source_id="b", target_id="c", kind=EdgeKind.DEPENDS_ON),
            RequirementEdge(source_id="c", target_id="a", kind=EdgeKind.DEPENDS_ON),
        ],
    )
    assert detect_cycles(g) == [["a", "b", "c"]]


def test_no_false_cycle_for_refines_diamond():
    # a refines b; a refines c; b -> d; c -> d (DAG): no cycles
    g = _graph(
        [_node(n) for n in "abcd"],
        edges=[
            RequirementEdge(source_id="a", target_id="b", kind=EdgeKind.REFINES),
            RequirementEdge(source_id="a", target_id="c", kind=EdgeKind.REFINES),
            RequirementEdge(source_id="b", target_id="d", kind=EdgeKind.REALIZES),
            RequirementEdge(source_id="c", target_id="d", kind=EdgeKind.REALIZES),
        ],
    )
    assert detect_cycles(g) == []


def test_find_orphans_and_asymmetric_conflicts():
    g = _graph(
        [_node("a"), _node("b"), _node("lonely", priority="should")],
        edges=[
            RequirementEdge(source_id="a", target_id="b", kind=EdgeKind.CONFLICTS_WITH),
        ],
    )
    findings = analyze(g)
    assert findings.orphan_nodes == ["lonely"]
    assert findings.asymmetric_conflicts == [["a", "b"]]
    assert findings.has_structural_problems is True


def test_cross_reference_traceability():
    graph = _graph([_node("req-1"), _node("req-2")])
    model = SystemModel(
        system_name="s",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        capabilities=[
            BusinessCapability(
                id="cap-1", name="One",
                traced_requirement_ids=["req-1", "req-ghost"],
            )
        ],
    )
    findings = cross_reference(graph, model)
    assert [f.node_id for f in findings.untraced_must_requirements] == ["req-2"]
    assert [f.node_id for f in findings.unknown_trace_references] == ["cap-1"]
    assert findings.traced_ratio == 0.5


def test_cross_reference_no_must_functional_is_trivially_100():
    graph = RequirementGraph(graph_id="g", nodes=[_node("q", kind="quality")])
    model = SystemModel(
        system_name="s", requirements_ref=RequirementsReference(graph_id="g", graph_hash="h")
    )
    findings = cross_reference(graph, model)
    assert findings.traced_ratio == 1.0
    assert findings.untraced_must_requirements == []
