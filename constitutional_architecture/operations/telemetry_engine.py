"""
Telemetry Engine — Top-Level Orchestrator.

The sensory system of the platform. Orchestrates all operational
intelligence subsystems.

CONSTITUTIONAL CONSTRAINT: This module imports from isr.*.
It NEVER imports from engine.*.
It NEVER imports from compiler.*.
It NEVER imports from deployment.*.
It produces signals; it does not trigger evolution.
"""

from __future__ import annotations

import uuid
from typing import Optional

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.operations.anomaly_detector import AnomalyDetector
from constitutional_architecture.operations.classification import ObservationClassifier
from constitutional_architecture.operations.cost_analyzer import CostAnalyzer
from constitutional_architecture.operations.drift_detector import DriftDetector, RunningSystemSnapshot
from constitutional_architecture.operations.events import (
    OperationalEvent,
    OperationalEventBus,
    OperationalEventType,
)
from constitutional_architecture.operations.fitness_feedback import FitnessFeedbackProducer
from constitutional_architecture.operations.incident_engine import IncidentEngine
from constitutional_architecture.operations.log_analyzer import LogAnalyzer
from constitutional_architecture.operations.metrics_collector import MetricPoint, MetricsCollector
from constitutional_architecture.operations.observation_model import (
    FitnessSignal,
    Observation,
    ObservationClassification,
    Recommendation,
)
from constitutional_architecture.operations.operational_memory import OperationalMemory
from constitutional_architecture.operations.recommendation_engine import RecommendationEngine
from constitutional_architecture.operations.reliability_analyzer import ReliabilityAnalyzer
from constitutional_architecture.operations.tracing_engine import TracingEngine


class TelemetryEngine:

    def __init__(
        self,
        event_bus: Optional[OperationalEventBus] = None,
        memory: Optional[OperationalMemory] = None,
    ) -> None:
        self._event_bus = event_bus or OperationalEventBus()
        self._memory = memory or OperationalMemory()
        self._classifier = ObservationClassifier()
        self._metrics = MetricsCollector()
        self._tracing = TracingEngine()
        self._logs = LogAnalyzer()
        self._anomaly_detector = AnomalyDetector()
        self._drift_detector = DriftDetector()
        self._incident_engine = IncidentEngine(self._classifier)
        self._reliability = ReliabilityAnalyzer()
        self._cost = CostAnalyzer()
        self._fitness_producer = FitnessFeedbackProducer(self._classifier)
        self._recommendation_engine = RecommendationEngine(self._incident_engine)

    def ingest_metric(self, point: MetricPoint) -> None:
        self._metrics.record(point)
        self._event_bus.publish(OperationalEvent(
            event_type=OperationalEventType.METRIC_COLLECTED,
            data={"metric": point.name, "value": point.value},
        ))

    def ingest_trace(self, trace) -> None:
        self._tracing.record_trace(trace)
        self._event_bus.publish(OperationalEvent(
            event_type=OperationalEventType.TRACE_ANALYZED,
            data={"trace_id": trace.trace_id},
        ))

    def ingest_log(self, entry) -> None:
        self._logs.ingest(entry)

    def ingest_observation(self, observation: Observation) -> None:
        result = self._classifier.classify(observation)
        classified = Observation(
            id=observation.id, source=observation.source,
            severity=observation.severity, timestamp=observation.timestamp,
            title=observation.title, description=observation.description,
            details=observation.details,
            deployment_id=observation.deployment_id,
            isr_hash=observation.isr_hash,
            isr_node_id=observation.isr_node_id,
            artifact_path=observation.artifact_path,
            service_name=observation.service_name,
            classification=result.classification,
            classification_confidence=result.confidence,
            classification_reasoning=result.reasoning,
            metadata=observation.metadata,
        )

        self._memory.record_observation(classified)
        self._event_bus.publish(OperationalEvent(
            event_type=OperationalEventType.OBSERVATION_CLASSIFIED,
            data={
                "observation_id": classified.id,
                "classification": classified.classification.value,
                "confidence": classified.classification_confidence,
            },
        ))

    def ingest_snapshot(self, snapshot: RunningSystemSnapshot) -> None:
        self._drift_detector.record_snapshot(snapshot)

    def analyze(self, isr: Optional[ISR] = None) -> list[Observation]:
        observations: list[Observation] = []
        observations.extend(self._metrics.check_thresholds())
        observations.extend(self._logs.analyze())
        observations.extend(self._cost.produce_observations())

        if isr is not None:
            latest_snapshot = (
                self._drift_detector._snapshots[-1]
                if self._drift_detector._snapshots
                else None
            )
            if latest_snapshot is not None:
                drift_report = self._drift_detector.detect_drift(isr, latest_snapshot)
                self._memory.record_drift(drift_report)
                if drift_report.drift_type != "none":
                    self._event_bus.publish(OperationalEvent(
                        event_type=OperationalEventType.DRIFT_DETECTED,
                        data={
                            "drift_type": drift_report.drift_type,
                            "severity": drift_report.severity.value,
                            "recommended_action": drift_report.recommended_action,
                        },
                    ))

        for obs in observations:
            self.ingest_observation(obs)

        return observations

    def detect_anomalies(self) -> list:
        all_anomalies = []
        for metric_name in self._metrics.metric_names:
            series = self._metrics.get_series(metric_name)
            result = self._anomaly_detector.detect(series)
            for anomaly in result.anomalies:
                self._memory.record_anomaly(anomaly)
                all_anomalies.append(anomaly)
                self._event_bus.publish(OperationalEvent(
                    event_type=OperationalEventType.ANOMALY_DETECTED,
                    data={
                        "anomaly_id": anomaly.id,
                        "metric": anomaly.metric_name,
                        "deviation": anomaly.deviation,
                    },
                ))
        return all_anomalies

    def create_incident(self, observations: list[Observation]):
        incident = self._incident_engine.create_incident(observations)
        self._memory.record_incident(incident)
        self._event_bus.publish(OperationalEvent(
            event_type=OperationalEventType.INCIDENT_CLASSIFIED,
            data={
                "incident_id": incident.id,
                "classification": incident.classification.value,
                "severity": incident.severity.value,
            },
        ))
        return incident

    def produce_fitness_signals(
        self, deployment_id: str = "", isr_hash: str = "",
    ) -> list[FitnessSignal]:
        recent = self._memory.get_recent_observations(100)
        signal = self._fitness_producer.produce_signal(
            recent, deployment_id=deployment_id, isr_hash=isr_hash,
        )
        if signal is not None:
            self._memory.record_fitness_signal(signal)
            self._event_bus.publish(OperationalEvent(
                event_type=OperationalEventType.FITNESS_SIGNAL_PRODUCED,
                data={
                    "signal_id": signal.id,
                    "dimensions": list(signal.dimensions.keys()),
                    "classification": signal.classification.value,
                },
            ))
            return [signal]
        return []

    def get_latest_fitness_signal(self) -> Optional[FitnessSignal]:
        signals = self._memory.get_recent_signals(1)
        return signals[0] if signals else None

    def generate_recommendations(self) -> list[Recommendation]:
        observations = self._memory.get_recent_observations(500)
        incidents = self._memory.incidents
        recommendations = self._recommendation_engine.generate_recommendations(
            observations, incidents,
        )
        for rec in recommendations:
            self._memory.record_recommendation(rec)
            self._event_bus.publish(OperationalEvent(
                event_type=OperationalEventType.RECOMMENDATION_GENERATED,
                data={
                    "recommendation_id": rec.id,
                    "category": rec.category,
                    "target": rec.target_subsystem,
                },
            ))
        return recommendations

    def subscribe(self, event_type: OperationalEventType, handler) -> None:
        self._event_bus.subscribe(event_type, handler)

    @property
    def metrics_collector(self) -> MetricsCollector:
        return self._metrics

    @property
    def drift_detector(self) -> DriftDetector:
        return self._drift_detector

    @property
    def incident_engine(self) -> IncidentEngine:
        return self._incident_engine

    @property
    def recommendation_engine(self) -> RecommendationEngine:
        return self._recommendation_engine

    @property
    def memory(self) -> OperationalMemory:
        return self._memory
