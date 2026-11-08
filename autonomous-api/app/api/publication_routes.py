"""Governed publication API — fail closed unless production stores are configured."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.engine.governed_publication_gateway import (
    GovernedPublicationUnavailable,
    execute_governed_publish,
    publication_status,
    require_governed_services,
)
from certification.orchestration.implir_ingress_guard import ImplirIngressBlocked
from app.middleware.security import require_auth
from app.schemas.publication import GovernedPublishBody
from tiannara.application.publication.governed_publication_boundary import (
    GovernedPublicationRequest,
)

router = APIRouter(prefix="/publication", tags=["publication"])


@router.get("/status")
async def governed_publication_status(_auth=Depends(require_auth)):
    st = publication_status()
    return {
        "governedProductionEnabled": st.governed_production_enabled,
        "trustedEvidenceLedger": st.trusted_evidence_ledger or None,
        "governanceCandidateStore": st.governance_candidate_store or None,
        "explicitProductionFlag": st.explicit_production_flag,
    }


@router.get("/candidates/{candidate_id}")
async def governed_candidate_snapshot(candidate_id: str, _auth=Depends(require_auth)):
    try:
        _evidence, promotion = require_governed_services()
    except GovernedPublicationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        rec = promotion.get_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "candidateId": rec.candidate_id,
        "state": rec.state.value,
        "artifactSha256": rec.artifact_sha256,
        "sourceRevision": rec.source_revision,
        "certificationId": rec.certification_id or None,
        "evidenceIds": list(rec.evidence_ids),
    }


@router.post("/publish")
async def governed_publish(body: GovernedPublishBody, _auth=Depends(require_auth)):
    if not publication_status().governed_production_enabled:
        raise HTTPException(
            status_code=503,
            detail="governed-publication-not-configured",
        )
    request = GovernedPublicationRequest(
        candidate_id=body.candidate_id,
        isr_hash=body.isr_hash,
        artifact_sha256=body.artifact_sha256,
        source_revision=body.source_revision,
        artifact_manifest_digest=body.artifact_manifest_digest,
        certification_id=body.certification_id,
        deployment_ref=body.deployment_ref,
    )
    try:
        return execute_governed_publish(
            request=request,
            include_handoff=body.include_handoff,
            isr_ingress_authority=body.isr_ingress_authority,
            governed_lineage_ref=body.governed_lineage_ref,
        )
    except ImplirIngressBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except GovernedPublicationUnavailable as exc:
        detail = str(exc)
        code = 409 if "not-publishable" in detail or "mismatch" in detail else 503
        raise HTTPException(status_code=code, detail=detail) from exc
