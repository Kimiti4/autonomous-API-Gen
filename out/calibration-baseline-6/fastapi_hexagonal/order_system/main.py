from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from order_system.api.deps import make_auth_dependency
from order_system.api.routes import build_order_router
from order_system.application.services import OrderService
from order_system.config import Settings, load_settings
from order_system.infrastructure.memory_repositories import InMemoryOrderRepository
from order_system.logging_config import configure_logging


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

    order_repository = InMemoryOrderRepository()
    order_service = OrderService(order_repository)
    app.include_router(build_order_router(order_service, auth_dependency))

    return app
