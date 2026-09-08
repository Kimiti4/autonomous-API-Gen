"""VS-D15 — central authorization policy boundary (central-policy profile).

This component is the architectural delta of vs1-evolved-96fe2d29fd76:
all authorization decisions flow through one explicit, auditable policy
boundary instead of living inline in each service operation. Behavior is
preserved; responsibility placement is what evolved.
"""

from __future__ import annotations

from vertical_slice.app.models import Membership, User
from vertical_slice.app.service import (
    AuthError as _AuthError,
)
from vertical_slice.app.service import (
    AuthorizationError as _AuthorizationError,
)
from vertical_slice.app.store import TaskTrackerStore

AuthError = _AuthError
AuthorizationError = _AuthorizationError

_INVALID_CREDENTIALS = "invalid credentials"


class AuthorizationPolicy:
    """Central policy boundary: the single place authorization is decided."""

    def __init__(self, store: TaskTrackerStore) -> None:
        self._store = store

    def check_session(self, token: str | None) -> User:
        if not token:
            raise AuthError(_INVALID_CREDENTIALS)
        session = self._store.get_session(token)
        if session is None:
            raise AuthError(_INVALID_CREDENTIALS)
        user = self._store.get_user(session.user_id)
        if user is None:
            raise AuthError(_INVALID_CREDENTIALS)
        return user

    def check_member(self, workspace_id: str, user_id: str) -> Membership:
        membership = self._store.membership(workspace_id, user_id)
        if membership is None:
            raise AuthorizationError("caller is not a workspace member")
        return membership

    def check_admin(self, workspace_id: str, user_id: str) -> None:
        membership = self.check_member(workspace_id, user_id)
        if membership.role != "admin":
            raise AuthorizationError("admin role required")
