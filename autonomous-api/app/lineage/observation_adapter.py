"""LineageObservationAdapter (§3.7) — implements the observation layer's
CanonicalLineageAccessor by reading this subsystem's materialized state."""
from __future__ import annotations


class LineageObservationAdapter:
    """Implements CanonicalLineageAccessor (see
    app.observation.projectors.base)."""

    def __init__(self, lineage) -> None:
        self._l = lineage

    async def get_candidate_lineage(self, candidate_id: str):
        return await self._l.materialize(candidate_id)