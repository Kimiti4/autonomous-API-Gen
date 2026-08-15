"""
Models for evolutionary fitness feedback integration.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils import utcnow


class ObjectivePressure(BaseModel):
    """Pressure applied to one fitness objective."""

    objective: str

    pressure: float = Field(default=0.0, ge=0.0, le=1.0)

    severity: str = "INFO"

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    evidence_refs: List[str] = Field(default_factory=list)

    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())


class GenomeHint(BaseModel):
    """Hint for architectural genome refinement."""

    chromosome_family: str

    gene_id: str

    action: str

    priority: str = "MEDIUM"

    rationale: str

    evidence_refs: List[str] = Field(default_factory=list)


class EvolutionFeedbackBundle(BaseModel):
    """Bundle of evolutionary feedback produced from operational learning."""

    id: str

    scope: str = "platform"

    source_insight_ids: List[str] = Field(default_factory=list)

    objective_pressures: Dict[str, ObjectivePressure] = Field(
        default_factory=dict
    )

    genome_hints: List[GenomeHint] = Field(default_factory=list)

    recommended_actions: List[str] = Field(default_factory=list)

    priority: str = "MEDIUM"

    requires_governance: bool = False

    status: str = "GENERATED"

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class EvolutionSubmissionResult(BaseModel):
    """Result of submitting evolutionary feedback to the Evolution Engine."""

    submission_id: str

    status: str

    reason: str = ""

    proposal_id: Optional[str] = None

    submitted_at: str = Field(default_factory=lambda: utcnow().isoformat())


class EvolutionFeedbackPolicy(BaseModel):
    """Policy controlling evolutionary feedback generation."""

    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    pressure_threshold: float = Field(default=0.10, ge=0.0, le=1.0)

    high_pressure_threshold: float = Field(default=0.50, ge=0.0, le=1.0)

    max_pressures: int = Field(default=10, ge=1)

    critical_security_requires_governance: bool = True

    high_pressure_requires_governance: bool = True

    duplicate_suppression: bool = True


class FitnessFeedbackState(BaseModel):
    """Current fitness pressure state for a scope."""

    scope: str

    pressures: Dict[str, ObjectivePressure] = Field(default_factory=dict)

    last_updated: str = Field(default_factory=lambda: utcnow().isoformat())


class IntegrationReport(BaseModel):
    """Report produced by an integration sync."""

    generated_bundle_id: Optional[str] = None

    submission_id: Optional[str] = None

    status: str = "NO_ACTION"

    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())
