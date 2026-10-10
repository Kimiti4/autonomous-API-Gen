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
    monkeypatch.setattr(routes, "_outbox_for_path", lambda path: FakeOutbox())
    result = await routes.maintenance_outbox_status(limit=5, _auth=object())
    assert result["status"] == "available"
    assert result["summary"]["dead_letter"] == 1
    assert result["items"] == [item]
    assert "payload" not in result
