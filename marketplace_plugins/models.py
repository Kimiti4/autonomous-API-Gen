"""
Models for the Marketplace & Plugin Ecosystem.

These models represent the primary Phase 27 ISR extensions:

- PluginManifestISR
- ExtensionCapabilityISR
- DependencyGraphISR
- SandboxPolicyISR
- MarketplaceListingISR
- CompatibilityReportISR
- PublisherIdentityISR
- RevocationRecordISR
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
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class PluginCapability(str, Enum):
    """Capabilities that an extension may provide."""

    COMPILER_BACKEND = "COMPILER_BACKEND"
    EVOLUTION_MUTATOR = "EVOLUTION_MUTATOR"
    TELEMETRY_ADAPTER = "TELEMETRY_ADAPTER"
    KNOWLEDGE_INGESTOR = "KNOWLEDGE_INGESTOR"
    UI_COMPONENT = "UI_COMPONENT"
    VERIFICATION_ENGINE = "VERIFICATION_ENGINE"
    INFRASTRUCTURE_TEMPLATE = "INFRASTRUCTURE_TEMPLATE"
    DOMAIN_PACK = "DOMAIN_PACK"


class PluginStatus(str, Enum):
    """Lifecycle status for a marketplace listing."""

    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    INSTALLED = "INSTALLED"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"


class PublisherStatus(str, Enum):
    """Lifecycle status for a publisher identity."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class SandboxPolicyISR(BaseModel):
    """Sandbox policy for plugin execution."""

    allow_isr_mutation: bool = False
    allow_network_access: bool = False
    allow_file_system_access: bool = False

    max_execution_time_ms: int = Field(default=5000, ge=100)
    max_memory_mb: int = Field(default=256, ge=16)


class ExtensionCapabilityISR(BaseModel):
    """Declared capability of an extension."""

    capability: PluginCapability

    description: str = ""

    risk_level: str = "LOW"


class DependencyGraphISR(BaseModel):
    """Dependency graph for a plugin."""

    plugin_id: str

    dependencies: Dict[str, str] = Field(default_factory=dict)


class PluginManifestISR(BaseModel):
    """Signed manifest describing a plugin."""

    id: str = Field(default_factory=lambda: new_id("plugin"))
    name: str
    version: str
    publisher_id: str

    capabilities: List[PluginCapability] = Field(default_factory=list)

    dependencies: Dict[str, str] = Field(default_factory=dict)

    required_permissions: List[str] = Field(default_factory=list)

    sandbox_policy: SandboxPolicyISR = Field(default_factory=SandboxPolicyISR)

    signature: str
    payload_hash: str

    created_at: datetime = Field(default_factory=utcnow)


class PublisherIdentityISR(BaseModel):
    """Publisher identity record."""

    id: str
    name: str
    public_key_ref: str
    status: PublisherStatus = PublisherStatus.ACTIVE
    created_at: datetime = Field(default_factory=utcnow)


class MarketplaceListingISR(BaseModel):
    """Marketplace listing for a plugin manifest."""

    id: str = Field(default_factory=lambda: new_id("listing"))
    manifest: PluginManifestISR

    status: PluginStatus = PluginStatus.PENDING_REVIEW

    approval_ref: Optional[str] = None
    audit_trail: List[str] = Field(default_factory=list)

    installed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None


class CompatibilityReportISR(BaseModel):
    """Compatibility report for a plugin."""

    plugin_id: str
    is_compatible: bool
    missing_dependencies: List[str] = Field(default_factory=list)
    version_conflicts: List[str] = Field(default_factory=list)
    capability_conflicts: List[str] = Field(default_factory=list)
    reason: str = ""


class RevocationRecordISR(BaseModel):
    """Immutable revocation record."""

    id: str = Field(default_factory=lambda: new_id("revocation"))
    plugin_id: str
    plugin_version: str
    reason: str
    revoked_by: str
    revoked_at: datetime = Field(default_factory=utcnow)
    affected_dependents: List[str] = Field(default_factory=list)
