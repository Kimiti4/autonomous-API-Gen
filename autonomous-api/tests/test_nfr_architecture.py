"""Tests for Bucket 3.10 architecture-level NFR reasoning."""

import pytest

from app.engine.nfr_architecture import (
    NFRArchitectureEngine,
    NFRConstraint,
    NFRMeasurement,
)


def engine():
    return NFRArchitectureEngine(
        project_id="p1",
        constraints=[
            NFRConstraint("SEC-1", "security", "security score", 0.9, "mandatory", "min"),
            NFRConstraint("PERF-1", "performance", "latency budget", 200, "mandatory", "max"),
            NFRConstraint("COST-1", "cost", "cost ceiling", 100, "mandatory", "max"),
            NFRConstraint("OPS-1", "operability", "operability", 0.8, "advisory", "min"),
        ],
    )


def test_candidate_is_admissible_only_when_mandatory_constraints_have_current_passing_evidence():
    result = engine().assess(
        "arch-A",
        [
            NFRMeasurement("SEC-1", 0.95, "E-SEC"),
            NFRMeasurement("PERF-1", 150, "E-PERF"),
            NFRMeasurement("COST-1", 80, "E-COST"),
            NFRMeasurement("OPS-1", 0.7, "E-OPS"),
        ],
    )

    assert result.admissible
    assert result.violated_constraint_ids == ()
    assert result.advisory_constraint_ids == ("OPS-1",)


def test_mandatory_violation_blocks_candidate():
    result = engine().assess(
        "arch-B",
        [
            NFRMeasurement("SEC-1", 0.7, "E-SEC"),
            NFRMeasurement("PERF-1", 150, "E-PERF"),
            NFRMeasurement("COST-1", 80, "E-COST"),
            NFRMeasurement("OPS-1", 0.9, "E-OPS"),
        ],
    )

    assert not result.admissible
    assert set(result.violated_constraint_ids) == {"SEC-1", "PERF-1"}


def test_missing_or_stale_mandatory_evidence_blocks_admission():
    result = engine().assess(
        "arch-C",
        [
            NFRMeasurement("SEC-1", 0.99, "E-SEC", current=True),
            NFRMeasurement("PERF-1", 300, "E-PERF", current=False),
            NFRMeasurement("COST-1", 90, "E-COST", current=True),
        ],
    )

    assert not result.admissible
    assert result.insufficient_evidence_ids == ("PERF-1",)


def test_direction_is_explicit():
    result = NFRArchitectureEngine(
        project_id="p1",
        constraints=[
            NFRConstraint("C", "cost", "maximum cost", 100, "mandatory", "max"),
        ],
    ).assess("arch", [NFRMeasurement("C", 99, "E")])

    assert result.admissible


def test_duplicate_measurements_fail_closed():
    with pytest.raises(ValueError, match="duplicate-measurement"):
        engine().assess(
            "arch",
            [
                NFRMeasurement("SEC-1", 0.9, "E1"),
                NFRMeasurement("SEC-1", 0.95, "E2"),
            ],
        )


def test_deterministic_assessment_digest():
    measurements = [
        NFRMeasurement("SEC-1", 0.95, "E1"),
        NFRMeasurement("PERF-1", 180, "E2"),
        NFRMeasurement("COST-1", 90, "E3"),
        NFRMeasurement("OPS-1", 0.9, "E4"),
    ]
    a = engine().assess("arch", measurements)
    b = engine().assess("arch", reversed(measurements))

    assert a == b
    assert len(a.digest) == 64
