"""
Models for the autonomous ecosystem and cross-marketplace federation.
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


class TreatyStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_GOVERNANCE = "PENDING_GOVERNANCE"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class PartnerStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BANNED = "BANNED"


class PartnerType(str, Enum):
    HUMAN_ORGANIZATION = "HUMAN_ORGANIZATION"
    AGENT = "AGENT"
    MARKETPLACE = "MARKETPLACE"
    VENDOR = "VENDOR"


class ContractStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class SLAOperator(str, Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"


class PenaltyStatus(str, Enum):
    PENDING_GOVERNANCE = "PENDING_GOVERNANCE"
    ENFORCED = "ENFORCED"
    DENIED = "DENIED"


class FederationTreaty(BaseModel):
    """Treaty between two marketplaces."""

    id: str = Field(default_factory=lambda: new_id("federation_treaty"))

    name: str

    source_marketplace_id: str
    target_marketplace_id: str

    revenue_share_pct: float = Field(default=0.0, ge=0.0, le=100.0)

    routing_policy: Dict[str, Any] = Field(default_factory=dict)

    status: TreatyStatus = TreatyStatus.DRAFT

    governance_ref: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)

    expires_at: Optional[datetime] = None


class PartnerOrganization(BaseModel):
    """Partner organization in the ecosystem."""

    id: str = Field(default_factory=lambda: new_id("partner"))

    name: str

    partner_type: PartnerType = PartnerType.VENDOR

    status: PartnerStatus = PartnerStatus.PENDING

    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)

    capabilities: List[str] = Field(default_factory=list)

    evidence_refs: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utcnow)

    governance_ref: Optional[str] = None


class B2BContract(BaseModel):
    """Contract between a partner and a marketplace."""

    id: str = Field(default_factory=lambda: new_id("b2b_contract"))

    partner_id: str

    marketplace_id: str

    contract_type: str

    terms: Dict[str, Any] = Field(default_factory=dict)

    status: ContractStatus = ContractStatus.ACTIVE

    created_at: datetime = Field(default_factory=utcnow)

    governance_ref: Optional[str] = None


class SLADefinition(BaseModel):
    """SLA definition attached to a contract."""

    metric: str

    threshold: float

    operator: SLAOperator

    window_minutes: int = Field(default=60, ge=1)


class SLABreach(BaseModel):
    """SLA breach event."""

    id: str = Field(default_factory=lambda: new_id("sla_breach"))

    contract_id: str

    metric: str

    observed_value: float

    threshold: float

    operator: SLAOperator

    detected_at: datetime = Field(default_factory=utcnow)


class PenaltyRecord(BaseModel):
    """A penalty enforcement outcome attached to an SLA breach."""

    id: str = Field(default_factory=lambda: new_id("penalty"))

    contract_id: str

    breach_id: str

    penalty_amount: float = 0.0

    status: PenaltyStatus = PenaltyStatus.PENDING_GOVERNANCE

    evidence_refs: List[str] = Field(default_factory=list)

    governance_ref: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)


class RoutingRequest(BaseModel):
    """Request to evaluate cross-marketplace routing."""

    source_marketplace_id: str

    product_id: str

    candidate_marketplace_ids: List[str] = Field(default_factory=list)

    partner_id: Optional[str] = None

    constraints: Dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    """Routing decision produced by the routing engine."""

    id: str = Field(default_factory=lambda: new_id("routing_decision"))

    source_marketplace_id: str

    product_id: str

    selected_marketplace_id: str

    score: float

    reasons: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utcnow)


class EcosystemSyncRecord(BaseModel):
    """Record synced into the ecosystem knowledge graph."""

    id: str = Field(default_factory=lambda: new_id("ecosystem_sync"))

    entity_type: str

    entity_id: str

    payload: Dict[str, Any] = Field(default_factory=dict)

    synced_at: datetime = Field(default_factory=utcnow)


class EcosystemReport(BaseModel):
    """Ecosystem operational report."""

    active_treaties: int = 0

    active_partners: int = 0

    active_contracts: int = 0

    sla_breaches: int = 0

    synced_records: int = 0

    generated_at: datetime = Field(default_factory=utcnow)
