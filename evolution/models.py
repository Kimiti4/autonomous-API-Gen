"""
Self-Evolution Engine data models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


class EvolutionTargetType(str, Enum):
    """Target type for evolution."""

    APPLICATION_ARCHITECTURE = "APPLICATION_ARCHITECTURE"
    PLATFORM_CORE = "PLATFORM_CORE"
    COMPILER_PIPELINE = "COMPILER_PIPELINE"
    ISR_SCHEMA = "ISR_SCHEMA"
    OPTIMIZATION_STRATEGY = "OPTIMIZATION_STRATEGY"


class ProposalStatus(str, Enum):
    """Lifecycle status for an evolution proposal."""

    DRAFT = "DRAFT"
    MUTATED = "MUTATED"
    SIMULATED = "SIMULATED"
    VERIFIED = "VERIFIED"
    EVALUATED = "EVALUATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class MutationOperationType(str, Enum):
    """Mutation operation type."""

    SET_VALUE = "SET_VALUE"
    ADD_ITEM = "ADD_ITEM"
    REMOVE_ITEM = "REMOVE_ITEM"
    MERGE_OBJECT = "MERGE_OBJECT"


class MutationOperationSpec(BaseModel):
    """A single mutation operation."""

    operation: MutationOperationType
    path: str
    value: Optional[Any] = None
    rationale: str = ""


class MutationSpec(BaseModel):
    """Specification of an architectural mutation."""

    id: Optional[str] = None

    operator: str
    chromosome_family: str
    gene_id: str

    operations: list[MutationOperationSpec] = Field(default_factory=list)
    rationale: str = ""


class EvolutionProposalRequest(BaseModel):
    """Request to create an evolution proposal."""

    title: str
    description: str = ""

    target_type: EvolutionTargetType
    target_ref: str

    base_isr: dict[str, Any]
    mutation: MutationSpec

    high_impact: bool = False
    allow_breaking_changes: bool = False

    environment: str = "development"


class CandidateArchitecture(BaseModel):
    """A mutated ISR candidate."""

    id: str
    proposal_id: str
    mutation_spec_id: str

    base_isr_hash: str
    content_hash: str

    isr: dict[str, Any]

    created_at: str


class SimulationIssue(BaseModel):
    """Issue discovered during simulation or verification."""

    severity: Literal[
        "ERROR",
        "WARNING",
        "INFO",
    ]

    code: str
    message: str


class SimulationResult(BaseModel):
    """Result of architecture simulation."""

    id: str
    candidate_id: str

    status: Literal[
        "PASSED",
        "FAILED",
    ]

    metrics: dict[str, Any] = Field(default_factory=dict)
    issues: list[SimulationIssue] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)

    created_at: str


class VerificationReport(BaseModel):
    """Compatibility and constitutional verification report."""

    candidate_id: str
    valid: bool

    issues: list[SimulationIssue] = Field(default_factory=list)

    created_at: str


class FitnessEvaluation(BaseModel):
    """Multi-objective fitness evaluation."""

    id: str
    candidate_id: str

    objectives: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, bool] = Field(default_factory=dict)

    passed: bool
    notes: list[str] = Field(default_factory=list)

    created_at: str


class GovernanceDecision(BaseModel):
    """Governance decision for evolution."""

    decision: Literal[
        "ALLOW",
        "DENY",
        "REQUIRE_APPROVAL",
        "REQUIRE_EVIDENCE",
    ]

    reason: str = ""

    constraints: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)


class ApprovalRecord(BaseModel):
    """Approval record for an evolution proposal."""

    approver_id: str
    decision: Literal[
        "APPROVED",
        "REJECTED",
    ]

    comments: str = ""
    governance_ref: Optional[str] = None

    created_at: str


class RollbackPlan(BaseModel):
    """Rollback plan for a promoted evolution."""

    parent_isr_hash: str
    steps: list[str] = Field(default_factory=list)
    automated: bool = False


class PromotionRecord(BaseModel):
    """Record of a promoted evolution."""

    id: str
    proposal_id: str
    candidate_id: str

    environment: str

    promoted_content_hash: str
    rollback_plan: RollbackPlan

    compilation_ref: Optional[str] = None

    status: str = "ACTIVE"

    rolled_back_at: Optional[str] = None
    rollback_reason: Optional[str] = None

    created_at: str


class EvolutionProposal(BaseModel):
    """Evolution proposal aggregate."""

    id: str
    status: ProposalStatus

    request: EvolutionProposalRequest

    candidate_ids: list[str] = Field(default_factory=list)
    simulation_ids: list[str] = Field(default_factory=list)

    verification: Optional[VerificationReport] = None
    fitness: Optional[FitnessEvaluation] = None

    governance_decision: Optional[GovernanceDecision] = None
    approval: Optional[ApprovalRecord] = None
    promotion: Optional[PromotionRecord] = None

    selected_candidate_id: Optional[str] = None
    error: Optional[str] = None

    created_at: str
    updated_at: str


class GenerateCandidatesRequest(BaseModel):
    """Request to generate multiple candidates for a proposal."""

    mutations: list[MutationSpec] = Field(default_factory=list)
    include_base_mutation: bool = True


class CandidateEvaluationRecord(BaseModel):
    """Evaluation state for one candidate architecture."""

    candidate_id: str

    simulation_id: Optional[str] = None
    verification: Optional[VerificationReport] = None
    fitness: Optional[FitnessEvaluation] = None

    feasible: bool = False
    reasons: list[str] = Field(default_factory=list)

    created_at: str


class ParetoSelectionPolicy(BaseModel):
    """Policy controlling Pareto selection."""

    objectives: list[str] = Field(default_factory=list)

    max_selected: int = Field(default=1, ge=1, le=20)

    min_objective_value: float = Field(default=0.2, ge=0.0, le=1.0)
    epsilon: float = Field(default=0.0, ge=0.0)

    require_constraints: bool = True


class ParetoCandidate(BaseModel):
    """A candidate within a Pareto front."""

    candidate_id: str
    rank: int
    crowding_distance: float

    objectives: dict[str, float] = Field(default_factory=dict)


class ParetoSelectionResult(BaseModel):
    """Result of Pareto selection."""

    proposal_id: str

    objectives: list[str] = Field(default_factory=list)

    fronts: list[list[ParetoCandidate]] = Field(default_factory=list)

    selected_candidate_ids: list[str] = Field(default_factory=list)
    selected_candidate_id: Optional[str] = None

    created_at: str


class EvolutionEvent(BaseModel):
    """Audit event for evolution history."""

    id: str
    proposal_id: str

    event_type: str
    actor_id: str

    details: dict[str, Any] = Field(default_factory=dict)

    timestamp: str

    previous_event_hash: str
    event_hash: str
