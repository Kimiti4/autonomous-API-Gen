"""Tests for the Phase 26.1 Telemetry Adapter Framework backfill."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from learning.engine import ContinuousLearningEngine
from learning.models import LearningSignalType, Severity
from learning.telemetry import (
    IncidentLogAdapter,
    PrometheusMetricsAdapter,
    TelemetryEvent,
    TelemetrySource,
    default_telemetry_adapter_registry,
    enable_telemetry_adapters,
)


def _prometheus_event(**overrides):
    fields = dict(
        source=TelemetrySource.PROMETHEUS.value,
        subject_ref="svc:payment-processor",
        signal_type="PERFORMANCE",
        severity="HIGH",
        metric="cpu_usage",
        value=82.5,
        unit="percent",
        evidence_refs=["evidence:cpu:001"],
    )
    fields.update(overrides)
    return TelemetryEvent(**fields)


def _log_event(**overrides):
    fields = dict(
        source=TelemetrySource.LOG_AGGREGATOR.value,
        subject_ref="svc:api-gateway",
        signal_type="LOG",
        severity="CRITICAL",
        metric=None,
        value=0.0,
        message="rate limit exceeded for client x",
    )
    fields.update(overrides)
    return TelemetryEvent(**fields)


def test_prometheus_adapter_maps_to_performance_signal():
    adapter = PrometheusMetricsAdapter()
    signal = adapter.adapt(_prometheus_event())
    assert signal is not None
    assert signal.signal_type == LearningSignalType.PERFORMANCE
    assert signal.source == TelemetrySource.PROMETHEUS.value
    assert signal.metric == "cpu_usage"
    assert signal.value == 82.5
    assert signal.severity == Severity.HIGH


def test_incident_log_adapter_maps_to_log_signal():
    adapter = IncidentLogAdapter()
    signal = adapter.adapt(_log_event())
    assert signal is not None
    assert signal.signal_type == LearningSignalType.LOG
    assert signal.severity == Severity.CRITICAL
    assert signal.message == "rate limit exceeded for client x"


def test_empty_event_produces_no_signal():
    adapter = PrometheusMetricsAdapter()
    assert adapter.adapt(TelemetryEvent(source="prometheus")) is None


def test_registry_routes_by_source():
    registry = default_telemetry_adapter_registry()
    assert isinstance(registry.get("prometheus"), PrometheusMetricsAdapter)
    assert isinstance(registry.get("log_aggregator"), IncidentLogAdapter)
    assert set(registry.names()) == {"prometheus", "log_aggregator"}


def test_enable_telemetry_adapters_collects_prometheus_event():
    app = FastAPI()
    learning_engine = ContinuousLearningEngine()
    config = enable_telemetry_adapters(app, learning_engine=learning_engine)
    assert config["learning_engine"] is learning_engine
    assert app.state.telemetry_adapter_registry is config["registry"]

    client = TestClient(app)
    response = client.post(
        "/v1/learning/telemetry/collect",
        json={
            "source": "prometheus",
            "subject_ref": "svc:queue-worker",
            "signal_type": "PERFORMANCE",
            "severity": "INFO",
            "metric": "queue_length",
            "value": 142.0,
            "unit": "count",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["signal_type"] == "PERFORMANCE"
    assert body["source"] == "prometheus"

    signals = learning_engine.pipeline.signals
    assert any(
        s.signal_type is LearningSignalType.PERFORMANCE and s.metric == "queue_length"
        for s in signals
    ), "telemetry event must be ingested as a learning signal"


def test_enable_telemetry_adapters_lists_registered_adapters():
    app = FastAPI()
    enable_telemetry_adapters(app)
    client = TestClient(app)
    response = client.get("/v1/learning/telemetry/adapters")
    assert response.status_code == 200
    assert set(response.json()["adapters"]) == {"prometheus", "log_aggregator"}
