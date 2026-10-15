from types import SimpleNamespace

from autonomous_api.app.engine.source_bound_full_stack import (
    project_source_bound_full_stack,
    source_snapshot_from_plan_artifacts,
)


class _Dumpable:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self):
        return self.payload


def _plan_artifacts(requirement_text="read item"):
    return SimpleNamespace(
        plan=_Dumpable({"plan_id": "plan-1", "isr_id": "isr-1", "services": []}),
        revision=_Dumpable({
            "system_id": "system-1", "revision_id": "rev-1",
            "content_hash": "a" * 64,
            "graph": {"nodes": {"isr:domain:item": {"id": "isr:domain:item"}}},
        }),
        genome=_Dumpable({"genes": []}),
        requirement_graph=_Dumpable({
            "nodes": {
                "req:item": {"id": "req:item", "statement": requirement_text},
            },
            "edges": {},
        }),
        requirement_graph_hash="b" * 64,
        genome_hash="c" * 64,
        plan_hash="d" * 64,
    )


def test_missing_mapping_fails_closed_without_inventing_ir():
    result = project_source_bound_full_stack(
        source_artifacts={"source_refs": ["req:1"], "requirements": ["create workspace"]},
        candidate_files={"app.py": "pass"},
    )
    assert result.status == "blocked"
    assert result.inputs is None
    assert not result.ready
    assert any(blocker.code == "SBFS-004" for blocker in result.blockers)


def test_incomplete_architecture_mapping_fails_closed():
    result = project_source_bound_full_stack(
        source_artifacts={"source_refs": ["req:1"]},
        candidate_files={"app.py": "pass"},
        explicit_mapping={
            "api": {"operations": []},
            "provenance": {"source_refs": ["req:1"]},
        },
    )
    assert result.status == "blocked"
    assert result.inputs is None
    missing = {b.message for b in result.blockers if b.code == "SBFS-005"}
    assert any("frontend" in message for message in missing)
    assert any("backend" in message for message in missing)
    assert any("effects" in message for message in missing)
    assert any("consequences" in message for message in missing)


def test_mapping_must_reference_known_source_ids_when_available():
    result = project_source_bound_full_stack(
        source_artifacts={"source_refs": ["req:known"]},
        candidate_files={"app.py": "pass"},
        explicit_mapping={
            "frontend": {},
            "api": {},
            "backend": {},
            "effects": [],
            "consequences": [],
            "provenance": {"source_refs": ["req:invented"]},
        },
    )
    assert result.status == "blocked"
    assert any(b.code == "SBFS-008" for b in result.blockers)


def test_source_and_candidate_mutations_change_their_digests():
    source = {"source_refs": ["req:1"], "requirements": ["read item"]}
    candidate = {"app.py": "def read_item(): return 1"}

    first = project_source_bound_full_stack(
        source_artifacts=source, candidate_files=candidate
    )
    changed_source = project_source_bound_full_stack(
        source_artifacts={**source, "requirements": ["read item with authorization"]},
        candidate_files=candidate,
    )
    changed_candidate = project_source_bound_full_stack(
        source_artifacts=source,
        candidate_files={"app.py": "def read_item(): return None"},
    )

    assert first.source_hash != changed_source.source_hash
    assert first.candidate_hash != changed_candidate.candidate_hash


def test_empty_candidate_manifest_fails_closed():
    result = project_source_bound_full_stack(
        source_artifacts={"source_refs": ["req:1"]},
        candidate_files={},
    )
    assert result.status == "blocked"
    assert result.candidate_hash == ""
    assert any(b.code == "SBFS-002" for b in result.blockers)



def test_mapping_blocks_when_source_inventory_is_absent():
    result = project_source_bound_full_stack(
        source_artifacts={"requirements": ["read item"]},
        candidate_files={"app.py": "pass"},
        explicit_mapping={
            "frontend": {},
            "api": {},
            "backend": {},
            "effects": [],
            "consequences": [],
            "provenance": {"source_refs": ["req:1"]},
        },
    )
    assert result.status == "blocked"
    assert any(b.code == "SBFS-010" for b in result.blockers)


def test_complete_shape_is_still_not_claimed_as_semantically_ready():
    result = project_source_bound_full_stack(
        source_artifacts={"source_refs": ["req:1"]},
        candidate_files={"app.py": "pass"},
        explicit_mapping={
            "frontend": {"routes": ["/items"]},
            "api": {"operations": [{"operation_id": "list_items"}]},
            "backend": {"modules": ["items"]},
            "effects": [],
            "consequences": [],
            "provenance": {"source_refs": ["req:1"]},
        },
    )
    assert result.status == "mapping_present_unverified"
    assert result.inputs is None
    assert result.ready is False



def test_snapshot_uses_real_plan_artifact_fields_and_inventories_ids():
    snapshot = source_snapshot_from_plan_artifacts(_plan_artifacts())
    assert snapshot["schema"] == "source-bound-plan-snapshot/1"
    assert "req:item" in snapshot["source_refs"]
    assert "isr:domain:item" in snapshot["source_refs"]
    assert snapshot["plan"]["plan_id"] == "plan-1"
    assert snapshot["revision"]["content_hash"] == "a" * 64


def test_snapshot_digest_changes_when_requirement_graph_changes():
    first = source_snapshot_from_plan_artifacts(_plan_artifacts("read item"))
    changed = source_snapshot_from_plan_artifacts(
        _plan_artifacts("read item only after authorization")
    )
    first_projection = project_source_bound_full_stack(
        source_artifacts=first, candidate_files={"app.py": "pass"}
    )
    changed_projection = project_source_bound_full_stack(
        source_artifacts=changed, candidate_files={"app.py": "pass"}
    )
    assert first_projection.source_hash != changed_projection.source_hash


def test_snapshot_rejects_plan_artifacts_without_source_identifiers():
    artifacts = _plan_artifacts()
    artifacts.requirement_graph = _Dumpable({"nodes": {}, "edges": {}})
    artifacts.revision = _Dumpable({
        "content_hash": "a" * 64, "graph": {"nodes": {}}
    })
    try:
        source_snapshot_from_plan_artifacts(artifacts)
    except ValueError as exc:
        assert "no canonical requirement/ISR identifiers" in str(exc)
    else:
        raise AssertionError("missing source identifiers must fail closed")



def _complete_explicit_mapping():
    return {
        "frontend": {
            "schema_version": "1", "contract_id": "frontend:items",
            "routes": ["/items"], "api_contract_id": "items",
            "quality_obligation_ids": [], "state_domains": ["items"],
            "interaction_flows": ["list-items"], "accessibility_requirements": [],
            "observability_requirements": [], "modules": [{
                "module_id": "items-page", "responsibility": "Render items",
                "dependencies": [], "invariants": [],
            }],
            "data_flows": [{
                "flow_id": "list-items", "source": "items-page",
                "destination": "GET /items", "contract": "items-list",
                "failure_policy": "show-error",
            }],
            "security_boundaries": ["authenticated-user"],
            "failure_states": ["load-failed"], "design_constraints": [],
        },
        "api": {
            "schema_version": "1", "contract_id": "items",
            "operations": [{
                "operation_id": "list_items", "method": "GET", "path": "/items",
                "request_schema": None, "response_schema": None,
                "authorization_policy": "authenticated-user", "errors": [],
                "idempotency_required": False, "paginated": False, "version": "v1",
            }],
            "global_error_contract": "problem-json", "auth_scheme": "bearer",
            "schemas": [],
        },
        "backend": {
            "schema_version": "1", "contract_id": "backend:items",
            "domain_modules": ["items"], "api_contract_id": "items",
            "quality_obligation_ids": [], "persistence_targets": ["items-store"],
            "event_targets": [], "observability_requirements": [],
            "modules": [{
                "module_id": "items", "responsibility": "Read items",
                "dependencies": [], "invariants": ["read-only"],
            }],
            "data_flows": [{
                "flow_id": "items-read", "source": "items-api",
                "destination": "items-store", "contract": "item-record",
                "failure_policy": "fail-closed",
            }],
            "security_boundaries": ["authenticated-user"], "failure_modes": ["store-unavailable"],
        },
        "effects": [],
        "consequences": [],
        "provenance": {"source_refs": ["req:item", "isr:domain:item"]},
    }


def test_explicit_mapping_lowers_to_canonical_ir_without_inferred_defaults():
    from autonomous_api.app.engine.source_bound_full_stack import (
        lower_explicit_mapping_to_full_stack_ir,
    )

    lowered = lower_explicit_mapping_to_full_stack_ir(_complete_explicit_mapping())
    assert lowered.frontend is not None
    assert lowered.api is not None
    assert lowered.backend is not None
    assert lowered.api.operations[0].authorization_policy == "authenticated-user"
    assert lowered.frontend.routes == ("/items",)
    assert lowered.backend.persistence_targets == ("items-store",)
    assert lowered.source_refs == ("isr:domain:item", "req:item")
    assert lowered.structurally_valid


def test_explicit_mapping_rejects_unknown_fields_instead_of_dropping_them():
    from autonomous_api.app.engine.source_bound_full_stack import (
        lower_explicit_mapping_to_full_stack_ir,
    )

    mapping = _complete_explicit_mapping()
    mapping["api"]["transport_guess"] = "http"
    lowered = lower_explicit_mapping_to_full_stack_ir(mapping)
    assert not lowered.structurally_valid
    assert any("unsupported keys" in finding for finding in lowered.findings)


def test_state_changing_api_without_explicit_effect_is_represented_for_gate_failure():
    from autonomous_api.app.engine.source_bound_full_stack import (
        lower_explicit_mapping_to_full_stack_ir,
    )
    from autonomous_api.app.engine.full_stack_verification import verify_full_stack

    mapping = _complete_explicit_mapping()
    mapping["api"]["operations"][0]["method"] = "POST"
    lowered = lower_explicit_mapping_to_full_stack_ir(mapping)
    assert lowered.structurally_valid
    report = verify_full_stack(
        lowered.frontend, lowered.api, lowered.backend,
        lowered.effects, lowered.consequences,
    )
    assert not report.passed
    assert any(f.code == "FS-EFFECT-002" for f in report.effects)



def test_architecture_fact_extraction_preserves_plan_and_isr_relationships():
    from autonomous_api.app.engine.source_bound_full_stack import (
        extract_architecture_facts,
    )

    artifacts = _plan_artifacts()
    artifacts.plan = _Dumpable({
        "plan_id": "plan-1", "isr_id": "isr-1",
        "services": [{
            "id": "svc:catalog", "name": "Catalog",
            "data_models": [{"id": "model:item", "entity_name": "Item"}],
            "published_events": [{"id": "event:item-created", "name": "ItemCreated"}],
            "consumed_events": [{"id": "event:price-updated", "name": "PriceUpdated"}],
        }],
        "security": [{"policy_id": "policy:catalog-read"}],
    })
    artifacts.revision = _Dumpable({
        "system_id": "system-1", "revision_id": "rev-1",
        "content_hash": "a" * 64,
        "graph": {
            "nodes": {"isr:domain:item": {"kind": "domain", "name": "Item"}},
            "edges": {"edge:owns": {"source": "isr:domain:item", "target": "isr:service:catalog"}},
        },
    })
    snapshot = source_snapshot_from_plan_artifacts(artifacts)
    facts = extract_architecture_facts(snapshot)

    assert facts.services == ({"id": "svc:catalog", "name": "Catalog"},)
    assert facts.data_models[0] == {
        "id": "model:item", "entity_name": "Item", "service_id": "svc:catalog"
    }
    assert facts.published_events[0]["id"] == "event:item-created"
    assert facts.consumed_events[0]["id"] == "event:price-updated"
    assert facts.security_policy_ids == ("policy:catalog-read",)
    assert facts.isr_nodes[0]["id"] == "isr:domain:item"
    assert facts.isr_edges[0]["source"] == "isr:domain:item"
    assert not facts.complete_for_full_stack


def test_architecture_fact_mutation_changes_source_hash_and_fact_value():
    from autonomous_api.app.engine.source_bound_full_stack import (
        extract_architecture_facts,
    )

    first_artifacts = _plan_artifacts()
    changed_artifacts = _plan_artifacts()
    for artifacts, name in ((first_artifacts, "Catalog"), (changed_artifacts, "Inventory")):
        artifacts.plan = _Dumpable({
            "plan_id": "plan-1", "isr_id": "isr-1",
            "services": [{
                "id": "svc:catalog", "name": name,
                "data_models": [{"id": "model:item", "entity_name": "Item"}],
                "published_events": [], "consumed_events": [],
            }],
            "security": [{"policy_id": "policy:read"}],
        })
    first = extract_architecture_facts(source_snapshot_from_plan_artifacts(first_artifacts))
    changed = extract_architecture_facts(source_snapshot_from_plan_artifacts(changed_artifacts))
    assert first.services[0]["name"] != changed.services[0]["name"]
    assert first.source_hash != changed.source_hash


def test_missing_plan_semantics_are_blockers_not_inferred_defaults():
    from autonomous_api.app.engine.source_bound_full_stack import (
        extract_architecture_facts,
    )

    artifacts = _plan_artifacts()
    artifacts.plan = _Dumpable({
        "plan_id": "plan-1", "isr_id": "isr-1",
        "services": [{"id": "svc:empty", "name": "Empty"}],
        "security": [],
    })
    facts = extract_architecture_facts(source_snapshot_from_plan_artifacts(artifacts))
    assert not facts.complete_for_full_stack
    assert any("no explicit data models" in blocker for blocker in facts.blockers)
    assert any("no explicit event declarations" in blocker for blocker in facts.blockers)
    assert any("no explicit security policy identifiers" in blocker for blocker in facts.blockers)



def test_source_bound_lowering_rejects_unbound_mapping_digests():
    from autonomous_api.app.engine.source_bound_full_stack import (
        lower_source_bound_candidate,
    )

    source = {"source_refs": ["req:item", "isr:domain:item"], "revision": "rev-1"}
    candidate = {"app.py": "print('candidate')"}
    mapping = _complete_explicit_mapping()
    mapping["provenance"]["source_hash"] = "0" * 64
    mapping["provenance"]["candidate_hash"] = "1" * 64

    result = lower_source_bound_candidate(
        source_artifacts=source,
        candidate_files=candidate,
        explicit_mapping=mapping,
    )
    assert not result.ready_for_verification
    assert result.lowered is not None
    assert any(blocker.code == "SBFS-011" for blocker in result.blockers)
    assert any(blocker.code == "SBFS-012" for blocker in result.blockers)


def test_source_bound_lowering_rejects_provenance_outside_source_snapshot():
    from autonomous_api.app.engine.source_bound_full_stack import (
        _canonical_hash,
        lower_source_bound_candidate,
    )

    source = {"source_refs": ["req:item"], "revision": "rev-1"}
    candidate = {"app.py": "print('candidate')"}
    mapping = _complete_explicit_mapping()
    mapping["provenance"]["source_refs"] = ["req:invented"]
    mapping["provenance"]["source_hash"] = _canonical_hash(source)
    mapping["provenance"]["candidate_hash"] = _canonical_hash(candidate)

    result = lower_source_bound_candidate(
        source_artifacts=source,
        candidate_files=candidate,
        explicit_mapping=mapping,
    )
    assert not result.ready_for_verification
    assert any(blocker.code == "SBFS-008" for blocker in result.blockers)


def test_source_bound_lowering_accepts_matching_source_candidate_and_ir_binding():
    from autonomous_api.app.engine.source_bound_full_stack import (
        _canonical_hash,
        lower_source_bound_candidate,
    )

    source = {"source_refs": ["req:item", "isr:domain:item"], "revision": "rev-1"}
    candidate = {"app.py": "print('candidate')"}
    mapping = _complete_explicit_mapping()
    mapping["provenance"]["source_hash"] = _canonical_hash(source)
    mapping["provenance"]["candidate_hash"] = _canonical_hash(candidate)

    result = lower_source_bound_candidate(
        source_artifacts=source,
        candidate_files=candidate,
        explicit_mapping=mapping,
    )
    assert result.ready_for_verification
    assert result.lowered is not None
    assert result.source_hash == _canonical_hash(source)
    assert result.candidate_hash == _canonical_hash(candidate)



def test_source_bound_lowering_blocks_unmapped_authoritative_requirement():
    from autonomous_api.app.engine.source_bound_full_stack import (
        _canonical_hash,
        lower_source_bound_candidate,
    )

    source = {
        "source_refs": ["req:item", "req:security", "isr:domain:item"],
        "requirement_graph": {
            "nodes": {
                "req:item": {"id": "req:item", "statement": "List items"},
                "req:security": {"id": "req:security", "statement": "Require authentication"},
            },
            "edges": {},
        },
        "revision": "rev-1",
    }
    candidate = {"app.py": "print('candidate')"}
    mapping = _complete_explicit_mapping()
    # Deliberately omit req:security from provenance even though it exists in
    # source_refs and its security intent is not otherwise traceably mapped.
    mapping["provenance"]["source_refs"] = ["req:item", "isr:domain:item"]
    mapping["requirement_bindings"] = [{
        "requirement_id": "req:item", "layer": "api", "target_id": "list_items",
        "requirement_hash": _canonical_hash(source["requirement_graph"]["nodes"]["req:item"]),
    }]
    mapping["provenance"]["source_hash"] = _canonical_hash(source)
    mapping["provenance"]["candidate_hash"] = _canonical_hash(candidate)

    result = lower_source_bound_candidate(
        source_artifacts=source,
        candidate_files=candidate,
        explicit_mapping=mapping,
    )
    assert not result.ready_for_verification
    assert any(
        blocker.code == "SBFS-017" and blocker.source_refs == ("req:security",)
        for blocker in result.blockers
    )


def test_source_bound_lowering_accepts_complete_requirement_reference_coverage():
    from autonomous_api.app.engine.source_bound_full_stack import (
        _canonical_hash,
        lower_source_bound_candidate,
    )

    source = {
        "source_refs": ["req:item", "req:security", "isr:domain:item"],
        "requirement_graph": {
            "nodes": {
                "req:item": {"id": "req:item", "statement": "List items"},
                "req:security": {"id": "req:security", "statement": "Require authentication"},
            },
            "edges": {},
        },
        "revision": "rev-1",
    }
    candidate = {"app.py": "print('candidate')"}
    mapping = _complete_explicit_mapping()
    mapping["provenance"]["source_refs"] = ["req:item", "req:security", "isr:domain:item"]
    mapping["requirement_bindings"] = [
        {"requirement_id": rid, "layer": "api", "target_id": "list_items",
         "requirement_hash": _canonical_hash(node)}
        for rid, node in source["requirement_graph"]["nodes"].items()
    ]
    mapping["provenance"]["source_hash"] = _canonical_hash(source)
    mapping["provenance"]["candidate_hash"] = _canonical_hash(candidate)

    result = lower_source_bound_candidate(
        source_artifacts=source,
        candidate_files=candidate,
        explicit_mapping=mapping,
    )
    assert result.ready_for_verification



def test_typed_requirement_binding_rejects_stale_requirement_content():
    from autonomous_api.app.engine.source_bound_full_stack import (
        _canonical_hash,
        lower_source_bound_candidate,
    )

    source = {
        "source_refs": ["req:item", "isr:domain:item"],
        "requirement_graph": {
            "nodes": {"req:item": {"id": "req:item", "statement": "Read item"}},
            "edges": {},
        },
    }
    candidate = {"app.py": "print('candidate')"}
    mapping = _complete_explicit_mapping()
    mapping["provenance"]["source_refs"] = ["req:item", "isr:domain:item"]
    mapping["requirement_bindings"] = [{
        "requirement_id": "req:item", "layer": "api", "target_id": "list_items",
        "requirement_hash": _canonical_hash({"id": "req:item", "statement": "Old requirement"}),
    }]
    mapping["provenance"]["source_hash"] = _canonical_hash(source)
    mapping["provenance"]["candidate_hash"] = _canonical_hash(candidate)

    result = lower_source_bound_candidate(
        source_artifacts=source, candidate_files=candidate, explicit_mapping=mapping
    )
    assert not result.ready_for_verification
    assert any(blocker.code == "SBFS-023" for blocker in result.blockers)


def test_typed_requirement_binding_rejects_nonexistent_architecture_target():
    from autonomous_api.app.engine.source_bound_full_stack import (
        _canonical_hash,
        lower_source_bound_candidate,
    )

    source = {
        "source_refs": ["req:item", "isr:domain:item"],
        "requirement_graph": {
            "nodes": {"req:item": {"id": "req:item", "statement": "Read item"}},
            "edges": {},
        },
    }
    candidate = {"app.py": "print('candidate')"}
    mapping = _complete_explicit_mapping()
    mapping["provenance"]["source_refs"] = ["req:item", "isr:domain:item"]
    mapping["requirement_bindings"] = [{
        "requirement_id": "req:item", "layer": "api", "target_id": "api:invented",
        "requirement_hash": _canonical_hash(source["requirement_graph"]["nodes"]["req:item"]),
    }]
    mapping["provenance"]["source_hash"] = _canonical_hash(source)
    mapping["provenance"]["candidate_hash"] = _canonical_hash(candidate)

    result = lower_source_bound_candidate(
        source_artifacts=source, candidate_files=candidate, explicit_mapping=mapping
    )
    assert not result.ready_for_verification
    assert any(blocker.code == "SBFS-024" for blocker in result.blockers)



def test_authorization_requirement_rejects_target_without_enforceable_policy():
    from autonomous_api.app.engine.source_bound_full_stack import _validate_semantic_obligations

    source = {"requirement_graph": {"nodes": {
        "req:auth": {"id": "req:auth", "statement": "Only the owner can delete a workspace"}
    }}}
    mapping = {
        "frontend": {}, "api": {}, "backend": {"modules": [{
            "module_id": "workspace_service", "responsibility": "workspace operations",
            "dependencies": [], "invariants": [], "security_boundaries": []
        }]}, "effects": [], "consequences": [],
        "requirement_bindings": [{
            "requirement_id": "req:auth", "layer": "backend",
            "target_id": "workspace_service"
        }]
    }
    blockers = _validate_semantic_obligations(source, mapping)
    assert any(b.code == "SBFS-026" for b in blockers)


def test_authorization_requirement_accepts_explicit_enforcement_contract_only():
    from autonomous_api.app.engine.source_bound_full_stack import _validate_semantic_obligations

    source = {"requirement_graph": {"nodes": {
        "req:auth": {"id": "req:auth", "statement": "Only the owner can delete a workspace"}
    }}}
    mapping = {
        "frontend": {}, "api": {}, "backend": {"modules": [{
            "module_id": "workspace_service", "responsibility": "workspace operations",
            "dependencies": [], "invariants": [],
            "security_boundaries": [{
                "policy_id": "workspace-owner-policy", "enforcement": "middleware"
            }]
        }]}, "effects": [], "consequences": [],
        "requirement_bindings": [{
            "requirement_id": "req:auth", "layer": "backend",
            "target_id": "workspace_service"
        }]
    }
    blockers = _validate_semantic_obligations(source, mapping)
    assert not any(b.code == "SBFS-026" for b in blockers)


def test_api_requirement_must_bind_to_explicit_contract_or_operation():
    from autonomous_api.app.engine.source_bound_full_stack import _validate_semantic_obligations

    source = {"requirement_graph": {"nodes": {
        "req:api": {"id": "req:api", "statement": "The API endpoint returns item details"}
    }}}
    mapping = {
        "frontend": {}, "api": {"operations": [{"operation_id": "get_item"}]},
        "backend": {}, "effects": [], "consequences": [],
        "requirement_bindings": [{
            "requirement_id": "req:api", "layer": "api", "target_id": "get_item"
        }]
    }
    blockers = _validate_semantic_obligations(source, mapping)
    assert any(b.code == "SBFS-027" for b in blockers)
