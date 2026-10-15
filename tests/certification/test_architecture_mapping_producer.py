"""Production tests for the source-derived architectural mapping producer."""
from certification.campaign.plan_builder import build_artifacts_for
from certification.corpus.corpus import default_corpus
from autonomous_api.app.engine.source_bound_full_stack import (
    produce_architecture_mapping,
    source_snapshot_from_plan_artifacts,
)


def test_isr_mapping_producer_preserves_real_node_and_edge_identity_deterministically():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = source_snapshot_from_plan_artifacts(artifacts)

    first = produce_architecture_mapping(snapshot)
    second = produce_architecture_mapping(snapshot)

    assert first == second
    # The current ISR cannot yet represent all five required layers, so the
    # producer must expose a blocker rather than publish an incomplete map.
    assert first.mapping is None
    assert first.blockers
    assert any(item.code == "MAP-FE-001" for item in first.blockers)
    assert any(item.code == "MAP-EFFECT-001" for item in first.blockers)
    assert any(item.code == "MAP-CONSEQ-001" for item in first.blockers)


def test_mapping_producer_does_not_claim_completion_when_source_lacks_required_semantics():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = source_snapshot_from_plan_artifacts(artifacts)

    result = produce_architecture_mapping(snapshot)

    assert not result.complete
    assert result.mapping is None
    assert all(item.code and item.message for item in result.blockers)


def test_mapping_producer_rejects_dangling_isr_relationships():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = source_snapshot_from_plan_artifacts(artifacts)
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    edges = dict(graph["edges"])
    edge_id = next(iter(edges))
    edge = dict(edges[edge_id])
    edge["target_id"] = "missing:target"
    edges[edge_id] = edge
    graph["edges"] = edges
    revision["graph"] = graph
    snapshot["revision"] = revision

    result = produce_architecture_mapping(snapshot)

    assert result.mapping is None
    assert any(item.code == "MAP-008" for item in result.blockers)
