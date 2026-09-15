"""Tiannara Observatory Backend application entrypoint.

NOTE on import-time behavior: module-level `app = create_app()` exists so
ASGI servers have an importable target. It creates the gateway/store
objects (opening the SQLite file) but starts no server, writes no data,
and emits no events.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router
from .bus import AsyncEventBus
from .config import get_settings
from .governance import AuthorizationError
from .gateway import NotFoundError, ObservatoryError, ObservatoryGateway
from .store import SqliteEventStore, StoreIntegrityError
from .workspace_governance_store import WorkspaceGovernanceStore
from .workspaces_routes import router as workspaces_router
from .workspaces_store import SqliteWorkspaceStore


def create_app() -> FastAPI:
    settings = get_settings()
    store = SqliteEventStore(settings.db_path)
    store.init()
    bus = AsyncEventBus()
    gateway = ObservatoryGateway(store=store, bus=bus)
    workspace_store = SqliteWorkspaceStore(settings.db_path)
    workspace_store.init()
    workspace_governance_store = WorkspaceGovernanceStore(settings.db_path)
    workspace_governance_store.init()
    app = FastAPI(
        title="Tiannara Observatory Backend",
        description=(
            "Python-native Observatory backend for Tiannara. Canonical event "
            "ingestion, epistemic projections, traceability, and governed "
            "command requests. It does not execute evolution, deployment, "
            "or production mutation."),
        version="0.1.0",
    )
    app.state.gateway = gateway
    app.state.workspace_store = workspace_store
    app.state.workspace_governance_store = workspace_governance_store
    app.include_router(router)
    app.include_router(workspaces_router)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=list(settings.cors_origins),
            allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.get("/", tags=["meta"])
    async def root():
        return {"service": "Tiannara Observatory Backend",
                "status": "ok", "endpoints": "/observatory/*"}

    @app.get("/healthz", tags=["meta"])
    async def healthz():
        return {"status": "ok"}

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={
            "error": "not_found", "detail": str(exc)})

    @app.exception_handler(AuthorizationError)
    async def authorization_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(status_code=403, content={
            "error": "authorization_failed", "detail": str(exc)})

    @app.exception_handler(StoreIntegrityError)
    async def store_integrity_handler(request: Request, exc: StoreIntegrityError):
        return JSONResponse(status_code=409, content={
            "error": "store_integrity_error", "detail": str(exc)})

    @app.exception_handler(ObservatoryError)
    async def observatory_error_handler(request: Request, exc: ObservatoryError):
        return JSONResponse(status_code=400, content={
            "error": "observatory_error", "detail": str(exc)})

    return app


app = create_app()
