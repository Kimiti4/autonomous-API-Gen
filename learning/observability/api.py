"""
API routes for learning observability and operational dashboards.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from .engine import LearningObservabilityEngine
from .models import ObservabilityPolicy


router = APIRouter(
    prefix="/v1/learning/observability",
    tags=["learning-observability"],
)


def enable_learning_observability(
    app: FastAPI,
    learning_engine=None,
    analytics_engine=None,
    integration_engine=None,
    governance_engine=None,
    knowledge_sync_engine=None,
    policy: ObservabilityPolicy | None = None,
) -> LearningObservabilityEngine:
    """Enable learning observability endpoints."""

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

    integration_engine = integration_engine or getattr(
        app.state,
        "evolution_integration_engine",
        None,
    )

    governance_engine = governance_engine or getattr(
        app.state,
        "learning_governance_engine",
        None,
    )

    knowledge_sync_engine = knowledge_sync_engine or getattr(
        app.state,
        "knowledge_sync_engine",
        None,
    )

    engine = LearningObservabilityEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        integration_engine=integration_engine,
        governance_engine=governance_engine,
        knowledge_sync_engine=knowledge_sync_engine,
        policy=policy,
    )

    app.state.learning_observability_engine = engine

    app.include_router(router)

    return engine


def _engine(request: Request) -> LearningObservabilityEngine:
    engine = getattr(
        request.app.state,
        "learning_observability_engine",
        None,
    )

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Learning observability engine is not configured.",
        )

    return engine


@router.get("/metrics")
def metrics(request: Request):
    engine = _engine(request)
    return engine.metrics_snapshot()


@router.get("/health")
def health(request: Request):
    engine = _engine(request)
    return engine.operational_health()


@router.get("/dashboard")
def dashboard(
    request: Request,
    format: str = Query(default="json"),
):
    engine = _engine(request)

    dashboard = engine.dashboard()

    if format == "html":
        return HTMLResponse(engine.render_dashboard_html(dashboard))

    return dashboard


@router.get("/report")
def report(request: Request):
    engine = _engine(request)

    return engine.report()
