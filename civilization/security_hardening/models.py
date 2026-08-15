"""
Models for security, privacy, and audit hardening.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PrincipalType(str, Enum):
    HUMAN = "HUMAN"
    AGENT = "AGENT"
    ORGANIZATION = "ORGANIZATION"
    SERVICE = "SERVICE"
    FEDERATION = "FEDERATION"


class Principal(BaseModel):
    """Authenticated actor requesting an action."""

    id: str
    type: PrincipalType = PrincipalType.AGENT

    roles: List[str] = Field(default_factory=list)

    attributes: Dict[str, Any] = Field(default_factory=dict)

    authenticated: bool = False


class AccessRequest(BaseModel):
    """Request to authorize an action."""

    principal: Principal

    action: str

    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    high_impact: bool = False

    context: Dict[str, Any] = Field(default_factory=dict)


class AccessDecision(BaseModel):
    """Decision returned by the security engine."""

    allowed: bool

    reason: str

    required_human_approval: bool = False

    alerts: List[str] = Field(default_factory=list)

    decision_id: Optional[str] = None

    timestamp: str


class SecurityClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class SecretFinding(BaseModel):
    """Secret or sensitive data finding."""

    path: str

    pattern_name: str

    severity: str

    is_pii: bool = False


class RedactionReport(BaseModel):
    """Report produced by redaction."""

    redacted: bool

    classification: SecurityClassification

    findings: List[SecretFinding] = Field(default_factory=list)

    redacted_payload: Any = None


class SecuredAuditEvent(BaseModel):
    """Tamper-evident audit event."""

    id: str

    occurred_at: str

    actor_id: str
    actor_type: str

    action: str

    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    decision: str
    reason: str = ""

    payload: Dict[str, Any] = Field(default_factory=dict)

    previous_hash: str
    event_hash: str


class SecurityAlert(BaseModel):
    """Security alert."""

    id: str

    alert_type: str

    severity: str

    principal_id: Optional[str] = None

    action: Optional[str] = None

    message: str

    created_at: str

    status: str = "OPEN"


class SecurityHardeningPolicy(BaseModel):
    """Policy controlling security hardening behavior."""

    require_authentication: bool = True

    allow_unauthenticated_read: bool = False

    high_impact_requires_approval: bool = True

    redact_secrets: bool = True

    classify_payloads: bool = True

    audit_all_access: bool = True

    repeated_denial_threshold: int = Field(default=3, ge=1)

    alert_on_secret_detection: bool = True

    alert_on_privilege_escalation: bool = True

    alert_on_unauthenticated_high_impact: bool = True
