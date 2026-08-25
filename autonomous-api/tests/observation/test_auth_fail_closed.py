"""GAP-05 acceptance: fail-closed auth on HTTP + WS, production gate."""
from __future__ import annotations

import pytest

from app.middleware.security import validate_auth_config


def test_production_refuses_to_start_without_auth():
    with pytest.raises(RuntimeError, match="fail-closed"):
        validate_auth_config("production", providers=[])


def test_production_allows_configured_auth():
    validate_auth_config("production", providers=["provider"])  # no raise


def test_unauthenticated_http_gets_401_envelope(client):
    resp = client.get("/observation/capabilities")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "SEC_UNAUTHENTICATED"
    assert body["recovery"]["action"] == "authenticate"
    assert "metadata" in body and "provenance" in body


def test_wrong_key_gets_401_envelope(client):
    resp = client.get(
        "/observation/capabilities", headers={"X-API-Key": "wrong"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "SEC_UNAUTHENTICATED"


def test_authenticated_request_passes(client, auth_headers):
    resp = client.get("/observation/capabilities", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractId"] == "platform.observation.capabilities"


def test_ws_never_accepts_anonymous(client):
    # Server closes before accept → client sees a disconnect/exception.
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/evolution"):
            pass


def test_ws_accepts_authenticated(client, auth_headers):
    # Header-based auth for non-browser clients (no token-in-URL).
    with client.websocket_connect(
        "/ws/evolution", headers=auth_headers
    ) as ws:
        # Connection accepted; server is now in receive loop.
        assert ws is not None