"""
API routes for the Autonomous Engineering Civilization.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import CivilizationEngine, CivilizationError
from .models import OrganizationCharter, RecommendationInput


router = APIRouter(
    prefix="/v1/civilization",
    tags=["autonomous-engineering-civilization"],
)


class CreateOrganizationRequest(BaseModel):
    name: str
    charter: OrganizationCharter


class CreateAgentRequest(BaseModel):
    name: str
    role_id: str

    capabilities: List[str] = Field(default_factory=list)

    trust_level: float = Field(default=0.5, ge=0.0, le=1.0)


class AssignAgentRequest(BaseModel):
    agent_id: str


class CreateTaskRequest(BaseModel):
    organization_id: str

    title: str
    objective: str
    task_type: str

    required_roles: List[str] = Field(default_factory=list)

    inputs: dict = Field(default_factory=dict)

    priority: int = Field(default=50, ge=0, le=100)

    high_impact: bool = False

    proposal_id: Optional[str] = None
    campaign_id: Optional[str] = None


class SubmitRecommendationRequest(BaseModel):
    agent_id: str
    payload: RecommendationInput


def enable_civilization(
    app: FastAPI,
    engine: Optional[CivilizationEngine] = None,
) -> CivilizationEngine:
    """Enable civilization endpoints."""

    civilization_engine = engine or CivilizationEngine()

    app.state.civilization_engine = civilization_engine

    app.include_router(router)

    return civilization_engine


def _engine(request: Request) -> CivilizationEngine:
    engine = getattr(request.app.state, "civilization_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Civilization engine is not configured.",
        )

    return engine


@router.post("/organizations", status_code=201)
def create_organization(payload: CreateOrganizationRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.create_organization(payload.name, payload.charter)
    except CivilizationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/agents", status_code=201)
def create_agent(payload: CreateAgentRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.create_agent(
            name=payload.name,
            role_id=payload.role_id,
            capabilities=payload.capabilities,
            trust_level=payload.trust_level,
        )
    except CivilizationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/organizations/{organization_id}/assign-agent")
def assign_agent(
    organization_id: str,
    payload: AssignAgentRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.assign_agent_to_organization(
            organization_id,
            payload.agent_id,
        )
    except CivilizationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks", status_code=201)
def create_task(payload: CreateTaskRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.create_task(
            organization_id=payload.organization_id,
            title=payload.title,
            objective=payload.objective,
            task_type=payload.task_type,
            required_roles=payload.required_roles,
            inputs=payload.inputs,
            priority=payload.priority,
            high_impact=payload.high_impact,
            proposal_id=payload.proposal_id,
            campaign_id=payload.campaign_id,
        )
    except CivilizationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/run")
def run_task(task_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.run_task(task_id)
    except CivilizationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/finalize")
def finalize_task(
    task_id: str,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _engine(request)

    try:
        return engine.finalize_task(task_id, x_actor_id)
    except CivilizationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tasks/{task_id}")
def get_task(task_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.get_task(task_id)
    except CivilizationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/recommendations")
def list_recommendations(task_id: str, request: Request):
    engine = _engine(request)

    return engine.list_recommendations(task_id)


@router.get("/tasks/{task_id}/conflicts")
def list_conflicts(task_id: str, request: Request):
    engine = _engine(request)

    return engine.list_conflicts(task_id)


@router.post("/organizations/{organization_id}/elect-leader")
def elect_leader(organization_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.elect_leader(organization_id)
    except CivilizationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/organizations/{organization_id}/memory")
def get_memory(organization_id: str, request: Request):
    engine = _engine(request)

    return engine.get_memory(organization_id)


@router.get("/messages")
def list_messages(
    request: Request,
    topic: Optional[str] = None,
    task_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    limit: int = 100,
):
    engine = _engine(request)

    return engine.bus.list_messages(
        topic=topic,
        task_id=task_id,
        organization_id=organization_id,
        limit=limit,
    )
