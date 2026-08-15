"""
Models for autonomous product certification and publishing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Generate a prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class CertificationGate(str, Enum):
    TESTS = "TESTS"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    DOCUMENTATION = "DOCUMENTATION"
    OBSERVABILITY = "OBSERVABILITY"
    DEPLOYMENT = "DEPLOYMENT"
    ROLLBACK = "ROLLBACK"
    LICENSING = "LICENSING"
    MARKETPLACE_POLICY = "MARKETPLACE_POLICY"
    LEARNING_CERTIFICATION = "LEARNING_CERTIFICATION"


class CertificationStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    CERTIFIED = "CERTIFIED"
    CONDITIONALLY_CERTIFIED = "CONDITIONALLY_CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class PublicationStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STAGED = "STAGED"
    PUBLISHED = "PUBLISHED"
    GUARDRAIL_TRIGGERED = "GUARDRAIL_TRIGGERED"
    DELISTED = "DELISTED"
    ROLLED_BACK = "ROLLED_BACK"


class GateResult(BaseModel):
    """Result of one certification gate."""

    gate: CertificationGate

    passed: bool

    severity: str = "INFO"

    reason: str = ""

    evidence_refs: List[str] = Field(default_factory=list)

    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ProductCertificationPolicy(BaseModel):
    """Policy controlling product certification."""

    require_tests: bool = True
    require_security: bool = True
    require_performance: bool = True
    require_documentation: bool = True
    require_observability: bool = True
    require_deployment: bool = True
    require_rollback: bool = True
    require_licensing: bool = True
    require_marketplace_policy: bool = True
    require_learning_pipeline_certification: bool = True

    require_human_first_publication: bool = True

    allow_autonomous_publishing: bool = False

    allow_conditional_certification: bool = True

    max_critical_security_findings: int = Field(default=0, ge=0)

    min_test_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)

    min_performance_score: float = Field(default=0.7, ge=0.0, le=1.0)

    certification_ttl_days: int = Field(default=90, ge=1)


class ProductCertificationReport(BaseModel):
    """Certification report for a product version."""

    id: str = Field(default_factory=lambda: new_id("product_certification"))

    product_id: str

    product_version: str

    status: CertificationStatus = CertificationStatus.DRAFT

    gates: List[GateResult] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None


class PublicationGuardrails(BaseModel):
    """Guardrails for published products."""

    max_refund_rate: float = Field(default=0.15, ge=0.0, le=1.0)

    max_fraud_score: float = Field(default=0.70, ge=0.0, le=1.0)

    min_conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    max_support_ticket_increase_pct: float = Field(default=25.0, ge=0.0)

    auto_delist_on_guardrail: bool = True


class PublicationRequest(BaseModel):
    """Request to publish a product to a marketplace."""

    id: str = Field(default_factory=lambda: new_id("publication_request"))

    product_id: str

    product_version: str

    marketplace_id: str

    publisher_id: str

    pricing_plan_ref: Optional[str] = None

    certification_report_id: str

    status: PublicationStatus = PublicationStatus.DRAFT

    approval_ref: Optional[str] = None

    guardrails: PublicationGuardrails = Field(
        default_factory=PublicationGuardrails
    )

    marketplace_listing_id: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)

    approved_at: Optional[datetime] = None

    published_at: Optional[datetime] = None

    delisted_at: Optional[datetime] = None

    delisting_reason: Optional[str] = None
