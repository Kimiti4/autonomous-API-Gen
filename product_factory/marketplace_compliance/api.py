"""
API routes for marketplace compliance, audit, and financial certification.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import MarketplaceComplianceEngine, MarketplaceCompliancePolicy
from .models import MarketplaceComplianceEvidence


router = APIRouter(
    prefix="/v1/marketplace/compliance",
    tags=["marketplace-compliance"],
)


class AuditBundleRequest(BaseModel):
    scope: str = "marketplace"
    records: List[Dict[str, Any]] = Field(default_factory=list)


class CertifyComplianceRequest(BaseModel):
    scope: str = "marketplace"
    certified_by: str = "system"
    evidence: MarketplaceComplianceEvidence = Field(
        default_factory=MarketplaceComplianceEvidence
    )


class RevokeComplianceRequest(BaseModel):
    reason: str
    revoked_by: str = "system"


def enable_marketplace_compliance(
    app: FastAPI,
    policy: MarketplaceCompliancePolicy | None = None,
) -> MarketplaceComplianceEngine:
    """Enable marketplace compliance endpoints."""

    engine = MarketplaceComplianceEngine(policy=policy)

    app.state.marketplace_compliance_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> MarketplaceComplianceEngine:
    engine = getattr(request.app.state, "marketplace_compliance_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Marketplace compliance engine is not configured.",
        )

    return engine


@router.post("/audit-bundle", status_code=201)
def create_audit_bundle(payload: AuditBundleRequest, request: Request):
    engine = _engine(request)

    return engine.build_audit_bundle(
        records=payload.records,
        scope=payload.scope,
    )


@router.post("/certify", status_code=201)
def certify_compliance(payload: CertifyComplianceRequest, request: Request):
    engine = _engine(request)

    return engine.certify(
        scope=payload.scope,
        certified_by=payload.certified_by,
        evidence=payload.evidence,
    )


@router.get("/latest")
def latest_report(request: Request):
    engine = _engine(request)

    report = engine.latest_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No compliance report found.",
        )

    return report


@router.get("/report/{report_id}")
def get_report(report_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.report(report_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/report/{report_id}/revoke")
def revoke_report(
    report_id: str,
    payload: RevokeComplianceRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.revoke(
            report_id=report_id,
            reason=payload.reason,
            revoked_by=payload.revoked_by,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
