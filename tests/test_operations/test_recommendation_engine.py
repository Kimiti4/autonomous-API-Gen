"""Tests for the recommendation engine."""

import pytest

from constitutional_architecture.operations.recommendation_engine import RecommendationEngine
from constitutional_architecture.operations.observation_model import (
    Incident,
    Observation,
    ObservationClassification,
    ObservationSeverity,
    ObservationSource,
)


class TestRecommendationEngine:
    def test_evolution_recommendation(self):
        engine = RecommendationEngine()
        incident = Incident(
            id="inc-1",
            severity=ObservationSeverity.ERROR,
            title="High coupling",
            description="High coupling detected between services",
            classification=ObservationClassification.ARCHITECTURAL_DEFICIENCY,
            classification_confidence=0.9,
            classification_reasoning="Pattern match",
        )
        recommendations = engine._recommend_evolution(incident, [])
        assert len(recommendations) >= 1
        assert recommendations[0].category == "evolution"
        assert recommendations[0].suggested_mutation_type == "extract_interface"

    def test_deployment_recommendation(self):
        engine = RecommendationEngine()
        incident = Incident(
            id="inc-2",
            severity=ObservationSeverity.ERROR,
            title="Connection refused",
            description="DB connection refused",
            classification=ObservationClassification.OPERATIONAL_MISCONFIGURATION,
            classification_confidence=0.85,
            classification_reasoning="Pattern match",
        )
        recommendations = engine._recommend_deployment(incident)
        assert len(recommendations) >= 1
        assert recommendations[0].category == "deployment"

    def test_requirement_recommendation(self):
        engine = RecommendationEngine()
        incident = Incident(
            id="inc-3",
            severity=ObservationSeverity.WARNING,
            title="Missing feature",
            description="Users requesting feature X",
            classification=ObservationClassification.REQUIREMENT_GAP,
            classification_confidence=0.7,
            classification_reasoning="Pattern match",
        )
        recommendations = engine._recommend_requirement(incident)
        assert len(recommendations) >= 1
        assert recommendations[0].category == "requirement"
