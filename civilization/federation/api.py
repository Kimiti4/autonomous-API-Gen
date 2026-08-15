"""
API routes for federated engineering organizations.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ..engine import CivilizationEngine
from .engine import (
    FederationEngine,
    FederationError,
    StaticFederationGovernanceGateway,
)
from .models import FederationCharter, VotePosition


router = APIRouter(
    prefix="/v1/civilization/federations",
    tags=["federated-engineering-organizations"],
)


class CreateFederationRequest(BaseModel):
    name: str
    charter: FederationCharter


class JoinFederationRequest(BaseModel):
    organization_id: str
    weight: float = Field(default=1.0, ge=0.0, le=100.0)
    jurisdictions: List[str] = Field(default_factory=list)


class CreateInitiativeRequest(BaseModel):
    title: str
    objective: str
    initiative_type: str

    required_roles: List[str] = Field(default_factory=list)
    member_organization_ids: Optional[List[str]] = None

    inputs: dict = Field(default_factory=dict)

    high_impact: bool = False

    proposal_id: Optional[str] = None
    campaign_id: Optional[str] = None


class AuthorizeInitiativeRequest(BaseModel):
    actor_id: str = "api"


class DelegateInitiativeRequest(BaseModel):
    actor_id: str = "api"


class CreateConflictRequest(BaseModel):
    party_organization_ids: List[str]
    subject_ref: str
    conflict_type: str

    initiative_id: Optional[str] = None
    recommendation_ids: List[str] = Field(default_factory=list)

    high_impact: bool = False


class ResolveConflictRequest(BaseModel):
    resolved_by: str
    selected_recommendation_id: Optional[str] = None
    rationale: str = ""


class ProposeDecisionRequest(BaseModel):
    title: str
    decision_type: str

    initiative_id: Optional[str] = None
    conflict_id: Optional[str] = None

    rationale: Optional[str] = None


class CastVoteRequest(BaseModel):
    organization_id: str
    position: VotePosition
    reason: str = ""


def enable_federation(
    app: FastAPI,
    civilization_engine: Optional[CivilizationEngine] = None,
) -> FederationEngine:
    """Enable federation endpoints."""

    civilization_engine = civilization_engine or getattr(
        app.state,
        "civilization_engine",
        None,
    )

    if not civilization_engine:
        raise RuntimeError("Civilization engine is not configured.")

    federation_engine = FederationEngine(
        civilization_engine=civilization_engine,
        governance_gateway=StaticFederationGovernanceGateway(),
    )

    app.state.federation_engine = federation_engine

    app.include_router(router)

    return federation_engine


def _engine(request: Request) -> FederationEngine:
    engine = getattr(request.app.state, "federation_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Federation engine is not configured.",
        )

    return engine


@router.post("", status_code=201)
def create_federation(payload: CreateFederationRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.create_federation(payload.name, payload.charter)
    except FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{federation_id}/members", status_code=201)
def join_federation(
    federation_id: str,
    payload: JoinFederationRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.join_federation(
            federation_id=federation_id,
            organization_id=payload.organization_id,
            weight=payload.weight,
            jurisdictions=payload.jurisdictions,
        )
    except FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{federation_id}/initiatives", status_code=201)
def create_initiative(
    federation_id: str,
    payload: CreateInitiativeRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.create_initiative(
            federation_id=federation_id,
            title=payload.title,
            objective=payload.objective,
            initiative_type=payload.initiative_type,
            required_roles=payload.required_roles,
            member_organization_ids=payload.member_organization_ids,
            inputs=payload.inputs,
            high_impact=payload.high_impact,
            proposal_id=payload.proposal_id,
            campaign_id=payload.campaign_id,
        )
    except FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/initiatives/{initiative_id}/authorize")
def authorize_initiative(
    initiative_id: str,
    payload: AuthorizeInitiativeRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.authorize_initiative(
            initiative_id=initiative_id,
            actor_id=payload.actor_id,
        )
    except FederationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/initiatives/{initiative_id}/delegate")
def delegate_initiative(
    initiative_id: str,
    payload: DelegateInitiativeRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.delegate_initiative_tasks(
            initiative_id=initiative_id,
            actor_id=payload.actor_id,
        )
    except FederationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{federation_id}/conflicts", status_code=201)
def create_conflict(
    federation_id: str,
    payload: CreateConflictRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.create_conflict(
            federation_id=federation_id,
            party_organization_ids=payload.party_organization_ids,
            subject_ref=payload.subject_ref,
            conflict_type=payload.conflict_type,
            initiative_id=payload.initiative_id,
            recommendation_ids=payload.recommendation_ids,
            high_impact=payload.high_impact,
        )
    except FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(
    conflict_id: str,
    payload: ResolveConflictRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.resolve_conflict(
            conflict_id=conflict_id,
            resolved_by=payload.resolved_by,
            selected_recommendation_id=payload.selected_recommendation_id,
            rationale=payload.rationale,
        )
    except FederationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{federation_id}/decisions", status_code=201)
def propose_decision(
    federation_id: str,
    payload: ProposeDecisionRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.propose_decision(
            federation_id=federation_id,
            title=payload.title,
            decision_type=payload.decision_type,
            initiative_id=payload.initiative_id,
            conflict_id=payload.conflict_id,
            rationale=payload.rationale,
        )
    except FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/decisions/{decision_id}/votes", status_code=201)
def cast_vote(
    decision_id: str,
    payload: CastVoteRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.cast_vote(
            decision_id=decision_id,
            organization_id=payload.organization_id,
            position=payload.position,
            reason=payload.reason,
        )
    except FederationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/decisions/{decision_id}/tally")
def tally_decision(decision_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.tally_decision(decision_id)
    except FederationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{federation_id}/report")
def federation_report(federation_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.federation_report(federation_id)
    except FederationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
