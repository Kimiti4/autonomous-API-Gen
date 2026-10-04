"""Governed workspace and artifact identities for ESAP execution."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping


@dataclass(frozen=True)
class WorkspaceArtifact:
    path: str
    content_digest: str
    size_bytes: int
    artifact_type: str


@dataclass(frozen=True)
class GovernedWorkspace:
    workspace_id: str
    baseline_digest: str
    artifacts: tuple[WorkspaceArtifact, ...]
    immutable: bool = True

    def canonical_payload(self) -> dict[str, object]:
        return {
            "workspace_id": self.workspace_id,
            "baseline_digest": self.baseline_digest,
            "artifacts": [
                {
                    "path": a.path,
                    "content_digest": a.content_digest,
                    "size_bytes": a.size_bytes,
                    "artifact_type": a.artifact_type,
                }
                for a in self.artifacts
            ],
            "immutable": self.immutable,
        }

    def verify_digest(self) -> str:
        return _digest(self.canonical_payload())


def materialize_workspace(
    *,
    workspace_id: str,
    baseline_digest: str,
    artifacts: Mapping[str, tuple[str, int, str]],
) -> GovernedWorkspace:
    if not workspace_id:
        raise ValueError("workspace-missing-id")
    if not baseline_digest:
        raise ValueError("workspace-missing-baseline-digest")

    rows = []
    for path, (content_digest, size_bytes, artifact_type) in artifacts.items():
        if not path or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("workspace-invalid-artifact-path:" + path)
        if not content_digest:
            raise ValueError("workspace-missing-artifact-digest:" + path)
        if size_bytes < 0:
            raise ValueError("workspace-invalid-artifact-size:" + path)
        if not artifact_type:
            raise ValueError("workspace-missing-artifact-type:" + path)
        rows.append(
            WorkspaceArtifact(path, content_digest, size_bytes, artifact_type)
        )

    return GovernedWorkspace(
        workspace_id=workspace_id,
        baseline_digest=baseline_digest,
        artifacts=tuple(sorted(rows, key=lambda a: a.path)),
    )


def _digest(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
