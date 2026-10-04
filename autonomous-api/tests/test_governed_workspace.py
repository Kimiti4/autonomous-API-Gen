import pytest

from app.engine.governed_workspace import materialize_workspace


def test_workspace_materializes_deterministic_artifact_inventory():
    ws = materialize_workspace(
        workspace_id="ws-1",
        baseline_digest="base",
        artifacts={
            "src/z.py": ("sha-z", 12, "source"),
            "src/a.py": ("sha-a", 8, "source"),
        },
    )
    assert [a.path for a in ws.artifacts] == ["src/a.py", "src/z.py"]
    assert ws.immutable
    assert len(ws.verify_digest()) == 64


def test_workspace_rejects_unsafe_paths_and_missing_identity():
    with pytest.raises(ValueError, match="workspace-invalid-artifact-path"):
        materialize_workspace(
            workspace_id="ws",
            baseline_digest="base",
            artifacts={"../secret": ("sha", 1, "source")},
        )
    with pytest.raises(ValueError, match="workspace-missing-baseline-digest"):
        materialize_workspace(
            workspace_id="ws",
            baseline_digest="",
            artifacts={},
        )


def test_workspace_rejects_invalid_artifact_metadata():
    with pytest.raises(ValueError, match="workspace-missing-artifact-digest"):
        materialize_workspace(
            workspace_id="ws",
            baseline_digest="base",
            artifacts={"src/a.py": ("", 1, "source")},
        )
    with pytest.raises(ValueError, match="workspace-invalid-artifact-size"):
        materialize_workspace(
            workspace_id="ws",
            baseline_digest="base",
            artifacts={"src/a.py": ("sha", -1, "source")},
        )
    with pytest.raises(ValueError, match="workspace-missing-artifact-type"):
        materialize_workspace(
            workspace_id="ws",
            baseline_digest="base",
            artifacts={"src/a.py": ("sha", 1, "")},
        )
