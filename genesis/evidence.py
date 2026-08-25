"""Genesis Evidence — coverage, consistency, and validation records."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field


class CoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_to_isr: Mapping[str, Sequence[str]] = Field(default_factory=dict)
    uncovered: Sequence[str] = Field(default_factory=list)


class ConsistencyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    ambiguities_resolved: int = 0
    conflicts_resolved: int = 0
    unresolved_escalated: Sequence[str] = Field(default_factory=list)


class ValidationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    adr008_invariants_passed: bool = False
    content_hash: str = ""


class GenesisEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    genesis_id: str
    mapping_spec_version: str
    requirement_graph_hash: str
    isr_candidate_hash: str
    coverage: CoverageReport
    consistency: ConsistencyReport
    validation: ValidationRecord
    constitutional_defaults_applied: Sequence[str] = Field(default_factory=list)
    created_by: str
    created_at: str


class EvidenceProjection(BaseModel):
    """1:1 shape with v1.1 EvidenceRecord; feeds the accountability plane."""

    model_config = ConfigDict(frozen=True)

    evidenceId: str
    evidenceType: str
    producedBy: str
    producedAt: str
    subjectRef: str
    summary: str
    contentHash: str


def _model_hash(model: BaseModel) -> str:
    payload = json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_to_v11_evidence(ev: GenesisEvidence) -> list[EvidenceProjection]:
    h = ev.isr_candidate_hash
    return [
        EvidenceProjection(
            evidenceId=f"{ev.genesis_id}:coverage",
            evidenceType="genesis-coverage",
            producedBy=ev.created_by,
            producedAt=ev.created_at,
            subjectRef=h,
            summary="requirement to ISR coverage",
            contentHash=_model_hash(ev.coverage),
        ),
        EvidenceProjection(
            evidenceId=f"{ev.genesis_id}:consistency",
            evidenceType="genesis-consistency",
            producedBy=ev.created_by,
            producedAt=ev.created_at,
            subjectRef=h,
            summary="requirement graph consistency",
            contentHash=_model_hash(ev.consistency),
        ),
        EvidenceProjection(
            evidenceId=f"{ev.genesis_id}:validation",
            evidenceType="genesis-validation",
            producedBy=ev.created_by,
            producedAt=ev.created_at,
            subjectRef=h,
            summary="ADR-008 invariant validation",
            contentHash=_model_hash(ev.validation),
        ),
    ]
