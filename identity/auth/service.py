"""AuthenticationService — orchestrates register / login / MFA step-up / session lifecycle."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict
from identity.core.principal import Principal
from identity.auth.session import Session
from identity.auth.protocols import MfaChallenge


class LoginOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str  # "session" | "mfa_required" | "failed"
    session: Optional[Session] = None
    mfa_challenge: Optional[MfaChallenge] = None
    principal: Optional[Principal] = None
    error: Optional[str] = None


class AuthenticationService:
    """Identity is infrastructure; nothing here enters the ISR or Evolution Engine."""

    TTL = 3600

    def __init__(self, email_auth, mfa_auth, sessions) -> None:
        self._email = email_auth
        self._mfa = mfa_auth
        self._sessions = sessions

    async def register(self, email: str, password: str) -> Principal:
        return await self._email.register(email, password)

    async def login(self, email: str, password: str) -> LoginOutcome:
        res = await self._email.login(email, password)
        if res.mfa_required and res.principal:
            ch = await self._mfa.challenge(res.principal)
            from dataclasses import asdict
            ch_dict = asdict(ch) if hasattr(ch, "__dataclass_fields__") else {"challenge_id": getattr(ch, "challenge_id", ""), "factor_type": getattr(ch, "factor_type", "totp")}
            return LoginOutcome(kind="mfa_required", mfa_challenge=MfaChallenge(**ch_dict), principal=res.principal)
        if res.authenticated and res.principal:
            s = await self._sessions.create(res.principal.principal_id, [], self.TTL)
            return LoginOutcome(kind="session", session=s)
        return LoginOutcome(kind="failed", error=res.error or "invalid")

    async def complete_mfa(self, principal: Principal, challenge_id: str, code: str) -> LoginOutcome:
        ok = await self._mfa.verify(principal, challenge_id, code)
        if not ok:
            return LoginOutcome(kind="failed", error="mfa_failed")
        s = await self._sessions.create(principal.principal_id, [], self.TTL)
        return LoginOutcome(kind="session", session=s)

    async def logout(self, session_id: str) -> None:
        await self._sessions._store.revoke(session_id)

    async def rotate(self, session_id: str) -> Session:
        return await self._sessions.rotate(session_id)
