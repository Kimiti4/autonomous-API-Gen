"""
Core models for the Autonomous Engineering Civilization.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .utils import utcnow


class OrganizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISSOLVED = "DISSOLVED"


class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class MembershipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REMOVED = "REMOVED"


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ESCALATED = "ESCALATED"


class ConflictStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class DecisionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class OrganizationCharter(BaseModel):
    """Charter governing an engineering organization."""

    mission: str

    principles: List[str] = Field(default_factory=list)

    required_roles: List[str] = Field(default_factory=list)

    max_agents: int = Field(default=25, ge=1, le=500)

    high_impact_requires_governance: bool = True


class Organization(BaseModel):
    """A persistent engineering organization."""

    id: str
    name: str

    charter: OrganizationCharter

    status: OrganizationStatus = OrganizationStatus.ACTIVE

    leader_agent_id: Optional[str] = None

    created_at: str
    updated_at: str


class RoleDefinition(BaseModel):
    """Definition of an engineering role."""

    role_id: str
    name: str

    responsibilities: List[str] = Field(default_factory=list)

    permissions: List[str] = Field(
        default_factory=lambda: [
            "recommend",
            "review",
        ]
    )

    authority_weight: float = Field(default=0.5, ge=0.0, le=1.0)

    required_evidence_types: List[str] = Field(default_factory=list)


class AgentProfile(BaseModel):
    """Profile for an autonomous engineering agent."""

    agent_id: str
    name: str

    role_id: str

    capabilities: List[str] = Field(default_factory=list)

    trust_level: float = Field(default=0.5, ge=0.0, le=1.0)

    status: AgentStatus = AgentStatus.ACTIVE


class Membership(BaseModel):
    """Membership of an agent in an organization."""

    organization_id: str
    agent_id: str
    role_id: str

    status: MembershipStatus = MembershipStatus.ACTIVE

    joined_at: str


class EngineeringTask(BaseModel):
    """Engineering task assigned to an organization."""

    id: str
    organization_id: str

    title: str
    objective: str

    task_type: str

    required_roles: List[str] = Field(default_factory=list)

    inputs: Dict[str, Any] = Field(default_factory=dict)

    priority: int = Field(default=50, ge=0, le=100)

    high_impact: bool = False

    status: TaskStatus = TaskStatus.OPEN

    assigned_agent_ids: List[str] = Field(default_factory=list)

    proposal_id: Optional[str] = None
    campaign_id: Optional[str] = None

    created_at: str
    updated_at: str


class RecommendationInput(BaseModel):
    """Recommendation payload produced by an agent runtime."""

    action: str
    target_ref: str

    rationale: str

    evidence_refs: List[str] = Field(default_factory=list)

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class AgentRecommendation(BaseModel):
    """Recommendation submitted by an agent."""

    id: str

    task_id: str
    agent_id: str
    role_id: str

    action: str
    target_ref: str

    rationale: str

    evidence_refs: List[str] = Field(default_factory=list)

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    created_at: str


class ConflictRecord(BaseModel):
    """Conflict between recommendations."""

    id: str

    task_id: str

    recommendation_ids: List[str] = Field(default_factory=list)

    conflict_type: str

    status: ConflictStatus = ConflictStatus.OPEN

    selected_recommendation_id: Optional[str] = None

    resolution_note: Optional[str] = None
    resolved_by: Optional[str] = None

    created_at: str


class CollaborationDecision(BaseModel):
    """Decision produced by collaboration."""

    id: str

    task_id: str

    status: DecisionStatus

    selected_recommendation_ids: List[str] = Field(default_factory=list)
    conflict_ids: List[str] = Field(default_factory=list)

    rationale: str

    created_at: str


class LeadershipTerm(BaseModel):
    """Leadership term for an organization."""

    id: str

    organization_id: str
    leader_agent_id: str

    method: str

    rationale: str

    elected_at: str
