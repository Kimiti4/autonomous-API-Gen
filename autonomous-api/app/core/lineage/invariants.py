"""Lineage invariant enforcement (§3.5, L-1..L-6)."""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from app.core.contracts.lineage import OriginSpec


class LineageInvariantError(Exception):
    """Raised when a command would violate a lineage invariant (L-x)."""


@runtime_checkable
class CandidateRegistry(Protocol):
    """Referential-integrity validator (L-4). Implemented against the
    candidate registry / ISR."""

    async def candidate_exists(self, candidate_id: str) -> bool: ...

    async def requirement_exists(self, requirement_id: str) -> bool: ...


def check_l1_isr_revision_required(isr_revision: str) -> None:
    """L-1: every candidate has exactly one isrRevision (constitutional
    source-of-truth linkage). Empty/missing is rejected."""
    if not isr_revision:
        raise LineageInvariantError(
            "L-1 violated: RecordCandidateOrigin requires isrRevision"
        )


def check_l2_parent_cardinality(origin: OriginSpec) -> None:
    """L-2: non-genesis candidates have >= 1 parent; genesis has zero."""
    if origin.operationType == "genesis" and origin.parentCandidateIds:
        raise LineageInvariantError(
            "L-2 violated: genesis origin must have zero parents"
        )
    if origin.operationType != "genesis" and not origin.parentCandidateIds:
        raise LineageInvariantError(
            "L-2 violated: %s origin requires at least one parent"
            % origin.operationType
        )


async def check_l4_referential_integrity(
    origin: OriginSpec,
    requirement_ids: list,
    registry: Optional[CandidateRegistry],
) -> None:
    """L-4: parents must reference existing candidates; requirements must
    reference ISR requirements."""
    if registry is None:
        return  # no registry bound → validation deferred (declared gap)
    for parent_id in origin.parentCandidateIds:
        if not await registry.candidate_exists(parent_id):
            raise LineageInvariantError(
                "L-4 violated: parent candidate %r does not exist" % parent_id
            )
    for req_id in requirement_ids:
        if not await registry.requirement_exists(req_id):
            raise LineageInvariantError(
                "L-4 violated: requirement %r not present in ISR" % req_id
            )


def check_l5_origin_idempotency(events: list) -> None:
    """L-5: RecordCandidateOrigin may be issued once per candidate."""
    if any(type(e).__name__ == "CandidateOriginRecorded" for e in events):
        raise LineageInvariantError(
            "L-5 violated: candidate already has an origin record"
        )