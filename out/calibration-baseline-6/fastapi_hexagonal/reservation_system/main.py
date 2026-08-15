from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from reservation_system.api.deps import make_auth_dependency
from reservation_system.api.routes import build_reservation_router
from reservation_system.application.services import ReservationService
from reservation_system.config import Settings, load_settings
from reservation_system.infrastructure.memory_repositories import InMemoryReservationRepository
from reservation_system.logging_config import configure_logging


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

    reservation_repository = InMemoryReservationRepository()
    reservation_service = ReservationService(reservation_repository)
    app.include_router(build_reservation_router(reservation_service, auth_dependency))

    return app
