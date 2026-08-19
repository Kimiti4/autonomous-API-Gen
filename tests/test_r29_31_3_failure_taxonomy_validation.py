"""R2.10.31.3 — Failure taxonomy validation: every deviation can be
correctly explained, and the explanation is grounded in evidence, not
rationalization.

Each of the five failure classes is INDUCED as a real execution condition;
the classifier derives a disposition from the evidence alone. The harness
knows what it induced; the classifier knows only the evidence — the gap
between those two is exactly what is validated.
"""
import ast
import inspect
import textwrap

import pytest

from tiannara.application.campaign.calibration import CalibrationHarness
from tiannara.application.campaign.failure_taxonomy import (
    FailureCategory,
)
from tiannara.application.campaign.failure_taxonomy_validation import (
    FailureInjector,
    FailureTaxonomyClass,
    TaxonomyClassifier,
    TaxonomyValidationHarness,
    TaxonomyVerdict,
    failure_category_map,
)

from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


class TaxonomyReadinessHarness:
    """31.3 over the frozen R2.10.9 wiring, with the 31.1 declared-stub
    assumption carried from the recorded calibration report."""

    def __init__(self) -> None:
        self._base = CampaignReadinessHarness()
        calibration = CalibrationHarness(
            self._base.harness, self._base.corpus, self._base.ledger
        )
        self.calibration_report = calibration.run(self._base.config)
        self.classifier = TaxonomyClassifier()
        self.injector = FailureInjector(
            intent_pipeline=self._base.intent_pipeline,
            registry=self._base.registry,
            evaluator=self._base.evaluator,
            verifier=self._base.verifier,
            conformance_registry=self._base.conformance_registry,
            ledger=self._base.ledger,
        )
        self.validation = TaxonomyValidationHarness(
            classifier=self.classifier,
            injector=self.injector,
            ledger=self._base.ledger,
            declared_assumptions=(
                self.calibration_report.declared_assumptions
                + self.injector_declared_assumptions()
            ),
        )
        self._report = None

    def injector_declared_assumptions(self) -> tuple[str, ...]:
        from tiannara.application.campaign.failure_taxonomy_validation import (
            INJECTION_ASSUMPTIONS,
        )

        return INJECTION_ASSUMPTIONS

    def run(self):
        if self._report is None:
            self._report = self.validation.run(
                self._base.corpus,
                ("react", "fastapi", "postgres", "terraform",
                 "cicd", "pytest", "markdown"),
                self._base.config,
            )
        return self._report

    def inject_infrastructure_causing_verification_failure(self):
        """A resource exhaustion that ALSO presents verification evidence:
        the classifier must read the root cause, not the symptom."""
        intent = self._base.corpus.intents[0]
        observation = self.injector.inject_infrastructure(intent, "fastapi")
        return observation

    def inject_genuine_artifact_defect(self):
        intent = self._base.corpus.intents[0]
        return self.injector.inject_generated_software_defect(
            intent, "fastapi"
        )

    def matrix_summary(self):
        return self._base.matrix_summary()

    def recipe_isr_hash(self):
        return self._base.recipe_isr_hash()


@pytest.fixture(scope="module")
def validation_harness() -> TaxonomyReadinessHarness:
    return TaxonomyReadinessHarness()


def test_each_class_exercised_with_real_evidence(validation_harness):
    report = validation_harness.run()
    induced = {c.induced_class for c in report.cases}
    assert induced == set(FailureTaxonomyClass)


def test_classifier_correct_for_every_induced_class(validation_harness):
    assert validation_harness.run().all_correct is True


def test_no_conflation_across_classes(validation_harness):
    assert validation_harness.run().no_conflation is True


def test_infrastructure_root_cause_not_symptom(validation_harness):
    """A resource exhaustion that causes a verification failure is
    classified as INFRASTRUCTURE (root cause), never GENERATED_SOFTWARE
    (symptom)."""
    observation = (
        validation_harness.inject_infrastructure_causing_verification_failure()
    )
    disposition = validation_harness.classifier.classify(observation)
    assert disposition.class_ is FailureTaxonomyClass.INFRASTRUCTURE


def test_genuine_defect_not_hidden_behind_environment(validation_harness):
    """A genuine artifact defect with no resource cause is
    GENERATED_SOFTWARE, never laundered into INFRASTRUCTURE."""
    observation = validation_harness.inject_genuine_artifact_defect()
    disposition = validation_harness.classifier.classify(observation)
    assert disposition.class_ is FailureTaxonomyClass.GENERATED_SOFTWARE


def test_classifier_reads_evidence_not_outcome(validation_harness):
    """Structural: the classifier has no access to compile success — it
    cannot rationalize, because it cannot see the outcome, only the
    evidence."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(TaxonomyClassifier.classify)))
    source = ast.unparse(tree).lower()
    assert "succeeded" not in source
    assert "compile_success" not in source
    assert "passed" not in source


def test_disposition_is_auditable_to_its_evidence(validation_harness):
    """Every disposition names the evidence it was derived from and the
    observation it came from — the certification measures reality and can
    show its work."""
    report = validation_harness.run()
    for case in report.cases:
        assert case.disposition.evidence_basis
        assert case.disposition.observation_ref


def test_every_case_chain_resolvable(validation_harness):
    validation_harness.run()
    assert validation_harness._base.ledger.verify_event_chain() is True


def test_declared_stub_assumption_propagates(validation_harness):
    """31.3 runs over the same declared-stub pipeline 31.1 calibrated and
    31.2 multiplied; the premise must carry forward, never lapse."""
    assert validation_harness.run().declared_assumptions


def test_verdict_is_readiness_not_certification(validation_harness):
    report = validation_harness.run()
    assert report.verdict is TaxonomyVerdict.READY_FOR_31_4
    assert not hasattr(TaxonomyVerdict, "CERTIFIED")


def test_matrix_identity_unchanged(validation_harness):
    assert validation_harness.matrix_summary() == (12, 18, 0, 0)
    assert validation_harness.recipe_isr_hash() == RECIPE_HASH


def test_taxonomy_maps_onto_r29_10_9_categories(validation_harness):
    """The five 31.3 classes and the eight R2.10.9 FailureCategory values
    are one coherent system: infrastructure classes stay infrastructure,
    contract violations stay contract, verification failures are
    generated-software, derivation/evolution/compile failures are
    campaign-harness."""
    assert (
        failure_category_map(FailureCategory.RESOURCE_EXHAUSTION)
        is FailureTaxonomyClass.INFRASTRUCTURE
    )
    assert (
        failure_category_map(FailureCategory.TIMEOUT)
        is FailureTaxonomyClass.INFRASTRUCTURE
    )
    assert (
        failure_category_map(FailureCategory.COMPILATION_CONTRACT_VIOLATION)
        is FailureTaxonomyClass.CONTRACT_CONFORMANCE
    )
    assert (
        failure_category_map(FailureCategory.VERIFICATION_FAILED)
        is FailureTaxonomyClass.GENERATED_SOFTWARE
    )
    for category in (
        FailureCategory.INTENT_DERIVATION_FAILED,
        FailureCategory.EVOLUTION_HALTED,
        FailureCategory.COMPILATION_FAILED,
        FailureCategory.UNKNOWN,
    ):
        assert (
            failure_category_map(category)
            is FailureTaxonomyClass.CAMPAIGN_HARNESS
        )


def test_induced_failures_are_real_not_synthetic_labels(validation_harness):
    """Each injection captures REAL execution evidence: the actual
    exception text, the real verifier's actual failure reasons."""
    intent = validation_harness._base.corpus.intents[0]
    infrastructure = validation_harness.injector.inject_infrastructure(
        intent, "fastapi"
    )
    assert "resource budget exceeded" in infrastructure.error_evidence

    generated = validation_harness.injector.inject_generated_software_defect(
        intent, "fastapi"
    )
    assert "artifact_modified" in generated.error_evidence

    contract = validation_harness.injector.inject_contract_violation(
        intent, "fastapi"
    )
    assert "silently_discarded" in contract.error_evidence