"""Governed full-stack orchestration ingress (Checkpoint 056)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.engine.orchestration_ingress_gateway import (
    orchestration_ingress_status,
    run_governed_full_stack,
)
from app.middleware.security import require_auth
from app.schemas.orchestration import GovernedFullStackRunBody
from certification.orchestration.implir_ingress_guard import ImplirIngressBlocked
from tiannara.application.orchestration.production_ingress import (
    GovernedFullStackIngressUnavailable,
)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


@router.get("/ingress-status")
async def governed_ingress_status(_auth=Depends(require_auth)):
    return orchestration_ingress_status()


@router.post("/full-stack/run")
async def governed_full_stack_run(body: GovernedFullStackRunBody, _auth=Depends(require_auth)):
    try:
        return run_governed_full_stack(body)
    except GovernedFullStackIngressUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ImplirIngressBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        if "unknown-workload" in detail:
            code = 404
        elif "mismatch" in detail or "binding" in detail:
            code = 409
        elif "impersonating" in detail:
            code = 403
        else:
            code = 400
        raise HTTPException(status_code=code, detail=detail) from exc
