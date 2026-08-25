"""ContractMetadata + ObservationProvenance (POC v1.1 §2).

Framework-agnostic. No FastAPI / DB / engine imports.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ContractMetadata(BaseModel):
    """Identity + version of an observation contract."""
    model_config = ConfigDict(frozen=True)
    contractId: str = Field(min_length=1)
    schemaVersion: str = Field(min_length=1)


class ObservationProvenance(BaseModel):
    """Uniform audit trail attached to every observation + error."""
    model_config = ConfigDict(frozen=True)
    sourceRevision: str = Field(min_length=1)
    sourceSubsystem: str = Field(min_length=1)
    capturedAt: datetime
    contentHash: str = Field(min_length=64, max_length=64)


def now_utc() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)