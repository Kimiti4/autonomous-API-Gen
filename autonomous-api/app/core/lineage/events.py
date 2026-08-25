"""Lineage domain events (§3.4). Past-tense, immutable, frozen."""
from __future__ import annotations

from typing import Union

from pydantic import BaseModel, ConfigDict

from app.core.contracts.lineage import (
    DeploymentLineage,
    EvolutionOperation,
    FitnessEvaluationLineage,
    OperationalFeedbackLineage,
    OriginSpec,
    VerificationLineage,
)


class CandidateOriginRecorded(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str
    generation: int
    isrRevision: str
    requirementIds: list
    origin: OriginSpec


class EvolutionOperationRecorded(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str
    operation: EvolutionOperation


class FitnessEvaluationRecorded(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str
    evaluation: FitnessEvaluationLineage


class VerificationRecorded(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str
    verification: VerificationLineage


class DeploymentRecorded(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str
    deployment: DeploymentLineage


class OperationalFeedbackRecorded(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str
    feedback: OperationalFeedbackLineage


LineageEvent = Union[
    CandidateOriginRecorded,
    EvolutionOperationRecorded,
    FitnessEvaluationRecorded,
    VerificationRecorded,
    DeploymentRecorded,
    OperationalFeedbackRecorded,
]