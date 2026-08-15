"""
Lineage Tracker (Engine-level).

Tracks the evolutionary lineage of all individuals.
Every ISR version knows its parents, generation, and mutations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.engine.individual import Individual


@dataclass(frozen=True)
class LineageEntry:
    individual_id: str
    isr_hash: str
    parent_ids: tuple[str, ...] = ()
    generation: int = 0
    mutation_applied: str = ""
    eir_id: str = ""
    fitness_before: Optional[dict[str, float]] = None
    fitness_after: Optional[dict[str, float]] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    evolution_run_id: str = ""
    reasoning: str = ""


class LineageTracker:
    """
    Tracks complete evolutionary lineage.

    Every individual is recorded with its ancestry, enabling:
    - Full evolutionary tree reconstruction
    - Querying ancestors and descendants
    - Understanding why an architecture is shaped the way it is
    - Reproducing any evolutionary path
    """

    def __init__(self) -> None:
        self._entries: dict[str, LineageEntry] = {}
        self._children: dict[str, list[str]] = {}
        self._by_generation: dict[int, list[str]] = {}

    def record(
        self,
        individual: Individual,
        mutation_applied: str = "",
        eir_id: str = "",
        fitness_before: Optional[dict[str, float]] = None,
        reasoning: str = "",
        run_id: str = "",
    ) -> None:
        entry = LineageEntry(
            individual_id=individual.id,
            isr_hash=individual.isr_hash,
            parent_ids=individual.parent_ids,
            generation=individual.generation,
            mutation_applied=mutation_applied,
            eir_id=eir_id,
            fitness_before=fitness_before,
            fitness_after=individual.fitness.to_dict(),
            evolution_run_id=run_id,
            reasoning=reasoning,
        )
        self._entries[individual.id] = entry

        for parent_id in individual.parent_ids:
            self._children.setdefault(parent_id, []).append(individual.id)

        self._by_generation.setdefault(individual.generation, []).append(individual.id)

    def get_entry(self, individual_id: str) -> Optional[LineageEntry]:
        return self._entries.get(individual_id)

    def get_parents(self, individual_id: str) -> list[LineageEntry]:
        entry = self._entries.get(individual_id)
        if entry is None:
            return []
        return [self._entries[pid] for pid in entry.parent_ids if pid in self._entries]

    def get_children(self, individual_id: str) -> list[LineageEntry]:
        child_ids = self._children.get(individual_id, [])
        return [self._entries[cid] for cid in child_ids if cid in self._entries]

    def get_ancestors(self, individual_id: str) -> list[LineageEntry]:
        ancestors: list[LineageEntry] = []
        visited: set[str] = set()
        queue = [individual_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            entry = self._entries.get(current)
            if entry:
                for pid in entry.parent_ids:
                    if pid not in visited:
                        parent_entry = self._entries.get(pid)
                        if parent_entry:
                            ancestors.append(parent_entry)
                        queue.append(pid)

        return list(reversed(ancestors))

    def get_generation(self, generation: int) -> list[LineageEntry]:
        ids = self._by_generation.get(generation, [])
        return [self._entries[i] for i in ids if i in self._entries]

    def get_mutation_history(self, individual_id: str) -> list[str]:
        ancestors = self.get_ancestors(individual_id)
        entry = self._entries.get(individual_id)
        mutations = [a.mutation_applied for a in ancestors if a.mutation_applied]
        if entry and entry.mutation_applied:
            mutations.append(entry.mutation_applied)
        return mutations

    @property
    def total_records(self) -> int:
        return len(self._entries)

    @property
    def max_generation(self) -> int:
        return max(self._by_generation.keys()) if self._by_generation else 0
