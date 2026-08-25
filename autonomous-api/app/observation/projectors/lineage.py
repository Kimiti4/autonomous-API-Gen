"""Lineage projection -- read-only, from canonical LineageSubsystem."""
from __future__ import annotations
from app.observation.projectors.base import ProjectionContract

class LineageProjector:
    def __init__(self, accessor):
        self._accessor = accessor

    async def get_candidate(self, candidate_id: str):
        lineage = await self._accessor.get_candidate_lineage(candidate_id)
        return {
            "metadata": {"contractId": ProjectionContract.LINEAGE[0], "schemaVersion": ProjectionContract.LINEAGE[1]},
            "provenance": {"sourceSubsystem": "lineage", "sourceRevision": "1.0.0"},
            "candidateId": candidate_id,
            "lineage": lineage,
        }
