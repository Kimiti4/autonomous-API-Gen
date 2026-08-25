"""Evidence contract -- minimal placeholder for POC v1.1."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

class EvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    evidenceId: str = Field(min_length=1)
    contentHash: str = Field(min_length=64, max_length=64)
