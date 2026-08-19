"""R2.10.31.1 — Calibration: the baseline everything else in Phase 31 is
measured against.

Calibration is a measurement phase, not a certification: it establishes the
reference distribution and proves the campaign pipeline is deterministic
and fully provenanced at the 26-intent scale. The verdict is
``READY_FOR_31_2``, never ``CERTIFIED`` — 31.5 earns the claim.
"""
import pytest

from tiannara.application.campaign.calibration import (
    CalibrationHarness,
    CalibrationReport,
    CalibrationVerdict,
    baseline_to_payload,
)
from tiannara.application.campaign.corpus import ProjectCategory
from tiannara.application.campaign.failure_taxonomy import FailureCategory

from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


class CalibrationReadinessHarness:
    """31.1 calibration over the frozen R2.10.9 campaign wiring (same
    corpus, same seed derivation, same declared stub)."""

    def __init__(self) -> None:
        self._base = CampaignReadinessHarness()
        self.calibration = CalibrationHarness(
            self._base.harness, self._base.corpus, self._base.ledger
        )
        self.config = self._base.config
        self._report: CalibrationReport | None = None

    def run(self) -> CalibrationReport:
        if self._report is None:
            self._report = self.calibration.run(self.config)
        return self._report

    def run_fresh(self) -> CalibrationReport:
        return self.calibration.run(self.config)

    def matrix_summary(self):
        return self._base.matrix_summary()

    def recipe_isr_hash(self):
        return self._base.recipe_isr_hash()


@pytest.fixture(scope="module")
def calibration_harness() -> CalibrationReadinessHarness:
    return CalibrationReadinessHarness()


def test_baseline_established_across_all_categories(calibration_harness):
    report = calibration_harness.run()
    assert set(report.baseline.per_category) == set(ProjectCategory)
    assert report.baseline.total_intents == 26


def test_deterministic_replay_across_two_runs(calibration_harness):
    assert calibration_harness.run().deterministic_replay_verified is True


def test_complete_provenance_for_every_successful_outcome(calibration_harness):
    assert calibration_harness.run().provenance_complete is True


def test_failures_fully_classified_no_silent_unknowns(calibration_harness):
    assert calibration_harness.run().failures_fully_classified is True


def test_failure_distribution_is_diagnosable(calibration_harness):
    """Failures are broken down by taxonomy class, not reduced to a count."""
    report = calibration_harness.run()
    if report.baseline.total_failure > 0:
        assert (
            sum(report.baseline.per_failure_class.values())
            == report.baseline.total_failure
        )


def test_calibration_verdict_reflects_readiness(calibration_harness):
    assert (
        calibration_harness.run().calibration_verdict
        is CalibrationVerdict.READY_FOR_31_2
    )


def test_calibration_is_measurement_not_certification(calibration_harness):
    """The verdict space has no CERTIFIED — calibration earns 31.2, not the
    claim."""
    assert not hasattr(CalibrationVerdict, "CERTIFIED")


def test_calibration_report_enters_ledger(calibration_harness):
    report = calibration_harness.run()
    assert report.calibration_event_ref is not None
    assert report.calibration_event_ref == "calibration-dry-run-1"
    assert calibration_harness._base.ledger.verify_event_chain() is True


def test_calibration_does_not_disturb_the_substrate(calibration_harness):
    """Calibration measures; it adds no semantics and moves no matrix row."""
    assert calibration_harness.matrix_summary() == (12, 18, 0, 0)
    assert calibration_harness.recipe_isr_hash() == RECIPE_HASH


def test_calibration_declares_the_stub_limitation(calibration_harness):
    """A calibration over stubbed derivations is a calibration of the stub —
    the report records the limitation rather than hiding it."""
    report = calibration_harness.run()
    assert report.declared_assumptions
    assert any("declared stub" in a for a in report.declared_assumptions)


def test_baseline_reproducible_across_harness_invocations(calibration_harness):
    """Two full calibration runs yield the same baseline distribution."""
    r1 = calibration_harness.run_fresh()
    r2 = calibration_harness.run_fresh()
    assert r1.baseline.total_success == r2.baseline.total_success
    assert r1.baseline.total_failure == r2.baseline.total_failure
    assert r1.baseline.per_failure_class == r2.baseline.per_failure_class


def test_baseline_payload_is_json_safe(calibration_harness):
    """The ledger payload is serializable — the ledger never imports the
    campaign package."""
    import json

    payload = baseline_to_payload(calibration_harness.run().baseline)
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped["total_intents"] == 26
    assert round_tripped["total_success"] == 26
    assert set(round_tripped["per_category"]) == {
        category.value for category in ProjectCategory
    }
    assert round_tripped["per_failure_class"] == {}