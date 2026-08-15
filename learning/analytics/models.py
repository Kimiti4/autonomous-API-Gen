"""
Models for anomaly detection and signal correlation.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..models import Severity
from ..utils import utcnow


class AnomalyDetectionPolicy(BaseModel):
    """Policy controlling anomaly detection and correlation."""

    z_threshold: float = Field(default=3.0, ge=0.0)

    ewma_alpha: float = Field(default=0.3, ge=0.0, le=1.0)

    min_samples: int = Field(default=5, ge=1)

    min_value_variance: float = Field(default=1e-6, ge=0.0)

    severity_anomaly_threshold: Severity = Severity.HIGH

    window_minutes: int = Field(default=60, ge=1)

    cluster_window_minutes: int = Field(default=15, ge=1)

    correlation_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

    min_cluster_signals: int = Field(default=2, ge=1)

    baseline_training: bool = True


class BaselineState(BaseModel):
    """Baseline state for one metric subject."""

    key: str

    count: int = 0

    mean: float = 0.0

    m2: float = 0.0

    ewma: float = 0.0

    ewm_var: float = 0.0

    updated_at: str = Field(default_factory=lambda: utcnow().isoformat())


class AnomalyRecord(BaseModel):
    """Anomaly detected from a learning signal."""

    id: str

    signal_id: str

    subject_ref: Optional[str] = None

    signal_type: str

    metric: Optional[str] = None

    severity: Severity = Severity.INFO

    value: float = 0.0

    baseline_mean: Optional[float] = None

    baseline_stddev: Optional[float] = None

    anomaly_score: float = 0.0

    detection_method: str

    timestamp: str


class SignalCorrelation(BaseModel):
    """Correlation between two signals."""

    id: str

    source_signal_id: str

    target_signal_id: str

    score: float

    reasons: List[str] = Field(default_factory=list)


class RootCauseCandidate(BaseModel):
    """Possible root-cause signal inside a correlated cluster."""

    signal_id: str

    subject_ref: Optional[str] = None

    signal_type: str

    severity: Severity

    score: float

    rationale: str


class IncidentCluster(BaseModel):
    """Cluster of correlated signals and anomalies."""

    id: str

    signal_ids: List[str] = Field(default_factory=list)

    anomaly_ids: List[str] = Field(default_factory=list)

    affected_subjects: List[str] = Field(default_factory=list)

    objectives: List[str] = Field(default_factory=list)

    severity: Severity = Severity.INFO

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    root_cause_candidates: List[RootCauseCandidate] = Field(
        default_factory=list
    )

    created_at: str = Field(default_factory=lambda: utcnow().isoformat())


class AnomalyReport(BaseModel):
    """Report produced by anomaly and correlation analysis."""

    analyzed_signals: int = 0

    anomalies: int = 0

    clusters: int = 0

    insights: int = 0

    generated_at: str = Field(default_factory=lambda: utcnow().isoformat())
