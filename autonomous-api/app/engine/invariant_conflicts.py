"""Detect and manage conflicts between evidence-backed invariants."""
from __future__ import annotations
from dataclasses import dataclass
from .invariant_contracts import Invariant


@dataclass(frozen=True)
class InvariantConflict:
    conflict_id: str
    invariant_ids: tuple[str, ...]
    domains: tuple[str, ...]
    reason: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ConflictResolution:
    conflict_id: str
    resolution_id: str
    compatible_invariant_ids: tuple[str, ...]
    retired_invariant_ids: tuple[str, ...]
    rationale: str
    evidence: tuple[str, ...]


def detect_conflict(
    conflict_id: str,
    left: Invariant,
    right: Invariant,
    reason: str,
) -> InvariantConflict:
    if left.invariant_id == right.invariant_id:
        raise ValueError("cannot-conflict-with-self")
    evidence = tuple(sorted(set(left.evidence + right.evidence)))
    if not evidence:
        raise ValueError("conflict-requires-evidence")
    return InvariantConflict(
        conflict_id,
        tuple(sorted((left.invariant_id, right.invariant_id))),
        tuple(sorted({left.domain, right.domain})),
        reason,
        evidence,
    )


def resolve_conflict(
    conflict: InvariantConflict,
    resolution_id: str,
    compatible_invariant_ids: tuple[str, ...],
    retired_invariant_ids: tuple[str, ...],
    rationale: str,
    evidence: tuple[str, ...],
) -> ConflictResolution:
    all_ids = set(compatible_invariant_ids) | set(retired_invariant_ids)
    if not all_ids.intersection(conflict.invariant_ids):
        raise ValueError("resolution-must-address-conflict")
    if not rationale:
        raise ValueError("resolution-requires-rationale")
    if not evidence:
        raise ValueError("resolution-requires-evidence")
    if set(compatible_invariant_ids) & set(retired_invariant_ids):
        raise ValueError("invariant-cannot-be-both-compatible-and-retired")
    return ConflictResolution(
        conflict.conflict_id, resolution_id,
        tuple(sorted(compatible_invariant_ids)),
        tuple(sorted(retired_invariant_ids)),
        rationale,
        tuple(sorted(set(evidence))),
    )


def require_conflict_resolution(
    conflict: InvariantConflict,
    resolution: ConflictResolution,
) -> None:
    if resolution.conflict_id != conflict.conflict_id:
        raise ValueError("resolution-conflict-mismatch")
    addressed = (
        set(resolution.compatible_invariant_ids)
        | set(resolution.retired_invariant_ids)
    )
    if not set(conflict.invariant_ids).issubset(addressed):
        raise ValueError("unresolved-invariant-conflict")
