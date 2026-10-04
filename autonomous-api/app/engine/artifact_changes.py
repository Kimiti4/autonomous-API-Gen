"""Deterministic, reviewable artifact mutations for ESAP workspaces."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping

from .governed_workspace import GovernedWorkspace, WorkspaceArtifact


@dataclass(frozen=True)
class ArtifactMutation:
    mutation_id: str
    workspace_id: str
    path: str
    operation: str
    expected_digest: str | None
    resulting_digest: str | None
    rationale: str
    work_id: str


@dataclass(frozen=True)
class ChangeSet:
    change_set_id: str
    workspace_id: str
    parent_digest: str
    mutations: tuple[ArtifactMutation, ...]
    proposed: bool = True

    def canonical_payload(self) -> dict[str, object]:
        return {
            "change_set_id": self.change_set_id,
            "workspace_id": self.workspace_id,
            "parent_digest": self.parent_digest,
            "mutations": [
                {
                    "mutation_id": m.mutation_id,
                    "workspace_id": m.workspace_id,
                    "path": m.path,
                    "operation": m.operation,
                    "expected_digest": m.expected_digest,
                    "resulting_digest": m.resulting_digest,
                    "rationale": m.rationale,
                    "work_id": m.work_id,
                }
                for m in self.mutations
            ],
            "proposed": self.proposed,
        }

    def digest(self) -> str:
        import json
        return hashlib.sha256(
            json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def propose_change_set(
    workspace: GovernedWorkspace,
    *,
    change_set_id: str,
    work_id: str,
    mutations: Mapping[str, tuple[str, str | None, str | None, str]],
) -> ChangeSet:
    if not change_set_id:
        raise ValueError("changeset-missing-id")
    if not work_id:
        raise ValueError("changeset-missing-work-id")

    known = {a.path: a for a in workspace.artifacts}
    rows = []
    for path, (operation, expected_digest, resulting_digest, rationale) in mutations.items():
        if path not in known and operation != "create":
            raise ValueError("changeset-unknown-artifact:" + path)
        if operation not in {"create", "modify", "delete"}:
            raise ValueError("changeset-invalid-operation:" + operation)
        if operation in {"modify", "delete"} and expected_digest != known[path].content_digest:
            raise ValueError("changeset-stale-artifact:" + path)
        if operation == "delete" and resulting_digest is not None:
            raise ValueError("changeset-delete-has-result:" + path)
        if operation in {"create", "modify"} and not resulting_digest:
            raise ValueError("changeset-missing-result-digest:" + path)
        if not rationale:
            raise ValueError("changeset-missing-rationale:" + path)

        mutation_id = hashlib.sha256(
            f"{workspace.workspace_id}|{work_id}|{path}|{operation}|{expected_digest}|{resulting_digest}".encode()
        ).hexdigest()[:16]
        rows.append(
            ArtifactMutation(
                mutation_id, workspace.workspace_id, path, operation,
                expected_digest, resulting_digest, rationale, work_id,
            )
        )

    return ChangeSet(
        change_set_id=change_set_id,
        workspace_id=workspace.workspace_id,
        parent_digest=workspace.verify_digest(),
        mutations=tuple(sorted(rows, key=lambda m: m.path)),
    )


def apply_change_set(
    workspace: GovernedWorkspace,
    change_set: ChangeSet,
) -> GovernedWorkspace:
    if change_set.workspace_id != workspace.workspace_id:
        raise ValueError("changeset-workspace-mismatch")
    if not change_set.proposed:
        raise ValueError("changeset-not-proposed")
    if change_set.parent_digest != workspace.verify_digest():
        raise ValueError("changeset-parent-mismatch")

    inventory = {a.path: a for a in workspace.artifacts}
    for mutation in change_set.mutations:
        current = inventory.get(mutation.path)
        if mutation.operation in {"modify", "delete"}:
            if current is None or current.content_digest != mutation.expected_digest:
                raise ValueError("changeset-concurrent-modification:" + mutation.path)
        if mutation.operation == "create":
            if current is not None:
                raise ValueError("changeset-create-conflict:" + mutation.path)
            inventory[mutation.path] = WorkspaceArtifact(
                mutation.path, mutation.resulting_digest, 0, "generated"
            )
        elif mutation.operation == "modify":
            inventory[mutation.path] = WorkspaceArtifact(
                mutation.path, mutation.resulting_digest, current.size_bytes, current.artifact_type
            )
        elif mutation.operation == "delete":
            del inventory[mutation.path]

    return GovernedWorkspace(
        workspace_id=workspace.workspace_id,
        baseline_digest=change_set.digest(),
        artifacts=tuple(sorted(inventory.values(), key=lambda a: a.path)),
    )
