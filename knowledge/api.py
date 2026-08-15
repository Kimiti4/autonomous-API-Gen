"""
Knowledge Graph API.

This is the external interface for the Phase 23 Knowledge Graph runtime.

It exposes:
- Entity creation and retrieval
- Relation creation and retrieval
- Ingestion
- Querying
- Searching
- Traceability
- Health checks
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from .compiler import KnowledgeCompiler
from .errors import KnowledgeGraphError, NotFound
from .models import (
    EntityCreate,
    IngestRequest,
    QueryRequest,
    RelationCreate,
    SearchRequest,
    SourceRef,
)
from .runtime import GraphRuntime
from .search import InMemorySearchStore
from .store import InMemoryGraphStore
from .recommendations.routes import router as recommendation_analytics_router
from .traceability.routes import router as traceability_router
from .visualization.routes import router as visualization_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise Knowledge Graph",
        version="0.1.0",
        description=(
            "Phase 23 Knowledge Graph runtime. "
            "This service is an evidence and traceability substrate. "
            "It does not mutate ISR and does not execute governance actions."
        ),
    )

    graph_store = InMemoryGraphStore()
    search_store = InMemorySearchStore()
    runtime = GraphRuntime(graph_store=graph_store, search_store=search_store)
    compiler = KnowledgeCompiler(runtime=runtime)

    app.state.runtime = runtime
    app.state.compiler = compiler

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
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return runtime.create_entity(payload, actor=x_actor_id)

    @app.get("/v1/knowledge/entities/{entity_id}")
    def get_entity(entity_id: str):
        return runtime.get_entity(entity_id)

    @app.post("/v1/knowledge/relations", status_code=201)
    def create_relation(
        payload: RelationCreate,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return runtime.create_relation(payload, actor=x_actor_id)

    @app.get("/v1/knowledge/relations/{relation_id}")
    def get_relation(relation_id: str):
        return runtime.get_relation(relation_id)

    @app.post("/v1/knowledge/ingest")
    def ingest(
        payload: IngestRequest,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
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


app = create_app()
