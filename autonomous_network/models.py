"""
Models for the Autonomous Software Engineering Network.
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
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _canonical_default(obj: Any) -> str:
    """JSON default hook that renders ``datetime``/``Enum`` canonically.

    ``datetime`` is rendered via ``isoformat`` so the representation
    round-trips the ISO-8601 timestamp strings produced by :func:`utcnow`,
    keeping hash-chained audit events verifiable under pydantic v2
    ``str``->``datetime`` coercion.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(
        f"Object of type {type(obj).__name__} is not JSON serializable"
    )


def canonical_json(payload: Dict[str, Any]) -> str:
    """Produce canonical JSON for deterministic hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_canonical_default,
    )


def sha256_hex(value: str) -> str:
    """Return SHA-256 hex digest for a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class OrganizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class ContractStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    TERMINATED = "TERMINATED"


class PipelineStageName(str, Enum):
    REQUIREMENT_ANALYSIS = "REQUIREMENT_ANALYSIS"
    ISR_CONSTRUCTION = "ISR_CONSTRUCTION"
    EVOLUTION = "EVOLUTION"
    VERIFICATION = "VERIFICATION"
    COMPILATION = "COMPILATION"
    DEPLOYMENT = "DEPLOYMENT"
    MONITORING = "MONITORING"
    LEARNING = "LEARNING"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class OrganizationRegistration(BaseModel):
    """Registered autonomous engineering organization."""

    org_id: str
    name: str

    capabilities: List[str] = Field(default_factory=list)

    policy_version: str
    public_key_ref: str

    status: OrganizationStatus = OrganizationStatus.ACTIVE

    attested: bool = False

    registered_at: datetime = Field(default_factory=utcnow)


class CrossOrganizationContract(BaseModel):
    """Contract governing collaboration between organizations."""

    contract_id: str

    parties: List[str] = Field(default_factory=list)

    objective: str

    obligations: List[str] = Field(default_factory=list)

    policy_version: str

    status: ContractStatus = ContractStatus.DRAFT

    approved_by: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)
    activated_at: Optional[datetime] = None


class StageResult(BaseModel):
    """Result returned by a pipeline stage adapter."""

    stage: PipelineStageName

    status: StageStatus

    data: Dict[str, Any] = Field(default_factory=dict)

    evidence_refs: List[str] = Field(default_factory=list)

    metrics: Dict[str, Any] = Field(default_factory=dict)

    error: Optional[str] = None


class StageRun(BaseModel):
    """Runtime state of one pipeline stage."""

    stage: PipelineStageName

    status: StageStatus = StageStatus.PENDING

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    evidence_refs: List[str] = Field(default_factory=list)

    metrics: Dict[str, Any] = Field(default_factory=dict)

    error: Optional[str] = None


class PipelineRun(BaseModel):
    """End-to-end pipeline run."""

    run_id: str

    contract_id: str

    objective: str

    requirements: Dict[str, Any] = Field(default_factory=dict)

    status: PipelineStatus = PipelineStatus.PENDING

    stages: List[StageRun] = Field(default_factory=list)

    artifacts: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class NetworkAlert(BaseModel):
    """Network-level operational alert."""

    alert_id: str = Field(default_factory=lambda: new_id("alert"))

    severity: str

    message: str

    created_at: datetime = Field(default_factory=utcnow)


class NetworkEvent(BaseModel):
    """Hash-chained network audit event."""

    event_id: str

    event_type: str

    org_id: Optional[str] = None
    run_id: Optional[str] = None

    payload: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utcnow)

    previous_hash: str
    event_hash: str


class GlobalMonitoringSnapshot(BaseModel):
    """Global monitoring snapshot."""

    active_orgs: int = 0
    suspended_orgs: int = 0

    active_contracts: int = 0

    pipeline_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0

    alerts_count: int = 0

    generated_at: datetime = Field(default_factory=utcnow)


class MemoryRecord(BaseModel):
    """Global engineering memory record."""

    record_id: str = Field(default_factory=lambda: new_id("memory"))

    entity_type: str
    entity_id: str

    payload: Dict[str, Any] = Field(default_factory=dict)

    evidence_refs: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utcnow)
