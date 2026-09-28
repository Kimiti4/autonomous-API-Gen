from fastapi.testclient import TestClient

from app.main import app
from app.middleware.security import SessionAuthProvider


def test_operator_session_provider_is_signed_and_expiring():
    provider = SessionAuthProvider(secret="x" * 32, cookie_name="session", ttl_seconds=60)
    value, expires_at = provider.issue("admin", now=100)
    assert expires_at == 160
    assert provider._verify(value, now=159).subject == "admin"
    assert provider._verify(value, now=160) is None
    encoded, signature = value.rsplit(".", 1)
    tampered = f"{encoded}.{'0' * len(signature)}"
    assert provider._verify(tampered, now=101) is None


def test_operator_login_establishes_platform_recognized_session():
    client = TestClient(app)

    unauthenticated = client.get("/api/v1/auth/session")
    assert unauthenticated.status_code == 401

    login = client.post("/api/v1/auth/login", json={"api_key": "test-admin-key"})
    assert login.status_code == 204
    assert "esap_operator_session" in login.cookies
    assert "HttpOnly" in login.headers["set-cookie"]

    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200
    assert session.json() == {"authenticated": True, "subject": "admin"}

    kill_switch = client.get("/api/v1/evolution/kill-switch")
    assert kill_switch.status_code == 403

    control = client.get(
        "/api/v1/evolution/kill-switch",
        headers={"X-API-Key": "test-admin-key"},
    )
    assert control.status_code == 200

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/session").status_code == 401


def test_operator_login_rejects_invalid_credential():
    client = TestClient(app)
    response = client.post("/api/v1/auth/login", json={"api_key": "wrong"})
    assert response.status_code == 401
