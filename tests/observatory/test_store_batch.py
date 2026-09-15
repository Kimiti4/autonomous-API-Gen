"""Store-level batch atomicity verification (real SQLite, temp DBs)."""
from __future__ import annotations

from datetime import datetime, timezone

from observatory.backend.domain import new_event
from observatory.backend.store import SqliteEventStore, StoreIntegrityError

FIXED_TIMESTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)


def create_store(tmp_path) -> SqliteEventStore:
    store = SqliteEventStore(str(tmp_path / "store.sqlite3"))
    store.init()
    return store


def test_empty_batch_returns_zero_counts(tmp_path):
    store = create_store(tmp_path)
    try:
        result = store.append_batch([])
        assert result.inserted == 0
        assert result.duplicates == 0
        assert result.accepted_event_ids == []
        assert result.inserted_events == []
    finally:
        store.close()


def test_batch_inserts_multiple_events(tmp_path):
    store = create_store(tmp_path)
    try:
        event_one = new_event(
            source="tiannara.test", category="runtime", type="test_event",
            subject_id="SUBJECT-1", id="evt-batch-1",
            timestamp=FIXED_TIMESTAMP, payload={"summary": "first"})
        event_two = new_event(
            source="tiannara.test", category="runtime", type="test_event",
            subject_id="SUBJECT-2", id="evt-batch-2",
            timestamp=FIXED_TIMESTAMP, payload={"summary": "second"})
        result = store.append_batch([event_one, event_two])
        assert result.inserted == 2
        assert result.duplicates == 0
        assert result.accepted_event_ids == ["evt-batch-1", "evt-batch-2"]
        assert len(result.inserted_events) == 2
        assert store.get_event("evt-batch-1") is not None
        assert store.get_event("evt-batch-2") is not None
    finally:
        store.close()


def test_identical_duplicate_event_is_idempotent(tmp_path):
    store = create_store(tmp_path)
    try:
        event = new_event(
            source="tiannara.test", category="runtime", type="test_event",
            subject_id="SUBJECT-DUPLICATE", id="evt-duplicate",
            timestamp=FIXED_TIMESTAMP, payload={"summary": "duplicate"})
        first_result = store.append_batch([event])
        second_result = store.append_batch([event])
        assert first_result.inserted == 1
        assert first_result.duplicates == 0
        assert second_result.inserted == 0
        assert second_result.duplicates == 1
        assert second_result.accepted_event_ids == ["evt-duplicate"]
        assert second_result.inserted_events == []
    finally:
        store.close()


def test_same_event_id_with_different_hash_is_rejected(tmp_path):
    store = create_store(tmp_path)
    try:
        event = new_event(
            source="tiannara.test", category="runtime", type="test_event",
            subject_id="SUBJECT-CONFLICT", id="evt-conflict",
            timestamp=FIXED_TIMESTAMP, payload={"version": 1})
        store.append_batch([event])
        conflicting_event = event.model_copy(
            update={"payload": {"version": 2}})
        try:
            store.append_batch([conflicting_event])
        except StoreIntegrityError:
            pass
        else:
            raise AssertionError("conflicting duplicate must raise")
    finally:
        store.close()


def test_batch_is_atomic_on_integrity_conflict(tmp_path):
    store = create_store(tmp_path)
    try:
        event_one = new_event(
            source="tiannara.test", category="runtime", type="test_event",
            subject_id="SUBJECT-A", id="evt-atomic-1",
            timestamp=FIXED_TIMESTAMP, payload={"summary": "event one"})
        event_two = new_event(
            source="tiannara.test", category="runtime", type="test_event",
            subject_id="SUBJECT-B", id="evt-atomic-2",
            timestamp=FIXED_TIMESTAMP, payload={"summary": "event two"})
        conflicting_event = event_one.model_copy(
            update={"payload": {"summary": "conflicting version of event one"}})
        try:
            store.append_batch([event_one, event_two, conflicting_event])
        except StoreIntegrityError:
            pass
        else:
            raise AssertionError("conflicting batch must raise")
        assert store.get_event("evt-atomic-1") is None
        assert store.get_event("evt-atomic-2") is None
    finally:
        store.close()
