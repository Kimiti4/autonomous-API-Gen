"""Deterministic candidate patch manifests and admission checks."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

@dataclass(frozen=True)
class FileChange:
    path: str
    before_digest: str
    after_digest: str
    change_type: str

@dataclass(frozen=True)
class CandidatePatch:
    candidate_id: str
    workspace_id: str
    source_revision: str
    base_digest: str
    changes: tuple[FileChange, ...]
    patch_digest: str

def build_candidate_patch(
    candidate_id: str,
    workspace_id: str,
    source_revision: str,
    base_digest: str,
    changes: Iterable[FileChange],
) -> CandidatePatch:
    ordered=tuple(sorted(changes,key=lambda c:(c.path,c.change_type,c.before_digest,c.after_digest)))
    if not candidate_id or not workspace_id or not source_revision:
        raise ValueError("missing-candidate-patch-identity")
    if any(not c.path or not c.change_type for c in ordered):
        raise ValueError("invalid-candidate-file-change")
    canonical="|".join(
        f"{c.path}:{c.before_digest}:{c.after_digest}:{c.change_type}" for c in ordered
    )
    digest=sha256(f"{candidate_id}|{workspace_id}|{source_revision}|{base_digest}|{canonical}".encode()).hexdigest()
    return CandidatePatch(candidate_id,workspace_id,source_revision,base_digest,ordered,digest)

def require_patch_matches_workspace(
    patch: CandidatePatch,
    *,
    candidate_id: str,
    workspace_id: str,
    source_revision: str,
    base_digest: str,
) -> None:
    if (patch.candidate_id,patch.workspace_id,patch.source_revision,patch.base_digest) != (
        candidate_id,workspace_id,source_revision,base_digest
    ):
        raise ValueError("candidate-patch-baseline-mismatch")
