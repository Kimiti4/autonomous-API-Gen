"""Governed full-stack orchestration API schemas (Checkpoint 056)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


WorkloadId = Literal["payroll", "orders", "appointments", "inventory", "projects"]


class GovernedFullStackRunBody(BaseModel):
    workload_id: WorkloadId
    idempotency_key: str = Field(default="", max_length=128)
    artifact_sha256_bind: str = Field(default="", pattern=r"^([a-f0-9]{64})?$")
    populate_senior_dimensions: bool = False
    isr_ingress_authority: str = Field(default="isr.core.revision")
    governed_lineage_ref: str = Field(default="")
    plan_binding_digest: str = Field(default="", pattern=r"^([a-f0-9]{64})?$")


class GovernedFullStackRunResponse(BaseModel):
    authorityId: str
    runId: str
    workloadId: str
    candidateId: str
    lifecycleState: str
    governanceLifecycleState: str | None = None
    isrProvenance: str
    artifactSha256: str
    canonicalContractDigest: str
    productAcceptance: str
    certified: bool = False
    publicationAuthorized: bool = False
    blockers: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
