"""Bucket 2 capability-specific verification profiles and evidence gates."""

from __future__ import annotations

from dataclasses import dataclass

from .work_mode import WorkMode


@dataclass(frozen=True)
class VerificationProfile:
    mode: WorkMode
    required_properties: tuple[str, ...]
    minimum_evidence_per_property: int = 1

    def validate_evidence(self, evidence_by_property: dict[str, tuple[str, ...]]) -> None:
        if self.minimum_evidence_per_property < 1:
            raise ValueError("invalid-minimum-evidence")
        for prop in self.required_properties:
            evidence = evidence_by_property.get(prop, ())
            if len(evidence) < self.minimum_evidence_per_property:
                raise ValueError(f"missing-capability-evidence:{self.mode.value}:{prop}")


_PROFILES = {
    WorkMode.GENERATE: ("generation-integrity", "requirement-traceability", "end-to-end-verification"),
    WorkMode.MAINTAIN: ("maintenance-safety", "regression-preservation", "operational-integrity"),
    WorkMode.IMPROVE: ("improvement-correctness", "regression-preservation", "requirement-traceability"),
    WorkMode.DOCUMENT: ("documentation-accuracy", "implementation-traceability"),
    WorkMode.SEO: ("seo", "metadata-correctness", "crawlability", "content-integrity"),
    WorkMode.TEST: ("test-correctness", "regression-preservation", "coverage-traceability"),
    WorkMode.ARCHITECTURE: ("architecture-consistency", "dependency-integrity", "requirement-traceability"),
    WorkMode.MIGRATE: ("migration-safety", "data-integrity", "rollback-readiness"),
    WorkMode.REFACTOR: ("behavior-preservation", "dependency-integrity", "regression-preservation"),
    WorkMode.CROSS_STACK: ("cross-domain-contracts", "end-to-end-flow", "integration-safety"),\n    WorkMode.FRONTEND_ONLY: ("frontend-contracts", "accessibility", "navigation-preservation"),\n    WorkMode.BACKEND_ONLY: ("backend-contracts", "effect-safety", "failure-recovery"),\n    WorkMode.API_CONTRACT_ONLY: ("api-contract-integrity", "schema-compatibility", "error-contract-preservation"),
}


def verification_profile(mode: WorkMode) -> VerificationProfile:
    try:
        return VerificationProfile(mode, _PROFILES[mode])
    except KeyError as exc:
        raise ValueError(f"missing-capability-verification-profile:{mode}") from exc
