"""Evidence subsystem commands (§4.2). Frozen, intent-carrying DTOs."""
from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class StoreEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    evidenceId: str = Field(min_length=1)
    evidenceType: str = Field(min_length=1)
    producedBy: str = Field(min_length=1)
    subjectRef: Optional[str] = None
    artifact: Union[bytes, str]
    summary: str