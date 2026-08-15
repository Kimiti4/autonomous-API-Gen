from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from notification_system.api.deps import make_auth_dependency
from notification_system.api.routes import build_notification_router, build_notification_ledger_router
from notification_system.application.services import NotificationService, NotificationLedgerService
from notification_system.config import Settings, load_settings
from notification_system.infrastructure.memory_repositories import InMemoryNotificationRepository, InMemoryNotificationLedgerRepository
from notification_system.logging_config import configure_logging


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

    notification_repository = InMemoryNotificationRepository()
    notification_service = NotificationService(notification_repository)
    app.include_router(build_notification_router(notification_service, auth_dependency))

    notification_ledger_repository = InMemoryNotificationLedgerRepository()
    notification_ledger_service = NotificationLedgerService(notification_ledger_repository)
    app.include_router(build_notification_ledger_router(notification_ledger_service, auth_dependency))

    return app
