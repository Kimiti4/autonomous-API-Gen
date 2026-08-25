"""Lineage contract value objects (write-side canonical subsystem).

Framework-agnostic. No FastAPI / DB / engine imports.

Lineage is the immutable, append-only causal history of every candidate
("why does this exist"). It never decides, never gates.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

OriginOperationType = Literal["genesis", "mutation", "crossover", "refinement"]


class OriginSpec(BaseModel):
    """How the candidate came into existence (L-2)."""
    model_config = ConfigDict(frozen=True)
    operationType: OriginOperationType
    parentCandidateIds: list = Field(default_factory=list)  # empty iff genesis
    operationId: str = Field(min_length=1)
    summary: str


class EvolutionOperation(BaseModel):
    model_config = ConfigDict(frozen=True)
    operationId: str = Field(min_length=1)
    operationType: str = Field(min_length=1)
    generation: int = Field(ge=0)
    summary: str
    occurredAt: str


class FitnessEvaluationLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    evaluationId: str = Field(min_length=1)
    generation: int = Field(ge=0)
    fitnessScore: float
    objectiveScores: dict = Field(default_factory=dict)
    evaluatedAt: str


class VerificationLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    verificationId: str = Field(min_length=1)
    verifiedBy: str = Field(min_length=1)
    verdict: str  # pass | fail | inconclusive
    evidenceRefs: list = Field(default_factory=list)
    verifiedAt: str


class DeploymentLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    deploymentId: str = Field(min_length=1)
    target: str = Field(min_length=1)
    deployedBy: str = Field(min_length=1)
    deployedAt: str


class OperationalFeedbackLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    feedbackId: str = Field(min_length=1)
    source: str = Field(min_length=1)
    summary: str
    influencedNextGeneration: bool = False  # L-6 loop linkage
    receivedAt: str


class CandidateLineageState(BaseModel):
    """Materialized lineage for one candidate — the fold of its event log."""
    model_config = ConfigDict(frozen=True)
    candidateId: str
    generation: int = Field(ge=0)
    isrRevision: str
    requirementIds: list = Field(default_factory=list)
    origin: Optional[OriginSpec] = None
    operations: list = Field(default_factory=list)
    evaluations: list = Field(default_factory=list)
    verifications: list = Field(default_factory=list)
    deployments: list = Field(default_factory=list)
    feedback: list = Field(default_factory=list)


CandidateLineage = CandidateLineageState