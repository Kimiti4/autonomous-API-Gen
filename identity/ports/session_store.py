"""Session store port — persistence seam for sessions."""
from __future__ import annotations
from typing import Protocol
from identity.auth.session import Session


class SessionStore(Protocol):
    async def put(self, session: Session) -> None: ...
    async def get(self, session_id: str) -> Session | None: ...
    async def revoke(self, session_id: str) -> None: ...
