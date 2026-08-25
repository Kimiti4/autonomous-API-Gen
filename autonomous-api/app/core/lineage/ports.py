"""Lineage storage ports (§3.6). Plugin-first; no storage specifics leak."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LineageEventStore(Protocol):
    """Append-only event log, partitioned per candidate (L-3)."""

    async def append(self, candidate_id: str, events: list) -> None: ...

    async def load(self, candidate_id: str) -> list: ...


@runtime_checkable
class LineageGraphIndex(Protocol):
    """Optional graph queries (impact analysis, ancestor traversal)."""

    async def children_of(self, candidate_id: str) -> list: ...

    async def ancestors_of(self, candidate_id: str) -> list: ...