from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from payment_system.api.deps import make_auth_dependency
from payment_system.api.routes import build_payment_router, build_payment_ledger_router
from payment_system.application.services import PaymentService, PaymentLedgerService
from payment_system.config import Settings, load_settings
from payment_system.infrastructure.memory_repositories import InMemoryPaymentRepository, InMemoryPaymentLedgerRepository
from payment_system.logging_config import configure_logging


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

    payment_repository = InMemoryPaymentRepository()
    payment_service = PaymentService(payment_repository)
    app.include_router(build_payment_router(payment_service, auth_dependency))

    payment_ledger_repository = InMemoryPaymentLedgerRepository()
    payment_ledger_service = PaymentLedgerService(payment_ledger_repository)
    app.include_router(build_payment_ledger_router(payment_ledger_service, auth_dependency))

    return app
