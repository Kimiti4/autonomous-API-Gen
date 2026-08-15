"""
API routes for production feedback integration.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request

from .feedback import InMemorySignalStore, ProductionSignal
from .feedback_engine import ProductionFeedbackAwareEngine


router = APIRouter(
    prefix="/v1/evolution/feedback",
    tags=["production-feedback"],
)


def enable_production_feedback(
    app: FastAPI,
    inner_engine,
    signal_store: InMemorySignalStore | None = None,
    policy=None,
) -> ProductionFeedbackAwareEngine:
    """Enable production feedback on an existing evolution engine."""

    feedback_engine = ProductionFeedbackAwareEngine(
        inner_engine=inner_engine,
        signal_store=signal_store,
        policy=policy,
    )

    app.state.multi_engine = feedback_engine
    app.state.feedback_engine = feedback_engine
    app.state.feedback_signal_store = feedback_engine.signal_store

    app.include_router(router)

    return feedback_engine


def _feedback_store(request: Request) -> InMemorySignalStore:
    store = getattr(request.app.state, "feedback_signal_store", None)

    if not store:
        engine = getattr(request.app.state, "feedback_engine", None)

        if engine:
            store = engine.signal_store

    if not store:
        raise HTTPException(
            status_code=500,
            detail="Production feedback store is not configured.",
        )

    return store


def _feedback_engine(request: Request) -> ProductionFeedbackAwareEngine:
    engine = getattr(request.app.state, "feedback_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Production feedback engine is not configured.",
        )

    return engine


@router.post("/signals", status_code=201)
def add_signal(
    payload: ProductionSignal,
    request: Request,
):
    store = _feedback_store(request)
    return store.add_signal(payload)


@router.get("/signals")
def list_signals(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
):
    store = _feedback_store(request)
    return store.list_signals(limit=limit)


@router.get("/reports/{proposal_id}/{candidate_id}")
def get_feedback_report(
    proposal_id: str,
    candidate_id: str,
    request: Request,
):
    engine = _feedback_engine(request)

    report = engine.get_feedback_report(proposal_id, candidate_id)

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No feedback report found for candidate.",
        )

    return report


@router.get("/recommendations/{proposal_id}/{candidate_id}")
def get_genome_recommendations(
    proposal_id: str,
    candidate_id: str,
    request: Request,
):
    engine = _feedback_engine(request)

    return engine.get_genome_recommendations(proposal_id, candidate_id)
