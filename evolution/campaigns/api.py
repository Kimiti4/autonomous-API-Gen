"""
API routes for multi-generation evolution campaigns.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import MultiGenerationCampaignEngine
from .gateway import DeterministicCandidateGenerator, StaticFitnessGateway
from .models import StopPolicy


router = APIRouter(
    prefix="/v1/evolution/campaigns",
    tags=["evolution-campaigns"],
)


class CreateCampaignRequest(BaseModel):
    name: str
    objective: str

    population_size: int = Field(default=5, ge=1)

    genome_ref: Optional[str] = None

    stop_policy: StopPolicy = Field(default_factory=StopPolicy)


class RunCampaignRequest(BaseModel):
    max_generations: Optional[int] = None


def enable_evolution_campaigns(
    app: FastAPI,
    engine: MultiGenerationCampaignEngine | None = None,
) -> MultiGenerationCampaignEngine:
    """Enable evolution campaign endpoints."""

    if not engine:
        engine = MultiGenerationCampaignEngine(
            candidate_generator=DeterministicCandidateGenerator(),
            fitness_gateway=StaticFitnessGateway(),
        )

    app.state.evolution_campaign_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> MultiGenerationCampaignEngine:
    engine = getattr(request.app.state, "evolution_campaign_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Evolution campaign engine is not configured.",
        )

    return engine


@router.post("", status_code=201)
def create_campaign(payload: CreateCampaignRequest, request: Request):
    engine = _engine(request)

    return engine.create_campaign(
        name=payload.name,
        objective=payload.objective,
        population_size=payload.population_size,
        genome_ref=payload.genome_ref,
        stop_policy=payload.stop_policy,
    )


@router.post("/{campaign_id}/run-generation")
def run_generation(campaign_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.run_generation(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{campaign_id}/run")
def run_campaign(
    campaign_id: str,
    payload: RunCampaignRequest,
    request: Request,
):
    engine = _engine(request)

    try:
        return engine.run_campaign(
            campaign_id,
            max_generations=payload.max_generations,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{campaign_id}/report")
def campaign_report(campaign_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.campaign_report(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{campaign_id}/memory")
def campaign_memory(campaign_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.campaign_memory(campaign_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
