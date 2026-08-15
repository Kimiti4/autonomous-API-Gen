"""
Audit emission for Knowledge Graph operations.

The Knowledge Graph must be auditable.

This module defines a minimal audit contract and a logging-based reference
implementation. Production deployments should emit audit events into the
Phase 28 Governance Kernel audit stream.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from pydantic import BaseModel, Field

from .models import utcnow


logger = logging.getLogger("knowledge.audit")


class AuditEvent(BaseModel):
    """A Knowledge Graph audit event."""

    event_type: str
    actor_id: str
    subject_type: str
    subject_id: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())


class AuditEmitter(Protocol):
    """Abstract audit emitter."""

    def emit(self, event: AuditEvent) -> None:
        ...


class LoggingAuditEmitter:
    """
    Logging-based audit emitter.

    This is a reference implementation. Replace it with an emitter that
    writes to the Governance Kernel audit log.
    """

    def emit(self, event: AuditEvent) -> None:
        logger.info(event.model_dump_json())
