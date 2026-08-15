"""
Lineage Tracker.

Tracks the complete evolutionary history of ISR versions.
Every ISR knows its parents, generation, and the mutations that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.isr.versioning.version import ISRVersion


@dataclass(frozen=True)
class LineageRecord:
    """A single record in the evolutionary lineage."""

    version: ISRVersion
    parent_hashes: tuple[str, ...] = ()
    child_hashes: tuple[str, ...] = ()
    mutation_applied: str = ""
    fitness_before: Optional[dict[str, float]] = None
    fitness_after: Optional[dict[str, float]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evolution_run_id: str = ""
    reasoning: str = ""


class LineageTracker:
    """
    Tracks the complete evolutionary lineage of ISR versions.

    Provides queryable history of all architectural decisions.
    """

    def __init__(self) -> None:
        self._versions: dict[str, ISRVersion] = {}
        self._records: dict[str, LineageRecord] = {}
        self._children: dict[str, list[str]] = {}

    def register(self, version: ISRVersion, record: LineageRecord) -> None:
        self._versions[version.content_hash] = version
        self._records[version.content_hash] = record

        for parent_hash in record.parent_hashes:
            self._children.setdefault(parent_hash, []).append(version.content_hash)

    def get_version(self, content_hash: str) -> Optional[ISRVersion]:
        return self._versions.get(content_hash)

    def get_record(self, content_hash: str) -> Optional[LineageRecord]:
        return self._records.get(content_hash)

    def get_parent(self, content_hash: str) -> Optional[ISRVersion]:
        record = self._records.get(content_hash)
        if record and record.parent_hashes:
            return self._versions.get(record.parent_hashes[0])
        return None

    def get_children(self, content_hash: str) -> list[ISRVersion]:
        child_hashes = self._children.get(content_hash, [])
        return [self._versions[h] for h in child_hashes if h in self._versions]

    def get_ancestors(self, content_hash: str) -> list[ISRVersion]:
        ancestors: list[ISRVersion] = []
        current = content_hash
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            record = self._records.get(current)
            if record and record.parent_hashes:
                parent_hash = record.parent_hashes[0]
                parent = self._versions.get(parent_hash)
                if parent:
                    ancestors.append(parent)
                current = parent_hash
            else:
                break

        return list(reversed(ancestors))

    def get_common_ancestor(self, hash_a: str, hash_b: str) -> Optional[ISRVersion]:
        ancestors_a = {v.content_hash for v in self.get_ancestors(hash_a)}
        ancestors_a.add(hash_a)

        current = hash_b
        visited: set[str] = set()
        while current and current not in visited:
            visited.add(current)
            if current in ancestors_a:
                return self._versions.get(current)
            record = self._records.get(current)
            if record and record.parent_hashes:
                current = record.parent_hashes[0]
            else:
                break

        return None

    @property
    def all_versions(self) -> list[ISRVersion]:
        return list(self._versions.values())

    @property
    def root_versions(self) -> list[ISRVersion]:
        return [v for v in self._versions.values() if v.is_root]

    @property
    def latest_generation(self) -> int:
        if not self._versions:
            return 0
        return max(v.generation for v in self._versions.values())
