"""Governance contract value objects (write-side canonical subsystem).

Framework-agnostic. No FastAPI / DB / engine imports.

These are the shared vocabulary for the Governance subsystem's commands,
domain events, aggregate, and the observation-layer projection.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

LifecycleState = Literal[
    "proposed",
    "evaluating",
    "verified",
    "certified",
    "selected",
    "deployed",
    "operating",
    "retired",
]

# Legal lifecycle ordering (§2.2). Each arrow is guarded by gates.
LIFECYCLE_ORDER: dict = {
    "proposed": 0,
    "evaluating": 1,
    "verified": 2,
    "certified": 3,
    "selected": 4,
    "deployed": 5,
    "operating": 6,
    "retired": 7,
}

# Required gate categories per transition (§2.2 table).
TRANSITION_GATES: dict = {
    ("proposed", "evaluating"): ("intake",),
    ("evaluating", "verified"): ("verification",),
    ("verified", "certified"): ("certification",),
    ("certified", "selected"): ("selection",),
    ("selected", "deployed"): ("deployment-readiness",),
    ("deployed", "operating"): ("operational-readiness",),
    ("operating", "retired"): ("retirement",),
}

GateStatus = Literal["pending", "passed", "failed", "waived"]

DecisionVerdict = Literal["approve", "reject", "defer"]

GateCategory = Literal[
    "intake", "verification", "certification", "selection",
    "deployment-readiness", "operational-readiness", "retirement",
    "constitution", "security", "policy",
]


class CouncilMember(BaseModel):
    """A governance council member with voting weight (G-7)."""
    model_config = ConfigDict(frozen=True)
    memberId: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    votingWeight: float = Field(ge=0)


class CouncilComposition(BaseModel):
    model_config = ConfigDict(frozen=True)
    members: list = Field(default_factory=list)
    updatedAt: Optional[str] = None


class TransitionRef(BaseModel):
    """A guarded lifecycle arrow, e.g. proposed -> evaluating."""
    model_config = ConfigDict(frozen=True)
    fromState: LifecycleState
    toState: LifecycleState


class GovernanceGate(BaseModel):
    """A registered gate guarding one or more transitions."""
    model_config = ConfigDict(frozen=True)
    gateId: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: GateCategory
    guards: list = Field(default_factory=list)
    description: Optional[str] = None


class PolicySummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    policyId: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    summary: str


class GateOutcome(BaseModel):
    """Result of evaluating a gate for a candidate (immutable once recorded)."""
    model_config = ConfigDict(frozen=True)
    gateId: str = Field(min_length=1)
    candidateId: str = Field(min_length=1)
    status: GateStatus
    evaluatedBy: str = Field(min_length=1)
    waivedBy: Optional[str] = None  # REQUIRED iff status == "waived" (G-3)
    evidenceRefs: list = Field(default_factory=list)
    note: Optional[str] = None
    evaluatedAt: str


class GovernanceDecision(BaseModel):
    """Immutable governance decision (G-4). Supersede, never mutate."""
    model_config = ConfigDict(frozen=True)
    decisionId: str = Field(min_length=1)
    candidateId: str = Field(min_length=1)
    generation: int = Field(ge=0)
    verdict: DecisionVerdict
    fromState: LifecycleState
    toState: LifecycleState
    authorizesTransition: bool
    decidedBy: list = Field(min_length=1)  # memberIds / "executive"
    rationale: str
    supersedesDecisionId: Optional[str] = None
    evidenceRefs: list = Field(default_factory=list)
    decidedAt: str


class Certification(BaseModel):
    model_config = ConfigDict(frozen=True)
    certificationId: str = Field(min_length=1)
    candidateId: str = Field(min_length=1)
    certifiedBy: str = Field(min_length=1)
    criteria: str = Field(min_length=1)
    scope: Optional[str] = None
    validUntil: Optional[str] = None
    evidenceRefs: list = Field(default_factory=list)
    grantedAt: str
    revokedAt: Optional[str] = None
    revokedBy: Optional[str] = None


def is_legal_transition(from_state, to_state) -> bool:
    """True iff to_state is exactly the next lifecycle step after from_state."""
    fi = LIFECYCLE_ORDER.get(from_state)
    ti = LIFECYCLE_ORDER.get(to_state)
    if fi is None or ti is None:
        return False
    return ti == fi + 1


def required_gate_categories(from_state, to_state) -> tuple:
    return TRANSITION_GATES.get((from_state, to_state), ())


class GovernanceProjection(BaseModel):
    model_config = ConfigDict(frozen=True)
    council: CouncilComposition
    decisions: list = Field(default_factory=list)
    gates: list = Field(default_factory=list)