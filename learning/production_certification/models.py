"""
Models for Production Learning Certification.
"""

from __future__ import annotations

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


class ProductionLearningDomain(str, Enum):
    LEARNING_PIPELINE_CERTIFICATION = "LEARNING_PIPELINE_CERTIFICATION"
    TELEMETRY_ADAPTERS = "TELEMETRY_ADAPTERS"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    KNOWLEDGE_SYNC = "KNOWLEDGE_SYNC"
    EVOLUTION_FEEDBACK = "EVOLUTION_FEEDBACK"
    LEARNING_GOVERNANCE = "LEARNING_GOVERNANCE"
    OBSERVABILITY = "OBSERVABILITY"

    MARKETPLACE_LEARNING = "MARKETPLACE_LEARNING"
    FRAUD_LEARNING = "FRAUD_LEARNING"
    PRICING_LEARNING = "PRICING_LEARNING"
    CONVERSION_LEARNING = "CONVERSION_LEARNING"
    REFUND_SUPPORT_LEARNING = "REFUND_SUPPORT_LEARNING"
    REVENUE_OPS_LEARNING = "REVENUE_OPS_LEARNING"
    MARKETPLACE_FITNESS = "MARKETPLACE_FITNESS"

    PRODUCTION_OPERATIONS = "PRODUCTION_OPERATIONS"


class CertificationGateResult(BaseModel):
    """Result of one production learning certification gate."""

    domain: ProductionLearningDomain

    status: GateStatus

    reason: str = ""

    evidence_refs: List[str] = Field(default_factory=list)


class OperationalReadinessEvidence(BaseModel):
    """Evidence required for production learning certification."""

    slo_definitions: List[str] = Field(default_factory=list)

    runbooks: List[str] = Field(default_factory=list)

    incident_response_plans: List[str] = Field(default_factory=list)

    backup_restore_evidence: List[str] = Field(default_factory=list)

    observability_evidence: List[str] = Field(default_factory=list)

    dashboard_refs: List[str] = Field(default_factory=list)

    marketplace_metrics_refs: List[str] = Field(default_factory=list)

    fraud_learning_evidence: List[str] = Field(default_factory=list)

    pricing_learning_evidence: List[str] = Field(default_factory=list)

    conversion_learning_evidence: List[str] = Field(default_factory=list)

    refund_support_learning_evidence: List[str] = Field(default_factory=list)

    revenue_ops_learning_evidence: List[str] = Field(default_factory=list)


class ProductionLearningCertificationPolicy(BaseModel):
    """Policy controlling production learning certification."""

    require_learning_pipeline_certification: bool = True

    require_telemetry_adapters: bool = True
    require_anomaly_detection: bool = True
    require_knowledge_sync: bool = True
    require_evolution_feedback: bool = True
    require_learning_governance: bool = True
    require_observability: bool = True

    require_marketplace_learning: bool = True
    require_fraud_learning: bool = True
    require_pricing_learning: bool = True
    require_conversion_learning: bool = True
    require_refund_support_learning: bool = True
    require_revenue_ops_learning: bool = True
    require_marketplace_fitness: bool = True

    require_production_readiness: bool = True

    require_slos: bool = True
    require_runbooks: bool = True
    require_incident_response: bool = True
    require_backup_restore: bool = True
    require_observability_evidence: bool = True
    require_dashboard_evidence: bool = True
    require_marketplace_metrics: bool = True

    require_human_certification: bool = True

    allow_conditional_certification: bool = True

    certification_ttl_days: int = Field(default=90, ge=1)


class ProductionLearningCertificationReport(BaseModel):
    """Production learning certification report."""

    id: str = Field(default_factory=lambda: new_id("production_learning_certification"))

    scope: str = "production_learning"

    status: CertificationStatus = CertificationStatus.NOT_CERTIFIED

    gates: List[CertificationGateResult] = Field(default_factory=list)

    reasons: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    prerequisite_26_7_report_id: Optional[str] = None

    certified_by: str = "system"

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None

    revoked_at: Optional[datetime] = None

    revocation_reason: Optional[str] = None
