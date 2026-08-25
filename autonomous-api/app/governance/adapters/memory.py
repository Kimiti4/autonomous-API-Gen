"""In-memory GovernanceEventStore + GovernanceReferenceStore (dev/tests).

Production backends (PostgreSQL event log + registry tables) implement the
same ports from app.core.governance.ports.
"""
from __future__ import annotations

from collections import defaultdict

from app.core.contracts.governance import CouncilComposition


class InMemoryGovernanceEventStore:
    def __init__(self) -> None:
        self._log: dict = defaultdict(list)
        self._generation_index: dict = defaultdict(set)

    async def append(self, candidate_id: str, events: list) -> None:
        self._log[candidate_id].extend(events)

    async def load(self, candidate_id: str) -> list:
        return list(self._log.get(candidate_id, []))

    async def load_generation(self, generation: int) -> dict:
        """Returns {candidateId: [events]} for candidates whose decisions
        carry the given generation."""
        result: dict = {}
        for cid, events in self._log.items():
            if any(
                type(e).__name__ == "GovernanceDecisionMade"
                and e.decision.generation == generation
                for e in events
            ):
                result[cid] = list(events)
        return result


class InMemoryGovernanceReferenceStore:
    def __init__(self) -> None:
        self._council: CouncilComposition | None = None
        self._gates: dict = {}
        self._policies: dict = {}

    async def save_council(self, composition) -> None:
        self._council = composition

    async def load_council(self):
        return self._council

    async def save_gate(self, gate) -> None:
        self._gates[gate.gateId] = gate

    async def load_gates(self) -> list:
        return list(self._gates.values())

    async def save_policy(self, policy) -> None:
        self._policies[policy.policyId] = policy

    async def load_policies(self) -> list:
        return list(self._policies.values())