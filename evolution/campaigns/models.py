"""
Models for multi-generation evolution campaigns.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from evolution.utils import utcnow


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    GOVERNANCE_HOLD = "GOVERNANCE_HOLD"


class StopPolicy(BaseModel):
    """Policy controlling when a campaign stops."""

    max_generations: int = Field(default=5, ge=1)

    target_objectives: Dict[str, float] = Field(default_factory=dict)

    stagnation_generations: int = Field(default=3, ge=1)

    min_improvement: float = Field(default=0.01, ge=0.0)

    max_elites: int = Field(default=20, ge=1)


class EvolutionCandidate(BaseModel):
    """Candidate architecture generated during a campaign."""

    id: str

    campaign_id: str

    generation_index: int

    genome_ref: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateFitness(BaseModel):
    """Fitness result for one candidate."""

    candidate_id: str

    objectives: Dict[str, float] = Field(default_factory=dict)

    constraints: Dict[str, bool] = Field(default_factory=dict)

    passed: bool = False

    evaluated_at: str = Field(default_factory=lambda: utcnow().isoformat())


class GenerationRecord(BaseModel):
    """Record of one generation inside a campaign."""

    generation_index: int

    candidate_ids: List[str] = Field(default_factory=list)

    selected_candidate_ids: List[str] = Field(default_factory=list)

    elite_candidate_ids: List[str] = Field(default_factory=list)

    best_objectives: Dict[str, float] = Field(default_factory=dict)

    improvements_count: int = 0

    stagnation_counter: int = 0

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class EliteRecord(BaseModel):
    """Elite candidate preserved in evolutionary memory."""

    candidate_id: str

    campaign_id: str

    generation_index: int

    objectives: Dict[str, float] = Field(default_factory=dict)

    genome_ref: Optional[str] = None

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class EvolutionCampaign(BaseModel):
    """Evolution campaign aggregate."""

    id: str

    name: str

    objective: str

    genome_ref: Optional[str] = None

    status: CampaignStatus = CampaignStatus.DRAFT

    population_size: int = Field(default=5, ge=1)

    stop_policy: StopPolicy = Field(default_factory=StopPolicy)

    generations: List[GenerationRecord] = Field(default_factory=list)

    elites: List[EliteRecord] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())

    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())


class CampaignReport(BaseModel):
    """Report produced for a campaign."""

    campaign_id: str

    status: CampaignStatus

    generation_count: int = 0

    elite_count: int = 0

    best_objectives: Dict[str, float] = Field(default_factory=dict)

    objective_trends: Dict[str, List[float]] = Field(default_factory=dict)

    recommendations: List[str] = Field(default_factory=list)

    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())


class EvolutionaryMemoryRecord(BaseModel):
    """Record stored in evolutionary memory."""

    campaign_id: str

    generation_index: Optional[int] = None

    record_type: str

    payload: Dict[str, Any] = Field(default_factory=dict)

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())
