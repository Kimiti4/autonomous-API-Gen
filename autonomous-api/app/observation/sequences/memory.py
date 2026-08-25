"""Concurrency-safe in-memory SequenceStore. Dev/tests only."""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from app.core.contracts.events import EvolutionEventEnvelope


class InMemorySequenceStore:
    """Concurrency-safe in-memory store. Dev/tests only.

    Invariants:
    - next() is atomic under the lock → strictly monotonic per stream.
    - replay returns envelopes in strict ascending sequence order.
    """

    def __init__(self, *, replay_window: int = 10_000) -> None:
        self._counter: dict = defaultdict(lambda: -1)
        self._log: dict = defaultdict(
            lambda: deque(maxlen=replay_window)
        )
        self._lock = asyncio.Lock()

    async def next(self, stream_id: str) -> int:
        async with self._lock:
            self._counter[stream_id] += 1
            return self._counter[stream_id]

    async def current(self, stream_id: str) -> int:
        async with self._lock:
            return self._counter[stream_id]

    async def persist(self, envelope: EvolutionEventEnvelope) -> None:
        async with self._lock:
            self._log[envelope.streamId].append(envelope)

    async def replay(
        self, stream_id: str, after: int, limit: int
    ) -> list:
        async with self._lock:
            return [
                e for e in self._log[stream_id] if e.sequence > after
            ][:limit]