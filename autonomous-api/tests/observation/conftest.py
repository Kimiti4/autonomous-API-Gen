"""Shared fixtures for the observation subsystem tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.middleware.security import (
    ApiKeyAuthProvider,
    CompositeAuthProvider,
    set_auth_provider,
)
from app.observation.gateway.dispatcher import EventDispatcher
from app.observation.projectors.fitness import FitnessProjector
from app.observation.sequences.memory import InMemorySequenceStore
from app.api.observation_routes import configure_observation

TEST_API_KEY = "test-admin-key"


class _FakeGenerationProvider:
    """In-memory CanonicalStateProvider stub for tests."""

    def __init__(self, generations: dict):
        self._generations = generations

    async def get_isr(self):
        return {}

    async def get_generation(self, generation: int):
        return self._generations.get(generation, [])

    async def get_lineage(self, candidate_id: str):
        return None


@pytest.fixture()
def sequence_store():
    return InMemorySequenceStore()


@pytest.fixture()
def dispatcher(sequence_store):
    from app.core.contracts.events import EventSource

    return EventDispatcher(
        store=sequence_store,
        source=EventSource(subsystem="test", revision="test-rev"),
    )


@pytest.fixture()
def fitness_projector():
    # Two candidates: A dominates B on every objective dimension.
    rich = {
        "services": ["svc-a", "svc-b", "svc-c", "svc-d", "svc-e", "svc-f"],
        "auth": "jwt",
        "database": "postgres",
        "cache_enabled": True,
        "rate_limiting": True,
        "cors_enabled": True,
        "logging_level": "INFO",
        "health_endpoints": True,
        "metrics_endpoints": True,
        "tracing_enabled": True,
        "circuit_breaker": True,
        "backends": [{"type": "rest", "implementation": "fastapi"}],
        "middleware": [{"name": "cors"}],
    }
    poor = {
        "services": ["svc-a"],
        "auth": "none",
        "database": "sqlite",
        "cache_enabled": False,
        "rate_limiting": False,
        "cors_enabled": False,
        "logging_level": "DEBUG",
        "health_endpoints": False,
        "metrics_endpoints": False,
        "tracing_enabled": False,
        "circuit_breaker": False,
        "backends": [],
        "middleware": [],
    }
    provider = _FakeGenerationProvider(
        {1: [{"genome_data": rich}, {"genome_data": poor}]}
    )
    return FitnessProjector(provider=provider, source_revision="test-rev")


@pytest.fixture()
def client(sequence_store, dispatcher, fitness_projector):
    settings = get_settings()
    settings.ADMIN_API_KEY = TEST_API_KEY

    set_auth_provider(
        CompositeAuthProvider([ApiKeyAuthProvider(api_key=TEST_API_KEY)])
    )
    configure_observation(
        store=sequence_store,
        dispatcher=dispatcher,
        fitness_projector=fitness_projector,
    )

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}