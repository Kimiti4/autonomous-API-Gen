"""
Models for federated engineering organizations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FederationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISSOLVED = "DISSOLVED"


class FederationMembershipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REMOVED = "REMOVED"


class InitiativeStatus(str, Enum):
    OPEN = "OPEN"
    COORDINATING = "COORDINATING"
    EXECUTING = "EXECUTING"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class CouncilDecisionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    VOTING = "VOTING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class CrossOrganizationConflictStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class VotePosition(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"


class FederationDecisionPolicy(str, Enum):
    CONSENSUS = "CONSENSUS"
    MAJORITY_WEIGHTED = "MAJORITY_WEIGHTED"


class FederationCharter(BaseModel):
    """Charter governing a federation."""

    mission: str

    principles: List[str] = Field(default_factory=list)

    decision_policy: FederationDecisionPolicy = (
        FederationDecisionPolicy.MAJORITY_WEIGHTED
    )

    quorum_ratio: float = Field(default=0.5, ge=0.0, le=1.0)

    high_impact_requires_governance: bool = True

    security_veto: bool = True
    architecture_veto: bool = True


class Federation(BaseModel):
    """A federation of engineering organizations."""

    id: str
    name: str

    charter: FederationCharter

    status: FederationStatus = FederationStatus.ACTIVE

    created_at: str
    updated_at: str


class FederationMembership(BaseModel):
    """Membership of an organization in a federation."""

    federation_id: str
    organization_id: str

    status: FederationMembershipStatus = FederationMembershipStatus.ACTIVE

    weight: float = Field(default=1.0, ge=0.0, le=100.0)

    jurisdictions: List[str] = Field(default_factory=list)

    joined_at: str


class FederationInitiative(BaseModel):
    """Cross-organization initiative."""

    id: str
    federation_id: str

    title: str
    objective: str

    initiative_type: str

    required_roles: List[str] = Field(default_factory=list)

    member_organization_ids: List[str] = Field(default_factory=list)

    inputs: Dict[str, Any] = Field(default_factory=dict)

    high_impact: bool = False

    status: InitiativeStatus = InitiativeStatus.OPEN

    proposal_id: Optional[str] = None
    campaign_id: Optional[str] = None

    created_at: str
    updated_at: str


class DelegatedTaskRecord(BaseModel):
    """Record of a task delegated to a member organization."""

    id: str

    initiative_id: str
    federation_id: str
    organization_id: str
    task_id: str

    created_at: str


class CouncilVote(BaseModel):
    """Vote cast by a member organization."""

    id: str

    decision_id: str
    organization_id: str

    position: VotePosition

    weight: float = Field(default=1.0, ge=0.0, le=100.0)

    reason: str = ""

    created_at: str


class CouncilDecision(BaseModel):
    """Decision proposed to the federation council."""

    id: str

    federation_id: str

    title: str
    decision_type: str

    initiative_id: Optional[str] = None
    conflict_id: Optional[str] = None

    status: CouncilDecisionStatus = CouncilDecisionStatus.PROPOSED

    result: Optional[str] = None
    rationale: Optional[str] = None

    created_at: str
    updated_at: str


class CrossOrganizationConflict(BaseModel):
    """Conflict between member organizations."""

    id: str

    federation_id: str

    initiative_id: Optional[str] = None

    party_organization_ids: List[str] = Field(default_factory=list)

    subject_ref: str
    conflict_type: str

    recommendation_ids: List[str] = Field(default_factory=list)

    high_impact: bool = False

    status: CrossOrganizationConflictStatus = (
        CrossOrganizationConflictStatus.OPEN
    )

    selected_recommendation_id: Optional[str] = None

    resolution_note: Optional[str] = None
    resolved_by: Optional[str] = None

    created_at: str
    updated_at: str
