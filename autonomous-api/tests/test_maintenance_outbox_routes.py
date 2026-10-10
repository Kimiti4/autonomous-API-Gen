from types import SimpleNamespace

import pytest
from fastapi.responses import JSONResponse

from app.api import maintenance_outbox_routes as routes


@pytest.mark.asyncio
async def test_status_is_unavailable_when_storage_is_not_configured(monkeypatch):
    monkeypatch.setattr(
        routes, "get_settings", lambda: SimpleNamespace(MAINTENANCE_OUTBOX_DB_PATH="")
    )
    response = await routes.maintenance_outbox_status(limit=20, _auth=object())
    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert b"MAINTENANCE_OUTBOX_NOT_CONFIGURED" in response.body


@pytest.mark.asyncio
async def test_status_returns_only_summary_and_delivery_metadata(monkeypatch):
    item = {
        "event_digest": "a" * 64,
        "status": "dead_letter",
        "attempts": 8,
        "next_attempt_at": 10.0,
        "lease_until": None,
        "observatory_event_id": None,
        "last_error": "delivery-failed:TimeoutError",
        "created_at": 1.0,
        "updated_at": 2.0,
    }

    class FakeOutbox:
        def summary(self):
            return {"pending": 0, "delivering": 0, "delivered": 2, "dead_letter": 1}

        def list_recent(self, *, limit):
            assert limit == 5
            return [item]

    monkeypatch.setattr(
        routes, "get_settings",
        lambda: SimpleNamespace(MAINTENANCE_OUTBOX_DB_PATH="/persistent/outbox.sqlite3"),
    )
    monkeypatch.setattr(routes.Path, "is_file", lambda self: True)
    monkeypatch.setattr(routes, "_outbox_for_path", lambda path: FakeOutbox())
    result = await routes.maintenance_outbox_status(limit=5, _auth=object())
    assert result["status"] == "available"
    assert result["summary"]["dead_letter"] == 1
    assert result["items"] == [item]
    assert "payload" not in result


@pytest.mark.asyncio
async def test_status_does_not_create_uninitialized_storage_on_read(monkeypatch):
    monkeypatch.setattr(
        routes, "get_settings",
        lambda: SimpleNamespace(MAINTENANCE_OUTBOX_DB_PATH="/persistent/not-created.sqlite3"),
    )
    monkeypatch.setattr(routes.Path, "is_file", lambda self: False)
    monkeypatch.setattr(
        routes, "_outbox_for_path",
        lambda path: pytest.fail("GET must not initialize or create the outbox"),
    )
    response = await routes.maintenance_outbox_status(limit=20, _auth=object())
    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert b"MAINTENANCE_OUTBOX_NOT_INITIALIZED" in response.body


@pytest.mark.asyncio
async def test_dashboard_auth_accepts_platform_api_key_provider(monkeypatch):
    context = object()

    class FakeAuth:
        async def authenticate(self, request):
            return context

    monkeypatch.setattr(routes, "get_auth", lambda: FakeAuth())
    monkeypatch.setattr(
        routes, "authenticate_operator_session",
        lambda request: pytest.fail("session fallback is not needed"),
    )
    assert await routes.require_dashboard_auth(object()) is context


@pytest.mark.asyncio
async def test_dashboard_auth_falls_back_to_signed_operator_session(monkeypatch):
    context = object()

    class FakeAuth:
        async def authenticate(self, request):
            return None

    async def session_auth(request):
        return context

    monkeypatch.setattr(routes, "get_auth", lambda: FakeAuth())
    monkeypatch.setattr(routes, "authenticate_operator_session", session_auth)
    assert await routes.require_dashboard_auth(object()) is context


@pytest.mark.asyncio
async def test_dashboard_auth_rejects_anonymous_requests(monkeypatch):
    from app.core.exceptions import UnauthenticatedError

    class FakeAuth:
        async def authenticate(self, request):
            return None

    async def session_auth(request):
        return None

    monkeypatch.setattr(routes, "get_auth", lambda: FakeAuth())
    monkeypatch.setattr(routes, "authenticate_operator_session", session_auth)
    with pytest.raises(UnauthenticatedError):
        await routes.require_dashboard_auth(object())
