"""Composition root for the Autonomous Evolution Engine."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.ws import router as ws_router
from app.api.observation_routes import router as observation_router
from app.api.governance_routes import router as governance_router
from app.core.config import get_settings
from app.core.logger import logger
from app.middleware.error_handler import ErrorHandlingConfig, install_error_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import (
    ApiKeyAuthProvider,
    CompositeAuthProvider,
    SecurityHeadersMiddleware,
    set_auth_provider,
    validate_auth_config,
    validate_cors_origins,
)
from app.observation.gateway.dispatcher import EventDispatcher
from app.observation.projectors.fitness import FitnessProjector
from app.observation.sequences.memory import InMemorySequenceStore
from app.core.contracts.events import EventSource
from app.storage.db import init_db, engine as db_engine
from app.storage.models import GenomeRecord
from app.core.metrics import setup_metrics
from app.engine.evolution import EvolutionEngine
from app.governance.subsystem import GovernanceSubsystem
from app.governance.adapters.sqlite import (
    SqliteGovernanceEventStore,
    SqliteGovernanceReferenceStore,
)
from app.governance.runtime import configure_governance

settings = get_settings()

auth_providers = []
if settings.ADMIN_API_KEY:
    auth_providers.append(ApiKeyAuthProvider(api_key=settings.ADMIN_API_KEY))
validate_auth_config(settings.ENVIRONMENT, auth_providers)
if auth_providers:
    set_auth_provider(CompositeAuthProvider(auth_providers))
else:
    logger.warning(
        "No ADMIN_API_KEY configured — protected endpoints will reject requests."
    )

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Evolution Engine - Genetic API Architecture Generator",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

validated_origins = validate_cors_origins(settings.CORS_ORIGINS)
logger.info(f"CORS origins configured: {validated_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=validated_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600,
)

install_error_handlers(app, ErrorHandlingConfig(source_revision=settings.APP_VERSION))

if settings.ENVIRONMENT == "production":
    from app.observation.sequences.persisted import PersistedSequenceStore
    from app.observation.sequences.sql_binding import SqlSequencePersistence

    store = PersistedSequenceStore(SqlSequencePersistence(db_engine))
else:
    store = InMemorySequenceStore()

dispatcher = EventDispatcher(
    store=store,
    source=EventSource(subsystem="evolution-engine", revision=settings.APP_VERSION),
)


class _DbGenerationProvider:
    """Concrete CanonicalStateProvider over the existing GenomeRecord table."""

    async def get_isr(self):
        raise NotImplementedError("ISR binding is a declared audit gap")

    async def get_generation(self, generation: int):
        from sqlalchemy.orm import Session

        with Session(db_engine) as session:
            rows = session.query(GenomeRecord).filter(GenomeRecord.generation == generation).all()
            return [row.to_dict() for row in rows]

    async def get_lineage(self, candidate_id: str):
        return None


fitness_projector = FitnessProjector(
    provider=_DbGenerationProvider(), source_revision=settings.APP_VERSION
)

from app.api.observation_routes import configure_observation

configure_observation(
    store=store,
    dispatcher=dispatcher,
    fitness_projector=fitness_projector,
)


def _governance_certifiers() -> set[str]:
    return {
        value.strip()
        for value in settings.GOVERNANCE_CERTIFIERS.split(",")
        if value.strip()
    }


governance = GovernanceSubsystem(
    event_store=SqliteGovernanceEventStore(settings.GOVERNANCE_AUDIT_SIGNING_KEY or settings.SECRET_KEY),
    reference_store=SqliteGovernanceReferenceStore(),
    quorum_threshold=settings.GOVERNANCE_QUORUM_THRESHOLD,
    recognized_certifiers=_governance_certifiers() or None,
    executive_voting_weight=settings.GOVERNANCE_EXECUTIVE_WEIGHT,
)
configure_governance(governance)


async def manager_broadcast(envelope) -> None:
    await ws_manager.broadcast(envelope.model_dump(mode="json"))


def _bridge_to_ws(envelope) -> None:
    import asyncio

    asyncio.ensure_future(manager_broadcast(envelope))


from app.api.ws import manager as ws_manager  # noqa: E402

dispatcher.subscribe(_bridge_to_ws)

try:
    from app.api.routes import evolution_engine, elite_engine

    evolution_engine.set_dispatcher(dispatcher)
    elite_engine.set_dispatcher(dispatcher)
except Exception:  # pragma: no cover
    logger.warning("Evolution engine dispatcher injection deferred")

app.include_router(router)
app.include_router(ws_router)
app.include_router(observation_router)
app.include_router(governance_router)
setup_metrics(app)


@app.get("/")
async def root():
    return {
        "message": "Autonomous Evolution Engine",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "websocket": "/ws/evolution",
    }


@app.on_event("startup")
async def startup_event():
    """Initialize critical services; fail startup if the database cannot initialize."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Ollama URL: {settings.OLLAMA_URL}")
    logger.info(f"Model: {settings.OLLAMA_MODEL}")
    try:
        init_db()
        recovered = EvolutionEngine.recover_interrupted_runs()
        if recovered:
            logger.warning(
                "Recovered %s interrupted evolution run(s) as abandoned", recovered
            )
        logger.info("Database initialized successfully")
    except Exception:
        logger.exception("Database initialization failed; refusing to start")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application")
