"""Session manager — create, rotate, revoke, validate sessions."""
from __future__ import annotations
import uuid
from identity.auth.session import Session
from identity.ports.session_store import SessionStore


class ReferenceSessionManager:
    def __init__(self, store: SessionStore, ttl: int = 3600) -> None:
        self._store = store
        self._ttl = ttl

    async def create(self, principal_id: str, grants: list[str], ttl: int | None = None) -> Session:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        exp = datetime.now(timezone.utc)
        s = Session(
            session_id=str(uuid.uuid4()),
            principal_id=principal_id,
            active_grants=grants,
            created_at=now.isoformat(),
            expires_at=exp.isoformat(),
        )
        await self._store.put(s)
        return s

    async def rotate(self, session_id: str) -> Session:
        old = await self._store.get(session_id)
        if old is None:
            raise ValueError("session not found")
        await self._store.revoke(session_id)
        return await self.create(old.principal_id, list(old.active_grants))

    async def validate(self, session_id: str) -> Session | None:
        s = await self._store.get(session_id)
        if s is None or s.revoked:
            return None
        return s
