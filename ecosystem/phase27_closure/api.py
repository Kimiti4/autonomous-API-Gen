"""
API routes for Phase 27 closure certification.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import Phase27ClosureEngine, Phase27ClosurePolicy
from .models import Phase27Evidence


router = APIRouter(
    prefix="/v1/ecosystem/phase27/closure",
    tags=["phase27-closure"],
)


class CertifyClosureRequest(BaseModel):
    certified_by: str = "system"
    evidence: Phase27Evidence = Field(default_factory=Phase27Evidence)


class RevokeClosureRequest(BaseModel):
    reason: str
    revoked_by: str = "system"


def enable_phase27_closure(
    app: FastAPI,
    policy: Phase27ClosurePolicy | None = None,
) -> Phase27ClosureEngine:
    """Enable Phase 27 closure endpoints."""

    engine = Phase27ClosureEngine(policy=policy)

    app.state.phase27_closure_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> Phase27ClosureEngine:
    engine = getattr(request.app.state, "phase27_closure_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Phase 27 closure engine is not configured.",
        )

    return engine


@router.post("/certify", status_code=201)
def certify_closure(payload: CertifyClosureRequest, request: Request):
    engine = _engine(request)

    return engine.certify(
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
            detail="No Phase 27 closure report found.",
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
    payload: RevokeClosureRequest,
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
