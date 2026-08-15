"""
Compiler SDK models.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..models import ValidationIssue, utcnow


class ContractTestResult(BaseModel):
    """Result of one backend contract test."""

    name: str
    passed: bool
    message: str = ""


class DeterminismResult(BaseModel):
    """Result of backend determinism verification."""

    passed: bool
    artifact_count_match: bool
    content_hashes_match: bool
    message: str = ""


class CertificationStatus(str, Enum):
    """Backend certification status."""

    UNCERTIFIED = "UNCERTIFIED"
    PROVISIONAL = "PROVISIONAL"
    CERTIFIED = "CERTIFIED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


class BackendCertificationRequest(BaseModel):
    """Request to certify a backend."""

    backend_id: str
    backend_version: Optional[str] = None

    test_isr: Optional[dict[str, Any]] = None

    environment: str = "certification"


class RevokeCertificationRequest(BaseModel):
    """Request to revoke backend certification."""

    version: Optional[str] = None
    reason: str = ""


class BackendCertificationReport(BaseModel):
    """Certification report for a backend."""

    backend_id: str
    backend_version: str

    status: CertificationStatus

    contract_tests: list[ContractTestResult] = Field(default_factory=list)
    contract_tests_passed: bool = False

    determinism: DeterminismResult
    determinism_passed: bool = False

    validation_passed: bool = False

    issues: list[ValidationIssue] = Field(default_factory=list)

    certified_at: str
    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None


class CertificationEvent(BaseModel):
    """Audit event for backend certification lifecycle."""

    event_type: str
    backend_id: str
    backend_version: str
    timestamp: str
    details: dict[str, Any] = Field(default_factory=dict)