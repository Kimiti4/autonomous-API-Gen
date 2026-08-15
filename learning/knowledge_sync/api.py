"""
API routes for Knowledge Graph learning synchronization.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Request

from ..analytics.engine import AnomalyCorrelationEngine
from ..engine import ContinuousLearningEngine
from .engine import KnowledgeSyncEngine
from .models import KnowledgeGraphGateway


router = APIRouter(
    prefix="/v1/learning/knowledge-sync",
    tags=["knowledge-graph-sync"],
)


def enable_knowledge_sync(
    app: FastAPI,
    learning_engine: ContinuousLearningEngine | None = None,
    analytics_engine: AnomalyCorrelationEngine | None = None,
    kg_gateway: KnowledgeGraphGateway | None = None,
) -> KnowledgeSyncEngine:
    """Enable Knowledge Graph sync endpoints."""

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

    kg_gateway = kg_gateway or getattr(
        app.state,
        "knowledge_graph_gateway",
        None,
    )

    if not learning_engine or not analytics_engine or not kg_gateway:
        raise RuntimeError(
            "Learning engine, analytics engine, and KG gateway are required."
        )

    sync_engine = KnowledgeSyncEngine(
        learning_engine=learning_engine,
        analytics_engine=analytics_engine,
        kg_gateway=kg_gateway,
    )

    app.state.knowledge_sync_engine = sync_engine

    app.include_router(router)

    return sync_engine


def _engine(request: Request) -> KnowledgeSyncEngine:
    engine = getattr(request.app.state, "knowledge_sync_engine", None)

    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Knowledge sync engine is not configured.",
        )

    return engine


@router.post("/sync")
def sync_learning_evidence(request: Request):
    engine = _engine(request)

    return engine.sync()


@router.get("/state")
def get_sync_state(request: Request):
    engine = _engine(request)

    return engine.get_registry_state()
