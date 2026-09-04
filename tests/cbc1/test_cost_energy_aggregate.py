"""Test the wave-level cost/energy aggregate computation.

The aggregate is computed by `_compute_cost_energy_aggregate(trials)` in
`certification.campaign.campaign_b`. This test exercises the function
directly with synthetic trial lists, avoiding the B0 substrate run which
requires real Docker (and would race with an active B3 wave).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from certification.core.metrics import compute
from certification.core.trial import (
    StageEvidence, Trial, TrialStage, TrialMetrics,
)


def _stage_evidence(stage, duration_s=10.0, peak=""):
    return StageEvidence(
        stage=stage, passed=True,
        started_at="2026-09-04T00:00:00Z",
        completed_at="2026-09-04T00:00:30Z",
        logs_hash="x",
        duration_s=duration_s,
        peak_resource=peak,
    )


def _make_trial(backend, wall_clock_total_s, cost_efficiency, peak_cpu=0.0, peak_mem=0.0):
    """Build a synthetic Trial with a metrics object whose cost/energy
    fields are pre-set to the given values."""
    stages = [TrialStage.BUILD, TrialStage.TEST, TrialStage.DEPLOY, TrialStage.RUNTIME, TrialStage.DESTROY]
    by_stage = {s: _stage_evidence(s, duration_s=wall_clock_total_s / 5) for s in stages}
    m = compute(
        repo_files_count=10,
        stages={s: True for s in stages},
        structural_passed=True, test_passed=True, runtime_passed=True,
        files={}, stage_evidence=list(by_stage.values()),
    )
    # Force the cost/energy fields for deterministic aggregate values
    op = dict(m.operational_correctness)
    op["wall_clock_total_s"] = wall_clock_total_s
    op["peak_cpu_pct"] = peak_cpu
    op["peak_mem_mib"] = peak_mem
    m = m.model_copy(update={
        "operational_correctness": op,
        "cost_efficiency": cost_efficiency,
    })
    return Trial(
        trial_id=f"trial-{backend}-{wall_clock_total_s}",
        intent="i", category="c", novelty_class="template",
        requirement_graph_hash="r", genome_hash="g", isr_revision_id="rev",
        backend=backend, backend_class="behavioral", backend_version="1",
        compiler_version="1.4.0", repo_hash="repo", corpus_hash="corpus",
        stages=list(by_stage.values()), metrics=m, verdict="CERTIFIED",
    )


def test_aggregate_per_backend_means():
    """The aggregate computes mean wall-clock, mean cost-efficiency, and
    peak resource per backend."""
    from certification.campaign.campaign_b import _compute_cost_energy_aggregate
    trials = [
        _make_trial("python-fastapi", wall_clock_total_s=30.0, cost_efficiency=0.67, peak_cpu=50.0, peak_mem=200.0),
        _make_trial("python-fastapi", wall_clock_total_s=60.0, cost_efficiency=0.5, peak_cpu=80.0, peak_mem=300.0),
        _make_trial("rust-axum", wall_clock_total_s=90.0, cost_efficiency=0.4, peak_cpu=70.0, peak_mem=250.0),
    ]
    agg = _compute_cost_energy_aggregate(trials)
    assert "by_backend" in agg
    by_b = agg["by_backend"]
    assert set(by_b.keys()) == {"python-fastapi", "rust-axum"}
    py = by_b["python-fastapi"]
    assert py["trial_count"] == 2
    assert py["mean_wall_clock_s"] == pytest.approx(45.0)  # (30+60)/2
    assert py["mean_cost_efficiency"] == pytest.approx(0.585)  # (0.67+0.5)/2
    assert py["peak_cpu_pct_max"] == pytest.approx(80.0)  # max(50, 80)
    assert py["peak_mem_mib_max"] == pytest.approx(300.0)  # max(200, 300)
    rust = by_b["rust-axum"]
    assert rust["trial_count"] == 1
    assert rust["mean_wall_clock_s"] == pytest.approx(90.0)
    assert rust["mean_cost_efficiency"] == pytest.approx(0.4)
    assert agg["wall_clock_reference_s"] == 60.0


def test_aggregate_handles_seed_trial_without_metrics():
    """Seed trials (SimpleNamespace from resume) have no metrics.
    They contribute to trial_count but not to cost/energy sums."""
    from certification.campaign.campaign_b import _compute_cost_energy_aggregate
    import types
    seed = types.SimpleNamespace(backend="python-fastapi", verdict="CERTIFIED")
    real = _make_trial("python-fastapi", wall_clock_total_s=30.0, cost_efficiency=0.67)
    trials = [seed, real]
    agg = _compute_cost_energy_aggregate(trials)
    py = agg["by_backend"]["python-fastapi"]
    assert py["trial_count"] == 2
    # mean uses only the real trial (the seed has no metrics)
    assert py["mean_wall_clock_s"] == pytest.approx(30.0)
    assert py["mean_cost_efficiency"] == pytest.approx(0.67)


def test_aggregate_three_independent_dimensions_preserved():
    """mean wall-clock, mean cost-efficiency, peak resource are SEPARATE
    fields. No single aggregate score is emitted (master prompt §46)."""
    from certification.campaign.campaign_b import _compute_cost_energy_aggregate
    trials = [
        _make_trial("python-fastapi", wall_clock_total_s=30.0, cost_efficiency=0.67, peak_cpu=50.0, peak_mem=200.0),
    ]
    agg = _compute_cost_energy_aggregate(trials)
    py = agg["by_backend"]["python-fastapi"]
    # Each is a separate field
    assert "mean_wall_clock_s" in py
    assert "mean_cost_efficiency" in py
    assert "peak_cpu_pct_max" in py
    assert "peak_mem_mib_max" in py
    # No single aggregate score
    assert "score" not in py
    assert "aggregate" not in py


def test_aggregate_empty_trial_list():
    """Empty input is honest: empty per_backend dict, no division by zero."""
    from certification.campaign.campaign_b import _compute_cost_energy_aggregate
    agg = _compute_cost_energy_aggregate([])
    assert agg["by_backend"] == {}
    assert agg["wall_clock_reference_s"] == 60.0


def test_aggregate_note_explains_no_collapse():
    """The `note` field documents the no-aggregate-score invariant
    and the Pareto-dominance ranking primitive."""
    from certification.campaign.campaign_b import _compute_cost_energy_aggregate
    agg = _compute_cost_energy_aggregate([])
    assert "Pareto" in agg["note"]
    assert "no" in agg["note"].lower() or "independent" in agg["note"].lower()
