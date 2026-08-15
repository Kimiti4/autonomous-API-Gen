"""
Models for reputation, trust scoring, and capability certification.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReputationSubjectType(str, Enum):
    ORGANIZATION = "ORGANIZATION"
    AGENT = "AGENT"
    FEDERATION = "FEDERATION"


class ReputationOutcome(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class ReputationEventType(str, Enum):
    TASK_OUTCOME = "TASK_OUTCOME"
    INITIATIVE_OUTCOME = "INITIATIVE_OUTCOME"
    DECISION_OUTCOME = "DECISION_OUTCOME"
    PEER_REVIEW = "PEER_REVIEW"
    GOVERNANCE_APPROVAL = "GOVERNANCE_APPROVAL"
    GOVERNANCE_DENIAL = "GOVERNANCE_DENIAL"
    PRODUCTION_FEEDBACK = "PRODUCTION_FEEDBACK"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    QUALITY_REVIEW = "QUALITY_REVIEW"
    CONFLICT_RESOLUTION = "CONFLICT_RESOLUTION"
    PROMOTION_OUTCOME = "PROMOTION_OUTCOME"
    ROLLBACK_EVENT = "ROLLBACK_EVENT"


class ReputationEvent(BaseModel):
    """Evidence event contributing to reputation."""

    id: str

    subject_type: ReputationSubjectType
    subject_id: str

    event_type: ReputationEventType
    outcome: ReputationOutcome

    weight: float = Field(default=0.1, ge=0.0, le=1.0)

    capability: Optional[str] = None

    task_id: Optional[str] = None
    initiative_id: Optional[str] = None

    evidence_refs: List[str] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: str


class TrustPolicy(BaseModel):
    """Policy controlling trust scoring."""

    initial_trust: float = Field(default=0.5, ge=0.0, le=1.0)

    min_trust: float = Field(default=0.0, ge=0.0, le=1.0)
    max_trust: float = Field(default=1.0, ge=0.0, le=1.0)

    normalization_factor: float = Field(default=5.0, gt=0.0)

    half_life_days: float = Field(default=90.0, gt=0.0)

    confidence_event_target: float = Field(default=10.0, gt=0.0)

    max_event_weight: float = Field(default=1.0, ge=0.0, le=1.0)


class TrustReport(BaseModel):
    """Trust report for an organization, agent, or federation."""

    subject_type: ReputationSubjectType
    subject_id: str

    score: float
    confidence: float

    positive_effect: float = 0.0
    negative_effect: float = 0.0

    event_count: int = 0

    recent_positive_count: int = 0
    recent_negative_count: int = 0

    factors: Dict[str, Any] = Field(default_factory=dict)

    updated_at: str


class CertificationApplicationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CertificationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class CapabilityCertificationPolicy(BaseModel):
    """Policy required to certify a capability."""

    capability: str
    name: str

    description: str = ""

    required_evidence_types: List[str] = Field(default_factory=list)

    min_trust: float = Field(default=0.5, ge=0.0, le=1.0)

    min_completed_tasks: int = Field(default=0, ge=0)

    max_negative_events: int = Field(default=3, ge=0)

    ttl_days: int = Field(default=180, ge=1)

    require_governance: bool = False

    required_task_types: List[str] = Field(default_factory=list)

    required_roles: List[str] = Field(default_factory=list)


class CertificationApplication(BaseModel):
    """Application for capability certification."""

    id: str

    subject_type: ReputationSubjectType
    subject_id: str

    capability: str

    evidence_refs: List[str] = Field(default_factory=list)

    status: CertificationApplicationStatus = (
        CertificationApplicationStatus.PENDING
    )

    reason: Optional[str] = None

    created_at: str
    decided_at: Optional[str] = None


class CapabilityCertification(BaseModel):
    """Certification granted to an organization or agent."""

    id: str

    application_id: Optional[str] = None

    subject_type: ReputationSubjectType
    subject_id: str

    capability: str

    level: str = "certified"

    status: CertificationStatus = CertificationStatus.ACTIVE

    evidence_refs: List[str] = Field(default_factory=list)

    issued_at: str
    expires_at: str

    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None

    issuer: str = "reputation_engine"

    rationale: Optional[str] = None
