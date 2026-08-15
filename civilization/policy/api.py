"""
API routes for permissioned autonomy and policy enforcement.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import PolicyEngine, PolicyError
from .models import PermissionRule, PolicyEvaluationRequest


router = APIRouter(
    prefix="/v1/civilization/policy",
    tags=["permissioned-autonomy-policy"],
)


class CreatePolicyRequest(BaseModel):
    name: str
    rules: List[PermissionRule] = Field(default_factory=list)


class ActivatePolicyRequest(BaseModel):
    policy_id: str


class GrantDelegationRequest(BaseModel):
    grantor: str
    grantee: str

    actions: List[str] = Field(default_factory=list)

    expires_at: str

    scope: dict = Field(default_factory=dict)

    max_uses: Optional[int] = None


class SimulatePolicyRequest(BaseModel):
    request: PolicyEvaluationRequest
    policy_id: Optional[str] = None


def enable_policy(
    app: FastAPI,
    oversight_engine=None,
) -> PolicyEngine:
    """Enable policy endpoints."""

    engine = PolicyEngine(oversight_engine=oversight_engine)

    engine.bootstrap_default_policy()

    app.state.policy_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> PolicyEngine:
    engine = getattr(request.app.state, "policy_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Policy engine is not configured.",
        )

    return engine


@router.get("/actions")
def action_catalog(request: Request):
    engine = _engine(request)
    return list(engine.action_catalog.values())


@router.post("/policies", status_code=201)
def create_policy(payload: CreatePolicyRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.create_policy(payload.name, payload.rules)
    except PolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/policies/activate")
def activate_policy(payload: ActivatePolicyRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.activate_policy(payload.policy_id)
    except PolicyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/policies/active")
def active_policy(request: Request):
    engine = _engine(request)

    policy = engine.get_active_policy()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail="No active policy.",
        )

    return policy


@router.post("/evaluate")
def evaluate(payload: PolicyEvaluationRequest, request: Request):
    engine = _engine(request)
    return engine.evaluate(payload)


@router.post("/simulate")
def simulate(payload: SimulatePolicyRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.simulate(payload.request, payload.policy_id)
    except PolicyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/delegations", status_code=201)
def grant_delegation(payload: GrantDelegationRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.grant_delegation(
            grantor=payload.grantor,
            grantee=payload.grantee,
            actions=payload.actions,
            expires_at=payload.expires_at,
            scope=payload.scope,
            max_uses=payload.max_uses,
        )
    except PolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/delegations/{delegation_id}/revoke")
def revoke_delegation(delegation_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.revoke_delegation(delegation_id)
    except PolicyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/delegations")
def list_delegations(request: Request):
    engine = _engine(request)
    return list(engine.delegations.values())
