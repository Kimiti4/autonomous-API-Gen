"""Tests for the fitness vector."""

import pytest

from constitutional_architecture.engine.fitness import FitnessVector


class TestFitnessVector:
    def test_composite_score_equal_weights(self):
        fv = FitnessVector(values={"a": 0.8, "b": 0.6, "c": 1.0})
        score = fv.composite_score()
        assert abs(score - 0.8) < 0.001

    def test_composite_score_custom_weights(self):
        fv = FitnessVector(values={"a": 1.0, "b": 0.0})
        score = fv.composite_score(weights={"a": 2.0, "b": 1.0})
        assert abs(score - 2.0 / 3.0) < 0.001

    def test_distance(self):
        a = FitnessVector(values={"x": 0.0, "y": 0.0})
        b = FitnessVector(values={"x": 1.0, "y": 0.0})
        assert abs(a.distance(b) - 1.0) < 0.001

    def test_dominance(self):
        a = FitnessVector(values={"x": 0.9, "y": 0.8, "z": 0.7})
        b = FitnessVector(values={"x": 0.5, "y": 0.6, "z": 0.7})
        assert a.dominates(b)

    def test_delta(self):
        a = FitnessVector(values={"x": 0.8, "y": 0.6})
        b = FitnessVector(values={"x": 0.5, "y": 0.9})
        d = a.delta(b)
        assert abs(d.get("x") - 0.3) < 0.001
        assert abs(d.get("y") - (-0.3)) < 0.001

    def test_zero(self):
        fv = FitnessVector.zero(("a", "b", "c"))
        assert fv.get("a") == 0.0
        assert fv.dimension_count == 3
