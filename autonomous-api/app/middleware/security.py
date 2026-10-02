"""Security middleware + fail-closed authentication (closes GAP-05).

Constitutional rules enforced here:
- Production refuses to start without a configured auth provider.
- No anonymous observation or evolution-control paths in production.
- No bearer tokens in URLs (cookie/header only).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from fastapi import Depends, Request, Response, WebSocket
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.exceptions import UnauthenticatedError


PROTECTED_CONTROL_PREFIXES = ("/evolve", "/evolution", "/production/readiness", "/governance", "/api/v1/evolve", "/api/v1/evolution", "/api/v1/production/readiness", "/api/v1/governance")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply response hardening and enforce the evolution control boundary."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "OPTIONS" and request.url.path.startswith(PROTECTED_CONTROL_PREFIXES):
            try:
                auth = get_auth()
                ctx = await auth.authenticate(request)
            except Exception:
                ctx = None
            if ctx is None:
                response = JSONResponse(
                    status_code=401,
                    content={"code": "SEC_UNAUTHENTICATED", "message": "Authentication required"},
                )
                return self._secure(response)
            if "control" not in ctx.scopes:
                response = JSONResponse(
                    status_code=403,
                    content={"code": "SEC_UNAUTHORIZED", "message": "Control scope required"},
                )
                return self._secure(response)

        response = await call_next(request)
        return self._secure(response)

    @staticmethod
    def _secure(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        if "server" in response.headers:
            del response.headers["server"]
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
            "font-src 'self'; connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:*; "
            "frame-ancestors 'none';"
        )
        return response


def validate_cors_origins(origins: list) -> list:
    validated = []
    for origin in origins:
        origin = origin.strip()
        if not origin:
            continue
        if not (origin.startswith("http://") or origin.startswith("https://")):
            continue
        if "localhost" in origin or "127.0.0.1" in origin:
            validated.append(origin)
        elif origin.startswith("https://"):
            validated.append(origin)
    return validated


@dataclass(frozen=True)
class AuthContext:
    subject: str
    scopes: tuple = ()


@runtime_checkable
class AuthProvider(Protocol):
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        ...


@runtime_checkable
class WsAuthProvider(Protocol):
    async def authenticate(self, websocket: WebSocket) -> Optional[AuthContext]:
        ...


class ApiKeyAuthProvider:
    """Constant-time API-key authentication for headers, bearer auth, or cookie."""

    def __init__(self, *, api_key: str, header_name: str = "X-API-Key", cookie_name: str = "api_key") -> None:
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
            return AuthContext(subject="admin", scopes=("observe", "control"))
        return None

    async def authenticate_ws(self, websocket: WebSocket) -> Optional[AuthContext]:
        supplied = websocket.headers.get(self._header_name)
        if not supplied:
            authz = websocket.headers.get("Authorization", "")
            if authz.lower().startswith("bearer "):
                supplied = authz[7:].strip()
        if not supplied:
            supplied = websocket.cookies.get(self._cookie_name)
        if self._matches(supplied):
            return AuthContext(subject="admin", scopes=("observe", "control"))
        return None


class SessionAuthProvider:
    """Verifies an HttpOnly, signed operator session cookie.

    The cookie contains only an opaque signed subject/expiry pair. The ADMIN_API_KEY
    never enters the browser's runtime configuration and is exchanged only at login.
    """

    def __init__(self, *, secret: str, cookie_name: str, ttl_seconds: int) -> None:
        if not secret:
            raise RuntimeError("Session authentication requires a signing secret")
        self._secret = secret.encode("utf-8")
        self.cookie_name = cookie_name
        self.ttl_seconds = ttl_seconds

    def _signature(self, value: str) -> str:
        return hmac.new(self._secret, value.encode("utf-8"), hashlib.sha256).hexdigest()

    def issue(self, subject: str, *, now: Optional[int] = None) -> tuple[str, int]:
        issued_at = int(time.time()) if now is None else now
        expires_at = issued_at + self.ttl_seconds
        payload = f"{subject}:{expires_at}"
        encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
        value = f"{encoded}.{self._signature(encoded)}"
        return value, expires_at

    def _verify(self, value: Optional[str], *, now: Optional[int] = None) -> Optional[AuthContext]:
        if not value or "." not in value:
            return None
        encoded, signature = value.rsplit(".", 1)
        expected = self._signature(encoded)
        if not hmac.compare_digest(signature, expected):
            return None
        try:
            padded = encoded + "=" * (-len(encoded) % 4)
            subject, expires_raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8").rsplit(":", 1)
            expires_at = int(expires_raw)
        except (ValueError, UnicodeError):
            return None
        current = int(time.time()) if now is None else now
        if not subject or expires_at <= current:
            return None
        return AuthContext(subject=subject, scopes=("observe",))

    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        return self._verify(request.cookies.get(self.cookie_name))

    async def authenticate_ws(self, websocket: WebSocket) -> Optional[AuthContext]:
        return self._verify(websocket.cookies.get(self.cookie_name))

    def set_cookie(self, response: Response, value: str, *, secure: bool) -> None:
        response.set_cookie(
            key=self.cookie_name,
            value=value,
            max_age=self.ttl_seconds,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )

    def clear_cookie(self, response: Response) -> None:
        response.delete_cookie(self.cookie_name, path="/", samesite="lax")


class CompositeAuthProvider:
    """Tries providers in order; first success wins. Fail-closed otherwise."""

    def __init__(self, providers: list) -> None:
        if not providers:
            raise RuntimeError("At least one AuthProvider is required")
        self._providers = providers

    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        for provider in self._providers:
            ctx = await provider.authenticate(request)
            if ctx is not None:
                return ctx
        return None

    async def authenticate_ws(self, websocket: WebSocket) -> Optional[AuthContext]:
        for provider in self._providers:
            method = getattr(provider, "authenticate_ws", None)
            ctx = await method(websocket) if method else await provider.authenticate(websocket)
            if ctx is not None:
                return ctx
        return None


def validate_auth_config(environment: str, providers: list) -> None:
    if environment == "production" and not providers:
        raise RuntimeError(
            "FATAL: production requires configured auth providers. Refusing to start (fail-closed)."
        )


_auth_provider: Optional[CompositeAuthProvider] = None


def set_auth_provider(provider: CompositeAuthProvider) -> None:
    global _auth_provider
    _auth_provider = provider


def get_auth() -> CompositeAuthProvider:
    if _auth_provider is None:
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
