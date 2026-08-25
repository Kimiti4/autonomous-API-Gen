"""Global conversion of every exception into an ErrorEnvelope.

Constitutional rule: NO bare str(e) reaches a client. NO stack frames leak.
The HTTP status is a coarse hint; the envelope is authoritative.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.contracts.errors import (
    ErrorCode,
    ErrorEnvelope,
    RecoveryGuidance,
    build_error_envelope,
)
from app.core.contracts.provenance import now_utc
from app.core.exceptions import ObservationDomainError

logger = logging.getLogger("observation.errors")

_HTTP_TO_CODE: dict = {
    400: "CLIENT_INVALID_REQUEST",
    401: "SEC_UNAUTHENTICATED",
    403: "SEC_UNAUTHORIZED",
    404: "RESOURCE_NOT_FOUND",
    409: "RESOURCE_CONCURRENT_MODIFICATION",
    429: "RESOURCE_RATE_LIMITED",
    503: "PLATFORM_UNAVAILABLE",
}


class ErrorHandlingConfig:
    def __init__(
        self,
        *,
        source_revision: str,
        source_subsystem: str = "api",
        contract_id: str = "platform.observation.errors",
        schema_version: str = "1.0.0",
    ) -> None:
        self.source_revision = source_revision
        self.source_subsystem = source_subsystem
        self.contract_id = contract_id
        self.schema_version = schema_version


def _recovery_for(code: ErrorCode) -> RecoveryGuidance:
    if code == "RESOURCE_RATE_LIMITED":
        return RecoveryGuidance(
            action="retry_with_backoff", retryAfterSeconds=30,
            message="Retry after backoff",
        )
    if code in ("SYNC_SEQUENCE_GAP", "SYNC_REPLAY_EXHAUSTED"):
        return RecoveryGuidance(action="resync_stream", message="Resync stream")
    if code == "SEC_UNAUTHENTICATED":
        return RecoveryGuidance(action="authenticate", message="Authenticate")
    if code == "SEC_TOKEN_EXPIRED":
        return RecoveryGuidance(action="authenticate", message="Re-authenticate")
    if code == "PLATFORM_UNAVAILABLE":
        return RecoveryGuidance(
            action="retry_with_backoff", retryAfterSeconds=5,
            message="Retry with backoff",
        )
    return RecoveryGuidance(action="none", message="No automatic recovery")


def _respond(status_code: int, envelope: ErrorEnvelope) -> JSONResponse:
    headers = {}
    if (
        envelope.error.code == "RESOURCE_RATE_LIMITED"
        and envelope.recovery.retryAfterSeconds is not None
    ):
        headers["Retry-After"] = str(envelope.recovery.retryAfterSeconds)
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
        headers=headers or None,
    )


def install_error_handlers(app: FastAPI, cfg: ErrorHandlingConfig) -> None:
    @app.exception_handler(ObservationDomainError)
    async def _domain(request: Request, exc: ObservationDomainError):
        trace_id = str(uuid.uuid4())
        # Log the real detail server-side; send only the safe message.
        logger.exception(
            "observation_domain_error",
            extra={"trace_id": trace_id, "code": exc.code, "path": request.url.path},
        )
        rec = exc.recovery
        if rec.action == "none":
            # No explicit hint → derive the canonical recovery for the code.
            guidance = _recovery_for(exc.code)
            if guidance.message == "No automatic recovery":
                guidance = RecoveryGuidance(
                    action="none", message=exc.message
                )
        else:
            guidance = RecoveryGuidance(
                action=rec.action,
                retryAfterSeconds=rec.retry_after_seconds,
                resyncFromSequence=rec.resync_from_sequence,
                requiredContractVersion=rec.required_contract_version,
                message=rec.message or exc.message,
            )
        envelope = build_error_envelope(
            code=exc.code,
            message=exc.message,
            occurred_at=now_utc(),
            source_revision=cfg.source_revision,
            source_subsystem=cfg.source_subsystem,
            recovery=guidance,
            contract_id=cfg.contract_id,
            schema_version=cfg.schema_version,
            trace_id=trace_id,
            context=exc.context or None,
        )
        return _respond(exc.http_status, envelope)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        # Field names only; never echo raw input values back.
        fields = sorted({str(e.get("loc", ["?"])[-1]) for e in exc.errors()})
        envelope = build_error_envelope(
            code="CLIENT_INVALID_REQUEST",
            message="Request validation failed",
            occurred_at=now_utc(),
            source_revision=cfg.source_revision,
            source_subsystem=cfg.source_subsystem,
            recovery=RecoveryGuidance(action="none", message="Correct the request"),
            contract_id=cfg.contract_id,
            schema_version=cfg.schema_version,
            context={
                "operation": "request_validation",
                "parameters": {"fields": fields},
            },
        )
        return _respond(status.HTTP_422_UNPROCESSABLE_ENTITY, envelope)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = _HTTP_TO_CODE.get(exc.status_code, "PLATFORM_INTERNAL")
        envelope = build_error_envelope(
            code=code,
            message=str(exc.detail) if exc.detail else "Request failed",
            occurred_at=now_utc(),
            source_revision=cfg.source_revision,
            source_subsystem=cfg.source_subsystem,
            recovery=_recovery_for(code),
            contract_id=cfg.contract_id,
            schema_version=cfg.schema_version,
        )
        return _respond(exc.status_code, envelope)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        trace_id = str(uuid.uuid4())
        # Full detail stays server-side. Client gets a stable, safe message.
        logger.exception("unhandled_error", extra={"trace_id": trace_id})
        envelope = build_error_envelope(
            code="PLATFORM_INTERNAL",
            message="Internal platform error",
            occurred_at=now_utc(),
            source_revision=cfg.source_revision,
            source_subsystem=cfg.source_subsystem,
            recovery=RecoveryGuidance(
                action="retry_with_backoff", retryAfterSeconds=5,
                message="Retry with backoff",
            ),
            contract_id=cfg.contract_id,
            schema_version=cfg.schema_version,
            trace_id=trace_id,
        )
        return _respond(status.HTTP_500_INTERNAL_SERVER_ERROR, envelope)