"""
Models for Phase 24 closure certification.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Generate a prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class ClosureDomain(str, Enum):
    PRODUCT_FACTORY_CORE = "PRODUCT_FACTORY_CORE"
    MONETIZATION_OPS = "MONETIZATION_OPS"
    MARKETPLACE_FOUNDATION = "MARKETPLACE_FOUNDATION"
    PRODUCT_CERTIFICATION_PUBLISHING = "PRODUCT_CERTIFICATION_PUBLISHING"
    MARKETPLACE_DESIGN_ECONOMICS = "MARKETPLACE_DESIGN_ECONOMICS"
    FINANCIAL_HARDENING = "FINANCIAL_HARDENING"
    RECONCILIATION_SETTLEMENT = "RECONCILIATION_SETTLEMENT"
    MARKETPLACE_COMPLIANCE = "MARKETPLACE_COMPLIANCE"
    LEARNING_CERTIFICATION = "LEARNING_CERTIFICATION"
    GOVERNANCE_INTEGRATION = "GOVERNANCE_INTEGRATION"
    OBSERVABILITY = "OBSERVABILITY"
    DOCUMENTATION = "DOCUMENTATION"
    TEST_SUITE = "TEST_SUITE"


class ClosureStatus(str, Enum):
    NOT_CERTIFIED = "NOT_CERTIFIED"
    CONDITIONALLY_CERTIFIED = "CONDITIONALLY_CERTIFIED"
    CERTIFIED = "CERTIFIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class GateStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class Phase24Evidence(BaseModel):
    """Evidence required to close Phase 24."""

    product_factory_core_refs: List[str] = Field(default_factory=list)
    monetization_ops_refs: List[str] = Field(default_factory=list)
    marketplace_foundation_refs: List[str] = Field(default_factory=list)
    product_certification_publishing_refs: List[str] = Field(default_factory=list)
    marketplace_design_economics_refs: List[str] = Field(default_factory=list)
    financial_hardening_refs: List[str] = Field(default_factory=list)
    reconciliation_settlement_refs: List[str] = Field(default_factory=list)
    marketplace_compliance_refs: List[str] = Field(default_factory=list)
    learning_certification_refs: List[str] = Field(default_factory=list)
    governance_integration_refs: List[str] = Field(default_factory=list)
    observability_refs: List[str] = Field(default_factory=list)
    documentation_refs: List[str] = Field(default_factory=list)
    test_suite_refs: List[str] = Field(default_factory=list)


class ClosureGateResult(BaseModel):
    """Result of one Phase 24 closure gate."""

    domain: ClosureDomain

    status: GateStatus

    reason: str = ""

    evidence_refs: List[str] = Field(default_factory=list)


class Phase24ClosureReport(BaseModel):
    """Phase 24 closure certification report."""

    id: str = Field(default_factory=lambda: new_id("phase24_closure"))

    phase: str = "Phase 24"

    status: ClosureStatus = ClosureStatus.NOT_CERTIFIED

    gates: List[ClosureGateResult] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None
