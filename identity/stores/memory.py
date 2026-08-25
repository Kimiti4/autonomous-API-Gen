"""In-memory reference stores for identity (tests + gate verification)."""
from __future__ import annotations
from identity.ports.user_store import StoredUser
from identity.auth.session import Session


class InMemoryUserStore:
    def __init__(self) -> None:
        self._d: dict[str, StoredUser] = {}

    async def get_by_email(self, email: str) -> StoredUser | None:
        return self._d.get(email)

    async def put(self, user: StoredUser) -> None:
        self._d[user.principal.email] = user


class InMemorySessionStore:
    def __init__(self) -> None:
        self._d: dict[str, Session] = {}

    async def put(self, session: Session) -> None:
        self._d[session.session_id] = session

    async def get(self, session_id: str) -> Session | None:
        return self._d.get(session_id)

    async def revoke(self, session_id: str) -> None:
        if session_id in self._d:
            self._d[session_id] = self._d[session_id].model_copy(update={"revoked": True})
