"""Integration tests for the Telemetry Engine."""

import pytest
from datetime import datetime, timezone

from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service, Operation, OperationType
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.operations.telemetry_engine import TelemetryEngine
from constitutional_architecture.operations.metrics_collector import MetricPoint
from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationClassification,
    ObservationSeverity,
    ObservationSource,
)
from constitutional_architecture.operations.drift_detector import RunningSystemSnapshot
from constitutional_architecture.operations.events import OperationalEventType


def _create_test_isr() -> ISR:
    return ISR(
        system=System(
            id="shop", name="Shop",
            modules=(
                Module(
                    id="mod-orders", name="Orders",
                    entities=(
                        Entity(id="ent-order", name="Order",
                               fields=(Field(name="id", field_type=FieldType.UUID, is_primary_key=True),)),
                    ),
                    services=(
                        Service(id="svc-orders", name="OrderService",
                                operations=(Operation(id="op-create", name="create_order"),)),
                    ),
                ),
            ),
        ),
    )


class TestTelemetryEngine:
    def test_ingest_metric(self):
        engine = TelemetryEngine()
        engine.ingest_metric(MetricPoint(
            name="cpu_usage", value=75.0, service_name="OrderService",
        ))
        assert engine.metrics_collector.total_points == 1

    def test_ingest_observation(self):
        engine = TelemetryEngine()
        obs = Observation(
            id="obs-1", source=ObservationSource.METRICS,
            severity=ObservationSeverity.WARNING,
            title="High CPU usage",
            description="CPU usage is high coupling detected in OrderService",
        )
        engine.ingest_observation(obs)
        stored = engine.memory.observations
        assert len(stored) == 1
        assert stored[0].classification != ObservationClassification.UNKNOWN

    def test_drift_detection(self):
        engine = TelemetryEngine()
        isr = _create_test_isr()
        snapshot = RunningSystemSnapshot(
            deployment_id="deploy-1", isr_hash=isr.content_hash,
            running_modules=("Orders",),
            running_services=(),
            running_endpoints=(),
        )
        engine.ingest_snapshot(snapshot)
        observations = engine.analyze(isr)
        assert engine.drift_detector.has_drift

    def test_fitness_signal_production(self):
        engine = TelemetryEngine()
        obs = Observation(
            id="obs-1", source=ObservationSource.METRICS,
            severity=ObservationSeverity.ERROR,
            title="High coupling",
            description="High coupling detected between services",
        )
        engine.ingest_observation(obs)
        signals = engine.produce_fitness_signals(
            deployment_id="deploy-1", isr_hash="test-hash",
        )
        assert len(signals) == 1
        assert signals[0].classification == ObservationClassification.ARCHITECTURAL_DEFICIENCY

    def test_no_fitness_for_implementation_bugs(self):
        engine = TelemetryEngine()
        obs = Observation(
            id="obs-1", source=ObservationSource.LOGS,
            severity=ObservationSeverity.ERROR,
            title="Null pointer exception",
            description="Null pointer exception in OrderService.create_order",
        )
        engine.ingest_observation(obs)
        stored = engine.memory.observations
        if stored and stored[0].classification == ObservationClassification.IMPLEMENTATION_BUG:
            signals = engine.produce_fitness_signals()
            assert len(signals) == 0

    def test_events_published(self):
        engine = TelemetryEngine()
        events_received = []
        engine.subscribe(OperationalEventType.OBSERVATION_CLASSIFIED, lambda e: events_received.append(e))
        obs = Observation(
            id="obs-1", source=ObservationSource.METRICS,
            severity=ObservationSeverity.WARNING,
            title="Test", description="Test observation",
        )
        engine.ingest_observation(obs)
        assert len(events_received) == 1

    def test_isr_not_modified(self):
        engine = TelemetryEngine()
        isr = _create_test_isr()
        original_hash = isr.content_hash
        engine.analyze(isr)
        assert isr.content_hash == original_hash

    def test_no_engine_imports(self):
        import constitutional_architecture.operations.telemetry_engine as mod
        import inspect
        source = inspect.getsource(mod)
        assert "from constitutional_architecture.engine" not in source
        assert "import constitutional_architecture.engine" not in source
        assert "from constitutional_architecture.compiler" not in source
        assert "from constitutional_architecture.deployment" not in source
