"""Shared fixtures for the test suite.

Tier A (fast, default) — `python -m pytest`:
  Shares a single session-scoped ``CampaignReadinessHarness`` and a single
  calibrated wiring so duplicate 63s ``dry_run()`` / ~43s ``calibration.run()``
  calls are not repeated across files.

Tier C (certification, explicit) — `python -m pytest -m certification`:
  The Phase 31 certification harness produces calibration + matrix + taxonomy
  + scale-ramp evidence ONCE on a single shared ledger as an immutable bundle,
  then consumes it. This removes the redundant evidence regeneration that made
  31.4 + 31.5 take ~46 minutes when each regenerated the same campaign work.
"""
import pytest


@pytest.fixture(scope="session")
def campaign_readiness():
    """Session-scoped ``CampaignReadinessHarness`` — created once, shared by
    all Tier A tests that need the base campaign wiring."""
    from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

    return CampaignReadinessHarness()


@pytest.fixture(scope="session")
def calibrated_wiring(campaign_readiness):
    """Session-scoped ``(base, calibration_report)`` — created once, shared
    by Tier A Phase 31 test files that need a calibrated campaign harness."""
    from tiannara.application.campaign.calibration import CalibrationHarness

    base = campaign_readiness
    calibration = CalibrationHarness(
        base.harness, base.corpus, base.ledger
    ).run(base.config)
    return base, calibration


# -- Tier C: Phase 31 evidence bundle ---------------------------------------


@pytest.fixture(scope="session")
def phase31_base():
    """The single session-scoped base harness whose ledger accumulates ALL
    Phase 31 evidence (calibration, matrix, taxonomy, scale ramp) so the
    certification can verify one intact chain."""
    from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

    return CampaignReadinessHarness()


@pytest.fixture(scope="session")
def phase31_calibration(phase31_base):
    from tiannara.application.campaign.calibration import CalibrationHarness

    return CalibrationHarness(
        phase31_base.harness,
        phase31_base.corpus,
        phase31_base.ledger,
    ).run(phase31_base.config)


@pytest.fixture(scope="session")
def phase31_matrix(phase31_base, phase31_calibration):
    from tiannara.application.campaign.backend_matrix import MatrixHarness

    return MatrixHarness(
        intent_pipeline=phase31_base.intent_pipeline,
        registry=phase31_base.registry,
        evaluator=phase31_base.evaluator,
        verifier=phase31_base.verifier,
        conformance_registry=phase31_base.conformance_registry,
        ledger=phase31_base.ledger,
        declared_assumptions=phase31_calibration.declared_assumptions,
    ).run(phase31_base.corpus, phase31_base.config)


@pytest.fixture(scope="session")
def phase31_taxonomy(phase31_base, phase31_calibration):
    from tiannara.application.campaign.failure_taxonomy_validation import (
        FailureInjector,
        INJECTION_ASSUMPTIONS,
        TaxonomyClassifier,
        TaxonomyValidationHarness,
    )

    injector = FailureInjector(
        intent_pipeline=phase31_base.intent_pipeline,
        registry=phase31_base.registry,
        evaluator=phase31_base.evaluator,
        verifier=phase31_base.verifier,
        conformance_registry=phase31_base.conformance_registry,
        ledger=phase31_base.ledger,
    )
    return TaxonomyValidationHarness(
        classifier=TaxonomyClassifier(),
        injector=injector,
        ledger=phase31_base.ledger,
        declared_assumptions=(
            phase31_calibration.declared_assumptions + INJECTION_ASSUMPTIONS
        ),
    ).run(
        phase31_base.corpus,
        ("react", "fastapi", "postgres", "terraform",
         "cicd", "pytest", "markdown"),
        phase31_base.config,
    )


@pytest.fixture(scope="session")
def phase31_ramp(phase31_base, phase31_calibration):
    from tiannara.application.campaign.failure_taxonomy_validation import (
        TaxonomyClassifier,
    )
    from tiannara.application.campaign.scale_ramp import (
        CorpusBuilder,
        ScaleRampHarness,
        SCALE_LEVELS,
    )
    from tests.test_r29_31_4_scale_ramp import RERUN_SUBSET

    return ScaleRampHarness(
        campaign_harness=phase31_base.harness,
        intent_pipeline=phase31_base.intent_pipeline,
        registry=phase31_base.registry,
        evaluator=phase31_base.evaluator,
        verifier=phase31_base.verifier,
        conformance_registry=phase31_base.conformance_registry,
        ledger=phase31_base.ledger,
        corpus_builder=CorpusBuilder(phase31_base.corpus),
        taxonomy_classifier=TaxonomyClassifier(),
        rerun_subset=RERUN_SUBSET,
        declared_assumptions=phase31_calibration.declared_assumptions,
        scale_levels=SCALE_LEVELS,
        reachable_top=500,
        level_budget_seconds=300,
    ).run(phase31_base.config)


@pytest.fixture(scope="session")
def phase31_evidence(
    phase31_base,
    phase31_calibration,
    phase31_matrix,
    phase31_taxonomy,
    phase31_ramp,
):
    from tiannara.application.campaign.certification import CertificationEvidence

    return CertificationEvidence(
        phase31_calibration,
        phase31_matrix,
        phase31_taxonomy,
        phase31_ramp,
    )
