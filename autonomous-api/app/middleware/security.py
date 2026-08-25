"""Security middleware + fail-closed authentication (closes GAP-05).

Constitutional rules enforced here:
- Production refuses to start without a configured auth provider.
- No anonymous observation/WebSocket paths in production.
- No bearer tokens in URLs (cookie/header only).
"""
from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from fastapi import Depends, Request, Response, WebSocket
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import UnauthenticatedError


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.
    Implements OWASP security header recommendations.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate"
        )
        response.headers["Pragma"] = "no-cache"

        # Remove server header to avoid information disclosure
        if "server" in response.headers:
            del response.headers["server"]

        # Content Security Policy (adjust based on your needs)
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:*; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        return response


def validate_cors_origins(origins: list) -> list:
    """
    Validate and sanitize CORS origins.
    Only allows trusted origins in production.
    """
    validated = []

    for origin in origins:
        origin = origin.strip()

        # Skip empty origins
        if not origin:
            continue

        # Validate URL format
        if not (origin.startswith("http://") or origin.startswith("https://")):
            continue

        # Allow localhost for development and HTTPS origins in production
        if "localhost" in origin or "127.0.0.1" in origin:
            validated.append(origin)
        elif origin.startswith("https://"):
            validated.append(origin)

    return validated


# ==================== FAIL-CLOSED AUTHENTICATION ====================


@dataclass(frozen=True)
class AuthContext:
    subject: str
    scopes: tuple = ()


@runtime_checkable
class AuthProvider(Protocol):
    """Plugin-first: ApiKey, OIDC, mTLS, CookieSession are all backends."""

    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        """Return AuthContext on success, None on failure. Never raises for
        missing credentials — absence of credentials is simply failure."""
        ...


@runtime_checkable
class WsAuthProvider(Protocol):
    async def authenticate(
        self, websocket: WebSocket
    ) -> Optional[AuthContext]: ...


class ApiKeyAuthProvider:
    """Constant-time API-key check against the configured admin key.

    Accepts the key from the X-API-Key header or Authorization: Bearer,
    or an HttpOnly cookie (`api_key`) for browser clients — never URLs.
    """

    def __init__(self, *, api_key: str, header_name: str = "X-API-Key",
                 cookie_name: str = "api_key") -> None:
        self._api_key = api_key
        self._header_name = header_name
        self._cookie_name = cookie_name

    def _matches(self, candidate: Optional[str]) -> bool:
        if not candidate or not self._api_key:
            return False
        return hmac.compare_digest(candidate, self._api_key)

    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        supplied = request.headers.get(self._header_name)
        if not supplied:
            authz = request.headers.get("Authorization", "")
            if authz.lower().startswith("bearer "):
                supplied = authz[7:].strip()
        if not supplied:
            supplied = request.cookies.get(self._cookie_name)
        if self._matches(supplied):
            return AuthContext(subject="admin", scopes=("observe",))
        return None

    async def authenticate_ws(
        self, websocket: WebSocket
    ) -> Optional[AuthContext]:
        supplied = websocket.headers.get(self._header_name)
        if not supplied:
            authz = websocket.headers.get("Authorization", "")
            if authz.lower().startswith("bearer "):
                supplied = authz[7:].strip()
        if not supplied:
            supplied = websocket.cookies.get(self._cookie_name)
        if self._matches(supplied):
            return AuthContext(subject="admin", scopes=("observe",))
        return None


class CompositeAuthProvider:
    """Tries providers in order; first success wins. Fail-closed otherwise."""

    def __init__(self, providers: list) -> None:
        if not providers:
            raise RuntimeError("At least one AuthProvider is required")
        self._providers = providers

    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        for p in self._providers:
            ctx = await p.authenticate(request)
            if ctx is not None:
                return ctx
        return None

    async def authenticate_ws(
        self, websocket: WebSocket
    ) -> Optional[AuthContext]:
        for p in self._providers:
            ws_method = getattr(p, "authenticate_ws", None)
            if ws_method is not None:
                ctx = await ws_method(websocket)
            else:
                ctx = await p.authenticate(websocket)
            if ctx is not None:
                return ctx
        return None


def validate_auth_config(environment: str, providers: list) -> None:
    """Called at startup. Fail-closed in production."""
    if environment == "production" and not providers:
        raise RuntimeError(
            "FATAL: production requires configured auth providers. "
            "Refusing to start (fail-closed)."
        )


# Module-level singleton, wired by the composition root (main.py).
_auth_provider: Optional[CompositeAuthProvider] = None


def set_auth_provider(provider: CompositeAuthProvider) -> None:
    global _auth_provider
    _auth_provider = provider


def get_auth() -> CompositeAuthProvider:
    if _auth_provider is None:
        # Fail-closed: no provider configured means nothing authenticates.
        raise UnauthenticatedError("Authentication is not configured")
    return _auth_provider


async def require_auth(
    request: Request,
    auth: CompositeAuthProvider = Depends(get_auth),
) -> AuthContext:
    ctx = await auth.authenticate(request)
    if ctx is None:
        raise UnauthenticatedError("Authentication required")
    return ctx