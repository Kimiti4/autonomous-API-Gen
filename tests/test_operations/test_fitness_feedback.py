"""Tests for fitness feedback production."""

import pytest

from constitutional_architecture.operations.fitness_feedback import FitnessFeedbackProducer
from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationClassification,
    ObservationSeverity,
    ObservationSource,
)


class TestFitnessFeedbackProducer:
    def test_produces_signal_for_architectural(self):
        producer = FitnessFeedbackProducer()
        obs = Observation(
            id="obs-1", source=ObservationSource.METRICS,
            severity=ObservationSeverity.ERROR,
            title="High coupling",
            description="High coupling detected between services",
            classification=ObservationClassification.ARCHITECTURAL_DEFICIENCY,
            classification_confidence=0.9,
        )
        signal = producer.produce_signal([obs], deployment_id="deploy-1")
        assert signal is not None
        assert signal.classification == ObservationClassification.ARCHITECTURAL_DEFICIENCY

    def test_no_signal_for_implementation_bug(self):
        producer = FitnessFeedbackProducer()
        obs = Observation(
            id="obs-1", source=ObservationSource.LOGS,
            severity=ObservationSeverity.ERROR,
            title="Null pointer exception",
            description="Null pointer in OrderService",
            classification=ObservationClassification.IMPLEMENTATION_BUG,
            classification_confidence=0.9,
        )
        signal = producer.produce_signal([obs])
        assert signal is None

    def test_aggregate_signal(self):
        producer = FitnessFeedbackProducer()
        obs1 = Observation(
            id="obs-1", source=ObservationSource.METRICS,
            severity=ObservationSeverity.WARNING,
            title="High coupling",
            description="High coupling",
            classification=ObservationClassification.ARCHITECTURAL_DEFICIENCY,
            classification_confidence=0.8,
        )
        obs2 = Observation(
            id="obs-2", source=ObservationSource.METRICS,
            severity=ObservationSeverity.ERROR,
            title="Bottleneck",
            description="Scalability bottleneck",
            classification=ObservationClassification.ARCHITECTURAL_DEFICIENCY,
            classification_confidence=0.9,
        )
        signal1 = producer.produce_signal([obs1])
        signal2 = producer.produce_signal([obs2])
        assert signal1 is not None and signal2 is not None

        aggregated = producer.compute_aggregate_signal([signal1, signal2])
        assert aggregated is not None
        assert "reliability" in aggregated.dimensions
