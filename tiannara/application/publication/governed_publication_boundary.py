"""Governed publication and deployment handoff after FS00-FS-041 promotion."""

from __future__ import annotations

from dataclasses import dataclass
from constitutional_architecture.governance.candidate_promotion_lifecycle import (
    CandidateLifecycleState,
    GovernedCandidatePromotionService,
)
from constitutional_architecture.governance.trusted_evidence_resolution import (
    EvidenceBinding,
    GovernedTrustedEvidenceService,
    TrustBoundary,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.publication.deployment_handoff import handoff_to_deployment_governed
from tiannara.application.publication.repository_publisher_contract import (
    PublicationResult,
    RepositoryProvider,
    SystemDeploymentBundle,
    publish_bundle,
)


@dataclass(frozen=True)
class GovernedPublicationRequest:
    candidate_id: str
    isr_hash: str
    artifact_sha256: str
    source_revision: str
    artifact_manifest_digest: str
    certification_id: str
    deployment_ref: str


class GovernedPublicationBlocked(RuntimeError):
    """Raised when publication prerequisites are not met."""


def _binding(request: GovernedPublicationRequest) -> EvidenceBinding:
    return EvidenceBinding(
        candidate_id=request.candidate_id,
        artifact_sha256=request.artifact_sha256,
        source_revision=request.source_revision,
        artifact_manifest_digest=request.artifact_manifest_digest,
    )


def assert_candidate_ready_for_publication(
    promotion: GovernedCandidatePromotionService,
    candidate_id: str,
) -> None:
    rec = promotion.get_candidate(candidate_id)
    if rec.state not in {
        CandidateLifecycleState.CERTIFIED,
        CandidateLifecycleState.PROMOTED,
    }:
        raise GovernedPublicationBlocked(
            f"candidate-not-publishable:{candidate_id}:{rec.state.value}"
        )
    if not rec.certification_id:
        raise GovernedPublicationBlocked(f"candidate-missing-certification:{candidate_id}")


def publish_governed_candidate(
    request: GovernedPublicationRequest,
    *,
    provider: RepositoryProvider,
    ledger: EvolutionLedger,
    evidence_service: GovernedTrustedEvidenceService,
    promotion_service: GovernedCandidatePromotionService,
    certification_gate,
) -> PublicationResult:
    """Publish only after governance promotion lifecycle certifies the exact artifact."""
    assert_candidate_ready_for_publication(promotion_service, request.candidate_id)
    rec = promotion_service.get_candidate(request.candidate_id)
    if rec.artifact_sha256 != request.artifact_sha256:
        raise GovernedPublicationBlocked("publication-artifact-digest-mismatch")
    if rec.certification_id != request.certification_id:
        raise GovernedPublicationBlocked("publication-certification-id-mismatch")
    evidence_service.authorize_publication(
        binding=_binding(request),
        certification_id=request.certification_id,
        require_runtime=True,
    )
    bundle = SystemDeploymentBundle(
        request.isr_hash,
        request.artifact_sha256,
        (request.certification_id,),
        request.deployment_ref,
    )
    return publish_bundle(
        bundle,
        provider,
        ledger,
        certification_gate,
        trust_boundary=TrustBoundary.PRODUCTION,
        evidence_service=evidence_service,
        publication_binding=_binding(request),
    )


def publish_and_handoff_governed(
    request: GovernedPublicationRequest,
    *,
    provider: RepositoryProvider,
    ledger: EvolutionLedger,
    evidence_service: GovernedTrustedEvidenceService,
    promotion_service: GovernedCandidatePromotionService,
    certification_gate,
    handoff_evidence_ids: tuple[str, ...] = (),
) -> dict:
    """Publish, then run governed deployment handoff (still fail-closed without live adapter)."""
    result = publish_governed_candidate(
        request,
        provider=provider,
        ledger=ledger,
        evidence_service=evidence_service,
        promotion_service=promotion_service,
        certification_gate=certification_gate,
    )
    handoff = handoff_to_deployment_governed(
        result.repo_url,
        evidence_service=evidence_service,
        binding=_binding(request),
        certification_id=request.certification_id,
        handoff_evidence_ids=handoff_evidence_ids,
    )
    return {
        "publication": result,
        "handoff": handoff,
        "candidate_id": request.candidate_id,
        "artifact_sha256": request.artifact_sha256,
        "certification_id": request.certification_id,
    }
