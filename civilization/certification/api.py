"""
API routes for production certification and Phase 22 closure.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import (
    CertificationEngine,
    CertificationError,
    CertificationPolicy,
    DEFAULT_COLLECTORS,
    DOMAIN_REQUIREMENTS,
)
from .models import (
    CertifyRequestPayload,
    ManualEvidencePayload,
    RevokeCertificationPayload,
)


router = APIRouter(
    prefix="/v1/civilization/certification",
    tags=["production-certification"],
)


def enable_certification(
    app: FastAPI,
    policy: Optional[CertificationPolicy] = None,
    context: Optional[dict] = None,
) -> CertificationEngine:
    """Enable production certification endpoints."""

    engines = {
        "civilization": getattr(app.state, "civilization_engine", None),
        "federation": getattr(app.state, "federation_engine", None),
        "reputation": getattr(app.state, "reputation_engine", None),
        "oversight": getattr(app.state, "oversight_engine", None),
        "policy": getattr(app.state, "policy_engine", None),
        "memory": getattr(app.state, "memory_consolidation_engine", None),
        "resilience": getattr(app.state, "resilience_engine", None),
        "security": getattr(app.state, "security_engine", None),
    }

    certification_context = context or getattr(
        app.state,
        "certification_context",
        {},
    )

    engine = CertificationEngine(
        policy=policy,
        engines=engines,
        context=certification_context,
        collectors=DEFAULT_COLLECTORS,
    )

    app.state.certification_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> CertificationEngine:
    engine = getattr(request.app.state, "certification_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Certification engine is not configured.",
        )

    return engine


@router.get("/domains")
def list_domains():
    return DOMAIN_REQUIREMENTS


@router.post("/certify", status_code=201)
def certify(payload: CertifyRequestPayload, request: Request):
    engine = _engine(request)

    try:
        return engine.certify(issued_by=payload.issued_by)
    except CertificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/manual-evidence", status_code=201)
def submit_manual_evidence(
    payload: ManualEvidencePayload,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.add_manual_evidence(payload)
    except CertificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reports")
def list_reports(request: Request):
    engine = _engine(request)
    return engine.list_reports()


@router.get("/reports/{report_id}")
def get_report(report_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.get_report(report_id)
    except CertificationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reports/{report_id}/revoke")
def revoke_report(
    report_id: str,
    payload: RevokeCertificationPayload,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.revoke_certification(
            report_id=report_id,
            revoked_by=payload.revoked_by,
            reason=payload.reason,
        )
    except CertificationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
