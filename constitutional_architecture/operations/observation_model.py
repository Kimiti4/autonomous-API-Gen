"""
Observation Model.

Defines the data models for operational observations.
All observations are append-only historical records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Optional


@unique
class ObservationSource(str, Enum):
    """Source of an operational observation."""

    METRICS = "metrics"
    TRACES = "traces"
    LOGS = "logs"
    INCIDENTS = "incidents"
    HEALTH_CHECKS = "health_checks"
    DEPLOYMENT_EVENTS = "deployment_events"
    COST_REPORTING = "cost_reporting"
    EXTERNAL = "external"

    def __str__(self) -> str:
        return self.value


@unique
class ObservationSeverity(str, Enum):
    """Severity of an observation."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    def __str__(self) -> str:
        return self.value


@unique
class ObservationClassification(str, Enum):
    """
    Classification of an observation by responsibility.

    This is the key intellectual contribution of Phase 6:
    distinguishing between observations that require different responses.
    """

    ARCHITECTURAL_DEFICIENCY = "architectural_deficiency"
    IMPLEMENTATION_BUG = "implementation_bug"
    OPERATIONAL_MISCONFIGURATION = "operational_misconfiguration"
    REQUIREMENT_GAP = "requirement_gap"
    EXTERNAL_FACTOR = "external_factor"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value

    @property
    def target_subsystem(self) -> str:
        mapping = {
            ObservationClassification.ARCHITECTURAL_DEFICIENCY: "evolution_engine",
            ObservationClassification.IMPLEMENTATION_BUG: "compiler_backend",
            ObservationClassification.OPERATIONAL_MISCONFIGURATION: "deployment_engine",
            ObservationClassification.REQUIREMENT_GAP: "requirement_intelligence",
            ObservationClassification.EXTERNAL_FACTOR: "none",
            ObservationClassification.UNKNOWN: "analysis_required",
        }
        return mapping[self]

    @property
    def produces_fitness_signal(self) -> bool:
        return self in {
            ObservationClassification.ARCHITECTURAL_DEFICIENCY,
            ObservationClassification.OPERATIONAL_MISCONFIGURATION,
        }


@dataclass(frozen=True)
class Observation:
    """
    A single operational observation.

    Immutable. Append-only. Historical record.
    Every observation is classified by responsibility.
    """

    id: str
    source: ObservationSource
    severity: ObservationSeverity
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    title: str = ""
    description: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    deployment_id: str = ""
    isr_hash: str = ""
    isr_node_id: str = ""
    artifact_path: str = ""
    service_name: str = ""
    classification: ObservationClassification = ObservationClassification.UNKNOWN
    classification_confidence: float = 0.0
    classification_reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FitnessSignal:
    """
    A fitness signal produced from operational observations.

    This is the output of Phase 6 that feeds the Evolution Engine's
    Dynamic Fitness Interface.
    """

    id: str
    deployment_id: str = ""
    isr_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dimensions: dict[str, float] = field(default_factory=dict)
    observation_ids: tuple[str, ...] = ()
    classification: ObservationClassification = ObservationClassification.UNKNOWN
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "deployment_id": self.deployment_id,
            "isr_hash": self.isr_hash,
            "timestamp": self.timestamp.isoformat(),
            "dimensions": dict(self.dimensions),
            "classification": self.classification.value,
            "confidence": self.confidence,
            "observation_count": len(self.observation_ids),
        }


@dataclass(frozen=True)
class DriftReport:
    """Report of drift between the running system and the ISR."""

    id: str
    deployment_id: str = ""
    isr_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    drift_type: str = ""
    severity: ObservationSeverity = ObservationSeverity.WARNING
    description: str = ""
    missing_from_running: tuple[str, ...] = ()
    extra_in_running: tuple[str, ...] = ()
    modified_components: tuple[dict[str, Any], ...] = ()
    recommended_action: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class Anomaly:
    """A detected statistical anomaly."""

    id: str
    metric_name: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observed_value: float = 0.0
    expected_value: float = 0.0
    deviation: float = 0.0
    severity: ObservationSeverity = ObservationSeverity.WARNING
    description: str = ""
    service_name: str = ""
    deployment_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Incident:
    """A classified operational incident."""

    id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    severity: ObservationSeverity = ObservationSeverity.ERROR
    title: str = ""
    description: str = ""
    classification: ObservationClassification = ObservationClassification.UNKNOWN
    classification_confidence: float = 0.0
    classification_reasoning: str = ""
    affected_services: tuple[str, ...] = ()
    affected_users: int = 0
    duration_seconds: float = 0.0
    estimated_cost: float = 0.0
    deployment_id: str = ""
    isr_hash: str = ""
    observation_ids: tuple[str, ...] = ()
    status: str = "open"
    resolution: str = ""
    lessons_learned: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Recommendation:
    """
    A recommendation for evolution, deployment, or requirement revision.

    Produced by the recommendation engine based on accumulated observations.
    """

    id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    category: str = ""
    title: str = ""
    description: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    priority: int = 0
    target_subsystem: str = ""
    target_isr_node_id: str = ""
    target_deployment_id: str = ""
    observation_ids: tuple[str, ...] = ()
    fitness_impact: dict[str, float] = field(default_factory=dict)
    suggested_mutation_type: str = ""
    suggested_action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
