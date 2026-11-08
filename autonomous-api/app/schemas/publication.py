"""Request/response models for governed publication API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GovernedPublishBody(BaseModel):
    candidate_id: str = Field(min_length=1)
    isr_hash: str = Field(min_length=1)
    artifact_sha256: str = Field(min_length=64, max_length=64)
    source_revision: str = Field(min_length=1)
    artifact_manifest_digest: str = Field(min_length=64, max_length=64)
    certification_id: str = Field(min_length=1)
    deployment_ref: str = Field(min_length=1)
    include_handoff: bool = False
    isr_ingress_authority: str = Field(default="isr.core.revision")
    governed_lineage_ref: str = Field(default="")
