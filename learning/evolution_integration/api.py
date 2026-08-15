"""
API routes for evolutionary fitness feedback integration.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .engine import EvolutionFitnessIntegrationEngine
from .gateway import InMemoryEvolutionGateway
from .models import EvolutionFeedbackPolicy


router = APIRouter(
    prefix="/v1/learning/evolution-integration",
    tags=["evolution-fitness-integration"],
)


class ScopeRequest(BaseModel):
    scope: str = "platform"


class SubmitBundleRequest(BaseModel):
    bundle_id: Optional[str] = None


class SyncRequest(BaseModel):
    scope: str = "platform"


def enable_evolution_fitness_integration(
    app: FastAPI,
    learning_engine=None,
    analytics_engine=None,
    gateway=None,
    policy: EvolutionFeedbackPolicy | None = None,
) -> EvolutionFitnessIntegrationEngine:
    """Enable evolutionary fitness feedback integration endpoints."""

    learning_engine = learning_engine or getattr(
        app.state,
        "learning_engine",
        None,
    )

    analytics_engine = analytics_engine or getattr(
        app.state,
        "anomaly_engine",
        None,
    )

    gateway = gateway or InMemoryEvolutionGateway()

    engine = EvolutionFitnessIntegrationEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        gateway=gateway,
        policy=policy,
    )

    app.state.evolution_integration_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> EvolutionFitnessIntegrationEngine:
    engine = getattr(request.state.app, "evolution_integration_engine", None)

    if not engine:
        engine = getattr(
            request.app.state,
            "evolution_integration_engine",
            None,
        )

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Evolution fitness integration engine is not configured.",
        )

    return engine


@router.post("/generate")
def generate_feedback(payload: ScopeRequest, request: Request):
    engine = _engine(request)

    return engine.generate_feedback(scope=payload.scope)


@router.post("/submit")
def submit_feedback(payload: SubmitBundleRequest, request: Request):
    engine = _engine(request)

    try:
        return engine.submit_feedback(bundle_id=payload.bundle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sync")
def sync(payload: SyncRequest, request: Request):
    engine = _engine(request)

    return engine.sync(scope=payload.scope)


@router.get("/bundles/{bundle_id}")
def get_bundle(bundle_id: str, request: Request):
    engine = _engine(request)

    try:
        return engine.get_bundle(bundle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/fitness-state/{scope}")
def fitness_state(scope: str, request: Request):
    engine = _engine(request)

    return engine.fitness_state(scope=scope)


@router.get("/submissions")
def list_submissions(request: Request):
    engine = _engine(request)

    return list(engine.submissions.values())
