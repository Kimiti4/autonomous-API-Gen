"""
Models for production certification and Phase 22 closure.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CertificationDomain(str, Enum):
    ORGANIZATION_GOVERNANCE = "ORGANIZATION_GOVERNANCE"
    FEDERATION_GOVERNANCE = "FEDERATION_GOVERNANCE"
    REPUTATION_CERTIFICATION = "REPUTATION_CERTIFICATION"
    OVERSIGHT_CONTROLS = "OVERSIGHT_CONTROLS"
    PERMISSIONED_AUTONOMY = "PERMISSIONED_AUTONOMY"
    MEMORY_KNOWLEDGE_SYNC = "MEMORY_KNOWLEDGE_SYNC"
    OPERATIONAL_RESILIENCE = "OPERATIONAL_RESILIENCE"
    SECURITY_PRIVACY_AUDIT = "SECURITY_PRIVACY_AUDIT"
    OBSERVABILITY = "OBSERVABILITY"
    DOCUMENTATION_ADRS = "DOCUMENTATION_ADRS"
    TESTING_VERIFICATION = "TESTING_VERIFICATION"
    PRODUCTION_OPERATIONS = "PRODUCTION_OPERATIONS"


class EvidenceSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class CertificationStatus(str, Enum):
    CERTIFIED = "CERTIFIED"
    CONDITIONALLY_CERTIFIED = "CONDITIONALLY_CERTIFIED"
    NOT_CERTIFIED = "NOT_CERTIFIED"
    REVOKED = "REVOKED"


class CertificationEvidence(BaseModel):
    """Evidence supporting or blocking certification."""

    id: Optional[str] = None

    domain: CertificationDomain
    requirement: str

    satisfied: bool

    severity: EvidenceSeverity = EvidenceSeverity.INFO

    source: str = "unknown"

    details: str = ""

    override_allowed: bool = True

    collected_at: str


class DomainAssessment(BaseModel):
    """Assessment result for one certification domain."""

    domain: CertificationDomain

    passed: bool

    blocking_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)

    evidence_count: int = 0


class ProductionCertificationReport(BaseModel):
    """Production certification report."""

    id: str

    phase: str = "Phase 22"

    status: CertificationStatus

    domains: List[DomainAssessment] = Field(default_factory=list)

    blocking_count: int = 0
    warning_count: int = 0

    issued_by: str = "certification_engine"

    rationale: str = ""

    created_at: str
    expires_at: Optional[str] = None

    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None


class CertificationPolicy(BaseModel):
    """Policy controlling certification behavior."""

    certification_ttl_days: int = Field(default=90, ge=1)

    allow_conditional_on_warnings: bool = False

    require_all_domains: bool = True


class ManualEvidencePayload(BaseModel):
    """Manual evidence submission."""

    domain: CertificationDomain
    requirement: str

    satisfied: bool = True

    severity: EvidenceSeverity = EvidenceSeverity.INFO

    source: str = "manual"

    details: str = ""


class CertifyRequestPayload(BaseModel):
    """Request to run certification."""

    issued_by: str = "certification_api"


class RevokeCertificationPayload(BaseModel):
    """Request to revoke certification."""

    revoked_by: str
    reason: str = ""
