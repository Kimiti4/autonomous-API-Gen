"""Isolated candidate workspace contracts for existing-repository repair evaluation."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping

@dataclass(frozen=True)
class CandidateWorkspace:
    candidate_id: str
    source_revision: str
    workspace_id: str
    paths: tuple[str, ...]
    isolated: bool
    base_digest: str

@dataclass(frozen=True)
class WorkspacePlan:
    source_revision: str
    workspaces: tuple[CandidateWorkspace, ...]
    digest: str

def plan_candidate_workspaces(
    source_revision: str,
    files: Iterable[tuple[str,str]],
    candidate_ids: Iterable[str],
) -> WorkspacePlan:
    if not source_revision:
        raise ValueError("missing-source-revision")
    ordered=tuple(sorted(files,key=lambda x:x[0]))
    base=sha256("\n".join(f"{p}\0{s}" for p,s in ordered).encode()).hexdigest()
    ids=tuple(sorted(set(candidate_ids)))
    workspaces=tuple(
        CandidateWorkspace(
            cid,
            source_revision,
            sha256(f"{source_revision}|{cid}|{base}".encode()).hexdigest()[:24],
            tuple(p for p,_ in ordered),
            True,
            base,
        )
        for cid in ids
    )
    if len({w.workspace_id for w in workspaces}) != len(workspaces):
        raise ValueError("workspace-identity-collision")
    return WorkspacePlan(
        source_revision,
        workspaces,
        sha256("|".join(w.workspace_id for w in workspaces).encode()).hexdigest(),
    )

def require_isolated_workspace(workspace: CandidateWorkspace) -> None:
    if not workspace.isolated:
        raise ValueError(f"non-isolated-candidate-workspace:{workspace.candidate_id}")
