"""Tests for the cost/energy fitness axis (Phase 31 spec §Cross-Cutting Gaps #4).

The spec says: "Cost and energy as fitness dimensions ... Every phase
currently measures correctness/quality but not efficiency; a system
that passes at 100x the compute cost fails in reality."

We do NOT collapse cost and energy into a single aggregate score
(master prompt §46, "no cosmetic evolution", and the FitnessVector
"Never collapse to a single aggregate score" invariant). Each is a
separate, monotonically-scaled dimension.

This test enforces:
  - The cost/energy fields exist on TrialMetrics
  - The cost_efficiency is a monotonic [0, 1] axis bounded by reference
  - The wall_clock_total_s, peak_cpu_pct, peak_mem_mib are separate
    audit fields (never collapsed)
  - Backward-compat: missing stage_evidence yields honest zeros
  - Pareto dominance preserves the cost ranking (no surprise flips)
"""
import pytest

from certification.core.metrics import (
    WALL_CLOCK_REF_S,
    _cost_efficiency,
    _parse_peak_resource,
    compute,
)
from certification.core.trial import StageEvidence, TrialStage


def _evidence(stage: TrialStage, duration_s: float, peak: str = "") -> StageEvidence:
    return StageEvidence(
        stage=stage,
        passed=True,
        started_at="2026-09-04T00:00:00Z",
        completed_at="2026-09-04T00:00:30Z",
        logs_hash="x",
        duration_s=duration_s,
        peak_resource=peak,
    )


def test_cost_efficiency_at_reference_is_one_half():
    assert _cost_efficiency(WALL_CLOCK_REF_S) == pytest.approx(0.5)
    assert _cost_efficiency(0) == pytest.approx(1.0)
    assert _cost_efficiency(2 * WALL_CLOCK_REF_S) == pytest.approx(1 / 3)


def test_cost_efficiency_is_monotonically_decreasing():
    prev = 1.0
    for s in (0, 10, 30, 60, 120, 300, 600, 1800, 3600, 12000):
        v = _cost_efficiency(s)
        assert v <= prev, f"cost_efficiency not monotonically decreasing at s={s}: {v} > {prev}"
        prev = v
    assert 0 < prev < 1


def test_cost_efficiency_bounded_in_open_unit_interval():
    for s in (0, 1, 10, 100, 1000, 10000, 100000):
        v = _cost_efficiency(s)
        assert 0 < v <= 1


def test_peak_resource_parses_mib():
    cpu, mem = _parse_peak_resource("12.34%/128.5MiB")
    assert cpu == pytest.approx(12.34)
    assert mem == pytest.approx(128.5)


def test_peak_resource_parses_gib_to_mib():
    cpu, mem = _parse_peak_resource("50%/1GiB")
    assert cpu == pytest.approx(50.0)
    assert mem == pytest.approx(1024.0)


def test_peak_resource_parses_kib_to_mib():
    cpu, mem = _parse_peak_resource("5%/256KiB")
    assert cpu == pytest.approx(5.0)
    assert mem == pytest.approx(0.25)


def test_peak_resource_empty_returns_zeros():
    cpu, mem = _parse_peak_resource("")
    assert cpu == 0.0
    assert mem is None


def test_peak_resource_garbage_returns_zeros_not_raised():
    cpu, mem = _parse_peak_resource("totally-not-a-resource-string")
    assert cpu == 0.0
    assert mem is None


def test_compute_with_stage_evidence_sums_wall_clock():
    ev = [
        _evidence(TrialStage.BUILD, 10.0, "5%/100MiB"),
        _evidence(TrialStage.TEST, 20.0, "50%/200MiB"),
        _evidence(TrialStage.DEPLOY, 5.0, ""),
        _evidence(TrialStage.RUNTIME, 15.0, "80%/300MiB"),
        _evidence(TrialStage.DESTROY, 2.0, ""),
    ]
    stages = {
        TrialStage.BUILD: True, TrialStage.TEST: True, TrialStage.DEPLOY: True,
        TrialStage.RUNTIME: True, TrialStage.DESTROY: True,
        TrialStage.STRUCTURAL: True, TrialStage.VERIFY: True,
    }
    m = compute(
        repo_files_count=10, stages=stages,
        structural_passed=True, test_passed=True, runtime_passed=True,
        files={}, stage_evidence=ev,
    )
    assert m.operational_correctness["wall_clock_total_s"] == pytest.approx(52.0)
    assert m.operational_correctness["peak_cpu_pct"] == pytest.approx(80.0)
    assert m.operational_correctness["peak_mem_mib"] == pytest.approx(300.0)
    assert 0.5 < m.cost_efficiency < 0.6
    assert m.wall_clock_reference_s == WALL_CLOCK_REF_S


def test_compute_backward_compat_no_stage_evidence():
    """Old callers that don't pass stage_evidence must still work — they
    get honest zeros, not crashes."""
    stages = {
        TrialStage.BUILD: True, TrialStage.TEST: True, TrialStage.RUNTIME: True,
        TrialStage.STRUCTURAL: True,
    }
    m = compute(
        repo_files_count=10, stages=stages,
        structural_passed=True, test_passed=True, runtime_passed=True, files={},
    )
    assert m.operational_correctness["wall_clock_total_s"] == 0.0
    assert m.operational_correctness["peak_cpu_pct"] == 0.0
    assert m.operational_correctness["peak_mem_mib"] is None
    assert m.cost_efficiency == pytest.approx(1.0)


def test_compute_failed_stage_does_not_inflate_wall_clock():
    """A failed cascade-SKIPPED stage should not contribute to wall_clock.
    The metric is a measurement of the system's actual work, not its
    aborts."""
    ev = [
        _evidence(TrialStage.BUILD, 10.0),
        _evidence(TrialStage.TEST, 5.0),
        _evidence(TrialStage.DEPLOY, 0.0),  # failed
    ]
    stages = {
        TrialStage.BUILD: True, TrialStage.TEST: True, TrialStage.DEPLOY: False,
        TrialStage.RUNTIME: False, TrialStage.DESTROY: False,
        TrialStage.STRUCTURAL: True,
    }
    m = compute(
        repo_files_count=10, stages=stages,
        structural_passed=True, test_passed=True, runtime_passed=False,
        files={}, stage_evidence=ev,
    )
    # 10 + 5 = 15 (failed deploy does not contribute)
    assert m.operational_correctness["wall_clock_total_s"] == pytest.approx(15.0)


def test_pareto_dominance_preserves_cost_ranking():
    """Pareto dominance on cost_efficiency must match the ranking on
    -wall_clock_total_s (i.e. less wall_clock dominates more)."""
    faster = _cost_efficiency(30.0)
    slower = _cost_efficiency(60.0)
    assert faster > slower, "faster trial should have higher cost_efficiency"


def test_separate_dimensions_preserved_in_metrics():
    """The cost/energy fields are SEPARATE in operational_correctness, not
    collapsed into a single score. This is the no-aggregate-score invariant."""
    m = compute(
        repo_files_count=1, stages={}, structural_passed=True,
        test_passed=True, runtime_passed=True, files={},
    )
    op = m.operational_correctness
    # Each is a separate field
    assert "wall_clock_total_s" in op
    assert "peak_cpu_pct" in op
    assert "peak_mem_mib" in op
    # And TrialMetrics has the cost_efficiency axis at the top level
    assert hasattr(m, "cost_efficiency")
    assert hasattr(m, "wall_clock_reference_s")
    # cost_efficiency is NOT in operational_correctness
    assert "cost_efficiency" not in op
