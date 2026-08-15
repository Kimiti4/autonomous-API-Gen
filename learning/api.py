"""
API routes for continuous learning.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import ContinuousLearningEngine
from .models import LearningPolicy, LearningSignal, LearningSignalType, Severity


router = APIRouter(
    prefix="/v1/learning",
    tags=["continuous-learning"],
)


class IngestSignalsRequest(BaseModel):
    signals: List[LearningSignal] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    subject_ref: Optional[str] = None


class CompileFeedbackRequest(BaseModel):
    scope: str = "platform"
    subject_ref: Optional[str] = None


def enable_continuous_learning(
    app: FastAPI,
    engine: ContinuousLearningEngine | None = None,
) -> ContinuousLearningEngine:
    """Enable continuous learning endpoints."""

    learning_engine = engine or ContinuousLearningEngine(LearningPolicy())

    app.state.learning_engine = learning_engine

    app.include_router(router)

    return learning_engine


def _engine(request: Request) -> ContinuousLearningEngine:
    engine = getattr(request.app.state, "learning_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Continuous learning engine is not configured.",
        )

    return engine


@router.post("/signals", status_code=201)
def ingest_signals(payload: IngestSignalsRequest, request: Request):
    engine = _engine(request)

    count = engine.ingest_batch(payload.signals)

    return {
        "ingested_signals": count,
    }


@router.post("/analyze")
def analyze(payload: AnalyzeRequest, request: Request):
    engine = _engine(request)

    insights = engine.analyze(subject_ref=payload.subject_ref)

    return {
        "new_insights": insights,
        "total_insights": len(engine.insights),
    }


@router.get("/insights")
def list_insights(request: Request):
    engine = _engine(request)
    return list(engine.insights.values())


@router.get("/recommendations")
def list_recommendations(request: Request):
    engine = _engine(request)
    return list(engine.recommendations.values())


@router.get("/fitness-updates")
def list_fitness_updates(request: Request):
    engine = _engine(request)
    return list(engine.fitness_updates.values())


@router.post("/feedback-bundle", status_code=201)
def compile_feedback(payload: CompileFeedbackRequest, request: Request):
    engine = _engine(request)

    return engine.compile_feedback(
        scope=payload.scope,
        subject_ref=payload.subject_ref,
    )


@router.get("/report")
def learning_report(request: Request):
    engine = _engine(request)
    return engine.report()
