"""
API routes for learning governance and safety controls.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import LearningGovernanceEngine
from .models import LearningGovernancePolicy


router = APIRouter(
    prefix="/v1/learning/governance",
    tags=["learning-governance"],
)


class EvaluateRequest(BaseModel):
    scope: str = "platform"


class ScopeRequest(BaseModel):
    scope: str = "platform"
    requested_by: str = "system"
    auto_submit: bool = True


class ApprovalDecisionRequest(BaseModel):
    approver_id: str
    comments: str = ""
    auto_submit: bool = True


class KillSwitchRequest(BaseModel):
    reason: str = ""
    actor_id: str = "system"


def enable_learning_governance(
    app: FastAPI,
    integration_engine=None,
    policy: LearningGovernancePolicy | None = None,
) -> LearningGovernanceEngine:
    """Enable learning governance endpoints."""

    integration_engine = integration_engine or getattr(
        app.state,
        "evolution_integration_engine",
        None,
    )

    if not integration_engine:
        raise RuntimeError(
            "Evolution fitness integration engine is required."
        )

    engine = LearningGovernanceEngine(
        integration_engine=integration_engine,
        policy=policy,
    )

    app.state.learning_governance_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> LearningGovernanceEngine:
    engine = getattr(request.app.state, "learning_governance_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Learning governance engine is not configured.",
        )

    return engine


@router.post("/evaluate")
def evaluate_learning_sync(payload: EvaluateRequest, request: Request):
    engine = _engine(request)

    return engine.evaluate_sync(scope=payload.scope)


@router.post("/sync")
def governed_sync(payload: ScopeRequest, request: Request):
    engine = _engine(request)

    return engine.governed_sync(
        scope=payload.scope,
        requested_by=payload.requested_by,
        auto_submit=payload.auto_submit,
    )


@router.get("/approvals")
def list_approvals(request: Request):
    engine = _engine(request)

    return list(engine.approvals.values())


@router.post("/approvals/{approval_id}/approve")
def approve(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.approve(
            approval_id=approval_id,
            approver_id=payload.approver_id,
            comments=payload.comments,
            auto_submit=payload.auto_submit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/reject")
def reject(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.reject(
            approval_id=approval_id,
            approver_id=payload.approver_id,
            comments=payload.comments,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/kill-switch/activate")
def activate_kill_switch(payload: KillSwitchRequest, request: Request):
    engine = _engine(request)

    return engine.activate_kill_switch(
        reason=payload.reason,
        activated_by=payload.actor_id,
    )


@router.post("/kill-switch/deactivate")
def deactivate_kill_switch(payload: KillSwitchRequest, request: Request):
    engine = _engine(request)

    return engine.deactivate_kill_switch(
        deactivated_by=payload.actor_id,
        reason=payload.reason,
    )


@router.get("/report")
def governance_report(request: Request):
    engine = _engine(request)

    return engine.report()
