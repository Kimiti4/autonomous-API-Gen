"""
Models for continuous learning.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .utils import utcnow


class LearningSignalType(str, Enum):
    PERFORMANCE = "PERFORMANCE"
    INCIDENT = "INCIDENT"
    RELIABILITY = "RELIABILITY"
    COST = "COST"
    SECURITY = "SECURITY"
    CUSTOMER_FEEDBACK = "CUSTOMER_FEEDBACK"
    USAGE = "USAGE"
    LOG = "LOG"
    TRACE = "TRACE"
    AUDIT = "AUDIT"


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def severity_rank(severity: Severity) -> int:
    """Return numeric rank for severity."""
    return SEVERITY_RANK.get(severity, 0)


class LearningSignal(BaseModel):
    """Normalized learning signal."""

    id: Optional[str] = None

    source: str

    subject_ref: Optional[str] = None

    signal_type: LearningSignalType

    severity: Severity = Severity.INFO

    metric: Optional[str] = None

    value: float = 0.0

    unit: Optional[str] = None

    message: Optional[str] = None

    labels: Dict[str, str] = Field(default_factory=dict)

    evidence_refs: List[str] = Field(default_factory=list)

    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())


class LearningInsight(BaseModel):
    """Insight derived from one or more signals."""

    id: str

    title: str

    description: str

    affected_subjects: List[str] = Field(default_factory=list)

    signal_ids: List[str] = Field(default_factory=list)

    objectives: List[str] = Field(default_factory=list)

    severity: Severity = Severity.INFO

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    recommendations: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class LearningRecommendation(BaseModel):
    """Recommendation produced from learning insights."""

    id: str

    subject_ref: str

    action: str

    chromosome_family: str

    gene_id: str

    priority: str = "MEDIUM"

    rationale: str

    evidence_refs: List[str] = Field(default_factory=list)

    requires_governance: bool = False


class FitnessUpdate(BaseModel):
    """Fitness pressure update derived from learning."""

    id: str

    subject_ref: str

    objective_pressures: Dict[str, float] = Field(default_factory=dict)

    constraints: Dict[str, bool] = Field(default_factory=dict)

    rationale: str

    evidence_refs: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class GenomeRefinementHint(BaseModel):
    """Hint for genome refinement."""

    chromosome_family: str

    gene_id: str

    action: str

    priority: str = "MEDIUM"

    rationale: str

    evidence_refs: List[str] = Field(default_factory=list)


class ArchitectureFeedbackBundle(BaseModel):
    """Governed feedback bundle for the Evolution Engine."""

    id: str

    scope: str

    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())

    signal_ids: List[str] = Field(default_factory=list)

    insight_ids: List[str] = Field(default_factory=list)

    fitness_updates: List[FitnessUpdate] = Field(default_factory=list)

    genome_hints: List[GenomeRefinementHint] = Field(default_factory=list)

    recommendations: List[LearningRecommendation] = Field(default_factory=list)

    governance_required: bool = True

    status: str = "DRAFT"


class LearningPolicy(BaseModel):
    """Policy controlling continuous learning behavior."""

    latency_threshold_ms: float = Field(default=500.0, ge=0.0)

    error_rate_threshold: float = Field(default=0.05, ge=0.0, le=1.0)

    monthly_cost_threshold: float = Field(default=1000.0, ge=0.0)

    min_signals_for_insight: int = Field(default=1, ge=1)

    critical_security_requires_governance: bool = True

    high_severity_requires_governance: bool = True
