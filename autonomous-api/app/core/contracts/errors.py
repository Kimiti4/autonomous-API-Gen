"""ErrorEnvelope contract (POC v1.1 Error Contract v1.0).

Framework-agnostic. No FastAPI / DB / engine imports.

Invariants enforced here:
1. ERROR_TAXONOMY is the single source of truth for code to
   (category, severity) mapping. Totality is enforced by unit test.
2. build_error_envelope() guarantees taxonomy consistency and
   self-consistent provenance (contentHash over the error body).
3. traceId is correlation-only; it must never carry internals.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.contracts.provenance import (
    ContractMetadata,
    ObservationProvenance,
    now_utc,
)
from app.core.ids import content_hash

ErrorCategory = Literal[
    "client", "platform", "contract", "synchronization", "security", "resource",
]
ErrorSeverity = Literal["info", "warning", "error", "fatal"]
ErrorCode = Literal[
    "CLIENT_INVALID_REQUEST", "CLIENT_MISSING_PARAMETER",
    "CLIENT_INVALID_CONTRACT_VERSION",
    "SEC_UNAUTHENTICATED", "SEC_UNAUTHORIZED", "SEC_TOKEN_EXPIRED",
    "SEC_FORBIDDEN_RESOURCE",
    "CONTRACT_DEPRECATED", "CONTRACT_UNSUPPORTED_VERSION",
    "CONTRACT_SCHEMA_MISMATCH",
    "SYNC_SEQUENCE_GAP", "SYNC_STREAM_NOT_FOUND",
    "SYNC_CHECKPOINT_UNAVAILABLE", "SYNC_REPLAY_EXHAUSTED",
    "SYNC_DESYNCHRONIZED",
    "PLATFORM_INTERNAL", "PLATFORM_UNAVAILABLE", "PLATFORM_DEGRADED",
    "PLATFORM_MAINTENANCE",
    "RESOURCE_RATE_LIMITED", "RESOURCE_QUOTA_EXCEEDED", "RESOURCE_NOT_FOUND",
    "RESOURCE_CONCURRENT_MODIFICATION",
]
RecoveryAction = Literal[
    "none", "retry_immediately", "retry_with_backoff", "resync_stream",
    "renegotiate_contract", "authenticate", "failover", "halt_and_report",
]

# Single source of truth: code maps to (category, severity). Enforced by tests.
ERROR_TAXONOMY = {
    "CLIENT_INVALID_REQUEST": ("client", "error"),
    "CLIENT_MISSING_PARAMETER": ("client", "error"),
    "CLIENT_INVALID_CONTRACT_VERSION": ("client", "error"),
    "SEC_UNAUTHENTICATED": ("security", "error"),
    "SEC_UNAUTHORIZED": ("security", "error"),
    "SEC_TOKEN_EXPIRED": ("security", "warning"),
    "SEC_FORBIDDEN_RESOURCE": ("security", "error"),
    "CONTRACT_DEPRECATED": ("contract", "warning"),
    "CONTRACT_UNSUPPORTED_VERSION": ("contract", "fatal"),
    "CONTRACT_SCHEMA_MISMATCH": ("contract", "error"),
    "SYNC_SEQUENCE_GAP": ("synchronization", "error"),
    "SYNC_STREAM_NOT_FOUND": ("synchronization", "error"),
    "SYNC_CHECKPOINT_UNAVAILABLE": ("synchronization", "fatal"),
    "SYNC_REPLAY_EXHAUSTED": ("synchronization", "fatal"),
    "SYNC_DESYNCHRONIZED": ("synchronization", "fatal"),
    "PLATFORM_INTERNAL": ("platform", "error"),
    "PLATFORM_UNAVAILABLE": ("platform", "error"),
    "PLATFORM_DEGRADED": ("platform", "warning"),
    "PLATFORM_MAINTENANCE": ("platform", "warning"),
    "RESOURCE_RATE_LIMITED": ("resource", "error"),
    "RESOURCE_QUOTA_EXCEEDED": ("resource", "error"),
    "RESOURCE_NOT_FOUND": ("resource", "error"),
    "RESOURCE_CONCURRENT_MODIFICATION": ("resource", "error"),
}


class RecoveryGuidance(BaseModel):
    model_config = ConfigDict(frozen=True)
    action: RecoveryAction
    retryAfterSeconds: Optional[int] = Field(default=None, ge=0)
    alternativeEndpoint: Optional[str] = None
    resyncFromSequence: Optional[int] = Field(default=None, ge=0)
    requiredContractVersion: Optional[str] = None
    message: str


class ObservationError(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: ErrorCode
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    occurredAt: str  # ISO-8601 UTC
    traceId: Optional[str] = None  # correlation only; never carries internals


class ErrorContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    contractId: Optional[str] = None
    operation: Optional[str] = None
    parameters: Optional[dict] = None
    streamId: Optional[str] = None
    sequence: Optional[int] = Field(default=None, ge=0)


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: ContractMetadata
    error: ObservationError
    context: Optional[ErrorContext] = None
    recovery: RecoveryGuidance
    provenance: ObservationProvenance


def build_error_envelope(
    *,
    code,
    message: str,
    occurred_at=None,
    source_revision: str,
    source_subsystem: str,
    recovery: RecoveryGuidance,
    contract_id: str = "platform.observation.errors",
    schema_version: str = "1.0.0",
    context: Optional[ErrorContext] = None,
    trace_id: Optional[str] = None,
):
    """Factory guaranteeing taxonomy consistency + self-consistent provenance."""
    if code not in ERROR_TAXONOMY:
        raise ValueError("Unknown ErrorCode: %r" % (code,))
    category, severity = ERROR_TAXONOMY[code]

    if occurred_at is None:
        occurred_dt = now_utc()
    elif isinstance(occurred_at, datetime):
        occurred_dt = occurred_at
    else:
        occurred_dt = datetime.fromisoformat(occurred_at)
    occurred_iso = occurred_dt.isoformat()

    error = ObservationError(
        code=code, category=category, severity=severity,
        message=message, occurredAt=occurred_iso, traceId=trace_id,
    )
    # Hash over the error body itself for auditability.
    digest = content_hash(error.model_dump(mode="json"))
    provenance = ObservationProvenance(
        sourceRevision=source_revision,
        sourceSubsystem=source_subsystem,
        capturedAt=occurred_dt,
        contentHash=digest,
    )
    return ErrorEnvelope(
        metadata=ContractMetadata(contractId=contract_id, schemaVersion=schema_version),
        error=error,
        context=context,
        recovery=recovery,
        provenance=provenance,
    )