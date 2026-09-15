"""SQLite-backed canonical event store.

Write path is serialized (lock) with content-hash integrity: re-inserting
the identical event is idempotent; re-inserting the same ID with different
content raises StoreIntegrityError. Reads are plain indexed queries.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, List, NamedTuple, Optional, Union

from .domain import Event, EventCategory, event_hash


class StoreIntegrityError(Exception):
    pass


class BatchAppendResult(NamedTuple):
    inserted: int
    duplicates: int
    accepted_event_ids: List[str]
    inserted_events: List[Event]


class SqliteEventStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def init(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    correlation_id TEXT,
                    causation_id TEXT,
                    payload TEXT NOT NULL,
                    epistemic_status TEXT NOT NULL,
                    authorization TEXT,
                    evidence_refs TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    severity TEXT NOT NULL
                )
                """)
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS events_subject_idx "
                "ON events (subject_id, timestamp)")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS events_category_idx "
                "ON events (category, timestamp)")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS events_timestamp_idx "
                "ON events (timestamp)")
            self._conn.commit()

    def append(self, event: Event) -> bool:
        computed_hash = event_hash(event)
        dump = event.model_dump(mode="json")
        with self._lock:
            existing = self._conn.execute(
                "SELECT event_hash FROM events WHERE id = ?",
                (event.id,)).fetchone()
            if existing is not None:
                if existing["event_hash"] != computed_hash:
                    raise StoreIntegrityError(
                        f"event id {event.id} already exists with a different hash")
                return False
            self._conn.execute(
                """INSERT INTO events (id, event_hash, timestamp, source,
                    category, type, subject_id, correlation_id, causation_id,
                    payload, epistemic_status, authorization, evidence_refs,
                    provenance, severity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event.id, computed_hash, event.timestamp.isoformat(),
                 dump["source"], dump["category"], dump["type"],
                 dump["subject_id"], dump["correlation_id"],
                 dump["causation_id"],
                 json.dumps(dump["payload"], sort_keys=True, default=str),
                 dump["epistemic_status"], dump["authorization"],
                 json.dumps(dump["evidence_refs"], sort_keys=True, default=str),
                 json.dumps(dump["provenance"], sort_keys=True, default=str),
                 dump["severity"]))
            self._conn.commit()
            return True

    def append_batch(self, events: List[Event]) -> BatchAppendResult:
        # Atomic via the connection context manager: any integrity
        # conflict rolls back the whole batch (all-or-nothing).
        if not events:
            return BatchAppendResult(inserted=0, duplicates=0,
                                     accepted_event_ids=[],
                                     inserted_events=[])
        accepted_event_ids: List[str] = []
        inserted_events: List[Event] = []
        inserted = 0
        duplicates = 0
        with self._lock, self._conn:
            event_ids = [event.id for event in events]
            placeholders = ",".join("?" for _ in event_ids)
            existing_rows = self._conn.execute(
                f"SELECT id, event_hash FROM events WHERE id IN ({placeholders})",
                event_ids).fetchall()
            existing_hashes = {row["id"]: row["event_hash"]
                               for row in existing_rows}
            for event in events:
                computed_hash = event_hash(event)
                accepted_event_ids.append(event.id)
                if event.id in existing_hashes:
                    if existing_hashes[event.id] != computed_hash:
                        raise StoreIntegrityError(
                            f"event id {event.id} already exists with a "
                            f"different hash")
                    duplicates += 1
                    continue
                dump = event.model_dump(mode="json")
                self._conn.execute(
                    """INSERT INTO events (id, event_hash, timestamp, source,
                        category, type, subject_id, correlation_id,
                        causation_id, payload, epistemic_status,
                        authorization, evidence_refs, provenance, severity)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event.id, computed_hash, event.timestamp.isoformat(),
                     dump["source"], dump["category"], dump["type"],
                     dump["subject_id"], dump["correlation_id"],
                     dump["causation_id"],
                     json.dumps(dump["payload"], sort_keys=True, default=str),
                     dump["epistemic_status"], dump["authorization"],
                     json.dumps(dump["evidence_refs"], sort_keys=True,
                                default=str),
                     json.dumps(dump["provenance"], sort_keys=True,
                                default=str),
                     dump["severity"]))
                existing_hashes[event.id] = computed_hash
                inserted += 1
                inserted_events.append(event)
            return BatchAppendResult(
                inserted=inserted, duplicates=duplicates,
                accepted_event_ids=accepted_event_ids,
                inserted_events=inserted_events)

    def get_event(self, event_id: str) -> Optional[Event]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_event(row)

    def events_by_subject(self, subject_id: str, limit: int = 1000) -> List[Event]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE subject_id = ? "
                "ORDER BY timestamp ASC, id ASC LIMIT ?",
                (subject_id, limit)).fetchall()
        return [self._row_to_event(row) for row in rows]

    def events_by_category(self, category: Union[EventCategory, str],
                           limit: int = 1000) -> List[Event]:
        resolved = category.value if isinstance(category, EventCategory) else str(category)
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE category = ? "
                "ORDER BY timestamp ASC, id ASC LIMIT ?",
                (resolved, limit)).fetchall()
        return [self._row_to_event(row) for row in rows]

    def events_by_categories(self, categories, limit: int = 20000) -> List[Event]:
        resolved = [category.value if isinstance(category, EventCategory)
                    else str(category) for category in categories]
        if not resolved:
            return []
        placeholders = ",".join("?" for _ in resolved)
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE category IN "
                f"({placeholders}) ORDER BY timestamp ASC, id ASC LIMIT ?",
                (*resolved, limit)).fetchall()
        return [self._row_to_event(row) for row in rows]

    def _normalize_timestamp(self, value: Any) -> str:
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()

    def search_events(
        self,
        query: Optional[str] = None,
        categories: Optional[List[str]] = None,
        severities: Optional[List[str]] = None,
        epistemic_statuses: Optional[List[str]] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: int = 500,
    ) -> List[Event]:
        clauses: List[str] = []
        params: List[Any] = []
        if categories:
            resolved = [category.value if hasattr(category, "value")
                        else str(category) for category in categories]
            placeholders = ",".join("?" for _ in resolved)
            clauses.append(f"category IN ({placeholders})")
            params.extend(resolved)
        if severities:
            resolved = [str(severity) for severity in severities]
            placeholders = ",".join("?" for _ in resolved)
            clauses.append(f"severity IN ({placeholders})")
            params.extend(resolved)
        if epistemic_statuses:
            resolved = [str(status) for status in epistemic_statuses]
            placeholders = ",".join("?" for _ in resolved)
            clauses.append(f"epistemic_status IN ({placeholders})")
            params.extend(resolved)
        if since:
            clauses.append("timestamp >= ?")
            params.append(self._normalize_timestamp(since))
        if until:
            clauses.append("timestamp <= ?")
            params.append(self._normalize_timestamp(until))
        if query:
            like = f"%{query}%"
            clauses.append(
                "(subject_id LIKE ? OR type LIKE ? "
                "OR source LIKE ? OR payload LIKE ?)")
            params.extend([like, like, like, like])
        sql = "SELECT * FROM events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_event(row) for row in rows]

    def recent_events(self, limit: int = 100, descending: bool = False) -> List[Event]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC, id DESC LIMIT ?",
                (limit,)).fetchall()
        events = [self._row_to_event(row) for row in rows]
        if descending:
            return events
        return list(reversed(events))

    def count_events(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()
            return int(row["count"])

    def count_events_by_category(self, category: Union[EventCategory, str]) -> int:
        resolved = category.value if isinstance(category, EventCategory) else str(category)
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS count FROM events WHERE category = ?",
                (resolved,)).fetchone()
            return int(row["count"])

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        return Event.model_validate({
            "id": row["id"], "timestamp": row["timestamp"],
            "source": row["source"], "category": row["category"],
            "type": row["type"], "subject_id": row["subject_id"],
            "correlation_id": row["correlation_id"],
            "causation_id": row["causation_id"],
            "payload": json.loads(row["payload"]),
            "epistemic_status": row["epistemic_status"],
            "authorization": row["authorization"],
            "evidence_refs": json.loads(row["evidence_refs"]),
            "provenance": json.loads(row["provenance"]),
            "severity": row["severity"]})
