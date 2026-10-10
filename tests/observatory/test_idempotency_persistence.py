"""Durability and concurrency tests for Observatory idempotency records."""
from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from observatory.backend.domain import EventInput, event_from_input
from observatory.backend.store import SqliteEventStore


REQUEST_HASH = "a" * 64
EVENT_INPUT = {
    "source": "idempotency-test",
    "category": "runtime",
    "type": "process_started",
    "subject_id": "IDEMPOTENCY-DURABILITY",
    "payload": {"purpose": "durability-test"},
}


class IdempotencyDurability(unittest.TestCase):
    def test_idempotency_record_survives_store_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "observatory.sqlite3")
            first_store = SqliteEventStore(db_path)
            first_store.init()
            event = event_from_input(EventInput(**EVENT_INPUT))
            event_id, replayed, inserted = first_store.append_idempotent(
                event, "durability-key", REQUEST_HASH
            )
            self.assertEqual(event_id, event.id)
            self.assertFalse(replayed)
            self.assertTrue(inserted)
            first_store.close()

            reopened = SqliteEventStore(db_path)
            reopened.init()
            try:
                retry_event = event_from_input(EventInput(**EVENT_INPUT))
                retry_id, replayed, inserted = reopened.append_idempotent(
                    retry_event, "durability-key", REQUEST_HASH
                )
                self.assertEqual(retry_id, event.id)
                self.assertTrue(replayed)
                self.assertFalse(inserted)
                self.assertIsNotNone(reopened.get_event(event.id))
                self.assertEqual(reopened.count_events(), 1)
            finally:
                reopened.close()

    def test_concurrent_same_key_inserts_one_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "observatory.sqlite3")
            store = SqliteEventStore(db_path)
            store.init()
            try:
                def submit(_):
                    event = event_from_input(EventInput(**EVENT_INPUT))
                    return store.append_idempotent(
                        event, "concurrent-key", REQUEST_HASH
                    )

                with ThreadPoolExecutor(max_workers=12) as pool:
                    results = list(pool.map(submit, range(48)))

                event_ids = {result[0] for result in results}
                self.assertEqual(len(event_ids), 1)
                self.assertEqual(sum(1 for _, replayed, _ in results if not replayed), 1)
                self.assertEqual(sum(1 for _, _, inserted in results if inserted), 1)
                self.assertEqual(store.count_events(), 1)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
