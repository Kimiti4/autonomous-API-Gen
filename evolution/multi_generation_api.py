"""
API routes for multi-generation evolution campaigns.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request

from .memory import InMemoryEvolutionaryMemory
from .multi_generation import (
    CampaignStopPolicy,
    MultiGenerationCampaignEngine,
    RunCampaignRequest,
)


router = APIRouter(
    prefix="/v1/evolution/multi-generation",
    tags=["multi-generation-evolution"],
)


def enable_multi_generation_evolution(
    app: FastAPI,
    orchestrator=None,
    memory: InMemoryEvolutionaryMemory | None = None,
    stop_policy: CampaignStopPolicy | None = None,
) -> MultiGenerationCampaignEngine:
    """Enable multi-generation evolution on an existing application."""

    orchestrator = orchestrator or getattr(app.state, "orchestrator", None)

    if not orchestrator:
        raise RuntimeError("Evolution orchestrator is not configured.")

    engine = MultiGenerationCampaignEngine(
        orchestrator=orchestrator,
        memory=memory,
        stop_policy=stop_policy,
    )

    app.state.multi_generation_engine = engine
    app.state.evolutionary_memory = engine.memory

    app.include_router(router)

    return engine


def _engine(request: Request) -> MultiGenerationCampaignEngine:
    engine = getattr(request.app.state, "multi_generation_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Multi-generation evolution engine is not configured.",
        )

    return engine


@router.post("/campaigns/{campaign_id}/run")
def run_campaign(
    campaign_id: str,
    payload: RunCampaignRequest,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _engine(request)

    try:
        return engine.run_campaign(
            campaign_id=campaign_id,
            actor_id=x_actor_id,
            feedback_recommendations=payload.feedback_recommendations,
            stop_policy=payload.stop_policy,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/campaigns/{campaign_id}/generations")
def list_generations(
    campaign_id: str,
    request: Request,
):
    engine = _engine(request)
    return engine.memory.list_generation_summaries(campaign_id)


@router.get("/campaigns/{campaign_id}/elites")
def list_elites(
    campaign_id: str,
    request: Request,
):
    engine = _engine(request)
    return engine.memory.list_elites(campaign_id)


@router.get("/campaigns/{campaign_id}/trend")
def get_campaign_trend(
    campaign_id: str,
    request: Request,
):
    engine = _engine(request)
    return engine.memory.get_trend(campaign_id)
