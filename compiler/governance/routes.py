"""
Compiler governance API routes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request

from ..models import CompilationRequest
from .audit import LoggingAuditEmitter
from .client import GovernanceClient
from .compiler import GovernedCompiler
from .enforcer import CompilerGovernanceEnforcer
from .models import CompilerGovernancePolicy


router = APIRouter(
    prefix="/v1/compiler/governance",
    tags=["compiler-governance"],
)


def enable_compiler_governance(
    app: FastAPI,
    compiler,
    certification_engine=None,
    governance_client: Optional[GovernanceClient] = None,
    policy: Optional[CompilerGovernancePolicy] = None,
    audit_emitter=None,
) -> GovernedCompiler:
    """Enable compiler governance on an existing compiler application."""

    enforcer = CompilerGovernanceEnforcer(
        registry=compiler.registry,
        certification_engine=certification_engine,
        governance_client=governance_client,
        policy=policy or CompilerGovernancePolicy(),
        audit_emitter=audit_emitter or LoggingAuditEmitter(),
    )

    governed_compiler = GovernedCompiler(
        inner=compiler,
        enforcer=enforcer,
    )

    app.state.raw_compiler = compiler
    app.state.compiler = governed_compiler
    app.state.compiler_governance_enforcer = enforcer

    app.include_router(router)

    return governed_compiler


def _get_enforcer(request: Request) -> CompilerGovernanceEnforcer:
    enforcer = getattr(
        request.app.state,
        "compiler_governance_enforcer",
        None,
    )

    if not enforcer:
        raise HTTPException(
            status_code=500,
            detail="Compiler governance is not configured.",
        )

    return enforcer


@router.get("/policy")
def get_policy(request: Request):
    """Return the active compiler governance policy."""

    enforcer = _get_enforcer(request)
    return enforcer.policy


@router.get("/backends/{backend_id}/status")
def backend_governance_status(
    backend_id: str,
    request: Request,
    version: Optional[str] = Query(default=None),
):
    """Return governance status for a backend."""

    enforcer = _get_enforcer(request)

    try:
        manifest = enforcer.registry.get_manifest(backend_id, version)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    certification = None

    if enforcer.certification_engine:
        certification = enforcer.certification_engine.get_report(
            manifest.backend_id,
            manifest.version,
        )

    return {
        "manifest": manifest,
        "certification": certification,
    }


@router.post("/evaluate-compilation")
def evaluate_compilation(
    payload: CompilationRequest,
    request: Request,
):
    """Evaluate whether a compilation request would be allowed."""

    enforcer = _get_enforcer(request)
    return enforcer.evaluate_compilation(payload)
