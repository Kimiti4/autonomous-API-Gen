"""
Models for learning observability and operational dashboards.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..utils import utcnow


class OperationalStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class ObservabilityPolicy(BaseModel):
    """Policy controlling operational health evaluation."""

    recent_signal_window_minutes: int = Field(default=60, ge=1)

    signal_staleness_minutes: int = Field(default=120, ge=1)

    anomaly_rate_warning_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

    anomaly_rate_critical_threshold: float = Field(default=0.60, ge=0.0, le=1.0)

    pending_approvals_warning_threshold: int = Field(default=5, ge=0)

    safety_blocker_critical_threshold: int = Field(default=1, ge=0)


class LearningMetricsSnapshot(BaseModel):
    """Snapshot of learning-platform operational metrics."""

    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())

    signal_count: int = 0
    recent_signal_count: int = 0

    anomaly_count: int = 0
    cluster_count: int = 0
    insight_count: int = 0

    insight_backlog: int = 0

    submission_count: int = 0
    pending_approval_count: int = 0

    kill_switch_enabled: bool = False

    safety_blocker_count: int = 0

    average_cluster_confidence: Optional[float] = None
    average_insight_confidence: Optional[float] = None

    quality_score: Optional[float] = None

    knowledge_sync_counts: Dict[str, int] = Field(default_factory=dict)


class OperationalHealth(BaseModel):
    """Operational health assessment."""

    status: OperationalStatus

    reasons: List[str] = Field(default_factory=list)

    checks: Dict[str, bool] = Field(default_factory=dict)

    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())


class DashboardPanel(BaseModel):
    """Dashboard panel."""

    title: str

    panel_type: str = "metric_table"

    data: Dict[str, Any] = Field(default_factory=dict)


class OperationalDashboard(BaseModel):
    """Operational dashboard model."""

    id: str

    title: str

    status: OperationalStatus

    reasons: List[str] = Field(default_factory=list)

    panels: List[DashboardPanel] = Field(default_factory=list)

    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())
