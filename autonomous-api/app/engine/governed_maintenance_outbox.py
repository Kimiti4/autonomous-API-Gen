"""Durable SQLite outbox for retryable Observatory evidence delivery.

The outbox persists the exact event payload before network delivery. Retries reuse
the same event ID and payload so an Observatory ingestion endpoint can deduplicate
at its idempotency boundary. This module never performs deployment or repository
mutations.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class OutboxItem:
    event_id: str
    payload: dict[str, Any]
    attempts: int
    last_error: str | None


@dataclass(frozen=True)
class OutboxDeliverySummary:
    delivered: int
    failed: int
    pending: int


class SQLiteObservatoryOutbox:
    """Small synchronous, durable outbox backed by SQLite.

    Use a persistent writable path in production (not `:memory:`). The callback
    receives the persisted JSON object and must send its stable `id` unchanged.
    Delivery is at-least-once: the remote ingestion API should treat the stable
    event ID as an idempotency key.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if not self.database_path.strip():
            raise ValueError("outbox-database-path-required")
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS observatory_outbox (
                    event_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'delivered')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    remote_event_id TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_observatory_outbox_pending "
                "ON observatory_outbox(status, created_at)"
            )

    @staticmethod
    def _canonical_payload(event_id: str, payload: dict[str, Any]) -> str:
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("outbox-event-id-required")
        if not isinstance(payload, dict):
            raise ValueError("outbox-payload-must-be-object")
        if payload.get("id") != event_id:
            raise ValueError("outbox-event-id-payload-mismatch")
        try:
            return json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("outbox-payload-not-json-serializable") from exc

    def enqueue(self, event_id: str, payload: dict[str, Any]) -> bool:
        """Persist an event; return True if new, False if identical duplicate."""
        canonical = self._canonical_payload(event_id, payload)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM observatory_outbox WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if row is not None:
                if row["payload_json"] != canonical:
                    raise ValueError("outbox-idempotency-key-payload-conflict")
                return False
            connection.execute(
                "INSERT INTO observatory_outbox "
                "(event_id, payload_json, status) VALUES (?, ?, 'pending')",
                (event_id, canonical),
            )
            return True

    def pending(self, limit: int = 100) -> tuple[OutboxItem, ...]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("outbox-limit-must-be-positive-integer")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_id, payload_json, attempts, last_error "
                "FROM observatory_outbox WHERE status = 'pending' "
                "ORDER BY created_at, event_id LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(
            OutboxItem(
                event_id=row["event_id"],
                payload=json.loads(row["payload_json"]),
                attempts=row["attempts"],
                last_error=row["last_error"],
            )
            for row in rows
        )

    def deliver_pending(
        self,
        deliver: Callable[[dict[str, Any]], str],
        *,
        limit: int = 100,
    ) -> OutboxDeliverySummary:
        """Attempt each pending item once; failures remain durable for retry."""
        if not callable(deliver):
            raise ValueError("outbox-deliver-callback-required")
        items = self.pending(limit)
        delivered = 0
        failed = 0
        for item in items:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE observatory_outbox SET attempts = attempts + 1, "
                    "updated_at = CURRENT_TIMESTAMP WHERE event_id = ? "
                    "AND status = 'pending'",
                    (item.event_id,),
                )
            try:
                remote_id = deliver(item.payload)
                if not isinstance(remote_id, str) or not remote_id.strip():
                    raise ValueError("outbox-delivery-acknowledgement-invalid")
            except Exception as exc:
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE observatory_outbox SET last_error = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE event_id = ? "
                        "AND status = 'pending'",
                        (f"{type(exc).__name__}: {exc}"[:1000], item.event_id),
                    )
                failed += 1
                continue
            with self._connect() as connection:
                connection.execute(
                    "UPDATE observatory_outbox SET status = 'delivered', "
                    "remote_event_id = ?, last_error = NULL, "
                    "updated_at = CURRENT_TIMESTAMP WHERE event_id = ? "
                    "AND status = 'pending'",
                    (remote_id.strip(), item.event_id),
                )
            delivered += 1
        with self._connect() as connection:
            remaining = connection.execute(
                "SELECT COUNT(*) FROM observatory_outbox WHERE status = 'pending'"
            ).fetchone()[0]
        return OutboxDeliverySummary(
            delivered=delivered, failed=failed, pending=int(remaining)
        )

    def get_status(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT event_id, status, attempts, remote_event_id, last_error "
                "FROM observatory_outbox WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return dict(row) if row is not None else None
