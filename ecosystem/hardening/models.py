"""
Models for ecosystem hardening.
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


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DependencyStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OPEN = "OPEN"


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


class EcosystemHardeningPolicy(BaseModel):
    """Policy controlling ecosystem hardening behavior."""

    min_partner_trust: float = Field(default=0.60, ge=0.0, le=1.0)

    max_revenue_share_pct: float = Field(default=50.0, ge=0.0, le=100.0)

    require_treaty_governance: bool = True

    require_partner_evidence: bool = True

    max_sla_breaches_before_escalation: int = Field(default=3, ge=1)

    auto_suspend_contract_on_sla_escalation: bool = False

    circuit_failure_threshold: int = Field(default=3, ge=1)

    require_human_compliance_certification: bool = True

    allow_degraded_routing: bool = False


class TreatyRiskAssessment(BaseModel):
    """Risk assessment for a federation treaty."""

    treaty_id: str

    risk_level: RiskLevel

    requires_governance: bool = False

    reasons: List[str] = Field(default_factory=list)


class PartnerTrustAssessment(BaseModel):
    """Trust assessment for an ecosystem partner."""

    partner_id: str

    trust_score: float

    evidence_count: int = 0

    status: str

    risk_level: RiskLevel

    recommended_action: str

    reasons: List[str] = Field(default_factory=list)


class RoutingGuardrailDecision(BaseModel):
    """Guardrail decision for cross-marketplace routing."""

    allowed: bool

    reasons: List[str] = Field(default_factory=list)

    base_decision: Optional[Dict[str, Any]] = None


class SLAEnforcementReport(BaseModel):
    """SLA enforcement report."""

    contract_id: str

    metric: str

    value: float

    breach_detected: bool = False

    total_breaches: int = 0

    escalated: bool = False

    recommended_action: str = "MONITOR"


class EcosystemComplianceEvidence(BaseModel):
    """Evidence required for ecosystem compliance certification."""

    governance_refs: List[str] = Field(default_factory=list)
    treaty_risk_refs: List[str] = Field(default_factory=list)
    partner_trust_refs: List[str] = Field(default_factory=list)
    sla_refs: List[str] = Field(default_factory=list)
    financial_refs: List[str] = Field(default_factory=list)
    security_refs: List[str] = Field(default_factory=list)
    learning_refs: List[str] = Field(default_factory=list)
    audit_refs: List[str] = Field(default_factory=list)


class EcosystemComplianceReport(BaseModel):
    """Ecosystem compliance certification report."""

    id: str = Field(default_factory=lambda: new_id("ecosystem_compliance"))

    scope: str = "ecosystem"

    status: ComplianceStatus = ComplianceStatus.NOT_CERTIFIED

    gates: List[Dict[str, Any]] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None


class EcosystemAuditBundle(BaseModel):
    """Audit bundle for ecosystem state."""

    id: str = Field(default_factory=lambda: new_id("ecosystem_audit_bundle"))

    scope: str = "ecosystem"

    records: List[Dict[str, Any]] = Field(default_factory=list)

    bundle_hash: str

    created_at: datetime = Field(default_factory=utcnow)


class EcosystemObservabilityReport(BaseModel):
    """Ecosystem observability report."""

    active_treaties: int = 0
    suspended_treaties: int = 0

    active_partners: int = 0
    low_trust_partners: int = 0

    active_contracts: int = 0
    sla_breaches: int = 0

    alerts: List[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=utcnow)


class DependencyHealth(BaseModel):
    """Health state for an ecosystem dependency."""

    dependency: str

    status: DependencyStatus

    failure_count: int = 0


class EcosystemResilienceReport(BaseModel):
    """Ecosystem resilience report."""

    dependencies: List[DependencyHealth] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=utcnow)
