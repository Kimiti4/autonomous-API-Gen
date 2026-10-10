"""Receiver/outbox regression for a request accepted before its ACK is lost.

This is an in-process integration test, not evidence of live deployment behavior.
"""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.engine.governed_maintenance_outbox import MaintenanceOutbox
from observatory.backend.config import get_settings
from observatory.backend.main import create_app
from test_governed_maintenance_outbox import maintenance_case


def test_lost_ack_retry_is_deduplicated_by_observatory(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSERVATORY_DB_PATH", str(tmp_path / "observatory.sqlite3"))
    monkeypatch.setenv("OBSERVATORY_API_TOKEN", "integration-test-token")
    get_settings.cache_clear()
    app = create_app()
    client = TestClient(app)
    try:
        record, event = maintenance_case()
        now = [1000.0]
        outbox = MaintenanceOutbox(
            tmp_path / "maintenance-outbox.sqlite3",
            base_backoff_seconds=2,
            max_backoff_seconds=8,
            clock=lambda: now[0],
        )
        outbox.enqueue(record, event)
        attempts = [0]

        def accept_then_drop_first_ack(request, timeout):
            response = client.post(
                "/observatory/events",
                content=request.data,
                headers=dict(request.header_items()),
            )
            assert response.status_code == 200, response.text
            attempts[0] += 1
            if attempts[0] == 1:
                # Receiver committed the event, but the caller never received
                # its acknowledgement: the ambiguous network-outcome case.
                raise TimeoutError("simulated acknowledgement loss")
            return response

        first = outbox.deliver_pending(
            base_url="http://localhost",
            token="integration-test-token",
            opener=accept_then_drop_first_ack,
        )
        assert first[0]["status"] == "pending"
        assert outbox.get(event.digest)["attempts"] == 1
        assert app.state.gateway.store.count_events() == 1

        now[0] += 2
        second = outbox.deliver_pending(
            base_url="http://localhost",
            token="integration-test-token",
            opener=accept_then_drop_first_ack,
        )
        assert second[0]["status"] == "delivered"
        assert second[0]["observatory_event_id"] == f"maintenance-{event.digest}"
        assert attempts[0] == 2
        assert app.state.gateway.store.count_events() == 1
        assert outbox.summary()["delivered"] == 1
    finally:
        client.close()
        for name in ("gateway", "workspace_store", "workspace_governance_store"):
            resource = getattr(app.state, name, None)
            close = getattr(resource, "close", None)
            if callable(close):
                close()
        get_settings.cache_clear()
