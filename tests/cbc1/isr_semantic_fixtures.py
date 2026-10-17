"""Pure-dict ISR snapshot fixture shared by CBC-1 projection tests.

The snapshot is built entirely from explicit literals so it is importable in
every environment (root pythonpath, PYTHONPATH=autonomous-api, pip-installed
autonomous_api) without plan-artifact or package side effects. Its node,
edge, requirement-graph, and canonical contract payloads mirror the proven
complete snapshot used by tests/certification/test_architecture_mapping_producer.py
so produce_architecture_mapping() reaches canonical_ready() on this input.
"""
from __future__ import annotations

_NODES: dict[str, dict] = {
    "requirement:project-create": {
        "id": "requirement:project-create", "type": "requirement_ref",
        "properties": {
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
        },
    },
    "capability:project-create": {
        "id": "capability:project-create", "type": "capability",
        "properties": {
            "name": "Create project",
            "description": "Create a project in a workspace",
        },
    },
    "ui:route:projects": {
        "id": "ui:route:projects", "type": "frontend_route",
        "properties": {
            "path": "/projects",
            "frontend_contract": {
                "schema_version": "1", "contract_id": "frontend:projects",
                "routes": ["/projects"], "api_contract_id": "projects",
                "quality_obligation_ids": [], "state_domains": ["projects"],
                "interaction_flows": ["create-project"],
                "accessibility_requirements": [],
                "observability_requirements": [],
                "modules": [{
                    "module_id": "projects-page",
                    "responsibility": "Manage projects",
                    "dependencies": [],
                    "invariants": ["project-name-non-empty"],
                }],
                "data_flows": [{
                    "flow_id": "create-project", "source": "projects-page",
                    "destination": "POST /projects", "contract": "projects",
                    "failure_policy": "show-error",
                }],
                "security_boundaries": ["policy:project-owner"],
                "failure_states": ["create-failed"], "design_constraints": [],
            },
        },
    },
    "ui:interaction:create-project": {
        "id": "ui:interaction:create-project", "type": "frontend_interaction",
        "properties": {"action": "create_project", "flow_id": "create-project"},
    },
    "api:projects": {
        "id": "api:projects", "type": "api",
        "properties": {
            "operations": [{
                "operation_id": "create_project", "method": "POST",
                "path": "/projects",
            }],
            "global_error_contract": {"schema": "ProblemDetails"},
            "auth_scheme": "bearer",
            "api_contract": {
                "schema_version": "1", "contract_id": "projects",
                "operations": [{
                    "operation_id": "create_project", "method": "POST",
                    "path": "/projects",
                    "request_schema": None, "response_schema": None,
                    "authorization_policy": "policy:project-owner",
                    "errors": [], "idempotency_required": True,
                    "paginated": False, "version": "v1",
                }],
                "global_error_contract": "problem-json",
                "auth_scheme": "bearer", "schemas": [],
            },
        },
    },
    "service:projects": {
        "id": "service:projects", "type": "service",
        "properties": {
            "responsibility": "Manage projects",
            "backend_contract": {
                "schema_version": "1", "contract_id": "backend:projects",
                "domain_modules": ["projects"], "api_contract_id": "projects",
                "quality_obligation_ids": [],
                "persistence_targets": ["dm:projects"],
                "event_targets": [], "observability_requirements": [],
                "modules": [{
                    "module_id": "service:projects",
                    "responsibility": "Manage projects",
                    "dependencies": [],
                    "invariants": ["project-name-non-empty"],
                }],
                "data_flows": [
                    {
                        "flow_id": "create-project", "source": "create_project",
                        "destination": "dm:projects", "contract": "project-record",
                        "failure_policy": "rollback",
                    },
                    {
                        "flow_id": "projects-write", "source": "create_project",
                        "destination": "dm:projects", "contract": "project-record",
                        "failure_policy": "rollback",
                    },
                ],
                "security_boundaries": ["policy:project-owner"],
                "failure_modes": ["store-unavailable", "idempotency-conflict"],
            },
        },
    },
    "dm:projects": {
        "id": "dm:projects", "type": "data_model",
        "properties": {
            "fields": [{
                "name": "project_id", "type": "string",
                "required": True, "unique": True,
            }],
            "invariants": ["project_id is unique"],
        },
    },
    "policy:project-owner": {
        "id": "policy:project-owner", "type": "security_policy",
        "properties": {
            "policy_id": "policy:project-owner", "enforcement": "runtime",
            "allowed_roles": ["owner"],
        },
    },
    "effect:create-project": {
        "id": "effect:create-project", "type": "effect",
        "properties": {
            "effect_type": "create", "idempotency_policy": "required",
            "replay_policy": "deduplicate", "failure_policy": "rollback",
            "effect_path": {
                "operation_id": "create_project",
                "frontend_flow_id": "create-project",
                "domain_module": "projects",
                "effect_id": "effect:create-project",
                "authorization_boundary": "policy:project-owner",
                "consequence": "consequence:duplicate",
            },
        },
    },
    "invariant:project-name": {
        "id": "invariant:project-name", "type": "invariant",
        "properties": {
            "expression": "project.name is non-empty",
            "enforcement_point": "database",
            "verification_method": "integration_test",
        },
    },
    "consequence:duplicate": {
        "id": "consequence:duplicate", "type": "consequence",
        "properties": {
            "trigger": "duplicate request",
            "outcome": "return prior result",
            "failure_policy": "no duplicate side effect",
            "effect_consequence": {
                "effect_id": "effect:create-project",
                "persistence": "dm:projects",
                "event": "none", "idempotency_key": "request-id",
                "uniqueness_constraint": "project-id",
                "retry_policy": "bounded",
                "concurrency_policy": "optimistic-lock",
                "recovery_policy": "return-prior-result",
            },
        },
    },
}

_EDGES: dict[str, dict] = {
    "edge:capability-requirement": {
        "id": "edge:capability-requirement", "type": "satisfies",
        "source_id": "capability:project-create",
        "target_id": "requirement:project-create", "properties": {},
    },
    "edge:capability-service": {
        "id": "edge:capability-service", "type": "implemented_by",
        "source_id": "capability:project-create",
        "target_id": "service:projects", "properties": {},
    },
    "edge:service-data": {
        "id": "edge:service-data", "type": "persists",
        "source_id": "service:projects",
        "target_id": "dm:projects", "properties": {},
    },
    "edge:route-api": {
        "id": "edge:route-api", "type": "routes_to",
        "source_id": "ui:route:projects",
        "target_id": "api:projects", "properties": {},
    },
    "edge:interaction-api": {
        "id": "edge:interaction-api", "type": "invokes",
        "source_id": "ui:interaction:create-project",
        "target_id": "api:projects", "properties": {},
    },
    "edge:api-effect": {
        "id": "edge:api-effect", "type": "causes_effect",
        "source_id": "api:projects",
        "target_id": "effect:create-project", "properties": {},
    },
    "edge:effect-invariant": {
        "id": "edge:effect-invariant", "type": "requires_invariant",
        "source_id": "effect:create-project",
        "target_id": "invariant:project-name", "properties": {},
    },
    "edge:consequence-effect": {
        "id": "edge:consequence-effect", "type": "consequence_of",
        "source_id": "consequence:duplicate",
        "target_id": "effect:create-project", "properties": {},
    },
}


def complete_canonical_snapshot() -> dict:
    """Return a self-contained ISR snapshot whose canonical projection is ready.

    Mirrors the complete fixture contract of
    tests/certification/test_architecture_mapping_producer.py: every typed
    node carries the explicit fields and canonical contract payloads the
    producer validates (frontend/api/backend contracts, effect_path,
    effect_consequence) and the authoritative requirement graph matches the
    requirement_ref node fields exactly.
    """
    nodes = {key: dict(value) for key, value in _NODES.items()}
    edges = {key: dict(value) for key, value in _EDGES.items()}
    return {
        "schema": "source-bound-plan-snapshot/1",
        "source_refs": sorted(set(nodes) | {"REQ-PROJECT-001"}),
        "plan": {"plan_id": "plan-fixture", "isr_id": "isr-fixture", "services": []},
        "revision": {
            "system_id": "system-fixture",
            "revision_id": "rev-fixture-1",
            "content_hash": "e" * 64,
            "graph": {"nodes": nodes, "edges": edges},
        },
        "genome": {"genes": []},
        "requirement_graph": {
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
        },
        "declared_hashes": {
            "requirement_graph_hash": "f" * 64,
            "genome_hash": "9" * 64,
            "plan_hash": "0" * 64,
            "isr_content_hash": "e" * 64,
        },
    }
