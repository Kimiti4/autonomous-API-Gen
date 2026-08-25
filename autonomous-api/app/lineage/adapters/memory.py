"""In-memory LineageEventStore + LineageGraphIndex (dev/tests).

Production backends: PostgreSQL event log; graph DB (e.g. Neo4j) for the
graph index. Both implement the ports from app.core.lineage.ports.
"""
from __future__ import annotations

from collections import defaultdict


class InMemoryLineageEventStore:
    def __init__(self) -> None:
        self._log: dict = defaultdict(list)

    async def append(self, candidate_id: str, events: list) -> None:
        self._log[candidate_id].extend(events)

    async def load(self, candidate_id: str) -> list:
        return list(self._log.get(candidate_id, []))


class InMemoryLineageGraphIndex:
    """Maintains parent/child edges from origin events."""

    def __init__(self, event_store) -> None:
        self._events = event_store

    async def children_of(self, candidate_id: str) -> list:
        children = []
        for cid in self._events._log:
            events = await self._events.load(cid)
            for e in events:
                if type(e).__name__ == "CandidateOriginRecorded":
                    if candidate_id in e.origin.parentCandidateIds:
                        children.append(cid)
                        break
        return sorted(children)

    async def ancestors_of(self, candidate_id: str) -> list:
        ancestors = []
        frontier = [candidate_id]
        seen = {candidate_id}
        while frontier:
            current = frontier.pop()
            events = await self._events.load(current)
            for e in events:
                if type(e).__name__ == "CandidateOriginRecorded":
                    for parent in e.origin.parentCandidateIds:
                        if parent not in seen:
                            seen.add(parent)
                            ancestors.append(parent)
                            frontier.append(parent)
        return sorted(ancestors)