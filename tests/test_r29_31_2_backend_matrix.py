"""R2.10.31.2 — the backend matrix experiment: coverage and invariance at
matrix scale, not throughput.

26 intents x 7 real backends = 182 cases, each disposed into exactly one of
the five disposition classes. The verdict is READY_FOR_31_3, never
CERTIFIED; a backend that honestly declares UNSUPPORTED semantics is
correct, not failing. The declared-stub assumption calibrated in 31.1 is
mechanically carried into the report, never dropped.
"""
import pytest

from tiannara.application.campaign.backend_matrix import (
    MatrixCase,
    MatrixDisposition,
    MatrixHarness,
    MatrixVerdict,
    SEVEN_BACKENDS,
    unsupported_required,
)
from tiannara.application.campaign.calibration import CalibrationHarness
from tiannara.application.compilation.consumption_contract import (
    CapabilityCoverage,
    CapabilitySupport,
)

from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


class MatrixReadinessHarness:
    """31.2 over the frozen R2.10.9 wiring, with the 31.1 declared-stub
    assumption carried from the recorded calibration report."""

    def __init__(self) -> None:
        self._base = CampaignReadinessHarness()
        calibration = CalibrationHarness(
            self._base.harness, self._base.corpus, self._base.ledger
        )
        self.calibration_report = calibration.run(self._base.config)
        self.matrix = MatrixHarness(
            intent_pipeline=self._base.intent_pipeline,
            registry=self._base.registry,
            evaluator=self._base.evaluator,
            verifier=self._base.verifier,
            conformance_registry=self._base.conformance_registry,
            ledger=self._base.ledger,
            declared_assumptions=(
                self.calibration_report.declared_assumptions
            ),
        )
        self._report = None

    def run(self):
        if self._report is None:
            self._report = self.matrix.run(
                self._base.corpus, self._base.config
            )
        return self._report

    def matrix_summary(self):
        return self._base.matrix_summary()

    def recipe_isr_hash(self):
        return self._base.recipe_isr_hash()


@pytest.fixture(scope="module")
def matrix_harness() -> MatrixReadinessHarness:
    return MatrixReadinessHarness()


def test_all_182_cases_disposed(matrix_harness):
    report = matrix_harness.run()
    assert len(report.cases) == 26 * 7
    assert all(c.disposition is not None for c in report.cases)


def test_every_non_verified_case_is_classified(matrix_harness):
    report = matrix_harness.run()
    for case in report.cases:
        if case.disposition is not MatrixDisposition.VERIFIED_COMPILATION:
            assert case.disposition in (
                MatrixDisposition.SUCCESSFUL_COMPILATION,
                MatrixDisposition.EXPLICITLY_UNSUPPORTED,
                MatrixDisposition.DIAGNOSED_FAILURE,
                MatrixDisposition.INFRASTRUCTURE_FAILURE,
            )


def test_explicit_unsupported_is_legitimate_and_named(matrix_harness):
    """EXPLICITLY_UNSUPPORTED is a terminal disposition — but the
    unsupported semantics must be NAMED, never silent."""
    report = matrix_harness.run()
    for case in report.cases:
        if case.disposition is MatrixDisposition.EXPLICITLY_UNSUPPORTED:
            assert case.unsupported_semantics


def test_cross_backend_invariance_per_intent(matrix_harness):
    assert matrix_harness.run().cross_backend_invariance_held is True


def test_artifacts_diverge_but_source_agrees(matrix_harness):
    """One intent's artifacts differ structurally across backends; their
    semantic source is identical. Divergence of realization with invariance
    of meaning."""
    report = matrix_harness.run()
    for intent_id in {c.intent_id for c in report.cases}:
        compiled = [
            c
            for c in report.cases
            if c.intent_id == intent_id and c.artifact_hash is not None
        ]
        if len(compiled) > 1:
            assert len({c.artifact_hash for c in compiled}) > 1
            assert len({c.isr_hash for c in compiled}) == 1


def test_verified_vs_successful_distinction_survives(matrix_harness):
    """A compilation that succeeds but does not independently verify is NOT
    counted as verified — the R2.10.8 gap stays visible, not averaged
    away."""
    report = matrix_harness.run()
    for case in report.cases:
        if case.disposition is MatrixDisposition.SUCCESSFUL_COMPILATION:
            assert case.verification_verified is False


def test_declared_stub_assumption_propagates(matrix_harness):
    """31.2 runs on the same declared-stub pipeline 31.1 calibrated; the
    assumption must be inherited from the calibration report, not dropped."""
    report = matrix_harness.run()
    assert report.declared_assumptions
    assert report.declared_assumptions == (
        matrix_harness.calibration_report.declared_assumptions
    )


def test_each_case_binds_to_conformance_evidence(matrix_harness):
    """Every case references the backend's R2.10.7 conformance report on
    the chain."""
    report = matrix_harness.run()
    for case in report.cases:
        assert case.conformance_evidence_ref is not None


def test_matrix_report_enters_ledger(matrix_harness):
    report = matrix_harness.run()
    assert report.matrix_event_ref == "matrix-dry-run-1"
    event = matrix_harness._base.ledger.event_by_ref(report.matrix_event_ref)
    assert event is not None
    assert event.payload["case_count"] == 26 * 7
    assert event.payload["declared_assumptions"]
    assert matrix_harness._base.ledger.verify_event_chain() is True


def test_matrix_identity_unchanged(matrix_harness):
    assert matrix_harness.matrix_summary() == (12, 18, 0, 0)
    assert matrix_harness.recipe_isr_hash() == RECIPE_HASH


def test_verdict_reflects_readiness(matrix_harness):
    assert matrix_harness.run().verdict is MatrixVerdict.READY_FOR_31_3


def test_verdict_has_no_certified(matrix_harness):
    """The verdict space has no CERTIFIED — 31.2 earns 31.3, not the Phase
    31 claim."""
    assert not hasattr(MatrixVerdict, "CERTIFIED")


def test_unsupported_decision_is_mechanical_and_named(matrix_harness):
    """The EXPLICITLY_UNSUPPORTED decision is made from the declared
    coverage BEFORE compiling, and the unsupported semantics are named —
    exercised here synthetically, since no 26-intent corpus case is
    all-unsupported on any real backend (each backend realizes at least one
    of the stub's carriers)."""
    required = frozenset(
        {"behavior", "capability", "requirement", "documentation"}
    )
    all_unsupported = tuple(
        CapabilityCoverage(
            capability_id=sid,
            support=CapabilitySupport.UNSUPPORTED,
            note="declared: not realized by this backend",
        )
        for sid in sorted(required)
    )
    named = unsupported_required(required, all_unsupported)
    assert set(named) == required  # every required semantic named

    partially_supported = tuple(
        CapabilityCoverage(
            capability_id=sid,
            support=(
                CapabilitySupport.SUPPORTED
                if sid == "behavior"
                else CapabilitySupport.UNSUPPORTED
            ),
            note="declared",
        )
        for sid in sorted(required)
    )
    assert unsupported_required(required, partially_supported) == tuple(
        sorted(required - {"behavior"})
    )