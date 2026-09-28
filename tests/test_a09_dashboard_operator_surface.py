"""A09-009 operator-surface deployment pins.

The React dashboard is a read-only presentation layer. It must consume the
canonical API through the versioned observation boundary and must never carry
platform credentials in browser/runtime configuration.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_observation_proxy_targets_versioned_api():
    nginx = (ROOT / "dashboard" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /observation/" in nginx
    assert "proxy_pass http://platform-api:8080/api/v1/observation/;" in nginx


def test_dashboard_auth_proxy_targets_platform_session_api():
    nginx = (ROOT / "dashboard" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /auth/" in nginx
    assert "proxy_pass http://platform-api:8080/api/v1/auth/;" in nginx
    assert "proxy_set_header Cookie" not in nginx  # nginx forwards cookies by default


def test_dashboard_runtime_config_contains_no_platform_secret():
    config = (ROOT / "dashboard" / "k8s" / "configmap.yaml").read_text(encoding="utf-8")
    forbidden = ("ADMIN_API_KEY", "API_KEY", "Authorization", "Bearer ")
    assert not any(token in config for token in forbidden)


def test_dashboard_observation_client_uses_same_origin_credentials():
    client = (ROOT / "dashboard" / "src" / "application" / "observationClient.ts").read_text(encoding="utf-8")
    fetcher = (ROOT / "dashboard" / "src" / "application" / "observationClient.ts").read_text(encoding="utf-8")
    assert "credentials: 'same-origin'" in client
    assert "baseUrl: config.observationApiPath" in fetcher


def test_dashboard_has_no_browser_embedded_api_key_and_requires_session():
    gate = (ROOT / "dashboard" / "src" / "presentation" / "components" / "AuthGate.tsx").read_text(encoding="utf-8")
    assert "fetch('/auth/session'" in gate
    assert "fetch('/auth/login'" in gate
    assert "credentials: 'same-origin'" in gate
    assert "localStorage" not in gate
    assert "sessionStorage" not in gate
