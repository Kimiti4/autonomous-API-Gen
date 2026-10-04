"""Materialize governed workspaces into isolated filesystem state."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
from typing import Mapping

from .artifact_changes import ChangeSet, apply_change_set
from .governed_workspace import GovernedWorkspace


@dataclass(frozen=True)
class MaterializedArtifact:
    path: str
    digest: str
    size_bytes: int


@dataclass(frozen=True)
class WorkspaceMaterialization:
    workspace: GovernedWorkspace
    root: str
    artifacts: tuple[MaterializedArtifact, ...]


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def materialize_to_directory(
    workspace: GovernedWorkspace,
    *,
    root: str,
    contents: Mapping[str, bytes],
) -> WorkspaceMaterialization:
    base = Path(root).resolve()
    rows = []
    for artifact in workspace.artifacts:
        if artifact.path not in contents:
            raise ValueError("materialization-missing-content:" + artifact.path)
        data = contents[artifact.path]
        if _digest_bytes(data) != artifact.content_digest:
            raise ValueError("materialization-content-digest-mismatch:" + artifact.path)
        rows.append(MaterializedArtifact(artifact.path, artifact.content_digest, len(data)))

    for artifact in workspace.artifacts:
        destination = (base / artifact.path).resolve()
        if base not in destination.parents:
            raise ValueError("materialization-path-escape:" + artifact.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents[artifact.path])

    return WorkspaceMaterialization(
        workspace=workspace,
        root=str(base),
        artifacts=tuple(rows),
    )


def materialize_change_set(
    workspace: GovernedWorkspace,
    change_set: ChangeSet,
    *,
    root: str,
    contents: Mapping[str, bytes],
    resulting_contents: Mapping[str, bytes],
) -> tuple[GovernedWorkspace, WorkspaceMaterialization]:
    current = materialize_to_directory(workspace, root=root, contents=contents)
    updated = apply_change_set(workspace, change_set)

    for mutation in change_set.mutations:
        if mutation.operation == "delete":
            destination = (Path(root).resolve() / mutation.path).resolve()
            if Path(root).resolve() not in destination.parents:
                raise ValueError("materialization-path-escape:" + mutation.path)
            if destination.exists():
                destination.unlink()
            continue

        if mutation.path not in resulting_contents:
            raise ValueError("materialization-missing-result-content:" + mutation.path)
        data = resulting_contents[mutation.path]
        if mutation.resulting_digest != _digest_bytes(data):
            raise ValueError("materialization-result-digest-mismatch:" + mutation.path)

        destination = (Path(root).resolve() / mutation.path).resolve()
        if Path(root).resolve() not in destination.parents:
            raise ValueError("materialization-path-escape:" + mutation.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    final = materialize_to_directory(
        updated,
        root=root,
        contents={
            **{p: d for p, d in contents.items() if p not in {m.path for m in change_set.mutations}},
            **dict(resulting_contents),
        },
    )
    return updated, final
