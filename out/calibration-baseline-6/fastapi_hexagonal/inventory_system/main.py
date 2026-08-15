from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from inventory_system.api.deps import make_auth_dependency
from inventory_system.api.routes import build_inventory_router
from inventory_system.application.services import InventoryService
from inventory_system.config import Settings, load_settings
from inventory_system.infrastructure.memory_repositories import InMemoryInventoryRepository
from inventory_system.logging_config import configure_logging


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name)
    auth_dependency = make_auth_dependency(settings)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/readiness")
    def readiness() -> dict:
        return {"status": "ready"}

    inventory_repository = InMemoryInventoryRepository()
    inventory_service = InventoryService(inventory_repository)
    app.include_router(build_inventory_router(inventory_service, auth_dependency))

    return app
