"""Governance subsystem commands (§2.3). Frozen, intent-carrying DTOs."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts.governance import (
    CouncilMember,
    GateStatus,
    GovernanceGate,
    LifecycleState,
    PolicySummary,
)


class RequestGovernanceDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    generation: int = Field(ge=0)
    fromState: LifecycleState
    toState: LifecycleState
    requestedBy: str = Field(min_length=1)  # agent role / Executive
    decidedBy: list = Field(min_length=1)   # memberIds / "executive" (G-5)
    verdict: str = "approve"                # DecisionVerdict
    authorizesTransition: bool = True
    rationale: str = ""
    supersedesDecisionId: Optional[str] = None
    evidenceRefs: list = Field(default_factory=list)


class RecordGateEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)
    gateId: str = Field(min_length=1)
    candidateId: str = Field(min_length=1)
    status: GateStatus
    evaluatedBy: str = Field(min_length=1)
    waivedBy: Optional[str] = None  # REQUIRED if status == "waived" (G-3)
    evidenceRefs: list = Field(default_factory=list)
    note: Optional[str] = None


class GrantCertification(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    certificationId: str = Field(min_length=1)
    certifiedBy: str = Field(min_length=1)
    criteria: str = Field(min_length=1)
    scope: Optional[str] = None
    validUntil: Optional[str] = None
    evidenceRefs: list = Field(default_factory=list)


class RevokeCertification(BaseModel):
    model_config = ConfigDict(frozen=True)
    certificationId: str = Field(min_length=1)
    revokedBy: str = Field(min_length=1)
    reason: str


class UpdateCouncil(BaseModel):
    model_config = ConfigDict(frozen=True)
    members: list[CouncilMember]
    updatedBy: str = Field(min_length=1)


class RegisterGate(BaseModel):
    model_config = ConfigDict(frozen=True)
    gate: GovernanceGate
    registeredBy: str = Field(min_length=1)


class RegisterPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    policy: PolicySummary
    registeredBy: str = Field(min_length=1)