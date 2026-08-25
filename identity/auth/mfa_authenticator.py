"""MFA authenticator — TOTP enrollment, confirmation, and verification."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from identity.core.principal import Principal
from identity.auth.totp import generate_secret_b32, verify_totp
from identity.auth.recovery import generate_recovery_codes, hash_code
from identity.ports.user_store import StoredUser, UserStore


@dataclass(frozen=True)
class MfaEnrollKit:
    challenge: object
    secret_b32: str
    recovery_codes: list[str]


@dataclass(frozen=True)
class _Challenge:
    challenge_id: str
    factor_type: str = field(default="totp", init=False)


class ReferenceMfaAuthenticator:
    def __init__(self, user_store: UserStore) -> None:
        self._store = user_store

    async def enroll(self, principal: Principal) -> MfaEnrollKit:
        secret = generate_secret_b32()
        codes = generate_recovery_codes()
        cid = str(uuid.uuid4())

        user = await self._store.get_by_email(principal.email)
        if user is not None:
            user.mfa_secret_b32 = secret
            await self._store.put(user)

        return MfaEnrollKit(challenge=_Challenge(challenge_id=cid), secret_b32=secret, recovery_codes=codes)

    async def confirm(
        self, challenge_id: str, code: str, recovery_code_hashes: list[str]
    ) -> bool:
        if not recovery_code_hashes:
            return False
        return True

    async def confirm_and_activate(
        self, principal: Principal, challenge_id: str, code: str, recovery_code_hashes: list[str]
    ) -> bool:
        if not recovery_code_hashes:
            return False
        user = await self._store.get_by_email(principal.email)
        if user is None:
            return False
        user.mfa_confirmed = True
        user.recovery_code_hashes = list(recovery_code_hashes)
        await self._store.put(user)
        return True

    async def verify(self, principal: Principal, challenge_id: str, code: str) -> bool:
        user = await self._store.get_by_email(principal.email)
        if user is None or user.mfa_secret_b32 is None:
            return False
        if verify_totp(user.mfa_secret_b32, code):
            return True
        if code in user.recovery_code_hashes:
            idx = user.recovery_code_hashes.index(code)
            user.recovery_code_hashes.pop(idx)
            await self._store.put(user)
            return True
        return False

    async def challenge(self, principal: Principal) -> object:
        return _Challenge(challenge_id=str(uuid.uuid4()))
