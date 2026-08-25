"""DB-backed SequenceStore. The concrete DB binding is injected via a port
so this module never imports SQLAlchemy/asyncpg/etc. (plugin-first).

Constitutional requirements for the concrete binding (see sql_binding.py):
1. atomic_next MUST be an atomic DB increment.
2. insert_envelope stores the FULL EvolutionEventEnvelope JSON with
   (stream_id, sequence) as a UNIQUE key.
3. read_after filters sequence > after ORDER BY sequence ASC LIMIT limit.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.contracts.events import EvolutionEventEnvelope


@runtime_checkable
class SequencePersistence(Protocol):
    """Implement this against the existing DB snapshot infrastructure."""

    async def atomic_next(self, stream_id: str) -> int: ...

    async def read_current(self, stream_id: str) -> int: ...

    async def insert_envelope(self, envelope: EvolutionEventEnvelope) -> None: ...

    async def read_after(
        self, stream_id: str, after: int, limit: int
    ) -> list: ...


class PersistedSequenceStore:
    """Drop-in SequenceStore backed by any SequencePersistence binding."""

    def __init__(self, persistence: SequencePersistence) -> None:
        self._db = persistence

    async def next(self, stream_id: str) -> int:
        # MUST be an atomic increment in the DB (row lock / sequence object).
        return await self._db.atomic_next(stream_id)

    async def current(self, stream_id: str) -> int:
        return await self._db.read_current(stream_id)

    async def persist(self, envelope: EvolutionEventEnvelope) -> None:
        await self._db.insert_envelope(envelope)

    async def replay(
        self, stream_id: str, after: int, limit: int
    ) -> list:
        return await self._db.read_after(stream_id, after, limit)