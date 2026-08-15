"""
Models for memory consolidation and Knowledge Graph sync.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemorySourceType(str, Enum):
    ORGANIZATION_MEMORY = "ORGANIZATION_MEMORY"
    TASK_DECISION = "TASK_DECISION"
    RECOMMENDATION = "RECOMMENDATION"
    REPUTATION_EVENT = "REPUTATION_EVENT"
    OVERSIGHT_ACTION = "OVERSIGHT_ACTION"
    POLICY_DECISION = "POLICY_DECISION"
    CERTIFICATION = "CERTIFICATION"
    FEDERATION_DECISION = "FEDERATION_DECISION"
    CONFLICT_RESOLUTION = "CONFLICT_RESOLUTION"
    EVOLUTION_EVENT = "EVOLUTION_EVENT"
    PRODUCTION_FEEDBACK = "PRODUCTION_FEEDBACK"


class MemorySensitivity(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class MemoryRecordStatus(str, Enum):
    RAW = "RAW"
    CONSOLIDATED = "CONSOLIDATED"
    DUPLICATE = "DUPLICATE"
    SYNCED = "SYNCED"
    EXPIRED = "EXPIRED"
    REDACTED = "REDACTED"


class NormalizedMemoryRecord(BaseModel):
    """Normalized organizational memory record."""

    id: str

    source_type: MemorySourceType
    source_id: str

    organization_id: Optional[str] = None

    subject_type: Optional[str] = None
    subject_id: Optional[str] = None

    title: str
    summary: str = ""

    content: Dict[str, Any] = Field(default_factory=dict)

    evidence_refs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL

    status: MemoryRecordStatus = MemoryRecordStatus.RAW

    content_hash: str

    ttl_days: Optional[int] = None

    occurred_at: str
    received_at: str

    properties: Dict[str, Any] = Field(default_factory=dict)


class MemoryConsolidationPolicy(BaseModel):
    """Policy controlling consolidation and sync behavior."""

    default_sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL

    default_ttl_days: Optional[int] = Field(default=365, ge=1)

    redact_restricted: bool = True

    dedupe_enabled: bool = True

    require_evidence_for_sync: bool = True

    allow_restricted_sync: bool = False

    allowed_sync_sensitivities: List[MemorySensitivity] = Field(
        default_factory=lambda: [
            MemorySensitivity.PUBLIC,
            MemorySensitivity.INTERNAL,
        ]
    )


class KGEntityPayload(BaseModel):
    """Entity payload for Knowledge Graph sync."""

    id: Optional[str] = None

    entity_type: str
    name: str

    namespace: str = "civilization"

    description: str = ""

    properties: Dict[str, Any] = Field(default_factory=dict)

    source_refs: List[str] = Field(default_factory=list)


class KGRelationPayload(BaseModel):
    """Relation payload for Knowledge Graph sync."""

    id: Optional[str] = None

    relation_type: str

    source_entity_id: str
    target_entity_id: str

    properties: Dict[str, Any] = Field(default_factory=dict)

    source_refs: List[str] = Field(default_factory=list)


class KGSyncStatus(str, Enum):
    SYNCED = "SYNCED"
    ALREADY_SYNCED = "ALREADY_SYNCED"
    FAILED = "FAILED"
    SKIPPED_SENSITIVITY = "SKIPPED_SENSITIVITY"
    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
    SKIPPED_EXPIRED = "SKIPPED_EXPIRED"
    SKIPPED_MISSING_EVIDENCE = "SKIPPED_MISSING_EVIDENCE"


class KGSyncResult(BaseModel):
    """Result of synchronizing one memory record."""

    record_id: str

    status: KGSyncStatus

    entity_id: Optional[str] = None

    relation_ids: List[str] = Field(default_factory=list)

    issues: List[str] = Field(default_factory=list)

    synced_at: str
