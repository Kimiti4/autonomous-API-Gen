"""
Platform Lineage.

Complete history of platform evolution.
Every platform mutation is recorded with full provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.meta.platform_genome import PlatformGenome
from constitutional_architecture.meta.platform_mutation import PlatformMutation


@dataclass(frozen=True)
class LineageEntry:
    genome_hash: str
    genome_version: int
    parent_hash: Optional[str]
    mutation: Optional[PlatformMutation]
    fitness_score: float = 0.0
    sandbox_passed: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reasoning: str = ""


class PlatformLineage:
    def __init__(self) -> None:
        self._entries: dict[str, LineageEntry] = {}
        self._by_version: dict[int, str] = {}
        self._children: dict[str, list[str]] = {}

    def record(
        self,
        genome: PlatformGenome,
        mutation: Optional[PlatformMutation] = None,
        fitness_score: float = 0.0,
        sandbox_passed: bool = False,
        reasoning: str = "",
    ) -> None:
        entry = LineageEntry(
            genome_hash=genome.content_hash,
            genome_version=genome.version,
            parent_hash=genome.parent_hash,
            mutation=mutation,
            fitness_score=fitness_score,
            sandbox_passed=sandbox_passed,
            reasoning=reasoning,
        )
        self._entries[genome.content_hash] = entry
        self._by_version[genome.version] = genome.content_hash
        if genome.parent_hash:
            self._children.setdefault(genome.parent_hash, []).append(genome.content_hash)

    def get_entry(self, genome_hash: str) -> Optional[LineageEntry]:
        return self._entries.get(genome_hash)

    def get_by_version(self, version: int) -> Optional[LineageEntry]:
        genome_hash = self._by_version.get(version)
        if genome_hash:
            return self._entries.get(genome_hash)
        return None

    def get_children(self, genome_hash: str) -> list[LineageEntry]:
        child_hashes = self._children.get(genome_hash, [])
        return [self._entries[h] for h in child_hashes if h in self._entries]

    def get_ancestors(self, genome_hash: str) -> list[LineageEntry]:
        ancestors: list[LineageEntry] = []
        current_hash: Optional[str] = genome_hash
        while current_hash:
            entry = self._entries.get(current_hash)
            if entry is None:
                break
            ancestors.insert(0, entry)
            current_hash = entry.parent_hash
        return ancestors

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    @property
    def max_version(self) -> int:
        return max(self._by_version.keys()) if self._by_version else 0

    @property
    def best_fitness_entry(self) -> Optional[LineageEntry]:
        if not self._entries:
            return None
        return max(self._entries.values(), key=lambda e: e.fitness_score)
