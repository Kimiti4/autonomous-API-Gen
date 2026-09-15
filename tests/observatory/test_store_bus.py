"""Observatory store + bus tests: integrity, idempotency, non-blocking fan-out."""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest

from observatory.backend.domain import (
    EventCategory, new_event)
from observatory.backend.store import SqliteEventStore, StoreIntegrityError


def _event(subject_id: str = "SUBJ-1", **overrides):
    base = {"category": EventCategory.RUNTIME, "source": "test",
            "type": "process_started", "subject_id": subject_id}
    base.update(overrides)
    return new_event(**base)


class Store(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = SqliteEventStore(
            os.path.join(self._tmp.name, "obs.sqlite3"))
        self.store.init()
        # LIFO: tmp.cleanup registered first so store.close runs first.
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.store.close)

    def test_append_and_read(self):
        event = _event(id="evt-fixed-1")
        self.assertTrue(self.store.append(event))
        fetched = self.store.get_event("evt-fixed-1")
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched.subject_id, "SUBJ-1")

    def test_idempotent_reinsert(self):
        event = _event(id="evt-fixed-2")
        self.assertTrue(self.store.append(event))
        self.assertFalse(self.store.append(event))

    def test_hash_conflict_raises(self):
        self.store.append(_event(id="evt-fixed-3"))
        with self.assertRaises(StoreIntegrityError):
            self.store.append(_event(id="evt-fixed-3", type="other_type"))

    def test_missing_returns_none(self):
        self.assertIsNone(self.store.get_event("evt-nope"))

    def test_subject_ordering(self):
        self.store.append(_event(id="e1"))
        self.store.append(_event(id="e2"))
        events = self.store.events_by_subject("SUBJ-1")
        self.assertEqual([e.id for e in events], ["e1", "e2"])

    def test_counts(self):
        self.store.append(_event(id="e1"))
        self.store.append(_event(
            id="e2", category=EventCategory.EVIDENCE, subject_id="E-1"))
        self.assertEqual(self.store.count_events(), 2)
        self.assertEqual(
            self.store.count_events_by_category(EventCategory.EVIDENCE), 1)


class Bus(unittest.TestCase):
    def test_publish_fanout(self):
        from observatory.backend.bus import AsyncEventBus

        async def scenario():
            bus = AsyncEventBus()
            first = bus.subscribe()
            second = bus.subscribe()
            await bus.publish(_event(id="evt-bus-1"))
            received_first = await asyncio.wait_for(first.get(), timeout=5)
            received_second = await asyncio.wait_for(second.get(), timeout=5)
            return received_first, received_second

        first, second = asyncio.run(scenario())
        self.assertEqual(first.id, "evt-bus-1")
        self.assertEqual(second.id, "evt-bus-1")

    def test_unsubscribe(self):
        from observatory.backend.bus import AsyncEventBus

        async def scenario():
            bus = AsyncEventBus()
            queue = bus.subscribe()
            bus.unsubscribe(queue)
            await bus.publish(_event(id="evt-bus-2"))
            return queue.empty()

        self.assertTrue(asyncio.run(scenario()))

    def test_slow_consumer_does_not_block(self):
        from observatory.backend.bus import AsyncEventBus

        async def scenario():
            bus = AsyncEventBus(max_queue_size=2)
            queue = bus.subscribe()
            for index in range(5):
                await bus.publish(_event(id=f"evt-flood-{index}"))
            return not queue.empty()

        self.assertTrue(asyncio.run(scenario()))


if __name__ == "__main__":
    unittest.main()
