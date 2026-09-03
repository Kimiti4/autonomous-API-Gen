"""R2.10.31.4 — the scale ramp: does the envelope hold as workload grows?

31.1-31.3 established the semantic contract at small scale; 31.4 observes
whether the properties hold as workload increases, up to a MEASURED
boundary. The ten gates are evaluated at every level; the ramp stops on a
gate failure, the declared reachable top, or a real resource signal — and
reports the envelope. The verdict is READY_FOR_31_5, never CERTIFIED:
31.4 earns the certification statement, 31.5 makes it.
"""
import dataclasses

import pytest

from tiannara.application.campaign.calibration import CalibrationHarness
from tiannara.application.campaign.corpus import GenerationCorpus
from tiannara.application.campaign.failure_taxonomy_validation import (
    TaxonomyClassifier,
)
from tiannara.application.campaign.scale_ramp import (
    CorpusBuilder,
    CorpusGrowthStrategy,
    DeterministicRerunSubset,
    SCALE_LEVELS,
    ScaleLevelResult,
    ScaleRampGate,
    ScaleRampHarness,
    ScaleRampVerdict,
)

from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

pytestmark = pytest.mark.certification

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


@pytest.fixture(scope="module")
def base_wiring(calibrated_wiring):
    base, calibration = calibrated_wiring
    return base, calibration


def make_ramp(
    base,
    calibration_report,
    *,
    campaign_id,
    corpus_builder,
    budget_seconds=300,
):
    ramp = ScaleRampHarness(
        campaign_harness=base.harness,
        intent_pipeline=base.intent_pipeline,
        registry=base.registry,
        evaluator=base.evaluator,
        verifier=base.verifier,
        conformance_registry=base.conformance_registry,
        ledger=base.ledger,
        corpus_builder=corpus_builder,
        taxonomy_classifier=TaxonomyClassifier(),
        rerun_subset=RERUN_SUBSET,
        declared_assumptions=calibration_report.declared_assumptions,
        scale_levels=SCALE_LEVELS,
        corpus_growth_strategy=CorpusGrowthStrategy.DERIVED_FROM_SEEDS,
        reachable_top=500,
        level_budget_seconds=budget_seconds,
    )
    config = dataclasses.replace(base.config, campaign_id=campaign_id)
    return ScaleProbe(ramp, base, config)


@pytest.fixture(scope="module")
def scale_ramp_harness(phase31_base, phase31_ramp):
    """Consumes the shared Phase 31 scale-ramp evidence instead of re-running
    the expensive 26/100/500 campaign climb."""
    return EvidenceProbe(phase31_ramp, phase31_base)


class DriftingBuilder(CorpusBuilder):
    """A genuinely different problem at scale 100 — the canary must see
    the drift and the ramp must refuse to certify it."""

    def build(self, scale, strategy=CorpusGrowthStrategy.DERIVED_FROM_SEEDS):
        corpus = super().build(scale, strategy)
        if scale == 100:
            intents = list(corpus.intents)
            intents[5] = dataclasses.replace(
                intents[5],
                problem_statement=(
                    "A completely different declared problem at the 100 "
                    "scale."
                ),
            )
            return GenerationCorpus(
                corpus_id=corpus.corpus_id, intents=tuple(intents)
            )
        return corpus


@pytest.fixture(scope="module")
def drift_ramp_harness(base_wiring):
    base, calibration = base_wiring
    return make_ramp(
        base,
        calibration,
        campaign_id="drift-ramp",
        corpus_builder=DriftingBuilder(base.corpus),
    )


@pytest.fixture(scope="module")
def envelope_ramp_harness(base_wiring):
    """The per-level budget is a REAL resource: a declared 1ms budget is
    breached by the real measured duration of the first level — the ramp
    stops and reports the envelope, honestly."""
    base, calibration = base_wiring
    return make_ramp(
        base,
        calibration,
        campaign_id="envelope-probe",
        corpus_builder=CorpusBuilder(base.corpus),
        budget_seconds=0.001,
    )


RERUN_SUBSET = DeterministicRerunSubset(
    subset_id="canary-6",
    intent_ids=(
        "billing-01",
        "workspace-02",
        "procurement-01",
        "accounting-02",
        "retail-bank-01",
        "credit-02",
    ),
)


class ScaleProbe:
    def __init__(self, ramp: ScaleRampHarness, base, config) -> None:
        self._ramp = ramp
        self._base = base
        self._config = config
        self._report = None

    def run(self):
        if self._report is None:
            self._report = self._ramp.run(self._config)
        return self._report

    def matrix_summary(self):
        return self._base.matrix_summary()

    def recipe_isr_hash(self):
        return self._base.recipe_isr_hash()


class EvidenceProbe:
    """A probe over SHARED Phase 31 evidence: it returns the already-produced
    ramp report instead of re-running the expensive campaign ramp."""

    def __init__(self, ramp_report, base) -> None:
        self._report = ramp_report
        self._base = base

    def run(self):
        return self._report

    def matrix_summary(self):
        return self._base.matrix_summary()

    def recipe_isr_hash(self):
        return self._base.recipe_isr_hash()


def test_scale_monotonicity_holds_at_every_level(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.SCALE_MONOTONICITY]
        for level in report.per_level
    )


def test_every_case_receives_exactly_one_disposition(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.FAILURE_RATE_ACCOUNTING]
        for level in report.per_level
    )
    for level in report.per_level:
        assert level.success_count + level.failure_count == level.total_cases


def test_taxonomy_stable_across_scale(scale_ramp_harness):
    """Identical causal evidence maps to the same class regardless of
    scale."""
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.TAXONOMY_STABILITY]
        for level in report.per_level
    )


def test_no_silent_omission_at_scale(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.NO_SILENT_OMISSION]
        for level in report.per_level
    )


def test_ledger_complete_at_scale(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.LEDGER_COMPLETENESS]
        for level in report.per_level
    )


def test_provenance_preserved_at_scale(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.PROVENANCE_PRESERVATION]
        for level in report.per_level
    )


def test_resource_exhaustion_is_infrastructure_not_defect(scale_ramp_harness):
    """Exhaustion is evidence about the envelope, never a campaign
    defect."""
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.RESOURCE_BOUND_HONESTY]
        for level in report.per_level
    )


def test_rerun_subset_stable_at_every_scale(scale_ramp_harness):
    """The canary: the fixed sample yields equivalent semantic outcomes
    at every level."""
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.DETERMINISTIC_RERUN_SUBSET]
        for level in report.per_level
    )


def test_no_cross_intent_contamination_at_scale(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert all(
        level.gates_held[ScaleRampGate.NO_CROSS_INTENT_CONTAMINATION]
        for level in report.per_level
    )


def test_verdict_is_readiness_not_certification(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert report.verdict is ScaleRampVerdict.READY_FOR_31_5
    assert not hasattr(ScaleRampVerdict, "CERTIFIED")


def test_scale_envelope_is_measured_and_declared(scale_ramp_harness):
    """The report names the largest scale at which all ten gates held —
    the envelope is a measurement, not an aspiration."""
    report = scale_ramp_harness.run()
    assert report.scale_envelope > 0
    assert report.per_level[-1].scale == report.scale_envelope


def test_corpus_growth_strategy_declared(scale_ramp_harness):
    """How the corpus grows is a declared assumption, never implicit."""
    report = scale_ramp_harness.run()
    assert report.corpus_growth_strategy is CorpusGrowthStrategy.DERIVED_FROM_SEEDS
    assert any("DERIVED_FROM_SEEDS" in a for a in report.declared_assumptions)


def test_rerun_subset_predeclared(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert report.rerun_subset.subset_id == "canary-6"
    assert report.rerun_subset.intent_ids == RERUN_SUBSET.intent_ids


def test_matrix_identity_unchanged(scale_ramp_harness):
    assert scale_ramp_harness.matrix_summary() == (12, 18, 0, 0)
    assert scale_ramp_harness.recipe_isr_hash() == RECIPE_HASH


def test_reachable_top_declared_not_silent(scale_ramp_harness):
    """Levels 1000/5000 are SCHEDULED but not run — declared in the report
    and in the assumptions, never silently capped."""
    report = scale_ramp_harness.run()
    assert report.reachable_top == 500
    assert 1000 in report.scheduled_levels
    assert 5000 in report.scheduled_levels
    assert report.per_level[-1].scale == 500
    assert any("reachable_top" in a for a in report.declared_assumptions)


def test_failure_exercise_is_declared_not_assumed(scale_ramp_harness):
    """The ramp observed no failures at scale; the report SAYS so rather
    than letting the taxonomy gate masquerade as exercised."""
    report = scale_ramp_harness.run()
    assert all(level.failure_count == 0 for level in report.per_level)
    assert report.taxonomy_exercised is False
    assert all(
        level.gates_held[ScaleRampGate.TAXONOMY_STABILITY]
        for level in report.per_level
    )


def test_envelope_budget_breach_stops_ramp_honestly(envelope_ramp_harness):
    """The per-level budget is a real resource: the declared 1ms budget is
    breached by the real measured duration — the ramp stops, names the
    breach, and still reports the envelope and its verdict honestly."""
    report = envelope_ramp_harness.run()
    assert report.envelope_hit_at == 26
    assert report.envelope_reason is not None
    assert "budget" in report.envelope_reason
    assert report.ramp_complete is False
    assert report.verdict is ScaleRampVerdict.READY_FOR_31_5
    assert len(report.per_level) == 1


def test_verdict_not_ready_when_canary_drifts(drift_ramp_harness):
    """A genuinely different problem at scale 100 changes the canary's
    artifact — determinism degraded, the ramp must refuse readiness."""
    report = drift_ramp_harness.run()
    assert report.verdict is ScaleRampVerdict.NOT_READY
    assert not report.ramp_complete
    failed = [level for level in report.per_level if not all(
        level.gates_held.values()
    )]
    assert failed
    assert failed[0].scale == 100
    assert (
        not failed[0].gates_held[ScaleRampGate.DETERMINISTIC_RERUN_SUBSET]
        or not failed[0].gates_held[ScaleRampGate.SCALE_MONOTONICITY]
    )
    assert report.scale_envelope == 26


def test_scale_ramp_report_enters_ledger(scale_ramp_harness):
    report = scale_ramp_harness.run()
    assert report.ramp_event_ref == "scale-ramp-dry-run-1"
    event = scale_ramp_harness._base.ledger.event_by_ref(report.ramp_event_ref)
    assert event is not None
    assert event.payload["scale_envelope"] == report.scale_envelope
    assert event.payload["scale_ramp_verdict"] == report.verdict.value
    assert len(event.payload["per_level"]) == len(report.per_level)
    assert event.payload["declared_assumptions"]
    assert scale_ramp_harness._base.ledger.verify_event_chain() is True


def test_level_results_are_typed_and_measurable(scale_ramp_harness):
    """The ramp measures real durations and counts — the envelope is a
    measurement, not an aspiration."""
    report = scale_ramp_harness.run()
    for level in report.per_level:
        assert isinstance(level, ScaleLevelResult)
        assert level.duration_ms > 0
        assert level.canary_tally["VERIFIED_COMPILATION"] == 6 * 7
        assert level.canary_invariance is True
        assert level.failure_count == 0
