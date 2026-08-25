"""Governance storage ports (§2.6). Plugin-first; no storage specifics leak."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GovernanceEventStore(Protocol):
    """Append-only event log, partitioned per candidate."""

    async def append(self, candidate_id: str, events: list) -> None: ...

    async def load(self, candidate_id: str) -> list: ...

    async def load_generation(self, generation: int) -> list: ...


@runtime_checkable
class GovernanceReferenceStore(Protocol):
    """Council / gates / policies registry (mutable reference data)."""

    async def save_council(self, composition) -> None: ...

    async def load_council(self): ...

    async def save_gate(self, gate) -> None: ...

    async def load_gates(self) -> list: ...

    async def save_policy(self, policy) -> None: ...

    async def load_policies(self) -> list: ...