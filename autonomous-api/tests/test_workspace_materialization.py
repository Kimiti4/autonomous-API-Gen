import hashlib
import pytest

from app.engine.governed_workspace import materialize_workspace
from app.engine.artifact_changes import propose_change_set
from app.engine.workspace_materialization import materialize_to_directory, materialize_change_set


def ws():
    a = b"print('a')\n"
    b = b"print('b')\n"
    return materialize_workspace(
        workspace_id="ws",
        baseline_digest="base",
        artifacts={
            "src/a.py": (hashlib.sha256(a).hexdigest(), len(a), "source"),
            "src/b.py": (hashlib.sha256(b).hexdigest(), len(b), "source"),
        },
    )


def test_materializes_verified_workspace(tmp_path):
    workspace = ws()
    contents = {"src/a.py": b"print('a')\n", "src/b.py": b"print('b')\n"}
    result = materialize_to_directory(workspace, root=str(tmp_path), contents=contents)
    assert (tmp_path / "src/a.py").read_bytes() == contents["src/a.py"]
    assert result.artifacts[0].digest == workspace.artifacts[0].content_digest


def test_rejects_unverified_source_content(tmp_path):
    with pytest.raises(ValueError, match="materialization-content-digest-mismatch"):
        materialize_to_directory(
            ws(), root=str(tmp_path),
            contents={"src/a.py": b"tampered", "src/b.py": b"print('b')\n"},
        )


def test_materializes_change_set_and_rehashes_result(tmp_path):
    workspace = ws()
    new = b"print('updated')\n"
    new_digest = hashlib.sha256(new).hexdigest()
    change = propose_change_set(
        workspace,
        change_set_id="cs",
        work_id="w",
        mutations={"src/a.py": ("modify", workspace.artifacts[0].content_digest, new_digest, "repair")},
    )
    updated, result = materialize_change_set(
        workspace,
        change,
        root=str(tmp_path),
        contents={"src/a.py": b"print('a')\n", "src/b.py": b"print('b')\n"},
        resulting_contents={"src/a.py": new},
    )
    assert (tmp_path / "src/a.py").read_bytes() == new
    assert next(a for a in updated.artifacts if a.path == "src/a.py").content_digest == new_digest
    assert result.artifacts[0].digest == new_digest


def test_rejects_result_digest_mismatch(tmp_path):
    workspace = ws()
    change = propose_change_set(
        workspace,
        change_set_id="cs",
        work_id="w",
        mutations={"src/a.py": ("modify", workspace.artifacts[0].content_digest, "expected", "repair")},
    )
    with pytest.raises(ValueError, match="materialization-result-digest-mismatch"):
        materialize_change_set(
            workspace, change, root=str(tmp_path),
            contents={"src/a.py": b"print('a')\n", "src/b.py": b"print('b')\n"},
            resulting_contents={"src/a.py": b"wrong"},
        )
