"""
Compiler governance audit events.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from pydantic import BaseModel, Field

from ..models import utcnow


logger = logging.getLogger("compiler.governance.audit")


class CompilerAuditEvent(BaseModel):
    """Audit event emitted by compiler governance."""

    event_type: str
    backend_id: str
    backend_version: str

    environment: str = ""
    actor_id: str = ""

    reason: str = ""
    details: dict[str, Any] = Field(default_factory=dict)

    timestamp: str = Field(
        default_factory=lambda: utcnow().isoformat()
    )


class AuditEmitter(Protocol):
    """Abstract audit emitter."""

    def emit(self, event: CompilerAuditEvent) -> None:
        ...


class LoggingAuditEmitter:
    """Logging-based audit emitter."""

    def emit(self, event: CompilerAuditEvent) -> None:
        logger.info(event.model_dump_json())
