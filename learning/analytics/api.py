"""
API routes for anomaly detection and signal correlation.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel

from ..engine import ContinuousLearningEngine
from .engine import AnomalyCorrelationEngine
from .models import AnomalyDetectionPolicy


router = APIRouter(
    prefix="/v1/learning/analytics",
    tags=["anomaly-detection"],
)


class AnalyzeRequest(BaseModel):
    subject_ref: Optional[str] = None


def enable_anomaly_detection(
    app: FastAPI,
    learning_engine: ContinuousLearningEngine | None = None,
    policy: AnomalyDetectionPolicy | None = None,
) -> AnomalyCorrelationEngine:
    """Enable anomaly detection endpoints."""

    engine = learning_engine or getattr(app.state, "learning_engine", None)

    if not engine:
        engine = ContinuousLearningEngine()
        app.state.learning_engine = engine

    analytics_engine = AnomalyCorrelationEngine(
        learning_engine=engine,
        policy=policy,
    )

    app.state.anomaly_engine = analytics_engine

    app.include_router(router)

    return analytics_engine


def _engine(request: Request) -> AnomalyCorrelationEngine:
    engine = getattr(request.app.state, "anomaly_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Anomaly detection engine is not configured.",
        )

    return engine


@router.post("/analyze")
def analyze(payload: AnalyzeRequest, request: Request):
    engine = _engine(request)

    return engine.analyze(subject_ref=payload.subject_ref)


@router.get("/anomalies")
def list_anomalies(request: Request):
    engine = _engine(request)
    return list(engine.anomalies.values())


@router.get("/clusters")
def list_clusters(request: Request):
    engine = _engine(request)
    return list(engine.clusters.values())


@router.get("/insights")
def list_insights(request: Request):
    engine = _engine(request)
    return list(engine.insights.values())


@router.get("/report")
def analytics_report(request: Request):
    engine = _engine(request)

    return {
        "anomaly_count": len(engine.anomalies),
        "cluster_count": len(engine.clusters),
        "insight_count": len(engine.insights),
    }
