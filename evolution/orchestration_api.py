"""
API routes for evolution orchestration.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request

from .orchestration import (
    EvolutionCampaignRequest,
    EvolutionOrchestrator,
    RunGenerationRequest,
)


router = APIRouter(
    prefix="/v1/evolution/orchestration",
    tags=["evolution-orchestration"],
)


def enable_evolution_orchestration(
    app: FastAPI,
    base_engine=None,
    candidate_engine=None,
) -> EvolutionOrchestrator:
    """Enable evolution orchestration on an existing application."""

    base_engine = base_engine or getattr(app.state, "engine", None)
    candidate_engine = candidate_engine or getattr(
        app.state,
        "multi_engine",
        None,
    )

    if not base_engine:
        raise RuntimeError("Base evolution engine is not configured.")

    if not candidate_engine:
        raise RuntimeError("Candidate evolution engine is not configured.")

    orchestrator = EvolutionOrchestrator(
        base_engine=base_engine,
        candidate_engine=candidate_engine,
    )

    app.state.orchestrator = orchestrator
    app.include_router(router)

    return orchestrator


def _orchestrator(request: Request) -> EvolutionOrchestrator:
    orchestrator = getattr(request.app.state, "orchestrator", None)

    if not orchestrator:
        raise HTTPException(
            status_code=500,
            detail="Evolution orchestrator is not configured.",
        )

    return orchestrator


@router.post("/campaigns", status_code=201)
def create_campaign(
    payload: EvolutionCampaignRequest,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    orchestrator = _orchestrator(request)
    return orchestrator.create_campaign(payload, x_actor_id)


@router.post("/campaigns/{campaign_id}/run-generation")
def run_generation(
    campaign_id: str,
    payload: RunGenerationRequest,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    orchestrator = _orchestrator(request)

    try:
        return orchestrator.run_generation(
            campaign_id=campaign_id,
            actor_id=x_actor_id,
            feedback_recommendations=payload.feedback_recommendations,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: str,
    request: Request,
):
    orchestrator = _orchestrator(request)

    try:
        return orchestrator.get_campaign(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
