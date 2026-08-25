"""Domain exceptions. Carry everything the error handler needs to build an
ErrorEnvelope. No framework imports here.

Constitutional rule: route handlers raise these; middleware/error_handler.py
owns the response shape. No bare str(e) ever reaches a client.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.contracts.errors import ErrorCode, RecoveryAction


@dataclass(frozen=True)
class RecoveryHint:
    action: RecoveryAction = "none"
    retry_after_seconds: Optional[int] = None
    resync_from_sequence: Optional[int] = None
    required_contract_version: Optional[str] = None
    message: str = ""


class ObservationDomainError(Exception):
    """Base for all observation-layer failures."""

    code: ErrorCode = "PLATFORM_INTERNAL"
    http_status: int = 500

    def __init__(
        self,
        message: str,
        *,
        recovery: Optional[RecoveryHint] = None,
        context: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.recovery = recovery or RecoveryHint()
        self.context = context or {}


class UnauthenticatedError(ObservationDomainError):
    code = "SEC_UNAUTHENTICATED"
    http_status = 401


class ForbiddenError(ObservationDomainError):
    code = "SEC_UNAUTHORIZED"
    http_status = 403


class NotFoundError(ObservationDomainError):
    code = "RESOURCE_NOT_FOUND"
    http_status = 404


class RateLimitedError(ObservationDomainError):
    code = "RESOURCE_RATE_LIMITED"
    http_status = 429

    def __init__(self, message: str, retry_after: int = 30, **kw) -> None:
        super().__init__(
            message,
            recovery=RecoveryHint(
                action="retry_with_backoff",
                retry_after_seconds=retry_after,
                message=f"Retry after {retry_after}s",
            ),
            **kw,
        )


class SequenceGapError(ObservationDomainError):
    code = "SYNC_SEQUENCE_GAP"
    http_status = 409


class StreamNotFoundError(ObservationDomainError):
    code = "SYNC_STREAM_NOT_FOUND"
    http_status = 404


class ReplayExhaustedError(ObservationDomainError):
    code = "SYNC_REPLAY_EXHAUSTED"
    http_status = 409

    def __init__(self, message: str, resync_from: int, **kw) -> None:
        super().__init__(
            message,
            recovery=RecoveryHint(
                action="resync_stream",
                resync_from_sequence=resync_from,
                message="Replay window exhausted; resync from snapshot",
            ),
            **kw,
        )


class ContractVersionError(ObservationDomainError):
    code = "CONTRACT_UNSUPPORTED_VERSION"
    http_status = 400