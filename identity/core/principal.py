"""Principal — the authenticated identity."""
from __future__ import annotations
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field


class Principal(BaseModel):
    model_config = ConfigDict(frozen=True)

    principal_id: str = Field(min_length=1)
    email: str = Field(min_length=1)
    display_name: str = ""
    providers: Sequence[str] = Field(default_factory=list)
    mfa_enabled: bool = False
    created_at: str = ""
