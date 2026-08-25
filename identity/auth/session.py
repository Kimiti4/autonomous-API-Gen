"""Session model — immutable authenticated session."""
from __future__ import annotations
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field


class Session(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    principal_id: str
    active_grants: Sequence[str] = Field(default_factory=list)
    created_at: str
    expires_at: str
    revoked: bool = False
