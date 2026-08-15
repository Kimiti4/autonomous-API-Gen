"""
Compiler SDK API routes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from ..errors import BackendNotFoundError, ISRValidationError
from .certification import BackendCertificationEngine
from .models import BackendCertificationRequest, RevokeCertificationRequest


router = APIRouter(
    prefix="/v1/compiler/sdk",
    tags=["compiler-sdk"],
)


def enable_compiler_sdk(app: FastAPI, compiler) -> None:
    """Enable the compiler SDK on an existing compiler app."""

    app.state.compiler = compiler

    if not hasattr(app.state, "certification_engine"):
        app.state.certification_engine = BackendCertificationEngine(
            compiler.registry
        )

    app.include_router(router)


def _get_engine(request: Request) -> BackendCertificationEngine:
    engine = getattr(request.app.state, "certification_engine", None)

    if engine:
        return engine

    compiler = getattr(request.app.state, "compiler", None)

    if not compiler:
        raise HTTPException(
            status_code=500,
            detail="Compiler is not configured.",
        )

    engine = BackendCertificationEngine(compiler.registry)
    request.app.state.certification_engine = engine

    return engine


@router.post("/certify")
def certify_backend(
    payload: BackendCertificationRequest,
    request: Request,
):
    """Certify a backend."""

    engine = _get_engine(request)

    try:
        return engine.certify(payload)
    except BackendNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ISRValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "message": str(exc),
                "report": exc.report.model_dump(mode="json"),
            },
        )


@router.get("/certifications")
def list_certifications(request: Request):
    """List backend certification reports."""

    engine = _get_engine(request)
    return engine.list_reports()


@router.get("/certifications/{backend_id}")
def get_certification(
    backend_id: str,
    request: Request,
    version: Optional[str] = Query(default=None),
):
    """Get a backend certification report."""

    engine = _get_engine(request)

    report = engine.get_report(backend_id, version)

    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No certification found for backend: {backend_id}",
        )

    return report


@router.post("/certifications/{backend_id}/revoke")
def revoke_certification(
    backend_id: str,
    payload: RevokeCertificationRequest,
    request: Request,
):
    """Revoke a backend certification."""

    engine = _get_engine(request)

    report = engine.revoke(
        backend_id,
        payload.version,
        payload.reason,
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No certification found for backend: {backend_id}",
        )

    return report