"""
Models for learning governance and safety controls.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils import utcnow


class LearningGovernancePolicy(BaseModel):
    """Policy controlling learning governance and safety."""

    min_quality_score: float = Field(default=0.60, ge=0.0, le=1.0)

    min_confidence: float = Field(default=0.50, ge=0.0, le=1.0)

    min_corroboration: float = Field(default=0.25, ge=0.0, le=1.0)

    max_evidence_age_hours: float = Field(default=72.0, ge=1.0)

    max_insights_per_sync: int = Field(default=50, ge=1)

    max_submissions_per_hour: int = Field(default=10, ge=1)

    critical_security_requires_approval: bool = True

    high_pressure_requires_approval: bool = True

    high_pressure_threshold: float = Field(default=0.50, ge=0.0, le=1.0)

    auto_submit_after_approval: bool = True


class EvidenceQualityReport(BaseModel):
    """Evidence quality report for a learning sync."""

    bundle_id: str

    evidence_count: int = 0

    average_confidence: float = 0.0

    corroboration_score: float = 0.0

    recency_score: float = 0.0

    quality_score: float = 0.0

    poisoning_indicators: List[str] = Field(default_factory=list)

    passed: bool = False

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class SafetyReport(BaseModel):
    """Safety report for a learning sync."""

    bundle_id: str

    allowed: bool = False

    required_human_approval: bool = False

    blockers: List[str] = Field(default_factory=list)

    warnings: List[str] = Field(default_factory=list)

    kill_switch_active: bool = False

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class LearningApprovalRequest(BaseModel):
    """Approval request for governed learning sync."""

    id: str

    bundle_id: str

    scope: str

    status: str = "PENDING"

    requested_by: str = "system"

    decided_by: Optional[str] = None

    comments: str = ""

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())

    decided_at: Optional[str] = None


class KillSwitchState(BaseModel):
    """Learning kill-switch state."""

    enabled: bool = False

    reason: str = ""

    activated_by: Optional[str] = None

    activated_at: Optional[str] = None

    deactivated_by: Optional[str] = None

    deactivated_at: Optional[str] = None


class GovernanceSyncReport(BaseModel):
    """Report produced by a governed learning sync."""

    bundle_id: Optional[str] = None

    scope: str = "platform"

    status: str = "NO_ACTION"

    quality: Optional[EvidenceQualityReport] = None

    safety: Optional[SafetyReport] = None

    approval_id: Optional[str] = None

    submission_id: Optional[str] = None

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())
