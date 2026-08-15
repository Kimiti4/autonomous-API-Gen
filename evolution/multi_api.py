"""
API routes for multi-candidate evolution.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request

from .models import GenerateCandidatesRequest, ParetoSelectionPolicy
from .multi import MultiCandidateEvolutionEngine


router = APIRouter(
    prefix="/v1/evolution",
    tags=["evolution-multi-candidate"],
)


def enable_multi_candidate_evolution(
    app: FastAPI,
    base_engine,
) -> MultiCandidateEvolutionEngine:
    """Enable multi-candidate evolution on an existing evolution app."""

    multi_engine = MultiCandidateEvolutionEngine(base_engine)

    app.state.multi_engine = multi_engine
    app.include_router(router)

    return multi_engine


def _multi_engine(request: Request) -> MultiCandidateEvolutionEngine:
    engine = getattr(request.app.state, "multi_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Multi-candidate evolution engine is not configured.",
        )

    return engine


@router.post("/proposals/{proposal_id}/generate-candidates")
def generate_candidates(
    proposal_id: str,
    payload: GenerateCandidatesRequest,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _multi_engine(request)
    return engine.generate_candidates(proposal_id, payload, x_actor_id)


@router.post("/proposals/{proposal_id}/evaluate-candidates")
def evaluate_candidates(
    proposal_id: str,
    request: Request,
    force: bool = False,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _multi_engine(request)
    return engine.evaluate_candidates(proposal_id, x_actor_id, force)


@router.post("/proposals/{proposal_id}/select-pareto")
def select_pareto(
    proposal_id: str,
    payload: ParetoSelectionPolicy,
    request: Request,
    x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
):
    engine = _multi_engine(request)
    return engine.select_pareto(proposal_id, payload, x_actor_id)


@router.get("/proposals/{proposal_id}/candidate-evaluations")
def get_candidate_evaluations(
    proposal_id: str,
    request: Request,
):
    engine = _multi_engine(request)
    return engine.get_evaluations(proposal_id)


@router.get("/proposals/{proposal_id}/pareto")
def get_pareto_result(
    proposal_id: str,
    request: Request,
):
    engine = _multi_engine(request)

    result = engine.get_pareto_result(proposal_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No Pareto selection result found for proposal.",
        )

    return result
