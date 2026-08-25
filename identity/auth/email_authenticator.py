"""Email authenticator — register + login with password."""
from __future__ import annotations
import uuid
from identity.core.principal import Principal
from identity.auth.password import PBKDF2PasswordHasher
from identity.auth.protocols import LoginResult
from identity.ports.user_store import StoredUser, UserStore


class ReferenceEmailAuthenticator:
    def __init__(self, user_store: UserStore, hasher: PBKDF2PasswordHasher | None = None) -> None:
        self._store = user_store
        self._hasher = hasher or PBKDF2PasswordHasher()

    async def register(self, email: str, password: str) -> Principal:
        hashed = self._hasher.hash(password)
        principal = Principal(
            principal_id=str(uuid.uuid4()),
            email=email,
            display_name=email.split("@")[0],
            created_at="",
        )
        await self._store.put(StoredUser(principal=principal, password_hash=hashed))
        return principal

    async def login(self, email: str, password: str) -> LoginResult:
        user = await self._store.get_by_email(email)
        if user is None:
            return LoginResult(error="user_not_found")
        if not self._hasher.verify(password, user.password_hash):
            return LoginResult(error="invalid_password")
        mfa_required = user.mfa_confirmed
        return LoginResult(
            authenticated=True,
            mfa_required=mfa_required,
            principal=user.principal,
        )
