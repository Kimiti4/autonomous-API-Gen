"""
Production application factory for the Knowledge Graph.

This wires the runtime with persistent adapters, audit emission,
governance integration, and the recommendation engine.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from .adapters.sqlite_stores import SQLiteGraphStore, SQLiteSearchStore
from .auth import Actor, get_actor, require_role
from .audit import LoggingAuditEmitter
from .compiler import KnowledgeCompiler
from .errors import KnowledgeGraphError, NotFound
from .governance import HttpGovernanceKernelClient
from .models import (
    EntityCreate,
    IngestRequest,
    QueryRequest,
    RelationCreate,
    SearchRequest,
    SourceRef,
)
from .recommendation import RecommendationEngine
from .runtime import GraphRuntime
from .recommendations.routes import router as recommendation_analytics_router
from .traceability.routes import router as traceability_router
from .visualization.routes import router as visualization_router


def create_production_app(database_path: Optional[str] = None) -> FastAPI:
    database_path = database_path or os.getenv(
        "KNOWLEDGE_GRAPH_DB",
        "knowledge_graph.db",
    )

    governance_base_url = os.getenv(
        "GOVERNANCE_KERNEL_BASE_URL",
        "http://localhost:8000",
    )

    graph_store = SQLiteGraphStore(database_path)
    search_store = SQLiteSearchStore(database_path)

    runtime = GraphRuntime(
        graph_store=graph_store,
        search_store=search_store,
    )

    compiler = KnowledgeCompiler(runtime=runtime)

    audit_emitter = LoggingAuditEmitter()
    governance_client = HttpGovernanceKernelClient(
        base_url=governance_base_url,
    )

    recommendation_engine = RecommendationEngine(
        governance_client=governance_client,
        audit_emitter=audit_emitter,
    )

    app = FastAPI(
        title="Enterprise Knowledge Graph",
        version="0.2.0",
        description=(
            "Phase 23 Knowledge Graph production runtime. "
            "This service is an evidence and traceability substrate. "
            "It does not mutate ISR and does not execute governance actions."
        ),
    )

    app.state.runtime = runtime
    app.state.compiler = compiler
    app.state.recommendation_engine = recommendation_engine
    app.state.graph_store = graph_store
    app.state.search_store = search_store

    app.include_router(visualization_router)
    app.include_router(traceability_router)
    app.include_router(recommendation_analytics_router)

    @app.exception_handler(NotFound)
    async def not_found_handler(request: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"message": str(exc)},
        )

    @app.exception_handler(KnowledgeGraphError)
    async def knowledge_graph_error_handler(
        request: Request,
        exc: KnowledgeGraphError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"message": str(exc)},
        )

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def health_ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/v1/knowledge/entities")
    def list_entities(
        entity_type: Optional[str] = Query(default=None),
        namespace: Optional[str] = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
    ):
        return runtime.list_entities(
            entity_type=entity_type,
            namespace=namespace,
            limit=limit,
        )

    @app.post("/v1/knowledge/entities", status_code=201)
    def create_entity(
        payload: EntityCreate,
        actor: Actor = Depends(get_actor),
    ):
        require_role(actor, "knowledge_writer")

        return runtime.create_entity(payload, actor=actor.actor_id)

    @app.get("/v1/knowledge/entities/{entity_id}")
    def get_entity(entity_id: str):
        return runtime.get_entity(entity_id)

    @app.post("/v1/knowledge/relations", status_code=201)
    def create_relation(
        payload: RelationCreate,
        actor: Actor = Depends(get_actor),
    ):
        require_role(actor, "knowledge_writer")

        return runtime.create_relation(payload, actor=actor.actor_id)

    @app.get("/v1/knowledge/relations/{relation_id}")
    def get_relation(relation_id: str):
        return runtime.get_relation(relation_id)

    @app.post("/v1/knowledge/ingest")
    def ingest(
        payload: IngestRequest,
        actor: Actor = Depends(get_actor),
    ):
        require_role(actor, "knowledge_ingestor")

        source_ref = SourceRef(
            source_type=payload.source_type,
            source_id=payload.source_id,
            source_hash=payload.source_hash,
        )

        if payload.source_type == "ISR_REVISION":
            return compiler.compile_isr_revision(
                source_ref=source_ref,
                payload=payload.payload,
            )

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source_type: {payload.source_type}",
        )

    @app.post("/v1/knowledge/query")
    def query(payload: QueryRequest):
        return runtime.query(payload)

    @app.post("/v1/knowledge/search")
    def search(payload: SearchRequest):
        return runtime.search(payload)

    @app.get("/v1/knowledge/trace/{entity_id}/backward")
    def trace_backward(
        entity_id: str,
        depth: int = Query(default=3, ge=1, le=10),
    ):
        request = QueryRequest(
            query_type="TRACE",
            entity_id=entity_id,
            direction="both",
            depth=depth,
        )

        return runtime.query(request)

    @app.get("/v1/knowledge/trace/{entity_id}/forward")
    def trace_forward(
        entity_id: str,
        depth: int = Query(default=3, ge=1, le=10),
    ):
        request = QueryRequest(
            query_type="TRACE",
            entity_id=entity_id,
            direction="both",
            depth=depth,
        )

        return runtime.query(request)

    return app


app = create_production_app()
