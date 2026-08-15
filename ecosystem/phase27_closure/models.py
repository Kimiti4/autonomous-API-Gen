"""
Models for Phase 27 closure certification.
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
    ECOSYSTEM_CORE = "ECOSYSTEM_CORE"
    FEDERATION_TREATIES = "FEDERATION_TREATIES"
    PARTNER_IDENTITY_TRUST = "PARTNER_IDENTITY_TRUST"
    CROSS_MARKETPLACE_ROUTING = "CROSS_MARKETPLACE_ROUTING"
    B2B_CONTRACT_SLA = "B2B_CONTRACT_SLA"

    ECOSYSTEM_HARDENING = "ECOSYSTEM_HARDENING"
    TREATY_RISK = "TREATY_RISK"
    PARTNER_TRUST_HARDENING = "PARTNER_TRUST_HARDENING"
    GUARDED_ROUTING = "GUARDED_ROUTING"
    SLA_ENFORCEMENT = "SLA_ENFORCEMENT"

    ECOSYSTEM_COMPLIANCE = "ECOSYSTEM_COMPLIANCE"
    AUDIT_BUNDLE = "AUDIT_BUNDLE"
    OBSERVABILITY = "OBSERVABILITY"
    RESILIENCE = "RESILIENCE"

    GOVERNANCE_INTEGRATION = "GOVERNANCE_INTEGRATION"
    LEARNING_CERTIFICATION = "LEARNING_CERTIFICATION"
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


class Phase27Evidence(BaseModel):
    """Evidence required to close Phase 27."""

    ecosystem_core_refs: List[str] = Field(default_factory=list)
    federation_treaty_refs: List[str] = Field(default_factory=list)
    partner_identity_trust_refs: List[str] = Field(default_factory=list)
    cross_marketplace_routing_refs: List[str] = Field(default_factory=list)
    b2b_contract_sla_refs: List[str] = Field(default_factory=list)

    ecosystem_hardening_refs: List[str] = Field(default_factory=list)
    treaty_risk_refs: List[str] = Field(default_factory=list)
    partner_trust_hardening_refs: List[str] = Field(default_factory=list)
    guarded_routing_refs: List[str] = Field(default_factory=list)
    sla_enforcement_refs: List[str] = Field(default_factory=list)

    ecosystem_compliance_refs: List[str] = Field(default_factory=list)
    audit_bundle_refs: List[str] = Field(default_factory=list)
    observability_refs: List[str] = Field(default_factory=list)
    resilience_refs: List[str] = Field(default_factory=list)

    governance_integration_refs: List[str] = Field(default_factory=list)
    learning_certification_refs: List[str] = Field(default_factory=list)
    documentation_refs: List[str] = Field(default_factory=list)
    test_suite_refs: List[str] = Field(default_factory=list)


class ClosureGateResult(BaseModel):
    """Result of one Phase 27 closure gate."""

    domain: ClosureDomain

    status: GateStatus

    reason: str = ""

    evidence_refs: List[str] = Field(default_factory=list)


class Phase27ClosureReport(BaseModel):
    """Phase 27 closure certification report."""

    id: str = Field(default_factory=lambda: new_id("phase27_closure"))

    phase: str = "Phase 27"

    status: ClosureStatus = ClosureStatus.NOT_CERTIFIED

    gates: List[ClosureGateResult] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None
