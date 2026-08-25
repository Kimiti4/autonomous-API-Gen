"""Auth protocol types — login results, MFA challenges."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict
from identity.core.principal import Principal


class LoginResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    authenticated: bool = False
    mfa_required: bool = False
    principal: Optional[Principal] = None
    error: Optional[str] = None


class MfaChallenge(BaseModel):
    model_config = ConfigDict(frozen=True)

    challenge_id: str
    factor_type: str = "totp"
