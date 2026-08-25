"""Governance domain events (§2.4). Past-tense, immutable, frozen."""
from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts.governance import (
    Certification,
    CouncilComposition,
    GateOutcome,
    GovernanceDecision,
    GovernanceGate,
    PolicySummary,
)


class GovernanceDecisionMade(BaseModel):
    """Emitted onto the observation stream as `governance.decision_made`."""
    model_config = ConfigDict(frozen=True)
    decision: GovernanceDecision


class GateEvaluated(BaseModel):
    model_config = ConfigDict(frozen=True)
    outcome: GateOutcome


class CertificationGranted(BaseModel):
    model_config = ConfigDict(frozen=True)
    certification: Certification


class CertificationRevoked(BaseModel):
    model_config = ConfigDict(frozen=True)
    certificationId: str = Field(min_length=1)
    revokedAt: str
    revokedBy: str = Field(min_length=1)


class CouncilUpdated(BaseModel):
    model_config = ConfigDict(frozen=True)
    composition: CouncilComposition
    updatedBy: str = Field(min_length=1)
    updatedAt: str


class GateRegistered(BaseModel):
    model_config = ConfigDict(frozen=True)
    gate: GovernanceGate


class PolicyRegistered(BaseModel):
    model_config = ConfigDict(frozen=True)
    policy: PolicySummary


GovernanceEvent = Union[
    GovernanceDecisionMade,
    GateEvaluated,
    CertificationGranted,
    CertificationRevoked,
    CouncilUpdated,
    GateRegistered,
    PolicyRegistered,
]