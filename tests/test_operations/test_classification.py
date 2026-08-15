"""Tests for the observation classifier."""

import pytest

from constitutional_architecture.operations.classification import ObservationClassifier
from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationClassification,
    ObservationSeverity,
    ObservationSource,
)


class TestObservationClassifier:
    def setup_method(self):
        self.classifier = ObservationClassifier()

    def test_architectural_deficiency(self):
        obs = Observation(
            id="obs-1", source=ObservationSource.METRICS,
            severity=ObservationSeverity.ERROR,
            title="High coupling detected",
            description="High coupling between OrderService and PaymentService",
        )
        result = self.classifier.classify(obs)
        assert result.classification == ObservationClassification.ARCHITECTURAL_DEFICIENCY

    def test_implementation_bug(self):
        obs = Observation(
            id="obs-2", source=ObservationSource.LOGS,
            severity=ObservationSeverity.ERROR,
            title="Null pointer exception",
            description="Null pointer exception in OrderService",
        )
        result = self.classifier.classify(obs)
        assert result.classification == ObservationClassification.IMPLEMENTATION_BUG

    def test_operational_misconfiguration(self):
        obs = Observation(
            id="obs-3", source=ObservationSource.HEALTH_CHECKS,
            severity=ObservationSeverity.ERROR,
            title="Connection refused",
            description="Connection refused to database on port 5432",
        )
        result = self.classifier.classify(obs)
        assert result.classification == ObservationClassification.OPERATIONAL_MISCONFIGURATION

    def test_requirement_gap(self):
        obs = Observation(
            id="obs-4", source=ObservationSource.EXTERNAL,
            severity=ObservationSeverity.INFO,
            title="Feature request",
            description="Users requesting missing feature for order tracking",
        )
        result = self.classifier.classify(obs)
        assert result.classification == ObservationClassification.REQUIREMENT_GAP

    def test_external_factor(self):
        obs = Observation(
            id="obs-5", source=ObservationSource.EXTERNAL,
            severity=ObservationSeverity.CRITICAL,
            title="AWS outage",
            description="AWS us-east-1 network outage affecting all services",
        )
        result = self.classifier.classify(obs)
        assert result.classification == ObservationClassification.EXTERNAL_FACTOR

    def test_unknown_low_confidence(self):
        obs = Observation(
            id="obs-6", source=ObservationSource.METRICS,
            severity=ObservationSeverity.INFO,
            title="Some event",
            description="Something happened",
        )
        result = self.classifier.classify(obs)
        assert result.confidence < 0.5
