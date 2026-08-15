"""D4: ContextGraph - the canonical, content-hashed representation of a
prompt's inputs.
"""
import pytest

from tiannara.domain.models.context_graph import (
    ContextGraph,
    ContextKind,
    ContextNode,
    EvidenceFragment,
)
from tiannara.domain.models.intelligence import TaskKind
from tiannara.domain.models.system_model import Priority


def _node(node_id, priority=Priority.SHOULD, pad=0):
    payload = {"summary": "s" + ("x" * pad)}
    return ContextNode(
        node_id=node_id,
        kind=ContextKind.CAPABILITY,
        priority=priority,
        title=node_id,
        payload=payload,
    )


def test_derive_is_deterministic():
    first = ContextGraph.derive(TaskKind.EXTRACTION, [_node("a"), _node("b")])
    second = ContextGraph.derive(TaskKind.EXTRACTION, [_node("a"), _node("b")])
    assert first.graph_id == second.graph_id
    assert first.content_hash() == second.content_hash()
    assert first.graph_id.startswith("cg-")


def test_node_order_is_semantic():
    forward = ContextGraph.derive(TaskKind.EXTRACTION, [_node("a"), _node("b")])
    backward = ContextGraph.derive(TaskKind.EXTRACTION, [_node("b"), _node("a")])
    assert forward.content_hash() != backward.content_hash()


def test_duplicate_node_ids_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        ContextGraph(
            graph_id="g", task_kind=TaskKind.SYNTHESIS,
            nodes=[_node("a"), _node("a")],
        )


def test_node_render_is_labelled_and_canonical():
    rendered = _node("a").render()
    assert rendered.startswith("### [capability:should] a")
    assert '"summary"' in rendered


def test_evidence_fragment_relevance_bounds():
    with pytest.raises(Exception):
        EvidenceFragment(fragment_id="e1", title="t", kind="k", relevance=1.5)
