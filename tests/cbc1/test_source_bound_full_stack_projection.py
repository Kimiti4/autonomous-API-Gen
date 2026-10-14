from autonomous_api.app.engine.source_bound_full_stack import (
    project_source_bound_full_stack,
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
