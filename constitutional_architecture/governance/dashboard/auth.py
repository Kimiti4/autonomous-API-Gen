"""
Phase 28 — Governance Dashboard authentication and authorization.

Session-based auth with role-based access and CSRF protection. The
dashboard grants web-level permissions only; every mutation is re-checked
by the Governance Kernel, whose authorization remains authoritative.

Permissions:
  read               view any page
  approve / reject   act on approval queue (POST)
  revoke_exception   revoke an exception (POST)
  verify_integrity   run audit chain verification (POST)
"""

from __future__ import annotations

import secrets
import time
import uuid
from typing import Dict, Mapping, Optional, Tuple

from constitutional_architecture.governance.dashboard.config import DashboardConfig
from constitutional_architecture.governance.dashboard.errors import (
    ForbiddenError,
    UnauthorizedError,
)

SESSION_COOKIE = "gov_session"
CSRF_HEADER = "X-CSRF-Token"


class SessionManager:
    """In-memory sessions with CSRF tokens. Replaceable by OIDC later."""

    def __init__(self, config: DashboardConfig) -> None:
        self.config = config
        self._sessions: Dict[str, dict] = {}

    def create_session(self, username: str) -> Tuple[str, dict]:
        token = secrets.token_urlsafe(24)
        session = {
            "username": username,
            "roles": tuple(self.config.users[username][1]),
            "created_at": time.time(),
            "last_seen": time.time(),
            "csrf": secrets.token_urlsafe(24),
        }
        self._sessions[token] = session
        return token, session

    def get_session(self, token: Optional[str]) -> Optional[dict]:
        if not token:
            return None
        session = self._sessions.get(token)
        if session is None:
            return None
        if time.time() - session["last_seen"] > self.config.session_ttl_seconds:
            self._sessions.pop(token, None)
            return None
        session["last_seen"] = time.time()
        return session

    def destroy_session(self, token: Optional[str]) -> None:
        if token:
            self._sessions.pop(token, None)

    def verify_csrf(self, session: dict, token: Optional[str]) -> None:
        expected = session.get("csrf")
        if not expected or not token or not secrets.compare_digest(expected, token):
            raise ForbiddenError("Invalid or missing CSRF token.")


class AuthenticatedUser:
    def __init__(self, username: str, roles: Tuple[str, ...]) -> None:
        self.username = username
        self.roles = roles

    @property
    def actor_id(self) -> str:
        return f"user:{self.username}"

    def has_permission(self, permission: str, config: DashboardConfig) -> bool:
        return any(
            permission in config.role_permissions.get(role, ())
            for role in self.roles
        )

    def kernel_roles(self, config: DashboardConfig) -> Tuple[str, ...]:
        roles: set[str] = set()
        for role in self.roles:
            roles.update(config.kernel_role_map.get(role, ()))
        return tuple(sorted(roles))

    def to_actor(self, config: DashboardConfig):
        from constitutional_architecture.governance.schemas import Actor, ActorType

        return Actor(
            actor_type=ActorType.HUMAN,
            actor_id=self.actor_id,
            roles=list(self.kernel_roles(config)),
            delegated_authority=[],
        )


class Authenticator:
    """Login/logout + per-route permission checks."""

    def __init__(self, config: DashboardConfig, sessions: SessionManager) -> None:
        self.config = config
        self.sessions = sessions

    def login(self, username: str, password: str) -> Tuple[str, dict]:
        entry = self.config.users.get(username)
        if entry is None or entry[0] != password:
            raise UnauthorizedError("Invalid credentials.")
        return self.sessions.create_session(username)

    def logout(self, token: Optional[str]) -> None:
        self.sessions.destroy_session(token)

    def require_user(self, token: Optional[str]) -> AuthenticatedUser:
        session = self.sessions.get_session(token)
        if session is None:
            raise UnauthorizedError("Authentication required.")
        return AuthenticatedUser(session["username"], session["roles"])

    def require_permission(
        self, token: Optional[str], permission: str
    ) -> AuthenticatedUser:
        user = self.require_user(token)
        if not user.has_permission(permission, self.config):
            raise ForbiddenError(
                f"{permission} requires a privileged role."
            )
        return user

    def require_csrf(self, session: dict, token: Optional[str]) -> None:
        self.sessions.verify_csrf(session, token)


def session_token_from_request(request) -> Optional[str]:
    return request.cookies.get(SESSION_COOKIE) or request.headers.get(SESSION_COOKIE)


def csrf_token_from_request(request) -> Optional[str]:
    return request.headers.get(CSRF_HEADER)
