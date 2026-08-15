from __future__ import annotations

from fastapi.testclient import TestClient

from inventory_system.config import Settings
from inventory_system.main import create_app


def _client() -> TestClient:
    app = create_app(Settings(api_key="test-key"))
    return TestClient(app)


def test_health_and_readiness_are_open() -> None:
    client = _client()
    assert client.get("/health").status_code == 200
    assert client.get("/readiness").status_code == 200


def test_resources_require_auth() -> None:
    client = _client()
    assert client.get("/inventories").status_code == 401


def test_list_with_api_key() -> None:
    client = _client()
    headers = {"X-API-Key": "test-key"}
    assert client.get("/inventories", headers=headers).status_code == 200
