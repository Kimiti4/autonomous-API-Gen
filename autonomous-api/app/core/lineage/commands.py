"""Lineage subsystem commands (§3.3). Frozen, intent-carrying DTOs."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts.lineage import (
    DeploymentLineage,
    EvolutionOperation,
    FitnessEvaluationLineage,
    OperationalFeedbackLineage,
    OriginSpec,
    VerificationLineage,
)


class RecordCandidateOrigin(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    generation: int = Field(ge=0)
    isrRevision: str = Field(min_length=1)  # REQUIRED — L-1
    requirementIds: list = Field(default_factory=list)
    origin: OriginSpec


class RecordEvolutionOperation(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    operation: EvolutionOperation


class RecordFitnessEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    evaluation: FitnessEvaluationLineage


class RecordVerification(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    verification: VerificationLineage


class RecordDeployment(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    deployment: DeploymentLineage


class RecordOperationalFeedback(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str = Field(min_length=1)
    feedback: OperationalFeedbackLineage