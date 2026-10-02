"""Integrity-preserving backup and restore for the SQLite control-plane state.

Backups are complete SQLite database images, not row-by-row exports. They are
validated with SQLite integrity_check before publication and before restore.
Restore is staged into a new database image and only replaces the live file
after validation.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy.engine import Engine


def _database_path(engine: Engine) -> Path:
    if engine.url.get_backend_name() != "sqlite":
        raise RuntimeError("SQLite backup/restore requires a SQLite engine")
    database = engine.url.database
    if not database or database == ":memory:":
        raise RuntimeError("SQLite backup/restore requires a file-backed database")
    return Path(database).resolve()


def _integrity_check(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"database backup does not exist: {path}")
    try:
        connection = sqlite3.connect(path)
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise ValueError(f"SQLite integrity check failed for {path}: {exc}") from exc
    if not result or result[0] != "ok":
        raise ValueError(f"SQLite integrity check failed for {path}: {result}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_path(path: Path) -> None:
    # Windows fsync requires a writable descriptor; O_RDONLY raises EBADF.
    fd = os.open(path, os.O_RDWR)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _copy_sqlite_image(source: Path, temporary: Path) -> None:
    source_connection = sqlite3.connect(source)
    target_connection = sqlite3.connect(temporary)
    try:
        source_connection.backup(target_connection)
        target_connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        target_connection.commit()
    finally:
        target_connection.close()
        source_connection.close()


def backup_sqlite_database(
    engine: Engine,
    backup_path: str | os.PathLike[str],
) -> str:
    """Create and validate an atomic, complete SQLite backup."""
    source = _database_path(engine)
    destination = Path(backup_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    engine.dispose()
    _integrity_check(source)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(fd)
    temporary = Path(temp_name)
    try:
        _copy_sqlite_image(source, temporary)
        _integrity_check(temporary)
        _fsync_path(temporary)
        os.replace(temporary, destination)
        return _sha256(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def restore_sqlite_database(
    engine: Engine,
    backup_path: str | os.PathLike[str],
    expected_digest: str,
) -> str:
    """Restore a validated SQLite backup, preserving a rollback copy of live state."""
    backup = Path(backup_path).resolve()
    _integrity_check(backup)
    actual_digest = _sha256(backup)
    if actual_digest != expected_digest:
        raise ValueError("database backup digest mismatch")

    destination = _database_path(engine)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rollback = destination.with_name(f".{destination.name}.previous")

    engine.dispose()
    _integrity_check(destination)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.restore.",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(fd)
    temporary = Path(temp_name)
    try:
        _copy_sqlite_image(backup, temporary)
        _integrity_check(temporary)
        _fsync_path(temporary)
        os.replace(destination, rollback)
        try:
            os.replace(temporary, destination)
        except Exception:
            os.replace(rollback, destination)
            raise
        return _sha256(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
