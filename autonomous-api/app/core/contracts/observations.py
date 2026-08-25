"""Observation contracts (POC v1.1 §3): flattened, read-only projections.

Framework-agnostic. No FastAPI / DB / engine imports.

Invariants:
1. Projectors never mutate canonical state (pure functions).
2. Every projection carries ContractMetadata + ObservationProvenance.
3. isOnParetoFrontier is computed by the platform — the dashboard is
   forbidden from recomputing it.
4. designDimensions are human-readable summaries, not raw encodings.
5. No endpoint returns the full canonical ISR graph.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts.provenance import (
    ContractMetadata,
    ObservationProvenance,
)


class ISRObservation(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: ContractMetadata
    provenance: ObservationProvenance
    isrRevision: str
    domains: list
    services: list
    deploymentTargets: list


class DomainSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    capabilityCount: int = Field(ge=0)


class ServiceSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    domain: str


class DeploymentTargetSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    target: str
    serviceCount: int = Field(ge=0)


ObjectiveDirection = Literal["maximize", "minimize"]


class FitnessObjective(BaseModel):
    model_config = ConfigDict(frozen=True)
    dimension: str
    direction: ObjectiveDirection
    normalization: str


class CandidateFitness(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidateId: str
    scores: dict
    isOnParetoFrontier: bool  # AUTHORITATIVE: computed by the platform


class FitnessReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: ContractMetadata
    provenance: ObservationProvenance
    generation: int = Field(ge=0)
    evaluatedAt: str
    objectives: list
    candidates: list
    paretoFrontierCandidateIds: list


class DesignDimension(BaseModel):
    model_config = ConfigDict(frozen=True)
    family: str
    summary: str


class CandidateProjection(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: ContractMetadata
    provenance: ObservationProvenance
    candidateId: str
    generation: int = Field(ge=0)
    lifecycleState: str
    designDimensions: list
    parentCandidateIds: list = Field(default_factory=list)
    evidenceRefs: list = Field(default_factory=list)


class RecoveryResult(BaseModel):
    """Returned by GET /observation/state.

    AM-3 (normative): `state` is the MATERIALIZED state AS OF `sequence`.
    Applying `replayEvents` (ascending; each sequence > `sequence`) yields
    the current state.
    """
    model_config = ConfigDict(frozen=True)
    state: dict
    sequence: int = Field(ge=-1)
    replayEvents: list = Field(default_factory=list)


class ObservationSnapshotWrapper(BaseModel):
    """AM-4: hydration wrapper — current materialized state + its stream
    sequence. Returned by GET /observation/snapshot."""
    model_config = ConfigDict(frozen=True)
    data: dict
    streamId: str = Field(min_length=1)
    sequence: int = Field(ge=-1)


class CapabilitySchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    contractId: str
    versions: list


class CapabilityFeature(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    version: str


class CapabilityContract(BaseModel):
    model_config = ConfigDict(frozen=True)
    contractId: str = "platform.observation.capabilities"
    schemaVersion: str = "1.0.0"
    observationSchemas: list
    eventTypes: list
    supportedStreamIds: list
    features: list