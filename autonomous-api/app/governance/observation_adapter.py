"""GovernanceObservationAdapter (§2.7) — implements the observation layer's
CanonicalGovernanceAccessor by reading this subsystem's materialized state.

The observation layer remains a pure, non-authoritative projection; this
adapter is the only bridge.
"""
from __future__ import annotations

from typing import Optional


class GovernanceObservationAdapter:
    """Implements CanonicalGovernanceAccessor (see
    app.observation.projectors.base)."""

    def __init__(self, governance, evidence=None) -> None:
        self._g = governance
        self._evidence = evidence

    async def get_generation_governance(self, generation: int) -> list:
        return await self._g.materialize_generation(generation)

    async def get_candidate_governance(self, candidate_id: str):
        return await self._g.materialize_candidate(candidate_id)

    async def get_evidence(self, evidence_id: str) -> Optional[dict]:
        if self._evidence is None:
            return None
        return await self._evidence.get(evidence_id)