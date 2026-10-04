"""Gate evolution admission on executable verification acceptance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .verification_acceptance import VerificationDisposition, VerificationDispositionResult
from .verification_executor import VerificationResult
from .verification_artifacts import VerificationArtifactResult


@dataclass(frozen=True)
class CandidateVerification:
    disposition: VerificationDispositionResult
    results: tuple[VerificationResult, ...]
    artifacts: tuple[VerificationArtifactResult, ...]
    evidence_digests: tuple[str, ...]


def materialize_candidate_verification(
    disposition: VerificationDispositionResult,
    results: Sequence[VerificationResult],
    artifacts: Sequence[VerificationArtifactResult] = (),
) -> CandidateVerification:
    evidence = [r.evidence.evidence_digest for r in results]
    evidence.extend(a.artifact_digest for a in artifacts)
    return CandidateVerification(
        disposition=disposition,
        results=tuple(results),
        artifacts=tuple(artifacts),
        evidence_digests=tuple(sorted(set(evidence))),
    )


def require_candidate_verification(
    verification: CandidateVerification,
) -> None:
    if verification.disposition.disposition is VerificationDisposition.PASS:
        if not verification.evidence_digests:
            raise ValueError("admission-missing-verification-evidence")
        return
    if verification.disposition.disposition is VerificationDisposition.INCOMPLETE:
        raise ValueError("admission-incomplete-verification")
    raise ValueError("admission-verification-failed")
