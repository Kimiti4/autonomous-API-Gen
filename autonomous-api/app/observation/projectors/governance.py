"""Governance projection -- read-only, flattened, from canonical GovernanceSubsystem."""
from __future__ import annotations
from app.observation.projectors.base import ProjectionContract
from app.core.contracts.governance import CouncilComposition

class GovernanceProjector:
    def __init__(self, accessor):
        self._accessor = accessor

    async def get_generation(self, generation: int):
        states = await self._accessor.get_generation_governance(generation)
        return {
            "metadata": {"contractId": ProjectionContract.CANDIDATES[0], "schemaVersion": ProjectionContract.CANDIDATES[1]},
            "provenance": {"sourceSubsystem": "governance", "sourceRevision": "1.0.0"},
            "generation": generation,
            "candidates": states,
        }

    async def get_candidate(self, candidate_id: str):
        state = await self._accessor.get_candidate_governance(candidate_id)
        return {
            "metadata": {"contractId": ProjectionContract.CANDIDATES[0], "schemaVersion": ProjectionContract.CANDIDATES[1]},
            "provenance": {"sourceSubsystem": "governance", "sourceRevision": "1.0.0"},
            "candidateId": candidate_id,
            "governance": state,
        }
