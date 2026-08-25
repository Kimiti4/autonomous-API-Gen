"""SqlSequencePersistence -- Postgres binding for the SequencePersistence port.

Implements the full port required by PersistedSequenceStore:
  1. atomic_next  -- single-statement atomic increment (INSERT ... ON CONFLICT
     DO UPDATE ... RETURNING), safe under arbitrary concurrency (V1-07).
  2. read_current -- current allocated value (== last returned sequence).
  3. insert_envelope -- stores the FULL EvolutionEventEnvelope JSON with
     (stream_id, sequence) as PRIMARY KEY: a duplicate persist raises
     IntegrityError and must NOT be swallowed.
  4. read_after   -- sequence > after ORDER BY sequence ASC LIMIT limit.

DDL lives in schema.sql (canonical). This module never issues DDL.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.contracts.events import EvolutionEventEnvelope

_ATOMIC_NEXT_SQL = text(
    "INSERT INTO observation_stream_counters (stream_id, next_val) "
    "VALUES (:sid, 1) "
    "ON CONFLICT (stream_id) "
    "DO UPDATE SET next_val = observation_stream_counters.next_val + 1 "
    "RETURNING next_val - 1"
)
_READ_CURRENT_SQL = text(
    "SELECT next_val - 1 FROM observation_stream_counters WHERE stream_id = :sid"
)
_INSERT_ENVELOPE_SQL = text(
    "INSERT INTO observation_events (stream_id, sequence, event_type, occurred_at, envelope) "
    "VALUES (:sid, :seq, :etype, :occurred_at, CAST(:envelope AS jsonb))"
)
_READ_AFTER_SQL = text(
    "SELECT envelope FROM observation_events "
    "WHERE stream_id = :sid AND sequence > :after "
    "ORDER BY sequence ASC LIMIT :limit"
)


class SqlSequencePersistence:
    """Engine-backed binding. Accepts an AsyncEngine (not a session factory):
    every operation opens its own short-lived connection so concurrent writers
    cannot share transaction state."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def atomic_next(self, stream_id: str) -> int:
        async with self._engine.begin() as conn:
            result = await conn.execute(_ATOMIC_NEXT_SQL, {"sid": stream_id})
            return result.scalar_one()

    async def read_current(self, stream_id: str) -> int:
        async with self._engine.connect() as conn:
            result = await conn.execute(_READ_CURRENT_SQL, {"sid": stream_id})
            row = result.scalar()
            return row if row is not None else -1

    async def insert_envelope(self, envelope: EvolutionEventEnvelope) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                _INSERT_ENVELOPE_SQL,
                {
                    "sid": envelope.streamId,
                    "seq": envelope.sequence,
                    "etype": envelope.eventType,
                    "occurred_at": envelope.occurredAt,
                    "envelope": envelope.model_dump_json(),
                },
            )

    async def read_after(
        self, stream_id: str, after: int, limit: int
    ) -> list[EvolutionEventEnvelope]:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                _READ_AFTER_SQL,
                {"sid": stream_id, "after": after, "limit": limit},
            )
            return [EvolutionEventEnvelope.model_validate_json(r[0]) for r in result]
