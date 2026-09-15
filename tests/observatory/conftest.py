"""Shared pytest fixtures for Observatory verification suites.

NOTE (repo adaptation): no root pytest.ini is created — it would override
pyproject.toml's canonical test configuration. Async tests below use
explicit @pytest.mark.asyncio markers (strict mode), which need no
config change.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from observatory.backend.config import get_settings
from observatory.backend.main import create_app

def register_store_cleanup(testcase, client) -> None:
    """Close every SQLite handle an app holds (gateway + workspace stores).

    Must be registered AFTER tmp.cleanup so LIFO ordering closes stores
    before the temp directory is removed (Windows file-lock hygiene).
    """
    stores = [client.app.state.gateway.store]
    for attr in ("workspace_store", "workspace_governance_store"):
        store = getattr(client.app.state, attr, None)
        if store is not None:
            stores.append(store)
    testcase.addCleanup(lambda: [store.close() for store in stores])


SYSTEM_HEADERS = {
    "X-Actor-Id": "test-system",
    "X-Actor-Role": "system",
    "X-Actor-Clearance": "system",
}

OBSERVER_HEADERS = {
    "X-Actor-Id": "test-observer",
    "X-Actor-Role": "observer",
    "X-Actor-Clearance": "observer",
}


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "OBSERVATORY_DB_PATH",
        str(tmp_path / "observatory.sqlite3"),
    )
    monkeypatch.setenv("OBSERVATORY_API_TOKEN", "")
    monkeypatch.setenv("OBSERVATORY_MAX_BATCH_SIZE", "100")
    get_settings.cache_clear()
    application = create_app()
    yield application
    get_settings.cache_clear()


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client
