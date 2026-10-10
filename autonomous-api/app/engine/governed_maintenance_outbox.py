"""Durable SQLite outbox for governed-maintenance Observatory events.

The outbox persists verified evidence before network delivery, retries transient
failures with bounded exponential backoff, and keeps exhausted events for manual
review. It never performs repository writes or deployment actions.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import asdict
import json
import math
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable

from .governed_maintenance_execution import GovernedMaintenanceEvent
from .governed_maintenance_observatory import (
    ObservatoryDeliveryError,
    deliver_maintenance_event,
)
from .governed_maintenance_record import GovernedMaintenanceRecord


class MaintenanceOutboxError(RuntimeError):
    """Raised when durable outbox integrity or state transitions fail."""


class MaintenanceOutbox:
    """SQLite-backed delivery queue with leases and bounded retry scheduling."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        max_attempts: int = 8,
        base_backoff_seconds: float = 2.0,
        max_backoff_seconds: float = 300.0,
        lease_seconds: float = 30.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(database_path, (str, Path)) or not str(database_path).strip():
            raise ValueError("outbox-database-path-required")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("outbox-max-attempts-invalid")
        for name, value in (
            ("base-backoff", base_backoff_seconds),
            ("max-backoff", max_backoff_seconds),
            ("lease", lease_seconds),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"outbox-{name}-invalid")
        if max_backoff_seconds < base_backoff_seconds:
            raise ValueError("outbox-backoff-range-invalid")
        self.database_path = str(database_path)
        self.max_attempts = max_attempts
        self.base_backoff_seconds = float(base_backoff_seconds)
        self.max_backoff_seconds = float(max_backoff_seconds)
        self.lease_seconds = float(lease_seconds)
        self.clock = clock
        if self.database_path != ":memory:":
            Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS maintenance_outbox (
                    event_digest TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('pending', 'delivering', 'delivered', 'dead_letter')),
                    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
                    next_attempt_at REAL NOT NULL,
                    lease_until REAL,
                    observatory_event_id TEXT,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS maintenance_outbox_due_idx "
                "ON maintenance_outbox(status, next_attempt_at, lease_until)"
            )

    @staticmethod
    def _serialize(record: Any, event: Any) -> tuple[str, str]:
        if getattr(event, "status", None) != "verified":
            raise ValueError("maintenance-event-not-verified")
        digest = getattr(event, "digest", None)
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("maintenance-event-digest-invalid")
        if (
            getattr(event, "observation_digest", None) != getattr(record, "observation_digest", None)
            or getattr(event, "obligation_id", None) != getattr(record, "obligation_id", None)
            or getattr(event, "patch_digest", None) != getattr(record, "patch_digest", None)
            or tuple(getattr(event, "evidence", ())) != tuple(getattr(record, "verification_evidence", ()))
        ):
            raise ValueError("maintenance-event-record-linkage-mismatch")
        try:
            payload = {
                "record": asdict(record),
                "event": asdict(event),
            }
        except (TypeError, ValueError) as exc:
            raise ValueError("maintenance-outbox-record-not-serializable") from exc
        return digest, json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def enqueue(self, record: GovernedMaintenanceRecord, event: GovernedMaintenanceEvent) -> str:
        """Persist the record/event pair before attempting delivery; idempotent by digest."""
        digest, payload_json = self._serialize(record, event)
        now = self.clock()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_json FROM maintenance_outbox WHERE event_digest = ?", (digest,)
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] != payload_json:
                    connection.rollback()
                    raise MaintenanceOutboxError("outbox-event-digest-collision")
                connection.commit()
                return digest
            connection.execute(
                """
                INSERT INTO maintenance_outbox
                    (event_digest, payload_json, status, attempts, next_attempt_at, created_at, updated_at)
                VALUES (?, ?, 'pending', 0, ?, ?, ?)
                """,
                (digest, payload_json, now, now, now),
            )
            connection.commit()
        return digest

    def _claim(self, *, limit: int) -> list[sqlite3.Row]:
        now = self.clock()
        claimed: list[sqlite3.Row] = []
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE maintenance_outbox
                   SET status = 'dead_letter', lease_until = NULL,
                       last_error = 'delivery-lease-expired-at-attempt-limit', updated_at = ?
                 WHERE status = 'delivering' AND lease_until <= ? AND attempts >= ?
                """,
                (now, now, self.max_attempts),
            )
            rows = connection.execute(
                """
                SELECT event_digest, payload_json, attempts
                  FROM maintenance_outbox
                 WHERE attempts < ?
                   AND ((status = 'pending' AND next_attempt_at <= ?)
                     OR (status = 'delivering' AND lease_until <= ?))
                 ORDER BY created_at, event_digest
                 LIMIT ?
                """,
                (self.max_attempts, now, now, limit),
            ).fetchall()
            for row in rows:
                updated = connection.execute(
                    """
                    UPDATE maintenance_outbox
                       SET status = 'delivering', attempts = attempts + 1,
                           lease_until = ?, updated_at = ?
                     WHERE event_digest = ? AND attempts = ?
                    """,
                    (now + self.lease_seconds, now, row["event_digest"], row["attempts"]),
                )
                if updated.rowcount == 1:
                    claimed.append(row)
            connection.commit()
        return claimed

    def _mark_failure(self, digest: str, attempts: int, error: Exception) -> dict[str, Any]:
        now = self.clock()
        dead_letter = attempts >= self.max_attempts
        delay = min(self.base_backoff_seconds * (2 ** max(0, attempts - 1)), self.max_backoff_seconds)
        status = "dead_letter" if dead_letter else "pending"
        # Avoid storing exception text: transport errors can contain URLs or other sensitive details.
        safe_error = "delivery-failed:" + type(error).__name__
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE maintenance_outbox
                   SET status = ?, next_attempt_at = ?, lease_until = NULL,
                       last_error = ?, updated_at = ?
                 WHERE event_digest = ? AND status = 'delivering'
                """,
                (status, now if dead_letter else now + delay, safe_error, now, digest),
            )
            connection.commit()
        return {
            "event_digest": digest,
            "status": status,
            "attempts": attempts,
            "retry_in_seconds": None if dead_letter else delay,
            "error": safe_error,
        }

    def deliver_pending(
        self,
        *,
        base_url: str,
        token: str,
        opener: Callable[..., Any] | None = None,
        timeout: float = 5.0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Deliver due items and persist each success/failure before returning."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("outbox-limit-invalid")
        claimed = self._claim(limit=limit)
        results: list[dict[str, Any]] = []
        for row in claimed:
            digest = row["event_digest"]
            attempts = int(row["attempts"]) + 1
            try:
                payload = json.loads(row["payload_json"])
                record_data = payload["record"]
                record_data["verification_evidence"] = tuple(record_data["verification_evidence"])
                event_data = payload["event"]
                event_data["evidence"] = tuple(event_data["evidence"])
                record = GovernedMaintenanceRecord(**record_data)
                event = GovernedMaintenanceEvent(**event_data)
                kwargs: dict[str, Any] = {"base_url": base_url, "token": token, "timeout": timeout}
                if opener is not None:
                    kwargs["opener"] = opener
                event_id = deliver_maintenance_event(record, event, **kwargs)
            except Exception as exc:
                results.append(self._mark_failure(digest, attempts, exc))
                continue
            now = self.clock()
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    UPDATE maintenance_outbox
                       SET status = 'delivered', observatory_event_id = ?,
                           lease_until = NULL, last_error = NULL, updated_at = ?
                     WHERE event_digest = ? AND status = 'delivering'
                    """,
                    (event_id, now, digest),
                )
                connection.commit()
            results.append({
                "event_digest": digest,
                "status": "delivered",
                "attempts": attempts,
                "observatory_event_id": event_id,
                "error": None,
            })
        return results

    def get(self, event_digest: str) -> dict[str, Any] | None:
        """Return delivery metadata without exposing the stored evidence payload."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT event_digest, status, attempts, next_attempt_at, lease_until,
                       observatory_event_id, last_error, created_at, updated_at
                  FROM maintenance_outbox WHERE event_digest = ?
                """,
                (event_digest,),
            ).fetchone()
        return dict(row) if row is not None else None

    def summary(self) -> dict[str, int]:
        """Return aggregate delivery counts suitable for a dashboard/health surface."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM maintenance_outbox GROUP BY status"
            ).fetchall()
        counts = {status: 0 for status in ("pending", "delivering", "delivered", "dead_letter")}
        counts.update({row["status"]: row["count"] for row in rows})
        return counts

    def retry_dead_letter(self, event_digest: str) -> bool:
        """Explicitly requeue one dead-letter event for operator-controlled recovery."""
        now = self.clock()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            result = connection.execute(
                """
                UPDATE maintenance_outbox
                   SET status = 'pending', attempts = 0, next_attempt_at = ?,
                       lease_until = NULL, last_error = NULL, updated_at = ?
                 WHERE event_digest = ? AND status = 'dead_letter'
                """,
                (now, now, event_digest),
            )
            connection.commit()
        return result.rowcount == 1
