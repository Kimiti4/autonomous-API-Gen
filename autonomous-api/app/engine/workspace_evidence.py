"""Evidence produced when ESAP materializes a governed workspace."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from .governed_workspace import GovernedWorkspace
from .workspace_materialization import WorkspaceMaterialization


@dataclass(frozen=True)
class WorkspaceMaterializationEvidence:
    schema_version: str
    workspace_id: str
    workspace_digest: str
    root: str
    artifacts: tuple[Mapping[str, object], ...]
    verified: bool
    digest: str

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "workspace_id": self.workspace_id,
            "workspace_digest": self.workspace_digest,
            "root": self.root,
            "artifacts": [dict(a) for a in self.artifacts],
            "verified": self.verified,
        }

    def verify_digest(self) -> bool:
        return self.digest == _digest(self.canonical_payload())

    def to_json(self) -> str:
        return json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"))


def materialize_evidence(
    workspace: GovernedWorkspace,
    materialization: WorkspaceMaterialization,
) -> WorkspaceMaterializationEvidence:
    if materialization.workspace.workspace_id != workspace.workspace_id:
        raise ValueError("materialization-evidence-workspace-mismatch")

    artifacts = tuple(
        {
            "path": artifact.path,
            "digest": artifact.digest,
            "size_bytes": artifact.size_bytes,
        }
        for artifact in sorted(materialization.artifacts, key=lambda a: a.path)
    )
    payload = {
        "schema_version": "esap.workspace-materialization.v1",
        "workspace_id": workspace.workspace_id,
        "workspace_digest": workspace.verify_digest(),
        "root": materialization.root,
        "artifacts": list(artifacts),
        "verified": True,
    }
    return WorkspaceMaterializationEvidence(
        **payload,
        digest=_digest(payload),
    )


def _digest(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
