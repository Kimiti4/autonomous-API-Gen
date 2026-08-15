"""
API routes for evolutionary crossover and recombination.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .population import PopulationDiversityController
from .recombination import (
    OffspringCandidate,
    RecombinationContext,
    RecombinationEngine,
    RecombinationPolicy,
    register_offspring_candidate,
)


router = APIRouter(
    prefix="/v1/evolution/recombination",
    tags=["evolutionary-recombination"],
)


class RecombineISRsRequest(BaseModel):
    parent_a_isr: Dict
    parent_b_isr: Dict

    policy: Optional[RecombinationPolicy] = None
    context: Optional[RecombinationContext] = None


class RecombineCandidatesRequest(BaseModel):
    candidate_a_id: str
    candidate_b_id: str

    policy: Optional[RecombinationPolicy] = None
    context: Optional[RecombinationContext] = None


class RegisterOffspringRequest(BaseModel):
    proposal_id: str
    offspring: OffspringCandidate


class DiversitySelectionRequest(BaseModel):
    candidate_ids: List[str]
    max_select: int = Field(default=5, ge=1, le=100)

    existing_ids: List[str] = Field(default_factory=list)

    isr_by_candidate_id: Dict[str, Dict] = Field(default_factory=dict)


def enable_recombination(app: FastAPI) -> RecombinationEngine:
    """Enable recombination endpoints."""

    engine = RecombinationEngine()
    diversity_controller = PopulationDiversityController()

    app.state.recombination_engine = engine
    app.state.population_diversity = diversity_controller

    app.include_router(router)

    return engine


def _recombination_engine(request: Request) -> RecombinationEngine:
    engine = getattr(request.app.state, "recombination_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Recombination engine is not configured.",
        )

    return engine


def _diversity_controller(request: Request) -> PopulationDiversityController:
    controller = getattr(request.app.state, "population_diversity", None)

    if not controller:
        raise HTTPException(
            status_code=500,
            detail="Population diversity controller is not configured.",
        )

    return controller


def _base_engine(request: Request):
    base_engine = getattr(request.app.state, "engine", None)

    if not base_engine:
        raise HTTPException(
            status_code=500,
            detail="Base evolution engine is not configured.",
        )

    return base_engine


@router.post("/recombine-isrs")
def recombine_isrs(payload: RecombineISRsRequest, request: Request):
    engine = _recombination_engine(request)

    return engine.recombine_candidates(
        parent_a=payload.parent_a_isr,
        parent_b=payload.parent_b_isr,
        policy=payload.policy,
        context=payload.context,
    )


@router.post("/recombine-candidates")
def recombine_candidates(payload: RecombineCandidatesRequest, request: Request):
    engine = _recombination_engine(request)
    base_engine = _base_engine(request)

    candidate_a = base_engine.candidates.get(payload.candidate_a_id)
    candidate_b = base_engine.candidates.get(payload.candidate_b_id)

    if not candidate_a:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate not found: {payload.candidate_a_id}",
        )

    if not candidate_b:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate not found: {payload.candidate_b_id}",
        )

    context = payload.context or RecombinationContext(
        parent_candidate_ids=[
            payload.candidate_a_id,
            payload.candidate_b_id,
        ],
    )

    return engine.recombine_candidates(
        parent_a=candidate_a,
        parent_b=candidate_b,
        policy=payload.policy,
        context=context,
    )


@router.post("/register-offspring")
def register_offspring(payload: RegisterOffspringRequest, request: Request):
    base_engine = _base_engine(request)

    try:
        return register_offspring_candidate(
            base_engine=base_engine,
            proposal_id=payload.proposal_id,
            offspring=payload.offspring,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/diversity/select")
def select_diverse(payload: DiversitySelectionRequest, request: Request):
    controller = _diversity_controller(request)

    for candidate_id, isr in payload.isr_by_candidate_id.items():
        controller.register_candidate(candidate_id, isr)

    return controller.select_diverse(
        candidate_ids=payload.candidate_ids,
        max_select=payload.max_select,
        existing_ids=payload.existing_ids,
    )
