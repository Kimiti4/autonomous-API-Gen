"""SequenceStore protocol — strictly monotonic sequence authority per stream.

Plugin-first: in-memory for dev/tests, persisted for production.
Framework-agnostic: no FastAPI / DB imports here.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.contracts.events import EvolutionEventEnvelope


@runtime_checkable
class SequenceStore(Protocol):
    async def next(self, stream_id: str) -> int:
        """Allocate the next sequence number for `stream_id` (atomic)."""
        ...

    async def current(self, stream_id: str) -> int:
        """Return the highest committed sequence for `stream_id` (-1 if none)."""
        ...

    async def persist(self, envelope: EvolutionEventEnvelope) -> None:
        """Durably record an envelope for later replay."""
        ...

    async def replay(
        self, stream_id: str, after: int, limit: int
    ) -> list:
        """Return envelopes with sequence > after, ascending, at most `limit`."""
        ...