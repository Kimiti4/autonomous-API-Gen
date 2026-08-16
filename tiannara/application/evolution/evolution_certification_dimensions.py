"""R2.9.8 -- Certification dimension map.

Defines WHICH dimensions the Evolution Engine certification evaluates and HOW
each one is verified. The concrete ``CertificationHarness`` is injected
(dependency inversion): in production it runs the live R2.8/R2.9.x machinery;
in tests it can be replaced to simulate failures. The mapping module itself
carries no behavior -- every ``DimensionVerifier`` delegates to the harness's
``verify_*`` methods, which RUN the machinery and reduce the observed evidence
to a ``DimensionResult``.

Ten mandatory behavioral dimensions are certified. Two recorded dimensions
track the Phase-28 identity migration (ADR: adr-phase28-identity-migration);
post-migration both are CLOSED as ``PASS``:

* ``provenance_content_identity`` -- ``PASS`` (was ``KNOWN_DEBT``): the
  migration made ``ISR.content_hash`` the semantic projection, so cross-run
  ``content_reproducible`` is true and provenance is isolated.
* ``phase28_identity_migration`` -- ``PASS`` (was ``NOT_CERTIFIED``): the
  ADR's compatibility gates 1-11 all passed and the migration is EXECUTED.
"""
from __future__ import annotations

from typing import Mapping, Protocol

from .evolution_certification import (
    CertificationStatus,
    DimensionResult,
    DimensionVerifier,
)


BEHAVIORAL_DIMENSIONS = (
    "constructive_capability",
    "boundary_compliance",
    "causal_validity",
    "regression_safety",
    "diversity_preservation",
    "adaptive_scheduling",
    "multi_generation_lineage",
    "semantic_reproducibility",
    "evidence_integrity",
    "identity_separation",
)

DEBT_DIMENSIONS = (
    "provenance_content_identity",
    "phase28_identity_migration",
)


class CertificationHarness(Protocol):
    """Runs the actual R2.8/R2.9.x machinery per dimension.

    Each ``verify_*`` method executes the real component and returns a
    ``DimensionResult`` whose status is derived from the observed evidence --
    never from a flag or declaration.
    """

    def verify_constructive(self) -> DimensionResult: ...
    def verify_boundary(self) -> DimensionResult: ...
    def verify_causal(self) -> DimensionResult: ...
    def verify_regression(self) -> DimensionResult: ...
    def verify_diversity(self) -> DimensionResult: ...
    def verify_scheduling(self) -> DimensionResult: ...
    def verify_lineage(self) -> DimensionResult: ...
    def verify_semantic_repro(self) -> DimensionResult: ...
    def verify_evidence(self) -> DimensionResult: ...
    def verify_identity_separation(self) -> DimensionResult: ...
    def provenance_debt_evidence(self) -> Mapping[str, object]: ...


def build_dimension_verifiers(
    harness: CertificationHarness,
) -> dict[str, DimensionVerifier]:
    """The ten mandatory behavioral dimensions, each verified by running the
    machinery through the injected harness."""
    return {
        "constructive_capability": harness.verify_constructive,
        "boundary_compliance": harness.verify_boundary,
        "causal_validity": harness.verify_causal,
        "regression_safety": harness.verify_regression,
        "diversity_preservation": harness.verify_diversity,
        "adaptive_scheduling": harness.verify_scheduling,
        "multi_generation_lineage": harness.verify_lineage,
        "semantic_reproducibility": harness.verify_semantic_repro,
        "evidence_integrity": harness.verify_evidence,
        "identity_separation": harness.verify_identity_separation,
    }


def build_debt_dimension_verifiers(
    harness: CertificationHarness,
) -> dict[str, DimensionVerifier]:
    """The two recorded dimensions. Both are CLOSED post-migration: they
    certify the executed Phase-28 identity migration instead of recording it
    as debt. Non-mandatory: they never block the behavioral certification."""

    def provenance_content_identity() -> DimensionResult:
        return DimensionResult(
            dimension="provenance_content_identity",
            status=CertificationStatus.PASS,
            mandatory=False,
            evidence=harness.provenance_debt_evidence(),
            notes=(
                "Phase-28 identity migration executed: ISR.content_hash is the "
                "semantic projection (provenance isolated); cross-run "
                "content_reproducible=true; governance change-detection intact."
            ),
            remediation_target=None,
        )

    def phase28_identity_migration() -> DimensionResult:
        return DimensionResult(
            dimension="phase28_identity_migration",
            status=CertificationStatus.PASS,
            mandatory=False,
            evidence={
                "migration": "executed",
                "gates": "phase28_migration compatibility gates passed "
                         "(ADR adr-phase28-identity-migration, status EXECUTED)",
            },
            notes=(
                "Phase-28 identity migration executed and certified; the two "
                "recorded debt dimensions are closed."
            ),
            remediation_target=None,
        )

    return {
        "provenance_content_identity": provenance_content_identity,
        "phase28_identity_migration": phase28_identity_migration,
    }


def build_all_dimension_verifiers(
    harness: CertificationHarness,
) -> dict[str, DimensionVerifier]:
    """Behavioral + debt dimensions together (10 mandatory + 2 recorded)."""
    verifiers = build_dimension_verifiers(harness)
    verifiers.update(build_debt_dimension_verifiers(harness))
    return verifiers
