"""
Compiler governance models.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GovernanceEvaluationRequest(BaseModel):
    """Request sent to a governance authority."""

    subject_type: str
    subject_id: str
    action: str

    actor: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)


class GovernanceDecision(BaseModel):
    """Decision returned by a governance authority."""

    decision: Literal[
        "ALLOW",
        "DENY",
        "REQUIRE_APPROVAL",
        "REQUIRE_EVIDENCE",
        "ALLOW_WITH_CONSTRAINTS",
    ]

    reason: str = ""

    constraints: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)


class CompilationGateDecision(BaseModel):
    """Decision produced by the compiler production gate."""

    allowed: bool
    reason: str

    environment: str
    backend_id: str
    backend_version: str

    certification_status: Optional[str] = None
    governance_decision: Optional[GovernanceDecision] = None

    constraints: list[dict[str, Any]] = Field(default_factory=list)


class CompilerGovernancePolicy(BaseModel):
    """Policy controlling compiler production gating."""

    production_environments: list[str] = Field(
        default_factory=lambda: ["production"]
    )

    certified_required_environments: list[str] = Field(
        default_factory=lambda: ["production", "staging"]
    )

    allow_uncertified_development: bool = True
    allow_provisional_in_non_production: bool = True

    require_governance_for_production: bool = True
    fail_closed_on_governance_unavailable: bool = True

    max_certification_age_days: Optional[int] = 90
