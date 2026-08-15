"""
Models for the Distributed Evolution Cloud.
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


def canonical_json(payload: Dict[str, Any]) -> str:
    """Produce canonical JSON for deterministic hashing.

    ``datetime`` values (and other non-JSON-native objects) are rendered
    via ``isoformat`` so the canonical representation round-trips the
    ISO-8601 strings produced by :func:`utcnow`.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_canonical_default,
    )


def _canonical_default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(
        f"Object of type {type(obj).__name__} is not JSON serializable"
    )


def sha256_hex(value: str) -> str:
    """Return SHA-256 hex digest for a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class JobKind(str, Enum):
    EVOLUTION = "EVOLUTION"
    SIMULATION = "SIMULATION"
    COMPILATION = "COMPILATION"
    VERIFICATION = "VERIFICATION"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CampaignStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"


class ResourceRequirements(BaseModel):
    """Resource requirements for a distributed job."""

    cpu: int = Field(default=1, ge=1)
    memory_mb: int = Field(default=512, ge=64)

    regions: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)


class ComputeNodeISR(BaseModel):
    """Compute node registration record."""

    node_id: str
    region: str

    capabilities: List[str] = Field(default_factory=list)

    cpu_capacity: int = Field(default=2, ge=1)
    memory_mb_capacity: int = Field(default=1024, ge=128)

    status: NodeStatus = NodeStatus.ACTIVE

    attested: bool = False

    policy_version: str
    public_key_ref: str

    last_heartbeat: datetime = Field(default_factory=utcnow)


class ComputeClusterISR(BaseModel):
    """Compute cluster record."""

    cluster_id: str = Field(default_factory=lambda: new_id("cluster"))

    name: str = "distributed-evolution-cloud"

    policy_version: str

    nodes: List[str] = Field(default_factory=list)

    regions: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utcnow)


class ResourceAllocationISR(BaseModel):
    """Resource allocation for a job."""

    allocation_id: str = Field(default_factory=lambda: new_id("allocation"))

    job_id: str
    node_id: str

    cpu: int
    memory_mb: int

    status: str = "ALLOCATED"

    created_at: datetime = Field(default_factory=utcnow)
    released_at: Optional[datetime] = None


class DistributedJobISR(BaseModel):
    """Distributed job record."""

    job_id: str

    campaign_id: str

    kind: JobKind

    name: str

    requirements: ResourceRequirements = Field(
        default_factory=ResourceRequirements
    )

    input_artifact_hashes: List[str] = Field(default_factory=list)

    output_artifact_specs: List[Dict[str, Any]] = Field(default_factory=list)

    policy_version: str

    idempotency_key: str

    attempt: int = 0
    max_attempts: int = Field(default=3, ge=1)

    status: JobStatus = JobStatus.PENDING

    node_id: Optional[str] = None

    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SimulationCampaignISR(BaseModel):
    """Distributed evolution or simulation campaign."""

    campaign_id: str

    name: str

    objective: str

    policy_version: str

    status: CampaignStatus = CampaignStatus.PENDING

    candidate_count: int = Field(default=1, ge=1)

    target_backends: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utcnow)


class DistributedCompilationPlanISR(BaseModel):
    """Distributed compilation plan."""

    plan_id: str = Field(default_factory=lambda: new_id("compilation_plan"))

    campaign_id: str

    isr_hash: str

    target_backends: List[str] = Field(default_factory=list)

    policy_version: str

    created_at: datetime = Field(default_factory=utcnow)


class ArtifactLocationISR(BaseModel):
    """Location of an artifact in the distributed artifact repository."""

    location_id: str = Field(default_factory=lambda: new_id("artifact_location"))

    artifact_hash: str

    node_id: str
    region: str

    uri: str

    created_at: datetime = Field(default_factory=utcnow)


class ArtifactRecord(BaseModel):
    """Artifact metadata record."""

    artifact_id: str

    content_hash: str

    size_bytes: int = 0

    produced_by_job: Optional[str] = None

    locations: List[ArtifactLocationISR] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=utcnow)


class FederationAgreementISR(BaseModel):
    """Federation agreement between distributed clusters."""

    agreement_id: str = Field(default_factory=lambda: new_id("federation"))

    cluster_ids: List[str] = Field(default_factory=list)

    regions: List[str] = Field(default_factory=list)

    policy_version: str

    mutual_verification: bool = True

    created_at: datetime = Field(default_factory=utcnow)


class FaultRecoveryPlanISR(BaseModel):
    """Fault recovery plan for a campaign."""

    plan_id: str = Field(default_factory=lambda: new_id("recovery_plan"))

    campaign_id: str

    strategy: str = "checkpoint-replay"

    max_job_attempts: int = Field(default=3, ge=1)

    checkpoint_enabled: bool = True

    rollback_enabled: bool = True

    created_at: datetime = Field(default_factory=utcnow)


class AuditEvent(BaseModel):
    """Audit event for distributed execution."""

    event_id: str

    event_type: str

    campaign_id: Optional[str] = None
    job_id: Optional[str] = None
    node_id: Optional[str] = None

    payload: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utcnow)

    previous_hash: str
    event_hash: str


class CloudMetrics(BaseModel):
    """Operational metrics for the distributed evolution cloud."""

    active_nodes: int = 0
    failed_nodes: int = 0

    pending_jobs: int = 0
    scheduled_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0

    artifacts_count: int = 0

    recovered_jobs: int = 0

    generated_at: datetime = Field(default_factory=utcnow)
