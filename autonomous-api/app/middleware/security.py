"""Security middleware + fail-closed authentication (closes GAP-05).

Constitutional rules enforced here:
- Production refuses to start without a configured auth provider.
- No anonymous observation or evolution-control paths in production.
- No bearer tokens in URLs (cookie/header only).
"""
from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from fastapi import Depends, Request, Response, WebSocket
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.exceptions import UnauthenticatedError


# HTTP paths that mutate or inspect evolution state. Keep this deny-by-default
# list close to the security boundary so new evolution routes cannot silently
# become public when they are added without an explicit security dependency.
PROTECTED_CONTROL_PREFIXES = ("/evolve", "/production/readiness")


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
                    content={
                        "code": "SEC_UNAUTHENTICATED",
                        "message": "Authentication required",
                    },
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
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:*; "
            "frame-ancestors 'none';"
        )
        return response


def validate_cors_origins(origins: list) -> list:
    """Validate and sanitize CORS origins."""
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
    """Plugin-first authentication provider contract."""
    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        ...


@runtime_checkable
class WsAuthProvider(Protocol):
    async def authenticate(self, websocket: WebSocket) -> Optional[AuthContext]:
        ...


class SessionAuthProvider:
    """Signed, expiring operator session cookie provider."""

    def __init__(self, *, secret: str, cookie_name: str = "esap_operator_session", ttl_seconds: int = 3600) -> None:
        if len(secret) < 16:
            raise ValueError("session secret must be at least 16 characters")
        if ttl_seconds <= 0:
            raise ValueError("session ttl must be positive")
        self._secret = secret.encode("utf-8")
        self.cookie_name = cookie_name
        self.ttl_seconds = ttl_seconds

    def issue(self, subject: str, *, now: int) -> tuple[str, int]:
        import base64
        import json
        import time

        expires_at = int(now) + self.ttl_seconds
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": subject, "exp": expires_at}, separators=(",", ":"), sort_keys=True).encode()
        ).rstrip(b"=").decode()
        signature = hmac.new(self._secret, payload.encode(), "sha256").digest()
        encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        return f"{payload}.{encoded_signature}", expires_at

    def _verify(self, value: str, *, now: int) -> Optional[AuthContext]:
        import base64
        import json

        try:
            encoded, supplied = value.rsplit(".", 1)
            expected = base64.urlsafe_b64encode(hmac.new(self._secret, encoded.encode(), "sha256").digest()).rstrip(b"=").decode()
            if not hmac.compare_digest(supplied, expected):
                return None
            payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
            if int(now) >= int(payload["exp"]):
                return None
            return AuthContext(subject=str(payload["sub"]), scopes=("observe", "control"))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeError):
            return None

    async def authenticate(self, request: Request) -> Optional[AuthContext]:
        import time
        value = request.cookies.get(self.cookie_name)
        return self._verify(value, now=int(time.time())) if value else None



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
    """Called at startup. Fail-closed in production."""
    if environment == "production" and not providers:
        raise RuntimeError(
            "FATAL: production requires configured auth providers. "
            "Refusing to start (fail-closed)."
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
