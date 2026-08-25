"""Shared Postgres fixtures for integration-marked observation tests (V1-07).

Lives at the tests/ root (not under tests/integration/) because the V1-07
tests live in tests/observation/ and pytest fixtures are conftest-scoped.
Single definition point: no duplicate fixture in subdirectory conftests.

DSN/schema are env-overridable so CI (service container on :5432) and local
docker compose (:5433, service pg-test) run the identical code path.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.observation.sequences.persisted import PersistedSequenceStore
from app.observation.sequences.sql_binding import SqlSequencePersistence

PG_DSN = os.getenv("TEST_PG_DSN", "postgresql+asyncpg://esap:esap@127.0.0.1:5433/esap_test")
SCHEMA_PATH = Path(
    os.getenv(
        "OBSERVATION_SCHEMA_SQL",
        str(Path(__file__).resolve().parents[1] / "app/observation/sequences/schema.sql"),
    )
)


@pytest_asyncio.fixture
async def pg_engine():
    engine = create_async_engine(PG_DSN, pool_pre_ping=True, pool_size=25, max_overflow=10)
    await _wait_until_ready(engine)
    await _bootstrap_schema(engine)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def pg_sequence_store(pg_engine):
    return PersistedSequenceStore(SqlSequencePersistence(pg_engine))


async def _wait_until_ready(engine, attempts=30, delay=1.0):
    for _ in range(attempts):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception:
            await asyncio.sleep(delay)
    raise RuntimeError(f"Postgres at {PG_DSN} did not become ready")


async def _bootstrap_schema(engine):
    schema_sql = SCHEMA_PATH.read_text()
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS observation_events CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS observation_stream_counters CASCADE"))
        for stmt in schema_sql.split(";"):
            s = stmt.strip()
            if s:
                await conn.execute(text(s))
