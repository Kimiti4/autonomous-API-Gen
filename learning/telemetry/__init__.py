"""
Telemetry Adapter Framework.

This package provides the safe ingestion boundary for the Continuous Learning
Infrastructure. Telemetry adapters normalize raw operational telemetry into
governed `LearningSignal` objects that feed anomaly detection and correlation.
"""

from .adapters import (
    BaseTelemetryAdapter,
    IncidentLogAdapter,
    PrometheusMetricsAdapter,
    TelemetryAdapter,
    TelemetryAdapterRegistry,
    default_telemetry_adapter_registry,
)
from .api import enable_telemetry_adapters
from .models import TelemetryEvent, TelemetrySource

__version__ = "0.1.0"

__all__ = [
    "BaseTelemetryAdapter",
    "IncidentLogAdapter",
    "PrometheusMetricsAdapter",
    "TelemetryAdapter",
    "TelemetryAdapterRegistry",
    "TelemetryEvent",
    "TelemetrySource",
    "default_telemetry_adapter_registry",
    "enable_telemetry_adapters",
]
