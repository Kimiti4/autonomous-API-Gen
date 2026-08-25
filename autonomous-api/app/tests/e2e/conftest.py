from __future__ import annotations
from types import SimpleNamespace
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from core.contracts.events import EventSource
from observation.gateway.dispatcher import EventDispatcher
from observation.readmodel.checkpoints import InMemoryCheckpointStore
from observation.readmodel.materializer import StateMaterializer
from observation.readmodel.reducer import CompositeObservationReducer
from observation.sequences.persisted import PersistedSequenceStore
from observation.sequences.sql_binding import SqlSequencePersistence
from tests.e2e.oracle import TruthfulnessOracle
from tests.integration.conftest import PG_DSN, _bootstrap_schema
async def _build_stack(engine):
    store = PersistedSequenceStore(SqlSequencePersistence(engine))
    reducer = CompositeObservationReducer()
    materializer = StateMaterializer(reducer=reducer, sequence_store=store, checkpoint_store=InMemoryCheckpointStore(), checkpoint_interval=50)
    dispatcher = EventDispatcher(store=store, source=EventSource(subsystem="e2e", revision="e2e"), materializer=materializer)
    return SimpleNamespace(engine=engine, store=store, reducer=reducer, materializer=materializer, dispatcher=dispatcher, oracle=TruthfulnessOracle(reducer, store))
@pytest_asyncio.fixture
async def e2e_platform(pg_engine):
    return await _build_stack(pg_engine)
@pytest_asyncio.fixture
async def rebuild_stack():
    engines = []
    async def _rebuild():
        engine = create_async_engine(PG_DSN, pool_pre_ping=True, pool_size=25, max_overflow=10)
        await _bootstrap_schema(engine)
        engines.append(engine)
        return await _build_stack(engine)
    yield _rebuild
    for e in engines:
        await e.dispose()
