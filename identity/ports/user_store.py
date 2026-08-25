"""User store port — persistence seam for user accounts."""
from __future__ import annotations
from typing import Protocol
from identity.core.principal import Principal


class StoredUser:
    def __init__(self, principal: Principal, password_hash: str) -> None:
        self.principal = principal
        self.password_hash = password_hash
        self.mfa_secret_b32: str | None = None
        self.mfa_confirmed: bool = False
        self.recovery_code_hashes: list[str] = []


class UserStore(Protocol):
    async def get_by_email(self, email: str) -> StoredUser | None: ...
    async def put(self, user: StoredUser) -> None: ...
