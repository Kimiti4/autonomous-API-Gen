"""R2.9.8 -- Certification dimension map.

Defines WHICH dimensions the Evolution Engine certification evaluates and HOW
each one is verified. The concrete ``CertificationHarness`` is injected
(dependency inversion): in production it runs the live R2.8/R2.9.x machinery;
in tests it can be replaced to simulate failures. The mapping module itself
carries no behavior -- every ``DimensionVerifier`` delegates to the harness's
``verify_*`` methods, which RUN the machinery and reduce the observed evidence
to a ``DimensionResult``.

Ten mandatory behavioral dimensions are certified. Two recorded debt
dimensions are non-mandatory and actionable:

* ``provenance_content_identity`` -- ``KNOWN_DEBT`` with
  ``remediation_target="phase28_identity_migration"`` and the R2.9.7 audit
  evidence (semantic identity is stable and reproducible; the Phase-28
  ``content_hash`` conflates volatile provenance). It never blocks
  certification -- it records the actionable next migration.
* ``phase28_identity_migration`` -- ``NOT_CERTIFIED`` (the migration itself is
  deliberately out of scope for R2.9.8) and, being non-mandatory, also never
  blocks certification.
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
    """The two recorded debt dimensions. Non-mandatory and actionable: they
    record the Phase-28 identity migration as the next step without blocking
    certification of the engine's behavior."""

    def provenance_content_identity() -> DimensionResult:
        return DimensionResult(
            dimension="provenance_content_identity",
            status=CertificationStatus.KNOWN_DEBT,
            mandatory=False,
            evidence=harness.provenance_debt_evidence(),
            notes=(
                "Phase-28 content_hash conflates volatile provenance "
                "(created_at, parent_hash) into the hash; the semantic "
                "identity (R2.9.7 three-identity audit) is stable and "
                "reproducible. Recorded as actionable debt."
            ),
            remediation_target="phase28_identity_migration",
        )

    def phase28_identity_migration() -> DimensionResult:
        return DimensionResult(
            dimension="phase28_identity_migration",
            status=CertificationStatus.NOT_CERTIFIED,
            mandatory=False,
            notes=(
                "Phase-28 identity migration (semantic-only content_hash) is "
                "deliberately out of scope for R2.9.8; recorded as not "
                "certified and non-mandatory so it never blocks the engine's "
                "behavioral certification."
            ),
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
