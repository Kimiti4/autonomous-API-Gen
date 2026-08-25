"""Evidence domain events (§4.2). Past-tense, immutable, frozen."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvidenceStored(BaseModel):
    model_config = ConfigDict(frozen=True)
    evidenceId: str = Field(min_length=1)
    contentHash: str = Field(min_length=64, max_length=64)
    storedAt: str