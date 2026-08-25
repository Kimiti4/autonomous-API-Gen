"""The single point where engine/evolution events become envelopes.

The evolution engine calls `dispatcher.emit(...)`; it never builds envelopes,
never touches sequences, never touches WebSockets. This keeps the engine
framework-agnostic (constitution: compiler backends, not core reasoning).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from app.core.contracts.events import (
    EventSource,
    EventType,
    EvolutionEventEnvelope,
    make_envelope,
)
from app.observation.sequences.store import SequenceStore

logger = logging.getLogger("observation.gateway")

Subscriber = Callable[[EvolutionEventEnvelope], Awaitable[None]]


class EventDispatcher:
    def __init__(self, *, store: SequenceStore, source: EventSource) -> None:
        self._store = store
        self._source = source
        self._subscribers: set = set()
        self._lock = asyncio.Lock()

    def subscribe(self, sub: Subscriber) -> Callable[[], None]:
        self._subscribers.add(sub)
        return lambda: self._subscribers.discard(sub)

    async def emit(
        self,
        *,
        stream_id: str,
        event_type: EventType,
        payload,
        correlation_id: str,
        generation: int,
        causation_id: str | None = None,
    ) -> EvolutionEventEnvelope:
        # Serialize allocation+persistence so sequence order == persist order.
        async with self._lock:
            seq = await self._store.next(stream_id)
            envelope = make_envelope(
                stream_id=stream_id,
                sequence=seq,
                event_type=event_type,
                payload=payload,
                correlation_id=correlation_id,
                generation=generation,
                source=self._source,
                causation_id=causation_id,
            )
            await self._store.persist(envelope)

        # Fan-out outside the sequence lock; a slow subscriber must not
        # block sequence allocation. Failures are isolated per subscriber.
        if self._subscribers:
            await asyncio.gather(
                *(self._deliver(s, envelope) for s in list(self._subscribers)),
                return_exceptions=True,
            )
        return envelope

    async def _deliver(
        self, sub: Subscriber, envelope: EvolutionEventEnvelope
    ) -> None:
        try:
            await sub(envelope)
        except Exception:  # noqa: BLE001 — isolation boundary
            logger.exception(
                "subscriber_delivery_failed",
                extra={"event_id": str(envelope.eventId)},
            )