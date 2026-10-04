import hashlib

import pytest

from app.engine.governed_workspace import materialize_workspace
from app.engine.workspace_materialization import materialize_to_directory
from app.engine.workspace_evidence import materialize_evidence


def test_materialization_produces_content_addressed_evidence(tmp_path):
    data = b"print('hello')\n"
    digest = hashlib.sha256(data).hexdigest()
    workspace = materialize_workspace(
        workspace_id="ws-evidence",
        baseline_digest="base",
        artifacts={"src/main.py": (digest, len(data), "source")},
    )
    materialized = materialize_to_directory(
        workspace, root=str(tmp_path), contents={"src/main.py": data}
    )
    evidence = materialize_evidence(workspace, materialized)

    assert evidence.verified
    assert evidence.workspace_id == "ws-evidence"
    assert evidence.artifacts[0]["digest"] == digest
    assert evidence.verify_digest()
    assert len(evidence.digest) == 64


def test_evidence_rejects_other_workspace():
    data = b"x"
    digest = hashlib.sha256(data).hexdigest()
    workspace = materialize_workspace(
        workspace_id="ws-a", baseline_digest="base",
        artifacts={"a": (digest, 1, "source")},
    )
    other = materialize_workspace(
        workspace_id="ws-b", baseline_digest="base",
        artifacts={"a": (digest, 1, "source")},
    )
    materialized = materialize_to_directory(
        other, root="/tmp/esap-evidence-other", contents={"a": data}
    )
    with pytest.raises(ValueError, match="materialization-evidence-workspace-mismatch"):
        materialize_evidence(workspace, materialized)
