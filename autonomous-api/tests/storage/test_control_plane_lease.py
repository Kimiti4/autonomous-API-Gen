import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.storage import lease


def _prepare_database(path):
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE control_plane_lease (
                lease_key VARCHAR PRIMARY KEY,
                owner_token VARCHAR NOT NULL,
                owner_run_id VARCHAR NOT NULL,
                acquired_at DATETIME NOT NULL,
                heartbeat_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_control_plane_lease_is_single_flight(tmp_path, monkeypatch):
    database = tmp_path / "lease.db"
    _prepare_database(database)
    monkeypatch.setattr(lease, "DATABASE_URL", f"sqlite:///{database}")

    first = lease.acquire_control_plane_lease(owner_run_id="run-1")
    with pytest.raises(lease.ControlPlaneBusy):
        lease.acquire_control_plane_lease(owner_run_id="run-2")

    lease.release_control_plane_lease(first)
    second = lease.acquire_control_plane_lease(owner_run_id="run-2")
    assert second != first
    lease.release_control_plane_lease(second)


def test_live_owner_can_heartbeat_and_stale_owner_can_be_taken_over(tmp_path, monkeypatch):
    database = tmp_path / "lease.db"
    _prepare_database(database)
    monkeypatch.setattr(lease, "DATABASE_URL", f"sqlite:///{database}")

    first = lease.acquire_control_plane_lease(owner_run_id="run-1", lease_seconds=60)
    lease.heartbeat_control_plane_lease(first, lease_seconds=60)

    connection = sqlite3.connect(database)
    try:
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        connection.execute(
            "UPDATE control_plane_lease SET expires_at = ? WHERE lease_key = ?",
            (expired, lease.LEASE_KEY),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(lease.ControlPlaneBusy):
        lease.acquire_control_plane_lease(owner_run_id="run-2")

    second = lease.acquire_control_plane_lease(
        owner_run_id="run-2",
        allow_stale_takeover=True,
    )
    with pytest.raises(lease.ControlPlaneBusy):
        lease.heartbeat_control_plane_lease(first)

    lease.release_control_plane_lease(second)


def test_lease_status_reflects_expiry(tmp_path, monkeypatch):
    database = tmp_path / "lease.db"
    _prepare_database(database)
    monkeypatch.setattr(lease, "DATABASE_URL", f"sqlite:///{database}")

    token = lease.acquire_control_plane_lease(owner_run_id="run-1", lease_seconds=60)
    assert lease.lease_is_live() is True
    lease.release_control_plane_lease(token)
    assert lease.lease_is_live() is False
