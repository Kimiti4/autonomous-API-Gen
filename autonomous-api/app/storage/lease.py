"""Cross-process single-flight lease for control-plane evolution.

The lease is deliberately stored in the SQLite control-plane database rather
than process memory, so separate workers cannot start overlapping authoritative
evolution runs. A heartbeat makes ownership observable; a stale lease can be
taken over only by recovery.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.storage.db import DATABASE_URL

LEASE_KEY = "evolution"
LEASE_SECONDS = 60
BUSY_MESSAGE = "another authoritative evolution operation is already active"


class ControlPlaneBusy(RuntimeError):
    """Raised when an authoritative control-plane operation is already active."""


def _database_path() -> Path:
    prefix = "sqlite:///"
    if not DATABASE_URL.startswith(prefix):
        raise RuntimeError("control-plane lease requires the SQLite control-plane database")
    return Path(DATABASE_URL[len(prefix):]).resolve()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(), timeout=5.0)
    connection.row_factory = sqlite3.Row
    return connection


def acquire_control_plane_lease(
    *,
    owner_run_id: str,
    lease_seconds: int = LEASE_SECONDS,
    allow_stale_takeover: bool = False,
) -> str:
    """Acquire the single evolution lease, failing closed while it is live."""
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    owner_token = str(uuid.uuid4())
    now = _now()
    expires = now + timedelta(seconds=lease_seconds)
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT owner_token, owner_run_id, expires_at FROM control_plane_lease WHERE lease_key = ?",
            (LEASE_KEY,),
        ).fetchone()
        if row is not None:
            active = _parse(row["expires_at"]) > now
            if active or not allow_stale_takeover:
                connection.rollback()
                raise ControlPlaneBusy(BUSY_MESSAGE)
        if row is None:
            connection.execute(
                """INSERT INTO control_plane_lease
                   (lease_key, owner_token, owner_run_id, acquired_at, heartbeat_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (LEASE_KEY, owner_token, owner_run_id, _stamp(now), _stamp(now), _stamp(expires)),
            )
        else:
            connection.execute(
                """UPDATE control_plane_lease
                   SET owner_token = ?, owner_run_id = ?, acquired_at = ?,
                       heartbeat_at = ?, expires_at = ?
                   WHERE lease_key = ?""",
                (owner_token, owner_run_id, _stamp(now), _stamp(now), _stamp(expires), LEASE_KEY),
            )
        connection.commit()
        return owner_token
    except Exception:
        try:
            connection.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        connection.close()


def heartbeat_control_plane_lease(
    owner_token: str,
    *,
    lease_seconds: int = LEASE_SECONDS,
) -> None:
    """Renew a live lease; renewal by a non-owner fails closed."""
    now = _now()
    expires = now + timedelta(seconds=lease_seconds)
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        result = connection.execute(
            """UPDATE control_plane_lease
               SET heartbeat_at = ?, expires_at = ?
               WHERE lease_key = ? AND owner_token = ?""",
            (_stamp(now), _stamp(expires), LEASE_KEY, owner_token),
        )
        if result.rowcount != 1:
            connection.rollback()
            raise ControlPlaneBusy("control-plane lease ownership was lost")
        connection.commit()
    finally:
        connection.close()


def release_control_plane_lease(owner_token: str) -> None:
    """Release only the lease held by this owner."""
    connection = _connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DELETE FROM control_plane_lease WHERE lease_key = ? AND owner_token = ?",
            (LEASE_KEY, owner_token),
        )
        connection.commit()
    finally:
        connection.close()


def lease_is_live() -> bool:
    """Return whether a non-expired control-plane lease exists."""
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT expires_at FROM control_plane_lease WHERE lease_key = ?",
            (LEASE_KEY,),
        ).fetchone()
        return row is not None and _parse(row["expires_at"]) > _now()
    finally:
        connection.close()


@contextmanager
def control_plane_lease(*, owner_run_id: str):
    token = acquire_control_plane_lease(owner_run_id=owner_run_id)
    try:
        yield token
    finally:
        release_control_plane_lease(token)
