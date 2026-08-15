"""
Models for learning pipeline hardening and production certification.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils import utcnow


def new_id(prefix: str) -> str:
    """Generate a prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class CertificationStatus(str, Enum):
    CERTIFIED = "CERTIFIED"
    CONDITIONALLY_CERTIFIED = "CONDITIONALLY_CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class GateStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    MISSING = "MISSING"


class CertificationGateResult(BaseModel):
    """Result of one certification gate."""

    gate: str

    status: GateStatus

    reason: str = ""

    evidence_refs: List[str] = Field(default_factory=list)


class LearningPipelineCertificationPolicy(BaseModel):
    """Policy controlling learning pipeline certification."""

    min_signal_count: int = Field(default=1, ge=0)

    min_recent_signals: int = Field(default=1, ge=0)

    max_anomaly_rate: float = Field(default=0.60, ge=0.0, le=1.0)

    min_evidence_confidence: float = Field(default=0.50, ge=0.0, le=1.0)

    max_pending_approvals: int = Field(default=5, ge=0)

    require_kill_switch_disabled: bool = True

    require_observability_healthy: bool = True

    require_knowledge_sync: bool = False

    require_human_certification: bool = True

    allow_conditional_certification: bool = True

    certification_ttl_days: int = Field(default=90, ge=1)


class LearningPipelineCertificationReport(BaseModel):
    """Production certification report for the learning pipeline."""

    id: str = Field(default_factory=lambda: new_id("learning_certification"))

    scope: str = "learning_pipeline"

    status: CertificationStatus = CertificationStatus.NOT_CERTIFIED

    gates: List[CertificationGateResult] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None
