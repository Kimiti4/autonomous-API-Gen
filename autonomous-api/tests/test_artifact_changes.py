import pytest

from app.engine.artifact_changes import apply_change_set, propose_change_set
from app.engine.governed_workspace import materialize_workspace


def workspace():
    return materialize_workspace(
        workspace_id="ws-1",
        baseline_digest="base",
        artifacts={
            "src/a.py": ("sha-a", 10, "source"),
            "src/b.py": ("sha-b", 20, "source"),
        },
    )


def test_proposes_deterministic_changeset_and_applies_it():
    ws = workspace()
    cs = propose_change_set(
        ws,
        change_set_id="cs-1",
        work_id="work-1",
        mutations={
            "src/a.py": ("modify", "sha-a", "sha-a2", "repair defect"),
            "src/new.py": ("create", None, "sha-new", "add required module"),
        },
    )
    assert cs.proposed
    assert [m.path for m in cs.mutations] == ["src/a.py", "src/new.py"]
    assert all(len(m.mutation_id) == 16 for m in cs.mutations)

    updated = apply_change_set(ws, cs)
    assert {a.path for a in updated.artifacts} == {"src/a.py", "src/b.py", "src/new.py"}
    assert next(a for a in updated.artifacts if a.path == "src/a.py").content_digest == "sha-a2"


def test_rejects_stale_or_conflicting_changes():
    ws = workspace()
    with pytest.raises(ValueError, match="changeset-stale-artifact:src/a.py"):
        propose_change_set(
            ws, change_set_id="cs", work_id="w",
            mutations={"src/a.py": ("modify", "wrong", "new", "repair")},
        )

    cs = propose_change_set(
        ws, change_set_id="cs", work_id="w",
        mutations={"src/a.py": ("modify", "sha-a", "new", "repair")},
    )
    changed = materialize_workspace(
        workspace_id="ws-1", baseline_digest="other",
        artifacts={"src/a.py": ("different", 10, "source"), "src/b.py": ("sha-b", 20, "source")},
    )
    with pytest.raises(ValueError, match="changeset-parent-mismatch"):
        apply_change_set(changed, cs)


def test_rejects_invalid_mutation_semantics():
    ws = workspace()
    with pytest.raises(ValueError, match="changeset-invalid-operation"):
        propose_change_set(ws, change_set_id="cs", work_id="w",
                           mutations={"src/a.py": ("rename", "sha-a", "new", "rename")})
    with pytest.raises(ValueError, match="changeset-delete-has-result"):
        propose_change_set(ws, change_set_id="cs", work_id="w",
                           mutations={"src/a.py": ("delete", "sha-a", "new", "remove")})
    with pytest.raises(ValueError, match="changeset-missing-rationale"):
        propose_change_set(ws, change_set_id="cs", work_id="w",
                           mutations={"src/a.py": ("modify", "sha-a", "new", "")})
