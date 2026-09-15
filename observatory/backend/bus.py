"""Async non-blocking event bus (fan-out to subscriber queues).

Full queues drop oldest (with loss contained to that subscriber); publish
never blocks the emitter and never raises for slow consumers.
"""
from __future__ import annotations

import asyncio
from typing import Set

from .domain import Event


class AsyncEventBus:
    def __init__(self, max_queue_size: int = 1000) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._max_queue_size = max_queue_size

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: Event) -> None:
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue
