"""
API routes for evolutionary governance, safety interlocks, and promotion.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from .governance_safety import (
    EvolutionEvidence,
    SafetyInterlockEngine,
    SafetyInterlockPolicy,
)
from .promotion import (
    GovernanceGateway,
    PromotionControlEngine,
    PromotionControlPolicy,
    PromotionError,
)


router = APIRouter(
    prefix="/v1/evolution/governance",
    tags=["evolutionary-governance"],
)


class SafetyEvaluationPayload(BaseModel):
    evidence: EvolutionEvidence
    policy: Optional[SafetyInterlockPolicy] = None


class CreatePromotionRequestPayload(BaseModel):
    proposal_id: str
    candidate_id: str

    environment: str = "staging"

    actor_id: Optional[str] = None

    evidence: Optional[EvolutionEvidence] = None


class ApprovePromotionPayload(BaseModel):
    approver_id: str
    comments: str = ""


class RollbackPromotionPayload(BaseModel):
    reason: str = ""


def enable_evolutionary_governance(
    app: FastAPI,
    base_engine=None,
    governance_gateway: Optional[GovernanceGateway] = None,
    safety_policy: Optional[SafetyInterlockPolicy] = None,
    promotion_policy: Optional[PromotionControlPolicy] = None,
    evidence_collector=None,
) -> PromotionControlEngine:
    """Enable evolutionary governance endpoints."""

    safety_engine = SafetyInterlockEngine()

    promotion_engine = PromotionControlEngine(
        safety_engine=safety_engine,
        governance_gateway=governance_gateway,
        policy=promotion_policy,
        safety_policy=safety_policy,
        base_engine=base_engine,
        evidence_collector=evidence_collector,
    )

    app.state.safety_engine = safety_engine
    app.state.promotion_engine = promotion_engine

    app.include_router(router)

    return promotion_engine


def _promotion_engine(request: Request) -> PromotionControlEngine:
    engine = getattr(request.app.state, "promotion_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Promotion control engine is not configured.",
        )

    return engine


def _safety_engine(request: Request) -> SafetyInterlockEngine:
    engine = getattr(request.app.state, "safety_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Safety interlock engine is not configured.",
        )

    return engine


@router.post("/safety/evaluate")
def evaluate_safety(payload: SafetyEvaluationPayload, request: Request):
    engine = _safety_engine(request)

    return engine.evaluate(
        evidence=payload.evidence,
        policy=payload.policy,
    )


@router.post("/promotion-requests", status_code=201)
def create_promotion_request(
    payload: CreatePromotionRequestPayload,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _promotion_engine(request)

    actor_id = payload.actor_id or x_actor_id

    try:
        return engine.create_promotion_request(
            proposal_id=payload.proposal_id,
            candidate_id=payload.candidate_id,
            environment=payload.environment,
            actor_id=actor_id,
            evidence=payload.evidence,
        )
    except PromotionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/promotion-requests/{request_id}/submit-governance")
def submit_governance(
    request_id: str,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _promotion_engine(request)

    try:
        return engine.submit_governance(request_id, x_actor_id)
    except PromotionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/promotion-requests/{request_id}/approve")
def approve_promotion(
    request_id: str,
    payload: ApprovePromotionPayload,
    request: Request,
):
    engine = _promotion_engine(request)

    try:
        return engine.approve(
            request_id=request_id,
            approver_id=payload.approver_id,
            comments=payload.comments,
        )
    except PromotionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/promotion-requests/{request_id}/promote")
def promote_request(
    request_id: str,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _promotion_engine(request)

    try:
        return engine.promote(request_id, x_actor_id)
    except PromotionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/promotion-requests/{request_id}/rollback")
def rollback_request(
    request_id: str,
    payload: RollbackPromotionPayload,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _promotion_engine(request)

    try:
        return engine.rollback(
            request_id=request_id,
            actor_id=x_actor_id,
            reason=payload.reason,
        )
    except PromotionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/promotion-requests/{request_id}")
def get_promotion_request(request_id: str, request: Request):
    engine = _promotion_engine(request)

    try:
        return engine.get_request(request_id)
    except PromotionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/promotion-requests/{request_id}/packet")
def get_promotion_packet(request_id: str, request: Request):
    engine = _promotion_engine(request)

    try:
        return engine.get_packet(request_id)
    except PromotionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
