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


def _complete_semantic_snapshot(snapshot):
    snapshot = dict(snapshot)
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    # Use a deliberately small, fully specified graph so this test proves
    # the producer contract rather than inheriting unrelated corpus gaps.
    nodes = {}
    edges = {}

    def node(node_id, node_type, properties):
        nodes[node_id] = {"id": node_id, "type": node_type, "properties": properties}

    def edge(edge_id, edge_type, source_id, target_id):
        edges[edge_id] = {
            "id": edge_id, "type": edge_type,
            "source_id": source_id, "target_id": target_id, "properties": {},
        }

    node("ui:route:projects", "frontend_route", {"path": "/projects"})
    node("ui:interaction:create-project", "frontend_interaction", {"action": "create_project", "flow_id": "flow:create-project"})
    node("api:projects", "api", {
        "operations": [{"operation_id": "create_project", "method": "POST", "path": "/projects"}],
        "global_error_contract": {"schema": "ProblemDetails"},
        "auth_scheme": "bearer",
    })
    node("service:projects", "service", {"responsibility": "Manage projects"})
    node("policy:project-owner", "security_policy", {
        "policy_id": "policy:project-owner", "enforcement": "runtime",
        "allowed_roles": ["owner"],
    })
    node("effect:create-project", "effect", {
        "effect_type": "create", "idempotency_policy": "required",
        "replay_policy": "deduplicate", "failure_policy": "rollback",
    })
    node("invariant:project-name", "invariant", {
        "expression": "project.name is non-empty",
        "enforcement_point": "database", "verification_method": "integration_test",
    })
    node("consequence:duplicate", "consequence", {
        "trigger": "duplicate request", "outcome": "return prior result",
        "failure_policy": "no duplicate side effect",
    })
    edge("edge:route-api", "routes_to", "ui:route:projects", "api:projects")
    edge("edge:interaction-api", "invokes", "ui:interaction:create-project", "api:projects")
    edge("edge:api-effect", "causes_effect", "api:projects", "effect:create-project")
    edge("edge:effect-invariant", "requires_invariant", "effect:create-project", "invariant:project-name")
    edge("edge:consequence-effect", "consequence_of", "consequence:duplicate", "effect:create-project")
    graph["nodes"], graph["edges"] = nodes, edges
    revision["graph"] = graph
    snapshot["revision"] = revision
    snapshot["source_refs"] = sorted(set(snapshot.get("source_refs", ())) | set(nodes))
    return snapshot


def test_typed_isr_semantics_lower_to_all_five_mapping_layers():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))

    result = produce_architecture_mapping(snapshot)

    assert result.complete
    assert result.mapping is not None
    assert set(("frontend", "api", "backend", "effects", "consequences")).issubset(result.mapping)
    assert result.mapping["frontend"]["routes"][0]["id"] == "ui:route:projects"
    assert result.mapping["effects"][0]["id"] == "effect:create-project"
    assert result.mapping["consequences"]["invariants"][0]["id"] == "invariant:project-name"
    assert result.mapping["provenance"]["source_hash"]


def test_typed_effect_missing_replay_policy_blocks_full_mapping():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    nodes = dict(graph["nodes"])
    effect = dict(nodes["effect:create-project"])
    props = dict(effect["properties"])
    del props["replay_policy"]
    effect["properties"] = props
    nodes["effect:create-project"] = effect
    graph["nodes"] = nodes
    revision["graph"] = graph
    snapshot["revision"] = revision

    result = produce_architecture_mapping(snapshot)

    assert not result.complete
    assert result.mapping is None
    assert any(item.code == "MAP-EFFECT-002" for item in result.blockers)


def test_missing_cross_layer_relationship_blocks_mapping_even_when_nodes_are_complete():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    edges = dict(graph["edges"])
    del edges["edge:route-api"]
    graph["edges"] = edges
    revision["graph"] = graph
    snapshot["revision"] = revision

    result = produce_architecture_mapping(snapshot)

    assert not result.complete
    assert result.mapping is None
    assert any(item.code == "MAP-REL-001" for item in result.blockers)


def test_semantic_source_mutation_changes_source_binding_hash():
    artifacts = build_artifacts_for(default_corpus()[0])
    original = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    changed = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))

    revision = dict(changed["revision"])
    graph = dict(revision["graph"])
    nodes = dict(graph["nodes"])
    api = dict(nodes["api:projects"])
    props = dict(api["properties"])
    props["operations"] = [
        {"operation_id": "create_project", "method": "PUT", "path": "/projects/{project_id}"}
    ]
    api["properties"] = props
    nodes["api:projects"] = api
    graph["nodes"] = nodes
    revision["graph"] = graph
    changed["revision"] = revision

    original_result = produce_architecture_mapping(original)
    changed_result = produce_architecture_mapping(changed)

    assert original_result.complete and changed_result.complete
    assert original_result.mapping["provenance"]["source_hash"] != changed_result.mapping["provenance"]["source_hash"]
    assert original_result.mapping["api"] != changed_result.mapping["api"]
