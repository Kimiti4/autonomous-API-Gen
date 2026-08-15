"""
Telemetry adapters that normalize raw telemetry into learning signals.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from ..models import LearningSignal, LearningSignalType, Severity
from ..utils import utcnow
from .models import TelemetryEvent, TelemetrySource


class TelemetryAdapter(Protocol):
    """Protocol for telemetry adapters producing learning signals."""

    source: str

    def adapt(self, event: TelemetryEvent) -> Optional[LearningSignal]:
        """Convert a raw telemetry event into a governed learning signal."""
        ...


class BaseTelemetryAdapter:
    """Base adapter with shared normalization helpers."""

    source: str = "base"

    def classify_signal_type(self, event: TelemetryEvent) -> LearningSignalType:
        try:
            return LearningSignalType(event.signal_type)
        except ValueError:
            return LearningSignalType.LOG

    def classify_severity(self, event: TelemetryEvent) -> Severity:
        try:
            return Severity(event.severity)
        except ValueError:
            return Severity.INFO

    def adapt(self, event: TelemetryEvent) -> Optional[LearningSignal]:
        if not event.subject_ref and not event.metric and not event.message:
            return None
        return LearningSignal(
            source=event.source or self.source,
            subject_ref=event.subject_ref,
            signal_type=self.classify_signal_type(event),
            severity=self.classify_severity(event),
            metric=event.metric,
            value=event.value,
            unit=event.unit,
            message=event.message,
            timestamp=event.timestamp or utcnow().isoformat(),
            labels=dict(event.labels),
            evidence_refs=list(event.evidence_refs),
        )


class PrometheusMetricsAdapter(BaseTelemetryAdapter):
    """Adapter for Prometheus metric telemetry."""

    source = TelemetrySource.PROMETHEUS.value

    def classify_signal_type(self, event: TelemetryEvent) -> LearningSignalType:
        return LearningSignalType.PERFORMANCE


class IncidentLogAdapter(BaseTelemetryAdapter):
    """Adapter for log-aggregator / incident telemetry."""

    source = TelemetrySource.LOG_AGGREGATOR.value

    def classify_signal_type(self, event: TelemetryEvent) -> LearningSignalType:
        return LearningSignalType.LOG

    def adapt(self, event: TelemetryEvent) -> Optional[LearningSignal]:
        if not event.message:
            return None
        return super().adapt(event)


class TelemetryAdapterRegistry:
    """Registry mapping telemetry source name to an adapter."""

    def __init__(self) -> None:
        self._adapters: Dict[str, TelemetryAdapter] = {}

    def register(self, adapter: TelemetryAdapter) -> None:
        self._adapters[adapter.source] = adapter

    def get(self, source: str) -> Optional[TelemetryAdapter]:
        return self._adapters.get(source)

    def names(self) -> List[str]:
        return list(self._adapters.keys())


def default_telemetry_adapter_registry() -> TelemetryAdapterRegistry:
    """Build the default registry shipped with the learning engine."""
    registry = TelemetryAdapterRegistry()
    registry.register(PrometheusMetricsAdapter())
    registry.register(IncidentLogAdapter())
    return registry
