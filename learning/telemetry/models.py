"""
Models for telemetry ingestion and the adapter framework.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils import utcnow


class TelemetrySource(str, Enum):
    """Canonical telemetry sources an adapter can normalize."""

    PROMETHEUS = "prometheus"
    LOG_AGGREGATOR = "log_aggregator"
    INCIDENT_MANAGER = "incident_manager"
    SECURITY_SCANNER = "security_scanner"
    COST_EXPORTER = "cost_exporter"
    CUSTOMER_FEEDBACK = "customer_feedback"
    CUSTOM = "custom"


class TelemetryEvent(BaseModel):
    """Raw normalized telemetry event awaiting learning-signal conversion."""

    source: str

    subject_ref: Optional[str] = None

    signal_type: str = "PERFORMANCE"

    severity: str = "INFO"

    metric: Optional[str] = None

    value: float = 0.0

    unit: Optional[str] = None

    message: Optional[str] = None

    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())

    labels: Dict[str, str] = Field(default_factory=dict)

    evidence_refs: List[str] = Field(default_factory=list)
