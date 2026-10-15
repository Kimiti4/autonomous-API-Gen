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
