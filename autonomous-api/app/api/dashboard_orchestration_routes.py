"""Dashboard-authenticated governed full-stack orchestration (Checkpoint 057)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.maintenance_outbox_routes import require_dashboard_auth
from app.engine.orchestration_ingress_gateway import run_governed_full_stack
from app.schemas.orchestration import GovernedFullStackRunBody
from tiannara.application.orchestration.production_ingress import GovernedFullStackIngressUnavailable

router = APIRouter(prefix="/dashboard/orchestration", tags=["dashboard-orchestration"])


@router.post("/full-stack/run")
async def dashboard_full_stack_run(
    body: GovernedFullStackRunBody,
    _auth=Depends(require_dashboard_auth),
):
    """Server-side ingress for the operator dashboard (session or API key)."""
    try:
        result = run_governed_full_stack(body)
        result["ingressSurface"] = "dashboard"
        return result
    except GovernedFullStackIngressUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        code = 409 if "mismatch" in detail or "binding" in detail else 400
        raise HTTPException(status_code=code, detail=detail) from exc
