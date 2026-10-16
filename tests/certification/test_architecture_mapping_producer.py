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

    node("requirement:project-create", "requirement_ref", {
        "requirement_id": "REQ-PROJECT-001",
        "semantic_content": "An authorized workspace member can create a project.",
        "requirement_kind": "functional",
        "priority": "must",
        "acceptance_criteria": ["a project is created in the selected workspace"],
        "source_refs": ["taskflow-requirements.md#REQ-PROJECT-001"],
        "resolution_ref": None,
        "source_ref": "taskflow-requirements.md#REQ-PROJECT-001",
        "revision": "1",
        "verification_method": "integration_test",
    })
    node("capability:project-create", "capability", {
        "name": "Create project", "description": "Create a project in a workspace",
    })
    node("ui:route:projects", "frontend_route", {"path": "/projects"})
    node("ui:interaction:create-project", "frontend_interaction", {"action": "create_project", "flow_id": "flow:create-project"})
    node("api:projects", "api", {
        "operations": [{"operation_id": "create_project", "method": "POST", "path": "/projects"}],
        "global_error_contract": {"schema": "ProblemDetails"},
        "auth_scheme": "bearer",
    })
    node("service:projects", "service", {"responsibility": "Manage projects"})
    node("dm:projects", "data_model", {
        "fields": [{"name": "project_id", "type": "string", "required": True, "unique": True}],
        "invariants": ["project_id is unique"],
    })
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
    edge("edge:capability-requirement", "satisfies", "capability:project-create", "requirement:project-create")
    edge("edge:capability-service", "implemented_by", "capability:project-create", "service:projects")
    edge("edge:service-data", "persists", "service:projects", "dm:projects")
    edge("edge:route-api", "routes_to", "ui:route:projects", "api:projects")
    edge("edge:interaction-api", "invokes", "ui:interaction:create-project", "api:projects")
    edge("edge:api-effect", "causes_effect", "api:projects", "effect:create-project")
    edge("edge:effect-invariant", "requires_invariant", "effect:create-project", "invariant:project-name")
    edge("edge:consequence-effect", "consequence_of", "consequence:duplicate", "effect:create-project")
    graph["nodes"], graph["edges"] = nodes, edges
    revision["graph"] = graph
    snapshot["revision"] = revision
    snapshot["source_refs"] = sorted(set(snapshot.get("source_refs", ())) | set(nodes) | {"REQ-PROJECT-001"})
    snapshot["requirement_graph"] = {
        "schema_version": "1",
        "nodes": {
            "REQ-PROJECT-001": {
                "id": "REQ-PROJECT-001",
                "kind": "functional",
                "statement": "An authorized workspace member can create a project.",
                "priority": "must",
                "acceptance_criteria": ["a project is created in the selected workspace"],
                "source_refs": ["taskflow-requirements.md#REQ-PROJECT-001"],
            },
        },
        "edges": {},
    }
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
    assert result.mapping["requirement_obligations"][0]["requirement_id"] == "REQ-PROJECT-001"
    assert result.mapping["requirement_obligations"][0]["service_id"] == "service:projects"
    assert result.mapping["requirement_obligations"][0]["verification_method"] == "integration_test"
    assert result.mapping["consequences"]["invariants"][0]["id"] == "invariant:project-name"
    assert result.mapping["provenance"]["source_hash"]



def test_mapping_producer_emits_canonical_ir_only_when_every_layer_is_explicit():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    nodes = {key: dict(value) for key, value in graph["nodes"].items()}

    frontend_contract = {
        "schema_version": "1", "contract_id": "frontend:projects",
        "routes": ["/projects"], "api_contract_id": "projects",
        "quality_obligation_ids": [], "state_domains": ["projects"],
        "interaction_flows": ["create-project"], "accessibility_requirements": [],
        "observability_requirements": [],
        "modules": [{"module_id": "projects-page", "responsibility": "Manage projects", "dependencies": [], "invariants": ["project-name-non-empty"]}],
        "data_flows": [{"flow_id": "create-project", "source": "projects-page", "destination": "POST /projects", "contract": "projects", "failure_policy": "show-error"}],
        "security_boundaries": ["policy:project-owner"], "failure_states": ["create-failed"], "design_constraints": [],
    }
    api_contract = {
        "schema_version": "1", "contract_id": "projects",
        "operations": [{
            "operation_id": "create_project", "method": "POST", "path": "/projects",
            "request_schema": None, "response_schema": None,
            "authorization_policy": "policy:project-owner", "errors": [],
            "idempotency_required": True, "paginated": False, "version": "v1",
        }],
        "global_error_contract": "problem-json", "auth_scheme": "bearer", "schemas": [],
    }
    backend_contract = {
        "schema_version": "1", "contract_id": "backend:projects",
        "domain_modules": ["projects"], "api_contract_id": "projects",
        "quality_obligation_ids": [], "persistence_targets": ["dm:projects"],
        "event_targets": [], "observability_requirements": [],
        "modules": [{"module_id": "service:projects", "responsibility": "Manage projects", "dependencies": [], "invariants": ["project-name-non-empty"]}],
        "data_flows": [{"flow_id": "projects-write", "source": "create_project", "destination": "dm:projects", "contract": "project-record", "failure_policy": "rollback"}],
        "security_boundaries": ["policy:project-owner"], "failure_modes": ["store-unavailable"],
    }
    nodes["ui:route:projects"]["properties"]["frontend_contract"] = frontend_contract
    nodes["api:projects"]["properties"]["api_contract"] = api_contract
    nodes["service:projects"]["properties"]["backend_contract"] = backend_contract
    nodes["effect:create-project"]["properties"]["effect_path"] = {
        "operation_id": "create_project", "frontend_flow_id": "create-project",
        "domain_module": "projects", "effect_id": "effect:create-project",
        "authorization_boundary": "policy:project-owner", "consequence": "consequence:duplicate",
    }
    nodes["consequence:duplicate"]["properties"]["effect_consequence"] = {
        "effect_id": "effect:create-project", "persistence": "dm:projects",
        "event": "none", "idempotency_key": "request-id",
        "uniqueness_constraint": "project-id", "retry_policy": "bounded",
        "concurrency_policy": "optimistic-lock", "recovery_policy": "return-prior-result",
    }
    graph["nodes"] = nodes
    revision["graph"] = graph
    snapshot["revision"] = revision
    snapshot["source_refs"] = sorted(set(snapshot["source_refs"]) | {"REQ-PROJECT-001"})
    result = produce_architecture_mapping(snapshot)

    assert result.complete
    assert result.canonical_ready, result.canonical_blockers
    assert result.canonical_mapping is not None
    assert set(result.canonical_mapping) == {
        "frontend", "api", "backend", "effects", "consequences",
        "requirement_bindings", "provenance",
    }
    assert result.canonical_mapping["api"]["operations"][0]["operation_id"] == "create_project"
    assert result.canonical_mapping["requirement_bindings"][0]["requirement_id"] == "REQ-PROJECT-001"

    from app.engine.source_bound_full_stack import SourceBoundSemanticCorrespondenceVerifier
    from compiler.core.repository import build_repository
    files = {"app.py": "def create_project(): return {'created': True}"}
    mapping = dict(result.canonical_mapping)
    provenance = dict(mapping["provenance"])
    provenance["candidate_hash"] = build_repository(files).content_hash
    mapping["provenance"] = provenance
    verified = SourceBoundSemanticCorrespondenceVerifier().verify_bound(
        {
            "source_artifacts": snapshot,
            "explicit_mapping": mapping,
            "candidate_files": files,
        },
        build_repository(files).content_hash,
    )
    assert verified.passed, verified.findings


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


def test_requirement_without_authoritative_semantics_cannot_be_mapped():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    nodes = dict(graph["nodes"])
    requirement = dict(nodes["requirement:project-create"])
    props = dict(requirement["properties"])
    del props["semantic_content"]
    requirement["properties"] = props
    nodes["requirement:project-create"] = requirement
    graph["nodes"] = nodes
    revision["graph"] = graph
    snapshot["revision"] = revision

    result = produce_architecture_mapping(snapshot)

    assert result.mapping is None
    assert any(item.code == "MAP-REQ-002" for item in result.blockers)


def test_authorization_requirement_without_enforcement_policy_edge_is_blocked():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    nodes = dict(graph["nodes"])
    requirement = dict(nodes["requirement:project-create"])
    props = dict(requirement["properties"])
    props["requirement_kind"] = "authorization"
    requirement["properties"] = props
    nodes["requirement:project-create"] = requirement
    edges = dict(graph["edges"])
    edges["edge:capability-requirement"] = {
        "id": "edge:capability-requirement", "type": "satisfies",
        "source_id": "capability:project-create", "target_id": "requirement:project-create",
        "properties": {},
    }
    graph["nodes"], graph["edges"] = nodes, edges
    revision["graph"] = graph
    snapshot["revision"] = revision

    result = produce_architecture_mapping(snapshot)

    assert result.mapping is None
    assert any(item.code == "MAP-REQ-SEC-001" for item in result.blockers)


def test_api_operation_without_absolute_path_is_rejected():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    nodes = dict(graph["nodes"])
    api = dict(nodes["api:projects"])
    props = dict(api["properties"])
    props["operations"] = [{
        "operation_id": "create_project", "method": "POST", "path": "projects"
    }]
    api["properties"] = props
    nodes["api:projects"] = api
    graph["nodes"] = nodes
    revision["graph"] = graph
    snapshot["revision"] = revision

    result = produce_architecture_mapping(snapshot)

    assert result.mapping is None
    assert any(item.code == "MAP-API-007" for item in result.blockers)


def test_architecture_without_requirement_references_is_not_publishable():
    artifacts = build_artifacts_for(default_corpus()[0])
    snapshot = _complete_semantic_snapshot(source_snapshot_from_plan_artifacts(artifacts))
    revision = dict(snapshot["revision"])
    graph = dict(revision["graph"])
    nodes = dict(graph["nodes"])
    edges = dict(graph["edges"])
    nodes.pop("requirement:project-create")
    nodes.pop("capability:project-create")
    edges.pop("edge:capability-requirement")
    edges.pop("edge:capability-service")
    graph["nodes"], graph["edges"] = nodes, edges
    revision["graph"] = graph
    snapshot["revision"] = revision

    result = produce_architecture_mapping(snapshot)

    assert result.mapping is None
    assert any(item.code == "MAP-REQ-000" for item in result.blockers)
