"""
Models for marketplace compliance, audit, and financial certification.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """Generate a prefixed identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def canonical_json(payload: Any) -> str:
    """Produce canonical JSON for deterministic hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(value: str) -> str:
    """Return SHA-256 hex digest for a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ComplianceDomain(str, Enum):
    FINANCIAL_RECONCILIATION = "FINANCIAL_RECONCILIATION"
    SETTLEMENT_GOVERNANCE = "SETTLEMENT_GOVERNANCE"
    REFUND_GOVERNANCE = "REFUND_GOVERNANCE"
    TAX_EVIDENCE = "TAX_EVIDENCE"
    FRAUD_CONTROLS = "FRAUD_CONTROLS"
    SLA_MONITORING = "SLA_MONITORING"
    AUDIT_TRAIL = "AUDIT_TRAIL"
    MARKETPLACE_CERTIFICATION = "MARKETPLACE_CERTIFICATION"
    LEARNING_CERTIFICATION = "LEARNING_CERTIFICATION"
    SECURITY_CONTROLS = "SECURITY_CONTROLS"


class ComplianceStatus(str, Enum):
    NOT_CERTIFIED = "NOT_CERTIFIED"
    CONDITIONALLY_CERTIFIED = "CONDITIONALLY_CERTIFIED"
    CERTIFIED = "CERTIFIED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class GateStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class MarketplaceComplianceEvidence(BaseModel):
    """Evidence required for marketplace compliance certification."""

    financial_reconciliation_refs: List[str] = Field(default_factory=list)
    settlement_governance_refs: List[str] = Field(default_factory=list)
    refund_governance_refs: List[str] = Field(default_factory=list)
    tax_evidence_refs: List[str] = Field(default_factory=list)
    fraud_controls_refs: List[str] = Field(default_factory=list)
    sla_monitoring_refs: List[str] = Field(default_factory=list)
    audit_trail_refs: List[str] = Field(default_factory=list)
    marketplace_certification_refs: List[str] = Field(default_factory=list)
    learning_certification_refs: List[str] = Field(default_factory=list)
    security_controls_refs: List[str] = Field(default_factory=list)


class ComplianceGateResult(BaseModel):
    """Result of one compliance gate."""

    domain: ComplianceDomain

    status: GateStatus

    reason: str = ""

    evidence_refs: List[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    """Marketplace compliance certification report."""

    id: str = Field(default_factory=lambda: new_id("marketplace_compliance"))

    scope: str = "marketplace"

    status: ComplianceStatus = ComplianceStatus.NOT_CERTIFIED

    gates: List[ComplianceGateResult] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None


class AuditBundle(BaseModel):
    """Audit bundle containing hashed audit records."""

    id: str = Field(default_factory=lambda: new_id("audit_bundle"))

    scope: str = "marketplace"

    records: List[Dict[str, Any]] = Field(default_factory=list)

    bundle_hash: str

    created_at: datetime = Field(default_factory=utcnow)
