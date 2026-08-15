from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from subscription_system.api.deps import make_auth_dependency
from subscription_system.api.routes import build_subscription_router, build_subscription_ledger_router
from subscription_system.application.services import SubscriptionService, SubscriptionLedgerService
from subscription_system.config import Settings, load_settings
from subscription_system.infrastructure.memory_repositories import InMemorySubscriptionRepository, InMemorySubscriptionLedgerRepository
from subscription_system.logging_config import configure_logging


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

    subscription_repository = InMemorySubscriptionRepository()
    subscription_service = SubscriptionService(subscription_repository)
    app.include_router(build_subscription_router(subscription_service, auth_dependency))

    subscription_ledger_repository = InMemorySubscriptionLedgerRepository()
    subscription_ledger_service = SubscriptionLedgerService(subscription_ledger_repository)
    app.include_router(build_subscription_ledger_router(subscription_ledger_service, auth_dependency))

    return app
